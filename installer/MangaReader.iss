; 漫画阅读器 - Windows 安装包（Inno Setup 6）
; 用法: ISCC.exe /DAppVersion=1.2.3 installer\MangaReader.iss
; 前置: 先跑 pyinstaller（目录版），产物在 dist\onedir\MangaReader\

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#ifndef AppVersionNum
  #define AppVersionNum "1.0.0.0"
#endif

#define AppName "漫画阅读器"
#define AppExe "MangaReader.exe"
#define AppPublisher "MangaReader"
#define AppURL "https://github.com/"

[Setup]
AppId={{7C4B1F52-9A3E-4E6D-9C1B-2F5D8A0E3B77}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersionNum}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
DefaultDirName={autopf}\MangaReader
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=MangaReader-{#AppVersion}-windows-x64-setup
SetupIconFile=..\img.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
AllowNoIcons=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "..\dist\onedir\MangaReader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "立即启动 {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
