#!/usr/bin/env python3
"""
Mac 本地漫画阅读器 - 后端服务
用法:
  python3 server.py                          # 无参启动，在浏览器里选择文件夹
  python3 server.py /path/to/manga/folder    # 直接指定路径
  python3 server.py /path/to/manga.zip       # 直接打开压缩包
  python3 server.py --port 8899              # 自定义端口
"""

import os
import sys
import json
import argparse
import mimetypes
import webbrowser
import urllib.parse
import subprocess
import re
import zipfile
import tempfile
import shutil
import atexit
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# 尝试导入 rarfile（可选依赖）
try:
    import rarfile
    HAS_RAR = True
except ImportError:
    HAS_RAR = False

# 支持的图片格式
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif', '.avif'}

# 支持的压缩包格式
ARCHIVE_EXTENSIONS = {'.zip', '.cbz', '.cbr', '.rar', '.epub'}

# 最近打开记录文件
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.manga_history.json')
MAX_HISTORY = 20

# 书架数据文件
LIBRARY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.manga_library.json')

# 阅读进度文件（精确到页）
PROGRESS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.manga_progress.json')

# 临时解压目录管理
_temp_dirs = []

def _cleanup_temp_dirs():
    """程序退出时清理临时目录"""
    for d in _temp_dirs:
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass

atexit.register(_cleanup_temp_dirs)


def natural_sort_key(s):
    """自然排序：让 '第2话' 排在 '第10话' 前面"""
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', str(s))]


# ==================== 压缩包解压 ====================

def is_image_file(filename):
    """判断文件名是否为图片"""
    return Path(filename).suffix.lower() in IMAGE_EXTENSIONS


def extract_zip(archive_path, dest_dir):
    """解压 ZIP/CBZ 文件"""
    with zipfile.ZipFile(archive_path, 'r') as zf:
        # 过滤掉 macOS 的 __MACOSX 等垃圾
        members = [m for m in zf.namelist()
                   if not m.startswith('__MACOSX') and not m.startswith('.')]
        zf.extractall(dest_dir, members)


def extract_rar(archive_path, dest_dir):
    """解压 RAR/CBR 文件"""
    if not HAS_RAR:
        raise RuntimeError("需要安装 rarfile 库来支持 RAR/CBR 格式：pip3 install rarfile\n同时需要系统安装 unrar 命令")
    with rarfile.RarFile(archive_path, 'r') as rf:
        rf.extractall(dest_dir)


