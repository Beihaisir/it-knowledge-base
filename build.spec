# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

base = os.path.abspath(".")

entry_datas = []
for d, _, files in os.walk(os.path.join(base, "entries")):
    for f in files:
        if f.endswith((".md", ".svg", ".png", ".jpg")):
            full = os.path.join(d, f)
            dest_dir = os.path.relpath(d, base)      # e.g. entries/assets
            entry_datas.append((full, dest_dir))

app_datas = []
for d, _, files in os.walk(os.path.join(base, "app")):
    for f in files:
        if f.endswith((".py", ".toml")):
            full = os.path.join(d, f)
            dest_dir = os.path.relpath(d, base)
            app_datas.append((full, dest_dir))

a = Analysis(
    ["launcher.py"],
    pathex=[base],
    binaries=[],
    datas=entry_datas + app_datas,
    hiddenimports=["streamlit", "requests", "yaml", "pytz", "rich"] + collect_submodules("streamlit"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pygame", "scipy", "matplotlib", "IPython", "jupyter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="IT知识库",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
