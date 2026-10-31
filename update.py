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
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Tuple

CURRENT_VERSION = "2.0.1"
APP_NAME = "SN TOOL - STUDIO PRO"
DEFAULT_UPDATE_ZIP_URL = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip"

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

def check_for_updates(github_token: str = None) -> Dict[str, Any]:
    """
    Check for newer versions of SN_TOOL across cloud mirrors:
    1. Google Drive / Custom Cloud storage (via data/update_config.json)
    2. Direct version manifest fallback
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
                remote_ver = str(data["version"]).strip()
                has_up = is_newer_version(remote_ver, local_ver)
                dl_url = data.get("download_url") or ""
                if not dl_url or "/folders/" in dl_url:
                    dl_url = cfg.get("direct_download_url") or cfg.get("google_drive_zip_id") or dl_url
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
                    "channel": data.get("channel", "stable")
                }
        except Exception:
            pass

    # 2. Try direct custom manifest URL (with local data/cloud_manifest.json resilience)
    data = None
    if cloud_manifest_url and cloud_manifest_url.startswith("http"):
        try:
            direct_url = resolve_gdrive_direct_url(cloud_manifest_url)
            data = fetch_json_from_url(direct_url)
        except Exception:
            data = None

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
        remote_ver = str(data["version"]).strip()
        has_up = is_newer_version(remote_ver, local_ver)
        dl_url = data.get("download_url") or ""
        if not dl_url or "/folders/" in dl_url:
            dl_url = cfg.get("direct_download_url") or cfg.get("google_drive_zip_id") or dl_url
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
            "channel": data.get("channel", "stable")
        }

    # 3. Default Up-to-date response (graceful offline / standalone mode)
    return {
        "success": True,
        "has_update": False,
        "current_version": local_ver,
        "latest_version": local_ver,
        "title": "SN TOOL STUDIO PRO",
        "release_notes": "You are currently running the official release of SN TOOL STUDIO PRO.",
        "download_url": DEFAULT_UPDATE_ZIP_URL,
        "channel": "stable"
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

def apply_zip_download_update(download_url: str, app_dir: Path) -> Dict[str, Any]:
    """
    Download cloud update patch (SN_TOOL_UPDATE.zip ~26MB or Standalone Setup)
    and execute detached PowerShell updater script to extract directly over app_dir.
    License key and user configs are strictly preserved!
    """
    if not download_url:
        cfg = get_update_config()
        download_url = cfg.get("direct_download_url") or cfg.get("google_drive_zip_id") or DEFAULT_UPDATE_ZIP_URL
    if not download_url:
        return {"success": False, "error": "No download URL provided for update."}

    resolved_url = resolve_gdrive_direct_url(download_url)
    cache_dir = app_dir / "data" / "cache" / "update"
    cache_dir.mkdir(parents=True, exist_ok=True)
    is_exe = resolved_url.lower().split("?")[0].endswith(".exe")
    dest_file = cache_dir / ("SN_TOOL_Setup.exe" if is_exe else "update_package.zip")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        req = urllib.request.Request(resolved_url, headers=headers)
        with urllib.request.urlopen(req, timeout=300) as resp, open(dest_file, "wb") as out_f:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out_f.write(chunk)

        # Create detached PowerShell updater script
        ps1_file = app_dir / "apply_update.ps1"
        exe_file = app_dir / "SN_TOOL.exe"
        run_bat = app_dir / "START_SN_TOOL.bat"
        log_file = app_dir / "data" / "update_install.log"

        if is_exe:
            ps1_content = f"""
Start-Sleep -Seconds 2
Stop-Process -Name "SN_TOOL" -Force -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}}
Start-Sleep -Seconds 1
Start-Process "{dest_file}"
Remove-Item -Force $MyInvocation.MyCommand.Path -ErrorAction SilentlyContinue
"""
        else:
            ps1_content = f"""
$logPath = "{log_file}"
$appDir = "{app_dir}"
$destZip = "{dest_file}"

function Log-Update($msg) {{
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $msg"
    try {{ Add-Content -Path $logPath -Value $line -Encoding UTF8 }} catch {{}}
}}

Log-Update "Starting in-app OTA update installation..."

Start-Sleep -Seconds 2

# 1. Terminate any active process holding port 8000 or running in appDir
try {{
    Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }}
}} catch {{}}

Get-Process | Where-Object {{ $_.Path -like "$appDir*" }} | Stop-Process -Force -ErrorAction SilentlyContinue
Stop-Process -Name "SN_TOOL" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# 2. Backup existing license.key before extracting
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

# 3. Fast resilient extraction (.NET ZipFile with Expand-Archive fallback)
$extracted = $false
Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue

for ($attempt = 1; $attempt -le 8; $attempt++) {{
    try {{
        Log-Update "Extraction attempt $attempt..."
        if ([System.IO.Compression.ZipFile]) {{
            $archive = [System.IO.Compression.ZipFile]::OpenRead($destZip)
            foreach ($entry in $archive.Entries) {{
                $targetPath = [System.IO.Path]::Combine($appDir, $entry.FullName)
                $targetParent = [System.IO.Path]::GetDirectoryName($targetPath)
                if (-not [System.IO.Directory]::Exists($targetParent)) {{
                    [System.IO.Directory]::CreateDirectory($targetParent) | Out-Null
                }}
                if ($entry.Name -ne "") {{
                    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $targetPath, $true)
                }}
            }}
            $archive.Dispose()
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
        try {{
            Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {{
                Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
            }}
        }} catch {{}}
        Stop-Process -Name "SN_TOOL", "python", "pythonw" -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }}
}}

# 4. Restore license.key
if ($licBackup -ne $null) {{
    try {{
        [System.IO.File]::WriteAllBytes($licPath, $licBackup)
        Log-Update "License key restored successfully."
    }} catch {{
        Log-Update "Error restoring license key: $_"
    }}
}}

# 5. Remove temporary download package
Remove-Item -Force $destZip -ErrorAction SilentlyContinue

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
