import pytest

from barcodetaric import repo
from barcodetaric.config import SETTINGS
from barcodetaric.engine import ml_classifier
from barcodetaric.models import Client, ClientItem

sklearn = pytest.importorskip("sklearn")


def test_train_and_predict():
    # Χαμήλωσε το κατώφλι δειγμάτων για το test.
    SETTINGS.set("ml_min_samples", 8)
    cid = repo.create_client(Client(name="ML Test"))
    samples = [
        ("καφές αλεσμένος", "ground coffee", "0901"),
        ("καφές espresso", "espresso coffee", "0901"),
        ("στιγμιαίος καφές", "instant coffee", "0901"),
        ("κόκκοι καφέ", "coffee beans", "0901"),
        ("εμφιαλωμένο νερό", "bottled water", "2201"),
        ("μεταλλικό νερό", "mineral water", "2201"),
        ("νερό πηγής", "spring water", "2201"),
        ("ανθρακούχο νερό", "sparkling water", "2201"),
    ]
    for i, (el, en, taric) in enumerate(samples):
        repo.upsert_client_item(ClientItem(client_id=cid, barcode=f"B{i}", description_el=el,
                                           description_en=en, taric_code=taric, hs4=taric,
                                           verified=1))
    result = ml_classifier.retrain()
    assert result.get("trained"), result

    model = ml_classifier.get_model(reload=True)
    assert model.is_ready()
    # Χαμήλωσε το κατώφλι βεβαιότητας για ντετερμινιστικό test.
    SETTINGS.set("ml_confidence_threshold", 0.3)
    pred = model.predict("φρεσκοκομμένος καφές", "fresh coffee")
    assert pred is not None
    assert pred.hs4 == "0901"
