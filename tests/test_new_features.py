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
