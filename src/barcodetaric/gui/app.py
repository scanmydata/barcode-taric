"""QApplication bootstrap."""

from __future__ import annotations

import sys

from ..config import SETTINGS
from ..db import init_db
from . import theme


def main() -> int:
    from PySide6.QtWidgets import QApplication

    init_db()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("BarcodeTaric")

    palette = theme.set_theme(str(SETTINGS.get("theme", "dark")))
    app.setStyleSheet(theme.build(palette))

    from .main_window import MainWindow
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
