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


def _ensure_free(model: str) -> str:
    """Εγγύηση ότι χρησιμοποιείται ΜΟΝΟ δωρεάν μοντέλο OpenRouter (:free suffix)."""
    model = (model or "").strip() or "meta-llama/llama-3.3-70b-instruct:free"
    if not model.endswith(":free"):
        model = f"{model}:free"
    return model


def _openrouter(prompt: str, timeout: int) -> Optional[str]:
    api_key = SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    model = _ensure_free(SETTINGS.get("openrouter_model"))
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
    response = http_json(
        OPENROUTER_URL, method="POST", body=payload,
        headers={"Authorization": f"Bearer {api_key}",
                 "HTTP-Referer": "https://barcodetaric.local",
                 "X-Title": "BarcodeTaric"}, timeout=timeout,
    )
    # Αν το OpenRouter επιστρέψει σφάλμα (π.χ. μη-δωρεάν/rate limit), κατέγραψέ το.
    if isinstance(response, dict) and response.get("error"):
        debug(f"OpenRouter error: {response.get('error')}")
        return None
    return _parse_ai_text(response)


def list_free_models(timeout: int = 15) -> list[str]:
    """Λίστα δωρεάν μοντέλων OpenRouter (pricing prompt==0) — για επιλογή στις ρυθμίσεις."""
    try:
        data = http_json("https://openrouter.ai/api/v1/models", timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        debug(f"list_free_models failed: {exc}")
        return []
    out = []
    for m in (data.get("data") or []):
        mid = m.get("id", "")
        pricing = m.get("pricing") or {}
        if mid.endswith(":free") or (str(pricing.get("prompt", "1")) in ("0", "0.0")):
            out.append(mid)
    return sorted(set(out))


def test_providers(timeout: int = 12) -> list[tuple[str, bool, str]]:
    """Debugger: δοκιμάζει κάθε provider της αλυσίδας & επιστρέφει (name, ok, μήνυμα)."""
    order = SETTINGS.get("ai_provider_order") or ["openrouter", "groq", "duckduckgo", "pollinations"]
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
    "openrouter": _openrouter,
    "pollinations": _pollinations,
    "duckduckgo": _duckduckgo,
    "groq": _groq,
}


def ai_available() -> bool:
    """True αν υπάρχει τουλάχιστον ένας provider που μπορεί να απαντήσει."""
    order = SETTINGS.get("ai_provider_order") or ["openrouter", "groq", "duckduckgo", "pollinations"]
    if "openrouter" in order and (SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")):
        return True
    if "groq" in order and (SETTINGS.get("groq_api_key") or os.getenv("GROQ_API_KEY")):
        return True
    # Σημ.: τα no-key (pollinations/duckduckgo) συχνά χρεώνουν/περιορίζονται (402/429),
    # αλλά τα κρατάμε ως έσχατο fallback — δηλώνουμε «διαθέσιμο» αν είναι στη λίστα.
    return "pollinations" in order or "duckduckgo" in order


def chat(prompt: str, *, timeout: int = 20, max_len: int = 600) -> Optional[str]:
    """Καλεί τους providers με τη σειρά ρυθμίσεων· επιστρέφει το πρώτο μη-κενό."""
    order = SETTINGS.get("ai_provider_order") or ["openrouter", "groq", "duckduckgo", "pollinations"]
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
                       quantity: str = "") -> Optional[str]:
    """Παράγει ΑΝΑΛΥΤΙΚΗ περιγραφή προϊόντος (EL) για τελωνειακή κατάταξη.

    Αξιοποιεί μάρκα + κατηγορίες + ποσότητα ώστε ένα σκέτο brand name (π.χ. «Merenda»)
    να γίνει «προϊόν κακάο για επάλειψη με φουντούκι, 360g» — χρήσιμο και για matching.
    """
    context = "\n".join(p for p in (
        f"Όνομα/μάρκα: {name}" if name else "",
        f"Μάρκα: {brand}" if brand else "",
        f"Κατηγορίες: {categories}" if categories else "",
        f"Ποσότητα/μέγεθος: {quantity}" if quantity else "",
    ) if p)
    prompt = (
        "Δώσε μία σύντομη αλλά ΑΝΑΛΥΤΙΚΗ περιγραφή του προϊόντος στα Ελληνικά, κατάλληλη για "
        "τελωνειακή κατάταξη (TARIC): τι ακριβώς είναι, υλικό/σύσταση, χρήση, και μέγεθος/ποσότητα "
        "αν δίνεται. Μία-δύο προτάσεις, χωρίς εισαγωγικά ή σχόλια.\n" + context
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
            "You are given web search snippets for a barcode. Infer likely product metadata. "
            "Return ONLY valid JSON with keys: product_name, brand, categories, description, "
            "confidence. Description in English, concise. If uncertain, empty strings and "
            f"confidence='low'.\nBarcode: {barcode}\nWeb snippets:\n{web_context}"
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
        "You are a customs classification assistant. Given a product description and a list of "
        "candidate EU TARIC codes, pick the single best code. Return ONLY valid JSON with keys: "
        "code (exactly one of the candidate codes), rationale (one short sentence, Greek), "
        "confidence (0..1).\n"
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
