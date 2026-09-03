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


# Μοντέλα ΑΚΑΤΑΛΛΗΛΑ για τελωνειακή ταξινόμηση/JSON (κώδικας/όραση/μαθηματικά/ασφάλεια):
# απαντούν μεν, αλλά είναι αργά/κακά στο task — αιτία «κολλάει η αντιστοίχιση».
_UNSUITABLE_MARKERS = ("code", "coder", "-vl", "vision", "-math", "guard", "rerank",
                       "embed", "moderation", "distill")


def _is_suitable_model(model: str) -> bool:
    low = (model or "").lower()
    return not any(m in low for m in _UNSUITABLE_MARKERS)


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


# Cache της λίστας δωρεάν μοντέλων: το free landscape του OpenRouter αλλάζει συχνά, οπότε
# θέλουμε ΣΥΧΝΟ refresh — αλλά όχι HTTP κλήση σε κάθε άνοιγμα των Ρυθμίσεων. TTL από settings.
_FREE_CACHE: dict[str, Any] = {"ts": 0.0, "models": []}


def list_free_models(timeout: int = 15, *, force: bool = False) -> list[str]:
    """Δωρεάν chat μοντέλα OpenRouter (pricing prompt==0), φιλτραρισμένα & ταξινομημένα.

    Αποκλείει audio/image/embedding/moderation μοντέλα και βάζει τις καλές instruct
    οικογένειες πρώτες (βλ. `_rank_free`) ώστε η «έξυπνη» επιλογή να πετύχει γρήγορα.
    Cached με TTL (`free_models_ttl_sec`, default 6h)· `force=True` παρακάμπτει το cache.
    """
    import time as _time
    try:
        ttl = int(SETTINGS.get("free_models_ttl_sec") or 21600)
    except (TypeError, ValueError):
        ttl = 21600
    if not force and _FREE_CACHE["models"] and (_time.time() - _FREE_CACHE["ts"]) < ttl:
        return list(_FREE_CACHE["models"])
    try:
        data = http_json("https://openrouter.ai/api/v1/models", timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        debug(f"list_free_models failed: {exc}")
        return list(_FREE_CACHE["models"])  # σερβίρισε το τελευταίο γνωστό αν υπάρχει
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
    ranked = _rank_free(list(set(out)))
    if ranked:
        _FREE_CACHE["models"] = ranked
        _FREE_CACHE["ts"] = _time.time()
    return ranked


def best_free_model(timeout: int = 12, tries: int = 4) -> Optional[str]:
    """«Έξυπνη» επιλογή: δοκιμάζει τα κορυφαία δωρεάν μοντέλα & επιστρέφει το 1ο που απαντά.

    Χρήσιμο όταν το αποθηκευμένο μοντέλο αποσύρθηκε (404). Αποθηκεύει το εύρημα σε
    `_WORKING_MODEL` για αυτόματο fallback μέσα στη session.
    """
    global _WORKING_MODEL
    api_key = SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    suitable = [m for m in list_free_models(timeout=timeout) if _is_suitable_model(m)]
    candidates = suitable[:tries] or [DEFAULT_FREE_MODEL, "openrouter/free"]
    for mid in candidates:
        try:
            if _openrouter_call(mid, "Reply with the single word OK.", timeout):
                _WORKING_MODEL = mid
                debug(f"best_free_model picked: {mid}")
                return mid
        except Exception as exc:  # noqa: BLE001
            debug(f"best_free_model: {mid} failed: {exc}")
    return None


def auto_configure(progress=None) -> dict:
    """Αυτόματη επιλογή του ΚΑΛΥΤΕΡΟΥ διαθέσιμου AI provider (κλήση σε background worker).

    Προτεραιότητα:
      1) **Τοπικό LLM** (custom endpoint) αν έχει οριστεί & απαντά -> μπαίνει ΠΡΩΤΟ στη σειρά.
      2) **OpenRouter**: αν το αποθηκευμένο μοντέλο δεν απαντά (π.χ. code-model/αποσυρμένο),
         ανανεώνει τη λίστα δωρεάν μοντέλων & διαλέγει το 1ο που όντως δουλεύει.
      3) Αλλιώς αφήνει τη σειρά ως έχει (groq/duckduckgo/pollinations).

    Λύνει το «κολλάει η αντιστοίχιση»: κακό/αργό αποθηκευμένο μοντέλο -> auto-αντικατάσταση.
    Επιστρέφει {"provider","model","message"}.
    """
    def _say(m):
        if progress:
            progress(m)

    # 1) Τοπικό LLM πρώτο (ό,τι ζήτησε ο χρήστης: αν βρεθεί local config, προτίμησέ το).
    if (SETTINGS.get("custom_ai_base_url") or "").strip():
        _say("Έλεγχος τοπικού LLM…")
        order = list(SETTINGS.get("ai_provider_order") or _DEFAULT_ORDER)
        if order[:1] != ["custom"]:
            SETTINGS.set("ai_provider_order", ["custom"] + [p for p in order if p != "custom"])
            SETTINGS.save()
        try:
            if _custom("Reply with the single word OK.", 20):
                return {"provider": "custom", "model": SETTINGS.get("custom_ai_model") or "",
                        "message": "Χρήση τοπικού LLM (custom endpoint)."}
        except Exception as exc:  # noqa: BLE001
            debug(f"auto_configure custom failed: {exc}")

    # 2) Groq: ΔΩΡΕΑΝ & ΠΟΛΥ ΓΡΗΓΟΡΟ (llama-3.3-70b, ~1-2s/κλήση) — για μαζική αντιστοίχιση
    # είναι πολύ καλύτερο από τα αργά/ουρωμένα free μοντέλα του OpenRouter. Αν υπάρχει key,
    # ανέβασέ το ΠΡΩΤΟ στη σειρά.
    if SETTINGS.get("groq_api_key") or os.getenv("GROQ_API_KEY"):
        _say("Έλεγχος Groq (γρήγορο δωρεάν)…")
        try:
            if _groq("Reply with the single word OK.", 12):
                order = list(SETTINGS.get("ai_provider_order") or _DEFAULT_ORDER)
                if "groq" in order and order[:2] != ["custom", "groq"] and order[:1] != ["groq"]:
                    order = ["groq"] + [p for p in order if p != "groq"]
                    SETTINGS.set("ai_provider_order", order)
                    SETTINGS.save()
                return {"provider": "groq", "model": SETTINGS.get("groq_model") or "llama-3.3-70b",
                        "message": "Χρήση Groq (γρήγορο δωρεάν) για την αντιστοίχιση."}
        except Exception as exc:  # noqa: BLE001
            debug(f"auto_configure groq failed: {exc}")

    # 3) OpenRouter: εγγύηση ΚΑΛΟΥ & ΔΟΥΛΕΥΟΝΤΟΣ δωρεάν μοντέλου.
    if SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY"):
        global _WORKING_MODEL
        current = _ensure_free(SETTINGS.get("openrouter_model"))
        _say(f"Έλεγχος μοντέλου OpenRouter ({current})…")
        ok = False
        try:
            ok = bool(_openrouter_call(current, "Reply with the single word OK.", 12))
        except Exception:  # noqa: BLE001
            ok = False
        # Κράτα το αποθηκευμένο ΜΟΝΟ αν δουλεύει ΚΑΙ είναι κατάλληλο (instruct, όχι code/
        # specialized). Ένα code-model απαντά μεν, αλλά είναι αργό & κακό σε ταξινόμηση/JSON
        # (η αιτία του «κολλάει η αντιστοίχιση») -> προτίμησε καλύτερο general μοντέλο.
        if ok and _is_suitable_model(current):
            _WORKING_MODEL = current
            return {"provider": "openrouter", "model": current,
                    "message": f"Ενεργό μοντέλο OpenRouter: {current}"}
        reason = ("δεν απαντά" if not ok else "ακατάλληλο για ταξινόμηση (code/specialized)")
        _say(f"Το αποθηκευμένο μοντέλο {reason} — αναζήτηση καλύτερου δωρεάν…")
        picked = best_free_model()
        if picked:
            SETTINGS.set("openrouter_model", picked)
            SETTINGS.save()
            return {"provider": "openrouter", "model": picked,
                    "message": f"Επιλέχθηκε αυτόματα δωρεάν μοντέλο: {picked}"}
        if ok:   # δεν βρέθηκε καλύτερο -> κράτα το αποθηκευμένο που τουλάχιστον απαντά
            _WORKING_MODEL = current
            return {"provider": "openrouter", "model": current,
                    "message": f"Ενεργό μοντέλο OpenRouter: {current}"}

    # 3) fallback
    if SETTINGS.get("groq_api_key") or os.getenv("GROQ_API_KEY"):
        return {"provider": "groq", "model": SETTINGS.get("groq_model") or "",
                "message": "Χρήση Groq."}
    return {"provider": None, "model": "", "message": "Κανένας AI provider δεν ρυθμίστηκε."}


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


def _custom_endpoint_url() -> str:
    """Κανονικοποίηση του custom endpoint σε OpenAI-compatible /chat/completions.

    Δέχεται πλήρες endpoint (…/chat/completions), base (…/v1), ή σκέτο host — και
    συμπληρώνει ό,τι λείπει (π.χ. cloudflare tunnel του ollama: https://host -> +/v1/…).
    """
    url = (SETTINGS.get("custom_ai_base_url") or "").strip().rstrip("/")
    if not url:
        return ""
    if url.endswith("/chat/completions"):
        return url
    if url.endswith("/v1"):
        return url + "/chat/completions"
    return url + "/v1/chat/completions"


def _custom(prompt: str, timeout: int) -> Optional[str]:
    """Custom OpenAI-συμβατό endpoint (π.χ. τοπικό ollama μέσω Cloudflare tunnel).

    Ενεργοποιείται μόνο αν έχει οριστεί `custom_ai_base_url`. Χωρίς περιορισμό :free —
    ο χρήστης ελέγχει το endpoint. Ο τοπικός server δεν χρειάζεται key.
    """
    url = _custom_endpoint_url()
    if not url:
        return None
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
    "groq": _groq,
    "pollinations": _pollinations,
    "duckduckgo": _duckduckgo,
}

