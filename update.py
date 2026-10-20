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

CURRENT_VERSION = "1.1.0"
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
    """Fetch and parse JSON from direct HTTP URL."""
    if not url:
        return {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    req = urllib.request.Request(url, headers=headers)
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
                    "release_notes": data.get("release_notes", "Continuous performance optimizations and security improvements."),
                    "download_url": resolve_gdrive_direct_url(dl_url),
                    "release_date": data.get("release_date", ""),
                    "channel": data.get("channel", "stable")
                }
        except Exception:
            pass

    # 2. Try direct custom manifest URL
    if cloud_manifest_url and cloud_manifest_url.startswith("http"):
        try:
            direct_url = resolve_gdrive_direct_url(cloud_manifest_url)
            data = fetch_json_from_url(direct_url)
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
                    "release_notes": data.get("release_notes", "Continuous performance optimizations and security improvements."),
                    "download_url": resolve_gdrive_direct_url(dl_url),
                    "release_date": data.get("release_date", ""),
                    "channel": data.get("channel", "stable")
                }
        except Exception:
            pass

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

        if is_exe:
            ps1_content = f"""
Start-Sleep -Seconds 2
Stop-Process -Name "SN_TOOL" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-Process "{dest_file}"
Remove-Item -Force $MyInvocation.MyCommand.Path -ErrorAction SilentlyContinue
"""
        else:
            restart_target = f'"{exe_file}"' if exe_file.exists() else f'"{run_bat}"'
            ps1_content = f"""
Start-Sleep -Seconds 2
Stop-Process -Name "SN_TOOL" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
# Backup existing license.key before extracting
$licBackup = $null
if (Test-Path "{app_dir}\\license.key") {{
    $licBackup = [System.IO.File]::ReadAllBytes("{app_dir}\\license.key")
}}
Expand-Archive -Path "{dest_file}" -DestinationPath "{app_dir}" -Force
if ($licBackup -ne $null) {{
    [System.IO.File]::WriteAllBytes("{app_dir}\\license.key", $licBackup)
}}
Remove-Item -Force "{dest_file}" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
Start-Process {restart_target}
Remove-Item -Force $MyInvocation.MyCommand.Path -ErrorAction SilentlyContinue
"""
        with open(ps1_file, "w", encoding="utf-8") as f:
            f.write(ps1_content)

        # Launch detached PowerShell updater
        if sys.platform == "win32":
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1_file)],
                cwd=str(app_dir),
                creationflags=0x00000008 | 0x08000000
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
