"""Tests για τα νέα χαρακτηριστικά: hierarchy parser, free-model enforcement, AFM lookup."""

import pytest

from barcodetaric.config import SETTINGS


def test_openrouter_free_enforcement():
    from barcodetaric.engine.ai import _ensure_free
    assert _ensure_free("meta-llama/llama-3.3-70b-instruct") == "meta-llama/llama-3.3-70b-instruct:free"
    assert _ensure_free("x/y:free") == "x/y:free"
    assert _ensure_free("").endswith(":free")


def test_business_lookup_guards():
    from barcodetaric.engine import business_lookup
    # μη έγκυρο ΑΦΜ
    r = business_lookup.lookup_by_afm("123")
    assert not r["success"] and "ΑΦΜ" in (r["error"] or "")
    # έγκυρο ΑΦΜ αλλά χωρίς key
    SETTINGS.set("business_portal_key", "")
    import os
    os.environ.pop("BUSINESS_PORTAL_KEY", None)
    r2 = business_lookup.lookup_by_afm("094000000")
    assert not r2["success"] and "key" in (r2["error"] or "").lower()


def test_nomenclature_hierarchy_parser(tmp_path):
    from openpyxl import Workbook
    from barcodetaric.taric import importer

    def make(path, lang, descs):
        wb = Workbook(); ws = wb.active
        ws.append(["Goods code", "Start", "End", "Language", "Hier", "Indent", "Description", "x"])
        for code, indent, desc in descs:
            ws.append([code, "", "", lang, "", indent, desc, ""])
        wb.save(path)

    el = [("0100000000 80", None, "ΖΩΑ ΖΩΝΤΑΝΑ"),
          ("0101000000 80", None, "Άλογα κ.λπ."),
          ("0101210000 10", "- ", "Άλογα"),
          ("0101210000 80", "- - ", "Αναπαραγωγής καθαρής φυλής")]
    en = [("0100000000 80", None, "LIVE ANIMALS"),
          ("0101000000 80", None, "Horses etc."),
          ("0101210000 10", "- ", "Horses"),
          ("0101210000 80", "- - ", "Pure-bred breeding")]
    make(tmp_path / "el.xlsx", "EL", el)
    make(tmp_path / "en.xlsx", "EN", en)

    rows = importer.parse_nomenclature(tmp_path / "el.xlsx", tmp_path / "en.xlsx", "test")
    by_desc = {r.description_el: r for r in rows}
    leaf = by_desc["Αναπαραγωγής καθαρής φυλής"]
    assert leaf.code == "0101210000"
    assert leaf.hs4 == "0101"
    # Το path πρέπει να περιέχει το γονικό context (ζώα > άλογα > ...).
    assert "ΖΩΑ ΖΩΝΤΑΝΑ" in leaf.description_path_el
    assert "Αναπαραγωγής καθαρής φυλής" in leaf.description_path_el
    assert leaf.description_en == "Pure-bred breeding"
    assert "LIVE ANIMALS" in leaf.description_path_en


def test_fold_and_stem_greek():
    from barcodetaric.engine.http_util import stem_token
    assert stem_token("νερο") == stem_token("νερα")  # ίδια ρίζα ενικός/πληθυντικός
    assert stem_token("waters") == "water"


def test_ensure_free_router_alias():
    from barcodetaric.engine.ai import _ensure_free, DEFAULT_FREE_MODEL
    # ο generic router alias δεν παίρνει :free suffix
    assert _ensure_free("openrouter/free") == "openrouter/free"
    assert _ensure_free("") == DEFAULT_FREE_MODEL
    assert _ensure_free("x/y").endswith(":free")


def test_custom_provider_skipped_when_unset():
    from barcodetaric.engine import ai
    from barcodetaric.config import SETTINGS
    import os
    SETTINGS.set("custom_ai_base_url", "")
    os.environ.pop("CUSTOM_AI_BASE_URL", None)
    assert ai._custom("hello", 5) is None
    assert "custom" in ai._PROVIDERS


def test_searxng_tier_skipped_when_unset():
    from barcodetaric.engine import web_search
    from barcodetaric.config import SETTINGS
    SETTINGS.set("searxng_url", "")
    assert web_search._via_searxng("coffee", 3) == []
    assert "searxng" in web_search._TIERS
    # ο debugger επιστρέφει μία εγγραφή ανά tier της σειράς
    names = [n for n, _ok, _msg in web_search.test_tiers("x")]
    assert "searxng" in names


def test_rank_free_prefers_known_families():
    from barcodetaric.engine.ai import _rank_free
    ranked = _rank_free(["zzz/unknown-model:free", "openai/gpt-oss-20b:free",
                         "google/gemma-4-31b-it:free"])
    assert ranked[0].startswith("openai/gpt-oss")
    assert ranked[-1].startswith("zzz/")


def test_headless_tier_registered():
    from barcodetaric.engine import web_search
    assert "headless" in web_search._TIERS
    assert "headless" in web_search._DEFAULT_ORDER


def test_fetch_product_attaches_web_context(monkeypatch):
    from barcodetaric.engine import barcode_sources as bs
    # μία δομημένη πηγή βρίσκει προϊόν, οι υπόλοιπες όχι
    monkeypatch.setattr(bs, "_FETCHERS", (
        lambda code: {"source": "Test", "found": True, "product_name": "Merenda", "brand": "Pavlidis"},
    ))
    monkeypatch.setattr(bs.ai, "ai_available", lambda: True)
    monkeypatch.setattr(bs, "context_text", lambda q, limit=6: f"WEB[{q}]")
    out = bs.fetch_product("7622201126131", use_ai=True)
    assert out["found"] and out["product_name"] == "Merenda"
    # web context από αναζήτηση ΜΕ ΤΟ ΟΝΟΜΑ (όχι το barcode)
    assert out["web_context"] == "WEB[Merenda Pavlidis]"


