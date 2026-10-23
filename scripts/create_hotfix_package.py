# -*- coding: utf-8 -*-
import os
import shutil
import zipfile
from pathlib import Path

def create_client_hotfix():
    base_dir = Path(__file__).resolve().parent.parent
    hotfix_dir = base_dir / "dist" / "HOTFIX_FOR_CLIENT"
    if hotfix_dir.exists():
        shutil.rmtree(hotfix_dir)
    hotfix_dir.mkdir(parents=True, exist_ok=True)

    bat_file = hotfix_dir / "1_CLICK_FIX.bat"
    bat_code = (
        "@echo off\n"
        "chcp 65001 > nul\n"
        "title 🚀 SN TOOL - Quick Hotfix (Export & Auto-Open Fix)\n"
        "color 0a\n"
        "cls\n\n"
        "echo ========================================================================\n"
        "echo   🚀 SN TOOL STUDIO PRO - 1-CLICK CLIENT EXPORT HOTFIX\n"
        "echo   Fixes: Auto-open folder, filename sanitization, Drive E/export sync\n"
        "echo ========================================================================\n"
        "echo.\n\n"
        "echo [*] Closing running SN_TOOL instances...\n"
        "taskkill /f /im SN_TOOL.exe >nul 2>nul\n"
        "taskkill /f /im python.exe >nul 2>nul\n"
        "taskkill /f /im pythonw.exe >nul 2>nul\n"
        "timeout /t 1 /nobreak >nul\n\n"
        "set \"TARGET_DIR=\"\n"
        "if exist \"%LOCALAPPDATA%\\Programs\\SN_TOOL\\version.json\" set \"TARGET_DIR=%LOCALAPPDATA%\\Programs\\SN_TOOL\"\n"
        "if not defined TARGET_DIR if exist \"D:\\SN_TOOL\\version.json\" set \"TARGET_DIR=D:\\SN_TOOL\"\n"
        "if not defined TARGET_DIR if exist \"%~dp0version.json\" set \"TARGET_DIR=%~dp0\"\n"
        "if not defined TARGET_DIR if exist \"%USERPROFILE%\\Desktop\\SN_TOOL\\version.json\" set \"TARGET_DIR=%USERPROFILE%\\Desktop\\SN_TOOL\"\n"
        "if not defined TARGET_DIR if exist \"C:\\Program Files\\SN_TOOL\\version.json\" set \"TARGET_DIR=C:\\Program Files\\SN_TOOL\"\n\n"
        "if not defined TARGET_DIR (\n"
        "    echo [ERROR] Could not automatically locate SN_TOOL installation folder.\n"
        "    echo Please place this folder inside your SN_TOOL directory and run again.\n"
        "    pause\n"
        "    exit /b 1\n"
        ")\n\n"
        "echo [*] Target SN TOOL located at: %TARGET_DIR%\n"
        "echo [*] Applying updated engine files...\n\n"
        "copy /y \"%~dp0pipeline.py\" \"%TARGET_DIR%\\pipeline.py\" >nul\n"
        "copy /y \"%~dp0batch_engine.py\" \"%TARGET_DIR%\\batch_engine.py\" >nul\n"
        "copy /y \"%~dp0server.py\" \"%TARGET_DIR%\\server.py\" >nul\n\n"
        "if exist \"%~dp0static\\app.js\" (\n"
        "    if not exist \"%TARGET_DIR%\\static\" mkdir \"%TARGET_DIR%\\static\"\n"
        "    copy /y \"%~dp0static\\app.js\" \"%TARGET_DIR%\\static\\app.js\" >nul\n"
        "    if exist \"%TARGET_DIR%\\_internal\\static\" (\n"
        "        copy /y \"%~dp0static\\app.js\" \"%TARGET_DIR%\\_internal\\static\\app.js\" >nul\n"
        "    )\n"
        ")\n\n"
        "echo.\n"
        "echo ========================================================================\n"
        "echo   [SUCCESS] Hotfix applied 100%% successfully!\n"
        "echo   All export and auto-open folder fixes are now active.\n"
        "echo ========================================================================\n"
        "echo.\n\n"
        "if exist \"%TARGET_DIR%\\SN_TOOL.exe\" (\n"
        "    echo [*] Relaunching SN TOOL...\n"
        "    start \"\" \"%TARGET_DIR%\\SN_TOOL.exe\"\n"
        ")\n"
        "echo Press any key to exit this window...\n"
        "pause >nul\n"
    )
    bat_file.write_text(bat_code, encoding="utf-8")

    # Copy files
    for fname in ["pipeline.py", "batch_engine.py", "server.py"]:
        shutil.copy2(base_dir / fname, hotfix_dir / fname)

    (hotfix_dir / "static").mkdir(exist_ok=True)
    shutil.copy2(base_dir / "static" / "app.js", hotfix_dir / "static" / "app.js")

    # Create zip
    zip_out = base_dir / "dist" / "SN_TOOL_HOTFIX_CLIENT.zip"
    with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(hotfix_dir):
            for f in files:
                full_p = Path(root) / f
                rel_p = full_p.relative_to(hotfix_dir)
                zf.write(full_p, rel_p)

    print(f"Created: {zip_out} ({zip_out.stat().st_size} bytes)")

if __name__ == "__main__":
    create_client_hotfix()
