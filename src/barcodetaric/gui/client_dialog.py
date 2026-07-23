"""Dialog δημιουργίας/επεξεργασίας πελάτη."""

from __future__ import annotations

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

    def _fetch_from_vat(self) -> None:
        afm = self.vat.text().strip()
        if not afm:
            self.vat.setFocus()
            return
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Άντληση…")
        run_async(self, business_lookup.lookup_by_afm, afm,
                  on_done=self._on_fetched, on_error=lambda _m: self._reset_fetch())

    def _on_fetched(self, result: dict) -> None:
        self._reset_fetch()
        from PySide6.QtWidgets import QMessageBox
        if not result.get("success"):
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
