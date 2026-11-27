"""
SN TOOL - Safe Disk Cleaner & Post-Dubbing Scratch Auto-Purge Engine.
Automatically cleans intermediate WAV/PCM/scratch TTS line clips after export
while preserving user exports, project metadata, configs, catalogs, and license.key.
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

if getattr(sys, "frozen", False):
    APP_DIR = Path(os.path.dirname(sys.executable))
else:
    APP_DIR = Path(__file__).resolve().parent

DEFAULT_DISK_CONFIG: Dict[str, Any] = {
    "auto_clean_after_dubbing": True,
    "clean_intermediate_wavs": True,
    "clean_scratch_voices": True,
    "clean_cache_scratch": True,
    "last_clean_timestamp": 0,
}

_ACTIVE_GRACE_SECONDS = 300


def _get_config_path() -> Path:
    return APP_DIR / "data" / "disk_config.json"


def get_disk_config() -> Dict[str, Any]:
    """Load disk cleanup configuration from data/disk_config.json with safe defaults."""
    cfg = dict(DEFAULT_DISK_CONFIG)
    for cand in (_get_config_path(), Path("data/disk_config.json")):
        if cand.exists():
            try:
                loaded = json.loads(cand.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    cfg.update(loaded)
                return cfg
            except Exception:
                pass
    return cfg


def save_disk_config(cfg: Dict[str, Any]) -> bool:
    """Persist disk cleanup preferences atomically."""
    p = _get_config_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        merged = dict(DEFAULT_DISK_CONFIG)
        merged.update(cfg or {})
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(p)
        return True
    except Exception:
        return False


def _remove_file_if_possible(path: Path) -> int:
    try:
        sz = path.stat().st_size if path.exists() else 0
        path.unlink(missing_ok=True)
        return sz
    except Exception:
        return 0


def _prune_empty_dirs(root_dir: Path) -> None:
    if not root_dir.exists():
        return
    for d in sorted((x for x in root_dir.rglob("*") if x.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            if not any(d.iterdir()):
                d.rmdir()
        except Exception:
            pass


def cleanup_single_project_cache(project_dir: Union[str, Path]) -> Dict[str, Any]:
    """Remove intermediate WAVs, voice line clips, and temp scratch artifacts inside one project folder."""
    cfg = get_disk_config()
    if not cfg.get("auto_clean_after_dubbing", True):
        return {"success": True, "skipped": True, "files_removed": 0, "freed_mb": 0.0}

    p_dir = Path(project_dir)
    if not p_dir.exists() or not p_dir.is_dir():
        return {"success": True, "files_removed": 0, "freed_mb": 0.0}

    clean_wavs = bool(cfg.get("clean_intermediate_wavs", True))
    clean_voices = bool(cfg.get("clean_scratch_voices", True))
    removed_bytes = 0
    removed_files = 0

    for f in list(p_dir.rglob("*")):
        if not f.is_file():
            continue
        name_low = f.name.lower()
        ext_low = f.suffix.lower()
        in_voices = any(part.lower() in ("voices", "temp") for part in f.relative_to(p_dir).parts[:-1])

        should_delete = False
        if clean_wavs and ext_low in (".wav", ".tmp", ".part"):
            should_delete = True
        elif clean_voices and (
            in_voices
            or (name_low.startswith("line_") and ext_low == ".mp3")
            or name_low == "mixed_dubbed_audio.mp3"
        ):
            should_delete = True

        if should_delete:
            sz = _remove_file_if_possible(f)
            if not f.exists():
                removed_bytes += sz
                removed_files += 1

    for sub in ("voices", "temp"):
        sub_p = p_dir / sub
        if sub_p.exists():
            _prune_empty_dirs(sub_p)
            try:
                if not any(sub_p.iterdir()):
                    sub_p.rmdir()
            except Exception:
                pass

    return {
        "success": True,
        "files_removed": removed_files,
        "freed_mb": round(removed_bytes / (1024 * 1024), 2),
    }


def _collect_junk_candidates(min_age_seconds: int = _ACTIVE_GRACE_SECONDS) -> List[Path]:
    """Collect safe-to-purge scratch WAVs, intermediate voice clips, temp caches, and old download partials."""
    cfg = get_disk_config()
    now_t = time.time()
    candidates: List[Path] = []

    projects_root = APP_DIR / "data" / "projects"
    if projects_root.exists():
        for f in projects_root.rglob("*"):
            if not f.is_file():
                continue
            try:
                st = f.stat()
                if min_age_seconds > 0 and (now_t - st.st_mtime) < min_age_seconds:
                    continue
            except Exception:
                continue

            name_low = f.name.lower()
            ext_low = f.suffix.lower()
            rel_parts = [p.lower() for p in f.relative_to(projects_root).parts]
            in_scratch_sub = any(p in ("voices", "temp") for p in rel_parts[1:-1])

            if cfg.get("clean_intermediate_wavs", True) and ext_low in (".wav", ".tmp", ".part"):
                candidates.append(f)
            elif cfg.get("clean_scratch_voices", True) and (
                in_scratch_sub
                or (name_low.startswith("line_") and ext_low == ".mp3")
                or name_low == "mixed_dubbed_audio.mp3"
            ):
                candidates.append(f)

    if cfg.get("clean_cache_scratch", True):
        for cache_root in (
            APP_DIR / "cache" / "audio_cache",
            APP_DIR / "cache" / "audio_separation",
            APP_DIR / "data" / "cache" / "update",
        ):
            if not cache_root.exists():
                continue
            for f in cache_root.rglob("*"):
                if not f.is_file():
                    continue
                try:
                    if min_age_seconds > 0 and (now_t - f.stat().st_mtime) < min_age_seconds:
                        continue
                except Exception:
                    continue
                if f.suffix.lower() in (".wav", ".mp3", ".mp4", ".tmp", ".part", ".zip"):
                    candidates.append(f)

    return candidates


def scan_junk_files() -> Dict[str, Any]:
    """Report recoverable temporary scratch disk usage without deleting any files."""
    cfg = get_disk_config()
    cands = _collect_junk_candidates(min_age_seconds=0)
    total_bytes = 0
    for f in cands:
        try:
            total_bytes += f.stat().st_size
        except Exception:
            pass

    usage = shutil.disk_usage(str(APP_DIR))
    return {
        "success": True,
        "junk_files_count": len(cands),
        "total_junk_mb": round(total_bytes / (1024 * 1024), 2),
        "total_junk_gb": round(total_bytes / (1024 ** 3), 3),
        "free_disk_gb": round(usage.free / (1024 ** 3), 2),
        "total_disk_gb": round(usage.total / (1024 ** 3), 2),
        "auto_clean_enabled": bool(cfg.get("auto_clean_after_dubbing", True)),
    }


def execute_disk_cleanup() -> Dict[str, Any]:
    """Delete recoverable temporary scratch files and report recovered disk space."""
    cands = _collect_junk_candidates(min_age_seconds=_ACTIVE_GRACE_SECONDS)
    freed_bytes = 0
    removed_count = 0

    for f in cands:
        sz = _remove_file_if_possible(f)
        if not f.exists():
            freed_bytes += sz
            removed_count += 1

    _prune_empty_dirs(APP_DIR / "data" / "projects")

    cfg = get_disk_config()
    cfg["last_clean_timestamp"] = int(time.time())
    save_disk_config(cfg)

    usage = shutil.disk_usage(str(APP_DIR))
    return {
        "success": True,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
        "freed_gb": round(freed_bytes / (1024 ** 3), 3),
        "files_removed": removed_count,
        "free_disk_gb_now": round(usage.free / (1024 ** 3), 2),
    }
