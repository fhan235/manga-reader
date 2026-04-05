# 📚 漫画阅读器 (Manga Reader)

一款专为 macOS 打造的本地漫画阅读器，无需联网，双击即可启动，支持多种阅读模式，畅快阅读本地漫画。

![macOS](https://img.shields.io/badge/platform-macOS-lightgrey?logo=apple)
![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ 功能特性

### 🎯 核心功能
- **本地漫画阅读** — 直接打开本地漫画文件夹，支持多章节自动识别
- **原生文件夹选择** — 调用 macOS 原生文件夹选择对话框，体验自然
- **路径直达** — 支持直接输入漫画路径快速打开
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
├── app.py              # macOS App 入口（pywebview 窗口）
├── server.py           # HTTP 后端服务（漫画扫描、图片服务、历史记录）
├── index.html          # 前端单页面（HTML + CSS + JavaScript 一体）
├── build.spec          # PyInstaller 打包配置
├── make_dmg.sh         # DMG 磁盘映像制作脚本
├── icon.png            # 应用图标（PNG 源文件）
├── icon.icns           # 应用图标（macOS .icns 格式）
└── test-manga/         # 测试用漫画数据
    ├── 第01话-开始/
    ├── 第02话-觉醒/
    └── 第03话-战斗/
```

---

## 🛠️ 技术架构

```
┌─────────────────────────────────────────────────┐
│                macOS App (pywebview)             │
│        原生 Cocoa 窗口，内嵌 WebKit 渲染          │
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
- **桌面壳**：[pywebview](https://pywebview.flowrl.com/) 提供原生 macOS Cocoa 窗口，内嵌 WebKit 引擎渲染前端页面
- **打包**：PyInstaller 打包为独立 `.app`，可分发 DMG 安装包

---

## 🚀 快速开始

### 前置要求

- macOS 10.15 (Catalina) 或更高版本
- Python 3.8+
- pip

### 安装依赖

```bash
# 仅命令行/浏览器模式（零额外依赖，使用 Python 标准库）
# 无需安装任何包

# 如需 macOS 原生窗口模式
pip install pywebview
```

### 运行方式

#### 方式一：命令行 + 浏览器（无需额外依赖）

```bash
# 无参启动，在浏览器中选择文件夹
python3 server.py

# 直接指定漫画文件夹路径
python3 server.py /path/to/manga/folder

# 自定义端口
python3 server.py --port 9000

# 不自动打开浏览器
python3 server.py --no-open
```

启动后会自动在默认浏览器中打开 `http://127.0.0.1:8899`。

#### 方式二：原生 macOS 窗口（推荐）

```bash
# 需要先安装 pywebview
pip install pywebview

# 启动
python3 app.py
```

会弹出独立的 macOS 原生窗口，无需浏览器。

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

## 📦 打包为 macOS App

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
| `GET` | `/api/pick-folder` | 弹出 macOS 原生文件夹选择对话框 |
| `GET` | `/images/{path}` | 获取漫画图片 |
| `POST` | `/api/open` | 通过路径打开漫画，Body: `{"path": "/path/to/manga"}` |
| `POST` | `/api/remove-history` | 移除一条历史记录，Body: `{"path": "/path/to/manga"}` |

### 漫画数据结构示例

```json
{
  "manga_name": "电锯人",
  "root_path": "/Users/xxx/漫画/电锯人",
  "chapter_count": 3,
  "chapters": [
    {
      "name": "第01话-开始",
      "path": "第01话-开始",
      "image_count": 5,
      "images": ["001.jpg", "002.jpg", "003.jpg", "004.jpg", "005.jpg"]
    }
  ]
}
```

---

## 🗂️ 数据存储

| 数据 | 开发环境 | 打包后 App |
|------|----------|-----------|
| 历史记录 | 项目目录下 `.manga_history.json` | `~/Library/Application Support/MangaReader/.manga_history.json` |
| 阅读进度 | 浏览器 `localStorage` | WebKit `localStorage` |
| 双栏间距设置 | 浏览器 `localStorage` | WebKit `localStorage` |

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
| pywebview | 原生 macOS 窗口 | 仅 App 模式需要 |
| pyobjc | macOS 原生桥接 | pywebview 自动安装 |
| PyInstaller | 打包为 .app | 仅打包时需要 |

### 修改前端

前端为纯粹的单文件 `index.html`，直接修改即可，无需任何构建工具。修改后刷新浏览器（命令行模式）或重启应用（App 模式）即可生效。

---

## 📝 常见问题

### Q: 打开文件夹后看不到图片？
确保漫画文件夹中包含支持格式的图片文件（jpg/png/webp 等），且图片直接位于文件夹或其子文件夹中。

### Q: macOS 提示"无法打开，因为无法验证开发者"？
打包的 App 未经过签名，需要在系统偏好设置 → 安全性与隐私中允许打开，或右键选择"打开"。

### Q: 如何切换阅读模式？
点击工具栏右侧的下拉菜单选择模式，或按快捷键 `M` 循环切换。

### Q: 双栏模式下如何调整页面间距？
切换到双栏模式后，工具栏会显示"左右"和"上下"间距控制按钮，点击 +/- 调整，设置会自动保存。

### Q: 历史记录存在哪里？
- 开发模式：项目根目录 `.manga_history.json`
- 打包 App：`~/Library/Application Support/MangaReader/.manga_history.json`

---

## 📄 License

MIT License
