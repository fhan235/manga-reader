#!/usr/bin/env python3
"""
漫画阅读器 - 桌面端入口（macOS / Windows / Linux 通用）

双击启动后弹出独立窗口，无需浏览器、无需命令行。
- macOS  : Cocoa 后端（pywebview 自带）
- Windows: EdgeChromium 后端（需要 WebView2 Runtime，Win10/11 默认自带）
- Linux  : GTK / Qt 后端

命令行用法:
  MangaReader.exe                       # 打开上次的漫画
  MangaReader.exe "D:\\漫画\\火影忍者"    # 启动即打开指定目录
  MangaReader.exe "D:\\漫画\\火影.cbz"    # 启动即打开压缩包
"""

import os
import sys
import socket
import threading

IS_WIN = sys.platform.startswith('win')
IS_MAC = sys.platform == 'darwin'

APP_NAME = 'MangaReader'


# ==================== 资源路径解析 ====================
# PyInstaller 打包后资源在 sys._MEIPASS，开发时在脚本同级目录
FROZEN = getattr(sys, 'frozen', False)

if FROZEN:
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _user_data_dir():
    """历史记录 / 书架 / 进度 存到各平台的标准用户目录，而不是程序内部"""
    if IS_WIN:
        root = os.environ.get('APPDATA') or os.path.expanduser('~\\AppData\\Roaming')
        return os.path.join(root, APP_NAME)
    if IS_MAC:
        return os.path.join(
            os.path.expanduser('~/Library/Application Support'), APP_NAME)
    root = os.environ.get('XDG_DATA_HOME') or os.path.expanduser('~/.local/share')
    return os.path.join(root, APP_NAME)


# 打包后数据目录放用户目录；开发环境留在项目目录里，方便调试
if FROZEN:
    DATA_DIR = _user_data_dir()
else:
    DATA_DIR = BASE_DIR

os.makedirs(DATA_DIR, exist_ok=True)

# server.py 顶层就读这个环境变量定位数据文件，必须在 import server 之前设好
os.environ['MANGA_READER_DATA_DIR'] = DATA_DIR

# ==================== 导入 server 模块 ====================
sys.path.insert(0, BASE_DIR)
import server  # noqa: E402

# 兜底：即使 server 已被别处导入过，也把数据文件指到 DATA_DIR
server.DATA_DIR = DATA_DIR
server.HISTORY_FILE = os.path.join(DATA_DIR, '.manga_history.json')
server.LIBRARY_FILE = os.path.join(DATA_DIR, '.manga_library.json')
server.PROGRESS_FILE = os.path.join(DATA_DIR, '.manga_progress.json')
server.MangaHandler.static_dir = BASE_DIR


# ==================== 找可用端口 ====================
def find_free_port():
    """找一个可用端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


# ==================== 启动 HTTP 服务 ====================
def start_server(port):
    """在后台线程中启动 HTTP 服务"""
    srv = server.ThreadingHTTPServer(('127.0.0.1', port), server.MangaHandler)
    srv.serve_forever()


# ==================== 命令行参数 ====================
def parse_start_path(argv):
    """从命令行里取要打开的漫画路径（可选）"""
    for arg in argv[1:]:
        if arg.startswith('-'):
            continue
        candidate = os.path.abspath(os.path.expanduser(arg.strip('"\'')))
        if os.path.exists(candidate):
            return candidate
    return None


# ==================== 主函数 ====================
def main():
    import time
    import urllib.request
    import webview

    port = find_free_port()
    url = f'http://127.0.0.1:{port}'

    # 后台启动 HTTP 服务
    server.MangaHandler.manga_data = None
    server.MangaHandler.manga_root = None
    server.MangaHandler.static_dir = BASE_DIR

    t = threading.Thread(target=start_server, args=(port,), daemon=True)
    t.start()

    # 等待服务就绪
    for _ in range(80):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.1)

    # 如果命令行带了路径，先扫描好再开窗，避免前端闪一下空白
    start_path = parse_start_path(sys.argv)
    preloaded = None
    if start_path:
        preloaded = server.open_manga_path(start_path, record_history=True)
        if not preloaded.get('ok'):
            print(f"⚠️ 打开失败: {preloaded.get('error')}")

    window = webview.create_window(
        '漫画阅读器',
        url,
        width=1200,
        height=820,
        min_size=(800, 600),
        text_select=False,
        confirm_close=False,
    )

    # 启动 GUI 事件循环
    # Windows 上优先 EdgeChromium（WebView2）；没有的话 pywebview 会自己挑
    start_kwargs = {'debug': not FROZEN}
    if IS_WIN:
        start_kwargs['gui'] = 'edgechromium'
    try:
        webview.start(**start_kwargs)
    except Exception as exc:
        # WebView2 缺失 / 版本不匹配时退回 pywebview 默认后端
        print(f"⚠️ edgechromium 后端不可用（{exc}），改用默认后端")
        webview.start(debug=not FROZEN)
    return window


if __name__ == '__main__':
    main()
