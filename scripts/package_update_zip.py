import os
import sys
import zipfile
import shutil
from pathlib import Path

CLIENT_RUNTIME_PY = [
    "server.py", "desktop_app.py", "downloader.py", "pipeline.py",
    "batch_engine.py", "video_processor.py", "audio_processor.py",
    "translator.py", "tts_engine.py", "stt_engine.py", "vocal_remover.py",
    "license_engine.py", "hongguo_service.py", "hongguo_db.py",
    "shortmax_service.py", "reelshort_service.py", "recap_engine.py",
    "series_memory.py", "subtitle_styler.py", "translate_video.py",
    "run_studio.py", "update.py", "nisay_transcribe.py", "nisay_translate.py"
]

CLIENT_ROOT_FILES = [
    "version.json", "icon.ico", "license_config.json", "custom_keys.json",
    "START_SN_TOOL.bat", "SN_TOOL.bat", "Khmer_Drama_Studio_Launcher.bat", "CREATE_DESKTOP_SHORTCUT.bat",
    "1_CLICK_CLIENT_UPDATER.bat"
]

def package_update_zip():
    base_dir = Path(__file__).resolve().parent.parent
    zip_path = base_dir / "SN_TOOL_UPDATE.zip"
    temp_zip = base_dir / "SN_TOOL_UPDATE.tmp.zip"
    
    print(f"[*] Packaging clean in-app update patch: {zip_path.name}...")
    
    if temp_zip.exists():
        temp_zip.unlink(missing_ok=True)
        
    with zipfile.ZipFile(temp_zip, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # 1. Add only client runtime .py files (strictly exclude admin tools, generators, and dev scripts)
        for py_name in CLIENT_RUNTIME_PY:
            fpath = base_dir / py_name
            if fpath.exists():
                zf.write(fpath, py_name)
            
        # 2. Add client root configs & batch launchers (no admin keys or history)
        for fname in CLIENT_ROOT_FILES:
            fpath = base_dir / fname
            if fpath.exists():
                zf.write(fpath, fname)
                
        # 3. Add static folder
        static_dir = base_dir / "static"
        if static_dir.exists():
            for root, dirs, files in os.walk(static_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(base_dir)
                    zf.write(full_p, str(rel_p).replace('\\', '/'))
                    
        # 4. Add data folder (essential configs and catalogs, exclude temp caches and user projects)
        data_dir = base_dir / "data"
        if data_dir.exists():
            for root, dirs, files in os.walk(data_dir):
                if any(ex in Path(root).parts for ex in ["uploads", "exports", "cache", "projects"]):
                    continue
                for f in files:
                    if f.endswith(('.tmp', '.log', '.db', '.sqlite')):
                        continue
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(base_dir)
                    if f == "ai_provider_config.json":
                        try:
                            import json
                            with open(full_p, "r", encoding="utf-8") as jf:
                                c = json.load(jf)
                            c["gemini_api_key"] = ""
                            c["keys"] = []
                            c["keys_raw"] = ""
                            clean_bytes = json.dumps(c, indent=2, ensure_ascii=False).encode("utf-8")
                            zf.writestr(str(rel_p).replace('\\', '/'), clean_bytes)
                            continue
                        except Exception:
                            pass
                    zf.write(full_p, str(rel_p).replace('\\', '/'))
                    
        # 5. Add only essential scripts needed by client runtime
        for s_name in ["create_shortcut.ps1", "update_client.py", "client_updater.ps1"]:
            s_file = base_dir / "scripts" / s_name
            if s_file.exists():
                zf.write(s_file, f"scripts/{s_name}")

        # 6. Add _internal compiled bytecode and configs for PyInstaller binary support
        dist_internal = base_dir / "dist" / "SN_TOOL" / "_internal"
        if dist_internal.exists():
            for pyc_f in dist_internal.glob("*.pyc"):
                zf.write(pyc_f, f"_internal/{pyc_f.name}")
            int_vjson = dist_internal / "version.json"
            if int_vjson.exists():
                zf.write(int_vjson, "_internal/version.json")
            int_static = dist_internal / "static"
            if int_static.exists():
                for root, dirs, files in os.walk(int_static):
                    for f in files:
                        full_p = Path(root) / f
                        rel_p = full_p.relative_to(dist_internal)
                        zf.write(full_p, f"_internal/{str(rel_p).replace(chr(92), '/')}")

    # Replace target zip
    try:
        if zip_path.exists():
            zip_path.unlink()
        temp_zip.rename(zip_path)
    except Exception:
        shutil.move(str(temp_zip), str(zip_path))
        
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[OK] Successfully created clean {zip_path.name} ({size_mb:.2f} MB)")


def package_portable_zip():
    """
    Creates a clean portable zip from dist/SN_TOOL enclosed in a single root folder.
    When a user unzips this, it unpacks into a single neat 'SN_TOOL' folder with SN_TOOL.exe!
    """
    base_dir = Path(__file__).resolve().parent.parent
    dist_dir = base_dir / "dist" / "SN_TOOL"
    if not dist_dir.exists():
        print("[-] dist/SN_TOOL does not exist. Skipping portable zip.")
        return

    portable_zip = base_dir / "dist" / "SN_TOOL_Portable.zip"
    print(f"[*] Packaging standalone portable zip: {portable_zip.name}...")
    
    with zipfile.ZipFile(portable_zip, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(dist_dir):
            for f in files:
                if f.lower() == "license.key":
                    continue  # Ensure clients start unactivated
                full_p = Path(root) / f
                rel_p = full_p.relative_to(dist_dir)
                # Store under SN_TOOL/ so unzipping creates a single clean folder!
                archive_name = f"SN_TOOL/{str(rel_p).replace(chr(92), '/')}"
                zf.write(full_p, archive_name)

    size_mb = portable_zip.stat().st_size / (1024 * 1024)
    print(f"[OK] Successfully created {portable_zip.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    package_update_zip()
    package_portable_zip()
