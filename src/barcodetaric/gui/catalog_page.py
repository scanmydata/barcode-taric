"""Σελίδα κεντρικής βάσης γνώσης: γρήγορο FTS search + CRUD (barcode/περιγραφή/TARIC)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .. import repo
from .widgets import configure_table, h1, muted


class CatalogPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._ids: list[int] = []

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

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Barcode", "Περιγραφή (EL)", "Description (EN)", "TARIC", "Πηγή", "✔"])
        configure_table(self.table, stretch=[1, 2])
        root.addWidget(self.table)

        actions = QHBoxLayout()
        del_btn = QPushButton("Διαγραφή")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self.delete_selected)
        actions.addStretch(1)
        actions.addWidget(del_btn)
        root.addLayout(actions)

        self.reload()

    def reload(self) -> None:
        query = self.search.text().strip()
        items = repo.search_catalog(query) if query else repo.list_catalog()
        self._ids = [it.id for it in items]
        self.table.setRowCount(len(items))
        for row, it in enumerate(items):
            self.table.setItem(row, 0, QTableWidgetItem(it.barcode))
            self.table.setItem(row, 1, QTableWidgetItem(it.description_el))
            self.table.setItem(row, 2, QTableWidgetItem(it.description_en))
            self.table.setItem(row, 3, QTableWidgetItem(it.taric_code))
            self.table.setItem(row, 4, QTableWidgetItem(it.taric_source))
            self.table.setItem(row, 5, QTableWidgetItem("✔" if it.verified else ""))

    def delete_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        item_id = self._ids[rows[0].row()]
        if QMessageBox.question(self, "Διαγραφή", "Διαγραφή εγγραφής από τη βάση γνώσης;") == QMessageBox.Yes:
            repo.delete_catalog_item(item_id)
            self.reload()
