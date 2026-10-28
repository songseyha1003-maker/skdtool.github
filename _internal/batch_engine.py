"""
Automated Batch & Folder Auto-Dubbing Engine
Processes entire folders of drama episodes end-to-end with zero manual typing.
"""
import sys
import os
import re
import shutil
import asyncio
import threading
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pipeline import ProjectManager
from audio_processor import extract_audio_from_video, get_media_duration
from stt_engine import SpeechToTextEngine
from translator import DramaTranslator
from tts_engine import batch_synthesize
from vocal_remover import separate_vocals_and_bgm
from audio_processor import mix_dubbed_audio
from video_processor import render_dubbed_video

EXPORTS_DIR = Path("data/exports")
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_export_path(p_str: Optional[str]) -> Optional[str]:
    """
    Cleans up any recursive or overly-nested folder chains like:
    D:/SN_Dramas/封神殿/Drama_Series/东北话事人/封神殿/Dubbed/封神殿/Drama_Series
    Truncates at the first authentic drama folder level (e.g. D:/SN_Dramas/封神殿).
    Ensures zero nested subfolders (no /Dubbed_Khmer, no /Drama_Series, no duplicate names).
    """
    if not p_str or not str(p_str).strip():
        return None
    raw = str(p_str).strip().replace('\\', '/').rstrip('/')
    if re.match(r'^[a-zA-Z]:/?$', raw):
        return raw if raw.endswith('/') else raw + '/'

    parts = [pt for pt in raw.split('/') if pt]
    if not parts:
        return None

    cleaned_parts = []
    seen_lower = set()

    ROOT_CONTAINERS = {'sn_dramas', 'dramas', 'exports', 'data', 'downloads', 'my_dramas'}
    JUNK_TOKENS = {'dubbed', 'dubbed_khmer', 'dubbed_khmer_full_movie', 'temp', 'batch_temp', 'uploads', 'cache'}

    for idx, part in enumerate(parts):
        part_clean = part.strip()
        if not part_clean:
            continue
        p_lower = part_clean.lower()

        if p_lower in JUNK_TOKENS:
            break

        if (p_lower in ('drama_series', 'full_movie', 'video')) and len(cleaned_parts) >= 2:
            break

        if p_lower in seen_lower and p_lower not in ROOT_CONTAINERS and not re.match(r'^[a-zA-Z]:$', part_clean):
            break

        cleaned_parts.append(part_clean)
        if not re.match(r'^[a-zA-Z]:$', part_clean):
            seen_lower.add(p_lower)

        if len(cleaned_parts) >= 3 and cleaned_parts[1].lower() in ROOT_CONTAINERS:
            break

    if not cleaned_parts:
        return None
    if re.match(r'^[a-zA-Z]:$', cleaned_parts[0]):
        if len(cleaned_parts) == 1:
            return cleaned_parts[0] + '/'
        return cleaned_parts[0] + '/' + '/'.join(cleaned_parts[1:])
    return '/'.join(cleaned_parts)


