"""Σελίδα κωδικολογίου ενός πελάτη.

Λειτουργίες: import Excel/CSV, add-by-barcode (με web/AI lookup), add-by-description,
αντιστοίχιση όλων των εκκρεμών (async), επιβεβαίωση (verified -> training label),
export. Κάθε νέα εγγραφή τροφοδοτεί και την κεντρική βάση γνώσης (catalog).
"""

from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QCheckBox,
)

from .. import db, repo
from ..engine import resolve
from ..engine.barcode_sources import looks_like_barcode
from ..excel import exporter, reader
from ..models import CatalogItem, ClientItem
from .import_dialog import ImportMappingDialog
from .widgets import BusyOverlay, NumericItem, configure_table, h1, muted
from .workers import run_async

_ID_ROLE = Qt.UserRole + 1


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

        # --- γραμμή επιλογής (select-all / refresh) ---
        selrow = QHBoxLayout()
        self.select_all_cb = QCheckBox("Επιλογή όλων")
        self.select_all_cb.stateChanged.connect(self._on_select_all_toggle)
        refresh_btn = QPushButton("🔄 Ανανέωση")
        refresh_btn.setToolTip("Ανανέωση πίνακα (αν δεν ενημερώθηκε αυτόματα)")
        refresh_btn.clicked.connect(self.reload)
        selrow.addWidget(self.select_all_cb)
        selrow.addWidget(refresh_btn)
        selrow.addStretch(1)
        self.sel_count_lbl = muted("")
        selrow.addWidget(self.sel_count_lbl)
        root.addLayout(selrow)

        # --- πίνακας ---
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["☑", "Barcode", "Περιγραφή (EL)", "Description (EN)", "TARIC", "HS4", "Πηγή", "Βεβ.", "✔"])
        configure_table(self.table, stretch=[2, 3])
        self.table.itemDoubleClicked.connect(lambda *_: self.edit_selected())
        self.table.itemChanged.connect(self._on_item_changed)
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

        self._busy = BusyOverlay(self)

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
        self._loading = True                  # μη πυροδοτείς _on_item_changed κατά το γέμισμα
        self.table.setSortingEnabled(False)   # μη αναδιατάσσεις κατά το γέμισμα
        self.table.setRowCount(len(items))
        for row, it in enumerate(items):
            self._set_row(row, it)
        self.table.setSortingEnabled(True)
        self._loading = False
        self.select_all_cb.blockSignals(True)
        self.select_all_cb.setChecked(False)
        self.select_all_cb.blockSignals(False)
        self._update_sel_count()
        stats = repo.client_stats(self._client_id)
        self.stats_lbl.setText(
            f"Σύνολο: {stats['total']} · Με TARIC: {stats['matched']} · "
            f"Εκκρεμή: {stats['unmatched']} · Επιβεβαιωμένα: {stats['verified']}")

    def _set_row(self, row: int, it: ClientItem) -> None:
        check_item = QTableWidgetItem()
        check_item.setFlags(
            (Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable))
        check_item.setCheckState(Qt.Unchecked)
        check_item.setData(_ID_ROLE, it.id)   # id στη γραμμή -> ανθεκτικό σε sorting
        self.table.setItem(row, 0, check_item)
        self.table.setItem(row, 1, QTableWidgetItem(it.barcode))
        self.table.setItem(row, 2, QTableWidgetItem(it.description_el or it.description_en))
        self.table.setItem(row, 3, QTableWidgetItem(it.description_en or it.description_el))
        self.table.setItem(row, 4, QTableWidgetItem(it.taric_code))
        self.table.setItem(row, 5, QTableWidgetItem(it.hs4))
        self.table.setItem(row, 6, QTableWidgetItem(it.taric_source))
        self.table.setItem(row, 7, NumericItem(f"{it.confidence:.2f}" if it.confidence else "0"))
        self.table.setItem(row, 8, QTableWidgetItem("✔" if it.verified else ""))

    # ------------------------------------------------------ selection ----
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if getattr(self, "_loading", False) or item.column() != 0:
            return
        self._update_sel_count()

    def _on_select_all_toggle(self, state: int) -> None:
        checked = Qt.CheckState(state) == Qt.Checked
        self._loading = True
        for row in range(self.table.rowCount()):
            it = self.table.item(row, 0)
            if it is not None:
                it.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self._loading = False
        self._update_sel_count()

    def _update_sel_count(self) -> None:
        n = len(self._checked_ids())
        self.sel_count_lbl.setText(f"{n} επιλεγμένα" if n else "")

    def _checked_ids(self) -> list[int]:
        out = []
        for row in range(self.table.rowCount()):
            it = self.table.item(row, 0)
            if it is not None and it.checkState() == Qt.Checked:
                out.append(int(it.data(_ID_ROLE)))
        return out

    def _selected_item(self) -> ClientItem | None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        item = self.table.item(rows[0].row(), 0)
        if item is None:
            return None
        return repo.get_client_item(item.data(_ID_ROLE))

    def selected_items(self) -> list[ClientItem]:
        """Όλα τα επιλεγμένα είδη (multi-select) — για μαζικές ενέργειες."""
        out = []
        for idx in self.table.selectionModel().selectedRows():
            item = self.table.item(idx.row(), 0)
            if item is not None:
                ci = repo.get_client_item(item.data(_ID_ROLE))
                if ci:
                    out.append(ci)
        return out

    def _target_ids(self) -> list[int]:
        """IDs για μαζικές ενέργειες: πρώτα τα checked, αλλιώς οι επιλεγμένες γραμμές."""
        ids = self._checked_ids()
        if ids:
            return ids
        return [ci.id for ci in self.selected_items()]

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
            brand=res.brand, quantity=res.quantity, categories=res.categories,
            analysis=res.analysis, catalog_id=cat_id,
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
        # 1) Ανάλυση στηλών + διάλογος αντιστοίχισης (auto-detect + επιλογή extra στηλών).
        try:
            preview = reader.preview_columns(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Import", f"Αποτυχία ανάγνωσης: {exc}")
            return
        if not preview.n_cols:
            QMessageBox.information(self, "Import", "Δεν βρέθηκαν γραμμές.")
            return
        dlg = ImportMappingDialog(preview, parent=self)
        if not dlg.exec():
            return
        mapping = dlg.mapping()
        extra_cols = dlg.extra_cols()
        has_header = dlg.has_header()
        if mapping.get("barcode") is None and mapping.get("description") is None:
            QMessageBox.warning(self, "Import", "Επιλέξτε τουλάχιστον στήλη barcode ή περιγραφής.")
            return
        client_id = self._client_id
        self._busy.start("Εισαγωγή δεδομένων…")
        run_async(self, _import_job, path, client_id, mapping, extra_cols, has_header,
                  on_done=self._on_import_done, on_error=self._on_busy_error,
                  on_progress=self._busy.set_message)

    def _on_import_done(self, count: int) -> None:
        self._busy.stop()
        self.reload()
        QMessageBox.information(self, "Import", f"Εισήχθησαν {count} γραμμές.\n"
                               "(Κρατήθηκε αυτόματο αντίγραφο ασφαλείας.)")

    def _on_busy_error(self, message: str) -> None:
        self._busy.stop()
        self._on_error(message)

    # -------------------------------------------------------- match / edit ----
    def match_all(self) -> None:
        if self._client_id is None:
            return
        pending = repo.list_client_items(self._client_id, only_unmatched=True)
        if not pending:
            QMessageBox.information(self, "Αντιστοίχιση", "Δεν υπάρχουν εκκρεμή είδη.")
            return
        # Για 4k-10k κωδικούς το AI-ανά-είδος είναι ώρες + rate limits· δίνουμε επιλογή:
        #   «Γρήγορη» = FTS + semantic (χωρίς AI), «Ακριβής» = με AI (για μικρά σύνολα/review).
        box = QMessageBox(self)
        box.setWindowTitle("Αντιστοίχιση όλων")
        box.setText(f"Θα αντιστοιχιστούν {len(pending)} εκκρεμή είδη.\n\n"
                    "• Ακριβής (AI): batch — πολλά προϊόντα ανά κλήση AI, το AI διαβάζει "
                    "ελληνικά απευθείας. ~15-20′ για 10k. Συνιστάται.\n"
                    "• Γρήγορη: offline (FTS + εννοιολογικό), χωρίς AI — πρόχειρο draft.")
        ai_btn = box.addButton("🎯 Ακριβής (Batch-AI)", QMessageBox.AcceptRole)
        fast_btn = box.addButton("⚡ Γρήγορη (offline)", QMessageBox.AcceptRole)
        box.addButton("Άκυρο", QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked not in (fast_btn, ai_btn):
            return
        use_ai = clicked is ai_btn
        client_id = self._client_id
        self._busy.start(f"Αντιστοίχιση {len(pending)} ειδών…")
        run_async(self, _match_all_job, client_id, use_ai,
                  on_done=self._on_match_done, on_error=self._on_busy_error,
                  on_progress=self._busy.set_message)

    def _on_match_done(self, count: int) -> None:
        self._busy.stop()
        self.status.setText(f"Ολοκληρώθηκε: {count} αντιστοιχίσεις.")
        self.reload()

    def rematch_selected(self) -> None:
        ids = self._target_ids()
        if not ids:
            item = self._selected_item()
            if item:
                ids = [item.id]
        if not ids:
            QMessageBox.information(self, "Επανα-αντιστοίχιση", "Επιλέξτε είδη (checkbox ή γραμμές).")
            return
        self._busy.start(f"Επανα-αντιστοίχιση {len(ids)} ειδών…")
        run_async(self, _rematch_ids_job, ids,
                  on_done=self._on_rematch_done, on_error=self._on_busy_error,
                  on_progress=self._busy.set_message)

    def _on_rematch_done(self, n: int) -> None:
        self._busy.stop()
        self.status.setText(f"Έτοιμο: {n} αντιστοιχίσεις.")
        self.reload()

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
        ids = self._target_ids()
        if not ids:
            item = self._selected_item()
            if item:
                ids = [item.id]
        if not ids:
            QMessageBox.information(self, "Επιβεβαίωση", "Επιλέξτε είδη (checkbox ή γραμμές).")
            return
        done, skipped = 0, 0
        for iid in ids:
            item = repo.get_client_item(iid)
            if not item or not item.taric_code:
                skipped += 1
                continue
            repo.set_item_verified(item.id, 1)
            repo.upsert_catalog(CatalogItem(
                barcode=item.barcode, description_el=item.description_el,
                description_en=item.description_en, taric_code=item.taric_code, hs4=item.hs4,
                taric_description=item.taric_description, taric_source=item.taric_source,
                verified=1, source="verified"))
            done += 1
        msg = f"Επιβεβαιώθηκαν {done} — θα χρησιμοποιηθούν στην εκπαίδευση του μοντέλου."
        if skipped:
            msg += f" ({skipped} χωρίς TARIC παραλείφθηκαν)"
        self.status.setText(msg)
        self.reload()

    def delete_selected(self) -> None:
        ids = self._target_ids()
        if not ids:
            item = self._selected_item()
            if item:
                ids = [item.id]
        if not ids:
            QMessageBox.information(self, "Διαγραφή", "Επιλέξτε είδη (checkbox ή γραμμές).")
            return
        if len(ids) > 1:
            confirm = QMessageBox.question(
                self, "Διαγραφή", f"Διαγραφή {len(ids)} ειδών;")
            if confirm != QMessageBox.Yes:
                return
        repo.delete_client_items(ids)
        self.reload()

    def export(self) -> None:
        if self._client_id is None:
            return
        dlg = _ExportDialog(parent=self)
        if not dlg.exec():
            return
        include_extra = dlg.include_extra()
        client = repo.get_client(self._client_id)
        default = f"kodikologio_{(client.name if client else 'client').replace(' ', '_')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export κωδικολογίου", default, "Excel (*.xlsx);;CSV (*.csv)")
        if not path:
            return
        try:
            db.backup_db("export")        # αυτόματο backup πριν την εξαγωγή
            n = exporter.export(self._client_id, path, include_extra=include_extra)
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


class _ExportDialog(QDialog):
    """Βοηθός εξαγωγής: εξηγεί τι εξάγεται & αν θα μπουν οι επιπλέον στήλες."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Εξαγωγή κωδικολογίου")
        self.setMinimumWidth(520)
        root = QVBoxLayout(self)
        root.setSpacing(10)
        info = QLabel(
            "Θα εξαχθούν οι βασικές στήλες:\n"
            "• Barcode, Περιγραφή (EL/EN), TARIC, HS4\n"
            "• Περιγραφή TARIC, Βεβαιότητα, Πηγή, Αιτιολόγηση, Επιβεβαιωμένο\n\n"
            "Στο επόμενο βήμα επιλέγετε όνομα & τύπο αρχείου (Excel ή CSV).")
        info.setWordWrap(True)
        root.addWidget(info)
        self.chk_extra = QCheckBox(
            "Να συμπεριληφθούν και οι επιπλέον στήλες του αρχικού Excel "
            "(κωδικοί/λεπτομέρειες που κρατήθηκαν κατά το import)")
        self.chk_extra.setChecked(True)
        root.addWidget(self.chk_extra)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Συνέχεια")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def include_extra(self) -> bool:
        return self.chk_extra.isChecked()


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
        source=res.source, brand=res.brand, quantity=res.quantity, categories=res.categories,
        analysis=res.analysis))


def _apply_match(item: ClientItem, m) -> None:
    item.taric_code = m.taric_code
    item.hs4 = m.hs4
    item.taric_description = m.taric_description
    item.confidence = m.confidence
    item.ai_rationale = m.ai_rationale
    item.taric_source = m.taric_source


def _match_items(items: list[ClientItem], use_ai: bool, progress=None) -> int:
    """Αντιστοιχίζει λίστα ειδών· γράφει σε ΜΙΑ bulk transaction στο τέλος (ταχύτητα σε 10k).

    - use_ai=True  => BATCH-AI (`taric_match.match_batch`): πολλά προϊόντα ανά κλήση AI,
      ακρίβεια AI, ~500 κλήσεις για 10k. Το AI διαβάζει ελληνικά (χωρίς per-item μετάφραση).
    - use_ai=False => `fast` offline μονοπάτι (FTS + semantic, χωρίς δίκτυο/AI) — πρόχειρο.
    """
    from ..engine import taric_match
    total = len(items)
    updated: list[ClientItem] = []

    if use_ai:
        payload = [{"description_el": it.description_el, "description_en": it.description_en,
                    "barcode": it.barcode, "brand": it.brand, "quantity": it.quantity,
                    "categories": it.categories, "analysis": it.analysis, "source": it.source}
                   for it in items]
        matches = taric_match.match_batch(payload, progress=progress)
        for item, m in zip(items, matches):
            if m.taric_code:
                _apply_match(item, m)
                updated.append(item)
    else:
        step = 10                        # συχνότερη ένδειξη προόδου (να μη φαίνεται κολλημένο)
        for i, item in enumerate(items, 1):
            if progress and (i <= 2 or i % step == 0 or i == total):
                pct = int(i / total * 100) if total else 100
                progress(f"Αντιστοίχιση {i}/{total} ({pct}%): {item.description_el or item.barcode}")
            m = taric_match.match(item.description_el, item.description_en, barcode=item.barcode,
                                  brand=item.brand, quantity=item.quantity,
                                  categories=item.categories, use_ai=False, fast=True)
            if m.taric_code:
                _apply_match(item, m)
                updated.append(item)

    if progress:
        progress(f"Αποθήκευση {len(updated)} αντιστοιχίσεων…")
    repo.bulk_update_client_items(updated)
    return len(updated)


def _rematch_ids_job(item_ids: list[int], progress=None) -> int:
    items = [it for it in (repo.get_client_item(i) for i in item_ids) if it]
    # Επανα-αντιστοίχιση = ρητή ενέργεια χρήστη σε επιλεγμένα -> χρήση AI για ακρίβεια.
    return _match_items(items, use_ai=True, progress=progress)


def _match_all_job(client_id: int, use_ai: bool = True, progress=None) -> int:
    pending = repo.list_client_items(client_id, only_unmatched=True)
    return _match_items(pending, use_ai=use_ai, progress=progress)


def _import_job(path: str, client_id: int, mapping: dict, extra_cols: list,
                has_header: bool, progress=None) -> int:
    if progress:
        progress("Δημιουργία αντιγράφου ασφαλείας…")
    db.backup_db("import")
    if progress:
        progress("Ανάγνωση αρχείου…")
    rows = reader.read_with_mapping(path, mapping, extra_cols, has_header)
    if not rows:
        return 0
    items, catalog_items = [], []
    for r in rows:
        desc_el = r.description if _is_greek(r.description) else ""
        desc_en = r.description if not _is_greek(r.description) else ""
        hs4 = r.taric_code[:4] if r.taric_code else ""
        src = "manual" if r.taric_code else ""
        extra_json = json.dumps(r.extra, ensure_ascii=False) if r.extra else ""
        items.append(ClientItem(
            client_id=client_id, barcode=r.barcode,
            description_el=desc_el, description_en=desc_en,
            taric_code=r.taric_code, hs4=hs4, taric_source=src, source="excel",
            extra=extra_json))
        catalog_items.append(CatalogItem(
            barcode=r.barcode, description_el=desc_el, description_en=desc_en,
            taric_code=r.taric_code, hs4=hs4, taric_source=src, source="excel"))
    if progress:
        progress(f"Αποθήκευση {len(items)} γραμμών…")
    repo.bulk_upsert_client_items(items)
    repo.bulk_upsert_catalog(catalog_items)
    return len(rows)
