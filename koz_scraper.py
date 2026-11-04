#!/usr/bin/env python3
"""
方案D - koz.moe 漫画爬取测试脚本

功能:
  1. 抓取首页漫画列表（封面、标题、评分、作者、链接）  ✅ 无需登录
  2. 抓取漫画详情页（卷列表、大小、页数等）            ✅ 无需登录
  3. 按分类/排序浏览漫画列表                          🔒 需要登录
  4. 搜索漫画                                       🔒 需要登录
  5. 下载 EPUB/MOBI/ZIP 文件                        🔒 需要登录 + VIP

用法:
  python3 koz_scraper.py list                        # 抓取首页漫画列表（无需登录）
  python3 koz_scraper.py list --page 2               # 第2页（需登录）
  python3 koz_scraper.py list --category 愛情         # 按分类筛选（需登录）
  python3 koz_scraper.py search 进击的巨人             # 搜索漫画（需登录）
  python3 koz_scraper.py detail 10281                 # 查看漫画详情（无需登录）
  python3 koz_scraper.py download <URL>               # 下载文件
  python3 koz_scraper.py login                        # 登录账号
  python3 koz_scraper.py interactive                  # 交互模式

网站结构:
  - 首页:     https://koz.moe/             (不需登录，约20部推荐漫画)
  - 列表页:   https://koz.moe/l/.../{page}.htm  (需要登录)
  - 详情页:   https://koz.moe/c/{id}.htm    (不需登录)
  - 卷数据:   https://koz.moe/book_data.php?h=... (不需登录，通过详情页的隐藏URL获取)
  - 搜索:     https://koz.moe/list.php?s=... (需要登录)
  - 下载:     /dl/{bookid}/{volid}/...       (需要登录+VIP)

依赖:
  pip3 install requests beautifulsoup4 lxml
"""

import os
import sys
import re
import json
import time
import argparse
import urllib.parse
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("❌ 缺少依赖，请先安装：")
    print("   pip3 install requests beautifulsoup4 lxml")
    sys.exit(1)


# ==================== 配置 ====================

BASE_URL = "https://koz.moe"
DEFAULT_DOWNLOAD_DIR = os.path.expanduser("~/Downloads/koz-manga")

# 请求头，模拟浏览器
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}

# 请求间隔（秒），避免被封
REQUEST_DELAY = 1.0

# 会话（自动管理 cookies）
session = requests.Session()
session.headers.update(HEADERS)


# ==================== 工具函数 ====================

def delay():
    """礼貌性延迟，避免过于频繁请求"""
    time.sleep(REQUEST_DELAY)


def fetch_page(url):
    """获取页面内容，返回 BeautifulSoup 对象"""
    print(f"  🌐 请求: {url}")
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return BeautifulSoup(resp.text, "lxml")
    except requests.RequestException as e:
        print(f"  ❌ 请求失败: {e}")
        return None


def safe_filename(name):
    """生成安全的文件名"""
    # 替换非法字符
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    # 去首尾空格和点
    name = name.strip(' .')
    return name or "unnamed"


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 ** 3):.1f} GB"


# ==================== 登录（可选） ====================

def login(email, password):
    """
    登录 koz.moe 账号（部分功能需要登录）
    登录后 session 会自动保存 cookies
    """
    print(f"🔑 正在登录 {email}...")
    login_url = f"{BASE_URL}/login.php"

    # 先获取登录页，拿到可能的 CSRF token
    soup = fetch_page(login_url)
    if not soup:
        print("❌ 无法访问登录页")
        return False

    # 查找表单中的隐藏字段
    form = soup.find("form")
    payload = {}
    if form:
        for inp in form.find_all("input", {"type": "hidden"}):
            name = inp.get("name")
            value = inp.get("value", "")
            if name:
                payload[name] = value

    # 填写登录信息
    payload.update({
        "email": email,
        "password": password,
        "remember": "1",
    })

    try:
        resp = session.post(login_url, data=payload, timeout=15, allow_redirects=True)
        # 判断是否登录成功（通常成功后会跳转到首页）
        if "login.php" not in resp.url and resp.status_code == 200:
            print("✅ 登录成功！")
            return True
        else:
            print("❌ 登录失败，请检查邮箱和密码")
            return False
    except requests.RequestException as e:
        print(f"❌ 登录请求失败: {e}")
        return False


