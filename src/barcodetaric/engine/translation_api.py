"""Δωρεάν διαδικτυακή μετάφραση EL<->EN ΧΩΡΙΣ LLM (γρήγορη & ντετερμινιστική).

Γιατί ξεχωριστό tier από το `ai.translate`:
  * Η κατάταξη TARIC δουλεύει καλύτερα με ΑΓΓΛΙΚΑ (η επίσημη ονοματολογία CN/HS
    είναι τυποποιημένη στα αγγλικά). Χρειαζόμαστε αξιόπιστη μετάφραση EL->EN που
    ΔΕΝ εξαρτάται από διαθέσιμο/αργό LLM.
  * Το MyMemory έχει τεράστια μεταφραστική μνήμη με έμφαση σε κείμενα ΕΕ/ΟΗΕ —
    ακριβώς το λεξιλόγιο τελωνείων/εμπορίου. Δωρεάν, χωρίς key (5000 chars/μέρα·
    50000 με email στο `mymemory_email`).

Σειρά providers (ρυθμίζεται με `translation_provider_order`):
  1. mymemory      — GET, χωρίς key, μνήμη ΕΕ/ΟΗΕ.
  2. libretranslate — POST σε instance (url/key από ρυθμίσεις, προαιρετικό).
Επιστρέφεται το πρώτο μη-κενό, αλλιώς None (ο caller πέφτει σε LLM ή κρατά το κείμενο).

Cache in-memory ανά (text, source, target) ώστε επαναλαμβανόμενες μεταφράσεις
(π.χ. ίδιο customs_hint) να μη ξανα-χτυπούν το δίκτυο.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
from typing import Optional

from ..config import SETTINGS
from .http_util import contains_greek, contains_latin, debug, http_json

MYMEMORY_URL = "https://api.mymemory.translated.net/get"

# (text_lower, source, target) -> translation. Απλό, χωρίς όριο μεγέθους: τα κείμενα
# είναι σύντομες ονομασίες/hints προϊόντων.
_CACHE: dict[tuple[str, str, str], str] = {}


def _lang(text: str) -> str:
    """Πρόχειρη ανίχνευση γλώσσας: 'el' αν έχει ελληνικά, 'en' αν λατινικά, αλλιώς ''."""
    if contains_greek(text):
        return "el"
    if contains_latin(text):
        return "en"
    return ""


def _mymemory(text: str, source: str, target: str, timeout: int) -> Optional[str]:
    # Το MyMemory δέχεται max 500 bytes ανά q. Οι ονομασίες προϊόντων είναι σύντομες·
    # κόβουμε με ασφάλεια στα 480 bytes ώστε να μη σκάσει το request.
    q = text.encode("utf-8")[:480].decode("utf-8", errors="ignore")
    params = {"q": q, "langpair": f"{source}|{target}"}
    email = SETTINGS.get("mymemory_email")
    if email:
        params["de"] = email       # ανεβάζει το όριο σε 50000 chars/μέρα
    url = MYMEMORY_URL + "?" + urllib.parse.urlencode(params)
    try:
        payload = http_json(url, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        debug(f"MyMemory failed: {exc}")
        return None
    if not isinstance(payload, dict):
        return None
    # Το MyMemory επιστρέφει 200 ακόμη κι όταν εξαντληθεί το όριο· έλεγξε το status.
    status = payload.get("responseStatus")
    if status not in (200, "200", None):
        debug(f"MyMemory responseStatus={status}: {payload.get('responseDetails')}")
        return None
    data = payload.get("responseData") or {}
    translated = str(data.get("translatedText") or "").strip()
    if not translated:
        return None
    # Απόρριψε τα «σκουπίδια» που επιστρέφει όταν δεν έχει match.
    low = translated.lower()
    if "no query specified" in low or "invalid" in low or "please select" in low:
        return None
    return translated


# --- Argos Translate: OFFLINE νευρωνική μετάφραση (OPUS-MT) — διατηρεί το ΝΟΗΜΑ πολύ
# καλύτερα από το lookup του MyMemory. Optional extra ([translate]): lazy import, το
# μοντέλο el<->en κατεβαίνει ΜΙΑ φορά, μετά δουλεύει τελείως offline. ---
_ARGOS_FAILED = False
_ARGOS_INSTALLED: set[tuple[str, str]] = set()


def _argos_available() -> bool:
    global _ARGOS_FAILED
    if _ARGOS_FAILED or SETTINGS.get("argos_enabled") is False:
        return False
    try:
        import argostranslate.translate  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        _ARGOS_FAILED = True
        return False


def _ensure_argos_pair(from_code: str, to_code: str) -> bool:
    """Εγκαθιστά (μία φορά) το πακέτο γλώσσας from->to αν λείπει. Λήψη ~100MB την 1η φορά."""
    if (from_code, to_code) in _ARGOS_INSTALLED:
        return True
    try:
        import argostranslate.package as pkg
        import argostranslate.translate as tr
        installed = {(l.code) for l in tr.get_installed_languages()}
        # Αν και οι δύο γλώσσες υπάρχουν ήδη, θεώρησέ το εντάξει.
        if from_code in installed and to_code in installed:
            _ARGOS_INSTALLED.add((from_code, to_code))
            return True
        pkg.update_package_index()
        avail = pkg.get_available_packages()
        match = next((p for p in avail if p.from_code == from_code and p.to_code == to_code), None)
        if match is None:
            return False
        pkg.install_from_path(match.download())
        _ARGOS_INSTALLED.add((from_code, to_code))
        return True
    except Exception as exc:  # noqa: BLE001
        debug(f"Argos install {from_code}->{to_code} failed: {exc}")
        return False


def _argos(text: str, source: str, target: str, timeout: int) -> Optional[str]:
    if not _argos_available():
        return None
    if not _ensure_argos_pair(source, target):
        return None
    try:
        import argostranslate.translate as tr
        out = tr.translate(text, source, target)
        return out.strip() or None if isinstance(out, str) else None
    except Exception as exc:  # noqa: BLE001
        debug(f"Argos translate failed: {exc}")
        return None


def _libretranslate(text: str, source: str, target: str, timeout: int) -> Optional[str]:
    base = (SETTINGS.get("libretranslate_url") or "").strip().rstrip("/")
    if not base:
        return None
    body = {"q": text, "source": source, "target": target, "format": "text"}
    key = SETTINGS.get("libretranslate_api_key")
    if key:
        body["api_key"] = key
    try:
        payload = http_json(base + "/translate", method="POST", body=body, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        debug(f"LibreTranslate failed: {exc}")
        return None
    if isinstance(payload, dict):
        out = str(payload.get("translatedText") or "").strip()
        return out or None
    return None


_PROVIDERS = {
    "argos": _argos,
    "mymemory": _mymemory,
    "libretranslate": _libretranslate,
}

# Argos ΠΡΩΤΟ (offline, διατηρεί νόημα) αν είναι εγκατεστημένο· αλλιώς παρακάμπτεται σιωπηλά.
_DEFAULT_ORDER = ["argos", "mymemory", "libretranslate"]


def available() -> bool:
    """True αν υπάρχει έστω ένας provider που μπορεί να μεταφράσει χωρίς LLM."""
    order = SETTINGS.get("translation_provider_order") or _DEFAULT_ORDER
    if "argos" in order and _argos_available():
        return True
    if "mymemory" in order:
        return True                       # χωρίς key
    if "libretranslate" in order and SETTINGS.get("libretranslate_url"):
        return True
    return False


def translate(text: str, *, source: str = "auto", target: str = "en",
              timeout: int = 8) -> Optional[str]:
    """Μεταφράζει `text` σε `target` (ISO 639-1). Επιστρέφει None αν όλα απέτυχαν.

    `source='auto'` -> ανίχνευση από το κείμενο. Αν source==target ή δεν χρειάζεται
    μετάφραση, επιστρέφει το κείμενο ως έχει.
    """
    text = (text or "").strip()
    if not text:
        return None
    src = source if source != "auto" else _lang(text)
    if not src:
        return text                       # π.χ. μόνο αριθμοί — τίποτα να μεταφραστεί
    if src == target:
        return text

    key = (text.lower(), src, target)
    if key in _CACHE:
        return _CACHE[key]

    order = SETTINGS.get("translation_provider_order") or _DEFAULT_ORDER
    for name in order:
        fn = _PROVIDERS.get(name)
        if fn is None:
            continue
        result = fn(text, src, target, timeout)
        if result:
            debug(f"translation via {name}: {src}->{target}")
            _CACHE[key] = result
            return result
    return None


def to_english(text: str, *, timeout: int = 8) -> Optional[str]:
    """Βοηθός: φέρνει οτιδήποτε στα Αγγλικά (βασική γλώσσα κατάταξης)."""
    return translate(text, source="auto", target="en", timeout=timeout)


def to_greek(text: str, *, timeout: int = 8) -> Optional[str]:
    return translate(text, source="auto", target="el", timeout=timeout)


def to_english_offline(text: str) -> Optional[str]:
    """EL->EN ΜΟΝΟ offline (Argos) — για μαζική αντιστοίχιση ΧΩΡΙΣ δικτυακή κλήση/κρέμασμα.

    Επιστρέφει None αν το Argos δεν είναι εγκατεστημένο (ο caller κρατά το ελληνικό κείμενο).
    """
    text = (text or "").strip()
    if not text or not _argos_available():
        return None
    src = _lang(text)
    if src == "en":
        return text
    if src != "el":
        return None
    key = (text.lower(), "el", "en")
    if key in _CACHE:
        return _CACHE[key]
    out = _argos(text, "el", "en", 8)
    if out:
        _CACHE[key] = out
    return out
