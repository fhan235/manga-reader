# 漫画阅读器 - Windows 打包脚本
# 用法（在 manga-reader 目录下）:
#   powershell -ExecutionPolicy Bypass -File .\build_win.ps1              # 目录版（推荐）
#   powershell -ExecutionPolicy Bypass -File .\build_win.ps1 -OneFile     # 单文件 exe
#   powershell -ExecutionPolicy Bypass -File .\build_win.ps1 -Installer   # 额外用 Inno Setup 出安装包
#   powershell -ExecutionPolicy Bypass -File .\build_win.ps1 -Console     # 带控制台，便于排查
param(
    [switch]$OneFile,
    [switch]$Console,
    [switch]$Installer,
    [switch]$SkipDeps
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not $SkipDeps) {
    Write-Host '== 安装依赖 ==' -ForegroundColor Cyan
    python -m pip install --upgrade pip
    python -m pip install -r requirements-dev.txt
}

if (-not (Test-Path .\img.ico)) {
    Write-Host '== 生成 img.ico ==' -ForegroundColor Cyan
    python -c "from PIL import Image; Image.open('img.png').save('img.ico', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
}

$env:MR_ONEFILE = if ($OneFile) { '1' } else { '0' }
$env:MR_CONSOLE = if ($Console) { '1' } else { '0' }
$env:PYTHONIOENCODING = 'utf-8'
if (-not $env:APP_VERSION) { $env:APP_VERSION = '1.0.0' }
# Inno Setup 的 VersionInfoVersion 必须是纯数字四段版本号
if (-not $env:APP_VERSION_NUM) {
    $m = [regex]::Match($env:APP_VERSION, '^[0-9]+(\.[0-9]+){0,2}')
    $num = if ($m.Success) { $m.Value } else { '1.0.0' }
    $parts = $num.Split('.')
    while ($parts.Count -lt 3) { $parts += '0' }
    $env:APP_VERSION_NUM = ($parts -join '.') + '.0'
}

Write-Host "== PyInstaller 打包 (v$env:APP_VERSION) ==" -ForegroundColor Cyan
if ($OneFile) {
    python -m PyInstaller --noconfirm --clean --distpath dist/onefile --workpath build/onefile build.spec
} else {
    python -m PyInstaller --noconfirm --clean --distpath dist/onedir --workpath build/onedir build.spec
}

$exe = if ($OneFile) { '.\dist\onefile\MangaReader.exe' } else { '.\dist\onedir\MangaReader\MangaReader.exe' }
if (-not (Test-Path $exe)) {
    Write-Host '== 打包失败: 未找到 exe ==' -ForegroundColor Red
    exit 1
}
$size = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "== 完成: $exe ($size MB) ==" -ForegroundColor Green

if ($OneFile) {
    $zip = ".\dist\MangaReader-$env:APP_VERSION-windows-portable.zip"
    Compress-Archive -LiteralPath $exe -DestinationPath $zip -Force
    Write-Host "== 便携版: $zip ==" -ForegroundColor Green
}

if ($Installer) {
    if (-not (Test-Path .\dist\onedir\MangaReader\MangaReader.exe)) {
        Write-Host '== 生成安装包需要目录版产物 ==' -ForegroundColor Yellow
        $env:MR_ONEFILE = '0'
        python -m PyInstaller --noconfirm --clean --distpath dist/onedir --workpath build/onedir build.spec
    }
    $iscc = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) {
        Write-Host '== 未找到 Inno Setup 6，跳过安装包（winget install JRSoftware.InnoSetup）==' -ForegroundColor Yellow
    } else {
        Write-Host '== 编译安装包 ==' -ForegroundColor Cyan
        & $iscc "/DAppVersion=$env:APP_VERSION" "/DAppVersionNum=$env:APP_VERSION_NUM" 'installer\MangaReader.iss'
        if ($LASTEXITCODE -ne 0) { throw "ISCC 失败，退出码 $LASTEXITCODE" }
        Write-Host "== 安装包: .\dist\MangaReader-$env:APP_VERSION-windows-x64-setup.exe ==" -ForegroundColor Green
    }
}

exit 0
