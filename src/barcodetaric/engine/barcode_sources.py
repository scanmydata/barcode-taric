"""Multi-source barcode lookup (πορτάρισμα από taric_lookup.py).

Σειρά: AI web-inference -> OpenFoodFacts -> UPCItemDB -> Barcode Monster ->
Go-UPC (scrape) -> EAN-Search (scrape) -> BarcodeLookup (scrape). Πρώτο hit κερδίζει.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.parse
from typing import Any, Callable

from . import ai
from .http_util import BROWSER_UA, debug, http_json, http_text, unescape_text
from .web_search import context_text

OPENFOODFACTS_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup?upc={barcode}"
BARCODE_MONSTER_URL = "https://barcode.monster/api/{barcode}"
BARCODELOOKUP_URL = "https://www.barcodelookup.com/{barcode}"
GOUPC_SEARCH_URL = "https://go-upc.com/search?q={barcode}"
EAN_SEARCH_URL = "https://www.ean-search.org/?q={barcode}"


# ------------------------------------------------------------ EAN-13 helpers ----

def ean13_checksum(first12: str) -> int:
    nums = [int(d) for d in first12]
    total = sum(nums[i] for i in range(0, 12, 2)) + 3 * sum(nums[i] for i in range(1, 12, 2))
    return (10 - (total % 10)) % 10


def is_valid_ean13(code: str) -> bool:
    return code.isdigit() and len(code) == 13 and ean13_checksum(code[:12]) == int(code[-1])


def normalize_to_ean13(code: str) -> str | None:
    digits = re.sub(r"\D", "", code)
    if len(digits) == 13:
        return digits
    if len(digits) == 12:
        return f"{digits}{ean13_checksum(digits)}"
    if len(digits) == 8:
        return digits.rjust(13, "0")
    return None


def looks_like_barcode(text: str) -> bool:
    digits = re.sub(r"\D", "", text)
    return len(digits) in (8, 12, 13) and len(digits) == len(text.strip())


def _extract_label_pairs(html_text: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for label, value in re.findall(
        r'<td[^>]*class=["\']metadata-label["\'][^>]*>([^<]+)</td>\s*<td>(.*?)</td>',
        html_text, re.S | re.I,
    ):
        pairs[label.strip().lower()] = unescape_text(re.sub(r"<[^>]+>", " ", value))
    return pairs


# --------------------------------------------------------------- fetchers ----

def fetch_openfoodfacts(barcode: str) -> dict[str, Any]:
    try:
        payload = http_json(OPENFOODFACTS_URL.format(barcode=urllib.parse.quote(barcode)), timeout=10)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {"source": "OpenFoodFacts", "found": False}
    if payload.get("status") != 1:
        return {"source": "OpenFoodFacts", "found": False}
    p = payload.get("product", {})
    name = p.get("product_name_el") or p.get("product_name") or p.get("generic_name")
    return {"source": "OpenFoodFacts", "found": True, "product_name": name,
            "brand": p.get("brands"),
            "categories": p.get("categories_en") or p.get("categories"),
            "description": p.get("generic_name_el") or p.get("generic_name"),
            "quantity": p.get("quantity") or ""}


def fetch_upcitemdb(barcode: str) -> dict[str, Any]:
    try:
        payload = http_json(UPCITEMDB_URL.format(barcode=urllib.parse.quote(barcode)), timeout=10)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return {"source": "UPCItemDB", "found": False}
    items = payload.get("items") or []
    if not items:
        return {"source": "UPCItemDB", "found": False}
    it = items[0]
    return {"source": "UPCItemDB", "found": True, "product_name": it.get("title"),
            "brand": it.get("brand"), "categories": it.get("category"),
            "description": it.get("description")}


def fetch_barcode_monster(barcode: str) -> dict[str, Any]:
    try:
        payload = http_json(BARCODE_MONSTER_URL.format(barcode=urllib.parse.quote(barcode)), timeout=10)
    except (urllib.error.URLError, TimeoutError, ValueError, TypeError):
        return {"source": "BarcodeMonster", "found": False}
    if not payload or not payload.get("product"):
        return {"source": "BarcodeMonster", "found": False}
    return {"source": "BarcodeMonster", "found": True, "product_name": payload.get("product"),
            "brand": payload.get("brand"), "categories": payload.get("category"),
            "description": payload.get("description")}


def fetch_go_upc(barcode: str) -> dict[str, Any]:
    try:
        html_text = http_text(GOUPC_SEARCH_URL.format(barcode=urllib.parse.quote(barcode)),
                              timeout=15, headers={"User-Agent": BROWSER_UA})
    except (urllib.error.URLError, TimeoutError):
        return {"source": "GoUPC", "found": False}
    if "no product found" in html_text.lower():
        return {"source": "GoUPC", "found": False}
    name_m = re.search(r'<h1[^>]*class=["\']product-name["\'][^>]*>(.*?)</h1>', html_text, re.S | re.I)
    desc_m = re.search(r'<h2>\s*Description\s*</h2>\s*<span>(.*?)</span>', html_text, re.S | re.I)
    pairs = _extract_label_pairs(html_text)
    name = unescape_text(re.sub(r"<[^>]+>", " ", name_m.group(1))) if name_m else None
    if not name and not pairs:
        return {"source": "GoUPC", "found": False}
    return {"source": "GoUPC", "found": True, "product_name": name, "brand": pairs.get("brand"),
            "categories": pairs.get("category"),
            "description": unescape_text(desc_m.group(1)) if desc_m else None}


def fetch_ean_search(barcode: str) -> dict[str, Any]:
    try:
        html_text = http_text(EAN_SEARCH_URL.format(barcode=urllib.parse.quote(barcode)),
                              timeout=15, headers={"User-Agent": BROWSER_UA})
    except (urllib.error.URLError, TimeoutError):
        return {"source": "EANSearch", "found": False}
    if "no results" in html_text.lower():
        return {"source": "EANSearch", "found": False}
    title_m = re.search(r'<title>(.*?)</title>', html_text, re.S | re.I)
    name = unescape_text(title_m.group(1)) if title_m else None
    if name:
        name = re.sub(r"\s*[—-]\s*EAN.*$", "", name, flags=re.I).strip() or None
    meta_m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
                       html_text, re.S | re.I)
    desc = unescape_text(meta_m.group(1)) if meta_m else None
    return {"source": "EANSearch", "found": bool(name or desc), "product_name": name,
            "brand": None, "categories": None, "description": desc}


def fetch_barcodelookup(barcode: str) -> dict[str, Any]:
    try:
        html_text = http_text(BARCODELOOKUP_URL.format(barcode=urllib.parse.quote(barcode)),
                              timeout=15, headers={"User-Agent": BROWSER_UA})
    except (urllib.error.URLError, TimeoutError):
        return {"source": "BarcodeLookup", "found": False}
    if "no product found" in html_text.lower():
        return {"source": "BarcodeLookup", "found": False}
    title_m = re.search(r'<title>(.*?)</title>', html_text, re.S | re.I)
    name = unescape_text(title_m.group(1)) if title_m else None
    if name:
        name = re.sub(r"\s*[—-]\s*Barcode Lookup$", "", name, flags=re.I).strip() or None
    pairs = _extract_label_pairs(html_text)
    desc_m = re.search(r'<h2[^>]*>\s*Description\s*</h2>\s*<div[^>]*>(.*?)</div>',
                       html_text, re.S | re.I)
    return {"source": "BarcodeLookup", "found": bool(name or pairs), "product_name": name,
            "brand": pairs.get("brand"), "categories": pairs.get("category"),
            "description": unescape_text(desc_m.group(1)) if desc_m else None}


_FETCHERS: tuple[Callable[[str], dict[str, Any]], ...] = (
    fetch_openfoodfacts, fetch_upcitemdb, fetch_barcode_monster,
    fetch_go_upc, fetch_ean_search, fetch_barcodelookup,
)


def _as_text(value: Any) -> str:
    """Coerce AI JSON τιμή σε string (το μοντέλο μπορεί να γυρίσει list -> έσκαγε το regex)."""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value if v)
    return str(value).strip() if value else ""


def ai_infer_from_web(barcode: str) -> dict[str, Any] | None:
    """Χρησιμοποιεί πραγματικά Google/DDG results + AI για να συμπεράνει το προϊόν."""
    web = context_text(barcode, limit=6)
    data = ai.infer_product(barcode, web)
    if not data:
        return None
    name = _as_text(data.get("product_name"))
    desc = _as_text(data.get("description"))
    if not name and not desc:
        return None
    return {"source": "AI/Web", "found": True, "product_name": name or desc,
            "brand": _as_text(data.get("brand")), "categories": _as_text(data.get("categories")),
            "description": desc, "confidence": data.get("confidence", "low")}


def _web_context_for(result: dict[str, Any], barcode: str) -> str:
    """Πραγματικά Google/SearXNG/DDG results για ΤΟ ΟΝΟΜΑ του προϊόντος (όχι μόνο το barcode).

    Αναζήτηση με όνομα+μάρκα δίνει πολύ καλύτερα snippets από το σκέτο barcode number,
    και τροφοδοτεί το AI enrichment ώστε η περιγραφή να είναι αναλυτική/σωστή.
    """
    name = _as_text(result.get("product_name")) or _as_text(result.get("description"))
    brand = _as_text(result.get("brand"))
    # μια ΕΙΔΙΚΗ κατηγορία ως disambiguation hint (π.χ. «Merenda» -> «Merenda hazelnut spread»),
    # παρακάμπτοντας γενικόλογες («breakfasts», «spreads») που μπερδεύουν την αναζήτηση.
    _GENERIC = {"breakfasts", "spreads", "sweet spreads", "foods", "food", "snacks", "groceries"}
    cats = _as_text(result.get("categories")).replace(">", ",")
    cat_hint = ""
    for part in cats.split(","):
        part = re.sub(r"^[a-z]{2}:", "", part.strip()).replace("-", " ").strip()
        low = part.lower()
        if part and low not in _GENERIC and low not in (name.lower(), brand.lower()):
            cat_hint = part  # κράτα την πιο ειδική (τελευταία μη-γενική)
    query = " ".join(p for p in (name, brand, cat_hint) if p).strip() or barcode
    try:
        return context_text(query, limit=6)
    except Exception as exc:  # noqa: BLE001
        debug(f"web context lookup raised: {exc}")
        return ""


def fetch_product(barcode: str, *, use_ai: bool = True) -> dict[str, Any]:
    """barcode -> στοιχεία προϊόντος. Δομημένες πηγές πρώτα, μετά Google enrichment.

    1) Δοκίμασε τις δομημένες πηγές (OpenFoodFacts/UPC/scrapers) για όνομα/μάρκα/κατηγορία.
    2) Με βάση το όνομα, τράβα πραγματικά web results (`web_context`) για επαλήθευση/εμπλουτισμό.
    3) Αν καμία πηγή δεν βρήκε προϊόν, πέσε σε AI-inference από web (πάνω στο barcode).
    """
    best: dict[str, Any] = {"source": "none", "found": False}
    for fetcher in _FETCHERS:
        try:
            result = fetcher(barcode)
            if result.get("found"):
                debug(f"Product found via {result.get('source')} for {barcode}")
                best = result
                break
        except Exception as exc:  # noqa: BLE001
            debug(f"{fetcher.__name__} raised: {exc}")

    if use_ai and ai.ai_available():
        if best.get("found"):
            best["web_context"] = _web_context_for(best, barcode)
            return best
        # καμία δομημένη πηγή -> AI συμπεραίνει από πραγματικά web results
        try:
            primary = ai_infer_from_web(barcode)
            if primary and primary.get("found"):
                return primary
        except Exception as exc:  # noqa: BLE001
            debug(f"ai_infer_from_web raised: {exc}")
    return best
