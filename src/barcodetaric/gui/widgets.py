"""Επαναχρησιμοποιήσιμα custom widgets (StatTile, Card, section labels)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
<<<<<<< HEAD
    QAbstractItemView, QFrame, QHeaderView, QLabel, QTableWidget,
    QVBoxLayout, QWidget,
=======
    QAbstractItemView, QFrame, QHeaderView, QLabel, QPushButton, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
>>>>>>> b69f1c064e06f3062b3591fa58b396eb91ebe117
)


def configure_table(table: QTableWidget, *, stretch: list[int] | None = None,
                    row_height: int = 34, multiselect: bool = True,
                    sortable: bool = True) -> None:
    """Κοινές ρυθμίσεις ευανάγνωστου πίνακα.

    - alternating rows, elide, resize modes
    - **sortable**: κλικ στην κεφαλίδα ταξινομεί (numeric-aware μέσω `NumericItem`)
    - **reorderable**: σύρσιμο στηλών (movable header sections)
    - **multiselect**: πολλαπλή επιλογή γραμμών (Ctrl/Shift) για μαζικές ενέργειες
    """
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(
        QAbstractItemView.ExtendedSelection if multiselect else QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.ElideRight)
    table.setSortingEnabled(sortable)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(row_height)
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setSectionsMovable(True)          # reorderable στήλες (drag & drop)
    header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    cols = table.columnCount()
    stretch = stretch or []
    for i in range(cols):
        mode = QHeaderView.Stretch if i in stretch else QHeaderView.ResizeToContents
        header.setSectionResizeMode(i, mode)
    header.setStretchLastSection(not stretch)


class NumericItem(QTableWidgetItem):
    """QTableWidgetItem που ταξινομείται ΑΡΙΘΜΗΤΙΚΑ (όχι λεξικογραφικά: 2 < 10)."""

    def __init__(self, value) -> None:
        super().__init__(str(value))
        try:
            self._num = float(value)
        except (TypeError, ValueError):
            self._num = float("-inf")

    def __lt__(self, other) -> bool:  # type: ignore[override]
        if isinstance(other, NumericItem):
            return self._num < other._num
        return super().__lt__(other)


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
<<<<<<< HEAD
        self.setMinimumHeight(78)
=======
        # Ένα QPushButton με εσωτερικό layout δεν κρατά ύψος για τα child labels -> το μεγάλο
        # νούμερο (26px) «πατούσε» πάνω στη λεζάντα. Εγγυημένο ύψος + size policy το λύνει.
        self.setMinimumHeight(84)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
>>>>>>> b69f1c064e06f3062b3591fa58b396eb91ebe117
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        self._value = QLabel(value)
<<<<<<< HEAD
        self._value.setObjectName("tileValue")
        self._caption = QLabel(caption)
        self._caption.setObjectName("muted")
        self._caption.setWordWrap(True)
=======
        self._value.setStyleSheet("font-size: 24px; font-weight: 700; background: transparent;")
        self._value.setMinimumHeight(34)
        self._caption = QLabel(caption)
        self._caption.setObjectName("muted")
        self._caption.setWordWrap(True)
        self._caption.setStyleSheet("background: transparent;")
>>>>>>> b69f1c064e06f3062b3591fa58b396eb91ebe117
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
    lbl.setWordWrap(True)      # αποφυγή οριζόντιου overflow σε μεγάλους τίτλους
    return lbl


def muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("muted")
    # Χωρίς wrap, οι μεγάλες βοηθητικές γραμμές «σπρώχνουν» το card πέρα από το παράθυρο
    # και κόβονται δεξιά. Το wrap κρατά το πλάτος μέσα στα όρια της σελίδας.
    lbl.setWordWrap(True)
    return lbl


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("color: rgba(255,255,255,0.08);")
    line.setFixedHeight(1)
    return line
