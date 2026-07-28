"""Top-level pipeline: barcode/περιγραφή -> πλήρες αποτέλεσμα (περιγραφή EL/EN + TARIC)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import ai, barcode_sources, taric_match, translate, web_search


@dataclass
class ResolveResult:
    barcode: str = ""
    description_el: str = ""
    description_en: str = ""
    brand: str = ""
    quantity: str = ""
    categories: str = ""
    taric_code: str = ""
    hs4: str = ""
    taric_description: str = ""
    confidence: float = 0.0
    ai_rationale: str = ""
    taric_source: str = ""            # πηγή περιγραφής
    source: str = ""
    found: bool = False
    is_product: bool = True           # false = υπηρεσία/άυλο -> χωρίς TARIC
    customs_hint: str = ""            # εσωτερικό: είδος/υλικό για matching (δεν εμφανίζεται)
    analysis: str = ""                # δομημένη «ανάλυση» (hint+κατηγορίες+μάρκα+ποσότητα) -> tariff + ML
    candidates: list = field(default_factory=list)


def _clean_categories(categories) -> str:
    """Καθαρίζει τα OpenFoodFacts categories: αφαιρεί language prefixes & tags.

    Δέχεται str Ή list (το AI infer_product μπορεί να επιστρέψει JSON array -> ο
    παλιός κώδικας έσκαγε με «expected string, got list»).
    """
    if not categories:
        return ""
    if isinstance(categories, (list, tuple)):
        categories = ", ".join(str(c) for c in categories)
    parts = re.split(r"[,>]", str(categories))
    cleaned = []
    for part in parts:
        part = re.sub(r"^[a-z]{2}:", "", part.strip())      # 'en:' , 'fr:'
        part = part.replace("-", " ").strip()
        if part and part.lower() not in {"breakfasts", "spreads", "sweet spreads"}:
            cleaned.append(part)
    # κράτα τα πιο ειδικά (τελευταία), χωρίς διπλότυπα
    seen, out = set(), []
    for c in reversed(cleaned):
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return ", ".join(out[:3])


def resolve_barcode(barcode: str, *, use_ai: bool = True, do_match: bool = True) -> ResolveResult:
    """Από barcode -> ΟΝΟΜΑΣΙΑ (διασταύρωση πηγών + web + AI) -> TARIC.

    Ροή («ασφαλίζουμε την περιγραφή πριν κατατάξουμε»):
      1. Δομημένες πηγές barcode (OpenFoodFacts/UPC/…) -> υποψήφια ονομασία.
      2. Παράλληλη αναζήτηση web για το barcode ΚΑΙ για την ονομασία (cross-check).
      3. Ένα AI βήμα «κλειδώνει» ονομασία EL/EN (μόνο ΤΙ είναι, όχι αναλυτική
         περιγραφή), αν είναι προϊόν ή υπηρεσία, και ένα customs_hint για κατάταξη.
      4. Υπηρεσίες/άυλα ΔΕΝ λαμβάνουν TARIC. Τα προϊόντα κατατάσσονται με το hint.
    """
    normalized = barcode_sources.normalize_to_ean13(barcode) or barcode.strip()
    info = barcode_sources.fetch_product(normalized, use_ai=use_ai)

    name = translate.sanitize_name(
        info.get("product_name") or "",
        brand=info.get("brand") or "", description=info.get("description") or "",
        categories=info.get("categories") or "",
    )
    brand = info.get("brand") or ""
    categories = _clean_categories(info.get("categories") or "")
    quantity = str(info.get("quantity") or "").strip()
    raw_desc = info.get("description") or ""

    result = ResolveResult(
        barcode=normalized, brand=brand, quantity=quantity, categories=categories,
        source=info.get("source", ""), found=bool(info.get("found")),
    )

    # (2)+(3) διασταύρωση web (barcode + ονομασία) και AI confirm.
    if not _confirm_identity(result, candidate_name=name, candidate_description=raw_desc,
                             brand=brand, categories=categories, use_ai=use_ai):
        # Fallback χωρίς AI: κράτα ΟΝΟΜΑΣΙΑ (όχι αναλυτική περιγραφή).
        display = name or raw_desc or categories
        result.description_el, result.description_en = (
            translate.ensure_bilingual(display) if display else ("", "")
        )

    # (4) Υπηρεσίες/άυλα: χωρίς TARIC.
    if not result.is_product:
        result.taric_source = "service"
        result.ai_rationale = "Αναγνωρίστηκε ως υπηρεσία/άυλο — δεν λαμβάνει κωδικό TARIC."
        return result

    if do_match and (result.description_el or result.description_en or result.customs_hint):
        _apply_match(result, use_ai=use_ai)
    return result


def _fill_bilingual(el: str, en: str) -> tuple[str, str]:
    """Εξασφαλίζει ότι υπάρχουν και οι δύο γλώσσες (μεταφράζει ό,τι λείπει)."""
    el, en = (el or "").strip(), (en or "").strip()
    if el and not en:
        en = ai.translate(el, target="en") or el
    elif en and not el:
        el = ai.translate(en, target="el") or en
    return el, en


def _confirm_identity(result: ResolveResult, *, candidate_name: str, candidate_description: str = "",
                      brand: str = "", categories: str = "", use_ai: bool) -> bool:
    """Web cross-check (OpenSERP → … → DuckDuckGo) + ΕΝΑ AI confirm.

    Ψάχνει ΤΑΥΤΟΧΡΟΝΑ για το barcode και για την ονομασία/περιγραφή, και «κλειδώνει»
    ονομασία EL/EN (name-only), is_product και customs_hint. Χρησιμοποιείται και από
    το barcode και από το description path. Επιστρέφει True αν επιβεβαίωσε το AI.
    """
    if not (use_ai and ai.ai_available()):
        return False
    web = web_search.gather_context(barcode=result.barcode, name=candidate_name or candidate_description,
                                    brand=brand, limit=5)
    if web.get("barcode_hits") or web.get("name_hits"):
        result.found = True
    confirmed = ai.confirm_product(
        barcode=result.barcode, candidate_name=candidate_name,
        candidate_description=candidate_description, brand=brand,
        categories=categories, web_context=web.get("text", ""),
    )
    if not (confirmed and (confirmed["name_el"] or confirmed["name_en"])):
        return False
    el = confirmed["name_el"] or confirmed["name_en"]
    en = confirmed["name_en"] or confirmed["name_el"]
    result.description_el, result.description_en = _fill_bilingual(el, en)
    result.is_product = confirmed["is_product"]
    result.customs_hint = confirmed["customs_hint"]
    result.confidence = confirmed["confidence"]
    if confirmed["confidence"]:
        result.found = True
    return True


def resolve_description(description: str, *, barcode: str = "", use_ai: bool = True) -> ResolveResult:
    """Από περιγραφή -> (OpenSERP + AI confirm) -> ονομασία EL/EN -> TARIC.

    Και εδώ η περιγραφή «ασφαλίζεται»: γίνεται αναζήτηση web για να επιβεβαιωθεί
    τι είναι το προϊόν πριν την κατάταξη (ίδια λογική με το barcode path).
    """
    el, en = translate.ensure_bilingual(description)
    result = ResolveResult(barcode=barcode.strip(), description_el=el, description_en=en,
                           source="manual", found=bool(el or en))
    _confirm_identity(result, candidate_name=description, use_ai=use_ai)
    if not result.is_product:
        result.taric_source = "service"
        result.ai_rationale = "Αναγνωρίστηκε ως υπηρεσία/άυλο — δεν λαμβάνει κωδικό TARIC."
        return result
    if result.description_el or result.description_en or result.customs_hint:
        _apply_match(result, use_ai=use_ai)
    return result


def _apply_match(result: ResolveResult, *, use_ai: bool) -> None:
    # Στην κατάταξη δίνουμε ΟΝΟΜΑΣΙΑ + customs_hint (είδος/υλικό) + κατηγορίες:
    # το hint ξεχωρίζει π.χ. «μεταλλικό νερό» (2201) από «toilet water» (3303).
    hint = result.customs_hint
    # Δομημένη «ανάλυση» προϊόντος (αποθηκεύεται πίσω από την περιγραφή): υλικό/τύπος (hint) +
    # κατηγορίες + μάρκα + ποσότητα. Χρησιμεύει για ακριβέστερη κατάταξη ΚΑΙ ως ML feature.
    result.analysis = " · ".join(p for p in (
        hint, result.categories, result.brand, result.quantity) if p)
    el = " ".join(p for p in (result.description_el, hint, result.categories) if p).strip()
    en = " ".join(p for p in (result.description_en, hint, result.categories) if p).strip()
    m = taric_match.match(el, en, barcode=result.barcode, brand=result.brand,
                          quantity=result.quantity, categories=result.categories,
                          analysis=result.analysis, source=result.source, use_ai=use_ai)
    result.taric_code = m.taric_code
    result.hs4 = m.hs4
    result.taric_description = m.taric_description
    result.confidence = m.confidence
    result.ai_rationale = m.ai_rationale
    result.taric_source = m.taric_source
    result.candidates = m.candidates
