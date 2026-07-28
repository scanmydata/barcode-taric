"""Δωρεάν AI providers (OpenRouter :free -> DuckDuckGo -> Pollinations) + Groq stub.

Η σειρά καθορίζεται από τις ρυθμίσεις (`ai_provider_order`). Κάθε provider που
αποτυγχάνει/δεν έχει key παρακάμπτεται σιωπηλά. Επιστρέφεται το πρώτο μη-κενό
αποτέλεσμα. Στόχος: μηδενικό κόστος, χωρίς σκληρή εξάρτηση από ένα μόνο provider.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
from typing import Any, Optional

from ..config import SETTINGS
from .http_util import debug, http_json, http_text

POLLINATIONS_URL = "https://text.pollinations.ai/{prompt}"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DUCKDUCKGO_AI_URL = os.getenv("DUCKDUCKGO_AI_URL", "https://duckduckgo.com/duckchat/v1/chat")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _parse_ai_text(response: Any) -> Optional[str]:
    if response is None:
        return None
    if isinstance(response, str):
        return response.strip() or None
    if isinstance(response, dict):
        for key in ("text", "output", "answer", "response", "content", "message"):
            value = response.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if isinstance(response.get("choices"), list) and response["choices"]:
            choice = response["choices"][0]
            if isinstance(choice, dict):
                msg = choice.get("message") or choice
                return _parse_ai_text(msg)
        if isinstance(response.get("results"), list) and response["results"]:
            return _parse_ai_text(response["results"][0])
    return None


DEFAULT_FREE_MODEL = "openai/gpt-oss-20b:free"

# Προτιμώμενες οικογένειες (καλά instruct μοντέλα για ταξινόμηση/JSON). Ό,τι ταιριάζει
# ανεβαίνει στην κορυφή της λίστας/δοκιμής. Χαμηλότερα = generic router fallback.
_PREFERRED_FREE = (
    "openai/gpt-oss", "deepseek", "qwen", "meta-llama/llama-3.3", "meta-llama/llama-3.1",
    "google/gemma", "mistral", "nvidia/nemotron", "openrouter/free",
)
# Μοντέλα που ΔΕΝ κάνουν για chat/JSON (audio/image/video/embeddings/moderation) — εκτός.
_EXCLUDE_FREE = (
    "lyria", "whisper", "tts", "audio", "vision-only", "embedding", "embed",
    "content-safety", "moderation", "guard", "rerank", "image", "sdxl", "flux", "clip",
)

# Session cache: το τελευταίο μοντέλο που όντως απάντησε (για auto-fallback).
_WORKING_MODEL: Optional[str] = None


def _ensure_free(model: str) -> str:
    """Εγγύηση ότι χρησιμοποιείται ΜΟΝΟ δωρεάν μοντέλο OpenRouter (:free suffix)."""
    model = (model or "").strip() or DEFAULT_FREE_MODEL
    # generic router alias (openrouter/free) δεν παίρνει :free suffix
    if model == "openrouter/free" or model.endswith(":free"):
        return model
    return f"{model}:free"


def _rank_free(models: list[str]) -> list[str]:
    """Ταξινόμηση δωρεάν μοντέλων: προτιμώμενες οικογένειες πρώτα, με σταθερή σειρά."""
    def key(mid: str):
        low = mid.lower()
        rank = next((i for i, fam in enumerate(_PREFERRED_FREE) if fam in low), len(_PREFERRED_FREE))
        return (rank, mid)
    return sorted(models, key=key)


def _openrouter_call(model: str, prompt: str, timeout: int) -> Optional[str]:
    """Μία κλήση σε συγκεκριμένο μοντέλο. Πετάει HTTPError σε 404 (μοντέλο δεν υπάρχει)."""
    api_key = SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    response = http_json(
        OPENROUTER_URL, method="POST", body=payload,
        headers={"Authorization": f"Bearer {api_key}",
                 "HTTP-Referer": "https://barcodetaric.local",
                 "X-Title": "BarcodeTaric"}, timeout=timeout,
    )
    if isinstance(response, dict) and response.get("error"):
        debug(f"OpenRouter error ({model}): {response.get('error')}")
        return None
    return _parse_ai_text(response)


def _openrouter(prompt: str, timeout: int) -> Optional[str]:
    global _WORKING_MODEL
    api_key = SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    # Σειρά δοκιμής: working-cache -> ρυθμισμένο -> γνωστό-καλό default -> generic router.
    # (το openrouter/free δίνει απρόβλεπτη έξοδο, μπαίνει ΤΕΛΕΥΤΑΙΟ.)
    chain: list[str] = []
    for m in (_WORKING_MODEL, _ensure_free(SETTINGS.get("openrouter_model")),
              DEFAULT_FREE_MODEL, "openrouter/free"):
        if m and m not in chain:
            chain.append(m)
    for model in chain:
        try:
            result = _openrouter_call(model, prompt, timeout)
        except urllib.error.HTTPError as exc:
            # 404 = μοντέλο αποσύρθηκε/δεν υπάρχει -> δοκίμασε το επόμενο στην αλυσίδα.
            if exc.code in (400, 404):
                debug(f"OpenRouter model '{model}' -> HTTP {exc.code}, fallback στο επόμενο")
                continue
            raise
        if result:
            if model != _WORKING_MODEL:
                debug(f"OpenRouter working model: {model}")
                _WORKING_MODEL = model
            return result
    return None


def list_free_models(timeout: int = 15) -> list[str]:
    """Δωρεάν chat μοντέλα OpenRouter (pricing prompt==0), φιλτραρισμένα & ταξινομημένα.

    Αποκλείει audio/image/embedding/moderation μοντέλα και βάζει τις καλές instruct
    οικογένειες πρώτες (βλ. `_rank_free`) ώστε η «έξυπνη» επιλογή να πετύχει γρήγορα.
    """
    try:
        data = http_json("https://openrouter.ai/api/v1/models", timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        debug(f"list_free_models failed: {exc}")
        return []
    out = []
    for m in (data.get("data") or []):
        mid = m.get("id", "")
        low = mid.lower()
        pricing = m.get("pricing") or {}
        is_free = mid.endswith(":free") or (str(pricing.get("prompt", "1")) in ("0", "0.0"))
        if not is_free or any(bad in low for bad in _EXCLUDE_FREE):
            continue
        # κράτα μόνο μοντέλα με text output (αν το API δίνει modalities)
        modalities = ((m.get("architecture") or {}).get("output_modalities")) or ["text"]
        if "text" not in modalities:
            continue
        out.append(mid)
    return _rank_free(list(set(out)))


def best_free_model(timeout: int = 12, tries: int = 4) -> Optional[str]:
    """«Έξυπνη» επιλογή: δοκιμάζει τα κορυφαία δωρεάν μοντέλα & επιστρέφει το 1ο που απαντά.

    Χρήσιμο όταν το αποθηκευμένο μοντέλο αποσύρθηκε (404). Αποθηκεύει το εύρημα σε
    `_WORKING_MODEL` για αυτόματο fallback μέσα στη session.
    """
    global _WORKING_MODEL
    api_key = SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    candidates = list_free_models(timeout=timeout)[:tries] or [DEFAULT_FREE_MODEL, "openrouter/free"]
    for mid in candidates:
        try:
            if _openrouter_call(mid, "Reply with the single word OK.", timeout):
                _WORKING_MODEL = mid
                debug(f"best_free_model picked: {mid}")
                return mid
        except Exception as exc:  # noqa: BLE001
            debug(f"best_free_model: {mid} failed: {exc}")
    return None


def test_providers(timeout: int = 12) -> list[tuple[str, bool, str]]:
    """Debugger: δοκιμάζει κάθε provider της αλυσίδας & επιστρέφει (name, ok, μήνυμα)."""
    order = SETTINGS.get("ai_provider_order") or _DEFAULT_ORDER
    results = []
    for name in order:
        fn = _PROVIDERS.get(name)
        if fn is None:
            results.append((name, False, "άγνωστος provider"))
            continue
        try:
            r = fn("Reply with the single word OK.", timeout)
            results.append((name, bool(r), (r or "κενή απάντηση")[:60]))
        except Exception as exc:  # noqa: BLE001
            results.append((name, False, f"{type(exc).__name__}: {str(exc)[:60]}"))
    return results


def _custom(prompt: str, timeout: int) -> Optional[str]:
    """Custom OpenAI-συμβατό endpoint (μελλοντικό/on-prem).

    Ενεργοποιείται μόνο αν έχει οριστεί `custom_ai_base_url`. Δέχεται είτε πλήρες
    URL (…/chat/completions) είτε base (…/v1) και προσθέτει το path. Χωρίς περιορισμό
    :free — ο χρήστης ελέγχει το endpoint και το κόστος του.
    """
    base = (SETTINGS.get("custom_ai_base_url") or "").strip()
    if not base:
        return None
    # Δέχεται είτε πλήρες …/chat/completions είτε base …/v1 (π.χ. Ollama μέσω Cloudflare
    # tunnel: https://xxx.trycloudflare.com/v1). Προσθέτει το path αν λείπει.
    url = base if "/chat/completions" in base else base.rstrip("/") + "/chat/completions"
    model = (SETTINGS.get("custom_ai_model") or "").strip() or "gpt-3.5-turbo"
    api_key = SETTINGS.get("custom_ai_api_key") or os.getenv("CUSTOM_AI_API_KEY") or ""
    headers = {"Content-Type": "application/json"}
    if api_key:  # Ollama δεν χρειάζεται key· cloud endpoints ίσως ναι.
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    # Local LLM (qwen σε Ollama) μπορεί να αργεί στο πρώτο token -> γενναιόδωρο timeout.
    try:
        eff_timeout = max(timeout, int(SETTINGS.get("custom_ai_timeout") or 90))
    except (TypeError, ValueError):
        eff_timeout = max(timeout, 90)
    response = http_json(url, method="POST", body=payload, headers=headers, timeout=eff_timeout)
    if isinstance(response, dict) and response.get("error"):
        debug(f"custom endpoint error: {response.get('error')}")
        return None
    return _parse_ai_text(response)


def _pollinations(prompt: str, timeout: int) -> Optional[str]:
    encoded = urllib.parse.quote(prompt)
    text = http_text(POLLINATIONS_URL.format(prompt=encoded), timeout=timeout).strip()
    return text or None


def _duckduckgo(prompt: str, timeout: int) -> Optional[str]:
    if not DUCKDUCKGO_AI_URL:
        return None
    response = http_json(
        DUCKDUCKGO_AI_URL, method="POST", body={"question": prompt},
        headers={"Content-Type": "application/json"}, timeout=timeout,
    )
    return _parse_ai_text(response)


def _custom_endpoint_url() -> str:
    """Κανονικοποίηση του custom URL σε OpenAI-compatible chat/completions endpoint.

    Δέχεται είτε πλήρες endpoint (…/chat/completions), είτε base (…/v1), είτε host
    σκέτο — και συμπληρώνει ό,τι λείπει. Έτσι ο χρήστης βάζει π.χ. το cloudflare
    tunnel URL του τοπικού ollama (http://host:11434) και δουλεύει.
    """
    url = (SETTINGS.get("custom_ai_url") or "").strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return url + "/chat/completions"
    return url + "/v1/chat/completions"


def _custom(prompt: str, timeout: int) -> Optional[str]:
    """OpenAI-compatible custom endpoint (π.χ. τοπικό ollama μέσω cloudflare tunnel).

    Χρήσιμο για μελλοντικό self-hosted LLM: δηλώνεις URL + (προαιρετικά) key + model
    στις Ρυθμίσεις. Ο τοπικός server δεν χρειάζεται key — το Authorization μπαίνει
    μόνο αν οριστεί."""
    url = _custom_endpoint_url()
    if not url:
        return None
    model = SETTINGS.get("custom_ai_model") or "llama3.1"
    headers = {"Content-Type": "application/json"}
    api_key = SETTINGS.get("custom_ai_key") or os.getenv("CUSTOM_AI_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0, "stream": False}
    response = http_json(url, method="POST", body=payload, headers=headers, timeout=timeout)
    if isinstance(response, dict) and response.get("error"):
        debug(f"Custom endpoint error: {response.get('error')}")
        return None
    return _parse_ai_text(response)


def _groq(prompt: str, timeout: int) -> Optional[str]:
    """Groq: δωρεάν, γρήγορο, αξιόπιστο (llama-3.3-70b). Χρειάζεται δωρεάν API key
    από console.groq.com (χωρίς κάρτα). Είναι η πιο αξιόπιστη δωρεάν επιλογή τώρα
    που τα no-key providers (Pollinations/DuckDuckGo) χρεώνουν ή περιορίζονται."""
    api_key = SETTINGS.get("groq_api_key") or os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    model = SETTINGS.get("groq_model") or "llama-3.3-70b-versatile"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    response = http_json(GROQ_URL, method="POST", body=payload,
                         headers={"Authorization": f"Bearer {api_key}",
                                  "Content-Type": "application/json"}, timeout=timeout)
    if isinstance(response, dict) and response.get("error"):
        debug(f"Groq error: {response.get('error')}")
        return None
    return _parse_ai_text(response)


_PROVIDERS = {
    "custom": _custom,
    "openrouter": _openrouter,
    "custom": _custom,
    "pollinations": _pollinations,
    "duckduckgo": _duckduckgo,
    "groq": _groq,
}

_DEFAULT_ORDER = ["openrouter", "custom", "duckduckgo", "pollinations"]


def ai_available() -> bool:
    """True αν υπάρχει τουλάχιστον ένας provider που μπορεί να απαντήσει."""
<<<<<<< HEAD
    order = SETTINGS.get("ai_provider_order") or ["custom", "openrouter", "groq", "duckduckgo", "pollinations"]
    if "custom" in order and (SETTINGS.get("custom_ai_url") or "").strip():
        return True
=======
    order = SETTINGS.get("ai_provider_order") or _DEFAULT_ORDER
>>>>>>> b69f1c064e06f3062b3591fa58b396eb91ebe117
    if "openrouter" in order and (SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")):
        return True
    if "custom" in order and (SETTINGS.get("custom_ai_base_url") or "").strip():
        return True
    if "pollinations" in order:
        return True  # χωρίς key (αλλά ασταθές — μπορεί να επιστρέψει 402)
    return "duckduckgo" in order


def chat(prompt: str, *, timeout: int = 20, max_len: int = 600) -> Optional[str]:
    """Καλεί τους providers με τη σειρά ρυθμίσεων· επιστρέφει το πρώτο μη-κενό."""
    order = SETTINGS.get("ai_provider_order") or _DEFAULT_ORDER
    for name in order:
        fn = _PROVIDERS.get(name)
        if fn is None:
            continue
        try:
            result = fn(prompt, timeout)
            if result:
                debug(f"AI answered via {name}")
                return result[:max_len]
            debug(f"AI provider {name} returned empty")
        except (urllib.error.URLError, TimeoutError, KeyError, IndexError,
                TypeError, json.JSONDecodeError) as exc:
            debug(f"AI provider {name} failed: {exc}")
            continue
    debug("AI: όλοι οι providers απέτυχαν")
    return None


# --------------------------------------------------------- high-level tasks ----

def rewrite_to_customs_text(text: str) -> Optional[str]:
    prompt = (
        "Rewrite this commercial product text into a concise customs-style description "
        "suitable for EU TARIC classification. Focus on material composition, product "
        "use/function, and relevant classification hints. Return only the short English "
        f"description, no commentary. Product: {text}"
    )
    return chat(prompt, max_len=400)


def enrich_description(name: str, *, brand: str = "", categories: str = "",
                       quantity: str = "", web_context: str = "") -> Optional[str]:
    """Παράγει ΑΝΑΛΥΤΙΚΗ περιγραφή προϊόντος (EL) για τελωνειακή κατάταξη.

    Αξιοποιεί μάρκα + κατηγορίες + ποσότητα + (προαιρετικά) πραγματικά αποτελέσματα Google
    ώστε ένα σκέτο brand name (π.χ. «Merenda») να γίνει «κρέμα κακάο-φουντούκι για επάλειψη,
    360g» — χρήσιμο και για το matching.
    """
    context = "\n".join(p for p in (
        f"Όνομα/μάρκα: {name}" if name else "",
        f"Μάρκα: {brand}" if brand else "",
        f"Κατηγορίες: {categories}" if categories else "",
        f"Ποσότητα/μέγεθος: {quantity}" if quantity else "",
    ) if p)
    if web_context:
        context += ("\nΒοηθητικά web snippets (ΠΡΟΣΟΧΗ: μπορεί να αφορούν ΑΛΛΟ/παρόμοιο προϊόν — "
                    "χρησιμοποίησέ τα ΜΟΝΟ αν συμφωνούν με το όνομα/μάρκα παραπάνω):\n"
                    f"{web_context[:1000]}")
    prompt = (
        "Είσαι ειδικός τελωνειακής κατάταξης. Με βάση ΚΥΡΙΩΣ το όνομα/μάρκα/κατηγορίες του προϊόντος, "
        "γράψε ΜΙΑ σύντομη αλλά ουσιαστική περιγραφή στα Ελληνικά για κατάταξη TARIC. "
        "Ανάφερε: (1) τι ΑΚΡΙΒΩΣ είναι το προϊόν (γενικός τύπος, όχι μόνο η μάρκα), "
        "(2) υλικό/σύσταση, (3) χρήση, (4) μέγεθος/ποσότητα αν δίνεται.\n"
        "ΚΑΝΟΝΕΣ: ΜΗΝ εφευρίσκεις συστατικά ή στοιχεία που δεν δίνονται. Αν το όνομα είναι γνωστό "
        "προϊόν, βασίσου στο τι είναι πραγματικά. Αν τα web snippets αφορούν διαφορετικό προϊόν, "
        "ΑΓΝΟΗΣΕ τα. 1-2 προτάσεις, καθαρό κείμενο χωρίς εισαγωγικά/σχόλια/«Περιγραφή:».\n"
        + context
    )
    return chat(prompt, max_len=300)


def translate(text: str, *, target: str) -> Optional[str]:
    if not text.strip():
        return None
    label = "Greek" if target.lower().startswith("el") else "English"
    prompt = (
        f"Translate the following product text to {label}. Keep brand/product names when "
        f"appropriate. Return only the translation, no commentary. Text: {text}"
    )
    return chat(prompt, max_len=400)


def infer_product(barcode: str, web_context: str = "") -> Optional[dict[str, Any]]:
    """Ζητά από το AI να συμπεράνει μεταδεδομένα προϊόντος από web snippets."""
    if web_context:
        prompt = (
            "You are given real web search snippets for a product barcode (EAN/UPC). "
            "Identify the actual product. Return ONLY valid JSON with keys: product_name, brand, "
            "categories, description, confidence. 'description' must state the generic product TYPE, "
            "material/composition and size if present (English, concise, factual — no marketing). "
            "Base it on the snippets; do NOT invent. If the snippets are unrelated to the barcode, "
            f"use empty strings and confidence='low'.\nBarcode: {barcode}\nWeb snippets:\n{web_context}"
        )
    else:
        prompt = (
            "Infer likely product metadata for this barcode. Return ONLY valid JSON with keys: "
            "product_name, brand, categories, description, confidence. If uncertain, empty "
            f"strings and confidence='low'. Barcode: {barcode}"
        )
    raw = chat(prompt, timeout=25, max_len=800)
    return _extract_json(raw)


def confirm_product(*, barcode: str = "", candidate_name: str = "",
                    candidate_description: str = "", brand: str = "",
                    categories: str = "", web_context: str = "") -> Optional[dict[str, Any]]:
    """Διασταυρώνει barcode-DB + web αποτελέσματα και «κλειδώνει» την ταυτότητα.

    Δίνει στο AII όλο το σύνολο (υποψήφιο όνομα από βάσεις barcode + snippets από
    web αναζήτηση για το barcode ΚΑΙ για την ονομασία) και ζητά ΕΝΑ δομημένο JSON:

      name_el / name_en : σύντομη ΟΝΟΜΑΣΙΑ προϊόντος (τι είναι), όχι αναλυτική
                          περιγραφή — π.χ. «Φυσικό μεταλλικό νερό Θέρισσο».
      is_product        : true μόνο για υλικά αγαθά (υπηρεσίες -> false, χωρίς TARIC).
      customs_hint      : σύντομη αγγλική φράση υλικού/είδους για την κατάταξη TARIC
                          (εσωτερική, δεν εμφανίζεται) — π.χ. «natural mineral water,
                          bottled, non-carbonated» ώστε να μη μπερδευτεί με «toilet water».
      confidence        : 0..1 — πόσο συμφωνούν οι πηγές.

    Επιστρέφει dict ή None (αν το AI δεν είναι διαθέσιμο/απάντησε άκυρα).
    """
    if not ai_available():
        return None
    known = "\n".join(p for p in (
        f"Barcode: {barcode}" if barcode else "",
        f"Υποψήφια ονομασία (από βάσεις barcode): {candidate_name}" if candidate_name else "",
        f"Μάρκα: {brand}" if brand else "",
        f"Κατηγορίες: {categories}" if categories else "",
        f"Πρόσθετη περιγραφή πηγής: {candidate_description}" if candidate_description else "",
    ) if p)
    prompt = (
        "Είσαι βοηθός τελωνειακής ταξινόμησης. Σου δίνω ό,τι ξέρουμε για ένα προϊόν από "
        "βάσεις barcode ΚΑΙ αποτελέσματα αναζήτησης web (για το barcode και για την ονομασία). "
        "Διασταύρωσέ τα και προσδιόρισε ΤΙ ΑΚΡΙΒΩΣ είναι το προϊόν. "
        "Επίστρεψε ΜΟΝΟ έγκυρο JSON με κλειδιά: "
        "name_el (σύντομη ΟΝΟΜΑΣΙΑ στα ελληνικά, ΜΟΝΟ τι είναι το προϊόν, όχι αναλυτική περιγραφή), "
        "name_en (η ίδια σύντομη ονομασία στα αγγλικά), "
        "is_product (true αν είναι υλικό αγαθό που κατατάσσεται σε TARIC· false αν είναι υπηρεσία/άυλο), "
        "customs_hint (σύντομη ΑΓΓΛΙΚΗ φράση με το είδος/υλικό/χρήση για την κατάταξη, π.χ. "
        "'natural mineral water, bottled, still'), "
        "confidence (0..1, πόσο συμφωνούν οι πηγές). "
        "Αν οι πηγές είναι ασαφείς/αντιφατικές, βάλε χαμηλό confidence και μην εφευρίσκεις. "
        "ΜΗΝ μπερδέψεις πόσιμο/μεταλλικό νερό (τρόφιμο) με 'toilet water'/άρωμα.\n\n"
        f"{known}\n\n{web_context or '(δεν υπάρχουν web αποτελέσματα)'}"
    )
    data = _extract_json(chat(prompt, timeout=30, max_len=700))
    if not isinstance(data, dict):
        return None
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "name_el": str(data.get("name_el") or "").strip(),
        "name_en": str(data.get("name_en") or "").strip(),
        "is_product": bool(data.get("is_product", True)),
        "customs_hint": str(data.get("customs_hint") or "").strip(),
        "confidence": max(0.0, min(1.0, confidence)),
    }


def rank_taric(description: str, candidates: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Επιλογή του καλύτερου TARIC από λίστα υποψηφίων + αιτιολόγηση (rationalization).

    candidates: [{"code","description_el","description_en"}...]
    Επιστρέφει {"code","rationale","confidence"}.
    """
    if not candidates:
        return None
    lines = "\n".join(
        f"{i+1}. {c['code']} - {c.get('description_en') or c.get('description_el','')}"
        for i, c in enumerate(candidates)
    )
    prompt = (
        "You are an expert EU customs (TARIC/Combined Nomenclature) classifier. "
        "Choose the SINGLE best-matching code for the product from the candidate list below.\n"
        "Rules:\n"
        "- Classify by what the product ESSENTIALLY is (material, composition, function), not by brand.\n"
        "- Prefer the most SPECIFIC matching heading; use a generic/'other' (…90/…99) code only if "
        "no specific one fits.\n"
        "- The chosen code MUST be exactly one of the candidate codes (copy it verbatim).\n"
        "- If several fit, pick the one whose description best matches the material & use.\n"
        "Return ONLY valid JSON: {\"code\": \"<one candidate code>\", "
        "\"rationale\": \"<μία σύντομη πρόταση στα Ελληνικά>\", \"confidence\": <0..1>}.\n"
        f"Product: {description}\nCandidates:\n{lines}"
    )
    data = _extract_json(chat(prompt, timeout=25, max_len=500))
    if not data or not data.get("code"):
        return None
    valid_codes = {c["code"] for c in candidates}
    code = str(data["code"]).strip()
    if code not in valid_codes:
        # Το μοντέλο μπορεί να επέστρεψε παραλλαγή· κράτα την αν ταιριάζει σε prefix.
        match = next((vc for vc in valid_codes if vc.startswith(code) or code.startswith(vc)), None)
        if not match:
            return None
        code = match
    try:
        confidence = float(data.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6
    return {"code": code, "rationale": str(data.get("rationale", "")), "confidence": confidence}


def rationalize(description: str, code: str, taric_desc: str) -> Optional[str]:
    """Σύντομη αιτιολόγηση (στα Ελληνικά) γιατί ένα προϊόν παίρνει έναν κωδικό TARIC."""
    prompt = (
        "Γράψε μία σύντομη πρόταση στα Ελληνικά που εξηγεί γιατί το προϊόν κατατάσσεται στον "
        f"κωδικό TARIC. Προϊόν: {description}. Κωδικός: {code} ({taric_desc}). "
        "Επίστρεψε μόνο την πρόταση."
    )
    return chat(prompt, max_len=300)


def _extract_json(raw: Optional[str]) -> Optional[dict[str, Any]]:
    if not raw:
        return None
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None
