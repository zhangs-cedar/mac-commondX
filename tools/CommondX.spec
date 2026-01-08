# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置"""

import os
SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
ROOT_DIR = os.path.dirname(SPEC_DIR)

a = Analysis(
    [os.path.join(ROOT_DIR, 'main.py')],
    pathex=[ROOT_DIR],
    binaries=[],
    datas=[
        (os.path.join(ROOT_DIR, 'config.yaml'), '.'),
    ],
    hiddenimports=[
        'Foundation',
        'AppKit',
        'Quartz',
        'ApplicationServices',
        'PyObjCTools',
        'PyObjCTools.AppHelper',
        'objc',
        'yaml',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CommondX',
    debug=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='CommondX',
)

app = BUNDLE(
    coll,
    name='CommondX.app',
    icon=None,
    bundle_identifier='com.liuns.commondx',
    info_plist={
        'CFBundleName': 'CommondX',
        'CFBundleDisplayName': 'CommondX',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.15',
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
        'NSAppleEventsUsageDescription': 'CommondX 需要控制 Finder 来获取选中的文件',
        'NSAccessibilityUsageDescription': 'CommondX 需要辅助功能权限来监听全局快捷键',
    },
)
