from pathlib import Path

from barcodetaric import repo
from barcodetaric.excel import exporter, reader
from barcodetaric.models import Client, ClientItem


def test_read_codebook_with_headers(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Barcode", "Περιγραφή", "TARIC"])
    ws.append(["5201234567890", "Καφές αλεσμένος", "0901"])
    ws.append(["5209876543210", "Εμφιαλωμένο νερό", ""])
    path = tmp_path / "codebook.xlsx"
    wb.save(path)

    rows = reader.read_codebook(path)
    assert len(rows) == 2
    assert rows[0].barcode == "5201234567890"
    assert "Καφές" in rows[0].description
    assert rows[0].taric_code == "0901"


def test_read_codebook_no_headers(tmp_path):
    path = tmp_path / "raw.csv"
    path.write_text("5201234567890,Καφές\n5209876543210,Νερό\n", encoding="utf-8")
    rows = reader.read_codebook(path)
    assert len(rows) == 2
    assert all(r.barcode and r.description for r in rows)


def test_export_roundtrip(tmp_path):
    cid = repo.create_client(Client(name="Export Test"))
    repo.upsert_client_item(ClientItem(client_id=cid, barcode="5201234567890",
                                       description_el="Καφές", taric_code="0901", hs4="0901",
                                       taric_source="fts", confidence=0.5))
    out = tmp_path / "out.xlsx"
    n = exporter.export(cid, out)
    assert n == 1 and out.is_file()

    from openpyxl import load_workbook
    wb = load_workbook(out)
    ws = wb.active
    assert ws.max_row == 2  # header + 1
    assert ws.cell(1, 1).value == "Barcode"
