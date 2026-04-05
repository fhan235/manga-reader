#!/usr/bin/env python3
"""
漫画阅读器 - macOS App 入口
双击启动后弹出独立窗口，无需浏览器、无需命令行。
"""

import os
import sys
import socket
import threading

# ==================== 资源路径解析 ====================
# PyInstaller 打包后资源在 sys._MEIPASS，开发时在脚本同级目录
if getattr(sys, 'frozen', False):
    # 打包后的 .app 环境
    BASE_DIR = sys._MEIPASS
    # 历史记录存到用户 Application Support 目录，而非 app 内部
    APP_SUPPORT = os.path.join(
        os.path.expanduser('~/Library/Application Support'),
        'MangaReader'
    )
    os.makedirs(APP_SUPPORT, exist_ok=True)
else:
    # 开发环境
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_SUPPORT = BASE_DIR

# 把 HISTORY_FILE 和 static_dir 设好，然后导入 server 模块
# 但由于 server.py 在模块顶层就定义了 HISTORY_FILE，我们需要先 patch
# 所以这里直接 import server 模块的内容并覆盖

# ==================== 导入 server 模块 ====================
# 将 BASE_DIR 加入 sys.path 以便 import
sys.path.insert(0, BASE_DIR)
import server

# Patch：让历史记录存到 APP_SUPPORT
server.HISTORY_FILE = os.path.join(APP_SUPPORT, '.manga_history.json')
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

# ==================== 主函数 ====================
def main():
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
    import time
    import urllib.request
    for _ in range(50):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.1)

    # 创建 pywebview 窗口
    window = webview.create_window(
        '漫画阅读器',
        url,
        width=1200,
        height=820,
        min_size=(800, 600),
        text_select=False,
        confirm_close=False,
    )

    # 启动 GUI 事件循环（macOS 上用 Cocoa 后端）
    webview.start(
        debug=not getattr(sys, 'frozen', False),
    )


if __name__ == '__main__':
    main()
