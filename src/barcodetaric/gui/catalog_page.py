"""Σελίδα κεντρικής βάσης γνώσης: γρήγορο FTS search + CRUD (barcode/περιγραφή/TARIC)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import repo
from .widgets import configure_table, h1, muted

_ID_ROLE = Qt.UserRole + 1


class CatalogPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ids: list[int] = []
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(h1("Βάση γνώσης"))
        top.addStretch(1)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Αναζήτηση barcode ή περιγραφής…")
        self.search.setFixedWidth(320)
        self.search.textChanged.connect(self.reload)
        top.addWidget(self.search)
        root.addLayout(top)

        root.addWidget(muted(
            "Συσσωρευμένη γνώση από όλους τους πελάτες: barcode → περιγραφή → TARIC. "
            "Τα επιβεβαιωμένα (✔) τροφοδοτούν το τοπικό μοντέλο ML."))

        # --- γραμμή επιλογής (select-all / refresh) ---
        selrow = QHBoxLayout()
        self.select_all_cb = QCheckBox("Επιλογή όλων")
        self.select_all_cb.stateChanged.connect(self._on_select_all_toggle)
        refresh_btn = QPushButton("🔄 Ανανέωση")
        refresh_btn.clicked.connect(self.reload)
        selrow.addWidget(self.select_all_cb)
        selrow.addWidget(refresh_btn)
        selrow.addStretch(1)
        self.sel_count_lbl = muted("")
        selrow.addWidget(self.sel_count_lbl)
        root.addLayout(selrow)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["☑", "Barcode", "Περιγραφή (EL)", "Description (EN)", "TARIC", "Πηγή", "✔"])
        configure_table(self.table, stretch=[2, 3])
        self.table.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.table)

        actions = QHBoxLayout()
        del_btn = QPushButton("Διαγραφή επιλεγμένων")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self.delete_selected)
        actions.addStretch(1)
        actions.addWidget(del_btn)
        root.addLayout(actions)

        self.reload()

    def reload(self) -> None:
        query = self.search.text().strip()
        items = repo.search_catalog(query) if query else repo.list_catalog()
        self._loading = True
        self.table.setSortingEnabled(False)   # μη αναδιατάσσεις κατά το γέμισμα
        self.table.setRowCount(len(items))
        for row, it in enumerate(items):
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            check_item.setCheckState(Qt.Unchecked)
            check_item.setData(_ID_ROLE, it.id)   # id στη γραμμή -> ανθεκτικό σε sorting
            self.table.setItem(row, 0, check_item)
            self.table.setItem(row, 1, QTableWidgetItem(it.barcode))
            self.table.setItem(row, 2, QTableWidgetItem(it.description_el))
            self.table.setItem(row, 3, QTableWidgetItem(it.description_en))
            self.table.setItem(row, 4, QTableWidgetItem(it.taric_code))
            self.table.setItem(row, 5, QTableWidgetItem(it.taric_source))
            self.table.setItem(row, 6, QTableWidgetItem("✔" if it.verified else ""))
        self.table.setSortingEnabled(True)
        self._loading = False
        self.select_all_cb.blockSignals(True)
        self.select_all_cb.setChecked(False)
        self.select_all_cb.blockSignals(False)
        self._update_sel_count()

    # ------------------------------------------------------ selection ----
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 0:
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

    def _checked_ids(self) -> list[int]:
        out = []
        for row in range(self.table.rowCount()):
            it = self.table.item(row, 0)
            if it is not None and it.checkState() == Qt.Checked:
                out.append(int(it.data(_ID_ROLE)))
        return out

    def _update_sel_count(self) -> None:
        n = len(self._checked_ids())
        self.sel_count_lbl.setText(f"{n} επιλεγμένα" if n else "")

    def _target_ids(self) -> list[int]:
        ids = self._checked_ids()
        if ids:
            return ids
        # fallback: επιλεγμένες γραμμές
        out = []
        for idx in self.table.selectionModel().selectedRows():
            it = self.table.item(idx.row(), 0)
            if it is not None:
                out.append(int(it.data(_ID_ROLE)))
        return out

    def delete_selected(self) -> None:
        ids = self._target_ids()
        if not ids:
            QMessageBox.information(self, "Διαγραφή", "Επιλέξτε εγγραφές (checkbox ή γραμμές).")
            return
        msg = ("Διαγραφή εγγραφής από τη βάση γνώσης;" if len(ids) == 1
               else f"Διαγραφή {len(ids)} εγγραφών από τη βάση γνώσης;")
        if QMessageBox.question(self, "Διαγραφή", msg) == QMessageBox.Yes:
            for iid in ids:
                repo.delete_catalog_item(iid)
            self.reload()
