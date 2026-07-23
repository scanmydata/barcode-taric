"""Δημιουργεί ένα απλό icon.ico (cyan «BT» σε σκούρο φόντο) χωρίς εξωτερικά assets.

Χρησιμοποιεί PySide6 (ήδη dependency). Αν λείπει, ο installer απλώς τρέχει χωρίς εικονίδιο.
"""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("PySide6 δεν είναι διαθέσιμο — παράλειψη δημιουργίας icon.")
        return 0

    app = QApplication.instance() or QApplication([])  # noqa: F841
    out = Path(__file__).with_name("icon.ico")

    sizes = [16, 32, 48, 64, 128, 256]
    pixmaps = []
    for size in sizes:
        img = QImage(size, size, QImage.Format_ARGB32)
        img.fill(Qt.transparent)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#0b1220"))
        painter.setPen(Qt.NoPen)
        radius = size * 0.22
        painter.drawRoundedRect(0, 0, size, size, radius, radius)
        painter.setPen(QColor("#38bdf8"))
        font = QFont("Segoe UI", int(size * 0.42), QFont.Bold)
        painter.setFont(font)
        painter.drawText(img.rect(), Qt.AlignCenter, "BT")
        painter.end()
        pixmaps.append(QPixmap.fromImage(img))

    icon = QIcon()
    for pm in pixmaps:
        icon.addPixmap(pm)
    # Αποθήκευση του μεγαλύτερου ως .ico (Qt γράφει multi-size αν υποστηρίζεται).
    pixmaps[-1].save(str(out), "ICO")
    print(f"Δημιουργήθηκε {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
