"""
SN_TOOL - Multi-Cloud Resilient Auto Update Engine & Version Manager
Supports 1-Click Version Updates via Google Drive, Custom Cloud Mirrors, and Direct CDNs.
100% resilient against GitHub account suspensions.
"""

import os
import sys
import json
import time
import re
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Tuple

CURRENT_VERSION = "2.0.7"
APP_NAME = "SN TOOL"
DEFAULT_UPDATE_ZIP_URL = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip"
DEFAULT_VERSION_JSON_URL = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/version.json"

_UPDATE_PROGRESS_LOCK = threading.Lock()
_UPDATE_PROGRESS = {
    "status": "idle",
    "percent": 0,
    "downloaded_mb": 0.0,
    "total_mb": 44.2,
    "message": "Idle",
    "error": None
}

def get_update_progress() -> Dict[str, Any]:
    with _UPDATE_PROGRESS_LOCK:
        return dict(_UPDATE_PROGRESS)

def set_update_progress(status: str, percent: int, msg: str = "", downloaded_mb: float = 0.0, total_mb: float = 44.2, error: str = None):
    with _UPDATE_PROGRESS_LOCK:
        _UPDATE_PROGRESS["status"] = status
        _UPDATE_PROGRESS["percent"] = percent
        _UPDATE_PROGRESS["message"] = msg
        _UPDATE_PROGRESS["downloaded_mb"] = downloaded_mb
        _UPDATE_PROGRESS["total_mb"] = total_mb
        _UPDATE_PROGRESS["error"] = error

def parse_version_tuple(ver_str: str) -> Tuple[int, ...]:
    """Parse '1.0.7' into (1, 0, 7) tuple for accurate comparison."""
    try:
        clean = str(ver_str).strip().lstrip("vV")
        parts = [int(p) for p in clean.split(".") if p.isdigit()]
        return tuple(parts) if parts else (0, 0, 0)
    except Exception:
        return (0, 0, 0)

def is_newer_version(remote_ver: str, local_ver: str = CURRENT_VERSION) -> bool:
    """Return True if remote_ver is strictly newer than local_ver."""
    return parse_version_tuple(remote_ver) > parse_version_tuple(local_ver)

def get_local_version() -> str:
    """Read local version from version.json if present, else fallback to CURRENT_VERSION."""
    candidates = [
        Path(__file__).resolve().parent / "version.json",
        Path.cwd() / "version.json",
    ]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).parent / "version.json")
    for local_vjson in candidates:
        try:
            if local_vjson.exists():
                with open(local_vjson, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ver = data.get("version")
                    if ver:
                        return str(ver).strip()
        except Exception:
            pass
    return CURRENT_VERSION

def get_update_config() -> Dict[str, Any]:
    """Load cloud update configuration from data/update_config.json."""
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / "data" / "update_config.json",
        base_dir / "update_config.json",
        Path.cwd() / "data" / "update_config.json",
        Path.cwd() / "update_config.json",
    ]
    if getattr(sys, "frozen", False):
        candidates.insert(0, Path(sys.executable).parent / "data" / "update_config.json")
        candidates.insert(1, Path(sys.executable).parent / "update_config.json")

    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}

def resolve_gdrive_direct_url(url_or_id: str) -> str:
    """Convert any Google Drive URL (file link, sharing link, ID) to a high-speed direct download link."""
    if not url_or_id:
        return ""
    clean = str(url_or_id).strip()
    file_id = ""
    m = re.search(r"/file/d/([a-zA-Z0-9_-]{20,})", clean)
    if m:
        file_id = m.group(1)
    if not file_id:
        m = re.search(r"[?&]id=([a-zA-Z0-9_-]{20,})", clean)
        if m:
            file_id = m.group(1)
    if not file_id and "/" not in clean and len(clean) >= 20:
        file_id = clean

    if file_id:
        return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    return clean

