"""Export κωδικολογίου πελάτη με τους αντιστοιχισμένους TARIC (xlsx/csv)."""

from __future__ import annotations

import csv
from pathlib import Path

from .. import repo

HEADERS = ["Barcode", "Περιγραφή (EL)", "Description (EN)", "TARIC", "HS4",
           "Περιγραφή TARIC", "Βεβαιότητα", "Πηγή", "Αιτιολόγηση", "Επιβεβαιωμένο"]


def _rows_for_client(client_id: int) -> list[list[str]]:
    items = repo.list_client_items(client_id)
    out = []
    for it in items:
        out.append([
            it.barcode, it.description_el, it.description_en, it.taric_code, it.hs4,
            it.taric_description, f"{it.confidence:.2f}" if it.confidence else "",
            it.taric_source, it.ai_rationale, "Ναι" if it.verified else "Όχι",
        ])
    return out


def export_xlsx(client_id: int, path: str | Path) -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Κωδικολόγιο"
    ws.append(HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    rows = _rows_for_client(client_id)
    for r in rows:
        ws.append(r)
    # Auto-width (best-effort).
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(60, width + 2)
    wb.save(path)
    return len(rows)


def export_csv(client_id: int, path: str | Path) -> int:
    rows = _rows_for_client(client_id)
    with Path(path).open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADERS)
        writer.writerows(rows)
    return len(rows)


def export(client_id: int, path: str | Path) -> int:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return export_csv(client_id, path)
    return export_xlsx(client_id, path)