_DEFAULT_ORDER = ["custom", "openrouter", "groq", "duckduckgo", "pollinations"]


def ai_available() -> bool:
    """True αν υπάρχει τουλάχιστον ένας provider που μπορεί να απαντήσει."""
    order = SETTINGS.get("ai_provider_order") or _DEFAULT_ORDER
    if "custom" in order and (SETTINGS.get("custom_ai_base_url") or "").strip():
        return True
    if "openrouter" in order and (SETTINGS.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")):
        return True
    if "groq" in order and (SETTINGS.get("groq_api_key") or os.getenv("GROQ_API_KEY")):
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
        "You are an EU customs (TARIC/CN) classification assistant. Below is everything known about a "
        "product from barcode databases AND web search results (for the barcode and for the name). "
        "Cross-check them and determine WHAT THE PRODUCT EXACTLY IS, then produce a structured "
        "customs analysis. Reply with ONLY valid JSON (no markdown, no commentary) with these keys:\n"
        '  "name_el":   short PRODUCT NAME in Greek (only what it is, not a long description),\n'
        '  "name_en":   the same short name in English,\n'
        '  "is_product": true if it is a physical good classifiable under TARIC; false if a service/intangible,\n'
        '  "customs_hint": ONE short English phrase of kind/material/use for classification '
        "(e.g. 'natural mineral water, bottled, still'),\n"
        '  "analysis":  a concise ENGLISH structured analysis for tariff classification & ML, covering '
        "(when knowable): material/composition, product type, physical form/state, processing, "
        "intended use, and the likely HS chapter. 1-3 short clauses, factual, e.g. "
        "'Dairy product; cow milk, pasteurized, whole ~3.5% fat; liquid, retail 1L; food, HS chapter 04.',\n"
        '  "confidence": 0..1 (how well the sources agree).\n'
        "Rules: do NOT invent facts not supported by the sources; if unclear, keep it generic and lower "
        "confidence. Classify by what it ESSENTIALLY is, not by brand. Do NOT confuse drinking/mineral "
        "water (food, ch.22) with 'toilet water'/perfume (ch.33).\n\n"
        f"{known}\n\n{web_context or '(no web results)'}"
    )
    data = _extract_json(chat(prompt, timeout=30, max_len=900))
    if not isinstance(data, dict):
        return None
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    analysis = data.get("analysis")
    if isinstance(analysis, (list, tuple)):   # μερικά μοντέλα γυρνούν array
        analysis = "; ".join(str(a) for a in analysis if a)
    return {
        "name_el": str(data.get("name_el") or "").strip(),
        "name_en": str(data.get("name_en") or "").strip(),
        "is_product": bool(data.get("is_product", True)),
        "customs_hint": str(data.get("customs_hint") or "").strip(),
        "analysis": str(analysis or "").strip(),
        "confidence": max(0.0, min(1.0, confidence)),
    }


