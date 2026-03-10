# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Windows (Single File Mode)
# Usage: pyinstaller FHBinningTool_windows_onefile.spec
# Note: Single file mode has slower startup but easier distribution

import sys
import os

block_cipher = None

# Determine icon path
icon_path = 'assets/AppIcon.ico' if os.path.exists('assets/AppIcon.ico') else None

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
    # Single file specific options
    onefile=True,
)
