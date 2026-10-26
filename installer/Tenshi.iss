#define AppName "Tenshi"
#define AppVersion "3.0.3"

[Setup]
AppId={{C2771C39-6ACF-4F62-AFDC-C5B5D8D4C28A}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
VersionInfoVersion=3.0.3.0
VersionInfoDescription=Tenshi Windows Installer
VersionInfoProductName=Tenshi
VersionInfoProductVersion=3.0.3.0
DefaultDirName={localappdata}\Programs\Tenshi
DefaultGroupName=Tenshi
PrivilegesRequired=lowest
OutputDir=..\installer_output
OutputBaseFilename=Tenshi_Setup_3.0.3
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
LicenseFile=..\LICENSE
SetupIconFile=..\recoverydesk\assets\tenshi.ico
UninstallDisplayIcon={app}\Tenshi.exe
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\Tenshi.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Tenshi"; Filename: "{app}\Tenshi.exe"
Name: "{autodesktop}\Tenshi"; Filename: "{app}\Tenshi.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Zusaetzliche Symbole:"; Flags: unchecked

[Run]
Filename: "{app}\Tenshi.exe"; Description: "Tenshi starten"; Flags: nowait postinstall skipifsilent shellexec
