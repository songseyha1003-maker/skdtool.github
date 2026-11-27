"""
Build clean, verified SN_TOOL_UPDATE.zip OTA patch package
from D:\\Sal\\SN_TOOL without leaking admin tools, private keys, or user data.
Automatically syncs version.json -> data/cloud_manifest.json, compiles .pyc,
computes SHA-256 + size_bytes, verifies archive integrity, and stages READY_FOR_GOOGLE_DRIVE.
"""

import hashlib
import json
import os
import py_compile
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

CLIENT_RUNTIME_PY = [
    "server.py", "desktop_app.py", "downloader.py", "pipeline.py",
    "batch_engine.py", "video_processor.py", "audio_processor.py",
    "translator.py", "tts_engine.py", "stt_engine.py", "vocal_remover.py",
    "license_engine.py", "hongguo_service.py", "hongguo_db.py",
    "shortmax_service.py", "reelshort_service.py", "recap_engine.py",
    "series_memory.py", "subtitle_styler.py", "translate_video.py",
    "run_studio.py", "update.py", "disk_cleaner.py", "nisay_transcribe.py", "nisay_translate.py",
]

CLIENT_ROOT_FILES = [
    "version.json", "icon.ico", "license_config.json", "custom_keys.json",
    "START_SN_TOOL.bat", "SN_TOOL.bat", "Khmer_Drama_Studio_Launcher.bat",
    "CREATE_DESKTOP_SHORTCUT.bat", "1_CLICK_CLIENT_UPDATER.bat",
]

CLIENT_SCRIPTS = [
    "create_shortcut.ps1", "update_client.py", "client_updater.ps1", "hg_cli_runner.py"
]

