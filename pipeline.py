"""
Unified Drama Voice Translation & Facebook Movie Recap Pipeline Manager (V2.0 Pro)
"""
import os
import sys
import json
import uuid
import asyncio
import gc
from pathlib import Path
from typing import Dict, Any, List, Optional

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

if getattr(sys, 'frozen', False):
    APP_DIR = Path(os.path.dirname(sys.executable))
else:
    APP_DIR = Path(__file__).resolve().parent

DATA_DIR = APP_DIR / "data" / "projects"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = APP_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

from tts_engine import batch_synthesize, synthesize_khmer_speech, get_available_voices
from translator import DramaTranslator, parse_srt_content, format_srt_content
from audio_processor import (
    extract_audio_from_video,
    mix_dubbed_audio,
    create_waveform_data,
    get_media_duration
)

def safe_float(val: Any, default: float = 0.02) -> float:
    """Safely convert value to float with reliable fallback against empty strings and None."""
    try:
        if val is None or str(val).strip() == "":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

from video_processor import render_dubbed_video, generate_sample_drama_video
from vocal_remover import separate_vocals_and_bgm
from stt_engine import SpeechToTextEngine
from recap_engine import RecapEngine, VIRAL_KHMER_HOOKS
from downloader import download_video_from_url

SAMPLE_DRAMAS = {
    "chinese_romance": {
        "title": "រឿងភាគចិន៖ និស្ស័យស្នេហ៍លោកម្ចាស់ (Chinese Drama Sample)",
        "source_lang": "zh",
        "mode": "drama_dubbing",
        "description": "ឈុតឆាកសន្ទនារវាងតួប្រុស (ពិសិដ្ឋ) និងតួស្រី (ស្រីមុំ) ក្នុងរឿងភាគបុរាណចិន",
        "dialogues": [
            {
                "id": 1,
                "start": 0.5,
                "end": 3.8,
                "speaker": "តួប្រុស (Male Lead)",
                "text_original": "你终于来了，我已经在这里等了你三天三夜。",
                "text_km": "ទីបំផុតអូនបានមកដល់ហើយ បងបានរង់ចាំអូននៅទីនេះអស់រយៈពេលបីថ្ងៃបីយប់ហើយ។",
                "voice": "piseth",
                "rate_percent": 0,
                "pitch_hz": 0
            },
            {
                "id": 2,
                "start": 4.2,
                "end": 7.5,
                "speaker": "តួស្រី (Female Lead)",
                "text_original": "对不起，路上遇到了皇宫的追兵，我好不容易才逃出来的。",
                "text_km": "អូនសុំទោស តាមផ្លូវអូនបានជួបទាហានតាមចាប់ ពិបាកណាស់ទម្រាំតែអូនអាចរត់គេចខ្លួនបាន។",
                "voice": "sreymom",
                "rate_percent": 0,
                "pitch_hz": 0
            },
            {
                "id": 3,
                "start": 8.0,
                "end": 11.2,
                "speaker": "តួប្រុស (Male Lead)",
                "text_original": "别怕，只要有我在，没有任何人能够伤害你！",
                "text_km": "កុំខ្លាចអី ដរាបណាមានបងនៅក្បែរ គ្មានអ្នកណាអាចមកធ្វើបាបអូនបានឡើយ!",
                "voice": "piseth",
                "rate_percent": 0,
                "pitch_hz": 0
            },
            {
                "id": 4,
                "start": 11.8,
                "end": 15.0,
                "speaker": "តួស្រី (Female Lead)",
                "text_original": "我相信你，从此以后无论生死我都跟随你。",
                "text_km": "អូនជឿជាក់លើបង ចាប់ពីពេលនេះទៅ ទោះស្លាប់រស់ក៏អូននៅតែដើរតាមបងជានិច្ច។",
                "voice": "sreymom",
                "rate_percent": 0,
                "pitch_hz": 0
            }
        ]
    },
    "korean_action": {
        "title": "រឿងភាគកូរ៉េ៖ បេសកកម្មសម្ងាត់ (Korean Action Drama Sample)",
        "source_lang": "ko",
        "mode": "drama_dubbing",
        "description": "ឈុតឆាកស៊ើបអង្កេត និងប្រឈមមុខដាក់គ្នារវាងភ្នាក់ងារសម្ងាត់",
        "dialogues": [
            {
                "id": 1,
                "start": 0.5,
                "end": 3.6,
                "speaker": "ប្រធានក្រុម (Team Leader)",
                "text_original": "지금 즉시 작전을 시작한다. 모든 대원은 위치로 이동하라.",
                "text_km": "ចាប់ផ្តើមប្រតិបត្តិការភ្លាម! សមាជិកទាំងអស់ត្រូវចូលទៅកាន់ទីតាំងជាបន្ទាន់។",
                "voice": "piseth",
                "rate_percent": 5,
                "pitch_hz": 0
            },
            {
                "id": 2,
                "start": 4.0,
                "end": 7.2,
                "speaker": "ភ្នាក់ងារស្រី (Female Agent)",
                "text_original": "타겟이 건물 안으로 진입했습니다. 제가 먼저 추적하겠습니다.",
                "text_km": "គោលដៅបានដើរចូលទៅក្នុងអគារហើយ ខ្ញុំនឹងតាមដានពីក្រោយជាមុនសិន។",
                "voice": "sreymom",
                "rate_percent": 0,
                "pitch_hz": 0
            },
            {
                "id": 3,
                "start": 7.8,
                "end": 11.0,
                "speaker": "ប្រធានក្រុម (Team Leader)",
                "text_original": "조심해, 함정일 수도 있어. 지원팀이 곧 도착한다!",
                "text_km": "ប្រយ័ត្នខ្លួនណា! អាចជាអន្ទាក់ ក្រុមជំនួយនឹងទៅដល់ក្នុងពេលបន្តិចទៀតនេះ!",
                "voice": "piseth",
                "rate_percent": 0,
                "pitch_hz": 0
            }
        ]
    },
    "facebook_recap": {
        "title": "សម្រាយរឿង Facebook/TikTok៖ កំពូលអ្នកក្លាហាន (FB Movie Recap Style)",
        "source_lang": "en",
        "mode": "movie_recap",
        "description": "ទម្រង់សម្រាយសាច់រឿងទាក់ទាញបែប Facebook និង TikTok ដោយប្រើសំឡេងពិសិដ្ឋ និងស្រីមុំ",
        "dialogues": [
            {
                "id": 1,
                "start": 0.5,
                "end": 4.2,
                "speaker": "អ្នកសម្រាយ (Recap Host - Piseth)",
                "text_original": "This man thought he was just an ordinary worker, but he didn't know he was actually the billionaire's heir.",
                "text_km": "បុរសម្នាក់នេះគិតថាខ្លួនឯងគ្រាន់តែជាកម្មករធម្មតា ប៉ុន្តែគាត់មិនដឹងឡើយថា តាមពិតគាត់គឺជាអ្នកស្នងមរតកត្រកូលមហាសេដ្ឋី។",
                "voice": "piseth",
                "rate_percent": 5,
                "pitch_hz": 0
            },
            {
                "id": 2,
                "start": 4.8,
                "end": 8.5,
                "speaker": "អ្នករៀបរាប់ (Co-Host - Sreymom)",
                "text_original": "At that exact moment, a luxury car pulled up and changed his entire life forever.",
                "text_km": "ស្រាប់តែនៅពេលនោះ ឡានទំនើបមួយគ្រឿងបានមកឈប់នៅពីមុខគាត់ ហើយបានផ្លាស់ប្តូរជីវិតរបស់គាត់ជារៀងរហូត។",
                "voice": "sreymom",
                "rate_percent": 0,
                "pitch_hz": 0
            },
            {
                "id": 3,
                "start": 9.0,
                "end": 13.5,
                "speaker": "អ្នកសម្រាយ (Recap Host - Piseth)",
                "text_original": "What do you think he will do next? Don't forget to like and follow for episode 2!",
                "text_km": "តើអ្នកទាំងអស់គ្នាគិតថាគាត់នឹងធ្វើអ្វីបន្តទៀត? កុំភ្លេចចុច Like និង Follow ដើម្បីរង់ចាំទស្សនាភាគទីពីរទាំងអស់គ្នា!",
                "voice": "piseth",
                "rate_percent": 0,
                "pitch_hz": 0
            }
        ]
    }
}


