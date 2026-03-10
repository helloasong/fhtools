# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Windows - 企业环境兼容版（关闭 UPX）
# 
# 说明：
# - 关闭 UPX 压缩，避免触发企业安全软件（DEP、CFG、Device Guard）拦截
# - 适合云桌面、VDI 等企业受限环境使用
# - 体积会比标准版大 30-50%，但兼容性更好
#
# 使用方法：
#   pyinstaller FHBinningTool_windows_enterprise.spec
#
# 输出目录：dist/FHBinningTool_enterprise/

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
    upx=False,              # ← 关键：关闭 UPX 压缩，兼容企业安全环境
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

# 单目录分发（更稳定，不打包成单文件）
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,              # ← 关键：关闭 UPX 压缩
    upx_exclude=[],
    name='FHBinningTool_enterprise',
)
