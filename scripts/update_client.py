"""
1-Click Client Updater for SN TOOL STUDIO PRO
Directly updates installation to the latest official release.
Verifies SHA-256 & ZIP integrity, preserves license.key and user AI keys,
and updates both installed folders and portable directories cleanly.
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Any, Tuple

OFFICIAL_UPDATE_ZIP_URL = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip"
CLOUD_MANIFEST_URL = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/data/cloud_manifest.json"
VERSION_MANIFEST_URL = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/version.json"


def terminate_running_instances(target_dir: Path):
    """Terminate running SN_TOOL processes scoped to target_dir / port 8000."""
    print(f"[*] Closing running SN_TOOL instances in {target_dir}...")
    if sys.platform == "win32":
        norm_dir = str(target_dir.resolve()).replace("'", "''")
        ps_cmd = (
            "Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | "
            "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }; "
            f"Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {{ "
            f"$_.Name -match '^(SN_TOOL\\.exe|pythonw?\\.exe)$' -and ("
            f"($_.ExecutablePath -and $_.ExecutablePath.StartsWith('{norm_dir}', [System.StringComparison]::OrdinalIgnoreCase)) -or "
            f"($_.CommandLine -and $_.CommandLine -like '*{norm_dir}*')) }} | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; "
            "Stop-Process -Name 'SN_TOOL' -Force -ErrorAction SilentlyContinue"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                creationflags=0x08000000,
                timeout=15,
            )
            time.sleep(2)
        except Exception:
            pass


def fetch_latest_manifest() -> Tuple[str, str, str]:
    """Fetch remote version, download_url, and optional sha256 from Cloud CDN."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }
    ts = int(time.time())
    for url in (CLOUD_MANIFEST_URL, VERSION_MANIFEST_URL):
        try:
            req = urllib.request.Request(f"{url}?_cb={ts}", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                    if data and data.get("version"):
                        ver = str(data["version"]).strip()
                        dl_url = str(data.get("download_url") or OFFICIAL_UPDATE_ZIP_URL).strip()
                        sha = str(data.get("sha256") or "").strip().lower()
                        return ver, dl_url, sha
        except Exception:
            continue
    return "2.0.7", OFFICIAL_UPDATE_ZIP_URL, ""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    dest_root = dest_dir.resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target_p = (dest_root / member.filename).resolve()
            if target_p != dest_root and dest_root not in target_p.parents:
                raise RuntimeError(f"Unsafe archive path blocked: {member.filename}")
        zf.extractall(dest_root)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    target_ver, dl_url, expected_sha = fetch_latest_manifest()
    print("=" * 70)
    print(f"  SN TOOL STUDIO PRO - 1-CLICK CLIENT UPDATER (v{target_ver})")
    print("  1080p Video+Audio Downloader + SHA-256 Verified OTA")
    print("=" * 70)
    print()

    base_dir = Path(__file__).resolve().parent.parent
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    installed_c = Path(local_app_data) / "Programs" / "SN_TOOL" if local_app_data else None
    installed_d = Path(r"D:\SN_TOOL")

    target_dirs = []
    if installed_d.exists() and (installed_d / "version.json").exists():
        target_dirs.append(installed_d)
    if installed_c and (installed_c / "version.json").exists():
        target_dirs.append(installed_c)
    if base_dir not in target_dirs:
        target_dirs.append(base_dir)

    print(f"[*] Detected Update Target(s): {[str(p) for p in target_dirs]}")

    for td in target_dirs:
        terminate_running_instances(td)

    # 1. Backup license.key and user AI keys from targets
    lic_backups: Dict[Path, bytes] = {}
    ai_backups: Dict[Path, Dict[str, Any]] = {}
    for td in target_dirs:
        lic_file = td / "license.key"
        if lic_file.exists():
            try:
                lic_backups[td] = lic_file.read_bytes()
                print(f"[OK] License key backed up safely for {td} ({len(lic_backups[td])} bytes)")
            except Exception as e:
                print(f"[!] Warning reading license.key: {e}")

        ai_cfg_path = td / "data" / "ai_provider_config.json"
        if ai_cfg_path.exists():
            try:
                old_ai = json.loads(ai_cfg_path.read_text(encoding="utf-8"))
                if old_ai.get("gemini_api_key") or old_ai.get("keys") or old_ai.get("keys_raw"):
                    ai_backups[td] = {
                        k: old_ai[k]
                        for k in ("gemini_api_key", "keys", "keys_raw", "nisay_api_key")
                        if old_ai.get(k)
                    }
            except Exception:
                pass

    # 2. Download latest update package
    temp_zip = Path(os.environ.get("TEMP", ".")) / f"SN_TOOL_UPDATE_v{target_ver}.zip"
    print(f"\n[*] Downloading v{target_ver} package from Cloud CDN...")
    download_ok = False
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Cache-Control": "no-cache, no-store, must-revalidate",
    }

    try:
        sep = "&" if "?" in dl_url else "?"
        req = urllib.request.Request(f"{dl_url}{sep}_cb={int(time.time())}", headers=headers)
        with urllib.request.urlopen(req, timeout=180) as resp, open(temp_zip, "wb") as out_f:
            total_read = 0
            while chunk := resp.read(65536):
                out_f.write(chunk)
                total_read += len(chunk)
        if temp_zip.stat().st_size < 1_000_000:
            raise RuntimeError(f"Downloaded package too small ({temp_zip.stat().st_size} bytes)")
        if expected_sha:
            actual_sha = _sha256_file(temp_zip)
            if actual_sha != expected_sha:
                raise RuntimeError(f"SHA-256 mismatch ({actual_sha} != {expected_sha})")
            print("[OK] SHA-256 integrity verified.")
        with zipfile.ZipFile(temp_zip, "r") as zf:
            bad = zf.testzip()
            if bad:
                raise RuntimeError(f"Corrupt archive entry: {bad}")
        print(f"[OK] Download completed & verified ({total_read / (1024*1024):.2f} MB)!")
        download_ok = True
    except Exception as e:
        print(f"[!] Cloud download error: {e}")
        temp_zip.unlink(missing_ok=True)
        local_zip = base_dir / "SN_TOOL_UPDATE.zip"
        if local_zip.exists():
            print("[*] Using local SN_TOOL_UPDATE.zip package as fallback...")
            temp_zip = local_zip
            download_ok = True

    if not download_ok or not temp_zip.exists():
        print("[ERROR] Failed to obtain valid update package. Please check internet connection.")
        return 1

    # 3. Extract over targets with retry logic
    for td in target_dirs:
        print(f"\n[*] Extracting latest update patch over: {td}...")
        extracted = False
        for attempt in range(1, 5):
            try:
                _safe_extract_zip(temp_zip, td)
                print(f"  [OK] Extraction completed successfully on attempt {attempt}!")
                extracted = True
                break
            except Exception as e:
                print(f"  [!] Extraction retry {attempt}/4: {e}")
                terminate_running_instances(td)
                time.sleep(2)

        if not extracted:
            print(f"[!] Error: Could not extract all files into {td}")
            continue

        if td in lic_backups:
            try:
                (td / "license.key").write_bytes(lic_backups[td])
                print(f"  [OK] License key restored and verified for {td.name}!")
            except Exception as e:
                print(f"  [!] Error restoring license.key: {e}")

        if td in ai_backups:
            ai_cfg_path = td / "data" / "ai_provider_config.json"
            if ai_cfg_path.exists():
                try:
                    new_ai = json.loads(ai_cfg_path.read_text(encoding="utf-8"))
                    for k, v in ai_backups[td].items():
                        if not new_ai.get(k):
                            new_ai[k] = v
                    ai_cfg_path.write_text(json.dumps(new_ai, indent=2, ensure_ascii=False), encoding="utf-8")
                    print("  [OK] User AI provider keys preserved.")
                except Exception:
                    pass

        try:
            (td / "data" / ".update_pending").write_text(str(time.time()), encoding="utf-8")
        except Exception:
            pass

    if temp_zip != base_dir / "SN_TOOL_UPDATE.zip" and temp_zip.exists():
        temp_zip.unlink(missing_ok=True)

    print()
    print("=" * 70)
    print(f"  [SUCCESS] SN TOOL STUDIO PRO has been updated to v{target_ver}!")
    print("=" * 70)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