def fetch_json_from_url(url: str, timeout: int = 6) -> Dict[str, Any]:
    """Fetch and parse JSON from direct HTTP URL with zero-caching assurance."""
    if not url:
        return {}
    target_url = url
    if "githubusercontent.com" in target_url or "github.com" in target_url:
        sep = "&" if "?" in target_url else "?"
        target_url = f"{target_url}{sep}_cb={int(time.time())}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache"
    }
    req = urllib.request.Request(target_url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status == 200:
            raw = resp.read().decode("utf-8", errors="ignore")
            return json.loads(raw)
    return {}

def _build_update_payload(data: Dict[str, Any], local_ver: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize update manifest data into a uniform response payload."""
    remote_ver = str(data["version"]).strip()
    has_up = is_newer_version(remote_ver, local_ver)
    dl_url = data.get("download_url") or ""
    if not dl_url or "/folders/" in dl_url:
        dl_url = cfg.get("direct_download_url") or cfg.get("google_drive_zip_id") or dl_url or DEFAULT_UPDATE_ZIP_URL
    return {
        "success": True,
        "has_update": has_up,
        "current_version": local_ver,
        "latest_version": remote_ver,
        "title": data.get("title", f"SN TOOL v{remote_ver}"),
        "subtitle": data.get("subtitle") or data.get("description", ""),
        "release_notes": data.get("release_notes", "Continuous performance optimizations and security improvements."),
        "download_url": resolve_gdrive_direct_url(dl_url),
        "release_date": data.get("release_date", ""),
        "channel": data.get("channel", "stable"),
        "sha256": str(data.get("sha256") or "").strip().lower(),
        "size_bytes": int(data.get("size_bytes") or 0),
    }


def check_for_updates(github_token: str = None) -> Dict[str, Any]:
    """
    Check for newer versions of SN_TOOL across cloud mirrors:
    1. Google Drive / Custom Cloud storage (via data/update_config.json)
    2. Remote custom manifest / remote version.json fallback
    3. Local manifest fallback
    """
    local_ver = get_local_version()
    cfg = get_update_config()

    # 1. Try Google Drive or Custom Cloud Manifest
    cloud_manifest_url = cfg.get("custom_manifest_url") or cfg.get("google_drive_folder_url")
    version_file_id = cfg.get("google_drive_version_id") or cfg.get("version_file_id")

    if version_file_id:
        direct_vjson_url = resolve_gdrive_direct_url(version_file_id)
        try:
            data = fetch_json_from_url(direct_vjson_url)
            if data and "version" in data:
                return _build_update_payload(data, local_ver, cfg)
        except Exception:
            pass

    # 2. Try direct custom manifest URL & remote version.json (pick newest if both respond)
    remote_candidates = []
    if cloud_manifest_url and cloud_manifest_url.startswith("http") and "/folders/" not in cloud_manifest_url:
        try:
            direct_url = resolve_gdrive_direct_url(cloud_manifest_url)
            d1 = fetch_json_from_url(direct_url)
            if d1 and "version" in d1:
                remote_candidates.append(d1)
        except Exception:
            pass

    try:
        d2 = fetch_json_from_url(DEFAULT_VERSION_JSON_URL)
        if d2 and "version" in d2:
            remote_candidates.append(d2)
    except Exception:
        pass

    data = None
    cloud_not_published = False
    cloud_version = ""
    if remote_candidates:
        remote_candidates.sort(key=lambda item: parse_version_tuple(item.get("version", "0.0.0")), reverse=True)
        newest_remote = remote_candidates[0]
        cloud_version = str(newest_remote.get("version") or "").strip()
        if parse_version_tuple(cloud_version) >= parse_version_tuple(local_ver):
            data = newest_remote
        else:
            cloud_not_published = True

    if not data or "version" not in data:
        base_dir = Path(__file__).resolve().parent
        local_cloud_m = base_dir / "data" / "cloud_manifest.json"
        if local_cloud_m.exists():
            try:
                with open(local_cloud_m, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = None

    if data and "version" in data:
        payload = _build_update_payload(data, local_ver, cfg)
        if cloud_not_published:
            payload["cloud_not_published"] = True
            payload["cloud_version"] = cloud_version
        return payload

    # 3. Default Up-to-date response (graceful offline / standalone mode)
    return {
        "success": True,
        "has_update": False,
        "current_version": local_ver,
        "latest_version": local_ver,
        "title": "SN TOOL",
        "release_notes": "You are currently running the official release of SN TOOL.",
        "download_url": DEFAULT_UPDATE_ZIP_URL,
        "channel": "stable",
        "sha256": "",
        "size_bytes": 0,
    }

def apply_git_pull_update(app_dir: Path) -> Dict[str, Any]:
    """Execute git pull for developer installations."""
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=str(app_dir),
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=0x08000000 if sys.platform == "win32" else 0
        )
        if result.returncode == 0:
            return {
                "success": True,
                "message": "Git pull ជោគជ័យ! កម្មវិធីត្រូវបាន update ឡើងទៅ Version ថ្មីបំផុត។",
                "output": result.stdout
            }
        else:
            return {
                "success": False,
                "error": f"Git pull error: {result.stderr or result.stdout}"
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

def apply_zip_download_update(download_url: str, app_dir: Path, expected_sha256: str = "") -> Dict[str, Any]:
    """
    Download cloud update patch (SN_TOOL_UPDATE.zip or Standalone Setup) with SHA-256 verification,
    user credential preservation (license.key & AI keys), zip-slip protection, and detached restart.
    """
    if not download_url:
        cfg = get_update_config()
        download_url = cfg.get("direct_download_url") or cfg.get("google_drive_zip_id") or DEFAULT_UPDATE_ZIP_URL
    if not download_url:
        set_update_progress("error", 0, "No download URL provided for update.", error="No download URL provided")
        return {"success": False, "error": "No download URL provided for update."}

    resolved_url = resolve_gdrive_direct_url(download_url)
    if "githubusercontent.com" in resolved_url or "github.com" in resolved_url:
        sep = "&" if "?" in resolved_url else "?"
        resolved_url = f"{resolved_url}{sep}_cb={int(time.time())}"
    cache_dir = app_dir / "data" / "cache" / "update"
    cache_dir.mkdir(parents=True, exist_ok=True)
    is_exe = resolved_url.lower().split("?")[0].endswith(".exe")
    dest_file = cache_dir / ("SN_TOOL_Setup.exe" if is_exe else "update_package.zip")
    ota_flag_file = app_dir / "data" / ".ota_installing"

    try:
        sha_arg = expected_sha256.strip().lower() if expected_sha256 else ""
        used_local_verified = False
        local_pkg = app_dir / "SN_TOOL_UPDATE.zip"
        tot_mb = 44.2

        # If Cloud CDN still hosts an older release than local version, check verified local v2.0.7 package first
        if not is_exe and sha_arg and local_pkg.exists():
            try:
                chk_meta = check_for_updates()
                if chk_meta.get("cloud_not_published"):
                    import license_engine
                    loc_ok, _ = license_engine.verify_update_package_integrity(local_pkg, expected_sha256=sha_arg)
                    if loc_ok:
                        import shutil
                        tot_mb = round(local_pkg.stat().st_size / (1024 * 1024), 1)
                        set_update_progress("verifying", 86, f"Verified local v{get_local_version()} package ({tot_mb} MB)...", tot_mb, tot_mb, error=None)
                        shutil.copy2(local_pkg, dest_file)
                        used_local_verified = True
            except Exception:
                used_local_verified = False

        if not used_local_verified:
            set_update_progress("downloading", 5, "Connecting to Cloud CDN server...", 0.0, 44.2, error=None)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache"
            }
            req = urllib.request.Request(resolved_url, headers=headers)
            with urllib.request.urlopen(req, timeout=300) as resp:
                content_len_hdr = resp.headers.get("Content-Length")
                total_size = int(content_len_hdr) if content_len_hdr and content_len_hdr.isdigit() else 46324069
                tot_mb = round(total_size / (1024 * 1024), 1)
                downloaded = 0
                last_report_t = 0.0

                with open(dest_file, "wb") as out_f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)
                        now_t = time.time()
                        if now_t - last_report_t >= 0.25 or downloaded >= total_size:
                            last_report_t = now_t
                            cur_mb = round(downloaded / (1024 * 1024), 1)
                            pct = min(82, max(5, int((downloaded / max(total_size, 1)) * 82)))
                            set_update_progress(
                                "downloading",
                                pct,
                                f"Downloading update: {cur_mb} MB / {tot_mb} MB ({pct}%)...",
                                cur_mb,
                                tot_mb
                            )

            if not is_exe and dest_file.stat().st_size < 1_000_000:
                err_msg = f"Downloaded update archive too small ({dest_file.stat().st_size} bytes); possible network/CDN error."
                dest_file.unlink(missing_ok=True)
                set_update_progress("error", 0, err_msg, error=err_msg)
                return {"success": False, "error": err_msg}

        # 🛡️ SYSTEM 13: Secure Update Package Integrity Verification (ZIP structure + optional SHA-256)
        set_update_progress("verifying", 86, "Verifying update package integrity (86%)...", tot_mb, tot_mb)
        try:
            import license_engine
            upg_ok, upg_msg = license_engine.verify_update_package_integrity(dest_file, expected_sha256=sha_arg or None)
            if not upg_ok:
                dest_file.unlink(missing_ok=True)
                err_detail = f"Security check failed on downloaded update: {upg_msg}"
                try:
                    chk_meta = check_for_updates()
                    if chk_meta.get("cloud_not_published") and "SHA-256 checksum mismatch" in upg_msg:
                        c_ver = chk_meta.get("cloud_version") or "older"
                        l_ver = get_local_version()
                        err_detail = (
                            f"Cloud CDN (skdtool.github) still serves v{c_ver} instead of v{l_ver}. "
                            f"Please push dist/READY_FOR_GOOGLE_DRIVE (v{l_ver}) to GitHub/CDN first ({upg_msg})."
                        )
                except Exception:
                    pass
                set_update_progress("error", 0, err_detail, error=err_detail)
                return {"success": False, "error": err_detail}
        except ImportError:
            pass

        set_update_progress("extracting", 92, "Preparing update files and installer (92%)...", tot_mb, tot_mb)

        # Create OTA installing lock flag so /api/update/ping waits until extraction & restart are complete
        ota_flag_file.parent.mkdir(parents=True, exist_ok=True)
        ota_flag_file.write_text(str(time.time()), encoding="utf-8")

        # Create detached PowerShell updater script
        ps1_file = app_dir / "apply_update.ps1"
        exe_file = app_dir / "SN_TOOL.exe"
        log_file = app_dir / "data" / "update_install.log"
        rollback_dir = app_dir / "data" / "cache" / "update" / "rollback"

        if is_exe:
            ps1_content = f"""
Start-Sleep -Seconds 2
$targetDirFull = [System.IO.Path]::GetFullPath("{app_dir}").TrimEnd('\\')
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}}
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {{
    ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($targetDirFull, [System.StringComparison]::OrdinalIgnoreCase)) -or
    ($_.CommandLine -and $_.CommandLine -like "*$targetDirFull*")
}} | ForEach-Object {{
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}}
Start-Sleep -Seconds 1
Remove-Item -Force "{ota_flag_file}" -ErrorAction SilentlyContinue
Start-Process "{dest_file}"
Remove-Item -Force $MyInvocation.MyCommand.Path -ErrorAction SilentlyContinue
"""
        else:
            ps1_content = f"""