def extract_epub_images(epub_path, dest_dir):
    """
    从 EPUB 中提取图片。
    EPUB 本质是 ZIP，我们解析 OPF 找到 spine 里的图片顺序。
    只支持图片型漫画 EPUB。
    """
    with zipfile.ZipFile(epub_path, 'r') as zf:
        # 1. 读 META-INF/container.xml 找到 OPF 文件路径
        try:
            container = zf.read('META-INF/container.xml').decode('utf-8')
        except KeyError:
            # 不是标准 EPUB，当普通 ZIP 处理
            extract_zip(epub_path, dest_dir)
            return

        import xml.etree.ElementTree as ET
        root = ET.fromstring(container)
        ns = {'c': 'urn:oasis:names:tc:opendocument:xmlns:container'}
        rootfile_el = root.find('.//c:rootfile', ns)
        if rootfile_el is None:
            extract_zip(epub_path, dest_dir)
            return

        opf_path = rootfile_el.get('full-path', '')
        opf_dir = os.path.dirname(opf_path) if '/' in opf_path else ''

        # 2. 解析 OPF
        try:
            opf_content = zf.read(opf_path).decode('utf-8')
        except KeyError:
            extract_zip(epub_path, dest_dir)
            return

        opf_root = ET.fromstring(opf_content)
        # 处理命名空间
        opf_ns = {
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }

        # 3. 从 manifest 提取所有图片项
        manifest = {}
        for item in opf_root.findall('.//opf:manifest/opf:item', opf_ns):
            item_id = item.get('id', '')
            href = item.get('href', '')
            media_type = item.get('media-type', '')
            manifest[item_id] = {'href': href, 'media_type': media_type}

        # 4. 按 spine 顺序找到引用的图片
        spine_order = []
        for itemref in opf_root.findall('.//opf:spine/opf:itemref', opf_ns):
            idref = itemref.get('idref', '')
            if idref in manifest:
                spine_order.append(manifest[idref])

        # 5. 提取图片文件
        # 策略：先尝试从 spine 引用的 XHTML 中找图片，或直接找 manifest 中的图片
        image_items = []

        # 方式 A：直接是图片的 spine 项
        for item in spine_order:
            if item['media_type'].startswith('image/'):
                image_items.append(item['href'])

        # 方式 B：spine 引用的是 XHTML，从中提取 img src
        if not image_items:
            for item in spine_order:
                if 'html' in item['media_type'] or 'xml' in item['media_type']:
                    href = item['href']
                    full_path = f"{opf_dir}/{href}" if opf_dir else href
                    try:
                        html_content = zf.read(full_path).decode('utf-8')
                        # 用正则找 img src 或 image xlink:href
                        img_srcs = re.findall(r'(?:src|xlink:href)=["\']([^"\']+\.(jpe?g|png|gif|webp|bmp|tiff?|avif))["\']',
                                             html_content, re.IGNORECASE)
                        for src_match in img_srcs:
                            img_src = src_match[0]
                            # 相对路径转换
                            if not img_src.startswith('/'):
                                html_dir = os.path.dirname(full_path)
                                img_src = os.path.normpath(f"{html_dir}/{img_src}") if html_dir else img_src
                            image_items.append(img_src)
                    except Exception:
                        continue

        # 方式 C：如果还是没找到，直接提取所有图片
        if not image_items:
            for name in zf.namelist():
                if is_image_file(name) and not name.startswith('__MACOSX'):
                    image_items.append(name)
            image_items.sort(key=natural_sort_key)

        # 6. 提取图片到目标目录，按序号重命名保持顺序
        os.makedirs(dest_dir, exist_ok=True)
        for idx, img_path in enumerate(image_items):
            try:
                # 处理路径（EPUB 内部路径可能有 ../ 等）
                img_path_clean = img_path.replace('\\', '/')
                if img_path_clean.startswith('/'):
                    img_path_clean = img_path_clean[1:]

                img_data = zf.read(img_path_clean)
                ext = Path(img_path_clean).suffix.lower()
                if not ext:
                    ext = '.jpg'
                # 用序号命名保持顺序
                out_name = f"{idx + 1:04d}{ext}"
                out_path = os.path.join(dest_dir, out_name)
                with open(out_path, 'wb') as f:
                    f.write(img_data)
            except (KeyError, Exception):
                continue


def extract_archive(archive_path, dest_dir=None):
    """
    解压压缩包到临时/指定目录，返回解压后的路径。
    """
    ext = Path(archive_path).suffix.lower()

    if dest_dir is None:
        dest_dir = tempfile.mkdtemp(prefix='manga_reader_')
        _temp_dirs.append(dest_dir)

    if ext in ('.zip', '.cbz'):
        extract_zip(archive_path, dest_dir)
    elif ext in ('.rar', '.cbr'):
        extract_rar(archive_path, dest_dir)
    elif ext == '.epub':
        extract_epub_images(archive_path, dest_dir)
    else:
        raise ValueError(f"不支持的格式: {ext}")

    return dest_dir


# ==================== 漫画扫描 ====================

