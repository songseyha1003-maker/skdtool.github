@echo off
cd /d "%~dp0"
title SN TOOL - Google Drive Cloud Staging
color 0e
cls

echo ========================================================================
echo  SN TOOL - GOOGLE DRIVE CLOUD UPDATE STAGING (v1.1.0)
echo ========================================================================
echo.
echo  Opening Google Drive Folder in your browser...
start https://drive.google.com/drive/folders/1d1OhBZRLjz-JgEJo0ccfOpsWtoTxWbrN

echo.
echo  Opening local dist\READY_FOR_GOOGLE_DRIVE folder in File Explorer...
explorer.exe "%~dp0dist\READY_FOR_GOOGLE_DRIVE"

echo.
echo ========================================================================
echo  Please DRAG and DROP these files into the Google Drive folder:
echo     1. version.json (v1.1.0)
echo     2. SN_TOOL_UPDATE.zip (In-App Auto-Update Patch)
echo     3. SN_TOOL_Setup.exe (Full Standalone Installer v1.1.0)
echo ========================================================================
echo.
pause