def save_cookies(path=None):
    """保存 cookies 到文件，下次可免登录"""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), ".koz_cookies.json")
    cookies = session.cookies.get_dict()
    with open(path, "w") as f:
        json.dump(cookies, f)
    print(f"  💾 Cookies 已保存到 {path}")


def load_cookies(path=None):
    """从文件加载 cookies"""
    if path is None:
        path = os.path.join(os.path.dirname(__file__), ".koz_cookies.json")
    if not os.path.exists(path):
        return False
    try:
        with open(path) as f:
            cookies = json.load(f)
        session.cookies.update(cookies)
        print(f"  🍪 已从 {path} 加载 Cookies")
        return True
    except Exception:
        return False


# ==================== 核心功能 ====================

def parse_disp_divinfo_calls(html_text):
    """
    从页面 HTML 中提取 disp_divinfo() JS 函数调用，解析漫画数据。

    koz.moe 的漫画列表是通过 JS 动态渲染的，每个漫画项对应一个 disp_divinfo() 调用:
      disp_divinfo( div_id, book_url, cover_url, border_color,
                    tag_jp, tag_en, tag_end, tag_brk,
                    score, name, author, word_status, word_update )
    """
    # 匹配 disp_divinfo 调用，提取所有参数
    pattern = re.compile(
        r'disp_divinfo\(\s*'
        r'"div_info_"\+"(\d+)"\s*,\s*'       # div_id (数字)
        r'"([^"]*)"\s*,\s*'                   # book_url
        r'"([^"]*)"\s*,\s*'                   # cover_url
        r'"([^"]*)"\s*,\s*'                   # border_color
        r'"([^"]*)"\s*,\s*'                   # tag_jp (日語标签 display)
        r'"([^"]*)"\s*,\s*'                   # tag_en (英文标签 display)
        r'"([^"]*)"\s*,\s*'                   # tag_end (完结标签 display)
        r'"([^"]*)"\s*,\s*'                   # tag_brk (中断标签 display)
        r'"([^"]*)"\s*,\s*'                   # score
        r'"([^"]*)"\s*,\s*'                   # name
        r'"([^"]*)"\s*,\s*'                   # author
        r'"([^"]*)"\s*,\s*'                   # word_status
        r'"([^"]*)"\s*\)',                     # word_update
        re.DOTALL
    )

    results = []
    for m in pattern.finditer(html_text):
        idx = int(m.group(1))
        book_url = m.group(2)
        cover_url = m.group(3)
        border_color = m.group(4)
        tag_jp = m.group(5)     # "none" = 隐藏, "" = 显示
        tag_en = m.group(6)
        tag_end = m.group(7)
        tag_brk = m.group(8)
        score = m.group(9)
        name = m.group(10)
        author = m.group(11)
        word_status = m.group(12)
        word_update = m.group(13)

        # 构建标签
        tags = []
        if tag_jp != "none":
            tags.append("日語")
        if tag_en != "none":
            tags.append("英文")
        if tag_end != "none":
            tags.append("完結")
        if tag_brk != "none":
            tags.append("中斷")

        # 从 URL 提取漫画 ID
        id_match = re.search(r"/c/(\w+)\.htm", book_url)
        manga_id = id_match.group(1) if id_match else ""

        results.append({
            "index": idx,
            "id": manga_id,
            "title": name,
            "author": author,
            "score": score,
            "url": book_url,
            "cover": cover_url,
            "tags": tags,
            "status": word_status,
            "update": word_update,
        })

    # 按 index 排序
    results.sort(key=lambda x: x["index"])
    return results


def parse_pagination(html_text):
    """
    从 disp_divpage() 调用中解析分页信息。

    disp_divpage( id, ..., width,
                  prev_disabled, next_disabled, ...,
                  page1, page2, page3, page4, page5,
                  url1, url2, ..., url5, prev_url, next_url, ... )
    """
    # 简化：从页面中提取所有分页链接
    page_urls = re.findall(r'https://koz\.moe/l/[^"]+/(\d+)\.htm', html_text)
    pages = [int(p) for p in page_urls if p.isdigit()]
    max_page = max(pages) if pages else 1
    return max_page


