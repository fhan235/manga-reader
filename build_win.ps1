# 漫画阅读器 - Windows 打包脚本
# 用法（在 manga-reader 目录下）:
#   powershell -ExecutionPolicy Bypass -File .\build_win.ps1            # 目录版
#   powershell -ExecutionPolicy Bypass -File .\build_win.ps1 -OneFile   # 单文件 exe
param(
    [switch]$OneFile,
    [switch]$Console,
    [switch]$SkipDeps
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not $SkipDeps) {
    Write-Host '== 安装依赖 ==' -ForegroundColor Cyan
    python -m pip install --upgrade pywebview pyinstaller rarfile pillow
}

if (-not (Test-Path .\img.ico)) {
    Write-Host '== 生成 img.ico ==' -ForegroundColor Cyan
    python -c "from PIL import Image; Image.open('img.png').save('img.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
}

$env:MR_ONEFILE = if ($OneFile) { '1' } else { '0' }
$env:MR_CONSOLE = if ($Console) { '1' } else { '0' }
$env:PYTHONIOENCODING = 'utf-8'

Write-Host '== PyInstaller 打包 ==' -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean build.spec

$exe = if ($OneFile) { '.\dist\MangaReader.exe' } else { '.\dist\MangaReader\MangaReader.exe' }
if (Test-Path $exe) {
    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
    Write-Host "== 完成: $exe ($size MB) ==" -ForegroundColor Green
} else {
    Write-Host '== 打包失败: 未找到 exe ==' -ForegroundColor Red
    exit 1
}
