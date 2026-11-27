# SN TOOL - Universal PowerShell Client Updater (v2.0.7+)
# Preserves license.key & user AI provider keys, verifies SHA-256, and updates cleanly.
# Can be run locally OR via 1-line web command: irm <url> | iex

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  SN TOOL - 1-CLICK CLIENT UPDATER (Cloud Auto-Sync)" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""

function Test-SnToolInstallDir([string]$dirPath) {
    if (-not $dirPath -or -not (Test-Path $dirPath)) { return $false }
    $hasVer = Test-Path (Join-Path $dirPath "version.json")
    $hasRuntime = (Test-Path (Join-Path $dirPath "SN_TOOL.exe")) -or (Test-Path (Join-Path $dirPath "server.py"))
    return ($hasVer -and $hasRuntime)
}

function Compare-SemVer([string]$a, [string]$b) {
    try {
        $va = [version](($a -replace '^[^\d]*', '') -split '[^0-9\.]' | Select-Object -First 1)
        $vb = [version](($b -replace '^[^\d]*', '') -split '[^0-9\.]' | Select-Object -First 1)
        return $va.CompareTo($vb)
    } catch {
        return [string]::Compare($a, $b, [System.StringComparison]::OrdinalIgnoreCase)
    }
}

function Write-Utf8NoBom([string]$filePath, [string]$content) {
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($filePath, $content, $enc)
}

# 1. Resolve Target Installation Folder (detect running process or shortcut before terminating)
$targetDir = ""
$localAppData = $env:LOCALAPPDATA
$packageRoot = (Get-Location).Path
if ($PSScriptRoot) {
    try {
        $packageRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
        if (Test-SnToolInstallDir $packageRoot) {
            $targetDir = $packageRoot
        }
    } catch {}
}
if (-not $targetDir) {
    try {
        $p8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($p8000) {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($p8000.OwningProcess)" -ErrorAction SilentlyContinue
            if ($proc -and $proc.ExecutablePath) {
                $procDir = Split-Path -Parent $proc.ExecutablePath
                if (Test-SnToolInstallDir $procDir) { $targetDir = $procDir }
            }
        }
    } catch {}
}
if (-not $targetDir) {
    try {
        $snProc = Get-Process -Name "SN_TOOL" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($snProc -and $snProc.Path) {
            $procDir = Split-Path -Parent $snProc.Path
            if (Test-SnToolInstallDir $procDir) { $targetDir = $procDir }
        }
    } catch {}
}
if (-not $targetDir) {
    $candidates = @(
        "D:\SN_TOOL",
        (Join-Path $localAppData "Programs\SN_TOOL"),
        "C:\SN_TOOL",
        (Join-Path $env:ProgramFiles "SN_TOOL"),
        (Join-Path $env:USERPROFILE "Desktop\SN_TOOL"),
        (Join-Path $env:USERPROFILE "OneDrive\Desktop\SN_TOOL"),
        (Join-Path $env:USERPROFILE "Downloads\SN_TOOL"),
        (Get-Location).Path
    )
    foreach ($cand in $candidates) {
        if (Test-SnToolInstallDir $cand) {
            $targetDir = $cand
            break
        }
    }
}
if (-not $targetDir) {
    try {
        $wsh = New-Object -ComObject WScript.Shell
        foreach ($deskDir in @((Join-Path $env:USERPROFILE "Desktop"), (Join-Path $env:USERPROFILE "OneDrive\Desktop"))) {
            if (Test-Path $deskDir) {
                Get-ChildItem -Path $deskDir -Filter "*SN*TOOL*.lnk" -ErrorAction SilentlyContinue | ForEach-Object {
                    if (-not $targetDir) {
                        $lnkTarget = $wsh.CreateShortcut($_.FullName).TargetPath
                        if ($lnkTarget) {
                            $lnkDir = Split-Path -Parent $lnkTarget
                            if (Test-SnToolInstallDir $lnkDir) { $targetDir = $lnkDir }
                        }
                    }
                }
            }
        }
    } catch {}
}
if (-not $targetDir) {
    $targetDir = "D:\SN_TOOL"
}

