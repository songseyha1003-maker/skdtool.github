"""
SN TOOL - Cloud Auto-Update Link Manager
Allows Admin to configure Google Drive or direct cloud storage links for 100% resilient auto-updates.
"""

import sys
import os
import json
import re
from pathlib import Path

def extract_gdrive_id(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    # Direct match file/d/<id>
    m = re.search(r"/file/d/([a-zA-Z0-9_-]{20,})", url)
    if m:
        return m.group(1)
    # id=<id>
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]{20,})", url)
    if m:
        return m.group(1)
    # folder/<id>
    m = re.search(r"/folders/([a-zA-Z0-9_-]{20,})", url)
    if m:
        return m.group(1)
    # plain ID
    if "/" not in url and len(url) >= 20:
        return url
    return ""

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdin.reconfigure(encoding="utf-8")
        except Exception:
            pass

    base_dir = Path(__file__).resolve().parent.parent
    cfg_file = base_dir / "data" / "update_config.json"
    cfg = {}
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass

    print("=" * 65)
    print(" ☁️  SN TOOL - CLOUD AUTO-UPDATE LINK MANAGER (Google Drive)")
    print("=" * 65)
    print(" ប្រព័ន្ធនេះអនុញ្ញាតឱ្យ User ចាស់ទាំងអស់ Update ស្វ័យប្រវត្តិតាមរយៈ Google Drive")
    print(" ដោយមិនបាច់ពឹងផ្អែកលើ GitHub និងគ្មានថ្ងៃត្រូវគេបិទឡើយ!\n")

    current_link = cfg.get("google_drive_folder_url") or cfg.get("custom_manifest_url") or "មិនទាន់មាន (Not Set)"
    print(f" 🔗 Link បច្ចុប្បន្ន: {current_link}")
    print("-" * 65)
    print(" 👉 សូម Paste Link Google Drive (Folder ឬ File) ចូលត្រង់នេះ:")
    print("    (ឧទាហរណ៍៖ https://drive.google.com/drive/folders/... ឬ https://drive.google.com/file/d/...)")
    user_input = input("\n👉 Link Google Drive: ").strip()

    if not user_input:
        print("\n[!] មិនមានការផ្លាស់ប្តូរឡើយ។")
        return

    g_id = extract_gdrive_id(user_input)
    if g_id:
        cfg["update_source_type"] = "google_drive"
        cfg["google_drive_folder_url"] = user_input
        cfg["google_drive_file_id"] = g_id
        cfg["direct_download_url"] = f"https://drive.usercontent.google.com/download?id={g_id}&export=download&confirm=t"
        print(f"\n[OK] បានស្គាល់ Google Drive ID: {g_id}")
    else:
        cfg["update_source_type"] = "direct_url"
        cfg["custom_manifest_url"] = user_input
        print(f"\n[OK] បានកត់ត្រា Direct Cloud URL: {user_input}")

    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_file, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    # Sync to dist/SN_TOOL/data/update_config.json if exists
    dist_cfg = base_dir / "dist" / "SN_TOOL" / "data" / "update_config.json"
    if dist_cfg.parent.exists():
        dist_cfg.parent.mkdir(parents=True, exist_ok=True)
        with open(dist_cfg, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    print(f"[OK] បានរក្សាទុកការកំណត់ចូលក្នុង data/update_config.json ជោគជ័យ!")
    print("\n🎉 រួចរាល់ ១០០%! ចាប់ពីពេលនេះ User ចាស់ទាំងអស់នឹង Auto-Update តាម Link នេះ។")
    print("=" * 65)

if __name__ == "__main__":
    main()
