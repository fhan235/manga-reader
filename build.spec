# -*- mode: python ; coding: utf-8 -*-
"""
漫画阅读器 PyInstaller 打包配置
用法: pyinstaller build.spec
"""

import os

block_cipher = None
base_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(base_dir, 'app.py')],
    pathex=[base_dir],
    binaries=[],
    datas=[
        # 打包前端 HTML
        (os.path.join(base_dir, 'index.html'), '.'),
        # 打包后端 server 模块
        (os.path.join(base_dir, 'server.py'), '.'),
    ],
    hiddenimports=[
        'webview',
        'webview.platforms.cocoa',
        'objc',
        'Foundation',
        'AppKit',
        'WebKit',
        'PyObjCTools',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pydoc',
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MangaReader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,  # 无控制台窗口
    target_arch=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    name='MangaReader',
)

app = BUNDLE(
    coll,
    name='漫画阅读器.app',
    icon=os.path.join(base_dir, 'icon.icns'),  # 自定义图标
    bundle_identifier='com.mangareader.app',
    info_plist={
        'CFBundleName': '漫画阅读器',
        'CFBundleDisplayName': '漫画阅读器',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15',
        'NSAppleEventsUsageDescription': '漫画阅读器需要此权限来选择文件夹',
    },
)