$logPath = "{log_file}"
$appDir = "{app_dir}"
$destZip = "{dest_file}"
$otaFlag = "{ota_flag_file}"
$rollbackDir = "{rollback_dir}"
$appDirFull = [System.IO.Path]::GetFullPath($appDir).TrimEnd('\\') + '\\'

function Log-Update($msg) {{
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    try {{ Add-Content -Path $logPath -Value $line -Encoding UTF8 }} catch {{}}
}}

function Stop-AppProcesses {{
    try {{
        Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }}
    }} catch {{}}
    try {{
        netstat -ano | Select-String ":8000\\s+.*LISTENING\\s+(\\d+)" | ForEach-Object {{
            if ($_ -match "LISTENING\\s+(\\d+)") {{
                Stop-Process -Id $matches[1] -Force -ErrorAction SilentlyContinue
            }}
        }}
    }} catch {{}}
    try {{
        $targetNoSlash = $appDirFull.TrimEnd('\\')
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {{
            $_.Name -match '^(SN_TOOL\\.exe|pythonw?\\.exe)$' -and (
                ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($targetNoSlash, [System.StringComparison]::OrdinalIgnoreCase)) -or
                ($_.CommandLine -and $_.CommandLine -like "*$targetNoSlash*")
            )
        }} | ForEach-Object {{
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }}
    }} catch {{}}
    Stop-Process -Name "SN_TOOL" -Force -ErrorAction SilentlyContinue
}}

