from barcodetaric import repo
from barcodetaric.models import CatalogItem, Client, ClientItem


def test_client_crud():
    cid = repo.create_client(Client(name="Οξυγόνο ΑΕ", vat="094000000"))
    assert cid > 0
    client = repo.get_client(cid)
    assert client and client.name == "Οξυγόνο ΑΕ"

    client.email = "info@example.gr"
    assert repo.update_client(client)
    assert repo.get_client(cid).email == "info@example.gr"

    assert any(c.id == cid for c in repo.list_clients("Οξυγ"))
    assert repo.delete_client(cid)
    assert repo.get_client(cid) is None


def test_client_items_and_stats():
    cid = repo.create_client(Client(name="Test2"))
    repo.upsert_client_item(ClientItem(client_id=cid, barcode="5201111111114",
                                       description_el="καφές", taric_code="0901", hs4="0901"))
    repo.upsert_client_item(ClientItem(client_id=cid, barcode="5202222222227",
                                       description_el="άγνωστο"))
    # upsert ίδιου barcode -> ενημέρωση, όχι διπλή γραμμή
    repo.upsert_client_item(ClientItem(client_id=cid, barcode="5201111111114",
                                       description_el="καφές αλεσμένος", taric_code="0901"))
    items = repo.list_client_items(cid)
    assert len(items) == 2
    stats = repo.client_stats(cid)
    assert stats["total"] == 2 and stats["matched"] == 1 and stats["unmatched"] == 1


def test_catalog_upsert_and_search():
    repo.upsert_catalog(CatalogItem(barcode="4000000000009", description_el="σοκολάτα γάλακτος",
                                    description_en="milk chocolate", taric_code="1806"))
    hit = repo.get_catalog_by_barcode("4000000000009")
    assert hit and hit.taric_code == "1806"
    results = repo.search_catalog("chocolate")
    assert any(r.barcode == "4000000000009" for r in results)


def test_verified_training_rows():
    cid = repo.create_client(Client(name="Train"))
    repo.upsert_client_item(ClientItem(client_id=cid, barcode="1", description_el="νερό",
                                       description_en="water", taric_code="2201", verified=1))
    rows = repo.verified_training_rows()
    assert any(r["taric_code"] == "2201" for r in rows)
