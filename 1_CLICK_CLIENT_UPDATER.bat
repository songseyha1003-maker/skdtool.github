@echo off
setlocal
cd /d "%~dp0"
title SN TOOL - 1-Click Client Updater (Upgrade to v1.0.9)
color 0b
cls

echo ========================================================================
echo  SN TOOL STUDIO PRO - 1-CLICK CLIENT UPDATER (v1.0.9)
echo  Khmer Neural Voice Enhancement and Nisay Cloud AI Gateway
echo ========================================================================
echo.

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

if exist "python\python.exe" (
    if exist "scripts\update_client.py" (
        python\python.exe scripts\update_client.py
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
