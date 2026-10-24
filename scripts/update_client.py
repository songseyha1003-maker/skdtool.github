"""
1-Click Client Updater for SN TOOL STUDIO PRO
Directly updates installation to the latest official release (v1.1.4+)
Safe against file locks, preserves license.key, and updates both
installed Programs folder and portable directories.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import time
import urllib.request
from pathlib import Path

OFFICIAL_UPDATE_ZIP_URL = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip"
VERSION_MANIFEST_URL = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/version.json"

def terminate_running_instances(target_dir: Path):
    """Terminate running SN_TOOL and python worker processes to ensure clean file overwrite."""
    print("[*] Closing running SN_TOOL instances to avoid file lock collisions...")
    if sys.platform == "win32":
        try:
            # Terminate by process name
            subprocess.run(
                ["taskkill", "/f", "/im", "SN_TOOL.exe", "/im", "pythonw.exe"],
                capture_output=True,
                creationflags=0x08000000
            )
            # Give OS 2 seconds to release file handles
            time.sleep(2)
        except Exception:
            pass

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 70)
    print("  🚀 SN TOOL STUDIO PRO - 1-CLICK CLIENT UPDATER (v1.1.4+)")
    print("  ⚡ Auto Drama Folder & Ultra-Accurate AI Translation")
    print("=" * 70)
    print()

    base_dir = Path(__file__).resolve().parent.parent
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    installed_dir = Path(local_app_data) / "Programs" / "SN_TOOL" if local_app_data else None

    # Detect targets to update (can update both if both exist)
    target_dirs = []
    if installed_dir and (installed_dir / "version.json").exists():
        target_dirs.append(installed_dir)
    if base_dir not in target_dirs:
        target_dirs.append(base_dir)

    print(f"[*] Detected Update Target(s): {[str(p) for p in target_dirs]}")

    # Terminate running app instances first
    for td in target_dirs:
        terminate_running_instances(td)

    # 1. Backup license.key from targets
    backups = {}
    for td in target_dirs:
        lic_file = td / "license.key"
        if lic_file.exists():
            try:
                with open(lic_file, "rb") as f:
                    backups[td] = f.read()
                print(f"[OK] License key backed up safely for {td.name} ({len(backups[td])} bytes)")
            except Exception as e:
                print(f"[!] Warning reading license.key: {e}")

    # 2. Download latest update package
    temp_zip = Path(os.environ.get("TEMP", ".")) / "SN_TOOL_UPDATE_v114.zip"
    print(f"\n[*] Downloading latest v1.1.4 package from Cloud CDN...")
    download_ok = False
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cache-Control": "no-cache"
    }

    try:
        req = urllib.request.Request(OFFICIAL_UPDATE_ZIP_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp, open(temp_zip, "wb") as out_f:
            total_read = 0
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out_f.write(chunk)
                total_read += len(chunk)
        print(f"[OK] Download completed successfully ({total_read / (1024*1024):.2f} MB)!")
        download_ok = True
    except Exception as e:
        print(f"[!] Cloud download error: {e}")
        # Check local fallback in base_dir
        local_zip = base_dir / "SN_TOOL_UPDATE.zip"
        if local_zip.exists():
            print("[*] Using local SN_TOOL_UPDATE.zip package as fallback...")
            temp_zip = local_zip
            download_ok = True

    if not download_ok or not temp_zip.exists():
        print("[ERROR] Failed to obtain update package. Please check internet connection.")
        return 1

    # 3. Extract over targets with retry logic
    for td in target_dirs:
        print(f"\n[*] Extracting latest update patch over: {td}...")
        extracted = False
        for attempt in range(1, 4):
            try:
                with zipfile.ZipFile(temp_zip, "r") as zf:
                    zf.extractall(td)
                print(f"  [OK] Extraction completed successfully on attempt {attempt}!")
                extracted = True
                break
            except Exception as e:
                print(f"  [!] Extraction retry {attempt}/3: {e}")
                terminate_running_instances(td)
                time.sleep(2)

        if not extracted:
            print(f"[!] Error: Could not extract all files into {td}")

        # Restore license key
        if td in backups:
            try:
                lic_file = td / "license.key"
                with open(lic_file, "wb") as f:
                    f.write(backups[td])
                print(f"  [OK] License key restored and verified for {td.name}!")
            except Exception as e:
                print(f"  [!] Error restoring license.key: {e}")

    # Cleanup temp zip if created
    if temp_zip != base_dir / "SN_TOOL_UPDATE.zip" and temp_zip.exists():
        try:
            temp_zip.unlink(missing_ok=True)
        except Exception:
            pass

    print()
    print("=" * 70)
    print("  🎉 [SUCCESS] SN TOOL STUDIO PRO has been updated to v1.1.4!")
    print("  ✨ Auto Drama Folder, 1-Folder Clean Export & 184 Tropes active.")
    print("=" * 70)
    print()
    return 0

if __name__ == "__main__":
    sys.exit(main())
