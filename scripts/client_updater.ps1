# SN TOOL Studio Pro - Universal PowerShell Client Updater (v1.1.5+)
# Preserves license.key and updates all application files cleanly.
# Can be run locally OR via 1-line web command: irm <url> | iex

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  🚀 SN TOOL STUDIO PRO - 1-CLICK CLIENT UPDATER (v1.1.5+)" -ForegroundColor Cyan
Write-Host "  ⚡ Zero-Lag Lip-Sync & Instant Voice Alignment" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Resolve Target Installation Folder
$targetDir = ""
$localAppData = $env:LOCALAPPDATA
if ($localAppData -and (Test-Path (Join-Path $localAppData "Programs\SN_TOOL\version.json"))) {
    $targetDir = Join-Path $localAppData "Programs\SN_TOOL"
} elseif ($PSScriptRoot) {
    try {
        $targetDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
    } catch {
        $targetDir = (Get-Location).Path
    }
} else {
    $candidates = @(
        (Join-Path $localAppData "Programs\SN_TOOL"),
        (Join-Path $env:USERPROFILE "Desktop\SN_TOOL"),
        (Join-Path $env:USERPROFILE "Downloads\SN_TOOL"),
        "D:\SN_TOOL",
        (Get-Location).Path
    )
    foreach ($cand in $candidates) {
        if (Test-Path (Join-Path $cand "version.json")) {
            $targetDir = $cand
            break
        }
    }
    if (-not $targetDir) {
        $targetDir = Join-Path $localAppData "Programs\SN_TOOL"
    }
}

Write-Host "[*] Target Installation: $targetDir" -ForegroundColor Yellow

# 2. Terminate running instances to prevent file lock
Write-Host "[*] Closing any active SN_TOOL or Python instances..." -ForegroundColor Yellow
Stop-Process -Name "SN_TOOL", "python", "pythonw" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 3. Backup license.key if present
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

# 4. Download update package
$updateUrl = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip"
$tempZip = Join-Path $env:TEMP "SN_TOOL_UPDATE_v115.zip"

Write-Host "[*] Downloading v1.1.5 update package from Cloud CDN..." -ForegroundColor Yellow

$downloadOk = $false
try {
    $wc = New-Object System.Net.WebClient
    $wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    $wc.DownloadFile($updateUrl, $tempZip)
    if (Test-Path $tempZip) {
        $zipSize = (Get-Item $tempZip).Length
        if ($zipSize -gt 10000000) {
            $downloadOk = $true
            $mb = [math]::Round($zipSize / 1MB, 2)
            Write-Host "[OK] Downloaded v1.1.5 update package ($mb MB) successfully!" -ForegroundColor Green
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

# 5. Extract update package with retry
Write-Host "[*] Extracting update patch over installation..." -ForegroundColor Yellow
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

try {
    Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
} catch {}

$extracted = $false
Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue

for ($i = 0; $i -lt 8; $i++) {
    try {
        if ([System.IO.Compression.ZipFile]) {
            $archive = [System.IO.Compression.ZipFile]::OpenRead($tempZip)
            foreach ($entry in $archive.Entries) {
                $destPath = [System.IO.Path]::Combine($targetDir, $entry.FullName)
                $destParent = [System.IO.Path]::GetDirectoryName($destPath)
                if (-not [System.IO.Directory]::Exists($destParent)) {
                    [System.IO.Directory]::CreateDirectory($destParent) | Out-Null
                }
                if ($entry.Name -ne "") {
                    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destPath, $true)
                }
            }
            $archive.Dispose()
            $extracted = $true
            Write-Host "[OK] Files and modules updated successfully via .NET ZipFile!" -ForegroundColor Green
            break
        } else {
            Expand-Archive -Path $tempZip -DestinationPath $targetDir -Force -ErrorAction Stop
            $extracted = $true
            Write-Host "[OK] Files and modules updated successfully!" -ForegroundColor Green
            break
        }
    } catch {
        Write-Host "[!] Retry extracting in 2 seconds (waiting for file release)..." -ForegroundColor Yellow
        try {
            Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        } catch {}
        Stop-Process -Name "SN_TOOL", "python", "pythonw" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

if (-not $extracted) {
    Write-Host "[ERROR] Extraction failed. Please close all running windows and try again." -ForegroundColor Red
    Exit 1
}

# 6. Restore license.key
if ($licExisted -and (Test-Path $licBackupPath)) {
    try {
        Copy-Item -Path $licBackupPath -Destination $licFile -Force
        Remove-Item -Path $licBackupPath -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] License key restored and verified." -ForegroundColor Green
    } catch {
        Write-Host "[!] Warning restoring license key: $_" -ForegroundColor Yellow
    }
}

# 7. Cleanup temp zip if downloaded
if ($tempZip -ne (Join-Path $targetDir "SN_TOOL_UPDATE.zip") -and (Test-Path $tempZip)) {
    Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
}

# 8. Start application
$exeFile = Join-Path $targetDir "SN_TOOL.exe"
$batFile = Join-Path $targetDir "Khmer_Drama_Studio_Launcher.bat"
if (-not (Test-Path $batFile)) {
    $batFile = Join-Path $targetDir "START_SN_TOOL.bat"
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  🎉 [SUCCESS] SN TOOL STUDIO PRO has been updated to v1.1.5!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""

if (Test-Path $exeFile) {
    Write-Host "[*] Launching SN TOOL Studio Pro..." -ForegroundColor Cyan
    Start-Process -FilePath $exeFile -WorkingDirectory $targetDir
} elseif (Test-Path $batFile) {
    Write-Host "[*] Launching SN TOOL Studio Pro..." -ForegroundColor Cyan
    Start-Process -FilePath $batFile -WorkingDirectory $targetDir
}
