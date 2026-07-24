"""Σελίδα κωδικολογίου ενός πελάτη.

Λειτουργίες: import Excel/CSV, add-by-barcode (με web/AI lookup), add-by-description,
αντιστοίχιση όλων των εκκρεμών (async), επιβεβαίωση (verified -> training label),
export. Κάθε νέα εγγραφή τροφοδοτεί και την κεντρική βάση γνώσης (catalog).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QCheckBox,
)

from .. import repo
from ..engine import resolve
from ..engine.barcode_sources import looks_like_barcode
from ..excel import exporter, reader
from ..models import CatalogItem, ClientItem
from .widgets import configure_table, h1, muted
from .workers import run_async


class CodebookPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._client_id: int | None = None
        self._ids: list[int] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        top = QHBoxLayout()
        self.back_btn = QPushButton("←  Πελάτες")
        self.back_btn.setFixedWidth(120)
        top.addWidget(self.back_btn)
        self.title = h1("Κωδικολόγιο")
        top.addWidget(self.title)
        top.addStretch(1)
        self.stats_lbl = muted("—")
        top.addWidget(self.stats_lbl)
        root.addLayout(top)

        # --- γραμμή εργαλείων ---
        tools = QHBoxLayout()
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Barcode ή περιγραφή προϊόντος…")
        self.barcode_input.returnPressed.connect(self.add_from_input)
        add_btn = QPushButton("＋ Προσθήκη")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self.add_from_input)
        import_btn = QPushButton("📥 Import Excel")
        import_btn.clicked.connect(self.import_excel)
        match_btn = QPushButton("🎯 Αντιστοίχιση όλων")
        match_btn.clicked.connect(self.match_all)
        export_btn = QPushButton("📤 Export")
        export_btn.clicked.connect(self.export)
        tools.addWidget(self.barcode_input, 2)
        tools.addWidget(add_btn)
        tools.addWidget(import_btn)
        tools.addWidget(match_btn)
        tools.addWidget(export_btn)
        root.addLayout(tools)

        # --- πίνακας ---
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["Barcode", "Περιγραφή (EL)", "Description (EN)", "TARIC", "HS4", "Πηγή", "Βεβ.", "✔"])
        configure_table(self.table, stretch=[1, 2])
        self.table.itemDoubleClicked.connect(lambda *_: self.edit_selected())
        root.addWidget(self.table)

        bottom = QHBoxLayout()
        verify_btn = QPushButton("✔ Επιβεβαίωση (training)")
        verify_btn.clicked.connect(self.verify_selected)
        edit_btn = QPushButton("Επεξεργασία")
        edit_btn.clicked.connect(self.edit_selected)
        rematch_btn = QPushButton("Επανα-αντιστοίχιση")
        rematch_btn.clicked.connect(self.rematch_selected)
        del_btn = QPushButton("Διαγραφή")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self.delete_selected)
        bottom.addWidget(verify_btn)
        bottom.addWidget(rematch_btn)
        bottom.addWidget(edit_btn)
        bottom.addWidget(del_btn)
        bottom.addStretch(1)
        self.status = muted("")
        bottom.addWidget(self.status)
        root.addLayout(bottom)

    # ------------------------------------------------------------- data ----
    def load_client(self, client_id: int) -> None:
        self._client_id = client_id
        client = repo.get_client(client_id)
        self.title.setText(f"Κωδικολόγιο — {client.name}" if client else "Κωδικολόγιο")
        self.reload()

    def reload(self) -> None:
        if self._client_id is None:
            return
        items = repo.list_client_items(self._client_id)
        self._ids = [it.id for it in items]
        self.table.setRowCount(len(items))
        for row, it in enumerate(items):
            self._set_row(row, it)
        stats = repo.client_stats(self._client_id)
        self.stats_lbl.setText(
            f"Σύνολο: {stats['total']} · Με TARIC: {stats['matched']} · "
            f"Εκκρεμή: {stats['unmatched']} · Επιβεβαιωμένα: {stats['verified']}")

    def _set_row(self, row: int, it: ClientItem) -> None:
        self.table.setItem(row, 0, QTableWidgetItem(it.barcode))
        self.table.setItem(row, 1, QTableWidgetItem(it.description_el or it.description_en))
        self.table.setItem(row, 2, QTableWidgetItem(it.description_en or it.description_el))
        self.table.setItem(row, 3, QTableWidgetItem(it.taric_code))
        self.table.setItem(row, 4, QTableWidgetItem(it.hs4))
        self.table.setItem(row, 5, QTableWidgetItem(it.taric_source))
        self.table.setItem(row, 6, QTableWidgetItem(f"{it.confidence:.2f}" if it.confidence else ""))
        self.table.setItem(row, 7, QTableWidgetItem("✔" if it.verified else ""))

    def _selected_item(self) -> ClientItem | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        return repo.get_client_item(self._ids[rows[0].row()])

    # ---------------------------------------------------------- add flows ----
    def add_from_input(self) -> None:
        if self._client_id is None:
            return
        text = self.barcode_input.text().strip()
        if not text:
            return
        self.barcode_input.clear()
        self.status.setText("Αναζήτηση…")
        is_barcode = looks_like_barcode(text)
        fn = (lambda: resolve.resolve_barcode(text)) if is_barcode else (lambda: resolve.resolve_description(text))
        run_async(self, fn, on_done=self._on_resolved, on_error=self._on_error,
                  on_progress=self.status.setText)

    def _on_resolved(self, res: resolve.ResolveResult) -> None:
        if self._client_id is None:
            return
        cat_id = _upsert_catalog(res)
        item = ClientItem(
            client_id=self._client_id, barcode=res.barcode, description_el=res.description_el,
            description_en=res.description_en, taric_code=res.taric_code, hs4=res.hs4,
            taric_description=res.taric_description, confidence=res.confidence,
            ai_rationale=res.ai_rationale, taric_source=res.taric_source, source=res.source,
            brand=res.brand, quantity=res.quantity, categories=res.categories, catalog_id=cat_id,
        )
        repo.upsert_client_item(item)
        self.status.setText(
            f"Προστέθηκε: {res.description_el or res.description_en} → {res.taric_code or '—'}")
        self.reload()

    def _on_error(self, message: str) -> None:
        self.status.setText("Σφάλμα.")
        QMessageBox.warning(self, "Σφάλμα", message.splitlines()[0])

    def import_excel(self) -> None:
        if self._client_id is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Επιλογή αρχείου κωδικολογίου", "",
            "Υποστηριζόμενα (*.xlsx *.xlsm *.csv *.tsv *.txt)")
        if not path:
            return
        try:
            rows = reader.read_codebook(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Import", f"Αποτυχία ανάγνωσης: {exc}")
            return
        if not rows:
            QMessageBox.information(self, "Import", "Δεν βρέθηκαν γραμμές.")
            return
        for r in rows:
            item = ClientItem(
                client_id=self._client_id, barcode=r.barcode,
                description_el=r.description if _is_greek(r.description) else "",
                description_en=r.description if not _is_greek(r.description) else "",
                taric_code=r.taric_code, hs4=r.taric_code[:4] if r.taric_code else "",
                taric_source="manual" if r.taric_code else "", source="excel",
            )
            repo.upsert_client_item(item)
            repo.upsert_catalog(CatalogItem(
                barcode=r.barcode, description_el=item.description_el,
                description_en=item.description_en, taric_code=r.taric_code,
                hs4=item.hs4, taric_source=item.taric_source, source="excel"))
        self.reload()
        QMessageBox.information(self, "Import", f"Εισήχθησαν {len(rows)} γραμμές.")

    # -------------------------------------------------------- match / edit ----
    def match_all(self) -> None:
        if self._client_id is None:
            return
        pending = repo.list_client_items(self._client_id, only_unmatched=True)
        if not pending:
            QMessageBox.information(self, "Αντιστοίχιση", "Δεν υπάρχουν εκκρεμή είδη.")
            return
        client_id = self._client_id
        self.status.setText(f"Αντιστοίχιση {len(pending)} ειδών…")
        run_async(self, _match_all_job, client_id,
                  on_done=self._on_match_done, on_error=self._on_error,
                  on_progress=self.status.setText)

    def _on_match_done(self, count: int) -> None:
        self.status.setText(f"Ολοκληρώθηκε: {count} αντιστοιχίσεις.")
        self.reload()

    def rematch_selected(self) -> None:
        item = self._selected_item()
        if not item:
            return
        self.status.setText("Επανα-αντιστοίχιση…")
        run_async(self, _match_single_job, item.id,
                  on_done=lambda _: (self.status.setText("Έτοιμο."), self.reload()),
                  on_error=self._on_error, on_progress=self.status.setText)

    def edit_selected(self) -> None:
        item = self._selected_item()
        if not item:
            return
        dlg = _ItemDialog(item, parent=self)
        if dlg.exec():
            updated = dlg.result_item()
            repo.update_client_item(updated)
            if updated.verified:
                repo.upsert_catalog(CatalogItem(
                    barcode=updated.barcode, description_el=updated.description_el,
                    description_en=updated.description_en, taric_code=updated.taric_code,
                    hs4=updated.hs4, taric_description=updated.taric_description,
                    taric_source=updated.taric_source, verified=1, source="verified"))
            self.reload()

    def verify_selected(self) -> None:
        item = self._selected_item()
        if not item:
            return
        if not item.taric_code:
            QMessageBox.information(self, "Επιβεβαίωση", "Το είδος δεν έχει TARIC ακόμη.")
            return
        repo.set_item_verified(item.id, 1)
        repo.upsert_catalog(CatalogItem(
            barcode=item.barcode, description_el=item.description_el,
            description_en=item.description_en, taric_code=item.taric_code, hs4=item.hs4,
            taric_description=item.taric_description, taric_source=item.taric_source,
            verified=1, source="verified"))
        self.status.setText("Επιβεβαιώθηκε — θα χρησιμοποιηθεί στην εκπαίδευση του μοντέλου.")
        self.reload()

    def delete_selected(self) -> None:
        item = self._selected_item()
        if not item:
            return
        repo.delete_client_item(item.id)
        self.reload()

    def export(self) -> None:
        if self._client_id is None:
            return
        client = repo.get_client(self._client_id)
        default = f"kodikologio_{(client.name if client else 'client').replace(' ', '_')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export κωδικολογίου", default, "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        try:
            n = exporter.export(self._client_id, path)
            QMessageBox.information(self, "Export", f"Εξήχθησαν {n} γραμμές στο\n{path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export", f"Αποτυχία: {exc}")


# ------------------------------------------------------------ item dialog ----

class _ItemDialog(QDialog):
    def __init__(self, item: ClientItem, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Επεξεργασία είδους")
        self.setMinimumWidth(460)
        self._item = item

        root = QVBoxLayout(self)
        form = QFormLayout()
        self.barcode = QLineEdit(item.barcode)
        self.desc_el = QLineEdit(item.description_el)
        self.desc_en = QLineEdit(item.description_en)
        self.taric = QLineEdit(item.taric_code)
        self.taric_desc = QTextEdit(item.taric_description)
        self.taric_desc.setFixedHeight(60)
        self.verified = QCheckBox("Επιβεβαιωμένο (χρήση στην εκπαίδευση ML)")
        self.verified.setChecked(bool(item.verified))
        form.addRow("Barcode", self.barcode)
        form.addRow("Περιγραφή (EL)", self.desc_el)
        form.addRow("Description (EN)", self.desc_en)
        form.addRow("TARIC", self.taric)
        form.addRow("Περιγραφή TARIC", self.taric_desc)
        form.addRow("", self.verified)
        root.addLayout(form)

        if item.ai_rationale:
            rat = QLabel(f"Αιτιολόγηση: {item.ai_rationale}")
            rat.setObjectName("muted")
            rat.setWordWrap(True)
            root.addWidget(rat)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def result_item(self) -> ClientItem:
        self._item.barcode = self.barcode.text().strip()
        self._item.description_el = self.desc_el.text().strip()
        self._item.description_en = self.desc_en.text().strip()
        new_taric = self.taric.text().strip()
        if new_taric != self._item.taric_code:
            self._item.taric_source = "manual"
        self._item.taric_code = new_taric
        self._item.hs4 = new_taric[:4] if new_taric else ""
        self._item.taric_description = self.taric_desc.toPlainText().strip()
        self._item.verified = 1 if self.verified.isChecked() else 0
        return self._item


# --------------------------------------------------------------- helpers ----

def _is_greek(text: str) -> bool:
    import re
    return bool(re.search("[Ͱ-Ͽἀ-῿]", text or ""))


def _upsert_catalog(res: resolve.ResolveResult) -> int | None:
    if not res.barcode and not (res.description_el or res.description_en):
        return None
    return repo.upsert_catalog(CatalogItem(
        barcode=res.barcode, description_el=res.description_el, description_en=res.description_en,
        taric_code=res.taric_code, hs4=res.hs4, taric_description=res.taric_description,
        confidence=res.confidence, ai_rationale=res.ai_rationale, taric_source=res.taric_source,
        source=res.source, brand=res.brand, quantity=res.quantity, categories=res.categories))


def _match_single_job(item_id: int, progress=None) -> bool:
    from ..engine import taric_match
    item = repo.get_client_item(item_id)
    if not item:
        return False
    m = taric_match.match(item.description_el, item.description_en, barcode=item.barcode,
                          brand=item.brand, quantity=item.quantity, categories=item.categories)
    item.taric_code = m.taric_code
    item.hs4 = m.hs4
    item.taric_description = m.taric_description
    item.confidence = m.confidence
    item.ai_rationale = m.ai_rationale
    item.taric_source = m.taric_source
    repo.update_client_item(item)
    return True


def _match_all_job(client_id: int, progress=None) -> int:
    from ..engine import taric_match
    pending = repo.list_client_items(client_id, only_unmatched=True)
    done = 0
    for i, item in enumerate(pending, 1):
        if progress:
            progress(f"Αντιστοίχιση {i}/{len(pending)}: {item.description_el or item.barcode}")
        m = taric_match.match(item.description_el, item.description_en, barcode=item.barcode,
                              brand=item.brand, quantity=item.quantity, categories=item.categories)
        if m.taric_code:
            item.taric_code = m.taric_code
            item.hs4 = m.hs4
            item.taric_description = m.taric_description
            item.confidence = m.confidence
            item.ai_rationale = m.ai_rationale
            item.taric_source = m.taric_source
            repo.update_client_item(item)
            done += 1
    return done