EXCLUDED_DATA_DIRS = {"uploads", "exports", "cache", "projects", "series_bibles", "__pycache__"}
EXCLUDED_DATA_FILES = {
    "admin_private_key.pem",
    ".sys_anchor",
    "deleted_keys.json",
    "security_audit.log",
    "google_apps_script_v2.js",
    ".update_pending",
    ".ota_installing",
    "update_install.log",
}


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def sync_cloud_manifest_from_version(base_dir: Path, sha256: str = "", size_bytes: int = 0) -> dict:
    """Keep version.json and data/cloud_manifest.json synchronized without embedding stale hashes inside ZIP."""
    v_path = base_dir / "version.json"
    cm_path = base_dir / "data" / "cloud_manifest.json"

    v_data = json.loads(v_path.read_text(encoding="utf-8")) if v_path.exists() else {}
    cm_data = json.loads(cm_path.read_text(encoding="utf-8")) if cm_path.exists() else {}

    for field in ("version", "app_name", "release_date", "title", "subtitle", "release_notes", "download_url", "channel"):
        if v_data.get(field):
            cm_data[field] = v_data[field]

    # Never embed self-referential sha256 inside version.json (packaged into ZIP)
    v_data.pop("sha256", None)
    v_data.pop("size_bytes", None)
    if sha256:
        cm_data["sha256"] = sha256
    else:
        cm_data.pop("sha256", None)
    if size_bytes:
        cm_data["size_bytes"] = int(size_bytes)
    else:
        cm_data.pop("size_bytes", None)

    v_path.write_text(json.dumps(v_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cm_path.parent.mkdir(parents=True, exist_ok=True)
    cm_path.write_text(json.dumps(cm_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return cm_data


def build_core_manifest_sig(base_dir: Path) -> None:
    """Re-sign data/.core_manifest.sig against current source modules."""
    sys.path.insert(0, str(base_dir))
    prev_cwd = os.getcwd()
    try:
        os.chdir(str(base_dir))
        from license_engine import build_core_manifest
        manifest = build_core_manifest()
        print(f"[OK] Signed data/.core_manifest.sig ({len(manifest)} core modules)")
    finally:
        os.chdir(prev_cwd)


def package_update_zip(base_dir: Path | None = None) -> Path:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    base_dir = base_dir or Path(__file__).resolve().parent.parent
    # Pre-sync metadata fields before packaging internal manifests
    rel_meta = sync_cloud_manifest_from_version(base_dir)
    build_core_manifest_sig(base_dir)

    zip_path = base_dir / "SN_TOOL_UPDATE.zip"
    temp_zip = base_dir / "SN_TOOL_UPDATE.tmp.zip"
    if temp_zip.exists():
        temp_zip.unlink(missing_ok=True)

    print(f"[*] Packaging clean OTA patch v{rel_meta.get('version', '?')}: {zip_path.name}...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pyc_dir = tmp_path / "_internal"
        pyc_dir.mkdir(parents=True, exist_ok=True)

        # Compile optimized bytecode for _internal/ (fails fast on any syntax error)
        compiled_count = 0
        for py_name in CLIENT_RUNTIME_PY:
            src_py = base_dir / py_name
            if src_py.exists():
                pyc_dst = pyc_dir / f"{src_py.stem}.pyc"
                py_compile.compile(str(src_py), cfile=str(pyc_dst), optimize=2, doraise=True)
                compiled_count += 1
        print(f"[OK] Compiled {compiled_count} optimized .pyc modules for _internal/")

        with zipfile.ZipFile(temp_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            # 1. Root Python modules
            for py_name in CLIENT_RUNTIME_PY:
                fpath = base_dir / py_name
                if fpath.exists():
                    zf.write(fpath, py_name)

            # 2. Root configs & batch launchers
            for fname in CLIENT_ROOT_FILES:
                fpath = base_dir / fname
                if fpath.exists():
                    zf.write(fpath, fname)

            # 3. Static web UI (both root static/ and _internal/static/)
            static_dir = base_dir / "static"
            if static_dir.exists():
                for root, _, files in os.walk(static_dir):
                    for f in files:
                        full_p = Path(root) / f
                        rel_p = str(full_p.relative_to(base_dir)).replace("\\", "/")
                        zf.write(full_p, rel_p)
                        zf.write(full_p, f"_internal/{rel_p}")

            # 4. Data configs & catalogs (excluding DBs, logs, user projects, and private keys)
            data_dir = base_dir / "data"
            if data_dir.exists():
                for root, dirs, files in os.walk(data_dir):
                    dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DATA_DIRS]
                    rel_root = Path(root).relative_to(data_dir)
                    if any(part.lower() in EXCLUDED_DATA_DIRS for part in rel_root.parts):
                        continue
                    for f in files:
                        if f in EXCLUDED_DATA_FILES or f.lower() in EXCLUDED_DATA_FILES:
                            continue
                        if f.endswith((".tmp", ".log", ".db", ".sqlite", ".pyc")):
                            continue
                        full_p = Path(root) / f
                        rel_p = str(full_p.relative_to(base_dir)).replace("\\", "/")
                        if f == "ai_provider_config.json":
                            try:
                                cfg = json.loads(full_p.read_text(encoding="utf-8"))
                                cfg["gemini_api_key"] = ""
                                cfg["keys"] = []
                                cfg["keys_raw"] = ""
                                zf.writestr(rel_p, json.dumps(cfg, indent=2, ensure_ascii=False).encode("utf-8"))
                                continue
                            except Exception:
                                pass
                        zf.write(full_p, rel_p)

            # 5. Client scripts
            for s_name in CLIENT_SCRIPTS:
                s_file = base_dir / "scripts" / s_name
                if s_file.exists():
                    zf.write(s_file, f"scripts/{s_name}")

            # 6. _internal compiled .pyc and version.json
            for pyc_f in pyc_dir.glob("*.pyc"):
                zf.write(pyc_f, f"_internal/{pyc_f.name}")
            vjson = base_dir / "version.json"
            if vjson.exists():
                zf.write(vjson, "_internal/version.json")

        # Verify ZIP CRC integrity before replacing production zip
        with zipfile.ZipFile(temp_zip, "r") as zf_check:
            bad = zf_check.testzip()
            if bad:
                raise RuntimeError(f"Packaged archive CRC error in entry: {bad}")

    if zip_path.exists():
        zip_path.unlink(missing_ok=True)
    shutil.move(str(temp_zip), str(zip_path))

    # Compute exact SHA-256 and size_bytes and persist to manifests
    zip_sha256 = compute_sha256(zip_path)
    zip_bytes = zip_path.stat().st_size
    sync_cloud_manifest_from_version(base_dir, sha256=zip_sha256, size_bytes=zip_bytes)

    # Sync companion artifacts to dist/READY_FOR_GOOGLE_DRIVE
    gdrive_dir = base_dir / "dist" / "READY_FOR_GOOGLE_DRIVE"
    gdrive_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(zip_path, gdrive_dir / "SN_TOOL_UPDATE.zip")
    for item in ["1_CLICK_CLIENT_UPDATER.bat", "version.json"]:
        src = base_dir / item
        if src.exists():
            shutil.copy2(src, gdrive_dir / item)
    cm_src = base_dir / "data" / "cloud_manifest.json"
    if cm_src.exists():
        shutil.copy2(cm_src, gdrive_dir / "cloud_manifest.json")
    ps_src = base_dir / "scripts" / "client_updater.ps1"
    if ps_src.exists():
        (gdrive_dir / "scripts").mkdir(parents=True, exist_ok=True)
        shutil.copy2(ps_src, gdrive_dir / "scripts" / "client_updater.ps1")

    size_mb = zip_bytes / (1024 * 1024)
    print(f"[OK] Built {zip_path.name} ({size_mb:.2f} MB, sha256={zip_sha256[:16]}...) and synced READY_FOR_GOOGLE_DRIVE.")
    return zip_path


if __name__ == "__main__":
    package_update_zip()