def scan_manga_folder(root_path):
    """扫描漫画根目录，返回章节列表。支持文件夹和压缩包。"""
    root_path = str(root_path)

    # 如果是压缩包文件
    if os.path.isfile(root_path) and Path(root_path).suffix.lower() in ARCHIVE_EXTENSIONS:
        return scan_archive(root_path)

    root = Path(root_path)
    if not root.is_dir():
        return {"error": f"路径不存在或不是目录: {root_path}"}

    manga_name = root.name
    chapters = []

    # 获取所有子文件夹（章节）
    subdirs = sorted(
        [d for d in root.iterdir() if d.is_dir() and not d.name.startswith('.')],
        key=lambda d: natural_sort_key(d.name)
    )

    # 检查根目录是否包含压缩包文件
    archive_files = sorted(
        [f for f in root.iterdir() if f.is_file() and f.suffix.lower() in ARCHIVE_EXTENSIONS],
        key=lambda f: natural_sort_key(f.name)
    )

    # 检查根目录自身是否直接包含图片（单章节情况）
    root_images = sorted(
        [f for f in root.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda f: natural_sort_key(f.name)
    )

    if not subdirs and not archive_files and root_images:
        # 单章节：根目录直接有图片
        chapters.append({
            "name": manga_name,
            "path": "",
            "image_count": len(root_images),
            "images": [f.name for f in root_images]
        })
    else:
        # 多章节：先处理子文件夹
        for subdir in subdirs:
            images = sorted(
                [f for f in subdir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS],
                key=lambda f: natural_sort_key(f.name)
            )
            if images:
                chapters.append({
                    "name": subdir.name,
                    "path": subdir.name,
                    "image_count": len(images),
                    "images": [f.name for f in images]
                })

        # 再处理压缩包文件（每个压缩包当一个章节）
        for archive_file in archive_files:
            try:
                dest_dir = extract_archive(str(archive_file))
                # 扫描解压后的目录
                extracted_images = _collect_images_from_dir(dest_dir)
                if extracted_images:
                    # 用压缩包文件名（去掉扩展名）作为章节名
                    ch_name = archive_file.stem
                    chapters.append({
                        "name": ch_name,
                        "path": "",  # 特殊标记
                        "image_count": len(extracted_images),
                        "images": [img for img in extracted_images],
                        "_extracted_dir": dest_dir,  # 内部用
                    })
            except Exception as e:
                print(f"⚠️ 解压失败 {archive_file.name}: {e}")

        # 如果有根目录图片但也有子目录/压缩包，把根目录图片也作为一个章节
        if root_images and (subdirs or archive_files):
            chapters.insert(0, {
                "name": f"{manga_name} (散图)",
                "path": "",
                "image_count": len(root_images),
                "images": [f.name for f in root_images]
            })

    return {
        "manga_name": manga_name,
        "root_path": str(root),
        "chapter_count": len(chapters),
        "chapters": chapters,
        "source_type": "folder",
    }


def scan_archive(archive_path):
    """扫描单个压缩包文件"""
    archive_path = str(archive_path)
    manga_name = Path(archive_path).stem  # 去掉扩展名

    try:
        dest_dir = extract_archive(archive_path)
    except Exception as e:
        return {"error": f"解压失败: {e}"}

    # 检查解压后的结构
    dest = Path(dest_dir)

    # 可能解压后有子文件夹（多章节）
    subdirs = sorted(
        [d for d in dest.iterdir() if d.is_dir() and not d.name.startswith('.')],
        key=lambda d: natural_sort_key(d.name)
    )

    root_images = sorted(
        [f for f in dest.iterdir() if f.is_file() and is_image_file(f.name)],
        key=lambda f: natural_sort_key(f.name)
    )

    chapters = []

    # 如果只有一个子目录且没有根级图片，进入那个子目录
    if len(subdirs) == 1 and not root_images:
        single_dir = subdirs[0]
        inner_subdirs = sorted(
            [d for d in single_dir.iterdir() if d.is_dir() and not d.name.startswith('.')],
            key=lambda d: natural_sort_key(d.name)
        )
        inner_images = sorted(
            [f for f in single_dir.iterdir() if f.is_file() and is_image_file(f.name)],
            key=lambda f: natural_sort_key(f.name)
        )

        if inner_subdirs:
            for subdir in inner_subdirs:
                images = sorted(
                    [f for f in subdir.iterdir() if f.is_file() and is_image_file(f.name)],
                    key=lambda f: natural_sort_key(f.name)
                )
                if images:
                    rel_path = str(subdir.relative_to(dest))
                    chapters.append({
                        "name": subdir.name,
                        "path": rel_path,
                        "image_count": len(images),
                        "images": [f.name for f in images]
                    })
        elif inner_images:
            rel_path = str(single_dir.relative_to(dest))
            chapters.append({
                "name": manga_name,
                "path": rel_path,
                "image_count": len(inner_images),
                "images": [f.name for f in inner_images]
            })
    elif subdirs and not root_images:
        for subdir in subdirs:
            images = sorted(
                [f for f in subdir.iterdir() if f.is_file() and is_image_file(f.name)],
                key=lambda f: natural_sort_key(f.name)
            )
            if images:
                rel_path = str(subdir.relative_to(dest))
                chapters.append({
                    "name": subdir.name,
                    "path": rel_path,
                    "image_count": len(images),
                    "images": [f.name for f in images]
                })
    elif root_images and not subdirs:
        chapters.append({
            "name": manga_name,
            "path": "",
            "image_count": len(root_images),
            "images": [f.name for f in root_images]
        })
    else:
        # 混合情况
        if root_images:
            chapters.append({
                "name": f"{manga_name} (散图)",
                "path": "",
                "image_count": len(root_images),
                "images": [f.name for f in root_images]
            })
        for subdir in subdirs:
            images = sorted(
                [f for f in subdir.iterdir() if f.is_file() and is_image_file(f.name)],
                key=lambda f: natural_sort_key(f.name)
            )
            if images:
                rel_path = str(subdir.relative_to(dest))
                chapters.append({
                    "name": subdir.name,
                    "path": rel_path,
                    "image_count": len(images),
                    "images": [f.name for f in images]
                })

    if not chapters:
        return {"error": "压缩包中未找到漫画图片"}

    return {
        "manga_name": manga_name,
        "root_path": dest_dir,  # 解压后的临时目录作为 root
        "original_path": archive_path,  # 保留原始压缩包路径
        "chapter_count": len(chapters),
        "chapters": chapters,
        "source_type": "archive",
    }


def _collect_images_from_dir(dir_path):
    """递归收集目录中所有图片，返回相对路径列表"""
    images = []
    for root, dirs, files in os.walk(dir_path):
        # 跳过隐藏目录和 macOS 垃圾
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__MACOSX']
        for f in files:
            if is_image_file(f) and not f.startswith('.'):
                full = os.path.join(root, f)
                rel = os.path.relpath(full, dir_path)
                images.append(rel)
    images.sort(key=natural_sort_key)
    return images


# ==================== 历史记录管理 ====================

def load_history():
    """读取最近打开的漫画路径"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 过滤掉已不存在的路径
                return [item for item in data
                        if os.path.isdir(item['path']) or os.path.isfile(item['path'])]
    except Exception:
        pass
    return []

def save_history(history):
    """保存最近打开记录"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history[:MAX_HISTORY], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def add_to_history(manga_path, manga_name):
    """将路径添加到历史记录"""
    history = load_history()
    # 去掉重复项
    history = [h for h in history if h['path'] != manga_path]
    # 插入到最前面
    history.insert(0, {
        'path': manga_path,
        'name': manga_name,
    })
    save_history(history)


# ==================== 书架/书库管理 ====================

def load_library():
    """读取书架数据"""
    try:
        if os.path.exists(LIBRARY_FILE):
            with open(LIBRARY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_library(library):
    """保存书架数据"""
    try:
        with open(LIBRARY_FILE, 'w', encoding='utf-8') as f:
            json.dump(library, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def add_to_library(manga_path, manga_name, chapter_count, cover_path=None):
    """添加漫画到书架"""
    library = load_library()
    # 去重
    library = [item for item in library if item['path'] != manga_path]
    library.append({
        'path': manga_path,
        'name': manga_name,
        'chapter_count': chapter_count,
        'cover': cover_path,
        'added_at': __import__('time').time(),
    })
    save_library(library)
    return library

def remove_from_library(manga_path):
    """从书架移除漫画"""
    library = load_library()
    library = [item for item in library if item['path'] != manga_path]
    save_library(library)
    return library


# ==================== 阅读进度管理（精确到页）====================

def load_all_progress():
    """读取所有阅读进度"""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_all_progress(data):
    """保存所有阅读进度"""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def save_progress(manga_name, chapter_index, page_index):
    """保存某部漫画的阅读进度（精确到页）"""
    data = load_all_progress()
    data[manga_name] = {
        'chapter': chapter_index,
        'page': page_index,
    }
    save_all_progress(data)

def get_progress(manga_name):
    """获取某部漫画的阅读进度"""
    data = load_all_progress()
    return data.get(manga_name, None)


# ==================== macOS 文件选择 ====================

def pick_folder_macos():
    """调用 macOS 原生文件夹选择对话框"""
    script = '''
    tell application "System Events"
        activate
    end tell
    set chosenFolder to choose folder with prompt "选择漫画文件夹" default location (path to home folder)
    return POSIX path of chosenFolder
    '''
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            path = result.stdout.strip().rstrip('/')
            if path and os.path.isdir(path):
                return path
    except Exception:
        pass
    return None


def pick_file_macos():
    """调用 macOS 原生文件选择对话框，选择压缩包文件"""
    extensions = ' '.join([f'"{ext[1:]}"' for ext in ARCHIVE_EXTENSIONS])
    script = f'''
    tell application "System Events"
        activate
    end tell
    set chosenFile to choose file with prompt "选择漫画文件（ZIP/CBZ/RAR/CBR/EPUB）" of type {{{extensions}}} default location (path to home folder)
    return POSIX path of chosenFile
    '''
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            if path and os.path.isfile(path):
                return path
    except Exception:
        pass
    return None


# ==================== HTTP Handler ====================

class MangaHandler(SimpleHTTPRequestHandler):
    """处理漫画阅读器的 HTTP 请求"""

    manga_root = None
    manga_data = None
    static_dir = None
    original_path = None  # 记录原始路径（压缩包时用）

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/' or path == '/index.html':
            self.serve_static('index.html')
        elif path == '/api/manga':
            # 返回漫画数据时去掉内部字段
            if self.manga_data:
                clean_data = dict(self.manga_data)
                clean_chapters = []
                for ch in clean_data.get('chapters', []):
                    clean_ch = {k: v for k, v in ch.items() if not k.startswith('_')}
                    clean_chapters.append(clean_ch)
                clean_data['chapters'] = clean_chapters
                self.serve_json(clean_data)
            else:
                self.serve_json(None)
        elif path == '/api/history':
            self.serve_json(load_history())
        elif path == '/api/pick-folder':
            self.handle_pick_folder()
        elif path == '/api/pick-file':
            self.handle_pick_file()
        elif path == '/api/library':
            self.serve_json(load_library())
        elif path == '/api/progress':
            query = urllib.parse.parse_qs(parsed.query)
            manga_name = query.get('name', [''])[0]
            if manga_name:
                self.serve_json(get_progress(manga_name))
            else:
                self.serve_json(load_all_progress())
        elif path == '/api/cover':
            query = urllib.parse.parse_qs(parsed.query)
            manga_path = query.get('path', [''])[0]
            self.serve_cover(manga_path)
        elif path.startswith('/images/'):
            self.serve_image(path[8:])
        elif path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
        else:
            self.serve_static(path.lstrip('/'))

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/open':
            self.handle_open_folder()
        elif path == '/api/remove-history':
            self.handle_remove_history()
        elif path == '/api/library/add':
            self.handle_library_add()
        elif path == '/api/library/remove':
            self.handle_library_remove()
        elif path == '/api/progress/save':
            self.handle_save_progress()
        else:
            self.send_error(404)

    def handle_pick_folder(self):
        """弹出 macOS 原生文件夹选择对话框"""
        folder = pick_folder_macos()
        if not folder:
            self.serve_json({"ok": False, "error": "未选择文件夹"})
            return
        self._switch_manga(folder)

    def handle_pick_file(self):
        """弹出 macOS 原生文件选择对话框（压缩包）"""
        file_path = pick_file_macos()
        if not file_path:
            self.serve_json({"ok": False, "error": "未选择文件"})
            return
        self._switch_manga(file_path)

    def handle_open_folder(self):
        """通过传入路径切换漫画"""
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body.decode('utf-8'))
            folder = data.get('path', '').strip()
        except Exception:
            self.serve_json({"ok": False, "error": "无效请求"})
            return

        if not folder:
            self.serve_json({"ok": False, "error": "路径为空"})
            return

        folder = os.path.expanduser(folder)
        folder = os.path.abspath(folder)
        self._switch_manga(folder)

    def _switch_manga(self, path):
        """切换到新的漫画（文件夹或压缩包）"""
        is_file = os.path.isfile(path)
        is_dir = os.path.isdir(path)

        if not is_file and not is_dir:
            self.serve_json({"ok": False, "error": f"路径不存在: {path}"})
            return

        if is_file and Path(path).suffix.lower() not in ARCHIVE_EXTENSIONS:
            self.serve_json({"ok": False, "error": f"不支持的文件格式: {Path(path).suffix}"})
            return

        manga_data = scan_manga_folder(path)
        if "error" in manga_data:
            self.serve_json({"ok": False, "error": manga_data['error']})
            return

        if manga_data['chapter_count'] == 0:
            self.serve_json({"ok": False, "error": "未找到漫画图片"})
            return

        # 更新全局状态
        MangaHandler.manga_root = manga_data['root_path']
        MangaHandler.manga_data = manga_data
        MangaHandler.original_path = manga_data.get('original_path', path)

        # 写入历史记录（存原始路径）
        history_path = manga_data.get('original_path', path)
        add_to_history(history_path, manga_data['manga_name'])

        # 自动加入书架
        cover = self._get_first_cover(manga_data)
        add_to_library(history_path, manga_data['manga_name'],
                       manga_data['chapter_count'], cover)

        # 获取阅读进度
        progress = get_progress(manga_data['manga_name'])

        print(f"📂 切换到: {path} ({manga_data['chapter_count']} 章)")

        # 返回时去掉内部字段
        clean_data = dict(manga_data)
        clean_chapters = []
        for ch in clean_data.get('chapters', []):
            clean_ch = {k: v for k, v in ch.items() if not k.startswith('_')}
            clean_chapters.append(clean_ch)
        clean_data['chapters'] = clean_chapters

        self.serve_json({
            "ok": True,
            "manga": clean_data,
            "progress": progress,
        })

    def _get_first_cover(self, manga_data):
        """获取第一章第一张图的路径（用于封面）"""
        if manga_data['chapters']:
            ch = manga_data['chapters'][0]
            if ch['images']:
                return ch['images'][0]
        return None

    def handle_remove_history(self):
        """从历史记录中移除一条"""
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body.decode('utf-8'))
            path_to_remove = data.get('path', '')
        except Exception:
            self.serve_json({"ok": False})
            return

        history = load_history()
        history = [h for h in history if h['path'] != path_to_remove]
        save_history(history)
        self.serve_json({"ok": True, "history": history})

    def handle_library_add(self):
        """添加到书架"""
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body.decode('utf-8'))
            path = data.get('path', '')
            name = data.get('name', '')
            chapter_count = data.get('chapter_count', 0)
            cover = data.get('cover', None)
        except Exception:
            self.serve_json({"ok": False})
            return
        library = add_to_library(path, name, chapter_count, cover)
        self.serve_json({"ok": True, "library": library})

    def handle_library_remove(self):
        """从书架移除"""
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body.decode('utf-8'))
            path = data.get('path', '')
        except Exception:
            self.serve_json({"ok": False})
            return
        library = remove_from_library(path)
        self.serve_json({"ok": True, "library": library})

    def handle_save_progress(self):
        """保存阅读进度（精确到页）"""
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        try:
            data = json.loads(body.decode('utf-8'))
            manga_name = data.get('manga_name', '')
            chapter = data.get('chapter', 0)
            page = data.get('page', 0)
        except Exception:
            self.serve_json({"ok": False})
            return
        if manga_name:
            save_progress(manga_name, chapter, page)
            self.serve_json({"ok": True})
        else:
            self.serve_json({"ok": False, "error": "缺少漫画名"})

    def serve_cover(self, manga_path):
        """生成封面缩略图"""
        manga_path = urllib.parse.unquote(manga_path)
        if not manga_path:
            self.send_error(404)
            return

        # 如果当前正在看这部漫画，直接用 manga_root
        if self.manga_data and (manga_path == self.manga_data.get('root_path') or
                                 manga_path == self.manga_data.get('original_path') or
                                 manga_path == MangaHandler.original_path):
            if self.manga_data['chapters'] and self.manga_data['chapters'][0]['images']:
                ch = self.manga_data['chapters'][0]
                img_name = ch['images'][0]
                img_path = ch['path']
                if img_path:
                    file_path = Path(self.manga_root) / img_path / img_name
                else:
                    file_path = Path(self.manga_root) / img_name
                if file_path.is_file():
                    self._serve_file(file_path)
                    return

        # 否则尝试扫描并获取第一张图
        try:
            if os.path.isfile(manga_path) and Path(manga_path).suffix.lower() in ARCHIVE_EXTENSIONS:
                # 压缩包，快速提取第一张图
                self._serve_archive_cover(manga_path)
                return
            elif os.path.isdir(manga_path):
                data = scan_manga_folder(manga_path)
                if data.get('chapters') and data['chapters'][0]['images']:
                    ch = data['chapters'][0]
                    img_name = ch['images'][0]
                    img_path = ch['path']
                    root = data['root_path']
                    if img_path:
                        file_path = Path(root) / img_path / img_name
                    else:
                        file_path = Path(root) / img_name
                    if file_path.is_file():
                        self._serve_file(file_path)
                        return
        except Exception:
            pass

        self.send_error(404, "Cover not found")

    def _serve_archive_cover(self, archive_path):
        """从压缩包中快速提取第一张图作为封面"""
        ext = Path(archive_path).suffix.lower()
        try:
            if ext in ('.zip', '.cbz', '.epub'):
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    image_names = sorted(
                        [n for n in zf.namelist()
                         if is_image_file(n) and not n.startswith('__MACOSX') and not n.startswith('.')],
                        key=natural_sort_key
                    )
                    if image_names:
                        data = zf.read(image_names[0])
                        mime_type, _ = mimetypes.guess_type(image_names[0])
                        if not mime_type:
                            mime_type = 'image/jpeg'
                        self.send_response(200)
                        self.send_header('Content-Type', mime_type)
                        self.send_header('Content-Length', len(data))
                        self.send_header('Cache-Control', 'public, max-age=3600')
                        self.end_headers()
                        self.wfile.write(data)
                        return
            elif ext in ('.rar', '.cbr') and HAS_RAR:
                with rarfile.RarFile(archive_path, 'r') as rf:
                    image_names = sorted(
                        [n for n in rf.namelist() if is_image_file(n)],
                        key=natural_sort_key
                    )
                    if image_names:
                        data = rf.read(image_names[0])
                        mime_type, _ = mimetypes.guess_type(image_names[0])
                        if not mime_type:
                            mime_type = 'image/jpeg'
                        self.send_response(200)
                        self.send_header('Content-Type', mime_type)
                        self.send_header('Content-Length', len(data))
                        self.send_header('Cache-Control', 'public, max-age=3600')
                        self.end_headers()
                        self.wfile.write(data)
                        return
        except Exception:
            pass
        self.send_error(404, "Cover not found")

    def serve_json(self, data):
        content = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(content))
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(content)

    def serve_image(self, relative_path):
        if not self.manga_root:
            self.send_error(404, "No manga loaded")
            return

        relative_path = urllib.parse.unquote(relative_path)
        file_path = Path(self.manga_root) / relative_path

        if not file_path.is_file():
            self.send_error(404, f"Image not found: {relative_path}")
            return

        # 安全检查
        try:
            file_path.resolve().relative_to(Path(self.manga_root).resolve())
        except ValueError:
            self.send_error(403, "Access denied")
            return

        self._serve_file(file_path)

    def _serve_file(self, file_path):
        """通用文件服务"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'

        file_size = file_path.stat().st_size
        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', file_size)
        self.send_header('Cache-Control', 'public, max-age=86400')
        self.end_headers()

        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def serve_static(self, filename):
        file_path = Path(self.static_dir) / filename
        if not file_path.is_file():
            self.send_error(404)
            return

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'text/html'

        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', f'{mime_type}; charset=utf-8')
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)


def main():
    parser = argparse.ArgumentParser(description='Mac 本地漫画阅读器')
    parser.add_argument('manga_path', nargs='?', default=None,
                        help='漫画文件夹路径或压缩包路径（可选）')
    parser.add_argument('--port', type=int, default=8899, help='端口号 (默认 8899)')
    parser.add_argument('--no-open', action='store_true', help='不自动打开浏览器')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    MangaHandler.static_dir = script_dir

    if args.manga_path:
        manga_path = os.path.expanduser(args.manga_path)
        manga_path = os.path.abspath(manga_path)

        is_file = os.path.isfile(manga_path)
        is_dir = os.path.isdir(manga_path)

        if not is_file and not is_dir:
            print(f"❌ 错误：路径不存在: {manga_path}")
            sys.exit(1)

        if is_file and Path(manga_path).suffix.lower() not in ARCHIVE_EXTENSIONS:
            print(f"❌ 错误：不支持的文件格式: {Path(manga_path).suffix}")
            sys.exit(1)

        print(f"📂 扫描: {manga_path}")
        manga_data = scan_manga_folder(manga_path)

        if "error" in manga_data:
            print(f"❌ {manga_data['error']}")
            sys.exit(1)

        MangaHandler.manga_root = manga_data['root_path']
        MangaHandler.manga_data = manga_data
        MangaHandler.original_path = manga_data.get('original_path', manga_path)

        # 写入历史记录
        history_path = manga_data.get('original_path', manga_path)
        add_to_history(history_path, manga_data['manga_name'])

        print(f"📖 漫画: {manga_data['manga_name']}")
        print(f"📚 共 {manga_data['chapter_count']} 个章节")
        for ch in manga_data['chapters']:
            name = ch['name']
            count = ch['image_count']
            print(f"   ├─ {name} ({count} 页)")
    else:
        print("📚 无参数启动 — 请在浏览器中选择漫画文件夹或压缩包")
        MangaHandler.manga_data = None

    # 启动服务
    server = HTTPServer(('127.0.0.1', args.port), MangaHandler)
    url = f"http://127.0.0.1:{args.port}"
    print(f"\n🚀 阅读器已启动: {url}")
    print(f"   支持格式: 文件夹、ZIP、CBZ、RAR、CBR、EPUB（图片型）")
    print(f"   按 Ctrl+C 停止\n")

    if not args.no_open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 已停止")
        server.server_close()


if __name__ == '__main__':
    main()
