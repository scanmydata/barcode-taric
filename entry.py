#!/usr/bin/env python3
"""PyInstaller entry point. Wraps the GUI bootstrap so a frozen (console-less)
build shows a message box instead of dying silently on a startup error."""

from __future__ import annotations

import sys


def _run() -> int:
    from barcodetaric.gui.app import main
    return main()


if __name__ == "__main__":
    try:
        raise SystemExit(_run())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - last-resort GUI error surface
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "BarcodeTaric — Σφάλμα εκκίνησης", str(exc))
        except Exception:
            print(f"Startup error: {exc}", file=sys.stderr)
        raise SystemExit(1)
