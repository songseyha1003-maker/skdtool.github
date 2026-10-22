@echo off
chcp 65001 >nul
title SN TOOL - LICENSE ACTIVATION SCREEN PREVIEW (FOR VIDEO RECORDING)

echo ===============================================================================
echo     🔑 SN TOOL STUDIO PRO - LICENSE KEY ACTIVATION SCREEN (VIDEO SHOT)
echo ===============================================================================
echo.
echo [INFO] Opening License Activation Gate Screen for Video Recording / Editing...
echo [TIP] Press 'H' in the window to Hide/Show the Video Recording Assistant toolbar.
echo.

set "HTML_FILE=%~dp0static\preview_license_key.html"
set "SERVER_URL=http://127.0.0.1:8000/preview_license_key.html"

:: Check if Edge exists for frameless app window (looks 100%% like native app)
set "EDGE_EXE=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE_EXE%" set "EDGE_EXE=C:\Program Files\Microsoft\Edge\Application\msedge.exe"

set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

if exist "%EDGE_EXE%" (
    echo [OK] Launching in Frameless App Window with Microsoft Edge...
    start "" "%EDGE_EXE%" --app="file:///%HTML_FILE:\=/%" --window-size=1150,800
    exit /b 0
)

if exist "%CHROME_EXE%" (
    echo [OK] Launching in Frameless App Window with Google Chrome...
    start "" "%CHROME_EXE%" --app="file:///%HTML_FILE:\=/%" --window-size=1150,800
    exit /b 0
)

:: Fallback to default browser
echo [OK] Launching in Default Browser...
start "" "%HTML_FILE%"
exit /b 0
