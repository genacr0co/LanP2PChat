#define MyAppName "LAN P2P Chat"
#define MyAppVersion "1.0.0"
#define MyAppExeName "LANP2PChat.exe"

[Setup]
AppId={{A7B96B92-2A57-4F8A-9B2E-LANP2PCHAT}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\LANP2PChat
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=LANP2PChat_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "dist\LANP2PChat\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\LAN P2P Chat"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\LAN P2P Chat"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить LAN P2P Chat"; Flags: nowait postinstall skipifsilent

; 🔥 УДАЛЕНИЕ ПЕРЕД УСТАНОВКОЙ
[InstallDelete]
Type: filesandordirs; Name: "{localappdata}\Programs\LANP2PChat"
Type: filesandordirs; Name: "{localappdata}\LANP2PChat"

; 🔥 УДАЛЕНИЕ ПРИ ДЕИНСТАЛЛЯЦИИ
[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\Programs\LANP2PChat"
Type: filesandordirs; Name: "{localappdata}\LANP2PChat"