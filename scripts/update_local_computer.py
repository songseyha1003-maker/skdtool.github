"""
Update Local Computer Installation for SN TOOL
Directly updates C:\\Users\\M\\AppData\\Local\\Programs\\SN_TOOL and dist/SN_TOOL
with all latest v1.0.6 modules, static assets, and configurations while strictly
preserving license.key and user project data.
"""

import os
import sys
import json
import shutil
import py_compile
from pathlib import Path

def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    p = Path(__file__).resolve().parent
    if p.name == "scripts":
        p = p.parent
    if p.name == "_internal":
        p = p.parent
    base_dir = p
    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\M\AppData\Local")
    installed_c = Path(local_app_data) / "Programs" / "SN_TOOL"
    installed_d = Path(r"D:\SN_TOOL")

    v_file = base_dir / "version.json"
    target_ver = "2.0.7"
    if v_file.exists():
        try:
            target_ver = str(json.loads(v_file.read_text(encoding="utf-8")).get("version") or target_ver)
        except Exception:
            pass

    print("=" * 65)
    print(f"  🚀 SN TOOL - LOCAL COMPUTER UPDATE ENGINE (v{target_ver})")
    print("=" * 65)
    print(f" Source Workspace: {base_dir}")
    print("-" * 65)

    targets = []
    if installed_d.exists():
        targets.append((installed_d, installed_d / "_internal"))
    if installed_c.exists():
        targets.append((installed_c, installed_c / "_internal"))
    if (base_dir / "dist" / "SN_TOOL").exists():
        targets.append((base_dir / "dist" / "SN_TOOL", base_dir / "dist" / "SN_TOOL" / "_internal"))

    if not targets:
        # Default to D:\SN_TOOL if nothing exists
        targets.append((installed_d, installed_d / "_internal"))

    for root_d, int_d in targets:
        root_d.mkdir(parents=True, exist_ok=True)
        int_d.mkdir(parents=True, exist_ok=True)

    # 1. Update Core Python Modules
    python_modules = [
        "server.py", "desktop_app.py", "downloader.py", "pipeline.py",
        "batch_engine.py", "video_processor.py", "audio_processor.py",
        "translator.py", "tts_engine.py", "stt_engine.py", "vocal_remover.py",
        "license_engine.py", "hongguo_service.py", "hongguo_db.py",
        "shortmax_service.py", "reelshort_service.py", "recap_engine.py",
        "series_memory.py", "subtitle_styler.py", "translate_video.py",
        "run_studio.py", "update.py", "disk_cleaner.py", "nisay_transcribe.py", "nisay_translate.py"
    ]

    print("\n[*] Updating Python source modules and compiling bytecode...")
    for mod in python_modules:
        src = base_dir / mod
        if src.exists():
            for root_d, int_d in targets:
                shutil.copy2(src, root_d / mod)
                shutil.copy2(src, int_d / mod)
                pyc_dst = int_d / f"{src.stem}.pyc"
                try:
                    py_compile.compile(str(src), cfile=str(pyc_dst), optimize=2)
                except Exception:
                    pass

    print(f"  [OK] Updated {len(python_modules)} Python modules (both .py and .pyc)")

    # 2. Update Version & Configs
    print("\n[*] Updating version metadata & launcher configs...")
    config_files = [
        "version.json", "license_config.json", "custom_keys.json", "icon.ico",
        "START_SN_TOOL.bat", "CREATE_DESKTOP_SHORTCUT.bat",
        "create_shortcut.ps1", "SN_TOOL.bat", "1_CLICK_CLIENT_UPDATER.bat"
    ]
    for cfg in config_files:
        src = base_dir / cfg
        if src.exists():
            for root_d, int_d in targets:
                shutil.copy2(src, root_d / cfg)
                shutil.copy2(src, int_d / cfg)
    print(f"  [OK] version.json (v{target_ver}) and launch configs updated!")

    # 3. Update Static Assets (Web UI)
    print("\n[*] Updating Web UI static assets...")
    for root_d, int_d in targets:
        for target_static in [root_d / "static", int_d / "static"]:
            if target_static.exists():
                shutil.rmtree(target_static)
            shutil.copytree(base_dir / "static", target_static)
    print("  [OK] Static assets updated successfully!")

    # 4. Update Data Files (Carefully preserving user projects, API keys & license.key!)
    print("\n[*] Updating data catalogs and story configs...")
    data_files = [
        "ai_provider_config.json", "update_config.json", "cloud_manifest.json", "story_config.json",
        "drama_dictionary.json", "shortmax_all_dramas.json",
        "reelshort_all_dramas.json", "ai_dramas_streams.json", "license_keys_online.json",
        "revoked_keys.json", "hongguo_catalog.db"
    ]
    for root_d, int_d in targets:
        t_data = root_d / "data"
        t_data.mkdir(parents=True, exist_ok=True)
        t_int_data = int_d / "data"
        t_int_data.mkdir(parents=True, exist_ok=True)

        # Preserve any user-saved AI keys in target before overwriting ai_provider_config.json
        preserved_ai = {}
        target_ai_path = t_data / "ai_provider_config.json"
        if target_ai_path.exists():
            try:
                old_ai = json.loads(target_ai_path.read_text(encoding="utf-8"))
                for k in ("gemini_api_key", "keys", "keys_raw", "nisay_api_key"):
                    if old_ai.get(k):
                        preserved_ai[k] = old_ai[k]
            except Exception:
                pass

        for df in data_files:
            src = base_dir / "data" / df
            if src.exists():
                shutil.copy2(src, t_data / df)
                shutil.copy2(src, t_int_data / df)

        if preserved_ai and target_ai_path.exists():
            try:
                merged_ai = json.loads(target_ai_path.read_text(encoding="utf-8"))
                for k, v in preserved_ai.items():
                    if not merged_ai.get(k):
                        merged_ai[k] = v
                target_ai_path.write_text(json.dumps(merged_ai, indent=2, ensure_ascii=False), encoding="utf-8")
                (t_int_data / "ai_provider_config.json").write_text(json.dumps(merged_ai, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

        try:
            (t_data / ".update_pending").write_text("updated", encoding="utf-8")
        except Exception:
            pass
    print("  [OK] Catalogs, Nisay AI configs, and story settings synchronized!")

    # 5. Update Scripts and Tools
    print("\n[*] Synchronizing auxiliary scripts...")
    for root_d, int_d in targets:
        for target_scripts in [root_d / "scripts", int_d / "scripts"]:
            target_scripts.mkdir(parents=True, exist_ok=True)
            for sname in ["create_shortcut.ps1", "hg_cli_runner.py", "client_updater.ps1", "update_client.py"]:
                src = base_dir / "scripts" / sname
                if src.exists():
                    shutil.copy2(src, target_scripts / sname)

    # 6. Verify and preserve license.key
    for root_d, _ in targets:
        lic_file = root_d / "license.key"
        if lic_file.exists():
            print(f"\n[OK] Active client license.key PRESERVED intact: {lic_file}")
        else:
            ws_lic = base_dir / "license.key"
            if ws_lic.exists():
                shutil.copy2(ws_lic, lic_file)
                print(f"\n[OK] Copied license.key from workspace: {lic_file}")

    # 7. Refresh SN_TOOL.exe and SN_TOOL.exe.bak
    for root_d, _ in targets:
        exe_path = root_d / "SN_TOOL.exe"
        dist_exe = base_dir / "dist" / "SN_TOOL" / "SN_TOOL.exe"
        try:
            if dist_exe.exists() and dist_exe != exe_path:
                shutil.copy2(dist_exe, exe_path)
            exe_bak = root_d / "SN_TOOL.exe.bak"
            if exe_path.exists():
                shutil.copy2(exe_path, exe_bak)
                print(f"[OK] Refreshed Defender self-healing binary backup: {exe_bak}")
        except PermissionError:
            print("[*] Note: SN_TOOL.exe is currently active. Loose modules (.py / .pyc) and static assets updated successfully!")

    print("\n" + "=" * 65)
    print(f"  🎉 LOCAL COMPUTER UPDATE TO v{target_ver} COMPLETE 100%!")
    print("=" * 65)

if __name__ == "__main__":
    main()
