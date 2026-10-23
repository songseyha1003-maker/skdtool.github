"""
SN TOOL - Automated Disk Space & Cache Management Engine
Safely identifies and purges intermediate temporary audio files (*.wav, vocal separation scratch, temp frames)
while strictly preserving all user license keys, exported videos, subtitles, models, and application code.
"""
import os
import sys
import shutil
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

if getattr(sys, 'frozen', False):
    APP_DIR = Path(os.path.dirname(sys.executable))
else:
    APP_DIR = Path(__file__).resolve().parent

DATA_DIR = APP_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"
CACHE_DIR = APP_DIR / "cache"
CONFIG_FILE = DATA_DIR / "disk_config.json"


def get_disk_config() -> Dict[str, Any]:
    """Load or initialize disk cleanup configuration."""
    default_cfg = {
        "auto_clean_after_dubbing": True,
        "clean_intermediate_wavs": True,
        "clean_scratch_voices": True,
        "clean_cache_scratch": True,
        "last_clean_timestamp": 0
    }
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_cfg.update(saved)
        except Exception:
            pass
    return default_cfg


def save_disk_config(cfg: Dict[str, Any]):
    """Save disk cleanup configuration."""
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def get_disk_free_stats() -> Dict[str, float]:
    """Get free and total space on the current application drive."""
    try:
        usage = shutil.disk_usage(str(APP_DIR))
        return {
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2)
        }
    except Exception:
        return {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0}


def scan_junk_files() -> Dict[str, Any]:
    """
    Safely scan for temporary intermediate audio files that can be freed without any harm.
    Target:
      - *.wav files in data/projects/** (original_audio, vocals, bgm)
      - temp/ folders in data/projects/**
      - voices/*.mp3 in completed projects (where final video exists)
      - scratch *.wav and temporary separation files in cache/
    """
    junk_files: List[Path] = []
    junk_dirs: List[Path] = []
    total_bytes = 0

    # 1. Projects folder scan
    if PROJECTS_DIR.exists():
        for proj_folder in PROJECTS_DIR.iterdir():
            if not proj_folder.is_dir():
                continue

            # A. All *.wav files in project folder
            for wav_f in proj_folder.glob("*.wav"):
                if wav_f.is_file():
                    try:
                        total_bytes += wav_f.stat().st_size
                        junk_files.append(wav_f)
                    except Exception:
                        pass

            # B. Project temp folder
            temp_dir = proj_folder / "temp"
            if temp_dir.exists() and temp_dir.is_dir():
                junk_dirs.append(temp_dir)
                for f in temp_dir.rglob("*"):
                    if f.is_file():
                        try:
                            total_bytes += f.stat().st_size
                            junk_files.append(f)
                        except Exception:
                            pass

            # C. Check if project is completed (has final video or export)
            has_final_video = (proj_folder / "final_dubbed_video.mp4").exists() or \
                              len(list(proj_folder.glob("*.mp4"))) > 0 or \
                              proj_folder.name.startswith("batch_")
            
            # If completed, voices folder individual sentence mp3s are safe to purge
            voices_dir = proj_folder / "voices"
            if has_final_video and voices_dir.exists() and voices_dir.is_dir():
                for vf in voices_dir.glob("*.mp3"):
                    if vf.is_file():
                        try:
                            total_bytes += vf.stat().st_size
                            junk_files.append(vf)
                        except Exception:
                            pass

    # 2. Cache folder scan
    if CACHE_DIR.exists():
        # Clean scratch WAVs in cache
        for cw in CACHE_DIR.glob("*.wav"):
            if cw.is_file():
                try:
                    total_bytes += cw.stat().st_size
                    junk_files.append(cw)
                except Exception:
                    pass

        # Clean audio separation scratch
        sep_dir = CACHE_DIR / "audio_separation"
        if sep_dir.exists() and sep_dir.is_dir():
            junk_dirs.append(sep_dir)
            for f in sep_dir.rglob("*"):
                if f.is_file():
                    try:
                        total_bytes += f.stat().st_size
                        junk_files.append(f)
                    except Exception:
                        pass

        # Clean audio_cache scratch
        ac_dir = CACHE_DIR / "audio_cache"
        if ac_dir.exists() and ac_dir.is_dir():
            junk_dirs.append(ac_dir)
            for f in ac_dir.rglob("*"):
                if f.is_file():
                    try:
                        total_bytes += f.stat().st_size
                        junk_files.append(f)
                    except Exception:
                        pass

    stats = get_disk_free_stats()
    cfg = get_disk_config()

    return {
        "success": True,
        "junk_files_count": len(junk_files),
        "total_junk_bytes": total_bytes,
        "total_junk_mb": round(total_bytes / (1024 * 1024), 2),
        "total_junk_gb": round(total_bytes / (1024 ** 3), 2),
        "free_disk_gb": stats["free_gb"],
        "total_disk_gb": stats["total_gb"],
        "auto_clean_enabled": cfg.get("auto_clean_after_dubbing", True),
        "_files_list": junk_files,
        "_dirs_list": junk_dirs
    }


