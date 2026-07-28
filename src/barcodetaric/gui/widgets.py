"""Επαναχρησιμοποιήσιμα custom widgets (StatTile, Card, section labels)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHeaderView, QLabel, QTableWidget,
    QVBoxLayout, QWidget,
)


def configure_table(table: QTableWidget, *, stretch: list[int] | None = None,
                    row_height: int = 34) -> None:
    """Κοινές ρυθμίσεις ευανάγνωστου πίνακα (alternating rows, elide, resize modes)."""
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.ElideRight)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(row_height)
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    cols = table.columnCount()
    stretch = stretch or []
    for i in range(cols):
        mode = QHeaderView.Stretch if i in stretch else QHeaderView.ResizeToContents
        header.setSectionResizeMode(i, mode)
    header.setStretchLastSection(not stretch)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")


class StatTile(QFrame):
    """Clickable πλακίδιο με μεγάλο αριθμό + λεζάντα.

    Υλοποιείται ως QFrame (όχι QPushButton) γιατί το QPushButton δεν φιλοξενεί σωστά
    εσωτερικό layout δύο γραμμών — ο αριθμός & η λεζάντα επικαλύπτονταν. Εκπέμπει
    `clicked` ώστε να παραμείνει συμβατό με τους callers.
    """

    clicked = Signal()

    def __init__(self, caption: str, value: str = "0", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("tile")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(78)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        self._value = QLabel(value)
        self._value.setObjectName("tileValue")
        self._caption = QLabel(caption)
        self._caption.setObjectName("muted")
        self._caption.setWordWrap(True)
        layout.addWidget(self._value)
        layout.addWidget(self._caption)
        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        self._value.setText(str(value))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


def section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("sectionLabel")
    return lbl


def h1(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("h1")
    return lbl


def h2(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("h2")
    return lbl


def muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("muted")
    return lbl


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: rgba(255,255,255,0.08);")
    line.setFixedHeight(1)
    return line