def scrape_manga_list(category="all", region="all", lang="all",
                      sort="sortpoint", page=1, status="all"):
    """
    抓取漫画列表页

    参数:
      category: 分类，如 愛情/熱血/冒險/科幻/all
      region:   地区，如 日本/歐美/港臺/大陸/韓國/all
      lang:     语言，如 中文/繁体/简体/日語/英文/all
      sort:     排序方式，如 sortpoint(评分)/hot(热度)/update(最近更新)/new(最近收录)
      page:     页码
      status:   连载状态，如 完結/連載/all

    返回: [{ title, url, cover, score, author, tags, id }, ...]
    """
    # 构造筛选 URL
    # URL 格式: /l/{category},{region},{status},{sort},{lang},all,BL,0,0/{page}.htm
    filter_parts = [
        f"CAT*{category}" if category != "all" else "all",
        region,
        status,
        sort,
        lang,
        "all",   # 其他筛选
        "BL",    # 固定参数
        "0",
        "0",
    ]
    filter_str = ",".join(filter_parts)
    url = f"{BASE_URL}/l/{filter_str}/{page}.htm"

    print(f"\n📚 正在抓取漫画列表 (第{page}页)...")

    try:
        resp = session.get(url, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except requests.RequestException as e:
        print(f"  ❌ 请求失败: {e}")
        return []

    # 检查是否被重定向到登录页
    if "login.php" in resp.url:
        print("  ⚠️  列表页需要登录，尝试从首页获取数据...")
        try:
            resp = session.get(BASE_URL, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            html = resp.text
        except requests.RequestException as e:
            print(f"  ❌ 请求首页也失败: {e}")
            return []

    # 从 JS disp_divinfo() 调用中提取漫画数据
    results = parse_disp_divinfo_calls(html)

    # 获取分页信息
    total_pages = parse_pagination(html)

    print(f"  ✅ 本页找到 {len(results)} 部漫画 (共约 {total_pages} 页)")
    return results


def scrape_manga_detail(manga_id):
    """
    抓取漫画详情页

    参数:
      manga_id: 漫画 ID（数字或十六进制字符串），如 10281 或 66c2bc

    返回: {
      title, author, status, score, voters,
      categories, region, language,
      volumes: [{ vol_id, group, number, name, pages, size_zip, size_mobi, size_epub, date }],
      cover, book_data_url, download_url_prefix
    }
    """
    url = f"{BASE_URL}/c/{manga_id}.htm"
    print(f"\n📖 正在抓取漫画详情: {manga_id}...")

    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except requests.RequestException as e:
        print(f"  ❌ 请求失败: {e}")
        return None

    # 检查是否被重定向到登录页
    if "login.php" in resp.url:
        print("  ⚠️  详情页需要登录")
        return None

    detail = {
        "id": manga_id,
        "url": url,
        "title": "",
        "author": "",
        "status": "",
        "score": "",
        "voters": "",
        "categories": [],
        "region": "",
        "cover": "",
        "volumes": [],
        "download_url_prefix": "",
    }

    # 从 JS 变量提取基础信息
    bookid_m = re.search(r'var\s+bookid\s*=\s*"(\w+)"', html)
    if bookid_m:
        detail["id"] = bookid_m.group(1)

    status_m = re.search(r'var\s+bookstatus\s*=\s*"([^"]*)"', html)
    if status_m:
        detail["status"] = status_m.group(1)

    # 下载 URL 前缀: /dl/{bookid}/
    dl_prefix_m = re.search(r'var\s+str_down_url_prefix\s*=\s*"([^"]*)"', html)
    if dl_prefix_m:
        detail["download_url_prefix"] = dl_prefix_m.group(1)

    # 从 HTML 中提取标题、作者等
    soup = BeautifulSoup(html, "lxml")

    # 标题
    title_el = soup.find("h1") or soup.find("title")
    if title_el:
        title_text = title_el.get_text(strip=True)
        # 清理 title 标签中的多余信息
        title_text = title_text.split(":")[0].split(" [")[0].strip()
        detail["title"] = title_text

    # 封面
    cover_img = soup.find("img", src=re.compile(r"kmimg|cover"))
    if cover_img:
        detail["cover"] = cover_img.get("src", "")

    # 评分
    score_match = re.search(r'(\d+\.\d)\s*</b>', html)
    if score_match:
        detail["score"] = score_match.group(1)

    # 作者 - 从页面文本或 meta 信息中提取
    text = soup.get_text()
    author_match = re.search(r"(?:作者|artist|author)[：:\s]*([^\n\r]+)", text, re.IGNORECASE)
    if author_match:
        detail["author"] = author_match.group(1).strip()

    # 分类标签
    tag_links = soup.find_all("a", href=re.compile(r"/l/CAT\*"))
    for tl in tag_links:
        tag = tl.get_text(strip=True)
        if tag and tag not in detail["categories"]:
            detail["categories"].append(tag)

    # 提取 book_data.php URL 来获取卷数据
    book_data_match = re.search(r'/book_data\.php\?h=([^"\'\ ]+)', html)
    if book_data_match:
        book_data_url = f"{BASE_URL}{book_data_match.group(0)}"
        detail["book_data_url"] = book_data_url

        # 请求卷数据
        print(f"  📦 正在获取卷数据...")
        delay()
        try:
            resp2 = session.get(book_data_url, timeout=15)
            resp2.encoding = "utf-8"
            vol_html = resp2.text

            # 解析 postMessage 中的 volinfo
            # 格式: volinfo=卷ID,flag1,flag2,分组名,卷号,卷名,页数,总页数,?,zip大小MB,mobi大小MB,epub大小MB,,,日期信息...
            vol_pattern = re.compile(
                r'volinfo=(\d+),(\d+),(\d+),([^,]*),(\d+),([^,]*),(\d+),(\d+),'
                r'([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^"]*)"'
            )

            for vm in vol_pattern.finditer(vol_html):
                vol_id = vm.group(1)
                group_name = vm.group(4)
                vol_number = vm.group(5)
                vol_name = vm.group(6)
                pages = vm.group(7)
                total_pages = vm.group(8)
                size_zip = vm.group(10)
                size_mobi = vm.group(11)
                size_epub = vm.group(12)
                date_info = vm.group(15)

                # 提取日期（格式如 "2025-06-27 960x1280"）
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_info or "")
                date_str = date_match.group(1) if date_match else ""

                detail["volumes"].append({
                    "vol_id": vol_id,
                    "group": group_name,
                    "number": int(vol_number),
                    "name": vol_name,
                    "pages": int(pages),
                    "total_pages": int(total_pages),
                    "size_zip": f"{size_zip} MB" if size_zip and float(size_zip) > 0 else "-",
                    "size_mobi": f"{size_mobi} MB" if size_mobi and float(size_mobi) > 0 else "-",
                    "size_epub": f"{size_epub} MB" if size_epub and float(size_epub) > 0 else "-",
                    "date": date_str,
                })

        except Exception as e:
            print(f"  ⚠️  获取卷数据失败: {e}")

    print(f"  ✅ 标题: {detail['title']}")
    print(f"  ✅ 作者: {detail['author']}")
    print(f"  ✅ 评分: {detail['score']}")
    print(f"  ✅ 状态: {detail['status']}")
    print(f"  ✅ 找到 {len(detail['volumes'])} 个卷")

    return detail


def search_manga(keyword):
    """
    搜索漫画

    参数:
      keyword: 搜索关键词

    返回: 与 scrape_manga_list 相同格式的列表
    """
    print(f"\n🔍 搜索: {keyword}")

    # koz.moe 搜索接口: list.php?s=关键词
    url = f"{BASE_URL}/list.php?s={urllib.parse.quote(keyword)}"

    try:
        resp = session.get(url, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
    except requests.RequestException as e:
        print(f"  ❌ 请求失败: {e}")
        return []

    # 检查是否被重定向到登录页
    if "login.php" in resp.url:
        print("  ⚠️  搜索需要登录，请先使用 login 命令")
        return []

    # 搜索结果也使用 disp_divinfo 渲染
    results = parse_disp_divinfo_calls(html)

    if results:
        print(f"  ✅ 搜索到 {len(results)} 个结果")
    else:
        # 备选：从页面链接中提取
        links = re.findall(r'<a[^>]+href="([^"]*?/c/(\w+)\.htm)"[^>]*>', html)
        seen = set()
        for full_url, mid in links:
            if mid in seen or mid == "10001":
                continue
            seen.add(mid)
            results.append({
                "id": mid,
                "title": mid,
                "url": full_url if full_url.startswith("http") else BASE_URL + full_url,
                "author": "",
                "score": "",
                "cover": "",
                "tags": [],
            })

        if results:
            print(f"  ✅ 搜索到 {len(results)} 个结果 (简略)")
        else:
            print("  ⚠️  未找到搜索结果")

    return results


def download_file(url, save_dir=None, filename=None):
    """
    下载文件

    参数:
      url:      文件 URL
      save_dir: 保存目录（默认 ~/Downloads/koz-manga）
      filename: 文件名（默认从 URL 或 headers 提取）

    返回: 保存路径 或 None
    """
    if save_dir is None:
        save_dir = DEFAULT_DOWNLOAD_DIR
    os.makedirs(save_dir, exist_ok=True)

    print(f"\n📥 下载: {url}")

    try:
        resp = session.get(url, stream=True, timeout=30)
        resp.raise_for_status()

        # 确定文件名
        if not filename:
            # 尝试从 Content-Disposition 获取
            cd = resp.headers.get("Content-Disposition", "")
            fname_match = re.search(r'filename[*]?=["\']?(?:UTF-8\'\')?([^"\';\n]+)', cd)
            if fname_match:
                filename = urllib.parse.unquote(fname_match.group(1))
            else:
                filename = os.path.basename(urllib.parse.urlparse(url).path)

        filename = safe_filename(filename)
        save_path = os.path.join(save_dir, filename)

        # 避免覆盖
        if os.path.exists(save_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join(save_dir, f"{base}_{counter}{ext}")
                counter += 1

        # 写入文件
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded / total * 100
                        print(f"\r  ⏳ 下载中... {format_size(downloaded)}/{format_size(total)} ({pct:.1f}%)", end="")
                    else:
                        print(f"\r  ⏳ 下载中... {format_size(downloaded)}", end="")

        print(f"\n  ✅ 已保存: {save_path} ({format_size(os.path.getsize(save_path))})")
        return save_path

    except requests.RequestException as e:
        print(f"\n  ❌ 下载失败: {e}")
        return None


# ==================== 命令行界面 ====================

def print_manga_list(mangas):
    """格式化打印漫画列表"""
    if not mangas:
        print("  (无结果)")
        return

    print()
    print(f"  {'#':<4} {'评分':<6} {'标题':<30} {'作者':<20} {'标签':<14} {'ID'}")
    print(f"  {'─'*4} {'─'*6} {'─'*30} {'─'*20} {'─'*14} {'─'*10}")

    for i, m in enumerate(mangas, 1):
        score = m.get("score", "-") or "-"
        title = m["title"][:28]
        author = (m.get("author") or "-")[:18]
        tags = ",".join(m.get("tags", []))[:12] or "-"
        manga_id = m.get("id", "")
        if not manga_id:
            id_match = re.search(r"/c/(\w+)\.htm", m.get("url", ""))
            manga_id = id_match.group(1) if id_match else ""
        print(f"  {i:<4} {score:<6} {title:<30} {author:<20} {tags:<14} {manga_id}")

    print(f"\n  共 {len(mangas)} 部漫画")


def print_manga_detail(detail):
    """格式化打印漫画详情"""
    if not detail:
        print("  (无法获取详情)")
        return

    print()
    print(f"  ╔══════════════════════════════════════════╗")
    print(f"  ║ 📖 {detail['title']:<38} ║")
    print(f"  ╚══════════════════════════════════════════╝")
    print(f"  作者:  {detail.get('author', '-')}")
    print(f"  评分:  {detail.get('score', '-')}")
    print(f"  状态:  {detail.get('status', '-')}")
    print(f"  分类:  {', '.join(detail.get('categories', [])) or '-'}")
    print(f"  链接:  {detail.get('url', '-')}")

    volumes = detail.get("volumes", [])
    if volumes:
        print(f"\n  📦 卷列表 ({len(volumes)} 卷):")
        print(f"  {'#':<5} {'卷名':<20} {'页数':<6} {'ZIP':<10} {'EPUB':<10} {'MOBI':<10} {'日期'}")
        print(f"  {'─'*5} {'─'*20} {'─'*6} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")

        # 按分组显示
        current_group = ""
        for vol in volumes:
            if vol["group"] != current_group:
                current_group = vol["group"]
                print(f"\n  ── {current_group} ──")

            print(f"  {vol['number']:<5} {vol['name']:<20} {vol['pages']:<6} "
                  f"{vol['size_zip']:<10} {vol['size_epub']:<10} {vol['size_mobi']:<10} "
                  f"{vol.get('date', '')}")

        # 统计
        total_pages = sum(v['pages'] for v in volumes)
        print(f"\n  📊 共 {len(volumes)} 卷, {total_pages} 页")
    else:
        print(f"\n  ⚠️  未获取到卷数据（可能需要登录）")

    print()


def interactive_mode():
    """交互模式"""
    print("""
╔══════════════════════════════════════════════╗
║   🌐 koz.moe 漫画爬取工具 (方案D测试版)      ║
║                                              ║
║   命令:                                      ║
║     list [页码]     - 浏览漫画列表             ║
║     search <关键词> - 搜索漫画                 ║
║     detail <ID>    - 查看漫画详情              ║
║     download <URL> - 下载文件                  ║
║     login          - 登录账号                  ║
║     quit           - 退出                     ║
╚══════════════════════════════════════════════╝
    """)

    while True:
        try:
            cmd = input("koz> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 再见！")
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if action in ("quit", "exit", "q"):
            print("👋 再见！")
            break

        elif action == "list":
            page = int(arg) if arg.isdigit() else 1
            mangas = scrape_manga_list(page=page)
            print_manga_list(mangas)

        elif action == "search":
            if not arg:
                print("  ⚠️  用法: search <关键词>")
                continue
            results = search_manga(arg)
            print_manga_list(results)

        elif action == "detail":
            if not arg:
                print("  ⚠️  用法: detail <漫画ID>")
                continue
            detail = scrape_manga_detail(arg)
            print_manga_detail(detail)

        elif action == "download":
            if not arg:
                print("  ⚠️  用法: download <URL>")
                continue
            download_file(arg)

        elif action == "login":
            email = input("  邮箱: ").strip()
            import getpass
            password = getpass.getpass("  密码: ")
            if login(email, password):
                save_cookies()

        else:
            print(f"  ⚠️  未知命令: {action}")
            print("  输入 list/search/detail/download/login/quit")


# ==================== 主入口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="koz.moe 漫画爬取测试工具 (方案D)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s list                       # 浏览首页漫画列表
  %(prog)s list --page 2              # 第2页
  %(prog)s list --category 愛情       # 按分类
  %(prog)s list --sort hot            # 按热度排序
  %(prog)s search 进击的巨人           # 搜索
  %(prog)s detail 10281               # 查看详情
  %(prog)s download <URL>             # 下载文件
  %(prog)s interactive                # 交互模式
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list
    list_parser = subparsers.add_parser("list", help="浏览漫画列表")
    list_parser.add_argument("--page", "-p", type=int, default=1, help="页码")
    list_parser.add_argument("--category", "-c", default="all", help="分类")
    list_parser.add_argument("--region", "-r", default="all", help="地区")
    list_parser.add_argument("--lang", "-l", default="all", help="语言")
    list_parser.add_argument("--sort", "-s", default="sortpoint",
                             choices=["sortpoint", "hot", "update", "new", "random"],
                             help="排序方式")
    list_parser.add_argument("--status", default="all", help="连载状态")

    # search
    search_parser = subparsers.add_parser("search", help="搜索漫画")
    search_parser.add_argument("keyword", help="搜索关键词")

    # detail
    detail_parser = subparsers.add_parser("detail", help="查看漫画详情")
    detail_parser.add_argument("manga_id", help="漫画ID")

    # download
    dl_parser = subparsers.add_parser("download", help="下载文件")
    dl_parser.add_argument("url", help="下载URL")
    dl_parser.add_argument("--output", "-o", help="保存目录")
    dl_parser.add_argument("--filename", "-f", help="文件名")

    # interactive
    subparsers.add_parser("interactive", help="交互模式")

    # login
    login_parser = subparsers.add_parser("login", help="登录账号")
    login_parser.add_argument("--email", "-e", help="邮箱")
    login_parser.add_argument("--password", "-P", help="密码（建议交互输入）")

    args = parser.parse_args()

    # 尝试加载已保存的 cookies
    load_cookies()

    if args.command == "list":
        mangas = scrape_manga_list(
            category=args.category,
            region=args.region,
            lang=args.lang,
            sort=args.sort,
            page=args.page,
            status=args.status,
        )
        print_manga_list(mangas)

    elif args.command == "search":
        results = search_manga(args.keyword)
        print_manga_list(results)

    elif args.command == "detail":
        detail = scrape_manga_detail(args.manga_id)
        print_manga_detail(detail)

    elif args.command == "download":
        download_file(args.url, save_dir=args.output, filename=args.filename)

    elif args.command == "interactive":
        interactive_mode()

    elif args.command == "login":
        email = args.email or input("邮箱: ").strip()
        if args.password:
            password = args.password
        else:
            import getpass
            password = getpass.getpass("密码: ")
        if login(email, password):
            save_cookies()

    else:
        # 无命令时进入交互模式
        interactive_mode()


if __name__ == "__main__":
    main()
