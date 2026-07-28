"""Κύριο παράθυρο: sidebar + QStackedWidget (πελάτες/κωδικολόγιο/βάση/TARIC/ρυθμίσεις)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QStackedWidget, QStatusBar, QVBoxLayout, QWidget,
)

from .catalog_page import CatalogPage
from .clients_page import ClientsPage
from .codebook_page import CodebookPage
from .settings_page import SettingsPage
from .side_menu import SideMenu
from .taric_page import TaricPage
from . import theme

PAGE_INDEX = {"clients": 0, "codebook": 1, "catalog": 2, "taric": 3, "settings": 4}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BarcodeTaric — Πελατολόγιο & TARIC")
        self.resize(1280, 820)
        self.setMinimumSize(1080, 680)

        central = QWidget()
        self.setCentralWidget(central)
        shell = QHBoxLayout(central)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.menu = SideMenu()
        self.menu.triggered.connect(self._on_menu)
        shell.addWidget(self.menu)

        right = QWidget()
        right_l = QVBoxLayout(right)
        right_l.setContentsMargins(16, 14, 16, 10)
        right_l.setSpacing(10)

        topbar = QWidget()
        topbar.setObjectName("topbar")
        top_l = QHBoxLayout(topbar)
        top_l.setContentsMargins(0, 0, 0, 0)
        top_l.addStretch(1)
        self.active_label = QLabel("")
        self.active_label.setObjectName("muted")
        top_l.addWidget(self.active_label)
        right_l.addWidget(topbar)

        self.stack = QStackedWidget()
        self.clients_page = ClientsPage()
        self.codebook_page = CodebookPage()
        self.catalog_page = CatalogPage()
        self.taric_page = TaricPage()
        self.settings_page = SettingsPage()
        self.stack.addWidget(self.clients_page)
        self.stack.addWidget(self.codebook_page)
        self.stack.addWidget(self.catalog_page)
        self.stack.addWidget(self.taric_page)
        self.stack.addWidget(self.settings_page)
        right_l.addWidget(self.stack)
        shell.addWidget(right)

        self.setStatusBar(QStatusBar())

        # signals
        self.clients_page.open_codebook.connect(self._open_codebook)
        self.codebook_page.back_btn.clicked.connect(lambda: self._show("clients"))
        self.settings_page.theme_changed.connect(self._apply_theme)

        self._show("clients")
        self._startup_taric_check()
        self._warm_embeddings()

    # ------------------------------------------------------------- nav ----
    def _on_menu(self, name: str) -> None:
        if name == "new_client":
            self._show("clients")
            self.clients_page.new_client()
            return
        self._show(name)

    def _show(self, name: str) -> None:
        idx = PAGE_INDEX.get(name, 0)
        self.stack.setCurrentIndex(idx)
        self.menu.set_active(name if name in PAGE_INDEX else "clients")
        if name == "clients":
            self.clients_page.reload()
            self.active_label.setText("")
        elif name == "catalog":
            self.catalog_page.reload()
        elif name == "taric":
            self.taric_page.refresh()

    def _open_codebook(self, client_id: int) -> None:
        from .. import repo
        self.codebook_page.load_client(client_id)
        self.stack.setCurrentIndex(PAGE_INDEX["codebook"])
        self.menu.set_active("codebook")
        c = repo.get_client(client_id)
        self.active_label.setText(f"● {c.name}" if c else "")

    def _apply_theme(self, name: str) -> None:
        from PySide6.QtWidgets import QApplication
        palette = theme.set_theme(name)
        QApplication.instance().setStyleSheet(theme.build(palette))

    # ---------------------------------------------------- αυτόματη ενημέρωση ----
    def _startup_taric_check(self) -> None:
        """Στην εκκίνηση: αν είναι ενεργό, ελέγχει (και ενημερώνει) την ΕΕ ονοματολογία."""
        from ..config import SETTINGS
        from ..taric import updates
        from .workers import run_async
        if not SETTINGS.get("auto_update_taric"):
            return
        run_async(self, updates.check_for_updates, on_done=self._on_startup_check,
                  on_error=lambda _msg: None)

    def _on_startup_check(self, status) -> None:
        from ..taric import circabc
        from .workers import run_async
        if not (status.update_available or status.current_rows == 0):
            self.statusBar().showMessage(status.message, 8000)
            return
        self.statusBar().showMessage("Αυτόματη ενημέρωση ονοματολογίας TARIC από ΕΕ…")
        run_async(self, circabc.auto_import,
                  on_done=self._on_startup_updated,
                  on_error=lambda _msg: self.statusBar().showMessage(
                      "Η αυτόματη ενημέρωση TARIC απέτυχε — δοκιμάστε χειροκίνητα.", 8000),
                  on_progress=lambda m: self.statusBar().showMessage(m))

    def _on_startup_updated(self, n: int) -> None:
        self.statusBar().showMessage(f"Η ονοματολογία TARIC ενημερώθηκε από ΕΕ ({n} κωδικοί).", 10000)
        self.taric_page.refresh()
        self._warm_embeddings()

    def _warm_embeddings(self) -> None:
        """Χτίζει το εννοιολογικό μοντέλο (embeddings) σε background — το ΠΡΩΤΟ build
        της πλήρους ονοματολογίας είναι ακριβό (λεπτά σε CPU). Μέχρι να ετοιμαστεί, η
        κατάταξη δουλεύει με FTS· έτσι το UI δεν παγώνει ποτέ."""
        from ..engine import embeddings
        from .workers import run_async
        if not embeddings.available() or embeddings.is_cache_ready():
            return
        run_async(self, embeddings.warm, on_done=lambda _r: None, on_error=lambda _m: None,
                  on_progress=lambda m: self.statusBar().showMessage(m, 6000))