def test_web_context_query_uses_name_brand_category(monkeypatch):
    from barcodetaric.engine import barcode_sources as bs
    seen = {}
    monkeypatch.setattr(bs, "context_text", lambda q, limit=6: seen.setdefault("q", q) or "ctx")
    result = {"product_name": "Merenda", "brand": "Pavlidis",
              "categories": "en:hazelnut-spreads, en:breakfasts"}
    bs._web_context_for(result, "7622201126131")
    # disambiguation: όνομα + μάρκα + κατηγορία (όχι σκέτο barcode)
    assert "Merenda" in seen["q"] and "Pavlidis" in seen["q"]
    assert "hazelnut" in seen["q"].lower()


def test_confirm_identity_stores_ai_analysis(monkeypatch):
    """Το ΕΞΥΠΝΟ analysis από το confirm_product πρέπει να αποθηκεύεται στο ResolveResult."""
    from barcodetaric.engine import ai, web_search
    from barcodetaric.engine.resolve import ResolveResult, _confirm_identity
    monkeypatch.setattr(ai, "ai_available", lambda: True)
    monkeypatch.setattr(web_search, "gather_context",
                        lambda **k: {"barcode_hits": [], "name_hits": [], "text": ""})
    monkeypatch.setattr(ai, "confirm_product", lambda **k: {
        "name_el": "γάλα", "name_en": "milk", "is_product": True, "customs_hint": "cow milk",
        "analysis": "Dairy product; cow milk, pasteurised; food, HS chapter 04.", "confidence": 0.9})
    r = ResolveResult()
    ok = _confirm_identity(r, candidate_name="γάλα αγελάδος", use_ai=True)
    assert ok
    assert r.analysis == "Dairy product; cow milk, pasteurised; food, HS chapter 04."
    assert r.customs_hint == "cow milk"


def test_analysis_field_roundtrip():
    """Το πεδίο analysis (δομημένη ανάλυση προϊόντος) πρέπει να αποθηκεύεται & να διαβάζεται."""
    from barcodetaric import repo
    from barcodetaric.models import Client, ClientItem, CatalogItem
    cid = repo.create_client(Client(name="ML-Test Πελάτης"))
    item = ClientItem(client_id=cid, barcode="5200000000009", description_el="γάλα",
                      taric_code="0401100000", analysis="υγρό γαλακτοκομικό · αγελάδος · 1lt")
    iid = repo.upsert_client_item(item)
    got = repo.get_client_item(iid)
    assert got is not None and got.analysis == "υγρό γαλακτοκομικό · αγελάδος · 1lt"
    # catalog επίσης
    cat_id = repo.upsert_catalog(CatalogItem(barcode="5200000000016", description_el="καφές",
                                             taric_code="0901210000", analysis="κόκκοι καφέ · αλεσμένος"))
    assert repo.get_catalog_by_barcode("5200000000016").analysis == "κόκκοι καφέ · αλεσμένος"


def test_ml_feature_text_and_pipeline_include_analysis_and_char():
    from barcodetaric.engine import ml_classifier as ml
    txt = ml._feature_text("γάλα", "milk", "520", "Δέλτα", "1lt", "dairy", "υγρό γαλακτοκομικό")
    assert "υγρό γαλακτοκομικό" in txt
    # το pipeline πρέπει να έχει ΚΑΙ char analyzer (word+char n-grams)
    pytest.importorskip("sklearn")
    pipe = ml._build_pipeline()
    analyzers = [v.analyzer for _, v in pipe.named_steps["feats"].transformer_list]
    assert "word" in analyzers and "char_wb" in analyzers


def test_food_source_chapter_prior(monkeypatch):
    """Πηγή τροφίμου (OpenFoodFacts) πρέπει να στρέφει την κατάταξη σε κεφάλαια 01-24
    (π.χ. «water» -> 2201 μεταλλικό νερό, ΟΧΙ 3303 άρωμα)."""
    from barcodetaric.engine import taric_match as tm
    assert tm._is_food_source("OpenFoodFacts") is True
    assert tm._is_food_source("manual") is False
    assert tm._is_food_chapter("2201101100") is True
    assert tm._is_food_chapter("3303000000") is False


def test_custom_endpoint_builds_url(monkeypatch):
    from barcodetaric.engine import ai
    from barcodetaric.config import SETTINGS
    captured = {}
    SETTINGS.set("custom_ai_base_url", "https://x.trycloudflare.com/v1")
    SETTINGS.set("custom_ai_model", "qwen2.5:7b")
    SETTINGS.set("custom_ai_api_key", "")
    SETTINGS.set("custom_ai_timeout", 90)

    def fake_http_json(url, **kw):
        captured["url"] = url
        captured["timeout"] = kw.get("timeout")
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(ai, "http_json", fake_http_json)
    r = ai._custom("hi", 20)
    assert r == "ok"
    assert captured["url"] == "https://x.trycloudflare.com/v1/chat/completions"
    assert captured["timeout"] >= 90   # local LLM generous timeout (max(call_timeout, setting))
    SETTINGS.set("custom_ai_base_url", "")
