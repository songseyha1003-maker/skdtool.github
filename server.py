"""
Flask Web Server & REST APIs for Khmer AI Drama Voice Translator & Movie Recap Studio (SN STUDIO V1.0.0)
"""
import os
import sys
import time
import json
import shutil
import asyncio
import subprocess
import threading
import uuid
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

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

from flask import Flask, request, jsonify, send_file, send_from_directory

# Resolve base dir for PyInstaller executable support
if getattr(sys, 'frozen', False):
    APP_DIR = Path(os.path.dirname(sys.executable))
    BASE_DIR = Path(sys._MEIPASS)
    if (APP_DIR / "static").exists():
        STATIC_DIR = APP_DIR / "static"
    else:
        STATIC_DIR = BASE_DIR / "static"
else:
    APP_DIR = Path(__file__).resolve().parent
    BASE_DIR = APP_DIR
    STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.errorhandler(Exception)
def handle_unexpected_server_error(e):
    import traceback
    err_text = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    print(f"\n[SERVER API ERROR PREVENTED] {err_text}", file=sys.stderr)
    return jsonify({
        "success": False,
        "error": str(e),
        "message": "Technical issue occurred, but system continues running normally"
    }), 500

# Core Studio Modules & Engines
from tts_engine import get_available_voices, synthesize_khmer_speech
from translator import DramaTranslator, parse_srt_content
from pipeline import ProjectManager, SAMPLE_DRAMAS
from audio_processor import (
    extract_audio_from_video,
    create_waveform_data,
    get_media_duration,
    get_silent_kwargs,
    patch_silent_subprocess
)
patch_silent_subprocess()
from downloader import (
    download_video_from_url,
    get_supported_platforms_with_counts,
    DRAMA_CATALOG,
    get_drama_episodes,
    drama_downloader,
    find_authentic_episode_video,
    merge_downloaded_drama_episodes,
    get_hongguo_episode_real_stream_url,
    resolve_safe_save_location
)
import hongguo_db
import shortmax_service
from recap_engine import RecapEngine, VIRAL_KHMER_HOOKS
from batch_engine import batch_manager, EXPORTS_DIR
from video_processor import (
    merge_videos,
    split_video,
    batch_rename_files,
    compress_video
)
from license_engine import (
    check_current_device_license,
    activate_license_on_device,
    generate_license_key,
    register_custom_key,
    revoke_license_key,
    unrevoke_license_key,
    delete_license_key_record,
    get_revoked_keys,
    is_license_required,
    set_license_required,
    get_machine_hwid,
    record_permanent_device_ban,
    is_current_device_banned,
    unban_device,
    ADMIN_HISTORY_FILE
)
from update import (
    check_for_updates,
    get_version_info,
    apply_git_pull_update,
    apply_zip_download_update
)

pm = ProjectManager()

Path("static").mkdir(parents=True, exist_ok=True)
Path("data/uploads").mkdir(parents=True, exist_ok=True)
Path("data/exports").mkdir(parents=True, exist_ok=True)
Path("cache").mkdir(parents=True, exist_ok=True)


# ==========================================================================
# 🛡️ SERVER-LEVEL API FIREWALL & LICENSE ENFORCEMENT GUARD (Layer 1 & 3)
# ==========================================================================
PUBLIC_API_WHITELIST = {
    "/api/license/status",
    "/api/license/activate",
    "/api/license/hwid",
    "/api/system/play-completion-sound",
    "/api/version",
    "/health",
    "/api/health"
}

@app.before_request
def server_license_firewall():
    """
    Strictly intercepts and blocks unlicensed requests before reaching any engine.
    Ensures that bypasses on Frontend UI cannot execute any backend operations.
    """
    path = request.path

    # Allow static assets and root HTML page
    if path in ("/", "/index.html", "/favicon.ico", "/logo.png") or path.startswith("/static/"):
        return None

    # Allow whitelisted public endpoints (license verification / activation / health)
    if path in PUBLIC_API_WHITELIST or path.startswith("/api/license/") or path.startswith("/api/update/"):
        return None

    # Strictly protect all remaining /api/* endpoints
    if path.startswith("/api/"):
        # Layer 3: Localhost Origin & Referer Binding
        client_ip = request.remote_addr or ""
        if client_ip not in ("127.0.0.1", "::1", "localhost", "testclient"):
            return jsonify({
                "success": False,
                "error": "ACCESS_DENIED_EXTERNAL_IP",
                "message": "Security Violation: External network access is strictly prohibited.",
                "code": 403
            }), 403

        # Layer 1: Check License Requirement & Device License Status
        if is_license_required():
            lic = check_current_device_license()
            if lic.get("is_banned"):
                return jsonify({
                    "success": False,
                    "error": "DEVICE_PERMANENTLY_BANNED",
                    "message": lic.get("message", "⛔ ឧបករណ៍កុំព្យូទ័រនេះត្រូវបានចាក់សោរជាអចិន្ត្រៃយ៍"),
                    "code": 403,
                    "hwid": lic.get("hwid")
                }), 403

            if not lic.get("is_activated"):
                return jsonify({
                    "success": False,
                    "error": "DEVICE_UNLICENSED",
                    "message": "⚠️ ឧបករណ៍នេះមិនទាន់បានចុះឈ្មោះ License ស្របច្បាប់ឡើយ! សូមទាក់ទង Admin ដើម្បីទទួលបាន License Key។",
                    "code": 403,
                    "hwid": lic.get("hwid")
                }), 403

    return None


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,OPTIONS"
    return response


_last_sound_time = 0.0
_sound_lock = threading.Lock()

