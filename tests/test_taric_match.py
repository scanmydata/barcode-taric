import pytest

from barcodetaric import repo
from barcodetaric.engine import taric_match
from barcodetaric.taric import importer


@pytest.fixture(scope="module", autouse=True)
def _seed():
    importer.import_seed()
    assert repo.taric_row_count() >= 10
    # Απομόνωση από τυχόν ML model/threshold που άφησαν άλλα tests: θέλουμε καθαρό FTS.
    from barcodetaric.config import SETTINGS
    from barcodetaric.engine import ml_classifier
    SETTINGS.set("ml_confidence_threshold", 0.55)
    ml_classifier._CACHED = ml_classifier.TaricML()  # άδειο μοντέλο -> ML tier παρακάμπτεται


@pytest.mark.parametrize("el,en,expected", [
    ("καφές", "coffee beans", "0901"),
    ("εμφιαλωμένο νερό", "bottled water", "2201"),
    ("σοκολάτα γάλακτος", "milk chocolate bar", "1806"),
    ("χαρτί υγείας", "toilet paper", "4818"),
])
def test_offline_fts_match(el, en, expected):
    m = taric_match.match(el, en, use_ai=False)
    assert m.taric_code == expected
    assert m.taric_source in ("fts", "ml", "catalog")


def test_catalog_shortcut():
    from barcodetaric.models import CatalogItem
    repo.upsert_catalog(CatalogItem(barcode="9999999999994", description_el="δοκιμή",
                                    taric_code="1905", hs4="1905", verified=1))
    m = taric_match.match("δοκιμή", "", barcode="9999999999994", use_ai=False)
    assert m.taric_code == "1905"
    assert m.taric_source == "catalog"
