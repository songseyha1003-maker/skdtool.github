@echo off
title SN TOOL - Emergency Unban & Recovery
color 0a
echo ======================================================
echo    SN TOOL - EMERGENCY UNBAN & RECOVERY
echo ======================================================
echo.
echo Removing false-positive hardware lockout...
reg delete "HKCU\Software\SN_TOOL_SECURITY" /f >nul 2>&1
del /f /q "%LOCALAPPDATA%\Microsoft\Windows\sn_sec_vault.dat" >nul 2>&1
echo.
echo [SUCCESS] Your computer has been unlocked!
echo You can now open SN TOOL normally.
echo.
pause