def execute_disk_cleanup() -> Dict[str, Any]:
    """
    Executes 1-click safe cleanup.
    Deletes temporary scratch audio while ensuring 100% preservation of:
    - User license keys & registration history
    - Exported videos in data/exports and custom folders
    - Subtitle files (*.srt, *.ass)
    - Application code, ffmpeg, models
    """
    scan_res = scan_junk_files()
    files_to_delete = scan_res.get("_files_list", [])
    dirs_to_clean = scan_res.get("_dirs_list", [])

    deleted_count = 0
    freed_bytes = 0

    # Delete junk files
    for fp in files_to_delete:
        try:
            if fp.exists() and fp.is_file():
                sz = fp.stat().st_size
                fp.unlink()
                deleted_count += 1
                freed_bytes += sz
        except Exception:
            pass

    # Clean empty junk dirs
    for dp in dirs_to_clean:
        try:
            if dp.exists() and dp.is_dir():
                shutil.rmtree(str(dp), ignore_errors=True)
        except Exception:
            pass

    # Clean empty project folders if any batch projects have 0 files left
    if PROJECTS_DIR.exists():
        for p in PROJECTS_DIR.iterdir():
            if p.is_dir() and p.name.startswith("batch_"):
                try:
                    remaining = list(p.iterdir())
                    if len(remaining) == 0:
                        p.rmdir()
                except Exception:
                    pass

    # Record clean timestamp
    import time
    cfg = get_disk_config()
    cfg["last_clean_timestamp"] = int(time.time())
    save_disk_config(cfg)

    new_stats = get_disk_free_stats()

    return {
        "success": True,
        "files_removed": deleted_count,
        "freed_bytes": freed_bytes,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        "freed_gb": round(freed_bytes / (1024 ** 3), 2),
        "free_disk_gb_now": new_stats["free_gb"],
        "total_disk_gb": new_stats["total_gb"]
    }


def cleanup_single_project_cache(project_dir: Path):
    """
    Called immediately after a video finishes rendering.
    Safely purges the huge *.wav files and temporary frames for this specific project.
    """
    cfg = get_disk_config()
    if not cfg.get("auto_clean_after_dubbing", True):
        return

    if not project_dir.exists() or not project_dir.is_dir():
        return

    try:
        # 1. Purge *.wav files in project dir
        for wf in project_dir.glob("*.wav"):
            try:
                if wf.is_file():
                    wf.unlink()
            except Exception:
                pass

        # 2. Purge temp dir
        t_dir = project_dir / "temp"
        if t_dir.exists() and t_dir.is_dir():
            shutil.rmtree(str(t_dir), ignore_errors=True)

        # 3. Purge individual sentence voices if final video exists
        if (project_dir / "final_dubbed_video.mp4").exists():
            v_dir = project_dir / "voices"
            if v_dir.exists() and v_dir.is_dir():
                shutil.rmtree(str(v_dir), ignore_errors=True)
    except Exception as e:
        print(f"[AutoClean Note] {e}")


if __name__ == "__main__":
    print("Testing Disk Cleaner scan...")
    res = scan_junk_files()
    print(f"Found {res['junk_files_count']} files, {res['total_junk_gb']} GB junk.")
    print(f"Free disk space: {res['free_disk_gb']} GB / {res['total_disk_gb']} GB")