Log-Update "Starting in-app OTA update installation..."

Start-Sleep -Seconds 2

# 1. Terminate active SN_TOOL processes holding port 8000 or running inside appDir
Stop-AppProcesses
Start-Sleep -Seconds 2

# 2. Backup existing license.key, user AI config, and rollback snapshot of core scripts
$licBackup = $null
$licPath = Join-Path $appDir "license.key"
if (Test-Path $licPath) {{
    try {{
        $licBackup = [System.IO.File]::ReadAllBytes($licPath)
        Log-Update "License key backed up successfully."
    }} catch {{
        Log-Update "Warning backing up license key: $_"
    }}
}}

$aiCfgPath = Join-Path $appDir "data\\ai_provider_config.json"
$savedUserAiKeys = $null
if (Test-Path $aiCfgPath) {{
    try {{
        $oldAi = Get-Content -Path $aiCfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($oldAi.gemini_api_key -or ($oldAi.keys -and $oldAi.keys.Count -gt 0) -or $oldAi.keys_raw) {{
            $savedUserAiKeys = @{{
                gemini_api_key = $oldAi.gemini_api_key
                keys = $oldAi.keys
                keys_raw = $oldAi.keys_raw
                nisay_api_key = $oldAi.nisay_api_key
            }}
            Log-Update "Backed up user AI provider keys."
        }}
    }} catch {{}}
}}

