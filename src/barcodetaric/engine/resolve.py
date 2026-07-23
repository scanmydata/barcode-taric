"""Top-level pipeline: barcode/περιγραφή -> πλήρες αποτέλεσμα (περιγραφή EL/EN + TARIC)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import ai, barcode_sources, taric_match, translate


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
    candidates: list = field(default_factory=list)


def _clean_categories(categories: str) -> str:
    """Καθαρίζει τα OpenFoodFacts categories: αφαιρεί language prefixes & tags."""
    if not categories:
        return ""
    parts = re.split(r"[,>]", categories)
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
    """Από barcode -> αναλυτική περιγραφή (πολλαπλές πηγές + web/AI) -> TARIC."""
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

    # Βασικό κείμενο: όνομα + περιγραφή + ΚΑΤΗΓΟΡΙΕΣ (ο τύπος προϊόντος οδηγεί το matching).
    base = " · ".join(p for p in (name, raw_desc, categories) if p).strip(" ·") or name

    # AI enrichment -> αναλυτική περιγραφή με υλικό/χρήση/μέγεθος (π.χ. Merenda -> κακάο επάλειψη 360g).
    enriched = None
    if use_ai and ai.ai_available() and (name or categories):
        enriched = ai.enrich_description(name or base, brand=brand,
                                         categories=categories, quantity=quantity)

    display = enriched or base
    if quantity and quantity.lower() not in display.lower():
        display = f"{display} {quantity}".strip()

    el, en = translate.ensure_bilingual(display) if display else ("", "")

    result = ResolveResult(
        barcode=normalized, description_el=el, description_en=en, brand=brand,
        quantity=quantity, categories=categories,
        source=info.get("source", ""), found=bool(info.get("found")),
    )
    if do_match and (el or en):
        # Στο matching δίνουμε και τις κατηγορίες ως ενίσχυση (τύπος προϊόντος).
        _apply_match(result, extra=categories, use_ai=use_ai)
    return result


def resolve_description(description: str, *, barcode: str = "", use_ai: bool = True) -> ResolveResult:
    """Από περιγραφή (οποιαδήποτε γλώσσα) -> EL/EN -> TARIC."""
    el, en = translate.ensure_bilingual(description)
    result = ResolveResult(barcode=barcode.strip(), description_el=el, description_en=en,
                           source="manual", found=bool(el or en))
    if el or en:
        _apply_match(result, use_ai=use_ai)
    return result


def _apply_match(result: ResolveResult, *, extra: str = "", use_ai: bool) -> None:
    el = f"{result.description_el} {extra}".strip()
    en = f"{result.description_en} {extra}".strip()
    m = taric_match.match(el, en, barcode=result.barcode, brand=result.brand,
                          quantity=result.quantity, categories=result.categories, use_ai=use_ai)
    result.taric_code = m.taric_code
    result.hs4 = m.hs4
    result.taric_description = m.taric_description
    result.confidence = m.confidence
    result.ai_rationale = m.ai_rationale
    result.taric_source = m.taric_source
    result.candidates = m.candidates
