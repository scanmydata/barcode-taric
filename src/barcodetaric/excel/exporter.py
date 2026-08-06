"""Export κωδικολογίου πελάτη με τους αντιστοιχισμένους TARIC (xlsx/csv).

Ο χρήστης μπορεί να επιλέξει αν θα εξαχθούν και οι επιπλέον στήλες του αρχικού Excel
(κωδικοί προϊόντος, λεπτομέρειες κ.λπ.) που κρατήθηκαν στο πεδίο `extra` κατά το import.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .. import repo

BASE_HEADERS = ["Barcode", "Περιγραφή (EL)", "Description (EN)", "TARIC", "HS4",
                "Περιγραφή TARIC", "Βεβαιότητα", "Πηγή", "Αιτιολόγηση", "Επιβεβαιωμένο"]


def _base_row(it) -> list[str]:
    return [
        it.barcode, it.description_el, it.description_en, it.taric_code, it.hs4,
        it.taric_description, f"{it.confidence:.2f}" if it.confidence else "",
        it.taric_source, it.ai_rationale, "Ναι" if it.verified else "Όχι",
    ]


def _extra_keys(items) -> list[str]:
    """Ένωση όλων των κλειδιών `extra` (διατηρώντας σειρά πρώτης εμφάνισης)."""
    keys: list[str] = []
    for it in items:
        if not getattr(it, "extra", ""):
            continue
        try:
            data = json.loads(it.extra)
        except (ValueError, TypeError):
            continue
        for k in data:
            if k not in keys:
                keys.append(k)
    return keys


def _extra_values(it, keys: list[str]) -> list[str]:
    try:
        data = json.loads(it.extra) if getattr(it, "extra", "") else {}
    except (ValueError, TypeError):
        data = {}
    return [str(data.get(k, "")) for k in keys]


def _headers_and_rows(client_id: int, include_extra: bool) -> tuple[list[str], list[list[str]]]:
    items = repo.list_client_items(client_id)
    extra_keys = _extra_keys(items) if include_extra else []
    headers = BASE_HEADERS + extra_keys
    rows = [_base_row(it) + (_extra_values(it, extra_keys) if extra_keys else []) for it in items]
    return headers, rows


def export_xlsx(client_id: int, path: str | Path, include_extra: bool = True) -> int:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    headers, rows = _headers_and_rows(client_id, include_extra)
    wb = Workbook()
    ws = wb.active
    ws.title = "Κωδικολόγιο"
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in rows:
        ws.append(r)
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(60, width + 2)
    wb.save(path)
    return len(rows)


def export_csv(client_id: int, path: str | Path, include_extra: bool = True) -> int:
    headers, rows = _headers_and_rows(client_id, include_extra)
    with Path(path).open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
    return len(rows)


def export(client_id: int, path: str | Path, include_extra: bool = True) -> int:
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return export_csv(client_id, path, include_extra)
    return export_xlsx(client_id, path, include_extra)
