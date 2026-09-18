# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the standalone windowed build (Phase 9).
#
# Build:  py -m PyInstaller --noconfirm --clean MangaDownloader.spec
# Output: dist\MangaDownloader.exe (one-file, no console, PNG + ICO bundled)

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules("pystray")
# Pillow loads these formats lazily; make sure WebP/JPEG decoding ships in the exe.
hiddenimports += ["PIL._tkinter_finder"]
# customtkinter: theme JSON data files + all widget submodules must ship.
hiddenimports += collect_submodules("customtkinter")
hiddenimports += ["ctk_compat"]

datas = [
    ("MangaDownloader.png", "."),
    ("MangaDownloader.ico", "."),
]
datas += collect_data_files("customtkinter")

a = Analysis(
    ["manga_gui.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
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
