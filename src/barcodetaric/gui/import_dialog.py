"""Διάλογος αντιστοίχισης στηλών πριν το import Excel/CSV.

Το πρόγραμμα προτείνει αυτόματα ποια στήλη είναι barcode/περιγραφή/TARIC· ο χρήστης
επιβεβαιώνει ή διορθώνει, και επιλέγει ποιες ΕΠΙΠΛΕΟΝ στήλες (κωδικοί/λεπτομέρειες)
να διατηρηθούν ώστε να εξαχθούν αργότερα.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGridLayout,
    QGroupBox, QLabel, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..excel.reader import ColumnPreview
from .widgets import h2, muted

_NONE = "— (καμία) —"


class ImportMappingDialog(QDialog):
    def __init__(self, preview: ColumnPreview, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Αντιστοίχιση στηλών εισαγωγής")
        self.setMinimumWidth(720)
        self._preview = preview
        self._headers = preview.headers

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.addWidget(h2("Επιβεβαιώστε τις στήλες του αρχείου"))
        root.addWidget(muted(
            "Το πρόγραμμα εντόπισε αυτόματα τις στήλες (προεπιλεγμένες παρακάτω). "
            "Διορθώστε αν χρειάζεται. Οι «επιπλέον στήλες» που θα επιλέξετε κρατιούνται "
            "αυτούσιες και μπορούν να εξαχθούν ξανά (π.χ. εσωτερικοί κωδικοί, λεπτομέρειες)."))

        # --- mapping combos ---
        form = QFormLayout()
        form.setSpacing(8)
        self.cmb_barcode = self._make_combo(preview.suggested.get("barcode"))
        self.cmb_desc = self._make_combo(preview.suggested.get("description"))
        self.cmb_taric = self._make_combo(preview.suggested.get("taric"))
        for c in (self.cmb_barcode, self.cmb_desc, self.cmb_taric):
            c.currentIndexChanged.connect(self._sync_extra_enabled)
        form.addRow("Barcode / Κωδικός EAN:", self.cmb_barcode)
        form.addRow("Περιγραφή προϊόντος:", self.cmb_desc)
        form.addRow("TARIC (προαιρετικό):", self.cmb_taric)
        root.addLayout(form)

        # --- extra columns to keep ---
        box = QGroupBox("Επιπλέον στήλες προς διατήρηση (για εξαγωγή)")
        box_l = QVBoxLayout(box)
        hint = muted("Τυχόν στήλες πέραν των παραπάνω (εσωτερικοί κωδικοί, τιμές, σχόλια…).")
        box_l.addWidget(hint)
        grid_host = QWidget()
        self._extra_grid = QGridLayout(grid_host)
        self._extra_grid.setContentsMargins(0, 0, 0, 0)
        self._extra_checks: dict[int, QCheckBox] = {}
        for i, name in enumerate(self._headers):
            cb = QCheckBox(name)
            self._extra_checks[i] = cb
            self._extra_grid.addWidget(cb, i // 3, i % 3)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid_host)
        scroll.setMaximumHeight(120)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        box_l.addWidget(scroll)
        root.addWidget(box)

        # --- preview table ---
        root.addWidget(QLabel("Προεπισκόπηση:"))
        table = QTableWidget(len(preview.samples), len(self._headers))
        table.setHorizontalHeaderLabels(self._headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setMaximumHeight(200)
        for r, row in enumerate(preview.samples):
            for c in range(len(self._headers)):
                table.setItem(r, c, QTableWidgetItem(row[c] if c < len(row) else ""))
        table.resizeColumnsToContents()
        root.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Εισαγωγή")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._sync_extra_enabled()

    def _make_combo(self, selected: int | None) -> QComboBox:
        cmb = QComboBox()
        cmb.addItem(_NONE, None)
        for i, name in enumerate(self._headers):
            cmb.addItem(f"{i+1}. {name}", i)
        if selected is not None:
            cmb.setCurrentIndex(selected + 1)   # +1 λόγω του «καμία»
        return cmb

    def _mapped_indices(self) -> set[int]:
        out = set()
        for c in (self.cmb_barcode, self.cmb_desc, self.cmb_taric):
            idx = c.currentData()
            if idx is not None:
                out.add(idx)
        return out

    def _sync_extra_enabled(self) -> None:
        """Στήλη που χρησιμοποιείται ως πεδίο δεν μπορεί να είναι και «επιπλέον»."""
        used = self._mapped_indices()
        for i, cb in self._extra_checks.items():
            if i in used:
                cb.setChecked(False)
                cb.setEnabled(False)
            else:
                cb.setEnabled(True)

    # ---------------------------------------------------------- result ----
    def mapping(self) -> dict:
        return {
            "barcode": self.cmb_barcode.currentData(),
            "description": self.cmb_desc.currentData(),
            "taric": self.cmb_taric.currentData(),
        }

    def extra_cols(self) -> list[int]:
        used = self._mapped_indices()
        return [i for i, cb in self._extra_checks.items() if cb.isChecked() and i not in used]

    def has_header(self) -> bool:
        return self._preview.has_header
