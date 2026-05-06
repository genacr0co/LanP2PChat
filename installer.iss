#define MyAppName "LAN P2P Chat"
#define MyAppVersion "1.0.3"
#define MyAppExeName "LANP2PChat.exe"
#define MyAppIcon "static\src\assets\logo_gers_new.ico"

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
SetupIconFile={#MyAppIcon}
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersion}
VersionInfoProductName={#MyAppName}
VersionInfoDescription={#MyAppName} Installer

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "dist\LANP2PChat\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\LAN P2P Chat"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\LAN P2P Chat"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить LAN P2P Chat"; Flags: nowait postinstall skipifsilent; Check: not ShouldLaunchAppAfterSilentUpdate
Filename: "{app}\{#MyAppExeName}"; Flags: nowait skipifdoesntexist; Check: ShouldLaunchAppAfterSilentUpdate

; При обновлении НЕ удаляем {localappdata}\LANP2PChat,
; чтобы не потерять сообщения, группы и настройки пользователя.
; Старые файлы приложения в {app} перезаписываются секцией [Files].

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\Programs\LANP2PChat"

[Code]
function ShouldLaunchAppAfterSilentUpdate(): Boolean;
begin
  Result := ExpandConstant('{param:LAUNCHAPP|0}') = '1';
end;
