# 📚 漫画阅读器 (Manga Reader)

一款本地漫画阅读器，无需联网，双击即可启动，支持多种阅读模式，畅快阅读本地漫画。
**macOS / Windows / Linux 三端通用**（同一套代码，按平台自动切换窗口后端与原生对话框）。

![platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ 功能特性

### 🎯 核心功能
- **本地漫画阅读** — 直接打开本地漫画文件夹，支持多章节自动识别
- **原生文件夹选择** — macOS 走 osascript，Windows / Linux 走 tkinter 原生对话框
- **路径直达** — 支持直接输入漫画路径快速打开（Windows 盘符路径同样可用）
- **历史记录** — 自动记录最近打开的漫画（最多 20 条），一键重新打开
- **阅读进度记忆** — 自动保存上次阅读到的章节位置，下次打开自动恢复

### 📖 四种阅读模式
| 模式 | 说明 | 适用场景 |
|------|------|----------|
| 📖 **条漫模式** | 所有图片纵向排列，连续滚动阅读 | 条漫、webtoon |
| 📄 **单页模式** | 一次显示一张图片，点击/键盘翻页 | 传统日漫单页 |
| ↔ **适宽模式** | 图片自适应宽度，纵向滚动 | 宽幅漫画 |
| ▥ **双栏模式** | 两页并排显示，支持间距调节 | 传统日漫跨页 |

### 🎨 界面特性
- **暗色主题** — 精心设计的深色配色方案，护眼舒适
- **侧边栏章节导航** — 带搜索、序号、页数显示的章节列表
- **阅读进度条** — 顶部实时显示当前阅读进度
- **回到顶部按钮** — 滚动超过一定距离后自动显示
- **全屏支持** — 沉浸式阅读体验
- **图片懒加载** — 仅加载视口附近的图片，流畅不卡顿
- **自然排序** — 章节按自然顺序排列（"第2话"排在"第10话"前面）
- **响应式布局** — 自适应不同窗口大小

### ⌨️ 快捷键
| 快捷键 | 功能 |
|--------|------|
| `←` | 上一章 / 上一页（单页模式） |
| `→` | 下一章 / 下一页（单页模式） |
| `↑` / `↓` | 上下滚动 |
| `Space` | 向下翻页滚动 |
| `S` | 切换侧边栏 |
| `T` | 回到顶部 |
| `F` | 切换全屏 |
| `M` | 循环切换阅读模式 |
| `O` | 打开文件夹 |

---

## 📂 项目结构

```
manga-reader/
├── app.py              # 桌面端入口（pywebview 窗口，三平台通用）
├── server.py           # HTTP 后端服务（漫画扫描、图片服务、历史记录）
├── index.html          # 前端单页面（HTML + CSS + JavaScript 一体）
├── build.spec          # PyInstaller 打包配置（按平台分支）
├── build_win.ps1       # Windows 打包脚本
├── make_dmg.sh         # macOS DMG 磁盘映像制作脚本
├── png2icns.sh         # PNG → .icns 图标转换
├── img.png             # 应用图标源文件
├── img.icns            # macOS 图标
├── img.ico             # Windows 图标
└── test-manga/         # 测试用漫画数据
    ├── 第01话-开始/
    ├── 第02话-觉醒/
    └── 第03话-战斗/
```

---

## 🛠️ 技术架构

```
┌─────────────────────────────────────────────────┐
│     桌面窗口 (pywebview: Cocoa / WebView2)        │
│   macOS 内嵌 WKWebView，Windows 内嵌 WebView2     │
├─────────────────────────────────────────────────┤
│          本地 HTTP 服务器 (Python)                │
│    ┌──────────┬──────────┬──────────────┐       │
│    │  API路由  │ 图片服务  │  静态资源服务  │       │
│    └──────────┴──────────┴──────────────┘       │
├─────────────────────────────────────────────────┤
│          前端 (单文件 index.html)                 │
│    ┌──────────┬──────────┬──────────────┐       │
│    │  侧边栏   │  阅读区   │  工具栏      │       │
│    └──────────┴──────────┴──────────────┘       │
└─────────────────────────────────────────────────┘
```

- **前端**：纯原生 HTML/CSS/JavaScript，无任何框架依赖，单文件 `index.html` 包含全部 UI 逻辑
- **后端**：Python 标准库 `http.server`，零依赖 HTTP 服务器，负责漫画目录扫描、图片分发和历史记录管理
- **桌面壳**：[pywebview](https://pywebview.flowrl.com/) 提供原生窗口：macOS 用 Cocoa/WKWebView，Windows 用 EdgeChromium（WebView2），Linux 用 GTK/Qt
- **打包**：PyInstaller 打包为独立 `.app`（macOS）或 `.exe`（Windows，目录版 / 单文件版）

---

## 🚀 快速开始

### 前置要求

| 平台 | 要求 |
|------|------|
| macOS | 10.15 (Catalina) 或更高版本 |
| Windows | Windows 10 / 11（自带 WebView2 Runtime；Win10 旧版需装 [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/)） |
| Linux | 需 GTK（`python3-gi`）或 Qt（PyQt5/PySide6）之一 |
| 通用 | Python 3.8+、pip |

### 安装依赖

```bash
# 仅命令行/浏览器模式（零额外依赖，使用 Python 标准库）
# 无需安装任何包

# 如需原生窗口模式
pip install pywebview

# Windows 上打包/选文件夹还需要
pip install pyinstaller rarfile pillow
```

### 运行方式

#### 方式一：命令行 + 浏览器（无需额外依赖）

```bash
# macOS / Linux
python3 server.py /path/to/manga/folder

# Windows（注意路径里的反斜杠，用双引号包住）
python server.py "D:\漫画\火影忍者全彩版"

# 自定义端口 / 不自动打开浏览器
python server.py --port 9000 --no-open
```

启动后会自动在默认浏览器中打开 `http://127.0.0.1:8899`。

#### 方式二：原生窗口（推荐）

```bash
# macOS / Linux
python3 app.py

# Windows
python app.py
python app.py "D:\漫画\火影忍者全彩版"   # 启动即打开指定目录
```

会弹出独立窗口：macOS 用 Cocoa/WKWebView，Windows 用 EdgeChromium（WebView2）。

---

## 🪟 Windows 支持说明

代码里针对 Windows 做的适配：

| 位置 | 处理方式 |
|------|----------|
| 用户数据目录 | `%APPDATA%\MangaReader\`（历史 / 书架 / 进度），不再写进程序目录 |
| 文件夹 / 文件选择 | tkinter 原生对话框（跨线程安全，不依赖 pywebview 的 GUI 线程） |
| 下载 / 桌面目录 | `SHGetKnownFolderPath` 取 Known Folder，兼容中文系统的「下载」「桌面」 |
| 章节相对路径 | 统一转 POSIX 分隔符，避免 `\` 破坏前端 URL 与图片请求 |
| 图片请求 | `/images/...` 同时接受 `/` 与 `\`，并做穿越校验 |
| 控制台 | GBK 控制台 / `--windowed` 下 `sys.stdout=None` 均做了兜底 |
| 打包 | `build.spec` 按平台分支：Windows 出 `.exe`（可选单文件），macOS 出 `.app` |

### Windows 打包

```powershell
# 目录版（推荐，启动快）：dist\MangaReader\MangaReader.exe
powershell -ExecutionPolicy Bypass -File .\build_win.ps1

# 单文件版：dist\MangaReader.exe（约 40MB，首次启动稍慢）
powershell -ExecutionPolicy Bypass -File .\build_win.ps1 -OneFile

# 想看控制台日志排查问题
powershell -ExecutionPolicy Bypass -File .\build_win.ps1 -Console
```

也可以直接调 PyInstaller：

```powershell
pyinstaller --noconfirm --clean build.spec
```

> 打包产物里已包含 WebView2 加载器（`webview\lib`），但**目标机器仍需安装 WebView2 Runtime**（Win11 自带，Win10 1803+ 多数已随 Edge 安装）。

---

## 📁 漫画文件夹组织方式

阅读器支持两种目录结构：

### 多章节结构（推荐）

```
漫画名/
├── 第01话/
│   ├── 001.jpg
│   ├── 002.jpg
│   └── ...
├── 第02话/
│   ├── 001.jpg
│   └── ...
└── 第03话/
    └── ...
```

每个子文件夹被识别为一个章节，按自然排序排列。

### 单章节结构

```
漫画名/
├── 001.jpg
├── 002.jpg
├── 003.jpg
└── ...
```

根目录直接包含图片文件时，整个文件夹作为一个章节处理。

### 支持的图片格式

`.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` `.tiff` `.tif` `.avif`

---

## 📦 打包 macOS App（.app / DMG）

### 步骤一：安装打包依赖

```bash
pip install pyinstaller pywebview pyobjc-framework-Cocoa pyobjc-framework-WebKit
```

### 步骤二：使用 PyInstaller 打包

```bash
pyinstaller build.spec --distpath ./dist --workpath ./build --noconfirm
```

打包完成后会生成 `dist/漫画阅读器.app`。

### 步骤三：制作 DMG 安装包（可选）

```bash
bash make_dmg.sh
```

生成 `dist/漫画阅读器.dmg`，用户双击打开 DMG，将"漫画阅读器"拖入 Applications 即完成安装。

---

## 🔌 API 接口

后端服务提供以下 HTTP API，方便进行二次开发或调试：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/` | 前端页面 |
| `GET` | `/api/manga` | 获取当前加载的漫画数据 |
| `GET` | `/api/history` | 获取最近打开历史记录 |
| `GET` | `/api/library` | 获取书架列表 |
| `GET` | `/api/progress?name=漫画名` | 读取某部漫画的阅读进度 |
| `GET` | `/api/loading-status` | 扫描/解压进度轮询 |
| `GET` | `/api/pick-folder` | 弹出系统原生文件夹选择对话框 |
| `GET` | `/api/pick-file` | 弹出系统原生文件选择对话框（压缩包） |
| `GET` | `/images/{path}` | 获取漫画图片（`/` 与 `\` 均可） |
| `POST` | `/api/open` | 通过路径打开漫画，Body: `{"path": "D:\\漫画\\火影忍者"}` |
| `POST` | `/api/progress/save` | 保存进度，Body: `{"manga_name": "...", "chapter": 3, "page": 5}` |
| `POST` | `/api/remove-history` | 移除一条历史记录，Body: `{"path": "/path/to/manga"}` |

### 漫画数据结构示例

```json
{
  "manga_name": "火影忍者全彩版",
  "root_path": "C:\\原F盘分区\\漫画\\火影忍者全彩版",
  "chapter_count": 72,
  "chapters": [
    {
      "name": "1",
      "path": "1",
      "image_count": 97,
      "images": ["001.jpg", "002.jpg", "003.jpg"]
    }
  ]
}
```

---

## 🗂️ 数据存储

| 数据 | 开发环境（源码运行） | macOS App | Windows exe |
|------|----------------------|-----------|-------------|
| 历史记录 | 项目目录下 `.manga_history.json` | `~/Library/Application Support/MangaReader/` | `%APPDATA%\MangaReader\` |
| 书架 | 项目目录下 `.manga_library.json` | 同上 | 同上 |
| 阅读进度 | 项目目录下 `.manga_progress.json` | 同上 | 同上 |
| 阅读模式 / 双栏间距 | 浏览器 `localStorage` | WebView `localStorage` | WebView2 `localStorage` |

数据目录可用环境变量 `MANGA_READER_DATA_DIR` 覆盖（`app.py` 启动时会自动设置）。

---

## 🔒 安全特性

- **路径安全检查** — 图片请求通过 `Path.resolve().relative_to()` 进行路径穿越防护，阻止访问漫画目录之外的文件
- **仅本地监听** — HTTP 服务仅绑定 `127.0.0.1`，外部无法访问
- **动态端口** — App 模式自动选择可用端口，避免端口冲突

---

## 🤝 开发指南

### 本地开发

```bash
# 克隆项目
git clone <repo-url>
cd manga-reader

# 用测试数据运行
python3 server.py test-manga

# 或不带参数启动，在浏览器中手动选择
python3 server.py
```

### 项目依赖总结

| 依赖 | 用途 | 是否必须 |
|------|------|---------|
| Python 3.8+ | 运行环境 | ✅ |
| pywebview | 原生窗口（macOS Cocoa / Windows WebView2） | 仅窗口模式需要 |
| pyobjc | macOS 原生桥接 | pywebview 自动安装 |
| pythonnet | Windows 上 pywebview 的 .NET 桥接 | pywebview 自动安装 |
| tkinter | Windows / Linux 的原生选择对话框 | Python 标准库自带 |
| rarfile | 读取 RAR / CBR | 可选（需系统 unrar） |
| Pillow | 生成 `.ico` 图标、封面缩略图 | 打包时需要 |
| PyInstaller | 打包为 .app / .exe | 仅打包时需要 |

### 修改前端

前端为纯粹的单文件 `index.html`，直接修改即可，无需任何构建工具。修改后刷新浏览器（命令行模式）或重启应用（窗口模式）即可生效。

---

## 📝 常见问题

### Q: 打开文件夹后看不到图片？
确保漫画文件夹中包含支持格式的图片文件（jpg/png/webp 等），且图片直接位于文件夹或其子文件夹中。

### Q: macOS 提示"无法打开，因为无法验证开发者"？
打包的 App 未经过签名，需要在系统偏好设置 → 安全性与隐私中允许打开，或右键选择"打开"。

### Q: Windows 上双击 exe 没反应 / 白屏？
1. 确认已装 WebView2 Runtime（Win11 自带；Win10 到微软官网装 Evergreen Bootstrapper）；
2. 用 `build_win.ps1 -Console` 重新打包，命令行运行看报错；
3. 确认没被杀软拦截（PyInstaller 产物常见误报，加白名单即可）。

### Q: 如何切换阅读模式？
点击工具栏右侧的下拉菜单选择模式，或按快捷键 `M` 循环切换。

### Q: 双栏模式下如何调整页面间距？
切换到双栏模式后，工具栏会显示"左右"和"上下"间距控制按钮，点击 +/- 调整，设置会自动保存。

### Q: 历史记录存在哪里？
- 开发模式：项目根目录 `.manga_history.json`
- macOS App：`~/Library/Application Support/MangaReader/.manga_history.json`
- Windows exe：`%APPDATA%\MangaReader\.manga_history.json`

---

## 📄 License

MIT License