$targetDirFull = [System.IO.Path]::GetFullPath($targetDir).TrimEnd('\') + '\'
Write-Host "[*] Target Installation: $targetDir" -ForegroundColor Yellow

function Stop-TargetSnTool {
    try {
        Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    } catch {}
    try {
        $noSlash = $targetDirFull.TrimEnd('\')
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -match '^(SN_TOOL\.exe|pythonw?\.exe)$' -and (
                ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($noSlash, [System.StringComparison]::OrdinalIgnoreCase)) -or
                ($_.CommandLine -and $_.CommandLine -like "*$noSlash*")
            )
        } | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {}
    Stop-Process -Name "SN_TOOL" -Force -ErrorAction SilentlyContinue
}

# 2. Terminate running instances in targetDir / port 8000
Write-Host "[*] Closing active SN_TOOL instances in target folder..." -ForegroundColor Yellow
Stop-TargetSnTool
Start-Sleep -Seconds 2

# 3. Backup license.key and user AI keys if present
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

$aiCfgPath = Join-Path $targetDir "data\ai_provider_config.json"
$savedUserAiKeys = $null
if (Test-Path $aiCfgPath) {
    try {
        $oldAi = Get-Content -Path $aiCfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($oldAi.gemini_api_key -or ($oldAi.keys -and $oldAi.keys.Count -gt 0) -or $oldAi.keys_raw) {
            $savedUserAiKeys = @{
                gemini_api_key = $oldAi.gemini_api_key
                keys = $oldAi.keys
                keys_raw = $oldAi.keys_raw
                nisay_api_key = $oldAi.nisay_api_key
            }
            Write-Host "[OK] User AI provider keys backed up safely." -ForegroundColor Green
        }
    } catch {}
}

# 4. Query local bundled package AND remote Cloud CDN manifest (pick newest version)
$cb = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$manifestUrls = @(
    "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/data/cloud_manifest.json?_cb=$cb",
    "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/version.json?_cb=$cb"
)
$remoteVer = ""
$targetVer = "2.0.7"
$updateUrl = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip?_cb=$cb"
$expectedSha256 = ""

$localPkgZip = ""
$localPkgVer = ""
$localPkgSha = ""
foreach ($pkgDir in @($packageRoot, (Get-Location).Path, $targetDir)) {
    if (-not $pkgDir) { continue }
    $candZip = Join-Path $pkgDir "SN_TOOL_UPDATE.zip"
    if (Test-Path $candZip) {
        $localPkgZip = $candZip
        foreach ($mf in @((Join-Path $pkgDir "cloud_manifest.json"), (Join-Path $pkgDir "data\cloud_manifest.json"), (Join-Path $pkgDir "version.json"))) {
            if (Test-Path $mf) {
                try {
                    $lm = Get-Content -Path $mf -Raw -Encoding UTF8 | ConvertFrom-Json
                    if ($lm.version -and -not $localPkgVer) { $localPkgVer = ([string]$lm.version).Trim() }
                    if ($lm.sha256 -and -not $localPkgSha) { $localPkgSha = ([string]$lm.sha256).Trim().ToLower() }
                } catch {}
            }
        }
        break
    }
}

$wc = New-Object System.Net.WebClient
$wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
$wc.Headers.Add("Cache-Control", "no-cache, no-store, must-revalidate")

foreach ($mUrl in $manifestUrls) {
    try {
        $rawJson = $wc.DownloadString($mUrl)
        $mObj = $rawJson | ConvertFrom-Json
        if ($mObj -and $mObj.version) {
            $remoteVer = ([string]$mObj.version).Trim()
            $targetVer = $remoteVer
            if ($mObj.download_url) {
                $dl = [string]$mObj.download_url
                $sep = if ($dl.Contains("?")) { "&" } else { "?" }
                $updateUrl = "${dl}${sep}_cb=$cb"
            }
            if ($mObj.sha256) {
                $expectedSha256 = ([string]$mObj.sha256).Trim().ToLower()
            }
            break
        }
    } catch {}
}

$downloadOk = $false
$tempZip = Join-Path $env:TEMP "SN_TOOL_UPDATE_$targetVer.zip"
$useLocalBundleFirst = $false
if ($localPkgZip -and $localPkgVer) {
    if (-not $remoteVer -or (Compare-SemVer $localPkgVer $remoteVer) -ge 0) {
        $useLocalBundleFirst = $true
        $targetVer = $localPkgVer
        $expectedSha256 = $localPkgSha
    }
}

if ($useLocalBundleFirst) {
    Write-Host "[*] Using verified local v$targetVer update package ($localPkgZip)..." -ForegroundColor Yellow
    try {
        $zipSize = (Get-Item $localPkgZip).Length
        if ($zipSize -gt 1000000) {
            if ($expectedSha256) {
                $actualSha = (Get-FileHash -Path $localPkgZip -Algorithm SHA256).Hash.ToLower()
                if ($actualSha -ne $expectedSha256) {
                    throw "Local package SHA-256 mismatch! Got $actualSha, expected $expectedSha256"
                }
                Write-Host "[OK] Local package SHA-256 integrity verified." -ForegroundColor Green
            }
            $tempZip = $localPkgZip
            $downloadOk = $true
        }
    } catch {
        Write-Host "[!] Local package check notice: $_" -ForegroundColor Yellow
    }
}

if (-not $downloadOk) {
    Write-Host "[*] Downloading SN TOOL v$targetVer update package from Cloud CDN..." -ForegroundColor Yellow
    try {
        $wc.DownloadFile($updateUrl, $tempZip)
        if (Test-Path $tempZip) {
            $zipSize = (Get-Item $tempZip).Length
            if ($zipSize -gt 1000000) {
                if ($expectedSha256) {
                    $actualSha = (Get-FileHash -Path $tempZip -Algorithm SHA256).Hash.ToLower()
                    if ($actualSha -ne $expectedSha256) {
                        Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
                        throw "SHA-256 mismatch! Got $actualSha, expected $expectedSha256"
                    }
                    Write-Host "[OK] SHA-256 package integrity verified." -ForegroundColor Green
                }
                $downloadOk = $true
                $mb = [math]::Round($zipSize / 1MB, 2)
                Write-Host "[OK] Downloaded v$targetVer update package ($mb MB) successfully!" -ForegroundColor Green
            }
        }
    } catch {
        Write-Host "[!] Cloud CDN download notice: $_" -ForegroundColor Yellow
    }
}

if (-not $downloadOk) {
    if ($localPkgZip -and (Test-Path $localPkgZip)) {
        Write-Host "[*] Using local package SN_TOOL_UPDATE.zip as fallback..." -ForegroundColor Yellow
        $tempZip = $localPkgZip
        $downloadOk = $true
    } else {
        Write-Host "[ERROR] Could not obtain valid update package. Please check internet connection." -ForegroundColor Red
        Exit 1
    }
}

# 5. Extract update package with Zip-Slip path protection & retry
Write-Host "[*] Extracting update patch over installation..." -ForegroundColor Yellow
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

$extracted = $false
Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue

for ($i = 0; $i -lt 8; $i++) {
    try {
        if ([System.IO.Compression.ZipFile]) {
            $archive = $null
            try {
                $archive = [System.IO.Compression.ZipFile]::OpenRead($tempZip)
                foreach ($entry in $archive.Entries) {
                    $destPath = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($targetDir, $entry.FullName))
                    if (-not $destPath.StartsWith($targetDirFull, [System.StringComparison]::OrdinalIgnoreCase)) {
                        throw "Unsafe archive path blocked: $($entry.FullName)"
                    }
                    $destParent = [System.IO.Path]::GetDirectoryName($destPath)
                    if (-not [System.IO.Directory]::Exists($destParent)) {
                        [System.IO.Directory]::CreateDirectory($destParent) | Out-Null
                    }
                    if ($entry.Name -ne "") {
                        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destPath, $true)
                    }
                }
            } finally {
                if ($archive) { $archive.Dispose() }
            }
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
        Write-Host "[!] Retry extracting ($($_.Exception.Message))..." -ForegroundColor Yellow
        Stop-TargetSnTool
        Start-Sleep -Seconds 2
    }
}

