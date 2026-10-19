@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title ☁️ SN TOOL - Set Google Drive Auto-Update Link
color 0b
cls

python scripts\set_update_link.py
if %ERRORLEVEL% NEQ 0 (
    py -3.14 scripts\set_update_link.py
)

echo.
pause
