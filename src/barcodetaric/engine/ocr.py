"""OCR ετικέτας προϊόντος από φωτογραφία (δωρεάν, key-gated).

Σκοπός: όταν οι δομημένες πηγές barcode ΔΕΝ δίνουν αξιόπιστη ονομασία αλλά υπάρχει
εικόνα του προϊόντος (π.χ. από OpenFoodFacts), διαβάζουμε το κείμενο της ετικέτας
με OCR και το τροφοδοτούμε στην αναγνώριση/κατάταξη — «τι είναι το προϊόν» από την
εικόνα, όπως ζητήθηκε.

Provider: ocr.space (δωρεάν tier με key από ocr.space/ocrapi — χωρίς κάρτα).
Υποστηρίζει ελληνικά (`gre`) & αγγλικά (`eng`). Χωρίς key -> σιωπηλά ανενεργό
(graceful degradation, όπως όλες οι εξωτερικές εξαρτήσεις του app).

Το interface είναι σκόπιμα απλό ώστε να μπει μελλοντικά τοπικός OCR (Tesseract)
ή Google Vision χωρίς αλλαγές στους callers.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
from typing import Optional

from ..config import SETTINGS
from .http_util import debug, http_json

OCRSPACE_URL = "https://api.ocr.space/parse/imageurl"

# url -> εξαγόμενο κείμενο (cache· τα ίδια product images ξαναζητούνται συχνά).
_CACHE: dict[str, str] = {}


def available() -> bool:
    """True αν έχει ρυθμιστεί OCR provider (key)."""
    return bool(SETTINGS.get("ocrspace_api_key"))


def ocr_image_url(image_url: str, *, timeout: int = 25, language: str = "eng") -> Optional[str]:
    """Τρέχει OCR σε εικόνα (URL) και επιστρέφει το κείμενο, ή None.

    `language`: 'eng' (default) ή 'gre'. Η ocr.space δέχεται μία γλώσσα ανά κλήση —
    για ετικέτες με ανάμεικτο κείμενο, το 'eng' πιάνει και τα λατινικά ονόματα μαρκών.
    """
    image_url = (image_url or "").strip()
    if not image_url:
        return None
    if image_url in _CACHE:
        return _CACHE[image_url] or None

    api_key = SETTINGS.get("ocrspace_api_key")
    if not api_key:
        return None

    url = OCRSPACE_URL + "?" + urllib.parse.urlencode({
        "apikey": api_key, "url": image_url, "language": language,
        "isOverlayRequired": "false", "scale": "true", "OCREngine": "2",
    })
    try:
        payload = http_json(url, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        debug(f"ocr.space failed: {exc}")
        return None
    if not isinstance(payload, dict) or payload.get("IsErroredOnProcessing"):
        debug(f"ocr.space error: {payload.get('ErrorMessage') if isinstance(payload, dict) else 'bad payload'}")
        return None
    parsed = payload.get("ParsedResults") or []
    text = " ".join(
        str(pr.get("ParsedText") or "").strip()
        for pr in parsed if isinstance(pr, dict)
    ).strip()
    # Κανονικοποίηση whitespace (τα OCR κείμενα έχουν πολλά newlines).
    text = " ".join(text.split())
    _CACHE[image_url] = text
    return text or None
