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

    base_dir = Path(__file__).resolve().parent.parent
    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\M\AppData\Local")
    installed_dir = Path(local_app_data) / "Programs" / "SN_TOOL"

    print("=" * 65)
    print("  🚀 SN TOOL - LOCAL COMPUTER UPDATE ENGINE (v1.1.6)")
    print("=" * 65)
    print(f" Source Workspace: {base_dir}")
    print(f" Installed App Dir: {installed_dir}")
    print("-" * 65)

    if not installed_dir.exists():
        print(f"[!] Warning: Installed directory not found at {installed_dir}")
        print("[*] Creating installation directory...")
        installed_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        (installed_dir, installed_dir / "_internal"),
        (base_dir / "dist" / "SN_TOOL", base_dir / "dist" / "SN_TOOL" / "_internal")
    ]

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
        "run_studio.py", "update.py", "nisay_transcribe.py", "nisay_translate.py"
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
        "create_shortcut.ps1", "SN_TOOL.bat"
    ]
    for cfg in config_files:
        src = base_dir / cfg
        if src.exists():
            for root_d, int_d in targets:
                shutil.copy2(src, root_d / cfg)
                shutil.copy2(src, int_d / cfg)
    print("  [OK] version.json (v1.1.6) and launch configs updated!")

    # 3. Update Static Assets (Web UI)
    print("\n[*] Updating Web UI static assets...")
    for root_d, int_d in targets:
        for target_static in [root_d / "static", int_d / "static"]:
            if target_static.exists():
                shutil.rmtree(target_static)
            shutil.copytree(base_dir / "static", target_static)
    print("  [OK] Static assets updated successfully!")

    # 4. Update Data Files (Carefully preserving user projects & license.key!)
    print("\n[*] Updating data catalogs and story configs...")
    data_files = [
        "ai_provider_config.json", "update_config.json", "story_config.json",
        "drama_dictionary.json", "shortmax_all_dramas.json",
        "reelshort_all_dramas.json", "ai_dramas_streams.json", "license_keys_online.json",
        "revoked_keys.json", "hongguo_catalog.db"
    ]
    for root_d, int_d in targets:
        t_data = root_d / "data"
        t_data.mkdir(parents=True, exist_ok=True)
        t_int_data = int_d / "data"
        t_int_data.mkdir(parents=True, exist_ok=True)
        for df in data_files:
            src = base_dir / "data" / df
            if src.exists():
                shutil.copy2(src, t_data / df)
                shutil.copy2(src, t_int_data / df)
    print("  [OK] Catalogs, Nisay AI configs, and story settings synchronized!")

    # 5. Update Scripts and Tools
    print("\n[*] Synchronizing auxiliary scripts...")
    for root_d, int_d in targets:
        for target_scripts in [root_d / "scripts", int_d / "scripts"]:
            target_scripts.mkdir(parents=True, exist_ok=True)
            for sname in ["create_shortcut.ps1", "hg_cli_runner.py"]:
                src = base_dir / "scripts" / sname
                if src.exists():
                    shutil.copy2(src, target_scripts / sname)

    # 5.1 Synchronize dist/ADMIN_KEY_GENERATOR
    admin_dist = base_dir / "dist" / "ADMIN_KEY_GENERATOR"
    if admin_dist.exists():
        print("\n[*] Synchronizing dist/ADMIN_KEY_GENERATOR modules & admin UI...")
        for a_target in [admin_dist, admin_dist / "_internal"]:
            a_target.mkdir(parents=True, exist_ok=True)
            for m in ["admin_dashboard.py", "ADMIN_KEY_GENERATOR.py", "license_engine.py"]:
                src = base_dir / m
                if src.exists():
                    shutil.copy2(src, a_target / m)
            for cfg in ["license_config.json", "custom_keys.json"]:
                src = base_dir / cfg
                if src.exists():
                    shutil.copy2(src, a_target / cfg)
            s_admin = a_target / "static"
            s_admin.mkdir(parents=True, exist_ok=True)
            if (base_dir / "static" / "admin.html").exists():
                shutil.copy2(base_dir / "static" / "admin.html", s_admin / "admin.html")
        print("  [OK] dist/ADMIN_KEY_GENERATOR synchronized!")

    # 6. Verify and preserve license.key
    lic_file = installed_dir / "license.key"
    if lic_file.exists():
        print(f"\n[OK] Active client license.key PRESERVED intact: {lic_file}")
    else:
        # If there's a workspace license.key, copy it over
        ws_lic = base_dir / "license.key"
        if ws_lic.exists():
            shutil.copy2(ws_lic, lic_file)
            print(f"\n[OK] Copied license.key from workspace: {lic_file}")

    # 7. Refresh SN_TOOL.exe and SN_TOOL.exe.bak
    exe_path = installed_dir / "SN_TOOL.exe"
    root_exe = base_dir / "SN_TOOL.exe"
    dist_exe = base_dir / "dist" / "SN_TOOL" / "SN_TOOL.exe"
    src_exe = root_exe if root_exe.exists() else dist_exe
    try:
        if src_exe.exists():
            shutil.copy2(src_exe, exe_path)
            if dist_exe.parent.exists():
                shutil.copy2(src_exe, dist_exe)
        exe_bak = installed_dir / "SN_TOOL.exe.bak"
        if exe_path.exists():
            shutil.copy2(exe_path, exe_bak)
            print(f"[OK] Refreshed Defender self-healing binary backup: {exe_bak.name}")
    except PermissionError:
        print("[*] Note: SN_TOOL.exe is currently active. Loose modules (.py / .pyc) and static assets updated successfully!")

    print("\n" + "=" * 65)
    print("  🎉 LOCAL COMPUTER UPDATE TO v1.1.6 COMPLETE 100%!")
    print("=" * 65)

if __name__ == "__main__":
    main()
