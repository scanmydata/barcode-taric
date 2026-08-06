"""Σελίδα TARIC & ML: import/update επίσημης ΕΕ ονοματολογίας + εκπαίδευση μοντέλου."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFileDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from .. import repo
from ..engine.ml_classifier import retrain
from ..taric import circabc, importer, updates
from .widgets import BusyOverlay, Card, StatTile, h1, h2, muted
from .workers import run_async


class TaricPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(14)
        root.addWidget(h1("TARIC & Μοντέλο"))

        # --- κάρτα ΕΕ ονοματολογίας ---
        eu_card = Card()
        eu = QVBoxLayout(eu_card)
        eu.setContentsMargins(18, 16, 18, 16)
        eu.setSpacing(10)
        eu.addWidget(h2("Επίσημη ΕΕ ονοματολογία (Combined Nomenclature)"))
        eu.addWidget(muted(
            "Δεν υπάρχει δωρεάν επίσημο REST API της ΕΕ — κατεβάζουμε & κάνουμε import τοπικά "
            "(offline matching μετά). Πηγή: data.europa.eu «Combined Nomenclature <έτος>»."))
        self.taric_status = QLabel("—")
        self.taric_status.setWordWrap(True)
        eu.addWidget(self.taric_status)

        eu_btns = QHBoxLayout()
        auto_btn = QPushButton("Αυτόματη ενημέρωση από ΕΕ")
        auto_btn.setObjectName("primary")
        auto_btn.setToolTip("Κατεβάζει την πιο πρόσφατη ονοματολογία TARIC από το CIRCABC της ΕΕ")
        auto_btn.clicked.connect(self.auto_update)
        check_btn = QPushButton("Έλεγχος ενημερώσεων")
        check_btn.clicked.connect(self.check_updates)
        file_btn = QPushButton("Import από αρχείο")
        file_btn.clicked.connect(self.import_file)
        seed_btn = QPushButton("Δείγμα")
        seed_btn.clicked.connect(self.load_seed)
        eu_btns.addWidget(auto_btn)
        eu_btns.addWidget(check_btn)
        eu_btns.addWidget(file_btn)
        eu_btns.addWidget(seed_btn)
        eu_btns.addStretch(1)
        eu.addLayout(eu_btns)
        root.addWidget(eu_card)

        # --- κάρτα ML ---
        ml_card = Card()
        ml = QVBoxLayout(ml_card)
        ml.setContentsMargins(18, 16, 18, 16)
        ml.setSpacing(10)
        ml.addWidget(h2("Τοπικό μοντέλο ML"))
        ml.addWidget(muted(
            "Μαθαίνει από τα επιβεβαιωμένα (✔) είδη. Όσο μεγαλώνει το dataset, αναλαμβάνει "
            "όλο και περισσότερες αποφάσεις χωρίς κλήση AI."))

        grid = QGridLayout()
        grid.setSpacing(10)
        self.tile_samples = StatTile("Δείγματα εκπαίδευσης")
        self.tile_accuracy = StatTile("Ακρίβεια (CV)")
        self.tile_ml = StatTile("Αποφάσεις ML")
        self.tile_ai = StatTile("Αποφάσεις AI")
        grid.addWidget(self.tile_samples, 0, 0)
        grid.addWidget(self.tile_accuracy, 0, 1)
        grid.addWidget(self.tile_ml, 0, 2)
        grid.addWidget(self.tile_ai, 0, 3)
        ml.addLayout(grid)

        self.ml_status = QLabel("")
        self.ml_status.setObjectName("muted")
        ml.addWidget(self.ml_status)

        train_btn = QPushButton("🧠 Εκπαίδευση μοντέλου")
        train_btn.setObjectName("primary")
        train_btn.clicked.connect(self.train_model)
        ml.addWidget(train_btn)
        root.addWidget(ml_card)
        root.addStretch(1)

        self._busy = BusyOverlay(self)
        self.refresh()

    # ------------------------------------------------------------- data ----
    def refresh(self) -> None:
        meta = repo.taric_meta()
        if meta and meta.get("row_count"):
            self.taric_status.setText(
                f"Τοπική έκδοση: {meta.get('version')} · {meta.get('row_count')} εγγραφές · "
                f"import: {meta.get('imported_at')}")
        else:
            self.taric_status.setText("Δεν έχει γίνει ακόμη import ΕΕ ονοματολογίας.")

        ml_meta = repo.get_ml_meta()
        self.tile_samples.set_value(str((ml_meta or {}).get("n_samples", 0)))
        acc = (ml_meta or {}).get("cv_accuracy", 0) or 0
        self.tile_accuracy.set_value(f"{acc*100:.0f}%" if acc else "—")
        breakdown = repo.taric_source_breakdown()
        self.tile_ml.set_value(str(breakdown.get("ml", 0)))
        self.tile_ai.set_value(str(breakdown.get("ai", 0)))

    # ---------------------------------------------------------- actions ----
    def _busy_progress(self, msg: str) -> None:
        self.taric_status.setText(msg)
        self._busy.set_message(msg)

    def auto_update(self) -> None:
        self.taric_status.setText("Έναρξη αυτόματης ενημέρωσης από ΕΕ (CIRCABC)…")
        self._busy.start("Ενημέρωση ονοματολογίας TARIC από ΕΕ…\nΜπορεί να πάρει λίγα λεπτά.")
        run_async(self, circabc.auto_import,
                  on_done=lambda n: (self._busy.stop(),
                                     self._info(f"Ενημερώθηκε από ΕΕ: {n} κωδικοί TARIC."), self.refresh()),
                  on_error=self._busy_error, on_progress=self._busy_progress)

    def load_seed(self) -> None:
        self._busy.start("Φόρτωση δείγματος…")
        run_async(self, importer.import_seed,
                  on_done=lambda n: (self._busy.stop(),
                                     self._info(f"Φορτώθηκε δείγμα: {n} εγγραφές."), self.refresh()),
                  on_error=self._busy_error, on_progress=self._busy_progress)

    def import_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import ΕΕ ονοματολογίας", "",
            "Υποστηριζόμενα (*.xml *.csv *.tsv *.xlsx *.zip)")
        if not path:
            return
        self._busy.start("Εισαγωγή ονοματολογίας TARIC…\nΜπορεί να πάρει λίγα λεπτά.")
        run_async(self, importer.import_from_file, path,
                  on_done=lambda n: (self._busy.stop(),
                                     self._info(f"Εισήχθησαν {n} εγγραφές TARIC."), self.refresh()),
                  on_error=self._busy_error, on_progress=self._busy_progress)

    def check_updates(self) -> None:
        self.taric_status.setText("Έλεγχος ενημερώσεων…")
        run_async(self, updates.check_for_updates,
                  on_done=self._on_update_status, on_error=self._error)

    def _on_update_status(self, status: updates.UpdateStatus) -> None:
        self.taric_status.setText(status.message)
        if status.update_available or status.current_rows == 0:
            if QMessageBox.question(
                self, "Ενημέρωση", f"{status.message}\n\nΝα γίνει τώρα αυτόματη ενημέρωση από ΕΕ;",
            ) == QMessageBox.Yes:
                self.auto_update()

    def train_model(self) -> None:
        self.ml_status.setText("Εκπαίδευση…")
        self._busy.start("Εκπαίδευση τοπικού μοντέλου ML…")
        run_async(self, retrain, on_done=self._on_trained, on_error=self._busy_error)

    def _on_trained(self, result: dict) -> None:
        self._busy.stop()
        if result.get("trained"):
            self.ml_status.setText(
                f"Εκπαιδεύτηκε: {result.get('n_samples')} δείγματα · "
                f"ακρίβεια CV {result.get('cv_accuracy', 0)*100:.0f}%")
        else:
            reason = result.get("message") or result.get("reason", "")
            if result.get("reason") == "insufficient_samples":
                reason = (f"Χρειάζονται τουλάχιστον {result.get('min_samples')} επιβεβαιωμένα "
                          f"είδη (υπάρχουν {result.get('n_samples')}).")
            self.ml_status.setText(f"Δεν εκπαιδεύτηκε: {reason}")
        self.refresh()

    def _info(self, msg: str) -> None:
        QMessageBox.information(self, "TARIC", msg)

    def _error(self, message: str) -> None:
        QMessageBox.warning(self, "Σφάλμα", message.splitlines()[0])
        self.refresh()

    def _busy_error(self, message: str) -> None:
        self._busy.stop()
        self._error(message)
