"""Design tokens (dark/light) + QSS stylesheet — dark-first, cyan accent, rounded cards."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg: str
    panel: str
    chip: str
    line: str
    txt: str
    muted: str
    accent: str
    accent_txt: str
    ok: str
    bad: str
    warn: str
    menu_bg: str
    menu_txt: str
    row_alt: str
    header_bg: str


DARK = Palette(
    bg="#0b1220", panel="#111c30", chip="#16233c", line="#22334f",
    txt="#e6edf6", muted="#8ea3c0", accent="#38bdf8", accent_txt="#04202e",
    ok="#34d399", bad="#f87171", warn="#fbbf24", menu_bg="#0a1424", menu_txt="#c4d3ea",
    row_alt="#0e1a2e", header_bg="#16233c",
)

LIGHT = Palette(
    bg="#f3f6fb", panel="#ffffff", chip="#eef3fa", line="#d9e2ef",
    txt="#132033", muted="#5a6b85", accent="#0e7fbf", accent_txt="#ffffff",
    ok="#059669", bad="#dc2626", warn="#d97706", menu_bg="#0d1b2e", menu_txt="#c4d3ea",
    row_alt="#f5f8fc", header_bg="#eaf1f9",
)


class _Current:
    """Ζωντανός proxy — τα modules διαβάζουν πάντα το ενεργό palette."""
    palette: Palette = DARK


CURRENT = _Current()


def set_theme(name: str) -> Palette:
    CURRENT.palette = LIGHT if name == "light" else DARK
    return CURRENT.palette


def build(p: Palette) -> str:
    return f"""
    QWidget {{
        background: {p.bg};
        color: {p.txt};
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        font-size: 13px;
    }}
    QLabel#h1 {{ font-size: 22px; font-weight: 700; }}
    QLabel#h2 {{ font-size: 16px; font-weight: 600; }}
    QLabel#muted {{ color: {p.muted}; }}
    QLabel#sectionLabel {{ color: {p.muted}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}

    QFrame#card, QWidget#card {{
        background: {p.panel};
        border: 1px solid {p.line};
        border-radius: 14px;
    }}

    QWidget#sideMenu {{ background: {p.menu_bg}; }}
    QWidget#topbar {{ background: {p.bg}; }}

    QPushButton {{
        background: {p.chip};
        color: {p.txt};
        border: 1px solid {p.line};
        border-radius: 10px;
        padding: 8px 14px;
    }}
    QPushButton:hover {{ border-color: {p.accent}; }}
    QPushButton:disabled {{ color: {p.muted}; }}

    QPushButton#primary {{
        background: {p.accent};
        color: {p.accent_txt};
        border: none;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{ background: {p.accent}; }}
    QPushButton#danger {{ background: {p.bad}; color: white; border: none; }}

    QPushButton#menuButton {{
        background: transparent;
        color: {p.menu_txt};
        border: none;
        border-radius: 10px;
        padding: 9px 12px;
        text-align: left;
    }}
    QPushButton#menuButton:hover {{ background: rgba(255,255,255,0.06); }}
    QPushButton#menuButton[active="true"] {{
        background: {p.accent};
        color: {p.accent_txt};
        font-weight: 600;
    }}

    QFrame#tile {{
        background: {p.chip};
        border: 1px solid {p.line};
        border-radius: 12px;
    }}
    QFrame#tile:hover {{ border-color: {p.accent}; }}
    QLabel#tileValue {{ font-size: 26px; font-weight: 700; }}

    QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {p.chip};
        border: 1px solid {p.line};
        border-radius: 9px;
        padding: 7px 10px;
        selection-background-color: {p.accent};
    }}
    QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border-color: {p.accent}; }}
    QComboBox QAbstractItemView {{
        background: {p.panel};
        border: 1px solid {p.line};
        selection-background-color: {p.accent};
        selection-color: {p.accent_txt};
    }}

    QTableWidget, QTableView {{
        background: {p.panel};
        border: 1px solid {p.line};
        border-radius: 12px;
        gridline-color: {p.line};
        alternate-background-color: {p.row_alt};
        selection-background-color: {p.accent};
        selection-color: {p.accent_txt};
    }}
    QHeaderView::section {{
        background: {p.header_bg};
        color: {p.muted};
        border: none;
        border-bottom: 1px solid {p.line};
        padding: 9px 8px;
        font-weight: 700;
    }}
    QTableWidget::item, QTableView::item {{ padding: 6px 6px; }}
    QTableView {{ selection-color: {p.accent_txt}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {p.muted};
        margin-right: 8px;
    }}

    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {p.line}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::handle:vertical:hover {{ background: {p.accent}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

    QProgressBar {{
        background: {p.chip};
        border: 1px solid {p.line};
        border-radius: 8px;
        text-align: center;
        height: 16px;
    }}
    QProgressBar::chunk {{ background: {p.accent}; border-radius: 7px; }}

    QTabBar::tab {{
        background: {p.chip};
        padding: 8px 16px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    QTabBar::tab:selected {{ background: {p.accent}; color: {p.accent_txt}; }}
    QStatusBar {{ color: {p.muted}; }}
    QToolTip {{ background: {p.panel}; color: {p.txt}; border: 1px solid {p.line}; }}
    """