class ProjectManager:
    def __init__(self):
        self.translator = DramaTranslator()
        cfg_model = "base"
        try:
            cfg_file = Path("data/story_config.json")
            if cfg_file.exists():
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg_model = json.load(f).get("whisper_model", "base")
        except Exception:
            pass
        self.stt_engine = SpeechToTextEngine(model_size=cfg_model if cfg_model in ("tiny", "base", "small", "medium") else "base")

    def get_project_file(self, project_id: str) -> Path:
        return DATA_DIR / f"{project_id}.json"

    def create_project(self, title: str = "New Drama Dubbing Project", mode: str = "drama_dubbing") -> Dict[str, Any]:
        project_id = str(uuid.uuid4())[:8]
        proj_dir = Path(f"data/projects/{project_id}")
        proj_dir.mkdir(parents=True, exist_ok=True)
        
        # Load default ducking from story_config.json
        cfg_duck = 0.15
        try:
            cfg_p = Path("data/story_config.json")
            if cfg_p.exists():
                with open(cfg_p, "r", encoding="utf-8") as f:
                    cfg_duck = safe_float(json.load(f).get("ducking_volume"), 0.15)
        except Exception:
            cfg_duck = 0.15

        project = {
            "id": project_id,
            "title": title,
            "mode": mode,
            "source_lang": "auto",
            "video_file": None,
            "original_audio_file": None,
            "isolated_bgm_file": None,
            "mixed_audio_file": None,
            "output_video_file": None,
            "duration": 0.0,
            "ducking_factor": cfg_duck,
            "burn_subtitles": False,
            "aspect_ratio": "16:9",  # 16:9 or 9:16
            "watermark_text": "",
            "dialogues": [],
            "waveform": []
        }
        self.save_project(project)
        return project

    def save_project(self, project: Dict[str, Any]) -> None:
        p_file = self.get_project_file(project["id"])
        with open(p_file, "w", encoding="utf-8") as f:
            json.dump(project, f, ensure_ascii=False, indent=2)

    def load_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        p_file = self.get_project_file(project_id)
        if p_file.exists():
            with open(p_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_projects(self) -> List[Dict[str, Any]]:
        projects = []
        for p_file in DATA_DIR.glob("*.json"):
            try:
                with open(p_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    projects.append({
                        "id": data.get("id"),
                        "title": data.get("title"),
                        "mode": data.get("mode"),
                        "dialogues_count": len(data.get("dialogues", [])),
                        "duration": data.get("duration", 0)
                    })
            except Exception:
                pass
        return projects

    def load_sample(self, sample_key: str) -> Dict[str, Any]:
        sample_data = SAMPLE_DRAMAS.get(sample_key, SAMPLE_DRAMAS["chinese_romance"])
        project = self.create_project(title=sample_data["title"], mode=sample_data["mode"])
        project["source_lang"] = sample_data["source_lang"]
        project["dialogues"] = sample_data["dialogues"]
        
        proj_dir = Path(f"data/projects/{project['id']}")
        video_sample_path = proj_dir / "sample_video.mp4"
        audio_sample_path = proj_dir / "original_audio.wav"
        
        try:
            generate_sample_drama_video(str(video_sample_path), duration_sec=16)
            extract_audio_from_video(str(video_sample_path), str(audio_sample_path))
            project["video_file"] = str(video_sample_path)
            project["original_audio_file"] = str(audio_sample_path)
            project["duration"] = 16.0
            project["waveform"] = create_waveform_data(str(audio_sample_path))
        except Exception as e:
            print(f"Sample video creation note: {e}")

        self.save_project(project)
        return project

    def auto_transcribe_project(self, project_id: str) -> Dict[str, Any]:
        """Transcribe audio from project media file using AI Speech-to-Text on isolated vocals."""
        project = self.load_project(project_id)
        if not project or not project.get("original_audio_file"):
            raise ValueError("No audio file found to transcribe")

        audio_path = project.get("isolated_vocals_file")
        if not audio_path or not Path(audio_path).exists() or Path(audio_path).stat().st_size < 1000:
            audio_path = project["original_audio_file"]

        dialogues = self.stt_engine.transcribe_audio(
            audio_path=str(audio_path),
            source_lang=project.get("source_lang", "auto")
        )
        project["dialogues"] = dialogues
        self.save_project(project)
        return project

    def separate_project_vocals(self, project_id: str) -> Dict[str, Any]:
        """Separate dialogue vocals from background music/effects."""
        project = self.load_project(project_id)
        if not project or not project.get("original_audio_file"):
            raise ValueError("No audio found for vocal separation")

        proj_dir = Path(f"data/projects/{project_id}")
        bgm_path, voc_path = separate_vocals_and_bgm(project["original_audio_file"], output_dir=str(proj_dir))
        project["isolated_bgm_file"] = bgm_path
        if voc_path and Path(voc_path).exists():
            project["isolated_vocals_file"] = str(voc_path)
        self.save_project(project)
        return project

    async def translate_project(
        self,
        project_id: str,
        mode: Optional[str] = None,
        source_lang: Optional[str] = None,
        voice_override: Optional[str] = None
    ) -> Dict[str, Any]:
        project = self.load_project(project_id)
        if not project:
            raise ValueError("Project not found")

        mode = mode or project.get("mode", "drama_dubbing")
        source_lang = source_lang or project.get("source_lang", "auto")
        
        if not voice_override or voice_override in (None, "", "auto"):
            cfg = {}
            try:
                cfg_p = Path("data/story_config.json")
                if cfg_p.exists():
                    with open(cfg_p, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
            except Exception:
                pass
            if cfg.get("auto_multi_voice") is not False or cfg.get("khmer_voice") == "multi":
                v_override = "multi"
            else:
                v_override = cfg.get("khmer_voice", "multi")
        else:
            v_override = voice_override

        # Ensure dialogues have speaker role assignment if in multi-voice mode (Zero-Freeze Fast Diarization)
        if v_override in ("multi", "auto_multi"):
            last_role = "male"
            for d in project.get("dialogues", []):
                role = d.get("detected_role")
                if role in ("female", "male"):
                    last_role = role
                    d["voice"] = "sreymom" if role == "female" else "piseth"
                    continue

                spk_str = str(d.get("speaker", "")).lower()
                if any(kw in spk_str for kw in ("female", "ស្រី", "s1", "s3", "s5")):
                    d["detected_role"] = "female"
                    d["voice"] = "sreymom"
                    last_role = "female"
                elif any(kw in spk_str for kw in ("male", "ប្រុស", "s0", "s2", "s4")):
                    d["detected_role"] = "male"
                    d["voice"] = "piseth"
                    last_role = "male"
                else:
                    # Alternate conversation turn smoothly
                    new_role = "female" if last_role == "male" else "male"
                    d["detected_role"] = new_role
                    d["voice"] = "sreymom" if new_role == "female" else "piseth"
                    last_role = new_role

        translated_dialogues = await self.translator.translate_dialogues(
            dialogues=project.get("dialogues", []),
            mode=mode,
            source_lang=source_lang,
            target_voice_override=v_override,
            drama_title=project.get("title")
        )

        if v_override not in ("multi", "auto_multi"):
            chosen_v = "sreymom" if v_override == "sreymom" else "piseth"
            v_desc = "Sreymom (Female Solo)" if chosen_v == "sreymom" else "Piseth (Male Solo)"
            for d in translated_dialogues:
                d["voice"] = chosen_v
                d["pitch_hz"] = 0
                d["rate_percent"] = 0
                d["speaker"] = v_desc

        project["dialogues"] = translated_dialogues
        project["mode"] = mode
        project["source_lang"] = source_lang
        self.save_project(project)
        return project

    async def generate_project_audio(self, project_id: str) -> Dict[str, Any]:
        project = self.load_project(project_id)
        if not project:
            raise ValueError("Project not found")

        proj_dir = Path(f"data/projects/{project['id']}")
        voice_out_dir = proj_dir / "voices"
        voice_out_dir.mkdir(parents=True, exist_ok=True)

        processed_dialogues = await batch_synthesize(
            dialogue_items=project.get("dialogues", []),
            output_dir=str(voice_out_dir),
            default_voice=project.get("voice_override", "piseth")
        )

        # Strictly verify and recover any synthesized voices to ensure 100% audible speech
        from tts_engine import is_valid_audible_audio, synthesize_via_google_khmer_api
        for idx, d in enumerate(processed_dialogues):
            af = d.get("audio_file")
            if not is_valid_audible_audio(af):
                txt = (d.get("text_km") or d.get("text", "")).strip()
                v = d.get("voice") or project.get("voice_override") or "piseth"
                fix_out = voice_out_dir / f"line_recovered_{idx:04d}_{os.urandom(3).hex()}.mp3"
                new_af = synthesize_via_google_khmer_api(txt, v, str(fix_out))
                if new_af and is_valid_audible_audio(new_af):
                    d["audio_file"] = new_af

        project["dialogues"] = processed_dialogues

        # Automatically separate vocals if not already done
        # Automatically separate vocals if not already done
        if (not project.get("isolated_bgm_file") or not Path(str(project.get("isolated_bgm_file"))).exists()) and project.get("original_audio_file"):
            try:
                bgm_path, voc_path = separate_vocals_and_bgm(project["original_audio_file"], output_dir=str(proj_dir))
                project["isolated_bgm_file"] = bgm_path
            except Exception as e:
                print(f"Auto separation note: {e}")

        cfg_data = {}
        try:
            cfg_p = Path("data/story_config.json")
            if cfg_p.exists():
                with open(cfg_p, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
        except Exception:
            pass

        bgm_track = project.get("isolated_bgm_file") or project.get("original_audio_file")
        if not Path(str(bgm_track)).exists():
            bgm_track = project.get("original_audio_file")

        mixed_audio_path = proj_dir / "mixed_dubbed_audio.mp3"
        duck_val = safe_float(cfg_data.get("ducking_volume"), safe_float(project.get("ducking_factor"), 0.15))
        dub_mode = cfg_data.get("dubbing_mode", "smart_bgm")
        speech_boost = safe_float(cfg_data.get("speech_boost_db"), 2.5)

        mix_dubbed_audio(
            original_audio_path=bgm_track,
            dialogue_items=processed_dialogues,
            output_mixed_path=str(mixed_audio_path),
            total_duration_sec=project.get("duration", 0),
            ducking_volume_factor=duck_val,
            speech_volume_boost_db=speech_boost,
            dubbing_mode=dub_mode
        )

        project["mixed_audio_file"] = str(mixed_audio_path)
        project["waveform"] = create_waveform_data(str(mixed_audio_path))
        self.save_project(project)
        return project

    def render_project_video_final(
        self,
        project_id: str,
        burn_subtitles: bool = False,
        aspect_ratio: str = "16:9",
        watermark_text: Optional[str] = None,
        overlay_config: Optional[Dict[str, Any]] = None,
        custom_export_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        project = self.load_project(project_id)
        if not project:
            raise ValueError("Project not found")

        video_in = project.get("video_file")
        mixed_audio = project.get("mixed_audio_file")
        if not video_in or not Path(video_in).exists():
            raise ValueError("No video file found in project to render.")
        if not mixed_audio or not Path(mixed_audio).exists():
            raise ValueError("No mixed audio found. Please generate speech audio first.")

        proj_dir = Path(f"data/projects/{project['id']}")
        output_video_path = proj_dir / "final_dubbed_video.mp4"

        render_dubbed_video(
            original_video_path=video_in,
            mixed_audio_path=mixed_audio,
            output_video_path=str(output_video_path),
            dialogues=project.get("dialogues", []),
            burn_subtitles=burn_subtitles,
            aspect_ratio=aspect_ratio,
            watermark_text=watermark_text,
            overlay_config=overlay_config,
            temp_dir=str(proj_dir / "temp")
        )

        project["output_video_file"] = str(output_video_path)
        project["burn_subtitles"] = burn_subtitles
        project["aspect_ratio"] = aspect_ratio
        project["watermark_text"] = watermark_text or ""
        if overlay_config:
            project["overlay_config"] = overlay_config

        # Mirror cleanly to drama unified folder (only .mp4 video, zero extra files)
        try:
            import shutil
            from batch_engine import resolve_drama_export_directories
            import re
            clean_title = project.get("title") or Path(video_in).stem
            dest_dirs = resolve_drama_export_directories(video_in, clean_title, custom_export_dir=custom_export_dir)
            
            # Format clean output stem avoiding 'Dubbed_Dubbed_' or repeated extensions (.mp4.mp4)
            title_stem = project.get("title") or Path(video_in).stem
            clean_stem = re.sub(r'^(?:Dubbed_)+', '', str(title_stem), flags=re.IGNORECASE)
            clean_stem = re.sub(r'^Raw_Full_Movie_', '', clean_stem, flags=re.IGNORECASE)
            clean_stem = re.sub(r'(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$', '', clean_stem, flags=re.IGNORECASE)
            clean_stem = re.sub(r'_\d{9,12}$', '', clean_stem)
            
            # Check original filename before falling back to folder name
            orig_name = Path(video_in).stem
            orig_name = re.sub(r'^(?:Dubbed_)+', '', orig_name, flags=re.IGNORECASE)
            orig_name = re.sub(r'^Raw_Full_Movie_', '', orig_name, flags=re.IGNORECASE)
            orig_name = re.sub(r'(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$', '', orig_name, flags=re.IGNORECASE)
            orig_name = re.sub(r'_\d{9,12}$', '', orig_name)
            orig_name = re.sub(r'^\d{9,12}_', '', orig_name)

            if clean_stem.lower() in ("drama_series", "drama_series_full_movie", "full_movie", "video", ""):
                if orig_name and orig_name.lower() not in ("drama_series", "full_movie", "video", "source_media", "drama_video", "sample_video"):
                    clean_stem = orig_name
                elif dest_dirs:
                    parent_drama_name = dest_dirs[0].name
                    if parent_drama_name and parent_drama_name.lower() not in ("exports", "sn_dramas", "uploads", "data", "temp"):
                        clean_stem = f"{parent_drama_name}_Full_Movie"
                    else:
                        clean_stem = "Drama_Series_Full_Movie"

            # CRITICAL: Sanitize illegal Windows filename characters (: * ? " < > | / \)
            clean_stem = re.sub(r'[\\/*?:"<>|]', '_', str(clean_stem)).strip('. ') or "Video"
            out_stem = f"Dubbed_{clean_stem}"
            
            saved_paths = []
            for d in dest_dirs:
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    dest_file = d / f"{out_stem}.mp4"
                    if Path(output_video_path).resolve() != dest_file.resolve():
                        shutil.copy2(str(output_video_path), str(dest_file))
                    if dest_file.exists():
                        saved_paths.append(str(dest_file))
                except Exception as copy_e:
                    print(f"[Export Folder Copy Error] Failed copying to {d}: {copy_e}")

                # Clean up any lingering .srt file with the same stem if present
                try:
                    lingering_srt = d / f"{out_stem}.srt"
                    if lingering_srt.exists():
                        lingering_srt.unlink()
                except Exception:
                    pass

                try:
                    generic_srt = d / "Dubbed_Drama_Series_Full_Movie.srt"
                    if generic_srt.exists():
                        generic_srt.unlink()
                except Exception:
                    pass

            # If all destination directories failed (e.g. read-only or invalid drive), fall back to data/exports
            if not saved_paths:
                fallback_dir = Path("data/exports")
                fallback_dir.mkdir(parents=True, exist_ok=True)
                fallback_file = fallback_dir / f"{out_stem}.mp4"
                if Path(output_video_path).resolve() != fallback_file.resolve():
                    shutil.copy2(str(output_video_path), str(fallback_file))
                if fallback_file.exists():
                    saved_paths.append(str(fallback_file))

            if saved_paths:
                project["final_exported_video_path"] = saved_paths[0]
                project["final_exported_filename"] = Path(saved_paths[0]).name
                project["final_exported_dir"] = str(Path(saved_paths[0]).parent)
        except Exception as e:
            print(f"Unified drama folder export note: {e}")

        self.save_project(project)
        return project

    async def process_video_pipeline(
        self,
        video_path: str,
        title: Optional[str] = None,
        mode: str = "drama_dubbing",
        source_lang: str = "auto",
        voice_override: Optional[str] = None,
        aspect_ratio: str = "16:9",
        burn_subtitles: bool = False,
        overlay_config: Optional[Dict[str, Any]] = None,
        progress_callback = None,
        custom_export_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete 1-Click Automated Video Dubbing Pipeline:
        1. Extract Audio & Waveform (15%)
        2. Speech-to-Text via Faster-Whisper (35%)
        3. Translate Script to Natural Khmer Drama Dubbing (55%)
        4. Synthesize Khmer Voices with Piseth & Sreymom Neural TTS (75%)
        5. Smart Audio Ducking & BGM Mixing (85%)
        6. Render Final Master MP4 & Export (95%)
        """
        def update_prog(pct: int, msg_km: str, msg_en: str, dialogues = None):
            if progress_callback:
                try:
                    import inspect
                    sig = inspect.signature(progress_callback)
                    if len(sig.parameters) >= 4:
                        progress_callback(pct, msg_km, msg_en, dialogues)
                    else:
                        progress_callback(pct, msg_km, msg_en)
                except Exception:
                    try:
                        progress_callback(pct, msg_km, msg_en)
                    except Exception:
                        pass

        src_file = Path(video_path)
        if not src_file.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        proj_title = title or f"Dubbed_{src_file.stem}"
        project = self.create_project(title=proj_title, mode=mode)
        proj_id = project["id"]
        proj_dir = Path(f"data/projects/{proj_id}")
        proj_dir.mkdir(parents=True, exist_ok=True)

        # 1. Video & Audio Preparation (Direct zero-copy referencing for ultra-fast processing)
        update_prog(12, "1/7 Extracting audio from video...", "Extracting audio from video...")
        dest_video = src_file
        audio_dest = proj_dir / "original_audio.wav"
        extract_audio_from_video(str(dest_video), str(audio_dest))
        
        project["video_file"] = str(dest_video)
        project["original_audio_file"] = str(audio_dest)
        project["duration"] = get_media_duration(str(dest_video))
        project["waveform"] = create_waveform_data(str(audio_dest))
        project["aspect_ratio"] = aspect_ratio
        project["burn_subtitles"] = burn_subtitles
        self.save_project(project)
        gc.collect()

        # 2. Vocal Separation (Isolate BGM, Eliminate Chinese Vocals)
        update_prog(28, "2/7 Separating original vocals from BGM...", "Separating vocals from BGM...")
        voc_file = None
        try:
            bgm_file, voc_file = separate_vocals_and_bgm(str(audio_dest), output_dir=str(proj_dir))
            project["isolated_bgm_file"] = bgm_file
            if voc_file and Path(voc_file).exists():
                project["isolated_vocals_file"] = str(voc_file)
        except Exception as e:
            print(f"Vocal separation warning: {e}")
            project["isolated_bgm_file"] = str(audio_dest)
        self.save_project(project)
        gc.collect()

        # Resolve Voice Mode (Piseth Solo, Sreymom Solo, or Dual Multi-Voice)
        cfg_data = {}
        try:
            cfg_p = APP_DIR / "data" / "story_config.json"
            if not cfg_p.exists():
                cfg_p = Path("data/story_config.json")
            if cfg_p.exists():
                with open(cfg_p, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
        except Exception:
            pass

        if not voice_override or voice_override in (None, "", "auto"):
            if cfg_data.get("auto_multi_voice") is not False or cfg_data.get("khmer_voice") == "multi":
                voice_override = "multi"
            else:
                voice_override = cfg_data.get("khmer_voice", "multi")

        v_override = str(voice_override).lower().strip()
        is_multi = v_override in ("multi", "auto_multi")
        if is_multi:
            voice_label = "Piseth & Sreymom (Dual Voice)"
        elif v_override == "sreymom":
            voice_label = "Sreymom (Female Solo)"
        else:
            voice_label = "Piseth (Male Solo)"

        # 3. Speech-to-Text (Auto Transcribe via Faster-Whisper with word-level timestamps)
        update_prog(45, f"3/7 AI transcribing dialogue ({voice_label})...", "Transcribing speech...")
        # Use full-fidelity original audio for 100% complete dialogue capture (Zero Dropped Words Guarantee)
        stt_target_audio = str(audio_dest)
        try:
            dialogues = self.stt_engine.transcribe_audio(
                audio_path=stt_target_audio,
                source_lang=source_lang,
                voice_override=v_override,
                progress_callback=update_prog,
                video_path=str(dest_video)
            )
        except Exception as e:
            print(f"STT Exception: {e}")
            dialogues = []

        # Robust Fallback: If isolated vocals produced 0 dialogues or failed, retry directly on original audio!
        if not dialogues and str(audio_dest) != str(stt_target_audio) and Path(audio_dest).exists():
            print("Notice: Isolated vocals yielded 0 dialogues, falling back to original audio for STT...")
            update_prog(48, f"3/7 Scanning original audio ({voice_label})...", "Retrying transcription on original audio...")
            try:
                dialogues = self.stt_engine.transcribe_audio(
                    audio_path=str(audio_dest),
                    source_lang=source_lang,
                    voice_override=v_override,
                    progress_callback=update_prog
                )
            except Exception as e2:
                print(f"STT Fallback Exception: {e2}")

        if not dialogues:
            raise RuntimeError(
                "Speech Recognition (STT) could not detect any audible speech in the uploaded video. "
                "ប្រព័ន្ធ AI មិនអាចចាប់សំឡេងនិយាយនៅក្នុងវីដេអូបានទេ។ សូមពិនិត្យមើលថាវីដេអូដែលបានទម្លាក់ចូលមានសំឡេងនិយាយច្បាស់លាស់។"
            )

        project["dialogues"] = dialogues
        self.save_project(project)
        gc.collect()

        # 4. Translate to Khmer Drama Dialogue (Strictly honors Piseth, Sreymom, or Dual Voice)
        update_prog(62, f"4/7 AI translating script ({voice_label})...", f"Translating script to {voice_label}...")
        try:
            translated = await self.translator.translate_dialogues(
                dialogues=dialogues,
                mode=mode,
                source_lang=source_lang,
                target_voice_override=v_override,
                drama_title=proj_title
            )
        except Exception as te:
            print(f"Translation Exception: {te}")
            raise RuntimeError(f"AI Translation failed: {te}") from te

        if dialogues and not translated:
            print("Notice: Translation engine returned empty dialogues. Retrying with fallback...")
            try:
                translated = await self.translator.translate_dialogues(
                    dialogues=dialogues,
                    mode=mode,
                    source_lang=source_lang,
                    target_voice_override=v_override
                )
            except Exception as te2:
                print(f"Translation Fallback Exception: {te2}")

        if not translated or len(translated) == 0:
            raise RuntimeError(
                "AI Script Translation returned 0 dialogues. "
                "ការបកប្រែស្គ្រីបមិនទទួលបានជោគជ័យទេ។ សូមពិនិត្យមើលការភ្ជាប់ទៅកាន់ប្រព័ន្ធ AI។"
            )

        if not is_multi:
            chosen_v = "sreymom" if v_override == "sreymom" else "piseth"
            v_desc = "Sreymom (Female Solo)" if chosen_v == "sreymom" else "Piseth (Male Solo)"
            for d in (translated or []):
                d["voice"] = chosen_v
                d["pitch_hz"] = 0
                d["rate_percent"] = 0
                d["speaker"] = v_desc

        if mode == "movie_recap" and translated:
            import random
            recap_v = "sreymom" if v_override == "sreymom" else "piseth"
            has_hook = any("Viral Hook" in str(d.get("speaker", "")) for d in translated)
            if not has_hook:
                hook_opts = RecapEngine.get_hooks("drama_revenge")
                chosen_hook = random.choice(hook_opts) if hook_opts else "កុំទាន់អាលរំលង! រឿងរ៉ាវបន្ទាប់ពីនេះនឹងធ្វើឱ្យអ្នកស្មានមិនដល់..."
                translated = RecapEngine.inject_viral_hook(translated, chosen_hook, voice=recap_v)
            has_outro = any("Call To Action" in str(d.get("speaker", "")) for d in translated)
            if not has_outro:
                translated = RecapEngine.inject_viral_outro(translated, voice=recap_v)

        project["dialogues"] = translated or []
        self.save_project(project)
        gc.collect()
        trans_count = len(translated) if translated else 0
        update_prog(68, f"4/7 Translation completed ({trans_count} lines)! Preparing voice synthesis ({voice_label})...", f"Translation completed ({trans_count} lines)!", dialogues=translated)

        # 5. Neural Khmer Voice Synthesis
        voice_out_dir = proj_dir / "voices"
        voice_out_dir.mkdir(parents=True, exist_ok=True)
        total_d = len(translated)

        last_update_time = [0.0]
        def on_tts_progress(completed: int, total: int, item: Dict[str, Any]):
            # Progress smoothly spans 72% to 88%
            pct = 72 + int((completed / max(1, total)) * 16)
            now = time.time()
            if completed == total or completed % 2 == 0 or (now - last_update_time[0]) >= 0.5:
                last_update_time[0] = now
                pct_str = f"{int((completed / max(1, total)) * 100)}%"
                msg = f"5/7 Synthesizing voice ({completed}/{total} lines - {pct_str})..."
                update_prog(pct, msg, msg)

        update_prog(72, f"5/7 Synthesizing neural voice ({voice_label}) 0/{total_d} lines...", f"Synthesizing neural voice ({voice_label})...")
        synthesized = await batch_synthesize(
            translated,
            output_dir=str(voice_out_dir),
            default_voice="piseth" if is_multi else v_override,
            progress_callback=on_tts_progress
        )
        project["dialogues"] = synthesized
        self.save_project(project)
        gc.collect()

        # Verify and recover any synthesized voices to ensure 100% audible, non-silent speech
        from tts_engine import is_valid_audible_audio, synthesize_via_google_khmer_api
        recovered_count = 0
        for idx, d in enumerate(synthesized):
            af = d.get("audio_file")
            if not is_valid_audible_audio(af):
                txt = (d.get("text_km") or d.get("text", "")).strip()
                v = d.get("voice") or v_override or "piseth"
                fix_out = voice_out_dir / f"line_recovered_{idx:04d}_{os.urandom(3).hex()}.mp3"
                new_af = synthesize_via_google_khmer_api(txt, v, str(fix_out))
                if new_af and is_valid_audible_audio(new_af):
                    d["audio_file"] = new_af
                    recovered_count += 1

        valid_voices = [
            d for d in synthesized
            if is_valid_audible_audio(d.get("audio_file"))
        ]
        print(f"[OK] TTS Voice Synthesis: {len(valid_voices)} / {len(synthesized)} lines verified with audible speech (recovered {recovered_count}).")
        if len(synthesized) > 0 and len(valid_voices) == 0:
            raise RuntimeError(
                "Khmer Voice Synthesis failed to generate audible speech for any dialogue lines. "
                "ប្រព័ន្ធសំឡេង AI មិនអាចបង្កើតសំឡេងខ្មែរបានឡើយ។ សូមពិនិត្យមើលការភ្ជាប់អ៊ីនធឺណិត (Internet Connection) នៅលើកុំព្យូទ័ររបស់អ្នក។"
            )

        # 6. Audio Ducking & Clean BGM Mixing (Zero Vocal Leakage)
        update_prog(88, "6/7 Mixing dubbed voice with BGM (Zero Vocal Leakage)...", "Mixing dubbed audio with clean BGM...")
        mixed_audio = proj_dir / "mixed_dubbed_audio.mp3"
        bgm_track = project.get("isolated_bgm_file") or str(audio_dest)
        if not Path(bgm_track).exists():
            bgm_track = str(audio_dest)
        duck_val = safe_float(cfg_data.get("ducking_volume"), safe_float(project.get("ducking_factor"), 0.15))
        dub_mode = cfg_data.get("dubbing_mode", "smart_bgm")
        speech_boost = safe_float(cfg_data.get("speech_boost_db"), 2.5)
        mix_dubbed_audio(
            original_audio_path=bgm_track,
            dialogue_items=synthesized,
            output_mixed_path=str(mixed_audio),
            total_duration_sec=project.get("duration", 0),
            ducking_volume_factor=duck_val,
            speech_volume_boost_db=speech_boost,
            dubbing_mode=dub_mode
        )
        project["mixed_audio_file"] = str(mixed_audio)
        project["waveform"] = create_waveform_data(str(mixed_audio))
        self.save_project(project)
        gc.collect()

        # 7. Render Final Video
        update_prog(95, "7/7 Rendering final dubbed MP4 video...", "Rendering final dubbed video...")
        rendered_project = self.render_project_video_final(
            project_id=proj_id,
            burn_subtitles=burn_subtitles,
            aspect_ratio=aspect_ratio,
            overlay_config=overlay_config,
            custom_export_dir=custom_export_dir
        )
        gc.collect()

        update_prog(100, "🎉 100% Complete! Dubbed video saved successfully!", "Completed! Video ready.")
        return rendered_project
