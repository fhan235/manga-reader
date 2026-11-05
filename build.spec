# -*- mode: python ; coding: utf-8 -*-
"""
漫画阅读器 PyInstaller 打包配置（macOS / Windows 通用）

用法:
    pyinstaller build.spec            # 生成目录版产物
    MR_ONEFILE=1 pyinstaller build.spec   # Windows 单文件 exe（启动稍慢）

平台差异:
    macOS   -> dist/漫画阅读器.app   （Cocoa + WebKit，BUNDLE 打包）
    Windows -> dist/MangaReader/MangaReader.exe（EdgeChromium/WebView2）
"""

import os
import sys

block_cipher = None
base_dir = os.path.dirname(os.path.abspath(SPEC))
IS_WIN = sys.platform.startswith('win')
IS_MAC = sys.platform == 'darwin'

# 单文件模式：只在 Windows/Linux 上生效（macOS 依旧出 .app）
ONEFILE = os.environ.get('MR_ONEFILE', '') in ('1', 'true', 'yes')
# 想看到控制台日志（排查启动问题）时设 MR_CONSOLE=1
CONSOLE = os.environ.get('MR_CONSOLE', '') in ('1', 'true', 'yes')
# 版本号（CI 里由 tag 注入，本地默认 1.0.0）
APP_VERSION = os.environ.get('APP_VERSION') or '1.0.0'

datas = [
    # 前端 HTML
    (os.path.join(base_dir, 'index.html'), '.'),
    # 后端 server 模块（app.py 在运行时 import 它）
    (os.path.join(base_dir, 'server.py'), '.'),
]

hiddenimports = ['webview']

if IS_WIN:
    # pywebview 的 Windows 后端：EdgeChromium(WebView2) 为主，WinForms 兜底。
    # 两者都通过 pythonnet(clr) 调 .NET，必须显式收集，否则打包后 ImportError。
    hiddenimports += [
        'webview.platforms.edgechromium',
        'webview.platforms.winforms',
        'webview.platforms.mshtml',
        'clr',
        'clr_loader',
        'pythonnet',
    ]
    # WebView2 的 .NET 程序集与 WebView2Loader.dll 在 webview/lib 下
    try:
        from PyInstaller.utils.hooks import collect_data_files
        datas += collect_data_files('webview', includes=['lib/**/*'])
    except Exception as exc:
        print(f'⚠️ 收集 webview/lib 失败: {exc}')
elif IS_MAC:
    hiddenimports += [
        'webview.platforms.cocoa',
        'objc',
        'Foundation',
        'AppKit',
        'WebKit',
        'PyObjCTools',
    ]

# tkinter 是 Windows / Linux 上「选择文件夹」用的原生对话框，必须保留；
# macOS 走 osascript，不需要 tkinter。
excludes = ['unittest', 'pydoc', 'pytest', 'numpy', 'pandas', 'matplotlib']
if IS_MAC:
    excludes.append('tkinter')

a = Analysis(
    [os.path.join(base_dir, 'app.py')],
    pathex=[base_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, cipher=block_cipher)

icon_file = os.path.join(
    base_dir, 'img.ico' if IS_WIN else 'img.icns')
if not os.path.exists(icon_file):
    icon_file = None

if ONEFILE and not IS_MAC:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name='MangaReader',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=CONSOLE,
        icon=icon_file,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='MangaReader',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,          # Windows 上 strip 会破坏部分 pyd，保持关闭
        upx=False,
        console=CONSOLE,      # Windows 无控制台窗口；排查时设 MR_CONSOLE=1
        icon=icon_file,
        target_arch=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name='MangaReader',
    )

    if IS_MAC:
        app = BUNDLE(
            coll,
            name='漫画阅读器.app',
            icon=os.path.join(base_dir, 'img.icns'),
            bundle_identifier='com.mangareader.app',
            info_plist={
                'CFBundleName': '漫画阅读器',
                'CFBundleDisplayName': '漫画阅读器',
                'CFBundleShortVersionString': APP_VERSION,
                'CFBundleVersion': APP_VERSION,
                'NSHighResolutionCapable': True,
                'LSMinimumSystemVersion': '10.15',
                'NSAppleEventsUsageDescription': '漫画阅读器需要此权限来选择文件夹',
            },
        )
