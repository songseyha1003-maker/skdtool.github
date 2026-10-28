@echo off
setlocal
cd /d "%~dp0"
title SN TOOL - 1-Click Client Updater (Upgrade to v1.1.8)
color 0b
cls

echo ========================================================================
echo  🎬 SN TOOL STUDIO PRO - 1-CLICK CLIENT UPDATER (v1.1.8)
echo  📁 Unified Series Batch Dubbing Folder & Auto-Consolidation Pro
echo ========================================================================
echo.

echo [*] កំពុងបិទ Process ចាស់ដើម្បីការពារបញ្ហា File Lock Collision...
taskkill /f /im SN_TOOL.exe /im python.exe /im pythonw.exe >nul 2>&1
timeout /t 1 /nobreak >nul

if exist "%~dp0scripts\client_updater.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\client_updater.ps1"
    goto :END
)

if exist "scripts\client_updater.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\client_updater.ps1"
    goto :END
)

echo [*] កំពុងដំណើរការ Update ផ្ទាល់ពី Cloud CDN...
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/scripts/client_updater.ps1 | iex"

:END
echo.
echo ========================================================================
echo  Update process finished.
echo ========================================================================
echo.
pause
