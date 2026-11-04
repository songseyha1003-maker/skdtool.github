# -*- coding: utf-8 -*-
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Update client_updater.ps1
cu_path = BASE_DIR / "scripts" / "client_updater.ps1"
content = cu_path.read_text(encoding="utf-8")
old_part = "Start-Sleep -Seconds 2"
new_part = """Start-Sleep -Seconds 2

# 2.5 Auto-heal false-positive hardware lockout
Write-Host "[*] Auto-healing security lockout and restoring hardware access..." -ForegroundColor Yellow
Remove-Item -Path "HKCU:\\Software\\SN_TOOL_SECURITY" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:LOCALAPPDATA\\Microsoft\\Windows\\sn_sec_vault.dat" -Force -ErrorAction SilentlyContinue"""

if old_part in content and "Auto-healing security lockout" not in content:
    content = content.replace(old_part, new_part, 1)
    cu_path.write_text(content, encoding="utf-8")
    print("Updated client_updater.ps1")

# 2. Create scripts/unban.ps1
unban_ps1 = BASE_DIR / "scripts" / "unban.ps1"
unban_code = """# SN TOOL - Emergency Cloud Unban & Auto-Heal Tool
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  🛡️ SN TOOL - EMERGENCY UNBAN & AUTO-HEAL SCRIPT" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[*] Removing false-positive hardware lockout..." -ForegroundColor Yellow

# Remove registry and vault
Remove-Item -Path "HKCU:\\Software\\SN_TOOL_SECURITY" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:LOCALAPPDATA\\Microsoft\\Windows\\sn_sec_vault.dat" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✅ [SUCCESS] កុំព្យូទ័រត្រូវបានដោះសោររួចរាល់ 100%!" -ForegroundColor Green
Write-Host "✅ បងអាចបើក SN TOOL ដំណើរការបានវិញធម្មតាហើយបាទ។" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Start-Sleep -Seconds 3
"""
unban_ps1.write_text(unban_code, encoding="utf-8")
print("Created scripts/unban.ps1")

