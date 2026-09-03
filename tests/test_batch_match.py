"""Batch-AI μαζική αντιστοίχιση: πολλά προϊόντα ανά κλήση AI (offline, stubbed)."""

import json
import re

import pytest

from barcodetaric import repo
from barcodetaric.engine import ai, taric_match
from barcodetaric.taric import importer


@pytest.fixture(scope="module", autouse=True)
def _seed():
    importer.import_seed()
    assert repo.taric_row_count() >= 10
    from barcodetaric.config import SETTINGS
    from barcodetaric.engine import ml_classifier
    SETTINGS.set("ml_confidence_threshold", 0.55)
    ml_classifier._CACHED = ml_classifier.TaricML()  # άδειο μοντέλο -> ML tier παρακάμπτεται


@pytest.fixture
def stub_ai(monkeypatch):
    """AI που διαβάζει το batch prompt & επιστρέφει τον 1ο υποψήφιο κάθε προϊόντος."""
    calls = {"n": 0}

    def fake_chat(prompt, **kw):
        calls["n"] += 1
        out = []
        # Το batch prompt έχει ΔΥΟ μορφές (διαλέγεται η φθηνότερη σε tokens):
        #   shared : κοινό CODEBOOK + «[i] query / allowed: c1, c2»
        #   inline : «[i] query / c1 = desc»
        # Ο stub πιάνει και τις δύο: index -> ο 1ος κωδικός που ακολουθεί.
        for m in re.finditer(r"\[(\d+)\][^\[]*?(\d{4,10})", prompt, re.S):
            out.append({"i": int(m.group(1)), "code": m.group(2),
                        "confidence": 0.8, "rationale": "test"})
        return json.dumps(out)

    monkeypatch.setattr(ai, "chat", fake_chat)
    monkeypatch.setattr(ai, "ai_available", lambda: True)
    return calls


def test_rank_taric_batch_one_call(stub_ai):
    prods = [
        {"query": "coffee", "candidates": [{"code": "0901000000", "description_en": "coffee"}]},
        {"query": "water", "candidates": [{"code": "2201000000", "description_en": "water"}]},
    ]
    res = ai.rank_taric_batch(prods, batch_size=12)
    assert stub_ai["n"] == 1                       # ΕΝΑ AI call για 2 προϊόντα
    assert [r["code"] for r in res] == ["0901000000", "2201000000"]


def test_rank_taric_batch_rejects_noncandidate(stub_ai, monkeypatch):
    # AI επιστρέφει κωδικό εκτός υποψηφίων -> None (δεν τον δεχόμαστε)
    monkeypatch.setattr(ai, "chat",
                        lambda p, **k: json.dumps([{"i": 0, "code": "9999999999"}]))
    res = ai.rank_taric_batch([{"query": "x", "candidates": [{"code": "0901000000"}]}])
    assert res == [None]


def test_match_batch_catalog_then_ai(stub_ai):
    from barcodetaric.models import CatalogItem
    repo.upsert_catalog(CatalogItem(barcode="4000000000009", description_el="δοκιμή",
                                    taric_code="1905", hs4="1905", verified=1))
    items = [
        {"description_el": "δοκιμή", "barcode": "4000000000009", "source": "excel"},  # catalog
        {"description_el": "καφές", "description_en": "coffee", "source": "excel"},   # AI
    ]
    res = taric_match.match_batch(items)
    assert len(res) == 2
    assert res[0].taric_code == "1905" and res[0].taric_source == "catalog"
    assert stub_ai["n"] == 1                       # catalog δεν κάλεσε AI· μόνο το 2ο
    assert res[1].taric_source in ("ai", "fts")    # ai αν βρέθηκαν υποψήφιοι
