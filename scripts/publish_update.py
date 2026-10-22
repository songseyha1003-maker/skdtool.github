"""
SN TOOL STUDIO PRO - 1-Click Master Release & OTA Publisher
Automates the entire release cycle so the developer NEVER needs to manually configure,
package, or ask for help when updating versions in the future!

Workflow:
1. Bumps version in version.json, data/cloud_manifest.json, update.py
2. Synchronizes local computer installation & dist/SN_TOOL
3. Packages clean SN_TOOL_UPDATE.zip (No .exe collision) & SN_TOOL_Portable.zip
4. Synchronizes dist/READY_FOR_GOOGLE_DRIVE
5. Automatically commits and pushes to GitHub (OTA Cloud CDN)
6. Instant live deployment to all active users worldwide!
"""

import os
import sys
import json
import shutil
import datetime
import subprocess
from pathlib import Path

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass

    base_dir = Path(__file__).resolve().parent.parent
    vjson_file = base_dir / "version.json"
    manifest_file = base_dir / "data" / "cloud_manifest.json"
    update_py_file = base_dir / "update.py"

    print("=" * 70)
    print("  🚀 SN TOOL STUDIO PRO - 1-CLICK MASTER OTA UPDATE PUBLISHER")
    print("  Publish seamless updates directly to all client computers")
    print("=" * 70)

    # 1. Read current version
    current_ver = "1.1.3"
    current_notes = ""
    current_title = ""
    if vjson_file.exists():
        try:
            with open(vjson_file, "r", encoding="utf-8") as f:
                vdata = json.load(f)
                current_ver = str(vdata.get("version", current_ver)).strip()
                current_notes = vdata.get("release_notes", "")
                current_title = vdata.get("title", "")
        except Exception:
            pass

    # Suggest next version (e.g., 1.1.3 -> 1.1.4)
    parts = current_ver.split(".")
    if len(parts) == 3 and parts[2].isdigit():
        suggested_ver = f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"
    else:
        suggested_ver = current_ver

    print(f"\n📌 Version បច្ចុប្បន្ន: v{current_ver}")
    print(f"👉 Version បន្ទាប់ដែលបានណែនាំ: v{suggested_ver}")
    print("-" * 70)
    print(f"ចុច [Enter] ដើម្បីយក v{suggested_ver} ឬវាយលេខ Version ថ្មីដែលបងចង់បាន:")
    ver_input = input(f"New Version [{suggested_ver}]: ").strip()
    new_ver = ver_input.lstrip("vV") if ver_input else suggested_ver

    print(f"\n👉 វាយចំណុចថ្មី ឬកែលម្អក្នុង Version v{new_ver} (ចុច [Enter] ដើម្បីរក្សាកំណត់ត្រាចាស់):")
    notes_input = input("Release Notes: ").strip()
    if not notes_input:
        notes_input = current_notes or "• ⚡ Continuous performance optimizations and security improvements."

    today_str = datetime.date.today().isoformat()
    new_title = f"SN TOOL STUDIO PRO - Official Update v{new_ver}"
    dl_url = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip"

    print(f"\n[*] កំពុងធ្វើបច្ចុប្បន្នភាពឯកសារកំណត់ Version...")

    # 2. Update version.json
    vdata = {
        "version": new_ver,
        "app_name": "SN TOOL - STUDIO PRO",
        "release_date": today_str,
        "title": new_title,
        "release_notes": notes_input,
        "download_url": dl_url,
        "channel": "stable"
    }
    with open(vjson_file, "w", encoding="utf-8") as f:
        json.dump(vdata, f, indent=2, ensure_ascii=False)
    print("  [OK] version.json updated!")

    # 3. Update data/cloud_manifest.json
    manifest_data = {
        "version": new_ver,
        "app_name": "SN TOOL - STUDIO PRO",
        "release_date": today_str,
        "title": new_title,
        "subtitle": f"A major update (v{new_ver}) is available with the latest neural engine upgrades and performance improvements.",
        "release_notes": notes_input,
        "download_url": dl_url,
        "channel": "stable"
    }
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
    print("  [OK] data/cloud_manifest.json updated!")

    # 4. Update update.py CURRENT_VERSION
    if update_py_file.exists():
        try:
            content = update_py_file.read_text(encoding="utf-8")
            import re
            new_content = re.sub(r'CURRENT_VERSION\s*=\s*"[^"]+"', f'CURRENT_VERSION = "{new_ver}"', content, count=1)
            update_py_file.write_text(new_content, encoding="utf-8")
            print(f"  [OK] update.py CURRENT_VERSION set to {new_ver}!")
        except Exception as e:
            print(f"  [!] Warning updating update.py: {e}")

    # 5. Synchronize local installation & dist
    print("\n[*] 1/4. កំពុង Sync កូដថ្មីចូលម៉ាស៊ីនក្នុងស្រុក និង dist/SN_TOOL...")
    update_local_script = base_dir / "scripts" / "update_local_computer.py"
    if update_local_script.exists():
        subprocess.run([sys.executable, str(update_local_script)], cwd=str(base_dir))

    # 6. Package clean SN_TOOL_UPDATE.zip & SN_TOOL_Portable.zip
    print("\n[*] 2/4. កំពុងវេចខ្ចប់ SN_TOOL_UPDATE.zip & Portable Package...")
    package_script = base_dir / "scripts" / "package_update_zip.py"
    if package_script.exists():
        subprocess.run([sys.executable, str(package_script)], cwd=str(base_dir))

    # 7. Copy to READY_FOR_GOOGLE_DRIVE
    print("\n[*] 3/4. កំពុងរៀបចំថត dist/READY_FOR_GOOGLE_DRIVE...")
    gdrive_dir = base_dir / "dist" / "READY_FOR_GOOGLE_DRIVE"
    gdrive_dir.mkdir(parents=True, exist_ok=True)
    for fn in ["version.json", "SN_TOOL_UPDATE.zip", "1_CLICK_CLIENT_UPDATER.bat"]:
        src = base_dir / fn
        if src.exists():
            shutil.copy2(src, gdrive_dir / fn)
    if manifest_file.exists():
        shutil.copy2(manifest_file, gdrive_dir / "cloud_manifest.json")
    print("  [OK] dist/READY_FOR_GOOGLE_DRIVE is ready!")

    # 8. Git Commit & Push to GitHub OTA
    print("\n[*] 4/4. កំពុង Upload និង Push ទៅកាន់ GitHub OTA Cloud CDN...")
    try:
        subprocess.run(["git", "add", "-A"], cwd=str(base_dir), check=True)
        commit_msg = f"release: official release v{new_ver} - {notes_input[:50]}"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(base_dir))
        push_res = subprocess.run(["git", "push", "origin", "main"], cwd=str(base_dir))
        if push_res.returncode == 0:
            print("\n" + "=" * 70)
            print(f"  🎉 ជោគជ័យ ១០០%! VERSION v{new_ver} ត្រូវបានផ្សព្វផ្សាយឡើង OTA រួចរាល់ស្ថាពរ!")
            print("=" * 70)
            print(f"  📡 Cloud OTA URL: {dl_url}")
            print(f"  👉 ចាប់ពីពេលនេះទៅ នៅពេល User បើកកម្មវិធី SN TOOL វានឹងលោត:")
            print(f"     'New version available: v{new_ver}'")
            print(f"     ហើយគាត់គ្រាន់តែចុច 'Update Now (v{new_ver})' គឺវានឹង Update ឡើងដោយខ្លួនឯង!")
            print("=" * 70)
        else:
            print("\n[!] Git push ជួបបញ្ហា សូមពិនិត្យមើល Internet ឬរត់ PUSH_TO_GITHUB.bat")
    except Exception as e:
        print(f"\n[!] Git error: {e}")

    print("\nរួចរាល់! ចុច Enter ដើម្បីបិទផ្ទាំងនេះ...")
    input()

if __name__ == "__main__":
    main()