try {{
    if (Test-Path $rollbackDir) {{ Remove-Item -Path $rollbackDir -Recurse -Force -ErrorAction SilentlyContinue }}
    New-Item -ItemType Directory -Path $rollbackDir -Force | Out-Null
    Get-ChildItem -Path $appDir -Filter "*.py" -ErrorAction SilentlyContinue | ForEach-Object {{
        Copy-Item -Path $_.FullName -Destination (Join-Path $rollbackDir $_.Name) -Force -ErrorAction SilentlyContinue
    }}
    if (Test-Path (Join-Path $appDir "version.json")) {{
        Copy-Item -Path (Join-Path $appDir "version.json") -Destination (Join-Path $rollbackDir "version.json") -Force -ErrorAction SilentlyContinue
    }}
}} catch {{}}

# 3. Resilient extraction with Zip-Slip path validation
$extracted = $false
Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue

for ($attempt = 1; $attempt -le 8; $attempt++) {{
    try {{
        Log-Update "Extraction attempt $attempt..."
        if ([System.IO.Compression.ZipFile]) {{
            $archive = $null
            try {{
                $archive = [System.IO.Compression.ZipFile]::OpenRead($destZip)
                foreach ($entry in $archive.Entries) {{
                    $targetPath = [System.IO.Path]::GetFullPath([System.IO.Path]::Combine($appDir, $entry.FullName))
                    if (-not $targetPath.StartsWith($appDirFull, [System.StringComparison]::OrdinalIgnoreCase)) {{
                        throw "Unsafe archive path blocked: $($entry.FullName)"
                    }}
                    $targetParent = [System.IO.Path]::GetDirectoryName($targetPath)
                    if (-not [System.IO.Directory]::Exists($targetParent)) {{
                        [System.IO.Directory]::CreateDirectory($targetParent) | Out-Null
                    }}
                    if ($entry.Name -ne "") {{
                        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $targetPath, $true)
                    }}
                }}
            }} finally {{
                if ($archive) {{ $archive.Dispose() }}
            }}
            $extracted = $true
            Log-Update "Extraction via .NET ZipFile succeeded!"
            break
        }} else {{
            Expand-Archive -Path $destZip -DestinationPath $appDir -Force -ErrorAction Stop
            $extracted = $true
            Log-Update "Extraction via Expand-Archive succeeded!"
            break
        }}
    }} catch {{
        Log-Update "Extraction attempt $attempt notice: $_"
        Stop-AppProcesses
        Start-Sleep -Seconds 2
    }}
}}

if (-not $extracted -and (Test-Path $rollbackDir)) {{
    Log-Update "Extraction failed across all retries; restoring previous files from rollback..."
    try {{
        Get-ChildItem -Path $rollbackDir -ErrorAction SilentlyContinue | ForEach-Object {{
            Copy-Item -Path $_.FullName -Destination (Join-Path $appDir $_.Name) -Force -ErrorAction SilentlyContinue
        }}
    }} catch {{}}
}}

# 4. Restore license.key & user API keys
if ($licBackup -ne $null) {{
    try {{
        [System.IO.File]::WriteAllBytes($licPath, $licBackup)
        Log-Update "License key restored successfully."
    }} catch {{
        Log-Update "Error restoring license key: $_"
    }}
}}

