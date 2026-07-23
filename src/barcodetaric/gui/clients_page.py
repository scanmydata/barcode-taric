"""Σελίδα πελατολογίου: πίνακας πελατών + αναζήτηση + analysis panel (stat tiles)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QMessageBox, QPushButton,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QGridLayout,
)

from .. import repo
from ..models import Client
from .client_dialog import ClientDialog
from .widgets import Card, StatTile, configure_table, h1, h2, muted


class ClientsPage(QWidget):
    open_codebook = Signal(int)   # client_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(h1("Πελάτες"))
        header.addStretch(1)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Αναζήτηση επωνυμίας ή ΑΦΜ…")
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(self.reload)
        new_btn = QPushButton("＋ Νέος πελάτης")
        new_btn.setObjectName("primary")
        new_btn.clicked.connect(self.new_client)
        header.addWidget(self.search)
        header.addWidget(new_btn)
        root.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)

        # --- αριστερά: πίνακας πελατών ---
        left = QWidget()
        left_l = QVBoxLayout(left)
        left_l.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Επωνυμία", "ΑΦΜ", "Είδη", "Matched"])
        configure_table(self.table, stretch=[0])
        self.table.itemSelectionChanged.connect(self._on_select)
        self.table.itemDoubleClicked.connect(lambda *_: self._open_selected())
        left_l.addWidget(self.table)

        actions = QHBoxLayout()
        open_btn = QPushButton("Άνοιγμα κωδικολογίου")
        open_btn.setObjectName("primary")
        open_btn.clicked.connect(self._open_selected)
        edit_btn = QPushButton("Επεξεργασία")
        edit_btn.clicked.connect(self.edit_selected)
        del_btn = QPushButton("Διαγραφή")
        del_btn.setObjectName("danger")
        del_btn.clicked.connect(self.delete_selected)
        actions.addWidget(open_btn)
        actions.addWidget(edit_btn)
        actions.addWidget(del_btn)
        actions.addStretch(1)
        left_l.addLayout(actions)
        splitter.addWidget(left)

        # --- δεξιά: analysis panel ---
        self.panel = self._build_panel()
        splitter.addWidget(self.panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([760, 380])
        root.addWidget(splitter)

        self.reload()

    def _build_panel(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        self.panel_title = h2("Επιλέξτε πελάτη")
        layout.addWidget(self.panel_title)
        self.panel_sub = muted("—")
        layout.addWidget(self.panel_sub)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.tile_total = StatTile("Σύνολο ειδών")
        self.tile_matched = StatTile("Με TARIC")
        self.tile_unmatched = StatTile("Εκκρεμή")
        self.tile_verified = StatTile("Επιβεβαιωμένα")
        self.tile_total.clicked.connect(lambda: self._emit_open())
        self.tile_matched.clicked.connect(lambda: self._emit_open())
        self.tile_unmatched.clicked.connect(lambda: self._emit_open())
        grid.addWidget(self.tile_total, 0, 0)
        grid.addWidget(self.tile_matched, 0, 1)
        grid.addWidget(self.tile_unmatched, 1, 0)
        grid.addWidget(self.tile_verified, 1, 1)
        layout.addLayout(grid)
        layout.addStretch(1)
        return card

    # ------------------------------------------------------------- data ----
    def reload(self) -> None:
        clients = repo.list_clients(self.search.text())
        self.table.setRowCount(len(clients))
        self._ids: list[int] = []
        for row, c in enumerate(clients):
            stats = repo.client_stats(c.id)
            self._ids.append(c.id)
            self.table.setItem(row, 0, QTableWidgetItem(c.name))
            self.table.setItem(row, 1, QTableWidgetItem(c.vat))
            self.table.setItem(row, 2, QTableWidgetItem(str(stats["total"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(stats["matched"])))
        if clients and self._current_id in self._ids:
            self.table.selectRow(self._ids.index(self._current_id))
        elif not clients:
            self._current_id = None
            self._update_panel(None)

    def _on_select(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        self._current_id = self._ids[rows[0].row()]
        self._update_panel(self._current_id)

    def _update_panel(self, client_id: int | None) -> None:
        if client_id is None:
            self.panel_title.setText("Επιλέξτε πελάτη")
            self.panel_sub.setText("—")
            for t in (self.tile_total, self.tile_matched, self.tile_unmatched, self.tile_verified):
                t.set_value("0")
            return
        client = repo.get_client(client_id)
        stats = repo.client_stats(client_id)
        self.panel_title.setText(client.name if client else "—")
        self.panel_sub.setText(f"ΑΦΜ: {client.vat or '—'}" if client else "—")
        self.tile_total.set_value(str(stats["total"]))
        self.tile_matched.set_value(str(stats["matched"]))
        self.tile_unmatched.set_value(str(stats["unmatched"]))
        self.tile_verified.set_value(str(stats["verified"]))

    def _emit_open(self) -> None:
        if self._current_id is not None:
            self.open_codebook.emit(self._current_id)

    # ---------------------------------------------------------- actions ----
    def selected_id(self) -> int | None:
        return self._current_id

    def _open_selected(self) -> None:
        if self._current_id is None:
            QMessageBox.information(self, "Πελάτης", "Επιλέξτε πρώτα πελάτη.")
            return
        self.open_codebook.emit(self._current_id)

    def new_client(self) -> None:
        dlg = ClientDialog(parent=self)
        if dlg.exec():
            cid = repo.create_client(dlg.result_client())
            self._current_id = cid
            self.reload()

    def edit_selected(self) -> None:
        if self._current_id is None:
            return
        client = repo.get_client(self._current_id)
        if not client:
            return
        dlg = ClientDialog(client, parent=self)
        if dlg.exec():
            repo.update_client(dlg.result_client())
            self.reload()

    def delete_selected(self) -> None:
        if self._current_id is None:
            return
        client = repo.get_client(self._current_id)
        if not client:
            return
        confirm = QMessageBox.question(
            self, "Διαγραφή πελάτη",
            f"Διαγραφή του πελάτη «{client.name}» και όλου του κωδικολογίου του;",
        )
        if confirm == QMessageBox.Yes:
            repo.delete_client(self._current_id)
            self._current_id = None
            self.reload()
