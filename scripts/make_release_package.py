import os
import sys
import json
import shutil
import datetime
import subprocess
from pathlib import Path

def run_step(cmd_list, desc):
    print(f"\n[*] {desc}...")
    res = subprocess.run(cmd_list, cwd=str(Path(__file__).resolve().parent.parent))
    if res.returncode != 0:
        print(f"[!] Warning: Step failed with return code {res.returncode}")
    else:
        print(f"[OK] {desc} completed successfully.")

def get_github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="url=https://github.com/ksuyvisal-a11y/SN.git\n",
            capture_output=True,
            text=True,
            timeout=5
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("password=", 1)[1].strip()
    except Exception:
        pass
    return ""

def upload_release_asset(upload_url: str, file_path: Path, token: str):
    import urllib.request
    file_size = file_path.stat().st_size
    url = upload_url.split("{")[0] + f"?name={file_path.name}"
    content_type = "application/zip" if file_path.name.endswith(".zip") else "application/octet-stream"
    with open(file_path, "rb") as f:
        data = f.read()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Content-Type", content_type)
    req.add_header("Content-Length", str(file_size))
    req.add_header("User-Agent", "SN-Tool-AutoPublisher/1.0")
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.status in (200, 201)

def auto_publish_github_release(new_ver: str, vdata: dict, target_installer: Path, backup_zip: Path):
    import urllib.request
    token = get_github_token()
    if not token:
        print("\n[!] មិនមាន GitHub Token ទេ សូមធ្វើការ Upload ដោយដៃតាម Browser។")
        return False
    print(f"\n[*] កំពុង Publish Version v{new_ver} ទៅកាន់ GitHub Releases ដោយស្វ័យប្រវត្តិ...")
    headers = {
        "Authorization": f"token {token}",
        "User-Agent": "SN-Tool-AutoPublisher/1.0",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
    tag_name = f"v{new_ver}"
    # 1. Check if release exists
    rel_data = None
    try:
        check_req = urllib.request.Request(
            f"https://api.github.com/repos/ksuyvisal-a11y/SN/releases/tags/{tag_name}",
            headers=headers
        )
        with urllib.request.urlopen(check_req) as resp:
            rel_data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass

    # 2. If not exists, create release
    if not rel_data:
        try:
            create_payload = {
                "tag_name": tag_name,
                "target_commitish": "main",
                "name": f"SN TOOL STUDIO PRO - Official Update v{new_ver}",
                "body": vdata.get("release_notes", f"Official Release v{new_ver}"),
                "draft": False,
                "prerelease": False
            }
            create_req = urllib.request.Request(
                "https://api.github.com/repos/ksuyvisal-a11y/SN/releases",
                data=json.dumps(create_payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(create_req) as resp:
                rel_data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[!] Warning creating GitHub release: {e}")
            return False

    upload_url = rel_data.get("upload_url", "")
    if not upload_url:
        return False

    existing_assets = [a.get("name") for a in rel_data.get("assets", [])]
    for asset_file in [backup_zip, target_installer]:
        if asset_file and asset_file.exists():
            if asset_file.name in existing_assets:
                print(f"[OK] {asset_file.name} មានរួចហើយនៅលើ GitHub Release។")
                continue
            print(f"[*] កំពុង Upload {asset_file.name} ({asset_file.stat().st_size / (1024*1024):.2f} MB)...")
            try:
                upload_release_asset(upload_url, asset_file, token)
                print(f"[OK] Upload {asset_file.name} ជោគជ័យ!")
            except Exception as e:
                print(f"[!] Warning uploading {asset_file.name}: {e}")

    print(f"\n🎉 GitHub Release v{new_ver} ត្រូវបានផ្សព្វផ្សាយជោគជ័យ ១០០%!")
    print(f"👉 Link: https://github.com/ksuyvisal-a11y/SN/releases/tag/v{new_ver}")
    return True

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass

    base_dir = Path(__file__).resolve().parent.parent
    vjson_path = base_dir / "version.json"
    update_py_path = base_dir / "update.py"

    print("=" * 65)
    print("  🚀 SN TOOL - 1-CLICK UPDATE & RELEASE CREATOR (Khmer Edition)")
    print("=" * 65)

    current_ver = "1.0.7"
    vdata = {}
    if vjson_path.exists():
        try:
            with open(vjson_path, "r", encoding="utf-8") as f:
                vdata = json.load(f)
                current_ver = vdata.get("version", current_ver)
        except Exception:
            pass

    print(f"\n📌 Version បច្ចុប្បន្ន: v{current_ver}")
    print("-----------------------------------------------------------------")
    print(f"👉 វាយលេខ Version ថ្មី (ចុច Enter ភ្លាម ប្រសិនបើចង់រក្សាទុក v{current_ver}):")
    new_ver_input = input(f"New Version [Enter for v{current_ver}]: ").strip()
    new_ver = new_ver_input.lstrip("vV") if new_ver_input else current_ver

    # Update version.json
    today_str = datetime.date.today().isoformat()
    vdata["version"] = new_ver
    vdata["release_date"] = today_str
    vdata["title"] = f"SN TOOL STUDIO PRO - Official Update v{new_ver}"
    vdata["download_url"] = "https://github.com/ksuyvisal-a11y/SN/releases/latest/download/SN_TOOL_Setup.exe"
    
    with open(vjson_path, "w", encoding="utf-8") as f:
        json.dump(vdata, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] បានកែសម្រួល version.json ទៅជា v{new_ver} ({today_str})")

    # Update CURRENT_VERSION in update.py
    if update_py_path.exists():
        try:
            content = update_py_path.read_text(encoding="utf-8")
            import re
            new_content = re.sub(r'CURRENT_VERSION\s*=\s*"[^"]+"', f'CURRENT_VERSION = "{new_ver}"', content, count=1)
            update_py_path.write_text(new_content, encoding="utf-8")
            print(f"[OK] បានកែសម្រួល update.py CURRENT_VERSION ទៅជា v{new_ver}")
        except Exception as e:
            print(f"[!] Warning updating update.py: {e}")

    # 1. Sync dist folders
    run_step([sys.executable, str(base_dir / "scripts" / "sync_dist.py")], "Synchronizing static and configs to dist/")

    # 2. Package update zip (as backup patch)
    run_step([sys.executable, str(base_dir / "scripts" / "package_update_zip.py")], "Packaging backup patch SN_TOOL_UPDATE.zip")

    # 3. Build single-file installer SN_TOOL_Setup.exe
    run_step([sys.executable, str(base_dir / "scripts" / "build_installer.py")], "Compiling 1-File Standalone Setup (SN_TOOL_Setup.exe)")

    target_installer = base_dir / "dist" / "SN_TOOL_Setup.exe"

    print("\n" + "=" * 65)
    print("  🎉 រួចរាល់ ១០០%! ឯកសារ 1-FILE RELEASE ត្រូវបានបង្កើតរួចរាល់")
    print("=" * 65)
    if target_installer.exists():
        print(f"  💿 File តែមួយគត់សម្រាប់ Release: dist/{target_installer.name} ({target_installer.stat().st_size / (1024*1024):.2f} MB)")

    # 4. Prepare clean Google Drive release folder (only 2 small files!)
    gdrive_folder = base_dir / "dist" / "READY_FOR_GOOGLE_DRIVE"
    gdrive_folder.mkdir(parents=True, exist_ok=True)
    if (base_dir / "version.json").exists():
        shutil.copy2(base_dir / "version.json", gdrive_folder / "version.json")
    if (base_dir / "SN_TOOL_UPDATE.zip").exists():
        shutil.copy2(base_dir / "SN_TOOL_UPDATE.zip", gdrive_folder / "SN_TOOL_UPDATE.zip")

    print("\n" + "=" * 65)
    print("  ☁️  GOOGLE DRIVE AUTO-UPDATE PACK (ទំហំតែ ~26 MB)")
    print("=" * 65)
    print("  👉 ដើម្បីឱ្យ User ចាស់ទាំងអស់ Auto-Update ស្វ័យប្រវត្តិតាម Cloud:")
    print("     1. បើក Folder: dist\\READY_FOR_GOOGLE_DRIVE")
    print("     2. អូសទម្លាក់ File ទាំង ២ ចូលក្នុង Google Drive របស់បង")
    print("     3. ចុច SET_UPDATE_CLOUD_LINK.bat ដើម្បី Paste Link Google Drive តែម្តងគត់!")
    print("-----------------------------------------------------------------\n")

    # Automatically highlight the folder in Explorer
    try:
        subprocess.run(f'explorer "{gdrive_folder}"', shell=True)
    except Exception:
        pass

if __name__ == "__main__":
    main()


