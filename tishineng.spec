# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for TiShiNeng GUI.

Build from the repository root:
    .venv\\Scripts\\python -m PyInstaller tishineng.spec --clean --noconfirm
"""
from pathlib import Path


block_cipher = None

ROOT = Path(SPECPATH).resolve()

ICON_PATH = ROOT / "icon.ico"
if not ICON_PATH.exists():
    ICON_PATH = None
else:
    ICON_PATH = str(ICON_PATH)

a = Analysis(
    [str(ROOT / "gui_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "frontend"), "frontend"),
    ],
    hiddenimports=[
        "aiosqlite",
        "sqlalchemy.dialects.sqlite.aiosqlite",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "webview",
        "webview.platforms.edgechromium",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter.test",
        "test",
        "tests",
        "tkinter",
        "_tkinter",
        "tcl",
        "tk",
        "PySide6",
        "PyQt5",
        "PyQt6",
        "numpy.testing",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="TiShiNeng",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
    version=str(ROOT / "version_info.txt"),
)
