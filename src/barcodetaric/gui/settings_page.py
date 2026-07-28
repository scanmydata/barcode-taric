"""Σελίδα ρυθμίσεων: AI (μόνο δωρεάν μοντέλα) + web search + ΓΕΜΗ + debugger + εμφάνιση."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from ..config import SETTINGS
from ..engine import ai
from .widgets import Card, h1, h2, muted
from .workers import run_async


class SettingsPage(QWidget):
    theme_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(h1("Ρυθμίσεις"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # ποτέ οριζόντια κύλιση/κόψιμο
        outer.addWidget(scroll)
        container = QWidget()
        scroll.setWidget(container)
        root = QVBoxLayout(container)
        root.setContentsMargins(2, 2, 12, 2)
        root.setSpacing(14)

        # --- AI (μόνο δωρεάν) ---
        ai_card = Card()
        ai_l = QFormLayout(ai_card)
        ai_l.setContentsMargins(18, 16, 18, 16)
        ai_l.setSpacing(10)
        ai_l.addRow(h2("AI — μόνο δωρεάν μοντέλα"))
        self.openrouter_key = QLineEdit(str(SETTINGS.get("openrouter_api_key") or ""))
        self.openrouter_key.setEchoMode(QLineEdit.Password)
        self.openrouter_key.setPlaceholderText("sk-or-…")
        self.openrouter_model = QComboBox()
        self.openrouter_model.setEditable(True)
        # Επίτρεψε στο combo να συρρικνώνεται· μεγάλα model ids (…:free) αλλιώς σπρώχνουν
        # το form πέρα από το παράθυρο και κόβεται δεξιά.
        self.openrouter_model.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.openrouter_model.setMinimumContentsLength(12)
        self.openrouter_model.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.openrouter_model.addItem(str(SETTINGS.get("openrouter_model") or ""))
        model_row = QWidget()
        model_l = QHBoxLayout(model_row)
        model_l.setContentsMargins(0, 0, 0, 0)
        model_l.addWidget(self.openrouter_model, 1)
        free_btn = QPushButton("Λίστα μοντέλων")
        free_btn.setToolTip("Λήψη των δωρεάν μοντέλων OpenRouter")
        free_btn.clicked.connect(self._load_free_models)
        model_l.addWidget(free_btn)
        smart_btn = QPushButton("Έξυπνη επιλογή")
        smart_btn.setToolTip("Δοκιμάζει τα κορυφαία δωρεάν μοντέλα & επιλέγει ένα που δουλεύει")
        smart_btn.clicked.connect(self._smart_pick_model)
        model_l.addWidget(smart_btn)
        self.provider_order = QLineEdit(", ".join(SETTINGS.get("ai_provider_order") or []))
        self.groq_key = QLineEdit(str(SETTINGS.get("groq_api_key") or ""))
        self.groq_key.setEchoMode(QLineEdit.Password)
        self.groq_key.setPlaceholderText("gsk_… (προαιρετικό)")
        ai_l.addRow("OpenRouter API key", self.openrouter_key)
        ai_l.addRow("Μοντέλο (:free)", model_row)
        ai_l.addRow("", muted("Συνιστώμενο: OpenRouter με δωρεάν μοντέλο (:free προστίθεται αυτόματα). "
                              "Τα no-key (Pollinations/DuckDuckGo) πλέον χρεώνουν/περιορίζονται (402/429)."))
        ai_l.addRow("Groq API key (προαιρ.)", self.groq_key)
        ai_l.addRow("Σειρά providers", self.provider_order)
        root.addWidget(ai_card)

        # --- Web search ---
        web_card = Card()
        web_l = QFormLayout(web_card)
        web_l.setContentsMargins(18, 16, 18, 16)
        web_l.setSpacing(10)
        web_l.addRow(h2("Web search"))
        web_l.addRow("", muted("SearXNG → DuckDuckGo → headless Chrome (Google) → googlesearch → CSE"))
        self.searxng_url = QLineEdit(str(SETTINGS.get("searxng_url") or ""))
        self.searxng_url.setPlaceholderText("https://searx.example.org  ή  http://127.0.0.1:8888")
        self.cse_key = QLineEdit(str(SETTINGS.get("google_cse_api_key") or ""))
        self.cse_key.setEchoMode(QLineEdit.Password)
        self.cse_id = QLineEdit(str(SETTINGS.get("google_cse_id") or ""))
        self.web_order = QLineEdit(", ".join(SETTINGS.get("web_search_order") or []))
        web_l.addRow("SearXNG URL", self.searxng_url)
        web_l.addRow("", muted("SearXNG instance με ενεργό JSON API (self-host προτείνεται)."))
        web_l.addRow("Google CSE key", self.cse_key)
        web_l.addRow("Google CSE id", self.cse_id)
        web_l.addRow("Σειρά web tiers", self.web_order)
        self.headless_headed = QCheckBox("Ορατό παράθυρο Chrome")
        self.headless_headed.setToolTip("Το headless Chrome είναι πιο εύκολα ανιχνεύσιμο ως bot· "
                                        "με ορατό παράθυρο η Google μπλοκάρει λιγότερο.")
        self.headless_headed.setChecked(bool(SETTINGS.get("headless_headed")))
        web_l.addRow("", self.headless_headed)
        self.chrome_user_dir = QLineEdit(str(SETTINGS.get("chrome_user_data_dir") or ""))
        self.chrome_user_dir.setPlaceholderText(r"%LOCALAPPDATA%\Google\Chrome\User Data (προαιρ.)")
        self.chrome_profile = QLineEdit(str(SETTINGS.get("chrome_profile") or ""))
        self.chrome_profile.setPlaceholderText("Default ή Profile 1 (προαιρ.)")
        web_l.addRow("Chrome προφίλ (φάκελος)", self.chrome_user_dir)
        web_l.addRow("Chrome profile", self.chrome_profile)
        web_l.addRow("", muted("Χρήση του πραγματικού προφίλ Chrome (cookies/consent) μειώνει το "
                               "anti-bot. ΠΡΟΣΟΧΗ: κλείσε το Chrome πριν την αναζήτηση."))
        web_l.addRow("", muted("Το «headless» tier θέλει selenium + Chrome. Η Google μπορεί να ζητήσει "
                               "CAPTCHA (/sorry) σε συχνά queries — τότε πέφτει σε DuckDuckGo."))
        root.addWidget(web_card)

        # --- Custom AI endpoint (μελλοντικό/on-prem) ---
        custom_card = Card()
        custom_l = QFormLayout(custom_card)
        custom_l.setContentsMargins(18, 16, 18, 16)
        custom_l.setSpacing(10)
        custom_l.addRow(h2("Custom AI endpoint (προαιρετικό)"))
        custom_l.addRow("", muted("OpenAI-συμβατό endpoint· βάλε «custom» στη σειρά providers."))
        self.custom_url = QLineEdit(str(SETTINGS.get("custom_ai_base_url") or ""))
        self.custom_url.setPlaceholderText("https://my-host/v1/chat/completions")
        self.custom_model = QLineEdit(str(SETTINGS.get("custom_ai_model") or ""))
        self.custom_model.setPlaceholderText("π.χ. gpt-4o-mini, llama-3.1-8b-instruct")
        self.custom_key = QLineEdit(str(SETTINGS.get("custom_ai_api_key") or ""))
        self.custom_key.setEchoMode(QLineEdit.Password)
        self.custom_timeout = QDoubleSpinBox()
        self.custom_timeout.setRange(10, 600)
        self.custom_timeout.setSingleStep(10)
        self.custom_timeout.setSuffix(" s")
        self.custom_timeout.setValue(float(SETTINGS.get("custom_ai_timeout", 90)))
        custom_l.addRow("Base URL", self.custom_url)
        custom_l.addRow("", muted("Ollama μέσω Cloudflare tunnel: https://xxx.trycloudflare.com/v1"))
        custom_l.addRow("Μοντέλο", self.custom_model)
        custom_l.addRow("API key (προαιρ.)", self.custom_key)
        custom_l.addRow("Timeout", self.custom_timeout)
        root.addWidget(custom_card)

        # --- ΓΕΜΗ / TARIC / εμφάνιση ---
        misc_card = Card()
        misc_l = QFormLayout(misc_card)
        misc_l.setContentsMargins(18, 16, 18, 16)
        misc_l.setSpacing(10)
        misc_l.addRow(h2("ΓΕΜΗ, ονοματολογία & εμφάνιση"))
        self.business_key = QLineEdit(str(SETTINGS.get("business_portal_key") or ""))
        self.business_key.setEchoMode(QLineEdit.Password)
        self.business_key.setPlaceholderText("Business Portal API key (ΑΦΜ → στοιχεία)")
        self.auto_update = QCheckBox("Αυτόματη ενημέρωση TARIC από ΕΕ στην εκκίνηση")
        self.auto_update.setChecked(bool(SETTINGS.get("auto_update_taric")))
        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0.1, 0.99)
        self.threshold.setSingleStep(0.05)
        self.threshold.setValue(float(SETTINGS.get("ml_confidence_threshold", 0.55)))
        self.theme = QComboBox()
        self.theme.addItems(["dark", "light"])
        self.theme.setCurrentText(str(SETTINGS.get("theme", "dark")))
        self.theme.currentTextChanged.connect(self.theme_changed.emit)
        misc_l.addRow("ΓΕΜΗ API key", self.business_key)
        misc_l.addRow("", self.auto_update)
        misc_l.addRow("Κατώφλι βεβαιότητας ML", self.threshold)
        misc_l.addRow("Θέμα", self.theme)
        root.addWidget(misc_card)

        # --- Debugger ---
        dbg_card = Card()
        dbg_l = QVBoxLayout(dbg_card)
        dbg_l.setContentsMargins(18, 16, 18, 16)
        dbg_l.setSpacing(10)
        dbg_l.addWidget(h2("Debugger / Καταγραφή"))
        # 2×2 grid: 4 κουμπιά σε μία σειρά ξεπερνούσαν το πλάτος του παραθύρου (overflow).
        dbg_btns = QGridLayout()
        dbg_btns.setSpacing(8)
        test_btn = QPushButton("Έλεγχος AI providers")
        test_btn.clicked.connect(self._test_ai)
        test_web_btn = QPushButton("Έλεγχος web search")
        test_web_btn.clicked.connect(self._test_web)
        log_btn = QPushButton("Άνοιγμα αρχείου καταγραφής")
        log_btn.clicked.connect(self._open_log)
        refresh_log = QPushButton("Ανανέωση log")
        refresh_log.clicked.connect(self._refresh_log)
        dbg_btns.addWidget(test_btn, 0, 0)
        dbg_btns.addWidget(test_web_btn, 0, 1)
        dbg_btns.addWidget(log_btn, 1, 0)
        dbg_btns.addWidget(refresh_log, 1, 1)
        dbg_l.addLayout(dbg_btns)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(150)
        self.log_view.setPlaceholderText("Τα τελευταία events καταγραφής θα εμφανιστούν εδώ…")
        dbg_l.addWidget(self.log_view)
        root.addWidget(dbg_card)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_btn = QPushButton("Αποθήκευση ρυθμίσεων")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self.save)
        save_row.addWidget(save_btn)
        root.addLayout(save_row)
        root.addStretch(1)

    # ---------------------------------------------------------- actions ----
    def _load_free_models(self) -> None:
        run_async(self, ai.list_free_models, on_done=self._on_free_models,
                  on_error=lambda _m: None)

    def _on_free_models(self, models: list) -> None:
        if not models:
            QMessageBox.information(self, "Δωρεάν μοντέλα",
                                    "Δεν βρέθηκαν (ελέγξτε το OpenRouter key/σύνδεση).")
            return
        current = self.openrouter_model.currentText()
        self.openrouter_model.clear()
        self.openrouter_model.addItems(models)
        if current in models:
            self.openrouter_model.setCurrentText(current)

    def _smart_pick_model(self) -> None:
        self.log_view.setPlainText("Έξυπνη επιλογή δωρεάν μοντέλου…")
        run_async(self, ai.best_free_model, on_done=self._on_smart_picked,
                  on_error=lambda m: self.log_view.setPlainText(m))

    def _on_smart_picked(self, model) -> None:
        if not model:
            QMessageBox.information(self, "Έξυπνη επιλογή",
                                    "Δεν βρέθηκε μοντέλο που να απαντά (έλεγξε το OpenRouter key).")
            return
        if self.openrouter_model.findText(model) < 0:
            self.openrouter_model.insertItem(0, model)
        self.openrouter_model.setCurrentText(model)
        self.log_view.setPlainText(f"Επιλέχθηκε μοντέλο: {model}\n(πάτησε «Αποθήκευση ρυθμίσεων»)")

    def _test_ai(self) -> None:
        self.log_view.setPlainText("Έλεγχος providers…")
        run_async(self, ai.test_providers, on_done=self._on_tested,
                  on_error=lambda m: self.log_view.setPlainText(m))

    def _on_tested(self, results: list) -> None:
        lines = [("✓" if ok else "✗") + f"  {name}: {msg}" for name, ok, msg in results]
        self.log_view.setPlainText("\n".join(lines) or "—")

    def _test_web(self) -> None:
        from ..engine import web_search
        self.log_view.setPlainText("Έλεγχος web search tiers…")
        run_async(self, web_search.test_tiers, on_done=self._on_tested,
                  on_error=lambda m: self.log_view.setPlainText(m))

    def _open_log(self) -> None:
        from ..logs import log_path
        path = log_path()
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            QMessageBox.information(self, "Αρχείο καταγραφής", str(path))

    def _refresh_log(self) -> None:
        from ..logs import recent
        self.log_view.setPlainText("\n".join(recent(200)) or "—")

    def save(self) -> None:
        SETTINGS.set("openrouter_api_key", self.openrouter_key.text().strip())
        SETTINGS.set("openrouter_model", ai._ensure_free(self.openrouter_model.currentText().strip()))
        order = [p.strip() for p in self.provider_order.text().split(",") if p.strip()]
        SETTINGS.set("ai_provider_order", order or list(ai._DEFAULT_ORDER))
        SETTINGS.set("groq_api_key", self.groq_key.text().strip())
        SETTINGS.set("searxng_url", self.searxng_url.text().strip())
        SETTINGS.set("google_cse_api_key", self.cse_key.text().strip())
        SETTINGS.set("google_cse_id", self.cse_id.text().strip())
        web_order = [t.strip() for t in self.web_order.text().split(",") if t.strip()]
        from ..engine import web_search
        SETTINGS.set("web_search_order", web_order or list(web_search._DEFAULT_ORDER))
        SETTINGS.set("headless_headed", self.headless_headed.isChecked())
        SETTINGS.set("chrome_user_data_dir", self.chrome_user_dir.text().strip())
        SETTINGS.set("chrome_profile", self.chrome_profile.text().strip())
        SETTINGS.set("custom_ai_base_url", self.custom_url.text().strip())
        SETTINGS.set("custom_ai_model", self.custom_model.text().strip())
        SETTINGS.set("custom_ai_api_key", self.custom_key.text().strip())
        SETTINGS.set("custom_ai_timeout", float(self.custom_timeout.value()))
        SETTINGS.set("business_portal_key", self.business_key.text().strip())
        SETTINGS.set("auto_update_taric", self.auto_update.isChecked())
        SETTINGS.set("ml_confidence_threshold", float(self.threshold.value()))
        SETTINGS.set("theme", self.theme.currentText())
        SETTINGS.save()
        QMessageBox.information(self, "Ρυθμίσεις", "Οι ρυθμίσεις αποθηκεύτηκαν.")
