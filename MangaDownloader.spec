# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the standalone windowed build (Phase 9).
#
# Build:  py -m PyInstaller --noconfirm --clean MangaDownloader.spec
# Output: dist\MangaDownloader.exe (one-file, no console, PNG + ICO bundled)

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("pystray")
# Pillow loads these formats lazily; make sure WebP/JPEG decoding ships in the exe.
hiddenimports += ["PIL._tkinter_finder"]

a = Analysis(
    ["manga_gui.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("MangaDownloader.png", "."),
        ("MangaDownloader.ico", "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="MangaDownloader",
    icon="MangaDownloader.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    version="version_info.txt",
)
