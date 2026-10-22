@echo off
setlocal
cd /d "%~dp0"
title SN TOOL - 1-Click Client Updater (Upgrade to v1.1.3)
color 0b
cls

echo ========================================================================
echo  🎬 SN TOOL STUDIO PRO - 1-CLICK CLIENT UPDATER (v1.1.3)
echo  ⚡ 4x Fast Neural Voice Synthesis & Zero-Drop Nisay Translation
echo ========================================================================
echo.

echo [*] កំពុងបិទ Process ចាស់ដើម្បីការពារបញ្ហា File Lock Collision...
taskkill /f /im SN_TOOL.exe /im pythonw.exe >nul 2>&1
timeout /t 1 /nobreak >nul

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    if exist "scripts\update_client.py" (
        python scripts\update_client.py
        goto :END
    )
)

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    if exist "scripts\update_client.py" (
        py scripts\update_client.py
        goto :END
    )
)

if exist "%LOCALAPPDATA%\Programs\SN_TOOL\_internal\python.exe" (
    if exist "scripts\update_client.py" (
        "%LOCALAPPDATA%\Programs\SN_TOOL\_internal\python.exe" scripts\update_client.py
        goto :END
    )
)

if exist "scripts\client_updater.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\client_updater.ps1"
    goto :END
)

echo [ERROR] Update scripts not found. Please verify the folder structure.

:END
echo.
echo ========================================================================
echo  Update process finished.
echo ========================================================================
echo.
pause