def play_windows_completion_sound():
    """
    Plays the authentic Windows System Notification Sound directly on Windows OS.
    Runs asynchronously in a daemon thread so it never blocks HTTP request handling.
    Built-in, permanent notification sound with 5.0s debounce.
    """
    global _last_sound_time
    now = time.time()
    with _sound_lock:
        if now - _last_sound_time < 5.0:
            return
        _last_sound_time = now

    def _play():
        try:
            if sys.platform == "win32":
                import winsound
                windir = os.environ.get("WINDIR", "C:\\Windows")
                candidates = [
                    os.path.join(windir, "Media", "Windows Notify System Generic.wav"),
                    os.path.join(str(STATIC_DIR), "system_notification.wav"),
                    os.path.join(windir, "Media", "Windows Background.wav"),
                    os.path.join(str(STATIC_DIR), "windows_notify.wav"),
                    os.path.join(windir, "Media", "Windows Notify.wav"),
                ]
                for p in candidates:
                    if os.path.exists(p):
                        try:
                            winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_ASYNC)
                            return
                        except Exception:
                            pass
                
                try:
                    winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    return
                except Exception:
                    pass

                try:
                    winsound.PlaySound("Notification.Default", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    return
                except Exception:
                    pass

                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass
        except Exception as e:
            print(f"[Sound Notification] Sound play note: {e}", file=sys.stderr)

    threading.Thread(target=_play, daemon=True).start()


@app.route("/api/system/play-completion-sound", methods=["POST", "GET"])
def system_play_completion_sound_endpoint():
    play_windows_completion_sound()
    return jsonify({"success": True, "message": "Windows completion sound played"})


@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/static/<path:filename>")
def serve_static_alias(filename):
    """Ensure /static/ prefix always resolves properly to STATIC_DIR."""
    return send_from_directory(str(STATIC_DIR), filename)


@app.route("/favicon.ico")
@app.route("/icon.ico")
def favicon():
    return send_from_directory(str(STATIC_DIR), "favicon.ico")


@app.route("/api/voices", methods=["GET"])
def get_voices():
    return jsonify({"voices": get_available_voices()})


@app.route("/api/voices/preview", methods=["POST"])
def preview_voice():
    data = request.get_json(force=True) or {}
    text = data.get("text", "Hello")
    voice = data.get("voice", "piseth")
    rate = int(data.get("rate_percent", 0))
    pitch = int(data.get("pitch_hz", 0))

    try:
        sample_path = asyncio.run(synthesize_khmer_speech(
            text=text,
            voice=voice,
            rate_percent=rate,
            pitch_hz=pitch,
            use_cache=True
        ))
        return jsonify({"success": True, "audio_url": f"/media/{sample_path.replace(chr(92), '/')}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/samples", methods=["GET"])
def get_sample_list():
    return jsonify({"samples": SAMPLE_DRAMAS})


@app.route("/api/recap-hooks", methods=["GET"])
def get_recap_hooks():
    return jsonify({"hooks": VIRAL_KHMER_HOOKS})


@app.route("/api/recap/generate", methods=["POST"])
def generate_recap_story_endpoint():
    """
    Generate an AI Movie Recap script (សម្រាយសាច់រឿង Facebook & TikTok)
    using Gemini 3.8 Flash High on SN AI Online Cloud Server.
    """
    data = request.get_json(force=True) or {}
    project_id = data.get("project_id")
    raw_text = data.get("text", "")
    drama_title = data.get("title", "")
    genre = data.get("genre", "drama_revenge")
    voice = data.get("voice", "piseth")

    dialogues_input = None
    if project_id:
        p = pm.load_project(project_id)
        if p:
            dialogues_input = p.get("dialogues", [])
            if not drama_title:
                drama_title = p.get("title", "")
    if not dialogues_input and raw_text:
        dialogues_input = raw_text

    try:
        script = RecapEngine.generate_ai_movie_recap(
            transcript_or_dialogues=dialogues_input or "រឿងភាគខ្លី",
            drama_title=drama_title,
            genre=genre,
            voice=voice
        )
        return jsonify({"success": True, "recap_script": script})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<project_id>/apply-recap-script", methods=["POST"])
def apply_recap_script_endpoint(project_id):
    """
    Convert an AI-generated Movie Recap story into timed spoken dialogues and apply to project.
    """
    project = pm.load_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    data = request.get_json(force=True) or {}
    recap_script = data.get("recap_script", "")
    voice = data.get("voice", "piseth")
    duration = float(project.get("duration", 60.0) or 60.0)
    if not recap_script:
        return jsonify({"error": "recap_script is empty"}), 400

    timed_dialogues = RecapEngine.format_recap_script_into_timed_dialogues(
        recap_text=recap_script,
        total_duration=duration,
        voice=voice
    )
    project["dialogues"] = timed_dialogues
    project["mode"] = "movie_recap"
    pm.save_project(project)
    return jsonify({"success": True, "dialogues_count": len(timed_dialogues), "project": project})


@app.route("/api/projects/sample/<sample_key>", methods=["POST"])
def load_sample_drama(sample_key):
    try:
        project = pm.load_sample(sample_key)
        return jsonify({"success": True, "project": project})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects", methods=["GET"])
def list_projects():
    return jsonify({"projects": pm.list_projects()})


@app.route("/api/projects/new", methods=["POST"])
def create_new_project():
    title = request.form.get("title", "New Drama Project")
    mode = request.form.get("mode", "drama_dubbing")
    project = pm.create_project(title=title, mode=mode)
    return jsonify({"success": True, "project": project})


@app.route("/api/projects/<project_id>", methods=["GET"])
def get_project(project_id):
    project = pm.load_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify({"project": project})


@app.route("/api/projects/<project_id>/save", methods=["POST"])
def save_project_data(project_id):
    project = pm.load_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    data = request.get_json(force=True) or {}
    project.update(data)
    pm.save_project(project)
    return jsonify({"success": True, "project": project})


@app.route("/api/projects/<project_id>/upload-video", methods=["POST"])
def upload_video(project_id):
    project = pm.load_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    proj_dir = Path(f"data/projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)
    
    file_ext = Path(file.filename).suffix.lower()
    video_dest = proj_dir / f"source_media{file_ext}"
    file.save(str(video_dest))

    audio_dest = proj_dir / "original_audio.wav"
    try:
        extract_audio_from_video(str(video_dest), str(audio_dest))
        project["video_file"] = str(video_dest)
        project["original_audio_file"] = str(audio_dest)
        project["duration"] = get_media_duration(str(video_dest))
        project["waveform"] = create_waveform_data(str(audio_dest))
        pm.save_project(project)
        return jsonify({"success": True, "project": project})
    except Exception as e:
        return jsonify({"error": f"Failed to process media file: {str(e)}"}), 500


@app.route("/api/projects/<project_id>/download-url", methods=["POST"])
def download_url_endpoint(project_id):
    project = pm.load_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(force=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL cannot be empty"}), 400

    proj_dir = Path(f"data/projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        res = download_video_from_url(url, output_dir=str(proj_dir))
        video_path = res["video_file"]
        audio_dest = proj_dir / "original_audio.wav"
        
        extract_audio_from_video(str(video_path), str(audio_dest))
        project["video_file"] = str(video_path)
        project["original_audio_file"] = str(audio_dest)
        project["title"] = res.get("title", project["title"])
        project["duration"] = res.get("duration") or get_media_duration(str(video_path))
        project["waveform"] = create_waveform_data(str(audio_dest))
        pm.save_project(project)

        return jsonify({"success": True, "project": project})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<project_id>/auto-transcribe", methods=["POST"])
def auto_transcribe_endpoint(project_id):
    try:
        project = pm.auto_transcribe_project(project_id)
        return jsonify({"success": True, "project": project, "dialogues_count": len(project.get("dialogues", []))})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<project_id>/separate-vocals", methods=["POST"])
def separate_vocals_endpoint(project_id):
    try:
        project = pm.separate_project_vocals(project_id)
        return jsonify({"success": True, "project": project, "bgm_file": project.get("isolated_bgm_file")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<project_id>/inject-hook", methods=["POST"])
def inject_hook_endpoint(project_id):
    project = pm.load_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(force=True) or {}
    hook_text = data.get("hook_text", "")
    voice = data.get("voice", "piseth")

    if hook_text:
        project["dialogues"] = RecapEngine.inject_viral_hook(project.get("dialogues", []), hook_text, voice)
        pm.save_project(project)
        return jsonify({"success": True, "project": project})
    return jsonify({"error": "Hook text is empty"}), 400


@app.route("/api/projects/<project_id>/upload-srt", methods=["POST"])
def upload_srt(project_id):
    project = pm.load_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    content = file.read().decode("utf-8", errors="ignore")
    parsed_dialogues = parse_srt_content(content)
    
    project["dialogues"] = parsed_dialogues
    pm.save_project(project)
    return jsonify({"success": True, "dialogues_count": len(parsed_dialogues), "project": project})


@app.route("/api/projects/<project_id>/translate", methods=["POST"])
def translate_project_script(project_id):
    data = request.get_json(force=True) or {}
    mode = data.get("mode", "drama_dubbing")
    source_lang = data.get("source_lang", "auto")
    voice_override = data.get("voice_override")
    if not voice_override or voice_override == "auto":
        cfg = load_stored_story_config()
        if cfg.get("auto_multi_voice") is not False or cfg.get("khmer_voice") == "multi":
            voice_override = "multi"
        else:
            voice_override = cfg.get("khmer_voice", "multi")

    try:
        updated_project = asyncio.run(pm.translate_project(
            project_id=project_id,
            mode=mode,
            source_lang=source_lang,
            voice_override=voice_override
        ))
        return jsonify({"success": True, "project": updated_project})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<project_id>/generate-line-audio", methods=["POST"])
def generate_single_line_audio(project_id):
    project = pm.load_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json(force=True) or {}
    line_index = int(data.get("line_index", 0))
    text_km = data.get("text_km", "")
    voice = data.get("voice", "piseth")
    rate = int(data.get("rate_percent", 0))
    pitch = int(data.get("pitch_hz", 0))

    proj_dir = Path(f"data/projects/{project_id}/voices")
    proj_dir.mkdir(parents=True, exist_ok=True)
    out_line_path = proj_dir / f"line_{line_index:04d}.mp3"

    try:
        audio_path = asyncio.run(synthesize_khmer_speech(
            text=text_km,
            voice=voice,
            rate_percent=rate,
            pitch_hz=pitch,
            output_path=str(out_line_path)
        ))
        
        dialogues = project.get("dialogues", [])
        if 0 <= line_index < len(dialogues):
            dialogues[line_index]["audio_file"] = audio_path
            dialogues[line_index]["voice"] = voice
            dialogues[line_index]["text_km"] = text_km
            dialogues[line_index]["rate_percent"] = rate
            dialogues[line_index]["pitch_hz"] = pitch
            pm.save_project(project)

        return jsonify({"success": True, "audio_url": f"/media/{audio_path.replace(chr(92), '/')}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<project_id>/generate-audio-all", methods=["POST"])
def generate_audio_all(project_id):
    try:
        updated_project = asyncio.run(pm.generate_project_audio(project_id))
        return jsonify({
            "success": True,
            "project": updated_project,
            "mixed_audio_url": f"/media/{updated_project['mixed_audio_file'].replace(chr(92), '/')}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/<project_id>/render-video", methods=["POST"])
def render_video_endpoint(project_id):
    data = request.get_json(silent=True) or {}
    burn_sub = request.args.get("burn_subtitles") or data.get("burn_subtitles") or "false"
    burn_sub = str(burn_sub).lower() in ("true", "1", "yes")
    aspect_ratio = request.args.get("aspect_ratio") or data.get("aspect_ratio") or "16:9"
    watermark = request.args.get("watermark") or data.get("watermark") or ""
    overlay_config = data.get("overlay_config")
    
    custom_export_dir = request.args.get("custom_export_dir") or data.get("custom_export_dir")
    try:
        updated_project = pm.render_project_video_final(
            project_id=project_id,
            burn_subtitles=burn_sub,
            aspect_ratio=aspect_ratio,
            watermark_text=watermark,
            overlay_config=overlay_config,
            custom_export_dir=custom_export_dir
        )
        play_windows_completion_sound()
        return jsonify({
            "success": True,
            "project": updated_project,
            "video_url": f"/media/{updated_project['output_video_file'].replace(chr(92), '/')}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# Automated Batch & Folder Processing Endpoints
# ==========================================================================
@app.route("/api/batch/upload", methods=["POST"])
def batch_upload_endpoint():
    """Upload multiple videos or whole folder for automated auto-dubbing."""
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    voice_mode = request.form.get("voice_mode", "piseth")
    if voice_mode in ("auto", "", None):
        cfg = load_stored_story_config()
        voice_mode = cfg.get("khmer_voice", "piseth") if not cfg.get("auto_multi_voice", False) else "auto_multi"
    drama_mode = request.form.get("drama_mode", "drama_dubbing")
    aspect_ratio = request.form.get("aspect_ratio", "16:9")
    cfg = load_stored_story_config()
    burn_sub_default = "true" if cfg.get("subtitle_mode", "none") == "burn" else "false"
    burn_subtitles = request.form.get("burn_subtitles", burn_sub_default).lower() in ("true", "1", "yes")
    separate_bgm = request.form.get("separate_bgm", "true").lower() == "true"
    overlay_config = None
    raw_oc = request.form.get("overlay_config")
    if raw_oc:
        try:
            overlay_config = json.loads(raw_oc) if isinstance(raw_oc, str) else raw_oc
        except Exception:
            pass

    saved_paths = []
    upload_dir = Path("data/uploads/batch_temp")
    upload_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        if f.filename:
            dest = upload_dir / Path(f.filename).name
            f.save(str(dest))
            saved_paths.append(str(dest))

    custom_export_dir = request.form.get("custom_export_dir") or request.args.get("custom_export_dir")

    # Add to queue and trigger worker
    added_items = batch_manager.add_files_to_queue(
        file_paths=saved_paths,
        voice_mode=voice_mode,
        drama_mode=drama_mode,
        aspect_ratio=aspect_ratio,
        burn_subtitles=burn_subtitles,
        separate_bgm=separate_bgm,
        overlay_config=overlay_config,
        custom_export_dir=custom_export_dir
    )
    batch_manager.start_batch_processing()

    return jsonify({"success": True, "added_count": len(added_items), "queue": batch_manager.get_queue_status()})


@app.route("/api/batch/status", methods=["GET"])
def batch_status_endpoint():
    """Get real-time batch queue processing status."""
    return jsonify({
        "is_processing": batch_manager.is_processing,
        "queue": batch_manager.get_queue_status()
    })


@app.route("/api/batch/clear", methods=["POST"])
def batch_clear_endpoint():
    batch_manager.clear_completed()
    return jsonify({"success": True, "queue": batch_manager.get_queue_status()})


@app.route("/api/open-export-folder", methods=["POST"])
def open_export_folder():
    """Open output folder or specific drama folder in Windows File Explorer."""
    data = request.get_json(silent=True) or {}
    folder_path = data.get("folder_path") or request.args.get("path")
    drama_title = data.get("drama_title") or request.args.get("title")

    target_dir = None
    if folder_path and os.path.exists(folder_path):
        target_dir = Path(folder_path).resolve()
    elif drama_title:
        safe = re.sub(r'[\\/*?:"<>|《》【】「」『』\(\)\[\]]', '_', str(drama_title)).strip('_ ')
        for root in ("D:/SN_Dramas", "C:/SN_Dramas", "data/exports"):
            cand = Path(root) / safe
            if cand.exists():
                target_dir = cand.resolve()
                break

    if not target_dir:
        target_dir = EXPORTS_DIR.resolve()

    if sys.platform == "win32":
        try:
            os.startfile(str(target_dir))
            return jsonify({"success": True, "opened_path": str(target_dir)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"success": True, "opened_path": str(target_dir)})


def get_data_file(filename: str, create_dir: bool = False) -> Path:
    """Bulletproof resolver for data files across runtime, package, and user environments."""
    candidates = [
        APP_DIR / "data" / filename,
        APP_DIR / filename,
        BASE_DIR / "data" / filename,
        BASE_DIR / filename,
        Path("data") / filename,
        Path(filename),
        APP_DIR.parent / "data" / filename,
        BASE_DIR.parent / "data" / filename,
        APP_DIR / "_internal" / "data" / filename,
        Path(os.getcwd()) / "data" / filename,
        Path(os.getcwd()) / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    target = APP_DIR / "data" / filename
    if create_dir:
        target.parent.mkdir(parents=True, exist_ok=True)
    return target


AI_CONFIG_FILE = get_data_file("ai_provider_config.json", create_dir=True)
STORY_CONFIG_FILE = get_data_file("story_config.json", create_dir=True)

def load_stored_ai_config() -> dict:
    if AI_CONFIG_FILE.exists():
        try:
            with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                keys = cfg.get("keys", [])
                valid_gemini = [k.strip() for k in keys if str(k).strip().startswith("AIzaSy")]
                if valid_gemini:
                    pm.translator.set_api_keys(valid_gemini)
                    os.environ["GEMINI_API_KEY"] = "\n".join(valid_gemini)
                else:
                    pm.translator.set_api_keys([])

                groq_pool = cfg.get("groq_keys", [])
                if isinstance(groq_pool, list) and groq_pool:
                    pm.translator.groq_keys = [k.strip() for k in groq_pool if k and str(k).startswith("gsk_")]
                groq_k = cfg.get("groq_api_key", "").strip()
                if groq_k:
                    pm.translator.groq_api_key = groq_k
                    os.environ["GROQ_API_KEY"] = groq_k
                return cfg
        except Exception as e:
            print(f"Error loading AI config: {e}")
    return {
        "engine": "auto",
        "groq_api_key": "",
        "gemini_api_key": "",
        "keys": [],
        "keys_raw": "",
        "model": "llama-3.3-70b-versatile",
        "temperature": 0.3,
        "prompt_style": "drama_dubbing"
    }

def load_stored_story_config() -> dict:
    if STORY_CONFIG_FILE.exists():
        try:
            with open(STORY_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading story config: {e}")
    return {
        "khmer_voice": "piseth",
        "auto_multi_voice": True,
        "source_lang": "auto",
        "whisper_model": "medium",
        "aspect_ratio": "9:16",
        "subtitle_mode": "none",
        "dubbing_mode": "smart_bgm",
        "ducking_volume": "0.15",
        "speech_boost_db": 3.5
    }

# Initial load on server start
stored_ai_cfg = load_stored_ai_config()
stored_story_cfg = load_stored_story_config()


@app.route("/api/set-api-key", methods=["POST"])
def set_gemini_api_key():
    data = request.get_json(force=True) or {}
    key = data.get("api_key", "").strip()
    keys = [k.strip() for k in key.replace(",", "\n").splitlines() if k.strip()]
    valid_gemini = [k for k in keys if k.startswith("AIzaSy")]
    pm.translator.set_api_keys(valid_gemini)
    if valid_gemini:
        os.environ["GEMINI_API_KEY"] = "\n".join(valid_gemini)
    return jsonify({"success": True, "message": "API keys updated."})


@app.route("/api/ai-config", methods=["GET"])
def get_ai_config_endpoint():
    cfg = load_stored_ai_config()
    safe_cfg = {
        "engine": cfg.get("engine", "auto"),
        "mode": cfg.get("mode", "cloud_server_only"),
        "cloud_only": cfg.get("cloud_only", True),
        "stt_engine": cfg.get("stt_engine", "nisay-transcribe"),
        "translation_engine": cfg.get("translation_engine", "gemini-3.8-flash-high"),
        "has_cloud_engine": True,
        "gemini_api_key": cfg.get("gemini_api_key", ""),
        "keys": cfg.get("keys", []),
        "keys_raw": cfg.get("keys_raw", "\n".join(cfg.get("keys", []))),
        "model": cfg.get("model", "gemini-3.8-flash-high"),
        "temperature": cfg.get("temperature", 0.3),
        "prompt_style": cfg.get("prompt_style", "drama_dubbing")
    }
    return jsonify({
        "success": True,
        "config": safe_cfg,
        "active_keys_count": len([k for k in cfg.get("keys", []) if k.startswith("AIzaSy")]),
        "keys_raw": cfg.get("keys_raw", "\n".join(cfg.get("keys", [])))
    })


@app.route("/api/set-ai-config", methods=["POST"])
def set_ai_config_endpoint():
    data = request.get_json(force=True) or {}
    keys_raw = data.get("keys_raw", "")
    keys = data.get("keys", [])
    if not keys and keys_raw:
        keys = [k.strip() for k in keys_raw.replace(",", "\n").splitlines() if k.strip()]
    if not keys_raw and keys:
        keys_raw = "\n".join(keys)

    existing_cfg = load_stored_ai_config()
    groq_api_key = existing_cfg.get("groq_api_key", "")
    groq_keys = existing_cfg.get("groq_keys", [])

    gemini_api_key = data.get("gemini_api_key", "").strip()
    if gemini_api_key and gemini_api_key not in keys:
        keys.insert(0, gemini_api_key)

    engine = data.get("engine", "auto")
    model = data.get("model", "gemini-3.8-flash-high")
    try:
        temperature = float(data.get("temperature", 0.3))
    except Exception:
        temperature = 0.3
    prompt_style = data.get("prompt_style", "drama_dubbing")

    n_input = data.get("nisay_api_key", "").strip()
    saved_nisay = existing_cfg.get("nisay_api_key", "")
    if n_input and "••" not in n_input and n_input != "nisay-YOUR_API_KEY":
        saved_nisay = n_input
        os.environ["NISAY_API_KEY"] = n_input

    cfg = dict(existing_cfg)
    cfg.update({
        "engine": engine,
        "groq_api_key": groq_api_key,
        "groq_keys": groq_keys,
        "gemini_api_key": gemini_api_key,
        "keys": keys,
        "keys_raw": keys_raw,
        "model": model,
        "temperature": temperature,
        "prompt_style": prompt_style,
        "mode": existing_cfg.get("mode", "cloud_server_only"),
        "cloud_only": existing_cfg.get("cloud_only", True),
        "stt_engine": existing_cfg.get("stt_engine", "nisay-transcribe"),
        "translation_engine": existing_cfg.get("translation_engine", "gemini-3.8-flash-high"),
        "nisay_api_key": saved_nisay
    })

    AI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    valid_gemini = [k for k in keys if k.startswith("AIzaSy")]
    pm.translator.set_api_keys(valid_gemini)
    if valid_gemini:
        os.environ["GEMINI_API_KEY"] = "\n".join(valid_gemini)

    pm.translator.groq_api_key = groq_api_key
    pm.translator.groq_keys = groq_keys
    if groq_api_key:
        os.environ["GROQ_API_KEY"] = groq_api_key

    safe_cfg = {
        "engine": engine,
        "gemini_api_key": gemini_api_key,
        "keys": keys,
        "keys_raw": keys_raw,
        "model": model,
        "temperature": temperature,
        "prompt_style": prompt_style
    }

    return jsonify({
        "success": True,
        "config": safe_cfg,
        "message": "AI Studio Engine configuration saved successfully."
    })


@app.route("/api/drama-dictionary", methods=["GET", "POST"])
def drama_dictionary_endpoint():
    dict_file = get_data_file("drama_dictionary.json", create_dir=True)
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        entries = data.get("dictionary", data)
        if isinstance(entries, dict):
            dict_file.parent.mkdir(parents=True, exist_ok=True)
            with open(dict_file, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            return jsonify({"success": True, "dictionary": entries, "count": len(entries)})
        return jsonify({"success": False, "error": "Invalid dictionary format. Expected JSON object."}), 400

    # GET
    if dict_file.exists():
        try:
            with open(dict_file, "r", encoding="utf-8") as f:
                return jsonify({"success": True, "dictionary": json.load(f)})
        except Exception:
            pass
    return jsonify({"success": True, "dictionary": {}})


@app.route("/api/series/bible", methods=["GET", "POST"])
def series_bible_endpoint():
    """Retrieve or customize Drama Series Bible for 100% full series consistency."""
    from series_memory import series_memory
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        drama_title = data.get("title") or "Drama_Series"
        bible = series_memory.get_or_create_series_bible(drama_title)
        # Update user modifications
        for k in ("male_lead", "female_lead", "villain_or_rival", "glossary"):
            if k in data:
                bible[k] = data[k]
        bible_p = series_memory.get_bible_path(drama_title)
        with open(bible_p, "w", encoding="utf-8") as f:
            json.dump(bible, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True, "bible": bible})

    # GET
    title = request.args.get("title", "Drama_Series")
    bible = series_memory.get_or_create_series_bible(title)
    return jsonify({"success": True, "bible": bible})


@app.route("/api/series/merge", methods=["POST"])
def series_merge_endpoint():
    """Manually merge a list of dubbed episode videos into a single Full Movie (1-2 hours)."""
    data = request.get_json(force=True) or {}
    video_paths = data.get("video_paths", [])
    series_name = data.get("series_name", "Full_Drama")
    if not video_paths:
        return jsonify({"success": False, "error": "No video paths provided."}), 400

    from video_processor import merge_videos
    out_file = EXPORTS_DIR / f"Full_Movie_{series_name}.mp4"
    try:
        merge_videos(video_paths, str(out_file), auto_trim_freeze=True)
        return jsonify({
            "success": True,
            "output_video": str(out_file.resolve()).replace("\\", "/"),
            "filename": out_file.name
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/story-config", methods=["GET", "POST"])
def story_config_endpoint():
    cfg_file = get_data_file("story_config.json", create_dir=True)
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        cfg = {}
        if cfg_file.exists():
            try:
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                pass
        cfg.update(data)
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True, "config": cfg})

    # GET
    cfg = {}
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            pass
    return jsonify({"success": True, "config": cfg})



@app.route("/api/check-keys", methods=["POST"])
def check_keys_live_endpoint():
    data = request.get_json(force=True) or {}
    keys_raw = data.get("keys_raw", "")
    keys = data.get("keys", [])
    if not keys and keys_raw:
        keys = [k.strip() for k in keys_raw.replace(",", "\n").splitlines() if k.strip()]

    if not keys:
        return jsonify({"success": False, "error": "No API keys provided to check.", "total": 0, "valid": 0})

    results = []
    valid_count = 0

    for idx, key in enumerate(keys, start=1):
        masked = key[:6] + "..." + key[-4:] if len(key) > 10 else key
        status = "unknown"
        is_valid = False
        message = ""

        try:
            from google import genai
            client = genai.Client(api_key=key)
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="test",
                config={"max_output_tokens": 2}
            )
            is_valid = True
            status = "active"
            message = "Live (200 OK)"
            valid_count += 1
        except Exception as err:
            err_str = str(err)
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                status = "rate_limited"
                message = "Rate Limited (429)"
            elif any(token in err_str for token in ("401", "UNAUTHENTICATED", "API_KEY_INVALID", "400", "ACCESS_TOKEN")):
                status = "invalid"
                message = "Invalid Key (Need AIzaSy...)"
            else:
                status = "error"
                message = "Auth Failed"

        results.append({
            "index": idx,
            "key_masked": masked,
            "status": status,
            "valid": is_valid,
            "message": message
        })

    return jsonify({
        "success": True,
        "total": len(keys),
        "valid": valid_count,
        "results": results
    })


@app.route("/api/story-config", methods=["GET", "POST"])
def get_story_config_endpoint():
    if request.method == "POST":
        return set_story_config_endpoint()
    cfg = load_stored_story_config()
    ai_cfg = load_stored_ai_config()
    engine_name = ai_cfg.get("engine", "gemini_pool")
    if engine_name == "free_ai":
        provider_display = "Free AI (g4f)"
    elif engine_name == "google_free":
        provider_display = "Google Translate Built-in"
    elif engine_name == "gemini_pro":
        provider_display = "Gemini 2.5 Pro"
    else:
        provider_display = "Gemini API (Key Pool)"
        
    cfg["ai_provider_display"] = provider_display
    return jsonify({
        "success": True,
        "config": cfg
    })


@app.route("/api/set-story-config", methods=["POST"])
def set_story_config_endpoint():
    data = request.get_json(force=True) or {}
    cfg = load_stored_story_config()
    cfg.update(data)

    # Keep auto_multi_voice and khmer_voice synchronized
    if cfg.get("khmer_voice") == "multi":
        cfg["auto_multi_voice"] = True
    elif cfg.get("khmer_voice") in ("piseth", "sreymom"):
        cfg["auto_multi_voice"] = False

    # Sanitize ducking_volume so it is never empty or invalid
    raw_duck = str(cfg.get("ducking_volume", "")).strip()
    try:
        val = float(raw_duck)
        if val < 0:
            cfg["ducking_volume"] = "0.15"
        else:
            cfg["ducking_volume"] = f"{val:.2f}"
    except (ValueError, TypeError):
        cfg["ducking_volume"] = "0.15"

    STORY_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STORY_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    return jsonify({
        "success": True,
        "message": "Story settings saved successfully!",
        "config": cfg
    })



# ==========================================================================
# License & Security REST APIs
# ==========================================================================
@app.route("/api/license/status", methods=["GET"])
def license_status_endpoint():
    """Check device license status & HWID."""
    info = check_current_device_license()
    try:
        from update import get_local_version
        info["app_version"] = get_local_version()
    except Exception:
        info["app_version"] = "1.0.7"

    cfg_path = get_data_file("license_config.json")
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                info["telegram_link"] = cfg.get("telegram_link", "https://t.me/")
                info["facebook_link"] = cfg.get("facebook_link", "https://facebook.com/")
        except Exception:
            pass
    return jsonify(info)


_FAILED_ACTIVATION_ATTEMPTS = {}

@app.route("/api/license/activate", methods=["POST"])
def license_activate_endpoint():
    """Activate license key on this device with brute-force ban defense."""
    banned, reason = is_current_device_banned()
    if banned:
        return jsonify({
            "success": False,
            "error": "DEVICE_PERMANENTLY_BANNED",
            "message": f"⛔ ឧបករណ៍កុំព្យូទ័រនេះត្រូវបានចាក់សោរជាអចិន្ត្រៃយ៍! ({reason})"
        }), 403

    data = request.get_json(force=True) or {}
    key = data.get("license_key", "").strip()
    client_name = data.get("client_name", "").strip() or None
    if not key:
        return jsonify({"success": False, "error": "Please enter License Key", "message": "Please enter License Key"}), 400

    success, msg, record = activate_license_on_device(key, client_name=client_name)
    hwid = get_machine_hwid()
    if not success:
        _FAILED_ACTIVATION_ATTEMPTS[hwid] = _FAILED_ACTIVATION_ATTEMPTS.get(hwid, 0) + 1
        if _FAILED_ACTIVATION_ATTEMPTS[hwid] >= 5:
            record_permanent_device_ban("Excessive failed license key activation attempts (Brute Force)")
            return jsonify({
                "success": False,
                "error": "DEVICE_PERMANENTLY_BANNED",
                "message": "⛔ ឧបករណ៍កុំព្យូទ័ររបស់អ្នកត្រូវបានចាក់សោរជាអចិន្ត្រៃយ៍ ដោយសារការវាយបញ្ចូល Key ខុសច្រើនដង!"
            }), 403
    else:
        _FAILED_ACTIVATION_ATTEMPTS.pop(hwid, None)

    return jsonify({
        "success": success,
        "message": msg,
        "error": None if success else msg,
        "license": record
    })


@app.route("/api/license/unban", methods=["POST"])
def license_unban_endpoint():
    """Admin Emergency Override to unban a machine."""
    data = request.get_json(force=True) or {}
    unban_code = data.get("unban_code", "").strip()
    hwid = data.get("hwid", "").strip() or get_machine_hwid()
    success, msg = unban_device(hwid, unban_code)
    return jsonify({"success": success, "message": msg})


@app.route("/api/update/check", methods=["GET"])
def update_check_endpoint():
    """Check for latest studio version and patch notes."""
    token = request.args.get("token") or os.environ.get("GITHUB_TOKEN")
    return jsonify(check_for_updates(github_token=token))


@app.route("/api/update/apply", methods=["POST"])
def update_apply_endpoint():
    """Apply update via Google Drive Cloud direct zip download (100% resilient)."""
    data = request.get_json(silent=True) or {}
    download_url = data.get("download_url", "")
    if not download_url:
        chk = check_for_updates()
        download_url = chk.get("download_url") or "https://drive.usercontent.google.com/download?id=1x_k269mEwMPH01tx8o6N67QEtLz7jlUo&export=download&confirm=t"
    res = apply_zip_download_update(download_url, APP_DIR)
    return jsonify(res)



# ==========================================================================
# Downloader Studio REST APIs
# ==========================================================================
@app.route("/api/downloader/platforms", methods=["GET"])
def downloader_platforms_endpoint():
    """Get list of supported drama download platforms."""
    try:
        platforms = get_supported_platforms_with_counts()
        return jsonify({"success": True, "platforms": platforms})
    except Exception as e:
        default_platforms = [
            {"id": "all", "name": "All platforms", "icon": "fa-solid fa-globe", "count": 633672},
            {"id": "hongguo", "name": "Hongguo", "logo": "hongguo_logo.png", "icon": "fa-solid fa-play", "count": 49591},
            {"id": "shortmax", "name": "ShortMax", "logo": "shortmax_logo.png", "icon": "fa-solid fa-play", "count": 120000},
            {"id": "ai_drama", "name": "AI Dramas", "logo": "ai_drama_logo.png", "icon": "fa-solid fa-robot", "count": 24081},
            {"id": "reelshort", "name": "ReelShort", "logo": "reelshort_logo.png", "icon": "fa-solid fa-play", "count": 120000},
            {"id": "freereels", "name": "FreeReels", "logo": "freereels_logo.png", "icon": "fa-solid fa-play", "count": 120000},
            {"id": "anyreel", "name": "AnyReel", "logo": "anyreel_logo.png", "icon": "fa-solid fa-play", "count": 200000},
        ]
        return jsonify({"success": True, "platforms": default_platforms, "fallback": True})


@app.route("/api/downloader/categories", methods=["GET"])
def downloader_categories_endpoint():
    """Get list of Hongguo drama categories."""
    return jsonify({"success": True, "categories": hongguo_db.get_categories_list()})


@app.route("/api/downloader/catalog", methods=["GET"])
def downloader_catalog_endpoint():
    """Get list of catalog dramas with optional platform, category, pagination & search filters."""
    platform = request.args.get("platform", "all").lower()
    category = request.args.get("category", "all").lower()
    query = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 60))
    offset = max(0, (page - 1) * limit)

    dramas, total_count = hongguo_db.query_dramas(
        category=category if category != "all" else None,
        query=query if query else None,
        platform=platform if platform != "all" else None,
        limit=limit,
        offset=offset
    )

    return jsonify({
        "success": True,
        "dramas": dramas,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "has_more": (offset + len(dramas)) < total_count
    })


@app.route("/api/downloader/analyze", methods=["POST"])
def downloader_analyze_endpoint():
    """Analyze drama URL or fetch drama episode manifest."""
    data = request.get_json(force=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "URL cannot be empty."}), 400

    try:
        res = drama_downloader.analyze_url(url)
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/downloader/drama/<drama_id>", methods=["GET"])
def downloader_drama_detail_endpoint(drama_id):
    """Get single drama details with full episodes and rich story profile."""
    drama = hongguo_db.get_drama_by_id(drama_id)
    if not drama:
        drama = next((d for d in DRAMA_CATALOG if d.get("id") == drama_id), None)
    if not drama and drama_downloader.current_drama and drama_downloader.current_drama.get("id") == drama_id:
        drama = drama_downloader.current_drama

    if not drama:
        return jsonify({"success": False, "error": "Drama not found"}), 404

    if drama_downloader.is_downloading and drama_downloader.current_drama and str(drama_downloader.current_drama.get("id")) == str(drama_id):
        return jsonify({
            "success": True,
            "drama": drama_downloader.current_drama,
            "episodes": drama_downloader.episodes,
            "stats": drama_downloader.stats
        })

    episodes = get_drama_episodes(drama)
    drama_downloader.current_drama = drama
    drama_downloader.episodes = episodes
    drama_downloader.stats["total"] = len(episodes)
    drama_downloader.stats["selected"] = len(episodes)
    drama_downloader.stats["completed"] = 0
    drama_downloader.stats["failed"] = 0
    drama_downloader.stats["locked"] = 0

    return jsonify({
        "success": True,
        "drama": drama,
        "episodes": episodes,
        "stats": drama_downloader.stats
    })


@app.route("/api/downloader/preview/<drama_id>", methods=["GET"])
def downloader_preview_endpoint(drama_id):
    """Get authentic preview video for a drama to play directly in 9:16 monitor."""
    ep_num = request.args.get("ep", 1, type=int)
    drama = hongguo_db.get_drama_by_id(drama_id)
    if not drama and drama_downloader.current_drama:
        if str(drama_downloader.current_drama.get("id")) == str(drama_id):
            drama = drama_downloader.current_drama

    # 1. Check if active episodes manifest has a genuine video file for this episode
    if drama_downloader.episodes:
        for ep in drama_downloader.episodes:
            if ep.get("episode_number") == ep_num or ep.get("episode_num") == ep_num:
                if ep.get("video_url") and ep.get("filepath") and Path(ep["filepath"]).exists():
                    return jsonify({
                        "success": True,
                        "video_url": ep["video_url"],
                        "title": ep.get("title") or (drama.get("title") if drama else f"Episode {ep_num}"),
                        "poster": drama.get("poster") if drama else "posters/poster_sample_ceo.jpg",
                        "episode": ep_num
                    })

    # 2. Check if authentic video file exists in save location or imported folder
    auth_src = find_authentic_episode_video(drama, ep_num)
    if auth_src and auth_src.exists():
        rel_or_abs = str(auth_src.resolve()).replace("\\", "/")
        return jsonify({
            "success": True,
            "video_url": f"/media/{rel_or_abs}",
            "title": drama.get("title") if drama else "Hongguo Short Drama",
            "poster": drama.get("poster") if drama else "posters/poster_sample_ceo.jpg",
            "episode": ep_num
        })

    # 2.5 Special handler for ShortMax preview video
    is_shortmax = (drama and drama.get("platform_id") == "shortmax") or str(drama_id).startswith("shortmax_")
    if is_shortmax:
        sp_id_str = str(drama_id).replace("shortmax_", "").strip()
        try:
            sp_id = int(sp_id_str)
        except Exception:
            sp_id = 0
        if sp_id:
            pv_path = shortmax_service.get_or_create_preview_video(sp_id, ep_num)
            if pv_path and pv_path.exists():
                rel_or_abs = str(pv_path.resolve()).replace("\\", "/")
                return jsonify({
                    "success": True,
                    "video_url": f"/media/{rel_or_abs}",
                    "title": drama.get("title") if drama else f"Episode {ep_num}",
                    "poster": drama.get("poster") if drama else "posters/poster_sample_ceo.jpg",
                    "episode": ep_num
                })

    # 2.6 Special handler for ReelShort preview video
    is_reelshort = (drama and drama.get("platform_id") == "reelshort") or str(drama_id).startswith("reelshort_")
    if is_reelshort:
        import reelshort_service
        pv_path = reelshort_service.get_or_create_preview_video(str(drama_id), ep_num)
        if pv_path and pv_path.exists():
            rel_or_abs = str(pv_path.resolve()).replace("\\", "/")
            return jsonify({
                "success": True,
                "video_url": f"/media/{rel_or_abs}",
                "title": drama.get("title") if drama else f"Episode {ep_num}",
                "poster": drama.get("poster") if drama else "reelshort_logo.png",
                "episode": ep_num
            })

    # 3. If authentic live stream is available, provide direct stream URL for 9:16 preview
    if drama_downloader.episodes:
        for ep in drama_downloader.episodes:
            if ep.get("episode_number") == ep_num or ep.get("episode_num") == ep_num:
                s_url = ep.get("stream_url") or ep.get("download_url")
                if (not s_url or not str(s_url).startswith("http")) and ep.get("vid") and ep.get("series_id"):
                    s_url = get_hongguo_episode_real_stream_url(ep["series_id"], ep["vid"])
                    if s_url:
                        ep["stream_url"] = s_url
                        ep["download_url"] = s_url
                if s_url and str(s_url).startswith("http"):
                    return jsonify({
                        "success": True,
                        "video_url": s_url,
                        "stream_url": s_url,
                        "is_live_stream": True,
                        "title": ep.get("title") or (drama.get("title") if drama else f"Episode {ep_num}"),
                        "poster": drama.get("poster") if drama else "posters/poster_sample_ceo.jpg",
                        "episode": ep_num
                    })

    return jsonify({
        "success": False,
        "error": "no_video",
        "message": f"Episode {ep_num} is not downloaded locally yet",
        "poster": drama.get("poster") if drama else "posters/poster_sample_ceo.jpg",
        "episode": ep_num
    }), 404


@app.route("/api/downloader/import-folder", methods=["POST", "GET"])
def downloader_import_folder_endpoint():
    """
    Import an authentic local short drama folder containing downloaded episode video files.
    If folder_path is not provided, opens native Windows folder chooser dialog.
    """
    folder_path = ""
    if request.is_json:
        data = request.get_json(silent=True) or {}
        folder_path = data.get("folder_path", "").strip()
    elif request.form.get("folder_path"):
        folder_path = request.form.get("folder_path", "").strip()

    if not folder_path:
        folder_path = open_native_windows_folder_dialog(
            title="Select Downloaded Drama Folder"
        )
        if not folder_path:
            return jsonify({"success": False, "cancelled": True, "message": "Folder selection cancelled"})

    res = drama_downloader.import_drama_from_folder(folder_path)
    return jsonify(res)


@app.route("/api/downloader/send-to-studio", methods=["POST"])
def downloader_send_to_studio_endpoint():
    """Send an authentic downloaded or imported episode video directly to AI Studio Dubber."""
    data = request.get_json(force=True) or {}
    filepath = data.get("filepath", "").strip()
    filename = data.get("filename", "")
    drama_title = data.get("drama_title", "")

    if not filepath or not Path(filepath).exists():
        return jsonify({"success": False, "error": "Video file path does not exist on disk"}), 400

    p = Path(filepath)
    sz = p.stat().st_size
    sz_mb = f"{sz / (1024 * 1024):.1f}"

    return jsonify({
        "success": True,
        "filepath": str(p.resolve()).replace("\\", "/"),
        "filename": filename or p.name,
        "size_mb": sz_mb,
        "drama_title": drama_title or p.stem,
        "video_url": f"/media/{str(p.resolve()).replace(chr(92), '/')}"
    })


@app.route("/api/downloader/download-episodes", methods=["POST"])
def downloader_download_episodes_endpoint():
    """Start batch download for selected episodes with turbo concurrency and auto full drama merge."""
    data = request.get_json(force=True) or {}
    episode_ids = data.get("episode_ids", [])
    save_location = data.get("save_location") or str(resolve_safe_save_location()).replace("\\", "/")
    save_poster = data.get("save_poster", True)
    auto_merge_full = data.get("auto_merge_full", False)
    
    res = drama_downloader.start_download_batch(episode_ids, save_location, save_poster, auto_merge_full=auto_merge_full)
    return jsonify(res)


@app.route("/api/downloader/download_poster", methods=["POST"])
def downloader_download_poster_endpoint():
    """Download authentic high-resolution drama poster to local computer and return media link."""
    data = request.get_json(force=True) or {}
    poster_url = data.get("poster_url", "")
    drama_id = data.get("drama_id", "")
    title = data.get("title", "Drama")
    save_location = data.get("save_location") or str(resolve_safe_save_location()).replace("\\", "/")
    
    if not poster_url and drama_id:
        d_info = hongguo_db.get_drama_by_id(drama_id)
        if d_info:
            poster_url = d_info.get("poster") or d_info.get("cover_url")
            if not title or title == "Drama":
                title = d_info.get("title_cn") or d_info.get("title") or "Drama"
                
    if not poster_url:
        return jsonify({"success": False, "message": "No poster URL available"}), 400

    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip() or "Drama"
    dest_dir = Path(save_location) / safe_title
    dest_dir.mkdir(parents=True, exist_ok=True)
    poster_file = dest_dir / f"{safe_title}_Poster.jpg"
    
    cmd = [
        'curl.exe', '-4', '-s', '-m', '20',
        '-A', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        '-o', str(poster_file),
        poster_url
    ]
    try:
        subprocess.run(cmd, timeout=25)
        if poster_file.exists() and poster_file.stat().st_size > 500:
            return jsonify({
                "success": True,
                "message": "Poster downloaded successfully",
                "path": str(poster_file),
                "filename": f"{safe_title}_Poster.jpg",
                "file_url": f"/media/{str(poster_file.resolve()).replace(chr(92), '/')}"
            })
    except Exception as e:
        return jsonify({"success": False, "message": f"Download failed: {e}"}), 500
        
    return jsonify({"success": False, "message": "Failed to download poster file"}), 500


@app.route("/api/downloader/queue", methods=["GET", "POST", "DELETE"])
def downloader_queue_endpoint():
    """Manage multi-drama batch download queue."""
    if request.method == "GET":
        return jsonify({
            "queue": drama_downloader.get_queue(),
            "queue_active": drama_downloader.queue_active,
            "is_downloading": drama_downloader.is_downloading
        })
    elif request.method == "POST":
        data = request.get_json(silent=True) or {}
        drama_data = data.get("drama") or drama_downloader.current_drama
        save_loc = data.get("save_location") or str(resolve_safe_save_location()).replace("\\", "/")
        if not drama_data:
            return jsonify({"success": False, "error": "No drama data provided"}), 400
        res = drama_downloader.add_to_queue(drama_data, save_loc)
        return jsonify(res)
    elif request.method == "DELETE":
        res = drama_downloader.clear_queue()
        return jsonify(res)


@app.route("/api/downloader/queue/start", methods=["POST"])
def downloader_queue_start_endpoint():
    """Start automated sequential processing of all queued dramas."""
    data = request.get_json(silent=True) or {}
    save_loc = data.get("save_location") or str(resolve_safe_save_location()).replace("\\", "/")
    res = drama_downloader.start_queue(save_loc)
    return jsonify(res)


@app.route("/api/downloader/merge-full", methods=["POST"])
def downloader_merge_full_endpoint():
    """Manually merge downloaded drama episodes into 1 Full Drama Video."""
    data = request.get_json(silent=True) or {}
    folder = data.get("folder") or drama_downloader.last_download_dir
    res = merge_downloaded_drama_episodes(folder)
    return jsonify(res)


@app.route("/api/downloader/status", methods=["GET"])
def downloader_status_endpoint():
    """Poll real-time downloader status, episodes state, and activity logs."""
    return jsonify({
        "is_downloading": drama_downloader.is_downloading,
        "drama": drama_downloader.current_drama,
        "episodes": drama_downloader.episodes,
        "logs": drama_downloader.logs,
        "stats": drama_downloader.stats,
        "last_download_dir": drama_downloader.last_download_dir
    })


@app.route("/api/downloader/open-folder", methods=["POST", "GET"])
def downloader_open_folder_endpoint():
    """Open drama download folder directly in Windows File Explorer."""
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.args
    
    target_folder = data.get("folder") or drama_downloader.last_download_dir
    if not target_folder:
        if drama_downloader.current_drama:
            raw_title = drama_downloader.current_drama.get("title_cn") or drama_downloader.current_drama.get("title", "Drama")
            safe_title = re.sub(r'[\\/*?:"<>|《》]', "_", raw_title).strip() or "Hongguo_Drama"
            base_dir = "D:/SN_Dramas" if os.path.exists("D:/") else "C:/SN_Dramas"
            target_folder = os.path.join(base_dir, safe_title)
        else:
            target_folder = "D:/SN_Dramas" if os.path.exists("D:/") else "C:/SN_Dramas"

    try:
        p = resolve_safe_save_location(target_folder)
    except Exception:
        p = Path(target_folder)
        p.mkdir(parents=True, exist_ok=True)

    try:
        hongguo_service.standardize_folder(p)
        hongguo_service.clean_stray_download_artifacts(p)
    except Exception:
        pass

    try:
        resolved_str = str(p.resolve()).replace("/", "\\")
        if sys.platform == "win32":
            os.startfile(resolved_str)
        else:
            subprocess.Popen(["xdg-open", resolved_str])
        return jsonify({"success": True, "path": resolved_str})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/downloader/stop", methods=["POST"])
def downloader_stop_endpoint():
    """Stop active download queue."""
    return jsonify(drama_downloader.stop_download())


@app.route("/api/downloader/clear-log", methods=["POST"])
def downloader_clear_log_endpoint():
    """Clear downloader activity log."""
    drama_downloader.logs = [f"[{time.strftime('%H:%M:%S')}] Activity log cleared."]
    return jsonify({"success": True})


# ==========================================================================
# System / Folder Picker & File Explorer REST APIs
# ==========================================================================
@app.route("/api/system/default-paths", methods=["GET"])
def system_default_paths_endpoint():
    """Return clean standard Drive C: and Drive D: paths for saving downloaded media."""
    try:
        from downloader import resolve_safe_save_location
        safe_default = str(resolve_safe_save_location()).replace("\\", "/")
    except Exception:
        safe_default = str(Path.home() / "Downloads" / "SN_Dramas").replace("\\", "/")

    # Check if C:/SN_Dramas is writable without UAC error on standard user account
    drive_c = "C:/SN_Dramas"
    try:
        c_cand = Path("C:/SN_Dramas")
        c_cand.mkdir(parents=True, exist_ok=True)
        test_f = c_cand / f".write_test_{os.getpid()}"
        test_f.write_text("ok", encoding="utf-8")
        test_f.unlink(missing_ok=True)
    except Exception:
        drive_c = str(Path.home() / "Downloads" / "SN_Dramas").replace("\\", "/")

    drive_d = "D:/SN_Dramas" if os.path.exists("D:/") else drive_c
    
    return jsonify({
        "success": True,
        "default": safe_default,
        "drive_c": drive_c,
        "drive_d": drive_d,
        "has_drive_d": os.path.exists("D:/")
    })


def get_app_icon_path() -> str:
    """Find absolute path to application icon across development and compiled exe runtime."""
    candidates = [
        APP_DIR / "icon.ico",
        BASE_DIR / "icon.ico",
        STATIC_DIR / "favicon.ico",
        STATIC_DIR / "icon.ico",
        Path(__file__).resolve().parent / "icon.ico",
        Path(__file__).resolve().parent / "static" / "favicon.ico",
        Path.cwd() / "icon.ico",
    ]
    for p in candidates:
        try:
            if p.exists() and p.is_file():
                return str(p.resolve()).replace("\\", "/")
        except Exception:
            pass
    return ""


APP_ICON_PATH = get_app_icon_path()

MODERN_DIALOG_HELPER_CS = """
using System;
using System.IO;
using System.Threading;
using System.Runtime.InteropServices;

[ComImport]
[Guid("00000114-0000-0000-C000-000000000046")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IOleWindow {
    [PreserveSig] int GetWindow(out IntPtr phwnd);
    [PreserveSig] int ContextSensitiveHelp(bool fEnterMode);
}

[ComImport]
[Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IShellItem {
    void BindToHandler();
    void GetParent();
    void GetDisplayName(uint sigdnName, [MarshalAs(UnmanagedType.LPWStr)] out string ppszName);
    void GetAttributes();
    void Compare();
}

[ComImport]
[Guid("973510DB-7D7F-452B-8975-74A85828D354")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IFileDialogEvents {
    [PreserveSig] int OnFileOk(IntPtr pfd);
    [PreserveSig] int OnFolderChanging(IntPtr pfd, IntPtr psiFolder);
    [PreserveSig] int OnFolderChange(IntPtr pfd);
    [PreserveSig] int OnSelectionChange(IntPtr pfd);
    [PreserveSig] int OnShareViolation(IntPtr pfd, IntPtr psi, out int pResponse);
    [PreserveSig] int OnTypeChange(IntPtr pfd);
    [PreserveSig] int OnOverwrite(IntPtr pfd, IntPtr psi, out int pResponse);
}

[ComImport]
[Guid("DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7")]
public class FileOpenDialog { }

[ComImport]
[Guid("42f85136-db7e-439c-85f1-e4075d135fc8")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
public interface IFileOpenDialog {
    [PreserveSig] int Show(IntPtr parent);
    void SetFileTypes();
    void SetFileTypeIndex();
    void GetFileTypeIndex();
    void Advise(IFileDialogEvents pfde, out uint pdwCookie);
    void Unadvise(uint dwCookie);
    void SetOptions(uint fos);
    void GetOptions(out uint fos);
    void SetDefaultFolder(IShellItem psi);
    void SetFolder(IShellItem psi);
    void GetFolder(out IShellItem ppsi);
    void GetCurrentSelection(out IShellItem ppsi);
    void SetFileName([MarshalAs(UnmanagedType.LPWStr)] string pszName);
    void GetFileName([MarshalAs(UnmanagedType.LPWStr)] out string pszName);
    void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string pszTitle);
    void SetOkButtonLabel([MarshalAs(UnmanagedType.LPWStr)] string pszText);
    void SetFileNameLabel([MarshalAs(UnmanagedType.LPWStr)] string pszLabel);
    void GetResult(out IShellItem ppsi);
    void AddPlace();
    void SetDefaultExtension();
    void Close();
    void SetClientGuid();
    void ClearClientData();
    void SetFilter();
    void GetResults();
    void GetSelectedItems();
}

public class DialogEventHandler : IFileDialogEvents {
    private object _dialog;
    private string _iconPath;
    public DialogEventHandler(object dialog, string iconPath) {
        _dialog = dialog;
        _iconPath = iconPath;
    }

    public int OnFolderChange(IntPtr pfd) {
        try {
            var ole = _dialog as IOleWindow;
            if (ole != null) {
                IntPtr hwnd;
                if (ole.GetWindow(out hwnd) == 0) {
                    NativeDialogHelper.ApplyStyleAndIcon(hwnd, _iconPath);
                }
            }
        } catch { }
        return 0;
    }

    public int OnFileOk(IntPtr pfd) { return 0; }
    public int OnFolderChanging(IntPtr pfd, IntPtr psiFolder) {
        try {
            var ole = _dialog as IOleWindow;
            if (ole != null) {
                IntPtr hwnd;
                if (ole.GetWindow(out hwnd) == 0) {
                    NativeDialogHelper.ApplyStyleAndIcon(hwnd, _iconPath);
                }
            }
        } catch { }
        return 0;
    }
    public int OnSelectionChange(IntPtr pfd) { return 0; }
    public int OnShareViolation(IntPtr pfd, IntPtr psi, out int pResponse) { pResponse = 0; return 0; }
    public int OnTypeChange(IntPtr pfd) { return 0; }
    public int OnOverwrite(IntPtr pfd, IntPtr psi, out int pResponse) { pResponse = 0; return 0; }
}

public static class NativeDialogHelper {
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetProcessDpiAwarenessContext(IntPtr dpiContext);

    [DllImport("shcore.dll", SetLastError = true)]
    public static extern int SetProcessDpiAwareness(int awareness);

    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool SetProcessDPIAware();

    [DllImport("user32.dll")]
    private static extern int GetSystemMetrics(int nIndex);

    private const int SM_CXICON = 11;
    private const int SM_CYICON = 12;
    private const int SM_CXSMICON = 49;
    private const int SM_CYSMICON = 50;

    public static bool EnableHighDpi() {
        try {
            // Per-Monitor V2 High DPI Awareness (eliminates blurriness on 125%, 150%, 175%, 200% scaling)
            if (SetProcessDpiAwarenessContext((IntPtr)(-4))) {
                return true;
            }
        } catch { }
        try {
            if (SetProcessDpiAwareness(2) == 0) {
                return true;
            }
        } catch { }
        try {
            return SetProcessDPIAware();
        } catch { }
        return false;
    }

    [DllImport("shell32.dll")]
    private static extern int SHCreateItemFromParsingName(
        [MarshalAs(UnmanagedType.LPWStr)] string pszPath,
        IntPtr pbc,
        [In, MarshalAs(UnmanagedType.LPStruct)] Guid riid,
        [Out, MarshalAs(UnmanagedType.Interface)] out IShellItem ppv);

    [DllImport("dwmapi.dll")]
    public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll", CharSet = CharSet.Auto, SetLastError = true)]
    public static extern IntPtr LoadImage(IntPtr hinst, string lpszName, uint uType, int cxDesired, int cyDesired, uint fuLoad);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    public const int DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19;
    public const int DWMWA_USE_IMMERSIVE_DARK_MODE = 20;

    private const uint WM_SETICON = 0x0080;
    private const uint IMAGE_ICON = 1;
    private const uint LR_LOADFROMFILE = 0x00000010;

    public static void ApplyStyleAndIcon(IntPtr hwnd, string iconPath) {
        if (hwnd == IntPtr.Zero) return;
        try {
            int darkMode = 1;
            DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ref darkMode, sizeof(int));
            DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1, ref darkMode, sizeof(int));

            if (!string.IsNullOrEmpty(iconPath) && File.Exists(iconPath)) {
                int cxSmall = GetSystemMetrics(SM_CXSMICON);
                int cySmall = GetSystemMetrics(SM_CYSMICON);
                int cxBig = GetSystemMetrics(SM_CXICON);
                int cyBig = GetSystemMetrics(SM_CYICON);
                if (cxSmall <= 0) cxSmall = 16;
                if (cySmall <= 0) cySmall = 16;
                if (cxBig <= 0) cxBig = 32;
                if (cyBig <= 0) cyBig = 32;

                IntPtr hSmall = LoadImage(IntPtr.Zero, iconPath, IMAGE_ICON, cxSmall, cySmall, LR_LOADFROMFILE);
                if (hSmall != IntPtr.Zero) {
                    SendMessage(hwnd, WM_SETICON, (IntPtr)0, hSmall);
                }
                IntPtr hBig = LoadImage(IntPtr.Zero, iconPath, IMAGE_ICON, cxBig, cyBig, LR_LOADFROMFILE);
                if (hBig != IntPtr.Zero) {
                    SendMessage(hwnd, WM_SETICON, (IntPtr)1, hBig);
                }
            }
            SetForegroundWindow(hwnd);
        } catch { }
    }

    public static void WatchAndStyleDialog(IntPtr ownerHwnd, string iconPath) {
        ThreadPool.QueueUserWorkItem(_ => {
            for (int i = 0; i < 40; i++) {
                Thread.Sleep(30);
                IntPtr fg = GetForegroundWindow();
                if (fg != IntPtr.Zero && fg != ownerHwnd) {
                    ApplyStyleAndIcon(fg, iconPath);
                    break;
                }
            }
        });
    }

    public static string ShowFolderDialog(string initialPath, string title, string iconPath, IntPtr owner) {
        EnableHighDpi();
        var dialog = (IFileOpenDialog)new FileOpenDialog();
        uint FOS_PICKFOLDERS = 0x00000020;
        uint FOS_FORCEFILESYSTEM = 0x00000040;
        uint FOS_NOVALIDATE = 0x00000100;
        uint FOS_NOTESTFILECREATE = 0x00010000;
        uint FOS_PATHMUSTEXIST = 0x00000800;
        dialog.SetOptions(FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_NOVALIDATE | FOS_NOTESTFILECREATE | FOS_PATHMUSTEXIST);

        if (!string.IsNullOrEmpty(title)) {
            dialog.SetTitle(title);
            dialog.SetOkButtonLabel("Select Folder");
        }

        if (!string.IsNullOrEmpty(initialPath) && Directory.Exists(initialPath)) {
            IShellItem folderItem;
            Guid riid = new Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE");
            if (SHCreateItemFromParsingName(initialPath, IntPtr.Zero, riid, out folderItem) == 0) {
                dialog.SetFolder(folderItem);
            }
        }

        uint cookie = 0;
        var handler = new DialogEventHandler(dialog, iconPath);
        try {
            dialog.Advise(handler, out cookie);
        } catch { }

        // Proactively style and set icon immediately as soon as window is shown
        ThreadPool.QueueUserWorkItem(_ => {
            for (int i = 0; i < 30; i++) {
                Thread.Sleep(30);
                IntPtr hwnd = IntPtr.Zero;
                try {
                    var ole = dialog as IOleWindow;
                    if (ole != null) {
                        ole.GetWindow(out hwnd);
                    }
                } catch { }
                if (hwnd != IntPtr.Zero) {
                    ApplyStyleAndIcon(hwnd, iconPath);
                    break;
                }
            }
        });

        int hr = dialog.Show(owner);

        if (cookie != 0) {
            try { dialog.Unadvise(cookie); } catch { }
        }

        if (hr == 0) {
            IShellItem result;
            dialog.GetResult(out result);
            string path;
            result.GetDisplayName(0x80058000, out path); // SIGDN_FILESYSPATH
            return path;
        }
        return null;
    }
}
"""


def open_native_windows_folder_dialog(initial_dir: str = "", title: str = "Select Drama Series Folder") -> Optional[str]:
    """
    Open modern native Windows File Explorer folder picker (IFileOpenDialog with FOS_PICKFOLDERS).
    Displays only the single native Windows Explorer window with folder icons, breadcrumbs, search bar,
    and sidebar navigation. When the user cancels, it closes cleanly with no second popup window.
    """
    if not initial_dir or not os.path.exists(initial_dir):
        initial_dir = "D:/" if os.path.exists("D:/") else "C:/"

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes, POINTER, c_void_p, c_ulong, c_wchar_p, Structure, byref, WINFUNCTYPE, c_uint, c_long

            class GUID(Structure):
                _fields_ = [
                    ("Data1", wintypes.DWORD),
                    ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD),
                    ("Data4", wintypes.BYTE * 8)
                ]

            CLSID_FileOpenDialog = GUID(0xDC1C5A9C, 0xE88A, 0x4DDE, (wintypes.BYTE * 8)(0xA5, 0xA1, 0x60, 0xF8, 0x2A, 0x20, 0xAE, 0xF7))
            IID_IFileOpenDialog  = GUID(0xd57c7288, 0xd4ad, 0x4768, (wintypes.BYTE * 8)(0xbe, 0x02, 0x9d, 0x96, 0x95, 0x32, 0xd9, 0x60))
            IID_IShellItem       = GUID(0x43826D1E, 0xE718, 0x42EE, (wintypes.BYTE * 8)(0xBC, 0x55, 0xA1, 0xE2, 0x61, 0xC3, 0x7B, 0xFE))

            FOS_PICKFOLDERS      = 0x00000020
            FOS_FORCEFILESYSTEM  = 0x00000040
            FOS_PATHMUSTEXIST    = 0x00000800
            SIGDN_FILESYSPATH    = 0x80058000

            ole32 = ctypes.windll.ole32
            shell32 = ctypes.windll.shell32
            user32 = ctypes.windll.user32

            ole32.CoInitialize(None)
            p_dialog = c_void_p()
            hr = ole32.CoCreateInstance(byref(CLSID_FileOpenDialog), None, 1, byref(IID_IFileOpenDialog), byref(p_dialog))
            if hr == 0 and p_dialog:
                def v_call(ptr, idx, restype, argtypes, *args):
                    vt = ctypes.cast(ptr, POINTER(POINTER(c_void_p))).contents
                    proto = WINFUNCTYPE(restype, *argtypes)
                    return proto(vt[idx])(ptr, *args)

                try:
                    # SetOptions (index 9): FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST
                    v_call(p_dialog, 9, c_long, [c_void_p, c_uint], c_uint(FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_PATHMUSTEXIST))

                    # SetTitle (index 17)
                    if title:
                        v_call(p_dialog, 17, c_long, [c_void_p, c_wchar_p], str(title))

                    # SetOkButtonLabel (index 18)
                    v_call(p_dialog, 18, c_long, [c_void_p, c_wchar_p], "Select Folder")

                    # Set initial folder (index 12) if exists
                    if initial_dir and os.path.exists(initial_dir):
                        p_item = c_void_p()
                        hr_item = shell32.SHCreateItemFromParsingName(
                            c_wchar_p(os.path.abspath(initial_dir)),
                            None,
                            byref(IID_IShellItem),
                            byref(p_item)
                        )
                        if hr_item == 0 and p_item:
                            v_call(p_dialog, 12, c_long, [c_void_p, c_void_p], p_item)
                            v_call(p_item, 2, c_ulong, [c_void_p])

                    # Show dialog modal to active foreground window (index 3)
                    hwnd = user32.GetForegroundWindow()
                    hr_show = v_call(p_dialog, 3, c_long, [c_void_p, wintypes.HWND], hwnd)
                    if hr_show == 0:
                        # GetResult (index 20)
                        p_result = c_void_p()
                        hr_res = v_call(p_dialog, 20, c_long, [c_void_p, POINTER(c_void_p)], byref(p_result))
                        if hr_res == 0 and p_result:
                            p_path_str = c_wchar_p()
                            hr_name = v_call(p_result, 5, c_long, [c_void_p, c_uint, POINTER(c_wchar_p)], SIGDN_FILESYSPATH, byref(p_path_str))
                            chosen_path = None
                            if hr_name == 0 and p_path_str.value:
                                chosen_path = str(Path(p_path_str.value).resolve()).replace("\\", "/")
                                ole32.CoTaskMemFree(p_path_str)
                            v_call(p_result, 2, c_ulong, [c_void_p])
                            if chosen_path and os.path.exists(chosen_path):
                                return chosen_path
                    # User clicked Cancel, pressed Esc, or closed the window -> return None cleanly without popping any second window
                    return None
                except Exception:
                    return None
                finally:
                    v_call(p_dialog, 2, c_ulong, [c_void_p])
                    ole32.CoUninitialize()
        except Exception as ce:
            print(f"[Modern Folder Dialog] note: {ce}")
            return None

    return None


def open_native_windows_files_dialog(initial_dir: str = "", title: str = "Select Video Files for Drama Series") -> List[str]:
    """
    Open native Windows multi-file picker safely.
    Pops up instantly in the foreground with TopMost owner, eliminating window hiding and blurriness.
    Returns empty list when cancelled, with no secondary popup.
    """
    if not initial_dir or not os.path.exists(initial_dir):
        initial_dir = "D:/" if os.path.exists("D:/") else "C:/"

    # Priority 1: pywebview native window file dialog if active
    try:
        import desktop_app
        win = getattr(desktop_app, '_main_window', None)
        if win:
            import webview
            chosen = win.create_file_dialog(
                getattr(webview, 'OPEN_DIALOG', 10),
                directory=str(Path(initial_dir).resolve()),
                allow_multiple=True,
                file_types=("Video Files (*.mp4;*.mkv;*.mov;*.avi;*.webm;*.flv;*.ts;*.m4v)", "All Files (*.*)")
            )
            if chosen:
                return [str(Path(f).resolve()).replace("\\", "/") for f in chosen if os.path.exists(f)]
            # If user cancelled, return empty immediately - do not show second dialog
            return []
    except Exception as we:
        pass

    init_dir_esc = str(Path(initial_dir).resolve()).replace("'", "''")
    title_esc = str(title).replace("'", "''")

    # Priority 2: Ultra-fast PowerShell WinForms OpenFileDialog (0.05s startup, no C# compilation)
    ps_code = f"""
[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null
[System.Reflection.Assembly]::LoadWithPartialName('System.Drawing') | Out-Null

$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Title = '{title_esc}'
$dialog.Filter = 'Video Files (*.mp4;*.mkv;*.mov;*.avi;*.webm;*.flv;*.ts;*.m4v)|*.mp4;*.mkv;*.mov;*.avi;*.webm;*.flv;*.ts;*.m4v|All Files (*.*)|*.*'
$dialog.Multiselect = $true
$dialog.AutoUpgradeEnabled = $true
$initDir = '{init_dir_esc}'
if (Test-Path $initDir) {{
    $dialog.InitialDirectory = $initDir
}}

$topForm = New-Object System.Windows.Forms.Form
$topForm.TopMost = $true
$topForm.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$topForm.WindowState = [System.Windows.Forms.FormWindowState]::Minimized
$topForm.ShowInTaskbar = $false
$topForm.Opacity = 0

$res = $dialog.ShowDialog($topForm)
if ($res -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $json = ConvertTo-Json -Compress @($dialog.FileNames)
    Write-Output ("RESULT:" + $json)
}} else {{
    Write-Output "CANCELLED"
}}
$topForm.Dispose()
$dialog.Dispose()
exit 0
"""
    cache_dir = Path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    script_file = cache_dir / f"files_dlg_{uuid.uuid4().hex[:8]}.ps1"
    try:
        script_file.write_text(ps_code, encoding="utf-8")
        proc = subprocess.run(
            ["powershell.exe", "-STA", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script_file.resolve())],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            creationflags=0x08000000
        )
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("RESULT:"):
                raw_json = line[7:].strip()
                parsed = json.loads(raw_json)
                files = [parsed] if isinstance(parsed, str) else list(parsed)
                return [f.replace("\\", "/") for f in files if os.path.exists(f)]
            elif line == "CANCELLED":
                return []
    except Exception as e:
        print(f"Native file dialog note: {e}")
    finally:
        try:
            if script_file.exists():
                script_file.unlink()
        except Exception:
            pass

    return []


@app.route("/api/system/select-folder", methods=["POST", "GET"])
@app.route("/api/downloader/select-folder", methods=["POST", "GET"])
def system_select_folder_endpoint():
    """Pop native Windows folder picker dialog and return selected path."""
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    initial_dir = data.get("initial_dir", "")
    chosen_path = open_native_windows_folder_dialog(initial_dir, title="Select Download Save Folder")
    if chosen_path:
        return jsonify({"success": True, "path": chosen_path})
    return jsonify({"success": False, "cancelled": True})


@app.route("/api/system/select-media-files", methods=["POST", "GET"])
def system_select_media_files_endpoint():
    """Pop native Windows file picker dialog allowing multi-select of video files."""
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    initial_dir = data.get("initial_dir", "")

    chosen_files = open_native_windows_files_dialog(initial_dir, title="Select the video files for the drama series")

    if chosen_files:
        valid_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m4v", ".wmv"}
        meta_files = []
        for fp in chosen_files:
            p = Path(fp)
            if p.exists() and p.is_file() and p.suffix.lower() in valid_exts:
                sz = p.stat().st_size
                meta_files.append({
                    "filepath": str(p.resolve()).replace("\\", "/"),
                    "filename": p.name,
                    "size": sz,
                    "size_mb": f"{sz / (1024 * 1024):.1f}"
                })

        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s["filename"])]

        meta_files.sort(key=natural_sort_key)
        return jsonify({"success": True, "files": meta_files, "count": len(meta_files)})

    return jsonify({"success": False, "cancelled": True, "files": []})


@app.route("/api/system/select-media-folder", methods=["POST", "GET"])
def system_select_media_folder_endpoint():
    """Pop native Windows folder picker dialog, scanning and naturally sorting all drama episodes."""
    data = {}
    if request.is_json:
        data = request.get_json(silent=True) or {}
    initial_dir = data.get("initial_dir", "")

    chosen_folder = open_native_windows_folder_dialog(initial_dir, title="Select the folder that holds the episodes")

    if not chosen_folder or not os.path.exists(chosen_folder):
        return jsonify({"success": False, "cancelled": True, "files": []})

    folder_p = Path(chosen_folder)
    if folder_p.is_file():
        folder_p = folder_p.parent
    valid_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m4v", ".wmv"}

    found_paths = []
    try:
        for item in folder_p.rglob("*"):
            if item.is_file() and item.suffix.lower() in valid_exts:
                found_paths.append(item)
    except Exception as e:
        print(f"Folder recursive scan note: {e}")

    meta_files = []
    for p in found_paths:
        try:
            sz = p.stat().st_size
            meta_files.append({
                "filepath": str(p.resolve()).replace("\\", "/"),
                "filename": p.name,
                "size": sz,
                "size_mb": f"{sz / (1024 * 1024):.1f}"
            })
        except Exception:
            pass

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s["filename"])]

    meta_files.sort(key=natural_sort_key)

    series_title = folder_p.name
    return jsonify({
        "success": True,
        "folder": str(folder_p).replace("\\", "/"),
        "series_title": series_title,
        "files": meta_files,
        "count": len(meta_files)
    })


@app.route("/api/system/scan-folder", methods=["POST"])
def system_scan_folder_endpoint():
    """
    Directly scans a folder path or list of file paths dropped onto the app.
    Automatically detects directories, extracts all video episodes, sorts them
    naturally in story order (EP1, EP2... EP80), and returns full filepaths.
    """
    data = request.get_json(force=True, silent=True) or {}
    paths_to_check = []

    if "folder_path" in data and data["folder_path"]:
        paths_to_check.append(data["folder_path"])
    if "paths" in data and isinstance(data["paths"], list):
        paths_to_check.extend(data["paths"])

    valid_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m4v", ".wmv"}
    found_paths = []
    series_title = "Drama_Series"
    detected_folder = ""

    for raw_p in paths_to_check:
        if not raw_p or not isinstance(raw_p, str):
            continue
        p = Path(raw_p.strip())
        if not p.exists():
            continue

        if p.is_dir():
            detected_folder = str(p.resolve()).replace("\\", "/")
            series_title = p.name
            try:
                for item in p.rglob("*"):
                    if item.is_file() and item.suffix.lower() in valid_exts:
                        found_paths.append(item)
            except Exception as e:
                print(f"Dropped folder rglob scan note: {e}")
        elif p.is_file() and p.suffix.lower() in valid_exts:
            found_paths.append(p)
            if not detected_folder:
                detected_folder = str(p.parent.resolve()).replace("\\", "/")
                series_title = p.parent.name

    # Deduplicate paths
    unique_paths = []
    seen = set()
    for fp in found_paths:
        canonical = str(fp.resolve()).replace("\\", "/").lower()
        if canonical not in seen:
            seen.add(canonical)
            unique_paths.append(fp)

    meta_files = []
    for fp in unique_paths:
        try:
            sz = fp.stat().st_size
            meta_files.append({
                "filepath": str(fp.resolve()).replace("\\", "/"),
                "filename": fp.name,
                "size": sz,
                "size_mb": f"{sz / (1024 * 1024):.1f}"
            })
        except Exception:
            pass

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s["filename"])]

    meta_files.sort(key=natural_sort_key)

    return jsonify({
        "success": True if meta_files else False,
        "folder": detected_folder,
        "series_title": series_title,
        "files": meta_files,
        "count": len(meta_files)
    })


@app.route("/api/system/open-folder", methods=["POST"])
def system_open_folder_endpoint():
    """Open specified folder on the user's laptop using Windows Explorer."""
    data = request.get_json(force=True, silent=True) or {}
    folder_path = data.get("path", "").strip()
    if not folder_path:
        folder_path = str(Path("data/exports").resolve())
        
    p = Path(folder_path).resolve()
    target_dir = p.parent if (p.exists() and p.is_file()) else p
    try:
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            
        if sys.platform == "win32":
            os.startfile(str(target_dir))
        else:
            subprocess.Popen(["xdg-open", str(target_dir)])
        return jsonify({"success": True, "path": str(target_dir).replace("\\", "/")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================================================
# Power Tools REST APIs
# ==========================================================================
@app.route("/api/power/merge", methods=["POST"])
def power_merge_endpoint():
    """Merge multiple video files into one video."""
    data = request.get_json(force=True) or {}
    files = data.get("files", [])
    if len(files) < 2:
        return jsonify({"success": False, "error": "At least 2 video files are required for merging."}), 400
        
    custom_name = data.get("output_name", "").strip()
    if custom_name:
        if not custom_name.lower().endswith((".mp4", ".mkv", ".mov")):
            custom_name += ".mp4"
        out_file = f"data/exports/{custom_name}"
    else:
        out_file = f"data/exports/merged_drama_{int(time.time())}.mp4"
        
    auto_trim_freeze = bool(data.get("auto_trim_freeze", True))
        
    try:
        merge_res = merge_videos(files, out_file, auto_trim_freeze=auto_trim_freeze, return_details=True)
        res_p = merge_res["output_file"]
        play_windows_completion_sound()
        return jsonify({
            "success": True,
            "output_file": res_p.replace("\\", "/"),
            "download_url": f"/media/{res_p.replace(chr(92), '/')}",
            "output_dir": str(Path(res_p).parent).replace("\\", "/"),
            "auto_trim_freeze": auto_trim_freeze,
            "total_episodes": merge_res.get("total_episodes", len(files)),
            "trimmed_count": merge_res.get("trimmed_count", 0),
            "unaltered_count": merge_res.get("unaltered_count", len(files)),
            "total_seconds_saved": merge_res.get("total_seconds_saved", 0.0),
            "details": merge_res.get("details", [])
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/power/split", methods=["POST"])
def power_split_endpoint():
    """Split video file into parts."""
    data = request.get_json(force=True) or {}
    video_path = data.get("video_path", "")
    chunk_sec = max(60, int(data.get("chunk_duration_sec", 60)))
    if not video_path or not Path(video_path).exists():
        return jsonify({"success": False, "error": "Invalid source video path."}), 400
        
    out_dir = f"data/exports/split_{int(time.time())}"
    try:
        parts = split_video(video_path, chunk_sec, out_dir)
        play_windows_completion_sound()
        return jsonify({
            "success": True,
            "parts_count": len(parts),
            "parts": parts,
            "output_dir": str(Path(out_dir).resolve()).replace("\\", "/")
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/power/media-duration", methods=["POST"])
def power_media_duration_endpoint():
    """Get exact duration of a video file via ffprobe."""
    data = request.get_json(silent=True) or {}
    vpath = data.get("filepath") or data.get("video_path") or ""
    if not vpath or not Path(vpath).exists():
        return jsonify({"success": False, "error": "File does not exist."}), 400
    try:
        dur = get_media_duration(str(vpath))
        return jsonify({"success": True, "duration": round(dur, 2)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/power/rename", methods=["POST"])
def power_rename_endpoint():
    """Batch rename files."""
    data = request.get_json(force=True) or {}
    files = data.get("files", [])
    prefix = data.get("prefix", "Drama_EP")
    start_num = int(data.get("start_num", 1))
    
    try:
        res = batch_rename_files(files, prefix, start_num)
        play_windows_completion_sound()
        return jsonify({"success": True, "results": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/power/compress", methods=["POST"])
def power_compress_endpoint():
    """Compress video file."""
    data = request.get_json(force=True) or {}
    video_path = data.get("video_path", "")
    crf = int(data.get("crf", 26))
    preset = data.get("preset", "fast")
    target_height = data.get("target_height")
    if target_height:
        target_height = int(target_height)
        
    if not video_path or not Path(video_path).exists():
        return jsonify({"success": False, "error": "Invalid video path."}), 400
        
    out_file = f"data/exports/compressed_{Path(video_path).stem}_{int(time.time())}.mp4"
    try:
        orig_size = Path(video_path).stat().st_size
        res_p = compress_video(video_path, out_file, crf, preset, target_height)
        new_size = Path(res_p).stat().st_size
        saved_bytes = max(0, orig_size - new_size)
        play_windows_completion_sound()
        return jsonify({
            "success": True,
            "output_file": res_p.replace("\\", "/"),
            "download_url": f"/media/{res_p.replace(chr(92), '/')}",
            "output_dir": str(Path(res_p).parent).replace("\\", "/"),
            "orig_size": orig_size,
            "new_size": new_size,
            "saved_bytes": saved_bytes,
            "saved_pct": round((saved_bytes / orig_size) * 100) if orig_size > 0 else 0
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/power/compress-batch", methods=["POST"])
def power_compress_batch_endpoint():
    """Batch compress multiple video files."""
    data = request.get_json(force=True) or {}
    files = data.get("files", [])
    crf = int(data.get("crf", 26))
    preset = data.get("preset", "fast")
    target_height = data.get("target_height")
    if target_height:
        target_height = int(target_height)
    if not files:
        return jsonify({"success": False, "error": "No files provided."}), 400

    out_dir = Path("data/exports") / f"compressed_batch_{int(time.time())}"
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total_saved_bytes = 0
    for fp in files:
        p = Path(fp)
        if not p.exists():
            continue
        orig_size = p.stat().st_size
        out_p = out_dir / f"compressed_{p.name}"
        try:
            res_p = compress_video(str(p), str(out_p), crf, preset, target_height)
            new_size = Path(res_p).stat().st_size
            saved = max(0, orig_size - new_size)
            total_saved_bytes += saved
            results.append({
                "original": str(p),
                "compressed": res_p,
                "orig_size": orig_size,
                "new_size": new_size,
                "saved_bytes": saved,
                "success": True
            })
        except Exception as e:
            results.append({
                "original": str(p),
                "error": str(e),
                "success": False
            })

    play_windows_completion_sound()
    return jsonify({
        "success": True,
        "results": results,
        "output_dir": str(out_dir).replace("\\", "/"),
        "total_saved_bytes": total_saved_bytes
    })


# ==========================================================================
# 1-Click Automated Video Dubbing & Status Polling
# ==========================================================================
video_auto_tasks: Dict[str, Dict[str, Any]] = {}

@app.route("/api/projects/upload-overlay-logo", methods=["POST"])
def upload_overlay_logo_endpoint():
    """Upload logo watermark image file for overlay rendering."""
    if "logo_file" not in request.files:
        return jsonify({"success": False, "error": "No logo file provided"}), 400
    file = request.files["logo_file"]
    if not file.filename:
        return jsonify({"success": False, "error": "Empty filename"}), 400
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix or ".png"
    save_name = f"active_overlay_logo_{int(time.time())}{ext}"
    dest = upload_dir / save_name
    file.save(str(dest))
    return jsonify({
        "success": True,
        "logo_path": str(dest.resolve()),
        "filename": file.filename
    })


@app.route("/api/projects/upload-overlay-lower-third", methods=["POST"])
def upload_overlay_lower_third_endpoint():
    """Upload Lower Third video/animation file for overlay rendering."""
    if "lower_third_file" not in request.files:
        return jsonify({"success": False, "error": "No lower third file provided"}), 400
    file = request.files["lower_third_file"]
    if not file.filename:
        return jsonify({"success": False, "error": "Empty filename"}), 400
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix or ".mp4"
    timestamp = int(time.time())
    save_name = f"active_overlay_lt_{timestamp}{ext}"
    dest = upload_dir / save_name
    file.save(str(dest))

    from video_processor import get_video_dimensions
    from audio_processor import get_ffmpeg_path, get_silent_kwargs
    vw, vh = get_video_dimensions(str(dest))
    vw = vw or 2000
    vh = vh or 2500

    # Extract clean poster image at ss=1.0 (where banner is guaranteed to be fully animated and visible)
    thumb_name = f"lt_thumb_{timestamp}.png"
    thumb_dest = upload_dir / thumb_name
    try:
        thumb_cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-ss", "00:00:01",
            "-i", str(dest),
            "-vframes", "1",
            str(thumb_dest)
        ]
        subprocess.run(thumb_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, **get_silent_kwargs())
        if not thumb_dest.exists() or thumb_dest.stat().st_size < 1000:
            thumb_cmd_fallback = [
                get_ffmpeg_path(),
                "-nostdin",
                "-y",
                "-i", str(dest),
                "-vframes", "1",
                str(thumb_dest)
            ]
            subprocess.run(thumb_cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, **get_silent_kwargs())
    except Exception as te:
        print(f"[Lower Third Thumb Warning] {te}")

    # Generate lightweight transparent WebM proxy for browser playback (vital for .mov with qtrle/prores)
    preview_name = f"lt_preview_{timestamp}.webm"
    preview_dest = upload_dir / preview_name
    preview_url = f"/media/{dest.as_posix()}"
    try:
        webm_cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-i", str(dest),
            "-vf", "scale=480:-2",
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            "-deadline", "realtime",
            "-cpu-used", "8",
            "-b:v", "800k",
            "-auto-alt-ref", "0",
            "-c:a", "libopus",
            str(preview_dest)
        ]
        proc = subprocess.run(webm_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25, **get_silent_kwargs())
        if proc.returncode == 0 and preview_dest.exists() and preview_dest.stat().st_size > 1000:
            preview_url = f"/media/{preview_dest.as_posix()}"
    except Exception as we:
        print(f"[Lower Third WebM Preview Warning] {we}")

    thumb_url = f"/media/{thumb_dest.as_posix()}" if thumb_dest.exists() else ""

    return jsonify({
        "success": True,
        "video_path": str(dest.resolve()),
        "lower_third_path": str(dest.resolve()),
        "url": preview_url,
        "preview_url": preview_url,
        "thumb_url": thumb_url,
        "orig_width": vw,
        "orig_height": vh,
        "filename": file.filename
    })


@app.route("/api/projects/upload-overlay-subtitle", methods=["POST"])
def upload_overlay_subtitle_endpoint():
    """Upload custom Subtitle file (.srt, .ass, .vtt) for overlay rendering."""
    if "subtitle_file" not in request.files:
        return jsonify({"success": False, "error": "No subtitle file provided"}), 400
    file = request.files["subtitle_file"]
    if not file.filename:
        return jsonify({"success": False, "error": "Empty filename"}), 400
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix.lower() or ".srt"
    timestamp = int(time.time())
    save_name = f"active_overlay_sub_{timestamp}{ext}"
    dest = upload_dir / save_name
    file.save(str(dest))
    return jsonify({
        "success": True,
        "subtitle_path": str(dest.resolve()),
        "filename": file.filename
    })


def diagnose_pipeline_error(error_msg: str, tb_str: str = "") -> dict:
    combined = (str(error_msg) + " " + str(tb_str)).lower()
    
    # 1. GPU / CUDA Out of Memory
    if any(k in combined for k in ["cuda out of memory", "out of memory", "cuda error", "allocator"]):
        return {
            "category": "GPU / Memory Limit",
            "tag": "[GPU Out of Memory]",
            "suggestion_km": "ខ្វះ VRAM/Memory ក្រាហ្វិក។ សូមបិទកម្មវិធីផ្សេង ឬប្ដូរទៅដំណើរការលើ CPU វិញ។",
            "suggestion_en": "VRAM exhausted. Close background 3D/video apps or switch to CPU mode in settings."
        }
    
    # 2. Network / Edge TTS Connection / Timeout
    if any(k in combined for k in ["nodename nor servname", "getaddrinfo failed", "connection refused", "connection reset", "timed out", "timeout", "network is unreachable", "ssl", "edge_tts", "connecterror"]):
        return {
            "category": "Network & Cloud TTS Connection",
            "tag": "[Network / TTS Error]",
            "suggestion_km": "ដាច់ការតភ្ជាប់អ៊ីនធឺណិត ឬសេវាសំឡេង AI TTS។ សូមពិនិត្យមើល Internet / Wi-Fi របស់អ្នក។",
            "suggestion_en": "Cloud TTS / Network connection failed. Please check your internet connection or Wi-Fi."
        }
        
    # 3. FFmpeg / Codec / Corrupt Video
    if any(k in combined for k in ["moov atom not found", "invalid data found", "unsupported codec", "ffmpeg", "encoder", "muxer"]):
        return {
            "category": "FFmpeg / Media Codec",
            "tag": "[FFmpeg / Video Codec]",
            "suggestion_km": "វីដេអូខូចទម្រង់ ឬកូដិកមិនគាំទ្រ។ សូមបម្លែងវីដេអូទៅជា MP4 (H.264 / AAC) រួចសាកល្បងម្ដងទៀត។",
            "suggestion_en": "Video file appears damaged or uses an unsupported codec. Try re-encoding to MP4 (H.264)."
        }
        
    # 4. Whisper / Speech Recognition
    if any(k in combined for k in ["whisper", "faster_whisper", "ctranslate2", "speech-to-text", "transcribe"]):
        return {
            "category": "Speech Recognition (STT)",
            "tag": "[Whisper STT Error]",
            "suggestion_km": "កំហុសក្នុងការស្ដាប់និងបម្លែងសំឡេង (STT)។ សូមពិនិត្យមើលថាតើវីដេអូមានសំឡេងនិយាយច្បាស់លាស់ដែរឬទេ។",
            "suggestion_en": "Speech-to-text recognition encountered an error. Check if the audio track has spoken dialogue."
        }

    # 5. AI Script Translation (Gemini, Groq, Translation Engine)
    if any(k in combined for k in ["translat", "gemini", "groq", "dialogue", "script", "jsondecodeerror"]):
        return {
            "category": "AI Script Translation",
            "tag": "[AI Translation Error]",
            "suggestion_km": "កំហុសក្នុងម៉ាស៊ីនបកប្រែអត្ថបទ (AI Translation)។ សូមពិនិត្យមើល API Key (Gemini/Groq), Quota Limit, ឬការតភ្ជាប់អ៊ីនធឺណិត។",
            "suggestion_en": "AI Translation engine error. Verify Gemini/Groq API keys, quota limits, or network connectivity."
        }
        
    # 5. File / Storage / Disk Space
    if any(k in combined for k in ["no space left on device", "disk full", "permission denied", "filenotfounderror", "file not found"]):
        return {
            "category": "Storage / File Access",
            "tag": "[Storage / Disk Error]",
            "suggestion_km": "ទំហំផ្ទុក (Drive D/C) ពេញ ឬគ្មានសិទ្ធិបើកឯកសារ។ សូមពិនិត្យមើលទំហំថាសរឹងរបស់អ្នក។",
            "suggestion_en": "Disk is full or file permission denied. Please verify free storage on Drive D:/C: and try again."
        }
        
    # 6. General Pipeline
    return {
        "category": "Pipeline Execution",
        "tag": "[Pipeline Error]",
        "suggestion_km": "ដំណើរការត្រូវបានរំខាន។ សូមពិនិត្យមើលព័ត៌មានលម្អិតនៃកំហុសខាងក្រោម ឬសាកល្បងម្ដងទៀត។",
        "suggestion_en": "Process was interrupted. Please review error details below or retry with a different video file."
    }


@app.route("/api/projects/auto-dub-video", methods=["POST"])
def auto_dub_video_endpoint():
    """
    1-Click Automated Video Dubbing (Chinese/Multilingual Video -> Khmer Speech & Video).
    Accepts video file upload or local filepath, with interactive Logo watermark and Blur mask overlays.
    """
    mode = request.form.get("drama_mode", "drama_dubbing")
    source_lang = request.form.get("source_lang", "auto")
    voice_override = request.form.get("voice_override")
    aspect_ratio = request.form.get("aspect_ratio", "16:9")
    cfg = load_stored_story_config()
    burn_sub_default = "true" if cfg.get("subtitle_mode", "none") == "burn" else "false"
    burn_subtitles = request.form.get("burn_subtitles", burn_sub_default).lower() in ("true", "1", "yes")
    
    saved_video_path = None
    original_filename = "drama_video.mp4"
    overlay_config = None
    custom_export_dir = None

    if "file" in request.files and request.files["file"].filename:
        file = request.files["file"]
        original_filename = file.filename
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{int(time.time())}_{Path(original_filename).name}"
        dest = upload_dir / unique_name
        file.save(str(dest))
        saved_video_path = str(dest)
        custom_export_dir = request.form.get("custom_export_dir")
        raw_oc = request.form.get("overlay_config")
        if raw_oc:
            try:
                overlay_config = json.loads(raw_oc) if isinstance(raw_oc, str) else raw_oc
            except Exception:
                pass
        project_title = None
    elif request.is_json:
        data = request.get_json(force=True) or {}
        saved_video_path = data.get("filepath") or data.get("path") or data.get("local_path") or data.get("file")
        project_title = data.get("title")
        custom_export_dir = data.get("custom_export_dir")
        if not original_filename or original_filename == "drama_video.mp4":
            original_filename = data.get("filename") or data.get("name") or (Path(saved_video_path).name if saved_video_path else "drama_video.mp4")
        if saved_video_path:
            mode = data.get("drama_mode", mode)
            source_lang = data.get("source_lang", source_lang)
            voice_override = data.get("voice_override", voice_override)
            aspect_ratio = data.get("aspect_ratio", aspect_ratio)
            if "burn_subtitles" in data:
                val = data["burn_subtitles"]
                burn_subtitles = val if isinstance(val, bool) else str(val).lower() in ("true", "1", "yes")
            overlay_config = data.get("overlay_config")
            if isinstance(overlay_config, str):
                try:
                    overlay_config = json.loads(overlay_config)
                except Exception:
                    pass
    elif request.form.get("filepath") or request.form.get("path") or request.form.get("file"):
        saved_video_path = request.form.get("filepath") or request.form.get("path") or request.form.get("file")
        if str(saved_video_path) == "[object Object]":
            saved_video_path = None
        original_filename = request.form.get("filename") or request.form.get("name") or (Path(saved_video_path).name if saved_video_path else "drama_video.mp4")
        project_title = request.form.get("title")
        custom_export_dir = request.form.get("custom_export_dir")
        raw_oc = request.form.get("overlay_config")
        if raw_oc:
            try:
                overlay_config = json.loads(raw_oc) if isinstance(raw_oc, str) else raw_oc
            except Exception:
                pass
    else:
        project_title = request.form.get("title")
        custom_export_dir = request.form.get("custom_export_dir")
        if request.form.get("filename"):
            original_filename = request.form.get("filename")

    if not custom_export_dir:
        custom_export_dir = request.args.get("custom_export_dir")

    # Support direct logo_file upload in form data
    if "logo_file" in request.files and request.files["logo_file"].filename:
        logo_f = request.files["logo_file"]
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(logo_f.filename).suffix or ".png"
        saved_logo = upload_dir / f"overlay_logo_{int(time.time())}{ext}"
        logo_f.save(str(saved_logo))
        if not overlay_config:
            overlay_config = {}
        if "logo" not in overlay_config:
            overlay_config["logo"] = {}
        overlay_config["logo"]["active"] = True
        overlay_config["logo"]["path"] = str(saved_logo.resolve())

    # Support direct lower_third_file upload in form data
    if "lower_third_file" in request.files and request.files["lower_third_file"].filename:
        lt_f = request.files["lower_third_file"]
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(lt_f.filename).suffix or ".mp4"
        saved_lt = upload_dir / f"overlay_lt_{int(time.time())}{ext}"
        lt_f.save(str(saved_lt))
        if not overlay_config:
            overlay_config = {}
        if "lower_third" not in overlay_config:
            overlay_config["lower_third"] = {}
        overlay_config["lower_third"]["active"] = True
        overlay_config["lower_third"]["path"] = str(saved_lt.resolve())

    if not voice_override or voice_override in ("auto", "", None):
        cfg = load_stored_story_config()
        if cfg.get("auto_multi_voice") is not False or cfg.get("khmer_voice") == "multi":
            voice_override = "multi"
        else:
            voice_override = cfg.get("khmer_voice", "multi")

    # Intelligent Multi-Location Path Resolution
    resolved_path = None
    if saved_video_path and str(saved_video_path) != "[object Object]":
        clean_vp = str(saved_video_path).strip()
        if clean_vp.startswith("/media/"):
            clean_vp = clean_vp[7:]
        import urllib.parse
        clean_vp = urllib.parse.unquote(clean_vp)

        p = Path(clean_vp)
        if p.exists() and p.is_file():
            resolved_path = str(p.resolve())
        else:
            p_base = (BASE_DIR / clean_vp).resolve()
            if p_base.exists() and p_base.is_file():
                resolved_path = str(p_base)
            else:
                f_target_name = Path(original_filename or clean_vp).name
                for cand_dir in [
                    Path("data/uploads"),
                    Path("data/uploads/batch_temp"),
                    Path("data/exports"),
                    Path("data/uploads/downloads"),
                ]:
                    cand_p = (cand_dir / f_target_name).resolve()
                    if cand_p.exists() and cand_p.is_file():
                        resolved_path = str(cand_p)
                        break

                if not resolved_path and f_target_name:
                    for root_str in ("D:/SN_Dramas", "C:/SN_Dramas"):
                        root_p = Path(root_str)
                        if root_p.exists():
                            try:
                                for match in root_p.rglob(f_target_name):
                                    if match.is_file() and match.stat().st_size > 50000:
                                        resolved_path = str(match.resolve())
                                        break
                                if resolved_path:
                                    break
                            except Exception:
                                pass

    if not resolved_path and original_filename and original_filename != "drama_video.mp4":
        f_target_name = Path(original_filename).name
        for cand_dir in [
            Path("data/uploads"),
            Path("data/uploads/batch_temp"),
            Path("data/exports"),
            Path("data/uploads/downloads"),
        ]:
            cand_p = (cand_dir / f_target_name).resolve()
            if cand_p.exists() and cand_p.is_file():
                resolved_path = str(cand_p)
                break
        if not resolved_path:
            for root_str in ("D:/SN_Dramas", "C:/SN_Dramas"):
                root_p = Path(root_str)
                if root_p.exists():
                    try:
                        for match in root_p.rglob(f_target_name):
                            if match.is_file() and match.stat().st_size > 50000:
                                resolved_path = str(match.resolve())
                                break
                        if resolved_path:
                            break
                    except Exception:
                        pass

    if resolved_path:
        saved_video_path = resolved_path

    if not saved_video_path or not Path(saved_video_path).exists():
        return jsonify({"success": False, "error": f"No valid video file uploaded or provided: {original_filename}"}), 400

    task_id = str(uuid.uuid4())[:8]
    video_auto_tasks[task_id] = {
        "task_id": task_id,
        "filename": original_filename,
        "status": "processing",
        "progress": 5,
        "step_km": "Initializing pipeline...",
        "step_en": "Initializing pipeline...",
        "project": None,
        "error": None,
        "error_type": None,
        "error_stage": "Stage 1/7: Initializing",
        "error_details": None,
        "error_suggestion": None,
        "error_category": None,
        "error_tag": None
    }

    def _worker(t_id: str, v_path: str, m: str, sl: str, vo: str, ar: str, bs: bool, oc: dict, p_title: str = None, cust_dir: str = None):
        current_stage = "1/7 Audio Extraction"
        def _clean_branding(text: str) -> str:
            if not text:
                return text
            t = re.sub(r'https?://api\.nisay\.store(?:/v1)?', 'https://cloud.sntool.ai', str(text), flags=re.IGNORECASE)
            t = re.sub(r'api\.nisay(?:\.store)?', 'SN TOOL Cloud', t, flags=re.IGNORECASE)
            t = re.sub(r'nisay-transcribe', 'SN Tool Speech Engine', t, flags=re.IGNORECASE)
            t = re.sub(r'nisay[-_ ]*translate', 'SN Tool AI Translator', t, flags=re.IGNORECASE)
            t = re.sub(r'nisay[-_ ]*cloud', 'SN Tool Cloud', t, flags=re.IGNORECASE)
            t = re.sub(r'nisay', 'SN TOOL', t, flags=re.IGNORECASE)
            return t

        def _prog_cb(pct: int, km: str, en: str, dialogues: list = None):
            nonlocal current_stage
            if t_id in video_auto_tasks:
                current_stage = _clean_branding(en or km or current_stage)
                video_auto_tasks[t_id]["progress"] = pct
                video_auto_tasks[t_id]["step_km"] = _clean_branding(km)
                video_auto_tasks[t_id]["step_en"] = _clean_branding(en)
                video_auto_tasks[t_id]["error_stage"] = current_stage
                if dialogues is not None:
                    video_auto_tasks[t_id]["dialogues"] = dialogues

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                target_title = p_title or f"Dubbed_{Path(v_path).stem}"
                clean_target = re.sub(r'^(?:Dubbed_)+', '', str(target_title), flags=re.IGNORECASE)
                clean_target = re.sub(r'^Raw_Full_Movie_', '', clean_target, flags=re.IGNORECASE)
                clean_target = re.sub(r'_\d{9,12}$', '', clean_target)
                final_title = f"Dubbed_{clean_target}"

                res_proj = loop.run_until_complete(pm.process_video_pipeline(
                    video_path=v_path,
                    title=final_title,
                    mode=m,
                    source_lang=sl,
                    voice_override=vo,
                    aspect_ratio=ar,
                    burn_subtitles=bs,
                    overlay_config=oc,
                    progress_callback=_prog_cb,
                    custom_export_dir=cust_dir
                ))
            finally:
                loop.close()

            if t_id in video_auto_tasks:
                video_auto_tasks[t_id]["status"] = "completed"
                video_auto_tasks[t_id]["progress"] = 100
                video_auto_tasks[t_id]["step_km"] = "100% Completed (Success!)"
                video_auto_tasks[t_id]["step_en"] = "Completed successfully!"
                video_auto_tasks[t_id]["project"] = res_proj
                if res_proj and res_proj.get("dialogues"):
                    video_auto_tasks[t_id]["dialogues"] = res_proj.get("dialogues")
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            print(f"Auto dubbing worker error at stage [{current_stage}]: {e}\n{tb_str}")
            diag = diagnose_pipeline_error(str(e), tb_str)
            if t_id in video_auto_tasks:
                err_msg = _clean_branding(str(e) or type(e).__name__)
                sugg_text = f"{diag.get('suggestion_km')} • {diag.get('suggestion_en')}"
                video_auto_tasks[t_id]["status"] = "failed"
                video_auto_tasks[t_id]["error"] = err_msg
                video_auto_tasks[t_id]["error_type"] = type(e).__name__
                video_auto_tasks[t_id]["error_stage"] = current_stage
                video_auto_tasks[t_id]["error_details"] = _clean_branding(tb_str)
                video_auto_tasks[t_id]["error_suggestion"] = sugg_text
                video_auto_tasks[t_id]["error_category"] = diag.get("category")
                video_auto_tasks[t_id]["error_tag"] = diag.get("tag")
                video_auto_tasks[t_id]["step_km"] = f"Error at {current_stage}: {err_msg}"
                video_auto_tasks[t_id]["step_en"] = f"Error at {current_stage}: {err_msg}"

    threading.Thread(
        target=_worker,
        args=(task_id, saved_video_path, mode, source_lang, voice_override, aspect_ratio, burn_subtitles, overlay_config, project_title, custom_export_dir),
        daemon=True
    ).start()

    return jsonify({
        "success": True,
        "task_id": task_id,
        "message": "Video translation task started successfully."
    })


@app.route("/api/projects/auto-dub-status/<task_id>", methods=["GET"])
def auto_dub_status_endpoint(task_id):
    task = video_auto_tasks.get(task_id)
    if not task:
        return jsonify({"success": False, "error": "Task not found"}), 404

    dialogues = task.get("dialogues")
    if not dialogues and task.get("project"):
        dialogues = task["project"].get("dialogues")

    resp = {
        "success": True,
        "task_id": task["task_id"],
        "filename": task.get("filename"),
        "status": task.get("status"),
        "progress": task.get("progress", 0),
        "step_km": task.get("step_km", ""),
        "step_en": task.get("step_en", ""),
        "error": task.get("error"),
        "error_type": task.get("error_type"),
        "error_stage": task.get("error_stage"),
        "error_details": task.get("error_details"),
        "error_suggestion": task.get("error_suggestion"),
        "error_category": task.get("error_category"),
        "error_tag": task.get("error_tag"),
        "dialogues": dialogues or []
    }
    if task.get("status") == "completed" and task.get("project"):
        proj = task["project"]
        resp["project"] = proj
        out_vid = proj.get("output_video_file") or ""
        out_aud = proj.get("mixed_audio_file") or ""
        resp["video_url"] = f"/media/{out_vid.replace(chr(92), '/')}" if out_vid else ""
        resp["mixed_audio_url"] = f"/media/{out_aud.replace(chr(92), '/')}" if out_aud else ""
        resp["final_exported_video_path"] = proj.get("final_exported_video_path") or out_vid
        resp["final_exported_dir"] = proj.get("final_exported_dir") or (str(Path(out_vid).parent) if out_vid else "")

    return jsonify(resp)


@app.route("/api/projects/open-folder", methods=["POST"])
def open_project_folder_endpoint():
    data = request.get_json(force=True) or {}
    target_path = data.get("path")
    if not target_path:
        target_path = str(Path("data/exports").resolve())
    else:
        p = Path(target_path)
        if p.is_file():
            target_path = str(p.parent.resolve())
        else:
            target_path = str(p.resolve())

    if sys.platform == "win32":
        try:
            os.startfile(target_path)
            return jsonify({"success": True, "opened_path": target_path})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "opened_path": target_path})


@app.route("/api/projects/merge-episodes", methods=["POST"])
def merge_episodes_endpoint():
    """Merge multiple dubbed episode MP4 files into a single full movie video."""
    data = request.get_json(force=True) or {}
    video_paths = data.get("video_paths", [])
    series_title = data.get("series_title", "Drama_Series")

    clean_title = re.sub(r'^(?:Dubbed_)+', '', str(series_title), flags=re.IGNORECASE)
    clean_title = re.sub(r'[^\w\-_.]', '_', clean_title).strip('_')
    if not clean_title:
        clean_title = "Drama_Series"

    output_filename = f"Dubbed_{clean_title}_Full_Movie.mp4"
    custom_export_dir = data.get("custom_export_dir")
    if custom_export_dir and Path(custom_export_dir).exists():
        out_file = Path(custom_export_dir) / output_filename
    else:
        out_file = Path("data/exports") / output_filename

    if not video_paths:
        return jsonify({"success": False, "error": "No video paths provided"}), 400

    resolved_paths = []
    for vp in video_paths:
        p = Path(vp)
        if p.exists():
            resolved_paths.append(str(p.resolve()))
            continue
        p_exports = Path("data/exports") / p.name
        if p_exports.exists():
            resolved_paths.append(str(p_exports.resolve()))
            continue
        p_base = (BASE_DIR / vp).resolve()
        if p_base.exists():
            resolved_paths.append(str(p_base))
            continue

    if not resolved_paths:
        return jsonify({"success": False, "error": "No existing episode files found to merge"}), 404

    try:
        from video_processor import merge_videos
        final_path = merge_videos(resolved_paths, str(out_file), auto_trim_freeze=True)
        play_windows_completion_sound()
        return jsonify({
            "success": True,
            "merged_path": str(final_path),
            "merged_filename": output_filename,
            "video_url": f"/media/data/exports/{output_filename}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/projects/pre-merge-raw-episodes", methods=["POST"])
def pre_merge_raw_episodes_endpoint():
    """
    Pre-merge raw source video episodes into a single full-movie source video
    before dubbing, so the AI Dubbing engine dubs the full movie at once.
    """
    data = request.get_json(force=True) or {}
    video_paths = data.get("video_paths", [])
    series_title = data.get("series_title", "Drama_Series")

    clean_title = re.sub(r'^(?:Dubbed_)+', '', str(series_title), flags=re.IGNORECASE)
    clean_title = re.sub(r'[^\w\-_.]', '_', clean_title).strip('_')
    if not clean_title:
        clean_title = "Drama_Series"

    if not video_paths:
        return jsonify({"success": False, "error": "No video paths provided"}), 400

    resolved_paths = []
    for vp in video_paths:
        p = Path(vp)
        if p.exists():
            resolved_paths.append(str(p.resolve()))
            continue
        p_base = (BASE_DIR / vp).resolve()
        if p_base.exists():
            resolved_paths.append(str(p_base))
            continue
        p_uploads = (Path("data/uploads") / p.name).resolve()
        if p_uploads.exists():
            resolved_paths.append(str(p_uploads))
            continue

    if not resolved_paths:
        return jsonify({"success": False, "error": "None of the episode files were found on disk"}), 404

    try:
        from video_processor import merge_videos
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)
        out_filename = f"Raw_Full_Movie_{clean_title}_{int(time.time())}.mp4"
        out_file = upload_dir / out_filename

        merge_res = merge_videos(resolved_paths, str(out_file), auto_trim_freeze=True, return_details=True)
        final_path = merge_res["output_file"]
        file_size_mb = round(Path(final_path).stat().st_size / (1024 * 1024), 2)
        play_windows_completion_sound()
        return jsonify({
            "success": True,
            "merged_path": str(final_path),
            "merged_filename": out_filename,
            "series_title": clean_title,
            "episodes_count": len(resolved_paths),
            "trimmed_count": merge_res.get("trimmed_count", 0),
            "total_seconds_saved": merge_res.get("total_seconds_saved", 0.0),
            "size_mb": file_size_mb,
            "video_url": f"/media/{Path(final_path).as_posix()}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/system/find-sibling-episodes", methods=["POST"])
def find_sibling_episodes_endpoint():
    """
    Check if a staged single video has sibling episodes in its directory.
    Useful when user selected EP_01 but wants to export Full Movie Merged.
    """
    data = request.get_json(force=True) or {}
    filepath = data.get("filepath", "")
    if not filepath:
        return jsonify({"success": False, "has_siblings": False, "files": []})

    p = Path(filepath)
    if not p.exists():
        p_base = BASE_DIR / filepath
        if p_base.exists():
            p = p_base

    if not p.exists() or not p.is_file():
        return jsonify({"success": False, "has_siblings": False, "files": []})

    parent_dir = p.parent
    valid_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".ts"}
    candidates = []
    try:
        for item in parent_dir.iterdir():
            if item.is_file() and item.suffix.lower() in valid_exts:
                if not item.name.startswith("Dubbed_") and not item.name.startswith("Raw_"):
                    candidates.append(item)
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "has_siblings": False, "files": []})

    def natural_sort_key(s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s.name)]

    candidates.sort(key=natural_sort_key)

    if len(candidates) > 1:
        dir_name = parent_dir.name
        files_data = [{
            "filepath": str(f.resolve()),
            "filename": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 1)
        } for f in candidates]
        return jsonify({
            "success": True,
            "has_siblings": True,
            "total_count": len(candidates),
            "folder_name": dir_name,
            "files": files_data
        })

    return jsonify({"success": True, "has_siblings": False, "files": []})


@app.route("/media/<path:filename>")
def serve_media(filename):
    file_path = Path(filename)
    if not file_path.exists():
        return jsonify({"error": "Media file not found"}), 404
        
    return send_file(str(file_path.resolve()), conditional=True)


@app.route("/api/update/check", methods=["GET"])
def check_update_api():
    try:
        from update import check_for_updates
        token = request.args.get("token") or os.environ.get("GITHUB_TOKEN")
        res = check_for_updates(github_token=token)
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "has_update": False, "error": str(e)}), 500


@app.route("/api/update/apply", methods=["POST"])
def apply_update_api():
    try:
        from update import apply_zip_download_update, check_for_updates
        data = request.get_json(force=True) or {}
        download_url = data.get("download_url", "")
        if not download_url:
            chk = check_for_updates()
            download_url = chk.get("download_url") or "https://drive.usercontent.google.com/download?id=1x_k269mEwMPH01tx8o6N67QEtLz7jlUo&export=download&confirm=t"
        res = apply_zip_download_update(download_url, APP_DIR)
        return jsonify(res)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)

