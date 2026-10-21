@echo off
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title ⚡ SN TOOL - Admin License Key Generator Dashboard
color 0b
cls
echo ========================================================
echo  ⚡ SN TOOL - ADMIN LICENSE KEY GENERATOR DASHBOARD
echo  🔐 ប្រព័ន្ធបង្កើត និងគ្រប់គ្រង KEY ជូនទៅកាន់ CUSTOMER
echo ========================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python admin_dashboard.py
    if %ERRORLEVEL% NEQ 0 pause
    goto :END
)

py -3.14 --version >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3.14 admin_dashboard.py
    if %ERRORLEVEL% NEQ 0 pause
    goto :END
)

py --version >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py admin_dashboard.py
    if %ERRORLEVEL% NEQ 0 pause
    goto :END
)

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" admin_dashboard.py
    if %ERRORLEVEL% NEQ 0 pause
    goto :END
)

if exist "C:\Users\TUF\AppData\Local\Programs\Python\Python312\python.exe" (
    "C:\Users\TUF\AppData\Local\Programs\Python\Python312\python.exe" admin_dashboard.py
    if %ERRORLEVEL% NEQ 0 pause
    goto :END
)

if exist "dist\ADMIN_KEY_GENERATOR\ADMIN_KEY_GENERATOR.exe" (
    start "" "dist\ADMIN_KEY_GENERATOR\ADMIN_KEY_GENERATOR.exe"
    goto :END
)

echo [ERROR] Python not found! Please install Python.
pause

:END