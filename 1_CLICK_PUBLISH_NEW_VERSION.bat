@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title 🚀 SN TOOL - 1-Click Master OTA Update Publisher
color 0b
cls

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python scripts\publish_update.py
    goto :DONE
)

py -3.14 scripts\publish_update.py
if %ERRORLEVEL% EQU 0 goto :DONE

py scripts\publish_update.py
if %ERRORLEVEL% EQU 0 goto :DONE

if exist "%LOCALAPPDATA%\Programs\SN_TOOL\_internal\python.exe" (
    "%LOCALAPPDATA%\Programs\SN_TOOL\_internal\python.exe" scripts\publish_update.py
    goto :DONE
)

echo [ERROR] Python not found. Please install Python to run this publisher.
pause

:DONE
