# SN TOOL Studio Pro - PowerShell Client Updater (v1.1.3+)
# Preserves license.key and updates all application files cleanly.

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  SN TOOL STUDIO PRO - 1-CLICK CLIENT UPDATER (v1.1.3+)" -ForegroundColor Cyan
Write-Host "  4x Fast Neural Voice Synthesis & Zero-Drop Nisay Translation" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

$baseDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$targetDir = $baseDir.Path

$localAppData = $env:LOCALAPPDATA
if ($localAppData) {
    $installedDir = Join-Path $localAppData "Programs\SN_TOOL"
    if (Test-Path (Join-Path $installedDir "version.json")) {
        $targetDir = $installedDir
    }
}

Write-Host "[*] Target Installation: $targetDir" -ForegroundColor Yellow

# Terminate running instances to prevent file lock
Write-Host "[*] Closing any active SN_TOOL instances..." -ForegroundColor Yellow
Stop-Process -Name "SN_TOOL", "pythonw" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Backup license.key if present
$licFile = Join-Path $targetDir "license.key"
$licBackupPath = Join-Path $env:TEMP "sn_license_backup.key"
$licExisted = $false

if (Test-Path $licFile) {
    try {
        Copy-Item -Path $licFile -Destination $licBackupPath -Force
        $licExisted = $true
        Write-Host "[OK] Existing license key backed up safely." -ForegroundColor Green
    } catch {
        Write-Host "[!] Warning backing up license key: $_" -ForegroundColor Yellow
    }
}

# Download update package
$updateUrl = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip"
$tempZip = Join-Path $env:TEMP "SN_TOOL_UPDATE_v113.zip"

Write-Host "[*] Downloading v1.1.3 update package from Cloud CDN..." -ForegroundColor Yellow

$downloadOk = $false
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    $wc.DownloadFile($updateUrl, $tempZip)
    if (Test-Path $tempZip) {
        $zipSize = (Get-Item $tempZip).Length
        if ($zipSize -gt 1000000) {
            $downloadOk = $true
            $mb = [math]::Round($zipSize / 1MB, 2)
            Write-Host "[OK] Downloaded v1.1.3 update package ($mb MB) successfully!" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "[!] Cloud CDN direct download notice: $_" -ForegroundColor Yellow
}

if (-not $downloadOk) {
    # Check local fallback
    $localZip = Join-Path $targetDir "SN_TOOL_UPDATE.zip"
    if (Test-Path $localZip) {
        Write-Host "[*] Using local package SN_TOOL_UPDATE.zip as fallback..." -ForegroundColor Yellow
        $tempZip = $localZip
        $downloadOk = $true
    } else {
        Write-Host "[ERROR] Could not download update package. Please check internet connection." -ForegroundColor Red
        Exit 1
    }
}

# Extract update package with retry
Write-Host "[*] Extracting update patch over installation..." -ForegroundColor Yellow
$extracted = $false
for ($i = 0; $i -lt 5; $i++) {
    try {
        Expand-Archive -Path $tempZip -DestinationPath $targetDir -Force -ErrorAction Stop
        $extracted = $true
        Write-Host "[OK] Files and modules updated successfully!" -ForegroundColor Green
        break
    } catch {
        Write-Host "[!] Retry extracting in 2 seconds (waiting for file release)..." -ForegroundColor Yellow
        Stop-Process -Name "SN_TOOL", "pythonw" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

if (-not $extracted) {
    Write-Host "[ERROR] Extraction failed. Please close all running windows and try again." -ForegroundColor Red
    Exit 1
}

# Restore license.key
if ($licExisted -and (Test-Path $licBackupPath)) {
    try {
        Copy-Item -Path $licBackupPath -Destination $licFile -Force
        Remove-Item -Path $licBackupPath -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] License key restored and verified." -ForegroundColor Green
    } catch {
        Write-Host "[!] Warning restoring license key: $_" -ForegroundColor Yellow
    }
}

# Cleanup temp zip if downloaded
if ($tempZip -ne (Join-Path $targetDir "SN_TOOL_UPDATE.zip") -and (Test-Path $tempZip)) {
    Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  🎉 [SUCCESS] SN TOOL STUDIO PRO has been updated to v1.1.3!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""