if ($savedUserAiKeys -ne $null -and (Test-Path $aiCfgPath)) {{
    try {{
        $newAi = Get-Content -Path $aiCfgPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ((-not $newAi.gemini_api_key) -and $savedUserAiKeys.gemini_api_key) {{ $newAi | Add-Member -NotePropertyName 'gemini_api_key' -NotePropertyValue $savedUserAiKeys.gemini_api_key -Force }}
        if ((-not $newAi.keys -or $newAi.keys.Count -eq 0) -and $savedUserAiKeys.keys) {{ $newAi | Add-Member -NotePropertyName 'keys' -NotePropertyValue $savedUserAiKeys.keys -Force }}
        if ((-not $newAi.keys_raw) -and $savedUserAiKeys.keys_raw) {{ $newAi | Add-Member -NotePropertyName 'keys_raw' -NotePropertyValue $savedUserAiKeys.keys_raw -Force }}
        if ((-not $newAi.nisay_api_key) -and $savedUserAiKeys.nisay_api_key) {{ $newAi | Add-Member -NotePropertyName 'nisay_api_key' -NotePropertyValue $savedUserAiKeys.nisay_api_key -Force }}
        [System.IO.File]::WriteAllText($aiCfgPath, ($newAi | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding($false)))
        Log-Update "Preserved user AI provider keys."
    }} catch {{
        Log-Update "Notice restoring user AI keys: $_"
    }}
}}

# Signal auto-heal & re-sign for core manifest
try {{
    New-Item -ItemType File -Path (Join-Path $appDir "data\\.update_pending") -Force | Out-Null
    Log-Update "Created update_pending signal for automatic manifest re-signing."
}} catch {{}}

# Preserve exact verified sha256 in cloud_manifest.json so extracted ZIP never clears/breaks local hash
$verifiedSha = "{sha_arg}"
$cmJsonPath = Join-Path $appDir "data\\cloud_manifest.json"
if ($verifiedSha -and (Test-Path $cmJsonPath)) {{
    try {{
        $cmObj = Get-Content -Path $cmJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $cmObj | Add-Member -NotePropertyName 'sha256' -NotePropertyValue $verifiedSha -Force
        [System.IO.File]::WriteAllText($cmJsonPath, ($cmObj | ConvertTo-Json -Depth 10), (New-Object System.Text.UTF8Encoding($false)))
    }} catch {{}}
}}

# 5. Cleanup temp download package, rollback cache, and OTA lock flag
Remove-Item -Force $destZip -ErrorAction SilentlyContinue
Remove-Item -Path $rollbackDir -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Force $otaFlag -ErrorAction SilentlyContinue

# 6. Determine best restart binary or launcher
$targetExe = "{exe_file}"
if (-not (Test-Path $targetExe)) {{
    if (Test-Path (Join-Path $appDir "START_SN_TOOL.bat")) {{
        $targetExe = Join-Path $appDir "START_SN_TOOL.bat"
    }} elseif (Test-Path (Join-Path $appDir "Khmer_Drama_Studio_Launcher.bat")) {{
        $targetExe = Join-Path $appDir "Khmer_Drama_Studio_Launcher.bat"
    }} elseif (Test-Path (Join-Path $appDir "SN_TOOL.bat")) {{
        $targetExe = Join-Path $appDir "SN_TOOL.bat"
    }}
}}

Log-Update "Relaunching application via: $targetExe"
Start-Sleep -Seconds 1
if (Test-Path $targetExe) {{
    Start-Process -FilePath $targetExe -WorkingDirectory $appDir
}}

Log-Update "Update finished successfully."
Remove-Item -Force $MyInvocation.MyCommand.Path -ErrorAction SilentlyContinue
"""
        with open(ps1_file, "w", encoding="utf-8") as f:
            f.write(ps1_content)

        # Launch detached PowerShell updater
        if sys.platform == "win32":
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1_file)],
                cwd=str(app_dir),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000
            )

        return {
            "success": True,
            "message": "ការទាញយកជោគជ័យ! កម្មវិធីកំពុងដំឡើង និង Restart ឡើង Version ថ្មីក្នុងរយៈពេល 2 វិនាទី..."
        }
    except Exception as e:
        ota_flag_file.unlink(missing_ok=True)
        set_update_progress("error", 0, f"Update failed: {e}", error=str(e))
        return {"success": False, "error": str(e)}

def get_version_info() -> Dict[str, Any]:
    return {
        "version": get_local_version(),
        "app_name": APP_NAME,
        "author": "SN Team Cambodia",
        "update_engine": "Multi-Cloud Resilient Updater (Google Drive / CDN)"
    }

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    info = get_version_info()
    print("=" * 60)
    print(f" [*] {info['app_name']} - Version {info['version']}")
    print(f" [*] Update Engine: {info['update_engine']}")
    print("=" * 60)
    res = check_for_updates()
    print(f" Update Available: {res.get('has_update')}")
    print(f" Latest Version: {res.get('latest_version')}")
    print("=" * 60)