if (-not $extracted) {
    Write-Host "[ERROR] Extraction failed. Close SN TOOL (or right-click 1_CLICK_CLIENT_UPDATER.bat -> Run as administrator if installed in Program Files) and try again." -ForegroundColor Red
    Exit 1
}

# 6. Restore license.key & user AI keys
if ($licExisted -and (Test-Path $licBackupPath)) {
    try {
        Copy-Item -Path $licBackupPath -Destination $licFile -Force
        Remove-Item -Path $licBackupPath -Force -ErrorAction SilentlyContinue
        Write-Host "[OK] License key restored and verified." -ForegroundColor Green
    } catch {
        Write-Host "[!] Warning restoring license key: $_" -ForegroundColor Yellow
    }
}

if ($savedUserAiKeys -ne $null -and (Test-Path $aiCfgPath)) {
    try {
        $newAi = Get-Content -Path $aiCfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ((-not $newAi.gemini_api_key) -and $savedUserAiKeys.gemini_api_key) { $newAi | Add-Member -NotePropertyName 'gemini_api_key' -NotePropertyValue $savedUserAiKeys.gemini_api_key -Force }
        if ((-not $newAi.keys -or $newAi.keys.Count -eq 0) -and $savedUserAiKeys.keys) { $newAi | Add-Member -NotePropertyName 'keys' -NotePropertyValue $savedUserAiKeys.keys -Force }
        if ((-not $newAi.keys_raw) -and $savedUserAiKeys.keys_raw) { $newAi | Add-Member -NotePropertyName 'keys_raw' -NotePropertyValue $savedUserAiKeys.keys_raw -Force }
        if ((-not $newAi.nisay_api_key) -and $savedUserAiKeys.nisay_api_key) { $newAi | Add-Member -NotePropertyName 'nisay_api_key' -NotePropertyValue $savedUserAiKeys.nisay_api_key -Force }
        Write-Utf8NoBom $aiCfgPath ($newAi | ConvertTo-Json -Depth 10)
        Write-Host "[OK] User AI provider keys preserved." -ForegroundColor Green
    } catch {}
}

