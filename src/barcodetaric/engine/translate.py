"""EL<->EN μεταφράσεις (AI) + έλεγχοι ποιότητας ονόματος προϊόντος."""

from __future__ import annotations

import re

from . import ai
from .http_util import contains_greek, contains_latin, normalize_for_matching

_SPAM_TOKENS = {
    "women", "woman", "men", "man", "dark", "circle", "blemishes", "cover", "kit", "set",
    "skin", "care", "cosmetics", "makeup", "health", "beauty", "personal",
}


def looks_low_quality(name: str, *, description: str = "", brand: str = "") -> bool:
    normalized = normalize_for_matching(name)
    if not normalized:
        return True
    tokens = [t for t in normalized.split() if t]
    if len(tokens) >= 14:
        return True
    if sum(1 for t in tokens if t in _SPAM_TOKENS) >= 5:
        return True
    if description and normalize_for_matching(description) == normalized:
        return True
    if brand:
        nb = normalize_for_matching(brand)
        if nb and nb in normalized and len(tokens) > 10:
            return True
    return False


def derive_fallback_name(*, brand: str = "", description: str = "", categories: str = "") -> str:
    descriptor = ""
    if description:
        raw = re.findall(r"[A-Za-zΑ-ω0-9]+", description)
        keep = [t for t in raw if normalize_for_matching(t) not in _SPAM_TOKENS]
        descriptor = " ".join(keep[:3]).strip()
    if not descriptor and categories:
        descriptor = categories.split(">")[-1].strip()
    if brand and descriptor:
        if normalize_for_matching(brand) in normalize_for_matching(descriptor):
            return descriptor
        return f"{brand} {descriptor}".strip()
    return (brand or descriptor or "").strip()


def sanitize_name(name: str, *, brand: str = "", description: str = "", categories: str = "") -> str:
    clean = str(name or "").strip()
    if not clean:
        return ""
    if not looks_low_quality(clean, description=description, brand=brand):
        return clean
    return derive_fallback_name(brand=brand, description=description, categories=categories) or ""


def ensure_bilingual(text: str) -> tuple[str, str]:
    """Δέχεται περιγραφή σε οποιαδήποτε γλώσσα, επιστρέφει (ελληνικά, αγγλικά).

    Χρησιμοποιεί AI για τη μετάφραση που λείπει· αν αποτύχει, επιστρέφει ό,τι υπάρχει.
    """
    text = (text or "").strip()
    if not text:
        return "", ""
    el = text if contains_greek(text) else ""
    en = text if (contains_latin(text) and not contains_greek(text)) else ""
    if el and not en:
        en = ai.translate(el, target="en") or el      # fallback στο διαθέσιμο κείμενο
    elif en and not el:
        el = ai.translate(en, target="el") or en      # ποτέ κενό EL
    elif not el and not en:
        # ούτε ελληνικά ούτε λατινικά (π.χ. αριθμοί) — κράτα ως έχει
        el = en = text
    return el.strip(), en.strip()
