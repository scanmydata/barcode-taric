"""Αριστερό sidebar με sections. Pure emitter: εκπέμπει `triggered(name)`."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from .widgets import section_label

WIDTH = 232


class SideMenu(QWidget):
    triggered = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sideMenu")
        self.setFixedWidth(WIDTH)
        self._buttons: dict[str, QPushButton] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 12)
        root.setSpacing(4)

        title = QLabel("BarcodeTaric")
        title.setStyleSheet("font-size: 18px; font-weight: 800; padding: 4px 6px;")
        subtitle = QLabel("Πελατολόγιο & TARIC")
        subtitle.setObjectName("muted")
        subtitle.setStyleSheet("padding: 0 6px 6px 6px;")
        root.addWidget(title)
        root.addWidget(subtitle)

        new_client = QPushButton("＋  Νέος πελάτης")
        new_client.setObjectName("primary")
        new_client.setCursor(Qt.PointingHandCursor)
        new_client.clicked.connect(lambda: self.triggered.emit("new_client"))
        root.addWidget(new_client)
        root.addSpacing(6)

        self._add_nav(root, "clients", "👥  Πελάτες")
        self._add_nav(root, "codebook", "📋  Κωδικολόγιο")
        self._add_nav(root, "catalog", "🗂️  Βάση γνώσης")

        root.addSpacing(10)
        root.addWidget(section_label("ΔΕΔΟΜΕΝΑ"))
        self._add_nav(root, "taric", "🇪🇺  TARIC / Ενημερώσεις")

        root.addSpacing(10)
        root.addWidget(section_label("ΣΥΣΤΗΜΑ"))
        self._add_nav(root, "settings", "⚙️  Ρυθμίσεις")

        root.addStretch(1)
        version = QLabel("v0.1.0")
        version.setObjectName("muted")
        version.setAlignment(Qt.AlignCenter)
        root.addWidget(version)

        self.set_active("clients")

    def _add_nav(self, layout: QVBoxLayout, name: str, label: str) -> None:
        btn = QPushButton(label)
        btn.setObjectName("menuButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setProperty("active", False)
        btn.clicked.connect(lambda _=False, n=name: self.triggered.emit(n))
        layout.addWidget(btn)
        self._buttons[name] = btn

    def set_active(self, name: str) -> None:
        for key, btn in self._buttons.items():
            btn.setProperty("active", key == name)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