def rank_taric(description: str, candidates: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Επιλογή του καλύτερου TARIC από λίστα υποψηφίων + αιτιολόγηση (rationalization).

    candidates: [{"code","description_el","description_en"}...]
    Επιστρέφει {"code","rationale","confidence"}.
    """
    if not candidates:
        return None
    # Ομαδοποίηση ανά κεφάλαιο HS (2 πρώτα ψηφία) ώστε το μοντέλο να «βλέπει» το σωστό context.
    lines = "\n".join(
        f"{i+1}. [{c['code'][:2]}] {c['code']} - {c.get('description_en') or c.get('description_el','')}"
        for i, c in enumerate(candidates)
    )
    prompt = (
        "You are an expert EU customs (TARIC/Combined Nomenclature) classifier. "
        "Choose the SINGLE best-matching code for the product from the candidate list below.\n"
        "Method (think step by step, briefly):\n"
        "1) Identify what the product ESSENTIALLY is — material, composition, function — NOT the brand.\n"
        "2) Pick the correct HS CHAPTER first (the [NN] prefix): e.g. dairy milk=04, coffee=09, "
        "chocolate/cocoa=18, waters/beverages=22, cosmetics/perfume=33, chemicals=28/29. "
        "REJECT candidates from an unrelated chapter even if words overlap "
        "(e.g. a food is NOT a chemical/pesticide just because a brand name resembles one).\n"
        "3) Within that chapter pick the MOST SPECIFIC heading; use a generic/'other' (…90/…99) "
        "code only if nothing more specific fits.\n"
        "Constraints: the chosen code MUST be exactly one of the candidate codes (copy verbatim). "
        "If NONE of the candidates fit the correct chapter, pick the closest and set confidence<=0.3.\n"
        "Return ONLY valid JSON: {\"reason\": \"<short English chain: what it is + chapter>\", "
        "\"code\": \"<one candidate code>\", "
        "\"rationale\": \"<μία σύντομη πρόταση στα Ελληνικά>\", \"confidence\": <0..1>}.\n"
        f"Product: {description}\nCandidates:\n{lines}"
    )
    data = _extract_json(chat(prompt, timeout=25, max_len=600))
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


def rank_taric_batch(products: list[dict[str, Any]], batch_size: int = 20
                     ) -> list[Optional[dict[str, Any]]]:
    """Batch κατάταξη: πολλά προϊόντα ΑΝΑ κλήση AI (κλιμάκωση σε 4k-10k κωδικούς).

    products: [{"query": str, "candidates": [{"code","description_el","description_en"}...]}...]
    Επιστρέφει λίστα ΙΔΙΟΥ μήκους: {"code","rationale","confidence"} ή None ανά προϊόν.

    Το AI διαβάζει ελληνικά απευθείας (χωρίς per-item δικτυακή μετάφραση). Αν το batch JSON
    δεν διαβαστεί (μικρά free models), γίνεται fallback σε per-item `rank_taric` για ΤΟ batch.
    """
    results: list[Optional[dict[str, Any]]] = [None] * len(products)
    if not products or not ai_available():
        return results
    for start in range(0, len(products), batch_size):
        chunk = products[start:start + batch_size]
        parsed = _rank_batch_chunk(chunk)
        if parsed is None:
            # fallback: per-item (αργό αλλά ασφαλές) για ΑΥΤΟ το batch μόνο
            for j, p in enumerate(chunk):
                results[start + j] = rank_taric(p.get("query", ""), p.get("candidates", []))
            continue
        for j, res in enumerate(parsed):
            results[start + j] = res
    return results


def _rank_batch_chunk(chunk: list[dict[str, Any]]) -> Optional[list[Optional[dict[str, Any]]]]:
    """Μία κλήση AI για ≤batch_size προϊόντα. None => αποτυχία parse (κάνε fallback)."""
    # ΒΕΛΤΙΣΤΟΠΟΙΗΣΗ PROMPT: οι υποψήφιοι ΕΠΑΝΑΛΑΜΒΑΝΟΝΤΑΙ έντονα μεταξύ προϊόντων (τα ίδια
    # headings). Αντί να στέλνουμε την περιγραφή κάθε κωδικού N φορές, στέλνουμε ΜΙΑ ΦΟΡΑ ένα
    # κοινό «κωδικολόγιο» (το σχετικό slice της ονοματολογίας) και μετά κάθε προϊόν αναφέρει
    # ΜΟΝΟ τους επιτρεπτούς κωδικούς του. Μεγάλη μείωση tokens -> μεγαλύτερα batches/λιγότερες κλήσεις.
    codebook: dict[str, str] = {}
    for p in chunk:
        for c in p.get("candidates", []):
            code = c.get("code", "")
            if code and code not in codebook:
                codebook[code] = (c.get("description_en") or c.get("description_el") or "").strip()
    book = "\n".join(f"{code} = {desc}" for code, desc in codebook.items())

    shared_blocks, inline_blocks = [], []
    for i, p in enumerate(chunk):
        cands = p.get("candidates", [])
        allowed = ", ".join(c["code"] for c in cands if c.get("code"))
        shared_blocks.append(f"[{i}] {p.get('query','')}\n     allowed: {allowed}")
        lines = "\n".join(
            f"     {c['code']} = {c.get('description_en') or c.get('description_el','')}"
            for c in cands)
        inline_blocks.append(f"[{i}] {p.get('query','')}\n{lines}")

    shared = ("=== CODEBOOK (TARIC code = official description) ===\n" + book +
              "\n\n=== PRODUCTS (index, description, allowed codes) ===\n" +
              "\n".join(shared_blocks))
    inline = "=== PRODUCTS (index, description, candidate codes) ===\n" + "\n".join(inline_blocks)
    # Το κοινό codebook κερδίζει ΜΟΝΟ όταν οι υποψήφιοι επαναλαμβάνονται αρκετά μεταξύ
    # προϊόντων (συνηθισμένο σε μαζικό import ομοειδών ειδών). Σε ανομοιογενή batches το
    # inline είναι μικρότερο — διάλεξε αυτόματα το φθηνότερο σε tokens.
    body = shared if len(shared) <= len(inline) else inline

    prompt = (
        "You are an expert EU customs (TARIC/Combined Nomenclature) classifier.\n\n"
        f"{body}\n\n"
        "For EACH product choose the SINGLE best code from ITS OWN candidate/allowed list.\n"
        "Rules: identify what the product ESSENTIALLY is (material/composition/function, NOT the "
        "brand); pick the correct HS chapter first (dairy=04, coffee=09, cocoa/chocolate=18, "
        "waters/beverages=22, cosmetics=33…), rejecting candidates from an unrelated chapter even "
        "if words overlap; then the most specific heading (use generic '…90/…99' only if nothing "
        "specific fits). Product descriptions may be in Greek — classify them directly. "
        "The chosen code MUST appear verbatim in that product's allowed list.\n"
        "Return ONLY a valid JSON array, one object per product, same order, no commentary:\n"
        "[{\"i\": <index>, \"code\": \"<allowed code>\", "
        "\"confidence\": <0..1>, \"rationale\": \"<μία σύντομη ελληνική πρόταση>\"}]"
    )
    # Μεγαλύτερα batches (slow free tiers) -> γενναιόδωρο timeout & output limit.
    raw = chat(prompt, timeout=120, max_len=6000)
    arr = _extract_json_array(raw)
    if arr is None:
        return None
    by_i = {}
    for obj in arr:
        if isinstance(obj, dict) and "i" in obj:
            try:
                by_i[int(obj["i"])] = obj
            except (TypeError, ValueError):
                continue
    out: list[Optional[dict[str, Any]]] = []
    for i, p in enumerate(chunk):
        obj = by_i.get(i)
        out.append(_validate_choice(obj, p.get("candidates", [])) if obj else None)
    # Αν το μοντέλο δεν επέστρεψε ΚΑΝΕΝΑ έγκυρο, θεώρησέ το αποτυχία -> fallback.
    return out if any(o for o in out) else None


def _validate_choice(obj: dict[str, Any], candidates: list[dict[str, Any]]
                     ) -> Optional[dict[str, Any]]:
    code = str(obj.get("code", "")).strip()
    if not code:
        return None
    valid = {c["code"] for c in candidates}
    if code not in valid:
        match = next((vc for vc in valid if vc.startswith(code) or code.startswith(vc)), None)
        if not match:
            return None
        code = match
    try:
        confidence = float(obj.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6
    return {"code": code, "rationale": str(obj.get("rationale", "")), "confidence": confidence}


def _extract_json_array(raw: Optional[str]) -> Optional[list]:
    if not raw:
        return None
    match = re.search(r"\[.*\]", raw, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        return None


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
