# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置"""

block_cipher = None

a = Analysis(
    ['commondx.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.yaml', '.'),
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'Foundation',
        'AppKit',
        'Quartz',
        'ApplicationServices',
        'PyObjCTools',
        'PyObjCTools.AppHelper',
        'objc',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CommondX',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CommondX',
)

app = BUNDLE(
    coll,
    name='CommondX.app',
    icon='resources/icon.icns',
    bundle_identifier='com.liuns.commondx',
    info_plist={
        'CFBundleName': 'CommondX',
        'CFBundleDisplayName': 'CommondX',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.15',
        'LSUIElement': True,  # 不显示 Dock 图标
        'NSHighResolutionCapable': True,
        'NSAppleEventsUsageDescription': 'CommondX 需要控制 Finder 来获取选中的文件',
        'NSAccessibilityUsageDescription': 'CommondX 需要辅助功能权限来监听全局快捷键',
    },
)
