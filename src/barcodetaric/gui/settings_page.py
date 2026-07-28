"""Σελίδα ρυθμίσεων: AI (μόνο δωρεάν μοντέλα) + web search + ΓΕΜΗ + debugger + εμφάνιση."""

from __future__ import annotations

import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
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
        self.openrouter_model.addItem(str(SETTINGS.get("openrouter_model") or ""))
        model_row = QWidget()
        model_l = QHBoxLayout(model_row)
        model_l.setContentsMargins(0, 0, 0, 0)
        model_l.addWidget(self.openrouter_model, 1)
        free_btn = QPushButton("Λήψη δωρεάν μοντέλων")
        free_btn.clicked.connect(self._load_free_models)
        model_l.addWidget(free_btn)
        self.provider_order = QLineEdit(", ".join(SETTINGS.get("ai_provider_order") or []))
        self.groq_key = QLineEdit(str(SETTINGS.get("groq_api_key") or ""))
        self.groq_key.setEchoMode(QLineEdit.Password)
        self.groq_key.setPlaceholderText("gsk_… (προαιρετικό)")
        # Custom OpenAI-compatible endpoint (τοπικό ollama μέσω cloudflare tunnel).
        self.custom_url = QLineEdit(str(SETTINGS.get("custom_ai_url") or ""))
        self.custom_url.setPlaceholderText("https://ollama.mydomain.com  (ή …/v1/chat/completions)")
        self.custom_model = QLineEdit(str(SETTINGS.get("custom_ai_model") or ""))
        self.custom_model.setPlaceholderText("llama3.1 / qwen2.5 …")
        self.custom_key = QLineEdit(str(SETTINGS.get("custom_ai_key") or ""))
        self.custom_key.setEchoMode(QLineEdit.Password)
        self.custom_key.setPlaceholderText("προαιρετικό (τοπικός server δεν χρειάζεται)")
        ai_l.addRow("OpenRouter API key", self.openrouter_key)
        ai_l.addRow("Μοντέλο (:free)", model_row)
        ai_l.addRow("", muted("Συνιστώμενο: OpenRouter με δωρεάν μοντέλο (:free προστίθεται αυτόματα). "
                              "Τα no-key (Pollinations/DuckDuckGo) πλέον χρεώνουν/περιορίζονται (402/429)."))
        ai_l.addRow("Groq API key (προαιρ.)", self.groq_key)
        ai_l.addRow("Custom endpoint URL", self.custom_url)
        ai_l.addRow("Custom μοντέλο", self.custom_model)
        ai_l.addRow("Custom key (προαιρ.)", self.custom_key)
        ai_l.addRow("", muted("Custom = OpenAI-compatible endpoint για δικό σου local LLM "
                              "(π.χ. ollama μέσω cloudflare tunnel). Βάλε 'custom' πρώτο στη σειρά providers."))
        ai_l.addRow("Σειρά providers", self.provider_order)
        root.addWidget(ai_card)

        # --- Web search ---
        web_card = Card()
        web_l = QFormLayout(web_card)
        web_l.setContentsMargins(18, 16, 18, 16)
        web_l.setSpacing(10)
        web_l.addRow(h2("Web search (Google results)"))
        web_l.addRow("", muted("SearXNG → OpenSERP → Brave → Google CSE → DuckDuckGo → googlesearch. "
                               "Το googlesearch είναι αργό/rate-limited — γι' αυτό τελευταίο."))
        self.searxng_url = QLineEdit(str(SETTINGS.get("searxng_url") or ""))
        self.searxng_url.setPlaceholderText("http://127.0.0.1:8080 (self-hosted SearXNG, format=json)")
        web_l.addRow("SearXNG URL", self.searxng_url)
        web_l.addRow("", muted("Μετα-μηχανή (πολλές μηχανές μαζί, χωρίς key). Θέλει `format: json` "
                               "στο settings.yml. Ιδανικό στο μηχάνημα του τοπικού LLM."))
        self.openserp_url = QLineEdit(str(SETTINGS.get("openserp_url") or ""))
        self.openserp_url.setPlaceholderText("http://127.0.0.1:7000 (τοπικός OpenSERP server)")
        web_l.addRow("OpenSERP URL", self.openserp_url)
        web_l.addRow("", muted("Πραγματικά Google αποτελέσματα χωρίς key μέσω headless browser. Εκκίνηση:  "
                               "docker run --rm -p 127.0.0.1:7000:7000 karust/openserp:latest serve -a 0.0.0.0 -p 7000"))
        self.brave_key = QLineEdit(str(SETTINGS.get("brave_api_key") or ""))
        self.brave_key.setEchoMode(QLineEdit.Password)
        self.brave_key.setPlaceholderText("Brave Search API key — 2000 δωρεάν queries/μήνα (γρήγορο)")
        web_l.addRow("Brave API key (προαιρ.)", self.brave_key)
        self.cse_key = QLineEdit(str(SETTINGS.get("google_cse_api_key") or ""))
        self.cse_key.setEchoMode(QLineEdit.Password)
        self.cse_id = QLineEdit(str(SETTINGS.get("google_cse_id") or ""))
        web_l.addRow("Google CSE API key (προαιρ.)", self.cse_key)
        web_l.addRow("Google CSE id (προαιρ.)", self.cse_id)
        root.addWidget(web_card)

        # --- Μετάφραση & OCR ---
        tr_card = Card()
        tr_l = QFormLayout(tr_card)
        tr_l.setContentsMargins(18, 16, 18, 16)
        tr_l.setSpacing(10)
        tr_l.addRow(h2("Μετάφραση & OCR"))
        tr_l.addRow("", muted("Δωρεάν μετάφραση EL⇄EN χωρίς LLM (MyMemory — μνήμη ΕΕ/ΟΗΕ). "
                              "Η κατάταξη TARIC τρέχει με βασική γλώσσα τα Αγγλικά."))
        self.classify_en = QCheckBox("Κατάταξη με βασική γλώσσα τα Αγγλικά (συνιστάται)")
        self.classify_en.setChecked(bool(SETTINGS.get("classify_in_english", True)))
        tr_l.addRow("", self.classify_en)
        self.semantic_on = QCheckBox("Εννοιολογική αντιστοίχιση (τοπικά embeddings)")
        self.semantic_on.setChecked(bool(SETTINGS.get("semantic_enabled", True)))
        tr_l.addRow("", self.semantic_on)
        tr_l.addRow("", muted("Ταιριάζει βάσει νοήματος (συνώνυμα/παραφράσεις), όχι μόνο λέξεων. "
                              "Θέλει:  pip install -e \".[semantic]\"  (offline, δωρεάν)."))
        self.mymemory_email = QLineEdit(str(SETTINGS.get("mymemory_email") or ""))
        self.mymemory_email.setPlaceholderText("email (προαιρ.) — ανεβάζει το όριο 5000→50000 chars/μέρα")
        tr_l.addRow("MyMemory email (προαιρ.)", self.mymemory_email)
        self.libre_url = QLineEdit(str(SETTINGS.get("libretranslate_url") or ""))
        self.libre_url.setPlaceholderText("https://… (προαιρ. LibreTranslate instance)")
        tr_l.addRow("LibreTranslate URL (προαιρ.)", self.libre_url)
        self.libre_key = QLineEdit(str(SETTINGS.get("libretranslate_api_key") or ""))
        self.libre_key.setEchoMode(QLineEdit.Password)
        tr_l.addRow("LibreTranslate key (προαιρ.)", self.libre_key)
        self.ocr_key = QLineEdit(str(SETTINGS.get("ocrspace_api_key") or ""))
        self.ocr_key.setEchoMode(QLineEdit.Password)
        self.ocr_key.setPlaceholderText("ocr.space API key — OCR ετικέτας από φωτό προϊόντος")
        tr_l.addRow("OCR (ocr.space) key (προαιρ.)", self.ocr_key)
        root.addWidget(tr_card)

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
        dbg_btns = QHBoxLayout()
        test_btn = QPushButton("Έλεγχος AI providers")
        test_btn.clicked.connect(self._test_ai)
        log_btn = QPushButton("Άνοιγμα αρχείου καταγραφής")
        log_btn.clicked.connect(self._open_log)
        refresh_log = QPushButton("Ανανέωση log")
        refresh_log.clicked.connect(self._refresh_log)
        dbg_btns.addWidget(test_btn)
        dbg_btns.addWidget(log_btn)
        dbg_btns.addWidget(refresh_log)
        dbg_btns.addStretch(1)
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

    def _test_ai(self) -> None:
        self.log_view.setPlainText("Έλεγχος providers…")
        run_async(self, ai.test_providers, on_done=self._on_tested,
                  on_error=lambda m: self.log_view.setPlainText(m))

    def _on_tested(self, results: list) -> None:
        lines = [("✓" if ok else "✗") + f"  {name}: {msg}" for name, ok, msg in results]
        self.log_view.setPlainText("\n".join(lines) or "—")

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
        model = self.openrouter_model.currentText().strip() or "meta-llama/llama-3.3-70b-instruct:free"
        if not model.endswith(":free"):
            model = f"{model}:free"
        SETTINGS.set("openrouter_model", model)
        order = [p.strip() for p in self.provider_order.text().split(",") if p.strip()]
        SETTINGS.set("ai_provider_order", order or ["custom", "openrouter", "groq", "duckduckgo", "pollinations"])
        SETTINGS.set("groq_api_key", self.groq_key.text().strip())
        SETTINGS.set("custom_ai_url", self.custom_url.text().strip())
        SETTINGS.set("custom_ai_model", self.custom_model.text().strip() or "llama3.1")
        SETTINGS.set("custom_ai_key", self.custom_key.text().strip())
        SETTINGS.set("openserp_url", self.openserp_url.text().strip() or "http://127.0.0.1:7000")
        SETTINGS.set("searxng_url", self.searxng_url.text().strip())
        SETTINGS.set("brave_api_key", self.brave_key.text().strip())
        SETTINGS.set("google_cse_api_key", self.cse_key.text().strip())
        SETTINGS.set("google_cse_id", self.cse_id.text().strip())
        SETTINGS.set("classify_in_english", self.classify_en.isChecked())
        SETTINGS.set("semantic_enabled", self.semantic_on.isChecked())
        SETTINGS.set("mymemory_email", self.mymemory_email.text().strip())
        SETTINGS.set("libretranslate_url", self.libre_url.text().strip())
        SETTINGS.set("libretranslate_api_key", self.libre_key.text().strip())
        SETTINGS.set("ocrspace_api_key", self.ocr_key.text().strip())
        SETTINGS.set("business_portal_key", self.business_key.text().strip())
        SETTINGS.set("auto_update_taric", self.auto_update.isChecked())
        SETTINGS.set("ml_confidence_threshold", float(self.threshold.value()))
        SETTINGS.set("theme", self.theme.currentText())
        SETTINGS.save()
        QMessageBox.information(self, "Ρυθμίσεις", "Οι ρυθμίσεις αποθηκεύτηκαν.")
