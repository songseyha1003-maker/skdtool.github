@echo off
setlocal
cd /d "%~dp0"
title SN TOOL - 1-Click Client Updater (Upgrade to v2.0.7)
color 0b
cls

echo ========================================================================
echo  🎬 SN TOOL - 1-CLICK CLIENT UPDATER (v2.0.7+)
echo  🎬 1080p Video+Audio Downloader + Hardened SHA-256 OTA Updater
echo ========================================================================
echo.

echo [*] Checking running SN TOOL installation and preparing updater...

if exist "%~dp0scripts\client_updater.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\client_updater.ps1"
    goto :END
)

if exist "scripts\client_updater.ps1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\client_updater.ps1"
    goto :END
)

taskkill /f /im SN_TOOL.exe >nul 2>&1
timeout /t 1 /nobreak >nul
echo [*] កំពុងដំណើរការ Update ផ្ទាល់ពី Cloud CDN...
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/scripts/client_updater.ps1 | iex"

:END
echo.
echo ========================================================================
echo  Update process finished.
echo ========================================================================
echo.
pause
