"""Dataclasses για τις οντότητες της βάσης."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Client:
    id: Optional[int] = None
    name: str = ""
    vat: str = ""          # ΑΦΜ
    email: str = ""
    phone: str = ""
    address: str = ""
    notes: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class CatalogItem:
    """Κεντρική βάση γνώσης: barcode -> περιγραφή -> TARIC (μοιράζεται σε όλους τους πελάτες)."""
    id: Optional[int] = None
    barcode: str = ""
    description_el: str = ""
    description_en: str = ""
    taric_code: str = ""
    hs4: str = ""
    taric_description: str = ""
    confidence: float = 0.0
    ai_rationale: str = ""
    taric_source: str = ""   # ml | ai | fts | manual | web
    verified: int = 0        # 1 = επιβεβαιωμένο από χρήστη -> training label
    source: str = ""         # πηγή περιγραφής (OpenFoodFacts, excel, ...)
    brand: str = ""          # λεπτομέρειες προϊόντος (για matching/training)
    quantity: str = ""       # μέγεθος/ποσότητα (π.χ. 360g)
    categories: str = ""     # κατηγορίες/τύπος προϊόντος
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class ClientItem:
    """Γραμμή κωδικολογίου ενός πελάτη."""
    id: Optional[int] = None
    client_id: int = 0
    barcode: str = ""
    description_el: str = ""
    description_en: str = ""
    taric_code: str = ""
    hs4: str = ""
    taric_description: str = ""
    confidence: float = 0.0
    ai_rationale: str = ""
    taric_source: str = ""
    verified: int = 0
    source: str = ""
    brand: str = ""
    quantity: str = ""
    categories: str = ""
    catalog_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class TaricRow:
    """Εγγραφή επίσημης ΕΕ ονοματολογίας (CN/TARIC)."""
    id: Optional[int] = None
    code: str = ""
    level: int = 0
    parent_code: str = ""
    description_el: str = ""
    description_en: str = ""
    # Σύνθετη περιγραφή με το γονικό context (π.χ. «Βοοειδή ζωντανά > Άλλα») — βελτιώνει matching.
    description_path_el: str = ""
    description_path_en: str = ""
    hs4: str = ""
    indent: int = 0
    unit: str = ""
    valid_from: str = ""
    valid_to: str = ""
    source_version: str = ""


@dataclass
class TaricCandidate:
    """Υποψήφια αντιστοίχιση TARIC με σκορ/αιτιολόγηση."""
    code: str
    description_el: str
    description_en: str
    hs4: str
    score: float = 0.0
    source: str = ""            # ml | fts | ai | catalog
    rationale: str = ""
    extra: dict = field(default_factory=dict)