def extract_clean_series_name(raw_title: str) -> str:
    """
    Extracts authentic drama series title by stripping episode numbers, parts, and noise.
    Example:
      'Your_Majesty__Are_You_in_Love_Today_EP001.mp4' -> 'Your_Majesty__Are_You_in_Love_Today'
      'Dubbed_Your_Majesty__Are_You_in_Love_Today_EP002' -> 'Your_Majesty__Are_You_in_Love_Today'
      'Drama_Episode_12' -> 'Drama'
      'Story_第01集' -> 'Story'
      'EP001' -> '' (falls back to parent folder name)
    """
    if not raw_title:
        return ""
    t = str(raw_title).strip()
    t = re.sub(r'(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'^(?:Dubbed_|Raw_Full_Movie_)+', '', t, flags=re.IGNORECASE)
    t = re.sub(r'_\d{9,12}$', '', t)
    t = re.sub(r'_Full_Movie.*$', '', t, flags=re.IGNORECASE)
    # Strip episode markers anywhere near the end (e.g. _EP001, -EP01, .E05, _Episode_12, _Part_3, 第01集)
    t = re.sub(r'(?i)(?:[-_.\s]+(?:ep|episode|part|e|vol|ch|seq|第)[-_.\s]*\d+.*|\b(?:ep|episode|part)[-_.\s]*\d+.*|第\s*\d+\s*[集話部].*)', '', t)
    # Strip trailing pure episode numbers like _01, _001, -05, but preserve 4-digit release years (19xx, 20xx)
    def _strip_ep_num(m):
        num_str = m.group(1)
        if len(num_str) == 4 and (num_str.startswith('19') or num_str.startswith('20')):
            return m.group(0)
        return ''
    t = re.sub(r'[-_.\s]+(\d{1,4})$', _strip_ep_num, t)
    # If the title was strictly just an episode tag (e.g. EP001 or Episode 10), strip it so fallback kicks in
    t = re.sub(r'(?i)^(?:ep|episode|part|第)?[-_.\s]*\d+.*$', '', t)
    return t.strip('_ -.')


def consolidate_scattered_episode_folders(target_drama_dir: Path, safe_title: str):
    """
    Consolidates previously scattered episode folders (e.g., from old version bug) into the unified drama folder.
    Moves .mp4 videos into target_drama_dir and removes empty scattered directories.
    """
    try:
        if not target_drama_dir or not safe_title or safe_title.lower() in ("drama_series", "full_movie", ""):
            return
        parent = target_drama_dir.parent
        if not parent or not parent.exists():
            return

        target_drama_dir.mkdir(parents=True, exist_ok=True)
        for folder in list(parent.iterdir()):
            try:
                if folder.is_dir() and folder.resolve() != target_drama_dir.resolve():
                    f_clean = extract_clean_series_name(folder.name)
                    if f_clean and f_clean.lower() == safe_title.lower():
                        # Sibling folder belongs to this drama series! Consolidate videos
                        for item in list(folder.iterdir()):
                            if item.is_file() and item.suffix.lower() in (".mp4", ".mkv", ".mov"):
                                dest_f = target_drama_dir / item.name
                                if not dest_f.exists() or dest_f.stat().st_size < item.stat().st_size:
                                    shutil.move(str(item), str(dest_f))
                                    print(f"[Consolidate] Moved {item.name} -> {target_drama_dir.name}")
                        # Remove if empty or only lingering temporary files
                        remaining = [x for x in folder.iterdir() if x.suffix.lower() in (".mp4", ".mkv", ".mov")]
                        if not remaining:
                            shutil.rmtree(str(folder), ignore_errors=True)
                            print(f"[Consolidate] Removed empty scattered folder: {folder.name}")
            except Exception:
                pass
    except Exception as ce:
        print(f"[Consolidate Folders Note] {ce}")


def resolve_drama_export_directories(in_path: str, drama_title: str, custom_export_dir: Optional[str] = None) -> List[Path]:
    """
    Resolves the single direct folder for exporting dubbed videos (strictly 1 unified folder, NO separate per-episode folders).
    1. If user chose a custom_export_dir: sanitizes it and exports directly into it (zero subfolders).
    2. If user did not choose:
       - Exports directly into D:/SN_Dramas/<DramaTitle> (or C:/SN_Dramas or data/exports/<DramaTitle>).
    """
    # Extract clean series name (strip episode suffixes like EP_01, Episode 12, etc.)
    clean_series = extract_clean_series_name(drama_title)

    generic_names = ("drama_series", "dubbed_drama_series_full_movie", "full_movie", "raw_full_movie", "")
    if not clean_series or clean_series.lower() in generic_names:
        # Check in_path for authentic drama folder name
        try:
            p_in = Path(in_path).resolve()
            if p_in.parent.name.lower() not in ("batch_temp", "uploads", "cache", "temp", "exports", "sn_dramas", "downloads", "data"):
                clean_series = extract_clean_series_name(p_in.parent.name) or p_in.parent.name
        except Exception:
            pass

    if not clean_series or clean_series.lower() in generic_names:
        clean_series = "Drama_Series"

    safe_title = re.sub(r'[\\/*?:"<>|《》【】「」『』\(\)\[\]]', '_', str(clean_series)).strip('_ ') or "Drama_Series"

    # 1. User-selected custom export folder takes absolute priority!
    sanitized_cust = sanitize_export_path(custom_export_dir)
    if sanitized_cust:
        try:
            p_cust = Path(sanitized_cust).resolve()
            # If user selected an exact folder (e.g. D:/MyFolder or D:/SN_Dramas/封神殿), export directly into it!
            # Only if user selected the bare root container itself (e.g. D:/SN_Dramas or C:/SN_Dramas or D:/), put it inside the drama title
            is_bare_root = p_cust.name.lower() in ("sn_dramas", "dramas") or len(p_cust.parts) <= 2
            if is_bare_root and safe_title and safe_title.lower() not in ("drama_series", "full_movie"):
                p_cust = p_cust / safe_title
            p_cust.mkdir(parents=True, exist_ok=True)
            consolidate_scattered_episode_folders(p_cust, safe_title)
            return [p_cust]
        except Exception as ce:
            print(f"[Export Folder] Custom folder note ({custom_export_dir}): {ce}")

    # 2. When user did NOT pick a folder:
    # Always create ONE unified dedicated folder for this drama series before dubbing!
    for root_str in ("D:/SN_Dramas", "C:/SN_Dramas"):
        root_p = Path(root_str)
        if root_p.exists():
            root_drama = root_p / safe_title
            root_drama.mkdir(parents=True, exist_ok=True)
            consolidate_scattered_episode_folders(root_drama, safe_title)
            return [root_drama]

    # Fallback to data/exports/<safe_title>
    export_drama_dir = EXPORTS_DIR / safe_title
    export_drama_dir.mkdir(parents=True, exist_ok=True)
    consolidate_scattered_episode_folders(export_drama_dir, safe_title)
    return [export_drama_dir]


class BatchDubbingManager:
    def __init__(self):
        self.pm = ProjectManager()
        self.stt = SpeechToTextEngine(model_size="base")
        self.translator = DramaTranslator()
        self.queue: List[Dict[str, Any]] = []
        self.is_processing = False
        self._lock = threading.Lock()

    def add_files_to_queue(
        self,
        file_paths: List[str],
        voice_mode: str = "piseth",  # 'piseth', 'sreymom', 'auto_multi'
        drama_mode: str = "drama_dubbing",  # 'drama_dubbing' or 'movie_recap'
        aspect_ratio: str = "16:9",
        burn_subtitles: bool = False,
        separate_bgm: bool = True,
        overlay_config: Optional[Dict[str, Any]] = None,
        custom_export_dir: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Add multiple video/audio files to the automated batch queue."""
        added_items = []
        for path_str in file_paths:
            p = Path(path_str)
            if not p.exists():
                continue

            item_id = str(uuid.uuid4())[:8]
            item = {
                "id": item_id,
                "filename": p.name,
                "filepath": str(p),
                "voice_mode": voice_mode,
                "drama_mode": drama_mode,
                "aspect_ratio": aspect_ratio,
                "burn_subtitles": burn_subtitles,
                "separate_bgm": separate_bgm,
                "overlay_config": overlay_config,
                "custom_export_dir": custom_export_dir,
                "status": "pending",  # pending, processing, completed, failed
                "step": "Waiting to start",  # transcribing, translating, synthesizing, rendering, done
                "progress": 0,
                "output_video": None,
                "error": None
            }
            with self._lock:
                self.queue.append(item)
            added_items.append(item)
        return added_items

    def get_queue_status(self) -> List[Dict[str, Any]]:
        """Return list of all batch items with their current progress."""
        with self._lock:
            return list(self.queue)

    def clear_completed(self):
        """Remove completed tasks from queue."""
        with self._lock:
            self.queue = [item for item in self.queue if item["status"] not in ("completed", "failed")]

    def start_batch_processing(self):
        """Trigger background worker thread to process queue."""
        if not self.is_processing:
            threading.Thread(target=self._process_worker, daemon=True).start()

    def _process_worker(self):
        self.is_processing = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Adapt concurrency based on available physical RAM to guarantee stability without OOM freezes
            try:
                from stt_engine import get_system_ram_gb
                total_ram = get_system_ram_gb()
            except Exception:
                total_ram = 8.0

            if total_ram >= 24.0:
                max_workers = 3
            elif total_ram >= 12.0:
                max_workers = 2
            else:
                max_workers = 1  # 8GB or budget PCs: run 1 episode at a time to prevent CPU freezing and crashes

            async def _worker_loop():
                while True:
                    target_item = None
                    with self._lock:
                        for item in self.queue:
                            if item["status"] == "pending":
                                item["status"] = "processing"
                                target_item = item
                                break

                    if not target_item:
                        break

                    try:
                        await self._process_single_item(target_item)
                    except Exception as e:
                        target_item["status"] = "failed"
                        target_item["error"] = str(e)
                        target_item["step"] = "Error"

            async def _run_all():
                tasks = [_worker_loop() for _ in range(max_workers)]
                await asyncio.gather(*tasks)

            loop.run_until_complete(_run_all())
            try:
                self._auto_merge_completed_series()
            except Exception as me:
                print(f"Post-batch auto-merge note: {me}")
        finally:
            self.is_processing = False
            loop.close()

    async def _process_single_item(self, item: Dict[str, Any]):
        """Run complete 1-click pipeline on one video file."""
        item_id = item["id"]
        in_path = item["filepath"]
        item_dir = Path(f"data/projects/batch_{item_id}")
        item_dir.mkdir(parents=True, exist_ok=True)

        # 0. Create dedicated drama export folder FIRST on disk before any work begins!
        try:
            p_in = Path(in_path)
            parent_folder = p_in.parent.name
            if parent_folder and parent_folder.lower() not in ("batch_temp", "uploads", "exports", "sn_dramas", "downloads", "data"):
                early_title = extract_clean_series_name(parent_folder) or parent_folder
            else:
                early_title = extract_clean_series_name(p_in.stem) or "Drama_Series"
            target_dirs = resolve_drama_export_directories(in_path, early_title, custom_export_dir=item.get("custom_export_dir"))
            if target_dirs:
                target_dirs[0].mkdir(parents=True, exist_ok=True)
                print(f"[AutoFolder] Created drama folder on disk BEFORE dubbing: {target_dirs[0]}")
        except Exception as fe:
            print(f"[AutoFolder Init Note] {fe}")

        # 1. Extract Audio
        item["step"] = "1/5 Extracting audio from video..."
        item["progress"] = 15
        raw_audio = item_dir / "audio.wav"
        extract_audio_from_video(in_path, str(raw_audio))
        duration = get_media_duration(in_path)

        # 2. Vocal Separation if enabled
        bgm_track = str(raw_audio)
        if item.get("separate_bgm", True):
            item["step"] = "2/5 AI separating vocals & preserving BGM bed..."
            item["progress"] = 30
            try:
                bgm_out, _ = separate_vocals_and_bgm(str(raw_audio), output_dir=str(item_dir))
                bgm_track = bgm_out
            except Exception as e:
                print(f"Vocal separation fallback: {e}")

        # 3. Speech-to-Text (Auto Transcribe with Subtitle Extraction check)
        item["step"] = "3/5 AI transcribing speech (Faster-Whisper)..."
        item["progress"] = 45
        dialogues = self.stt.transcribe_audio(str(raw_audio), source_lang="auto", video_path=in_path)
        if not dialogues:
            dialogues = [{
                "id": 1,
                "start": 0.5,
                "end": max(3.0, duration - 0.5),
                "speaker": "Character",
                "text": "Drama video dialogue",
                "text_original": "Drama video dialogue"
            }]

        # 4. Contextual Drama/Recap Translation into Khmer with Series Bible Memory
        v_override = item["voice_mode"] if item.get("voice_mode") not in (None, "", "auto") else "piseth"
        v_override = str(v_override).lower().strip()
        is_multi = v_override in ("multi", "auto_multi")
        if is_multi:
            v_label = "Piseth & Sreymom (Dual Voice)"
        elif v_override == "sreymom":
            v_label = "Sreymom (Female Solo)"
        else:
            v_label = "Piseth (Male Solo)"

        # Infer drama series title and episode number from path and filename
        p_in = Path(in_path)
        raw_stem = p_in.stem
        ep_matches = re.findall(r'(?i)(?:EP|Episode|Part|第)?[\s_\-]*(\d+)', raw_stem)
        ep_num = int(ep_matches[-1]) if ep_matches else 1

        parent_folder = p_in.parent.name
        if parent_folder and parent_folder.lower() not in ("batch_temp", "uploads", "exports", "sn_dramas", "downloads"):
            drama_title = parent_folder
        else:
            clean_title = re.sub(r'(?i)(?:EP|Episode|Part|第)?[\s_\-]*\d+[\s_\-]*(?:集|話|部)?', '', raw_stem)
            clean_title = re.sub(r'[\s_\-]+', '_', clean_title).strip('_ ')
            drama_title = clean_title or "Drama_Series"

        total_batch_lines = len(dialogues)
        def on_batch_trans(completed: int, total: int, msg: str = ""):
            pct = 50 + int((completed / max(1, total)) * 25)
            item["progress"] = min(75, max(50, pct))
            item["step"] = f"៤/៥ AI កំពុងបកប្រែសាច់រឿង ({completed}/{total} ឃ្លា - {item['progress']}%)..."

        item["step"] = f"៤/៥ AI កំពុងបកប្រែសាច់រឿង {v_label} (0/{total_batch_lines} ឃ្លា)..."
        item["progress"] = 50
        translated_dialogues = await self.translator.translate_dialogues(
            dialogues=dialogues,
            mode=item["drama_mode"],
            source_lang="auto",
            target_voice_override=v_override,
            drama_title=drama_title,
            episode_number=ep_num,
            progress_callback=on_batch_trans
        )

        # Record this episode's summary into the series memory
        try:
            from series_memory import series_memory
            series_memory.record_episode_summary(drama_title, ep_num, translated_dialogues)
        except Exception as e:
            print(f"Record episode summary note: {e}")

        # 5. Batch TTS Synthesis
        item["step"] = f"5/5 Synthesizing audio {v_label} & Rendering..."
        item["progress"] = 80
        voices_dir = item_dir / "voices"
        def on_batch_tts(completed: int, total: int, itm: Dict[str, Any]):
            item["progress"] = 80 + int((completed / max(1, total)) * 10)
            item["step"] = f"5/5 Synthesizing audio ({completed}/{total} lines)..."

        synthesized_items = await batch_synthesize(
            translated_dialogues,
            output_dir=str(voices_dir),
            default_voice="piseth" if is_multi else v_override,
            progress_callback=on_batch_tts
        )

        # Verify and recover any synthesized voices to ensure 100% audible speech
        from tts_engine import is_valid_audible_audio, synthesize_via_google_khmer_api
        for idx, d in enumerate(synthesized_items):
            af = d.get("audio_file")
            if not is_valid_audible_audio(af):
                txt = (d.get("text_km") or d.get("text", "")).strip()
                v = d.get("voice") or v_override or "piseth"
                fix_out = voices_dir / f"line_recovered_{idx:04d}_{os.urandom(3).hex()}.mp3"
                new_af = synthesize_via_google_khmer_api(txt, v, str(fix_out))
                if new_af and is_valid_audible_audio(new_af):
                    d["audio_file"] = new_af

        # Mix Audio with BGM volume and Speech Boost from story settings
        mixed_audio = item_dir / "dubbed_mixed.mp3"
        cfg_duck = 0.12
        cfg_boost = 3.5
        try:
            cfg_p = Path("data/story_config.json")
            if cfg_p.exists():
                with open(cfg_p, "r", encoding="utf-8") as f:
                    _c = json.load(f)
                    cfg_duck = float(_c.get("ducking_volume", 0.15))
                    cfg_boost = float(_c.get("speech_boost_db", 3.5))
        except Exception:
            pass

        mix_dubbed_audio(
            original_audio_path=bgm_track,
            dialogue_items=synthesized_items,
            output_mixed_path=str(mixed_audio),
            total_duration_sec=duration,
            ducking_volume_factor=cfg_duck,
            speech_volume_boost_db=cfg_boost,
            dubbing_mode="smart_bgm"
        )

        # 6. Render and Save all drama files in ONE UNIFIED FOLDER
        custom_export_dir = item.get("custom_export_dir")
        target_dirs = resolve_drama_export_directories(in_path, drama_title, custom_export_dir=custom_export_dir)
        primary_dir = target_dirs[0]
        clean_in_stem = re.sub(r'^(?:Dubbed_)+', '', p_in.stem, flags=re.IGNORECASE)
        clean_in_stem = re.sub(r'(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$', '', clean_in_stem, flags=re.IGNORECASE)
        clean_in_stem = re.sub(r'[\\/*?:"<>|]', '_', clean_in_stem).strip('. ') or "Video"
        out_filename = f"Dubbed_{clean_in_stem}.mp4"
        final_video_path = primary_dir / out_filename
        
        render_dubbed_video(
            original_video_path=in_path,
            mixed_audio_path=str(mixed_audio),
            output_video_path=str(final_video_path),
            dialogues=synthesized_items,
            burn_subtitles=item.get("burn_subtitles", False),
            aspect_ratio=item.get("aspect_ratio", "16:9"),
            overlay_config=item.get("overlay_config"),
            temp_dir=str(item_dir / "temp")
        )

        # Mirror video to secondary folders if any (export only clean .mp4 videos, zero extra files)
        try:
            import shutil
            for td in target_dirs:
                if td.resolve() != primary_dir.resolve() and final_video_path.exists():
                    shutil.copy2(str(final_video_path), str(td / out_filename))
        except Exception as se:
            print(f"Folder mirror note: {se}")

        item["progress"] = 100
        item["status"] = "completed"
        item["step"] = "100% Completed"
        item["output_video"] = str(final_video_path)
        item["drama_folder"] = str(primary_dir.resolve()).replace("\\", "/")

        # Auto-clean temporary scratch files for this batch item
        try:
            from disk_cleaner import cleanup_single_project_cache
            cleanup_single_project_cache(item_dir)
        except Exception as cln_err:
            print(f"[Batch AutoClean Note] {cln_err}")


    def _auto_merge_completed_series(self):
        """Automatically merge completed episodes of a series into a single Full Movie (1-2 hours) in the drama folder."""
        import shutil
        series_groups: Dict[str, List[Path]] = {}
        with self._lock:
            for item in self.queue:
                if item["status"] == "completed" and item.get("output_video"):
                    out_p = Path(item["output_video"])
                    if out_p.exists():
                        stem = out_p.stem.replace("Dubbed_", "")
                        series_name = re.sub(r'(?i)(?:EP|Episode|Part|第)?[\s_\-]*\d+[\s_\-]*(?:集|話|部)?', '', stem)
                        series_name = re.sub(r'[\s_\-]+', '_', series_name).strip('_ ') or "Drama_Series"
                        if series_name not in series_groups:
                            series_groups[series_name] = []
                        if out_p not in series_groups[series_name]:
                            series_groups[series_name].append(out_p)

        for s_name, ep_paths in series_groups.items():
            if len(ep_paths) >= 2:
                def _get_ep(p):
                    m = re.findall(r'\d+', p.stem)
                    return int(m[-1]) if m else 0
                ep_paths.sort(key=_get_ep)

                # Save Full Movie directly in the drama's own folder where the episodes live
                first_dir = ep_paths[0].parent
                full_movie_name = f"Full_Movie_{s_name}_Khmer.mp4"
                full_movie_out = first_dir / full_movie_name

                if not full_movie_out.exists() or full_movie_out.stat().st_size < 1000:
                    try:
                        from video_processor import merge_videos
                        merge_videos([str(p) for p in ep_paths], str(full_movie_out), auto_trim_freeze=True)
                        print(f"[OK] Full Drama Series Movie merged in drama folder: {full_movie_out} ({len(ep_paths)} episodes)")

                        # Also mirror to data/exports/{s_name}/
                        export_mirror = EXPORTS_DIR / s_name / full_movie_name
                        export_mirror.parent.mkdir(parents=True, exist_ok=True)
                        if export_mirror.resolve() != full_movie_out.resolve():
                            shutil.copy2(str(full_movie_out), str(export_mirror))
                    except Exception as e:
                        print(f"Series auto-merge note: {e}")


# Global singleton instance
batch_manager = BatchDubbingManager()

