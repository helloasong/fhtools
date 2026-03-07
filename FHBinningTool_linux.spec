# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Linux
# Supports: Debian/Ubuntu based systems (统信UOS, 银河麒麟V10)
# Usage: pyinstaller FHBinningTool_linux.spec

import sys
import os

block_cipher = None

# Determine icon path (Linux typically uses .png or .xpm)
icon_path = None
for icon in ['assets/AppIcon.png', 'assets/AppIcon.xpm', 'assets/AppIcon.svg']:
    if os.path.exists(icon):
        icon_path = icon
        break

a = Analysis(
    ['src/ui/main_window.py'],
    pathex=[os.path.abspath(SPECPATH)],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('style.qss', '.'),
    ],
    hiddenimports=[
        'PyQt6.sip',
        'sklearn.tree._utils',
        'sklearn.utils._typedefs',
        'sklearn.utils._heap',
        'sklearn.utils._sorting',
        'sklearn.utils._vector_sentinel',
        'scipy.special.cython_special',
        'scipy.special._ufuncs_cxx',
        'pandas._libs.tslibs.base',
        'openpyxl',
        'qt_material',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib.backends.backend_tkagg',
        'IPython',
        'jupyter',
        'notebook',
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
    name='FHBinningTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

# Create a single directory distribution
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FHBinningTool',
)
