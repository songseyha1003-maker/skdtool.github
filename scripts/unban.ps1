# SN TOOL - Emergency Cloud Unban & Auto-Heal Tool
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  🛡️ SN TOOL - EMERGENCY UNBAN & AUTO-HEAL SCRIPT" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[*] Removing false-positive hardware lockout..." -ForegroundColor Yellow

# Remove registry and vault
Remove-Item -Path "HKCU:\Software\SN_TOOL_SECURITY" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "$env:LOCALAPPDATA\Microsoft\Windows\sn_sec_vault.dat" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "✅ [SUCCESS] កុំព្យូទ័រត្រូវបានដោះសោររួចរាល់ 100%!" -ForegroundColor Green
Write-Host "✅ បងអាចបើក SN TOOL ដំណើរការបានវិញធម្មតាហើយបាទ។" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Start-Sleep -Seconds 3
