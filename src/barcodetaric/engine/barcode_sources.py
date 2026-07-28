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


def ean8_checksum(first7: str) -> int:
    nums = [int(d) for d in first7]
    total = 3 * sum(nums[0::2]) + sum(nums[1::2])
    return (10 - (total % 10)) % 10


def is_valid_ean8(code: str) -> bool:
    return code.isdigit() and len(code) == 8 and ean8_checksum(code[:7]) == int(code[-1])


def normalize_to_ean13(code: str) -> str | None:
    """Κανονική μορφή για αποθήκευση/dedup.

    ΠΡΟΣΟΧΗ: ένα EAN-8 (π.χ. 64320458) ΔΕΝ γεμίζει με μηδενικά — το GTIN-8 είναι
    διαφορετικός κωδικός από ένα zero-padded GTIN-13, και οι βάσεις barcode το
    ευρετηριάζουν με τα 8 ψηφία. Το κρατάμε ως έχει, αλλιώς τα lookups αστοχούν.
    """
    digits = re.sub(r"\D", "", code)
    if len(digits) == 13:
        return digits
    if len(digits) == 12:
        return f"{digits}{ean13_checksum(digits)}"
    if len(digits) == 8:
        return digits
    return None


def barcode_variants(code: str) -> list[str]:
    """Μορφές του κωδικού που αξίζει να δοκιμαστούν στις πηγές (raw + κανονική)."""
    digits = re.sub(r"\D", "", code)
    variants: list[str] = []
    for v in (digits, normalize_to_ean13(code)):
        if v and v not in variants:
            variants.append(v)
    return variants


def looks_like_barcode(text: str) -> bool:
    digits = re.sub(r"\D", "", text)
    return len(digits) in (8, 12, 13) and len(digits) == len(text.strip())


# Ονόματα που δεν είναι προϊόντα αλλά τίτλοι/σελίδες των ίδιων των sites αναζήτησης
# barcode. Οι scrapers τα επέστρεφαν κατά λάθος ως «προϊόν» όταν δεν υπήρχε match.
_JUNK_NAME_PATTERNS = (
    "ean-search", "ean search", "barcode lookup", "barcodelookup", "upcitemdb",
    "go-upc", "go upc", "isbn lookup", "gtin", "lookup and api", "search our",
    "billion products", "no product", "not found", "database with over",
    "buy a barcode", "buyabarcode", "upc lookup", "product search",
)


def _is_junk_name(name: str | None) -> bool:
    """True αν το «όνομα» είναι τίτλος site/σελίδας «δεν βρέθηκε», όχι προϊόν."""
    if not name or len(name.strip()) < 2:
        return True
    low = name.lower()
    return any(p in low for p in _JUNK_NAME_PATTERNS)


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
            "quantity": p.get("quantity") or "",
            "image_url": p.get("image_front_url") or p.get("image_url") or ""}


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
    if _is_junk_name(name):
        name = None
    if not name and not pairs:
        return {"source": "GoUPC", "found": False}
    return {"source": "GoUPC", "found": bool(name or pairs), "product_name": name, "brand": pairs.get("brand"),
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
    # Αν το «όνομα» είναι ο τίτλος της ίδιας της σελίδας EAN-Search (χωρίς
    # πραγματικό match), μη το περάσεις ως προϊόν.
    if _is_junk_name(name):
        name = None
    if _is_junk_name(desc):
        desc = None
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
    if _is_junk_name(name):
        name = None
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


def ai_infer_from_web(barcode: str) -> dict[str, Any] | None:
    """Χρησιμοποιεί πραγματικά Google/DDG results + AI για να συμπεράνει το προϊόν."""
    web = context_text(barcode, limit=6)
    data = ai.infer_product(barcode, web)
    if not data:
        return None
    name = (data.get("product_name") or "").strip()
    desc = (data.get("description") or "").strip()
    if not name and not desc:
        return None
    return {"source": "AI/Web", "found": True, "product_name": name or desc,
            "brand": data.get("brand"), "categories": data.get("categories"),
            "description": desc, "confidence": data.get("confidence", "low")}


def fetch_product(barcode: str, *, use_ai: bool = True) -> dict[str, Any]:
    """Επιστρέφει το πρώτο έγκυρο αποτέλεσμα από όλες τις πηγές.

    Δοκιμάζει και τις εναλλακτικές μορφές του κωδικού (raw + κανονική) ώστε ένα
    EAN-8 να μη «χαθεί» ως λάθος zero-padded EAN-13. Αποτελέσματα με «σκουπίδι»
    όνομα (τίτλοι site) απορρίπτονται.
    """
    variants = barcode_variants(barcode) or [barcode]
    for fetcher in _FETCHERS:
        for variant in variants:
            try:
                result = fetcher(variant)
            except Exception as exc:  # noqa: BLE001
                debug(f"{fetcher.__name__} raised: {exc}")
                continue
            if not result.get("found"):
                continue
            if _is_junk_name(result.get("product_name")) and not (result.get("description") and not _is_junk_name(result.get("description"))):
                debug(f"{fetcher.__name__} returned junk name for {variant}, skipping")
                continue
            debug(f"Product found via {result.get('source')} for {variant}")
            return result
    # Τελευταία γραμμή: AI web-inference (όταν οι δομημένες πηγές δεν βρήκαν τίποτα).
    if use_ai and ai.ai_available():
        try:
            primary = ai_infer_from_web(barcode)
        except Exception as exc:  # noqa: BLE001
            debug(f"ai_infer_from_web raised: {exc}")
            primary = None
        if primary and primary.get("found") and not _is_junk_name(primary.get("product_name")):
            return primary
    return {"source": "none", "found": False}
