# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/ui/main_window.py'],
    pathex=[],
    binaries=[],
    datas=[('config.json', '.'), ('style.qss', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FHBinningTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FHBinningTool',
)
app = BUNDLE(
    coll,
    name='FHBinningTool.app',
    icon=None,
    bundle_identifier='com.fhtools.fhbinningtool',
)
