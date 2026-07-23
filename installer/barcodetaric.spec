# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — one-dir bundle (όχι one-file: αποφυγή αργής εκκίνησης/antivirus)."""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(os.path.abspath(SPECPATH)).parent
SRC = ROOT / "src"

datas = []
icon_path = ROOT / "installer" / "icon.ico"

hiddenimports = []
for pkg in ("barcodetaric", "sklearn", "scipy", "joblib", "openpyxl", "bs4", "googlesearch"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    [str(ROOT / "entry.py")],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtMultimedia", "tkinter",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="BarcodeTaric",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon_path) if icon_path.exists() else None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, name="BarcodeTaric",
)
