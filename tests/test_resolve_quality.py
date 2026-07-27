"""Tests για την ποιότητα/αξιοπιστία της αντιστοίχισης:

- EAN-8 (χωρίς λάθος zero-padding)
- φίλτρο «junk» ονομάτων (τίτλοι site αντί για προϊόν)
- chapter prior: «X water» από OpenFoodFacts -> τρόφιμο (2201), ΟΧΙ άρωμα (3303)
- AI confirm: ονομασία EL/EN + gate προϊόντος/υπηρεσίας
"""

import json

import pytest

from barcodetaric import repo
from barcodetaric.engine import barcode_sources as bs
from barcodetaric.models import TaricRow
from barcodetaric.taric import importer


def test_ean8_not_zero_padded():
    # 64320458 είναι EAN-8: πρέπει να μείνει ως έχει, όχι 0000064320458.
    assert bs.normalize_to_ean13("64320458") == "64320458"
    assert bs.barcode_variants("64320458") == ["64320458"]
    # EAN-13 παραμένει, EAN-12 συμπληρώνεται με checksum.
    assert bs.normalize_to_ean13("5200250049346") == "5200250049346"


def test_junk_name_filter():
    assert bs._is_junk_name("EAN-Search.org | EAN, GTIN, UPC & ISBN Lookup and API")
    assert bs._is_junk_name("Barcode Lookup")
    assert bs._is_junk_name("")
    assert not bs._is_junk_name("Θέρισσο Φυσικό Μεταλλικό Νερό 1.5L")


@pytest.fixture()
def _seed_with_water_trap():
    importer.import_seed()
    repo.bulk_insert_taric([
        TaricRow(code="3303000000", level=8, description_el="Αρώματα και κολόνιες",
                 description_en="Perfumes and toilet waters",
                 description_path_el="Αρώματα και κολόνιες",
                 description_path_en="Perfumes and toilet waters", hs4="3303"),
        TaricRow(code="2201101100", level=8, description_el="Φυσικά μεταλλικά νερά εμφιαλωμένα",
                 description_en="Natural mineral waters bottled",
                 description_path_el="Φυσικά μεταλλικά νερά",
                 description_path_en="Natural mineral waters bottled", hs4="2201"),
    ], version="test-inject", source_url="test")


def test_chapter_prior_steers_water_to_food(_seed_with_water_trap):
    from barcodetaric.engine import taric_match
    # Χωρίς πηγή: το «water» είναι ασαφές (μπορεί να πέσει σε 3303).
    # Με πηγή OpenFoodFacts (τρόφιμο) πρέπει σίγουρα να πάει σε κεφ. 22 (2201).
    m = taric_match.match("theriso water", "theriso water", source="OpenFoodFacts", use_ai=False)
    assert m.taric_code.startswith("2201"), m.taric_code
    assert not m.taric_code.startswith("3303")


def test_confirm_product_and_service_gate(monkeypatch):
    from barcodetaric.engine import ai

    def fake_chat(prompt, **kw):
        low = prompt.lower()
        if "insurance" in low or "ασφάλ" in low:
            return json.dumps({"name_el": "Ασφάλιση", "name_en": "Insurance",
                               "is_product": False, "customs_hint": "", "confidence": 0.9})
        return json.dumps({"name_el": "Φυσικό μεταλλικό νερό", "name_en": "Natural mineral water",
                           "is_product": True, "customs_hint": "natural mineral water bottled",
                           "confidence": 0.9})

    monkeypatch.setattr(ai, "chat", fake_chat)
    monkeypatch.setattr(ai, "ai_available", lambda: True)

    product = ai.confirm_product(candidate_name="theriso water", web_context="bottled mineral water")
    assert product["is_product"] is True
    assert product["name_el"] and product["name_en"]          # ονομασία EL + EN
    assert "water" in product["customs_hint"].lower()

    service = ai.confirm_product(candidate_name="car insurance", web_context="annual insurance policy")
    assert service["is_product"] is False                     # υπηρεσία -> χωρίς TARIC