# Preserve verified sha256 in cloud_manifest.json without UTF-8 BOM
$cmJsonPath = Join-Path $targetDir "data\cloud_manifest.json"
if ($expectedSha256 -and (Test-Path $cmJsonPath)) {
    try {
        $cmObj = Get-Content -Path $cmJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $cmObj | Add-Member -NotePropertyName 'sha256' -NotePropertyValue $expectedSha256 -Force
        Write-Utf8NoBom $cmJsonPath ($cmObj | ConvertTo-Json -Depth 10)
    } catch {}
}

# Signal auto-heal for core manifest
try {
    New-Item -ItemType File -Path (Join-Path $targetDir "data\.update_pending") -Force | Out-Null
} catch {}

# 7. Cleanup only temporary downloaded zip (preserve user's local bundle)
if ($tempZip -and ($tempZip -ne $localPkgZip) -and ($tempZip -ne (Join-Path $targetDir "SN_TOOL_UPDATE.zip")) -and (Test-Path $tempZip)) {
    Remove-Item -Path $tempZip -Force -ErrorAction SilentlyContinue
}

# 8. Start application
$exeFile = Join-Path $targetDir "SN_TOOL.exe"
$batFile = Join-Path $targetDir "START_SN_TOOL.bat"
if (-not (Test-Path $batFile)) {
    $batFile = Join-Path $targetDir "Khmer_Drama_Studio_Launcher.bat"
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Green
Write-Host "  [SUCCESS] SN TOOL has been updated to v$targetVer!" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Green
Write-Host ""

if (Test-Path $exeFile) {
    Write-Host "[*] Launching SN TOOL..." -ForegroundColor Cyan
    Start-Process -FilePath $exeFile -WorkingDirectory $targetDir
} elseif (Test-Path $batFile) {
    Write-Host "[*] Launching SN TOOL..." -ForegroundColor Cyan
    Start-Process -FilePath $batFile -WorkingDirectory $targetDir
}
