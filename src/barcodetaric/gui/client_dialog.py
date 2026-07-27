"""Dialog δημιουργίας/επεξεργασίας πελάτη."""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
)

from ..engine import business_lookup
from ..models import Client
from .workers import run_async


class ClientDialog(QDialog):
    def __init__(self, client: Client | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Επεξεργασία πελάτη" if client and client.id else "Νέος πελάτης")
        self.setMinimumWidth(460)
        self._client = client or Client()

        root = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(10)

        self.name = QLineEdit(self._client.name)
        self.vat = QLineEdit(self._client.vat)
        self.vat.setPlaceholderText("9 ψηφία — αυτόματη άντληση στοιχείων")
        self.vat.setMaxLength(9)
        self.vat.setValidator(QIntValidator(0, 999999999, self))
        self.email = QLineEdit(self._client.email)
        self.phone = QLineEdit(self._client.phone)
        self.address = QLineEdit(self._client.address)
        self.notes = QTextEdit(self._client.notes)
        self.notes.setFixedHeight(70)

        # ΑΦΜ + κουμπί άντλησης στοιχείων από ΓΕΜΗ
        vat_row = QWidget()
        vat_l = QHBoxLayout(vat_row)
        vat_l.setContentsMargins(0, 0, 0, 0)
        vat_l.setSpacing(8)
        vat_l.addWidget(self.vat, 1)
        self.fetch_btn = QPushButton("Άντληση από ΑΦΜ")
        self.fetch_btn.setToolTip("Συμπλήρωση στοιχείων από το ΓΕΜΗ (Business Portal)")
        self.fetch_btn.clicked.connect(self._fetch_from_vat)
        vat_l.addWidget(self.fetch_btn)

        # Αυτόματη άντληση μόλις συμπληρωθεί έγκυρος 9ψήφιος ΑΦΜ (με debounce
        # ώστε να μην πυροδοτείται σε κάθε πάτημα πλήκτρου).
        self._last_afm = ""
        self._afm_timer = QTimer(self)
        self._afm_timer.setSingleShot(True)
        self._afm_timer.setInterval(500)
        self._afm_timer.timeout.connect(self._maybe_auto_fetch)
        self.vat.textChanged.connect(lambda _t: self._afm_timer.start())

        form.addRow("Επωνυμία *", self.name)
        form.addRow("ΑΦΜ", vat_row)
        form.addRow("Email", self.email)
        form.addRow("Τηλέφωνο", self.phone)
        form.addRow("Διεύθυνση", self.address)
        form.addRow("Σημειώσεις", self.notes)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Αποθήκευση")
        buttons.button(QDialogButtonBox.Cancel).setText("Άκυρο")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _maybe_auto_fetch(self) -> None:
        """Πυροδοτείται (debounced) μόλις ο ΑΦΜ γίνει έγκυρος 9ψήφιος αριθμός."""
        afm = self.vat.text().strip()
        if len(afm) == 9 and afm.isdigit() and afm != self._last_afm:
            self._start_lookup(afm, silent=True)

    def _fetch_from_vat(self) -> None:
        afm = self.vat.text().strip()
        if not afm:
            self.vat.setFocus()
            return
        self._start_lookup(afm, silent=False)

    def _start_lookup(self, afm: str, *, silent: bool) -> None:
        self._last_afm = afm
        self._silent_lookup = silent   # στην αυτόματη άντληση δεν δείχνουμε popup σε αποτυχία
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Άντληση…")
        run_async(self, business_lookup.lookup_by_afm, afm,
                  on_done=self._on_fetched, on_error=lambda _m: self._reset_fetch())

    def _on_fetched(self, result: dict) -> None:
        self._reset_fetch()
        from PySide6.QtWidgets import QMessageBox
        if not result.get("success"):
            if not getattr(self, "_silent_lookup", False):
                QMessageBox.information(self, "Άντληση από ΑΦΜ",
                                        result.get("error") or "Δεν βρέθηκαν στοιχεία.")
            return
        c = result["company"]
        if c.get("name"):
            self.name.setText(c["name"])
        if c.get("address"):
            self.address.setText(c["address"])
        extra = " · ".join(p for p in (c.get("activity"), c.get("legal_form"),
                                       f"ΓΕΜΗ {c['ar_gemi']}" if c.get("ar_gemi") else "") if p)
        if extra:
            existing = self.notes.toPlainText().strip()
            self.notes.setPlainText((existing + "\n" if existing else "") + extra)

    def _reset_fetch(self) -> None:
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Άντληση από ΑΦΜ")

    def _on_accept(self) -> None:
        if not self.name.text().strip():
            self.name.setFocus()
            return
        self.accept()

    def result_client(self) -> Client:
        self._client.name = self.name.text().strip()
        self._client.vat = self.vat.text().strip()
        self._client.email = self.email.text().strip()
        self._client.phone = self.phone.text().strip()
        self._client.address = self.address.text().strip()
        self._client.notes = self.notes.toPlainText().strip()
        return self._client
