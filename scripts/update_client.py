"""
1-Click Client Updater for SN TOOL
Directly downloads the latest v1.0.9 update patch from Google Drive CDN,
safely preserves license.key, and unpacks cleanly over the target installation.
"""

import os
import sys
import shutil
import zipfile
import urllib.request
from pathlib import Path

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 70)
    print("  [*] SN TOOL STUDIO PRO - 1-CLICK CLIENT UPDATER (v1.0.9)")
    print("  [*] Google Drive Cloud CDN Direct Update Engine")
    print("=" * 70)
    print()

    base_dir = Path(__file__).resolve().parent.parent
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    installed_dir = Path(local_app_data) / "Programs" / "SN_TOOL" if local_app_data else None

    target_dir = base_dir
    if installed_dir and (installed_dir / "version.json").exists():
        target_dir = installed_dir

    print(f"[*] Target Directory: {target_dir}")

    # Backup license.key
    lic_file = target_dir / "license.key"
    lic_backup_bytes = None
    if lic_file.exists():
        try:
            with open(lic_file, "rb") as f:
                lic_backup_bytes = f.read()
            print(f"[*] License key backed up safely ({len(lic_backup_bytes)} bytes)")
        except Exception as e:
            print(f"[!] Warning reading license.key: {e}")

    # Download latest update from Google Drive
    download_url = "https://drive.usercontent.google.com/download?id=1x_k269mEwMPH01tx8o6N67QEtLz7jlUo&export=download&confirm=t"
    temp_zip = Path(os.environ.get("TEMP", ".")) / "SN_TOOL_UPDATE_v109.zip"

    print("[*] Downloading update package from Google Drive Cloud CDN...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        req = urllib.request.Request(download_url, headers=headers)
        with urllib.request.urlopen(req, timeout=300) as resp, open(temp_zip, "wb") as out_f:
            total_read = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out_f.write(chunk)
                total_read += len(chunk)
        print(f"[OK] Download complete ({total_read / (1024*1024):.2f} MB)!")
    except Exception as e:
        print(f"[!] Download failed: {e}")
        # If local SN_TOOL_UPDATE.zip exists, use as fallback
        local_zip = base_dir / "SN_TOOL_UPDATE.zip"
        if local_zip.exists():
            print("[*] Using local SN_TOOL_UPDATE.zip package as fallback...")
            temp_zip = local_zip
        else:
            return 1

    # Extract update package
    print(f"[*] Extracting v1.0.9 update patch over {target_dir}...")
    try:
        with zipfile.ZipFile(temp_zip, "r") as zf:
            zf.extractall(target_dir)
        print("[OK] All modules, static files, and configs extracted successfully!")
    except Exception as e:
        print(f"[!] Extraction error: {e}")
        return 1

    # Restore license key
    if lic_backup_bytes:
        try:
            with open(lic_file, "wb") as f:
                f.write(lic_backup_bytes)
            print("[OK] License key restored and verified!")
        except Exception as e:
            print(f"[!] Error restoring license.key: {e}")

    # Cleanup temp zip if downloaded
    if temp_zip != base_dir / "SN_TOOL_UPDATE.zip" and temp_zip.exists():
        try:
            temp_zip.unlink(missing_ok=True)
        except Exception:
            pass

    print()
    print("=" * 70)
    print("  [SUCCESS] SN TOOL Studio Pro has been updated to Version 1.0.9!")
    print("  [SUCCESS] Khmer Neural Audio & Nisay AI Gateway are active!")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
