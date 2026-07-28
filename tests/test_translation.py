"""Tests για το δωρεάν μεταφραστικό tier, το English-first matching & το web corroboration.

Όλα offline/ντετερμινιστικά: το δίκτυο (MyMemory/web) γίνεται mock.
"""

import pytest

from barcodetaric.config import SETTINGS
from barcodetaric.engine import translation_api, web_search


@pytest.fixture(autouse=True)
def _clear_cache():
    translation_api._CACHE.clear()
    yield
    translation_api._CACHE.clear()


def test_mymemory_translation(monkeypatch):
    calls = {"n": 0}

    def fake_http_json(url, **kw):
        calls["n"] += 1
        assert "langpair=el%7Cen" in url or "langpair=en%7Cel" in url  # el|en / en|el encoded
        return {"responseStatus": 200,
                "responseData": {"translatedText": "Natural mineral water"}}

    monkeypatch.setattr(translation_api, "http_json", fake_http_json)
    out = translation_api.to_english("Φυσικό μεταλλικό νερό")
    assert out == "Natural mineral water"
    # 2η κλήση ίδιου κειμένου -> από cache, χωρίς δεύτερο http hit.
    assert translation_api.to_english("Φυσικό μεταλλικό νερό") == "Natural mineral water"
    assert calls["n"] == 1


def test_translation_skips_when_same_language(monkeypatch):
    # Αγγλικό κείμενο με target=en -> επιστρέφει ως έχει, χωρίς δικτυακή κλήση.
    monkeypatch.setattr(translation_api, "http_json",
                        lambda *a, **k: pytest.fail("should not hit network"))
    assert translation_api.to_english("coffee beans") == "coffee beans"


def test_mymemory_rejects_quota_status(monkeypatch):
    monkeypatch.setattr(translation_api, "http_json",
                        lambda *a, **k: {"responseStatus": 429,
                                         "responseData": {"translatedText": "IGNORED"}})
    assert translation_api.to_english("Νερό") is None


def test_english_first_match_from_greek(monkeypatch):
    """Ελληνικό-μόνο query πρέπει να μεταφράζεται σε EN πριν το scoring."""
    from barcodetaric.engine import taric_match
    from barcodetaric.taric import importer

    importer.import_seed()
    # classify_in_english είναι True by default· αρκεί να «πιάσουμε» τη μετάφραση.
    monkeypatch.setattr(translation_api, "to_english", lambda t, **kw: "coffee")

    m = taric_match.match("καφές", "", use_ai=False)
    assert m.taric_code.startswith("0901"), m.taric_code


def test_semantic_fallback_used_when_stronger(monkeypatch):
    """Χωρίς AI: αν το semantic tier είναι πιο σίγουρο από το FTS, κερδίζει."""
    from barcodetaric.engine import taric_match, embeddings
    from barcodetaric.taric import importer
    from barcodetaric.models import TaricRow

    importer.import_seed()
    row = TaricRow(code="2202100000", level=8, description_el="Αναψυκτικά με ανθρακικό",
                   description_en="Carbonated soft drinks", hs4="2202")
    # Άσχετο query για το FTS, αλλά «κοντινό» εννοιολογικά -> semantic top.
    monkeypatch.setattr(embeddings, "semantic_candidates", lambda q, **kw: [(0.72, row)])
    monkeypatch.setattr(taric_match.embeddings, "semantic_candidates", lambda q, **kw: [(0.72, row)])

    m = taric_match.match("zzzznomatchword", "zzzznomatchword", use_ai=False)
    assert m.taric_source == "semantic", m.taric_source
    assert m.taric_code == "2202100000"


def test_clean_for_classification_strips_noise():
    from barcodetaric.engine import taric_match as tm
    out = tm.clean_for_classification("NOUNOU strained yogurt 1,5% fat 2x175g", brand="NOUNOU")
    low = out.lower()
    assert "yogurt" in low and "strained" in low          # κρατά το είδος
    assert "nounou" not in low                             # αφαιρεί brand
    assert "2x175g" not in low and "175" not in out        # αφαιρεί ποσότητα
    assert "1,5%" not in out and "%" not in out            # αφαιρεί ποσοστό
    # Ποτέ κενό: αν όλα «θόρυβος», κράτα το αρχικό.
    assert tm.clean_for_classification("500g", brand="") == "500g"


def test_custom_endpoint_url_normalization(monkeypatch):
    from barcodetaric.engine import ai
    cases = {
        "https://ollama.me": "https://ollama.me/v1/chat/completions",
        "https://ollama.me/v1": "https://ollama.me/v1/chat/completions",
        "https://ollama.me/v1/chat/completions": "https://ollama.me/v1/chat/completions",
        "": "",
    }
    for given, expected in cases.items():
        monkeypatch.setattr(ai.SETTINGS, "get",
                            lambda k, d=None, _g=given: _g if k == "custom_ai_url" else "")
        assert ai._custom_endpoint_url() == expected


def test_custom_provider_registered():
    from barcodetaric.engine import ai
    from barcodetaric.engine import web_search
    assert "custom" in ai._PROVIDERS
    assert "searxng" in web_search._TIERS


def test_name_corroboration():
    items = [
        {"title": "Θέρισσο Φυσικό Μεταλλικό Νερό 1.5L", "snippet": "εμφιαλωμένο νερό"},
        {"title": "Theriso mineral water", "snippet": "natural spring water bottled"},
    ]
    # Ονομασία που εμφανίζεται στα αποτελέσματα -> υψηλό score.
    assert web_search.name_corroboration("Θέρισσο μεταλλικό νερό", items) >= 0.5
    # Άσχετη ονομασία -> χαμηλό score.
    assert web_search.name_corroboration("wireless bluetooth headphones", items) < 0.5
    # Κενή/γενική ονομασία -> 0.
    assert web_search.name_corroboration("the product", items) == 0.0
