"""
Video Processing Engine: Video Rendering, Audio Replacement, Subtitle Burning, Aspect Ratio (9:16/16:9), and Watermarking
"""
import sys
import os
import re
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

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
from audio_processor import get_ffmpeg_path, get_silent_kwargs, get_media_duration
from translator import format_srt_content
from subtitle_styler import generate_ass_subtitles


def get_video_dimensions(video_path: str):
    """Extract width and height of video quickly via FFmpeg."""
    try:
        cmd = [get_ffmpeg_path(), "-nostdin", "-i", str(video_path)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="ignore", timeout=10, **get_silent_kwargs())
        m = re.search(r'Stream.*Video:.*?(\d{3,5})x(\d{3,5})', res.stderr)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return None, None



def generate_sample_drama_video(output_video_path: str, duration_sec: int = 15) -> str:
    """Generate sample drama MP4 video for quick testing."""
    out_p = Path(output_video_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration_sec}:size=1280x720:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration_sec}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(out_p)
    ]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", **get_silent_kwargs())
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to generate sample drama video: {proc.stderr or ''}")

    return str(out_p)


def format_ass_filter_path(file_path: Union[str, Path]) -> str:
    """Format an ASS file path for safe insertion into FFmpeg filter_complex on Windows and POSIX."""
    p = Path(file_path).resolve()
    try:
        rel = p.relative_to(Path.cwd().resolve()).as_posix()
        esc = rel.replace(":", r"\:").replace("'", r"\'")
        return f"ass='{esc}'"
    except Exception:
        esc = p.as_posix().replace(":", r"\:").replace("'", r"\'")
        return f"ass='{esc}'"


def parse_srt_to_dialogues(srt_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Parse .srt or .vtt subtitle file into standardized dialogue dictionaries."""
    dialogues = []
    try:
        with open(srt_path, "r", encoding="utf-8-sig", errors="ignore") as f:
            content = f.read()

        def _ts_to_sec(ts: str) -> float:
            ts = ts.strip().replace(",", ".")
            parts = ts.split(":")
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            return 0.0

        pattern = re.compile(
            r"(\d+)?\s*\r?\n?(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,\.]\d{1,3})\r?\n(.*?)(?=\r?\n\r?\n|\Z)",
            re.DOTALL
        )
        for match in pattern.finditer(content):
            s_sec = _ts_to_sec(match.group(2))
            e_sec = _ts_to_sec(match.group(3))
            txt = match.group(4).strip()
            clean_txt = re.sub(r"<[^>]+>", "", txt).strip()
            if clean_txt:
                dialogues.append({"start": s_sec, "end": e_sec, "text_km": clean_txt})
    except Exception as e:
        print(f"Error parsing subtitle file {srt_path}: {e}")
    return dialogues


def render_dubbed_video(
    original_video_path: str,
    mixed_audio_path: str,
    output_video_path: str,
    dialogues: Optional[List[Dict[str, Any]]] = None,
    burn_subtitles: bool = False,
    aspect_ratio: str = "16:9",  # "16:9" or "9:16"
    watermark_text: Optional[str] = None,
    overlay_config: Optional[Dict[str, Any]] = None,
    temp_dir: str = "cache/temp"
) -> str:
    """
    Render final dubbed video with new audio, subtitle burning, vertical 9:16 aspect ratio framing, 
    interactive Logo watermark overlay, and interactive Blur mask box.
    """
    out_p = Path(output_video_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    t_dir = Path(temp_dir)
    t_dir.mkdir(parents=True, exist_ok=True)

    # 1. Parse Subtitle, Logo, Blur, Text, and Lower Third Configurations
    sub_cfg = overlay_config.get("subtitle") if isinstance(overlay_config, dict) else None
    sub_active = bool(burn_subtitles or (sub_cfg and sub_cfg.get("active")))
    custom_sub_file = str(sub_cfg.get("custom_file") or "").strip() if sub_cfg else ""

    logo_cfg = overlay_config.get("logo") if isinstance(overlay_config, dict) else None
    blur_cfg = overlay_config.get("blur") if isinstance(overlay_config, dict) else None
    text_cfg = overlay_config.get("text") if isinstance(overlay_config, dict) else None
    lower_third_cfg = overlay_config.get("lower_third") if isinstance(overlay_config, dict) else None

    logo_active = bool(logo_cfg and logo_cfg.get("active") and logo_cfg.get("path") and Path(str(logo_cfg.get("path"))).exists())
    logo_path = str(Path(str(logo_cfg.get("path"))).resolve()) if logo_active else None

    blur_active = bool(blur_cfg and blur_cfg.get("active"))
    text_active = bool(text_cfg and text_cfg.get("active") and text_cfg.get("text"))

    lt_active = bool(lower_third_cfg and lower_third_cfg.get("active") and lower_third_cfg.get("path") and Path(str(lower_third_cfg.get("path"))).exists())
    lt_path = str(Path(str(lower_third_cfg.get("path"))).resolve()) if lt_active else None

    # 2. Detect video orientation & dimensions
    w, h = get_video_dimensions(original_video_path)
    w = w or 1920
    h = h or 1080
    is_already_vertical = (w < h)

    # 3. Phase 1 Turbo Optimization: Lossless Stream Copy Mode (1-2 seconds per episode!)
    # Only if NO subtitles, NO watermark, NO logo, NO blur, NO text, NO lower third, and no 9:16 framing needed
    can_use_stream_copy = (not sub_active) and (not watermark_text) and (not logo_active) and (not blur_active) and (not text_active) and (not lt_active) and (is_already_vertical or aspect_ratio != "9:16")
    if can_use_stream_copy:
        fast_cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-fflags", "+genpts",
            "-avoid_negative_ts", "make_zero",
            "-i", str(original_video_path),
            "-i", str(mixed_audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            "-shortest",
            str(out_p)
        ]
        fast_proc = subprocess.run(fast_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600, **get_silent_kwargs())
        if fast_proc.returncode == 0 and out_p.exists() and out_p.stat().st_size > 5000:
            try:
                import shutil
                exports_dir = Path("data/exports")
                exports_dir.mkdir(parents=True, exist_ok=True)
                stem = Path(original_video_path).stem
                export_copy = exports_dir / f"Dubbed_{stem}.mp4"
                shutil.copy2(str(out_p), str(export_copy))
            except Exception:
                pass
            return str(out_p)

    # 5. Build FFmpeg command inputs
    cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-i", str(original_video_path),
        "-i", str(mixed_audio_path)
    ]

    current_input_idx = 2
    logo_input_idx = None
    if logo_active and logo_path:
        cmd.extend(["-i", str(logo_path)])
        logo_input_idx = current_input_idx
        current_input_idx += 1

    lt_input_idx = None
    if lt_active and lt_path:
        lt_loop = bool(lower_third_cfg.get("loop", True))
        if lt_loop:
            cmd.extend(["-stream_loop", "-1"])
        cmd.extend(["-i", str(lt_path)])
        lt_input_idx = current_input_idx
        current_input_idx += 1

    # 6. Determine target dimensions & base video layout
    filter_parts = []
    if aspect_ratio == "9:16" and not is_already_vertical:
        target_w = 1080
        target_h = 1920
        filter_parts.append(
            "[0:v]split[bg][fg];"
            "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=12:1[bg_blur];"
            "[fg]scale=1080:-2[fg_scaled];"
            "[bg_blur][fg_scaled]overlay=(W-w)/2:(H-h)/2[v_base]"
        )
        current_v = "[v_base]"
    else:
        target_w = (w // 2) * 2
        target_h = (h // 2) * 2
        filter_parts.append(f"[0:v]scale={target_w}:{target_h}[v_base]")
        current_v = "[v_base]"

    # 7. Apply Blur Mask Box Filter
    if blur_active:
        norm_x = float(blur_cfg.get("norm_x", 0.0))
        norm_y = float(blur_cfg.get("norm_y", 0.50))
        norm_w = float(blur_cfg.get("norm_w", 1.0))
        norm_h = float(blur_cfg.get("norm_h", 0.08))
        radius = max(5, min(50, int(blur_cfg.get("radius", 25))))

        bw = max(16, min(target_w, int(target_w * norm_w)))
        bh = max(16, min(target_h, int(target_h * norm_h)))
        bx = max(0, min(target_w - bw, int(target_w * norm_x)))
        by = max(0, min(target_h - bh, int(target_h * norm_y)))

        # Snap to exact horizontal center if user centered it or selected centered preset
        is_blur_center = bool(blur_cfg.get("is_center")) or (norm_w >= 0.85) or (abs((bx + bw / 2.0) - target_w / 2.0) < (target_w * 0.04))
        if is_blur_center:
            if norm_w >= 0.88:
                bx = 0
                bw = target_w
            else:
                bx = max(0, (target_w - bw) // 2)

        bx = (bx // 2) * 2
        by = (by // 2) * 2
        bw = (bw // 2) * 2
        bh = (bh // 2) * 2

        bh = max(32, bh)
        b_power = max(2, min(radius, (bw // 4) - 1, (bh // 4) - 1, 18))
        filter_parts.append(
            f"{current_v}split[v_pre_blur][v_crop_in];"
            f"[v_crop_in]crop=w={bw}:h={bh}:x={bx}:y={by},boxblur={b_power}:2[v_blurred_box];"
            f"[v_pre_blur][v_blurred_box]overlay=x={bx}:y={by}[v_after_blur]"
        )
        current_v = "[v_after_blur]"

    # 8. Apply Logo Watermark Overlay Filter
    if logo_active and logo_path and logo_input_idx is not None:
        logo_norm_x = float(logo_cfg.get("norm_x", 0.04))
        logo_norm_y = float(logo_cfg.get("norm_y", 0.04))
        logo_norm_w = float(logo_cfg.get("norm_w", 0.16))
        opacity = max(0.1, min(1.0, float(logo_cfg.get("opacity", 1.0))))

        lw = max(32, min(target_w, int(target_w * logo_norm_w)))
        lw = (lw // 2) * 2
        lx = max(0, min(target_w - lw, int(target_w * logo_norm_x)))
        ly = max(0, min(target_h - 32, int(target_h * logo_norm_y)))

        is_logo_center = bool(logo_cfg.get("is_center")) or (abs((lx + lw / 2.0) - target_w / 2.0) < (target_w * 0.04))
        if is_logo_center:
            lx = max(0, (target_w - lw) // 2)

        filter_parts.append(
            f"[{logo_input_idx}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={opacity:.2f}[logo_scaled];"
            f"{current_v}[logo_scaled]overlay=x={lx}:y={ly}[v_after_logo]"
        )
        current_v = "[v_after_logo]"

    # 8.5 Apply Lower Third Video Overlay
    if lt_active and lt_path and lt_input_idx is not None:
        lt_orig_w, lt_orig_h = get_video_dimensions(lt_path)
        lt_orig_w = lt_orig_w or 2000
        lt_orig_h = lt_orig_h or 2500

        lt_norm_x = float(lower_third_cfg.get("norm_x", 0.0))
        lt_norm_y = float(lower_third_cfg.get("norm_y", 0.0))
        lt_norm_w = float(lower_third_cfg.get("norm_w", 1.0))
        lt_opacity = max(0.05, min(1.0, float(lower_third_cfg.get("opacity", 1.0))))
        lt_speed = max(0.25, min(4.0, float(lower_third_cfg.get("speed", 1.0))))
        lt_start = max(0.0, float(lower_third_cfg.get("start_time", 0.0)))
        lt_end = float(lower_third_cfg.get("end_time", 0.0))
        pos_type = str(lower_third_cfg.get("position", "bottom-center")).lower()

        lt_w = max(48, min(target_w, int(target_w * lt_norm_w)))
        lt_w = (lt_w // 2) * 2
        lt_h = int(round(lt_w * (lt_orig_h / float(lt_orig_w))))
        lt_h = (lt_h // 2) * 2

        is_lt_center = bool(lower_third_cfg.get("is_center")) or ("center" in pos_type) or (lt_norm_w >= 0.95)
        if is_lt_center or lt_norm_w >= 0.95:
            lt_x = max(0, (target_w - lt_w) // 2)
        else:
            lt_x = max(0, min(target_w - lt_w, int(target_w * lt_norm_x)))

        # Y position calculation:
        user_dragged = bool(lower_third_cfg.get("user_dragged"))
        if user_dragged or ("norm_y" in lower_third_cfg and abs(lt_norm_y) > 0.001):
            lt_y = int(round(target_h * lt_norm_y))
        elif "top" in pos_type:
            lt_y = -int(round(lt_h * 0.42))
        else:
            lt_y = max(0, target_h - lt_h)

        # Safety bound clamp: allow full top flush (negative offset) and full bottom flush
        lt_y = max(-int(lt_h * 0.85), min(target_h - int(lt_h * 0.15), lt_y))

        # Build enable condition
        if lt_end > lt_start and lt_end > 0.05:
            enable_expr = f":enable='between(t,{lt_start:.2f},{lt_end:.2f})'"
        elif lt_start > 0.05:
            enable_expr = f":enable='gte(t,{lt_start:.2f})'"
        else:
            enable_expr = ""

        # Build speed filter (pts multiplier = 1 / speed)
        speed_factor = 1.0 / lt_speed
        pts_filter = f"setpts={speed_factor:.3f}*PTS,"

        filter_parts.append(
            f"[{lt_input_idx}:v]{pts_filter}scale={lt_w}:-2,format=rgba,colorchannelmixer=aa={lt_opacity:.2f}[lt_scaled];"
            f"{current_v}[lt_scaled]overlay=x={lt_x}:y={lt_y}{enable_expr}[v_after_lt]"
        )
        current_v = "[v_after_lt]"

    # 9. Apply ASS Subtitles Burning
    if sub_active:
        ass_filter_cmd = None
        sub_style = str(sub_cfg.get("style", "viral_yellow")) if sub_cfg else "viral_yellow"
        sub_anim = str(sub_cfg.get("animation", "pop")).lower() if sub_cfg else "pop"
        sub_size = int(sub_cfg.get("size", 48)) if sub_cfg else 48
        sub_margin_v = int(sub_cfg.get("margin_v", 65)) if sub_cfg else 65

        # Calculate exact pixel coordinates (pos_x, pos_y) matching user positioning on preview
        sub_center_x = float(sub_cfg.get("center_x", 0.50)) if sub_cfg else 0.50
        sub_norm_y = sub_cfg.get("norm_y") if sub_cfg else None

        if sub_norm_y is not None:
            try:
                sub_pos_y = int(round(target_h * float(sub_norm_y)))
            except (ValueError, TypeError):
                sub_pos_y = target_h - sub_margin_v
        else:
            sub_pos_y = target_h - sub_margin_v

        # Ensure pos_y is safely bounded within the visible video canvas
        sub_pos_y = max(int(target_h * 0.06), min(int(target_h * 0.98), sub_pos_y))
        sub_pos_x = int(round(target_w * sub_center_x))

        target_dialogues = dialogues or []
        if custom_sub_file and Path(custom_sub_file).exists():
            c_ext = Path(custom_sub_file).suffix.lower()
            if c_ext in (".srt", ".vtt"):
                parsed_d = parse_srt_to_dialogues(custom_sub_file)
                if parsed_d:
                    target_dialogues = parsed_d
            elif c_ext == ".ass":
                ass_filter_cmd = format_ass_filter_path(Path(custom_sub_file))

        if not ass_filter_cmd and target_dialogues:
            ass_content = generate_ass_subtitles(
                target_dialogues, 
                style=sub_style, 
                fontsize=sub_size, 
                margin_v=sub_margin_v,
                play_res_x=target_w,
                play_res_y=target_h,
                pos_x=sub_pos_x,
                pos_y=sub_pos_y,
                animation=sub_anim
            )
            ass_file = t_dir / "subtitles_khmer.ass"
            with open(ass_file, "w", encoding="utf-8") as f:
                f.write(ass_content)
            ass_filter_cmd = format_ass_filter_path(ass_file)

        if ass_filter_cmd:
            filter_parts.append(f"{current_v}{ass_filter_cmd}[v_after_subs]")
            current_v = "[v_after_subs]"

    # 10. Apply Watermark Text
    if watermark_text and watermark_text.strip():
        wm_clean = watermark_text.replace("'", "").replace(":", "")
        filter_parts.append(
            f"{current_v}drawtext=text='{wm_clean}':fontsize=24:fontcolor=white@0.8:x=30:y=30:box=1:boxcolor=black@0.4:boxborderw=6[v_after_wm]"
        )
        current_v = "[v_after_wm]"

    # 10.5 Apply Watermark/Title Text Overlay (Universal High-Fidelity ASS Engine)
    if text_active:
        t_raw = str(text_cfg.get("text", "")).strip()
        if t_raw:
            t_size = int(text_cfg.get("size", 24))
            norm_fs = float(text_cfg.get("norm_font_size", 0.0))
            if norm_fs > 0.005:
                ass_fontsize = max(24, int(round(target_h * norm_fs)))
            else:
                ass_fontsize = max(28, int(round(t_size * (target_h / 560.0))))

            t_center_x = float(text_cfg.get("center_x", text_cfg.get("norm_center_x", 0.50)))
            t_norm_y = float(text_cfg.get("norm_y", 0.85))
            is_center = bool(text_cfg.get("is_center")) or (abs(t_center_x - 0.50) < 0.04)
            if is_center:
                t_center_x = 0.50

            t_color = str(text_cfg.get("color", "#ffffff")).lstrip("#")
            t_bg = bool(text_cfg.get("bg", True))
            t_motion = str(text_cfg.get("motion", "static")).lower()
            t_speed = max(15, min(250, int(text_cfg.get("speed", 65))))
            segments = text_cfg.get("segments") or []

            t_col_hex = t_color.strip().lstrip('#')
            if len(t_col_hex) == 6:
                tr, tg, tb = t_col_hex[0:2], t_col_hex[2:4], t_col_hex[4:6]
            else:
                tr, tg, tb = "FF", "FF", "FF"
            style_primary = f"&H00{tb}{tg}{tr}&"

            def _hex_to_ass_inline(h_str: str) -> str:
                h = h_str.strip().lstrip('#')
                if len(h) != 6:
                    return "&HFFFFFF&"
                r, g, b = h[0:2], h[2:4], h[4:6]
                return f"&H{b}{g}{r}&"

            ass_styled_text = ""
            if isinstance(segments, list) and len(segments) > 0:
                for seg in segments:
                    if not isinstance(seg, dict):
                        continue
                    w_txt = str(seg.get("text", "")).replace("{", "").replace("}", "")
                    w_col = str(seg.get("color", "#" + t_color))
                    ass_styled_text += f"{{\\c{_hex_to_ass_inline(w_col)}}}{w_txt} "
                ass_styled_text = ass_styled_text.strip()
            else:
                clean_t = t_raw.replace("{", "").replace("}", "")
                ass_styled_text = clean_t

            # Ensure newline breaks are preserved in ASS format (\N)
            ass_styled_text = ass_styled_text.replace("\r\n", "\\N").replace("\n", "\\N")

            ass_file = t_dir / "title_overlay.ass"
            border_style = 3 if t_bg else 1
            back_color = "&HA0000000" if t_bg else "&H80000000"
            outline_w = max(4, int(ass_fontsize * 0.12)) if t_bg else max(3, int(ass_fontsize * 0.08))
            shadow_val = 0 if t_bg else 1.5

            pos_x = int(target_w * t_center_x)
            pos_y = int(target_h * t_norm_y)

            ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {target_w}
PlayResY: {target_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TitleStyle,Kantumruy Pro,{ass_fontsize},{style_primary},&H000000FF,&H00000000,{back_color},-1,0,0,0,100,100,0,0,{border_style},{outline_w},{shadow_val},8,30,30,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
            ass_events = []
            if t_motion in ("scroll_up", "scroll_down"):
                # Retrieve explicit cycle duration from frontend or map based on speed
                explicit_dur = text_cfg.get("scroll_duration") or text_cfg.get("duration")
                if explicit_dur:
                    try:
                        cycle_duration = float(explicit_dur)
                    except Exception:
                        cycle_duration = 6.5
                else:
                    cycle_duration = 9.5 if t_speed <= 45 else (4.0 if t_speed >= 90 else 6.5)

                cycle_duration = max(2.0, min(30.0, cycle_duration))
                # Total cycles covering up to 4 hours of video
                total_cycles = min(2500, int(14400 / cycle_duration) + 1)

                # Vertical bounds: start completely off-screen and end completely off-screen so text never gets cut off
                y_bottom = target_h + int(ass_fontsize * 1.5)
                y_top = -int(ass_fontsize * 2.5)

                if t_motion == "scroll_up":
                    move_y_start, move_y_end = y_bottom, y_top
                else:  # scroll_down
                    move_y_start, move_y_end = y_top, y_bottom

                fade_ms = min(400, int(cycle_duration * 1000 * 0.06))

                for c_idx in range(total_cycles):
                    c_start = c_idx * cycle_duration
                    c_end = (c_idx + 1) * cycle_duration
                    s_str = f"{int(c_start//3600)}:{int((c_start%3600)//60):02d}:{c_start%60:05.2f}"
                    e_str = f"{int(c_end//3600)}:{int((c_end%3600)//60):02d}:{c_end%60:05.2f}"
                    # \an8 anchor keeps horizontal position pos_x centered/exact while \move travels smoothly without stutter or premature cutoff
                    ass_events.append(
                        f"Dialogue: 0,{s_str},{e_str},TitleStyle,,0,0,0,,{{\\an8\\move({pos_x},{move_y_start},{pos_x},{move_y_end})\\fad({fade_ms},{fade_ms})}}{ass_styled_text}"
                    )
            else:
                # \an8 (top-center anchor) guarantees exact horizontal centering at pos_x and vertical placement at pos_y
                ass_events.append(f"Dialogue: 0,0:00:00.00,9:59:59.00,TitleStyle,,0,0,0,,{{\\an8\\pos({pos_x},{pos_y})}}{ass_styled_text}")

            with open(ass_file, "w", encoding="utf-8") as f:
                f.write(ass_header + "\n".join(ass_events) + "\n")

            title_ass_filter = format_ass_filter_path(ass_file)
            filter_parts.append(
                f"{current_v}{title_ass_filter}[v_after_txt]"
            )
            current_v = "[v_after_txt]"

    # 11. Final Filter Complex and Encoding Flags
    full_filter_complex = ";".join(filter_parts)
    cmd.extend([
        "-filter_complex", full_filter_complex,
        "-map", current_v,
        "-map", "1:a:0",
        "-threads", str(min(4, os.cpu_count() or 2)),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-tune", "fastdecode",
        "-max_muxing_queue_size", "1024",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-ac", "2",
        "-shortest",
        str(out_p)
    ])

    import gc
    gc.collect()

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=7200, **get_silent_kwargs())
    gc.collect()

    if proc.returncode != 0:
        err_msg = proc.stderr or ""
        try:
            with open("render_err.log", "w", encoding="utf-8") as ef:
                ef.write(err_msg)
        except Exception:
            pass
        safe_preview = err_msg[:200].encode('ascii', errors='replace').decode('ascii')
        print(f"Render fallback triggered: {safe_preview}")
        # Direct mux fallback with universal H.264 and even dimension scaling
        fallback_cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-i", str(original_video_path),
            "-i", str(mixed_audio_path),
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-threads", str(min(4, os.cpu_count() or 2)),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "fastdecode",
            "-max_muxing_queue_size", "1024",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(out_p)
        ]
        subprocess.run(fallback_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=7200, **get_silent_kwargs())
        gc.collect()

    # Always ensure a copy exists in data/exports for easy user access!
    try:
        import shutil
        exports_dir = Path("data/exports")
        exports_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(original_video_path).stem
        export_copy = exports_dir / f"Dubbed_{stem}.mp4"
        shutil.copy2(str(out_p), str(export_copy))
    except Exception as e:
        print(f"Export copy note: {e}")

    return str(out_p)


def detect_ending_freeze_duration(
    video_path: Union[str, Path],
    scan_window_sec: float = 7.0,
    min_freeze_sec: float = 1.0,
    noise_tolerance: float = 0.003
) -> float:
    """
    Scans the outro / ending of a video to detect if it has frozen frames (cliffhanger still frame).
    Returns the duration in seconds of the trailing freeze (e.g. 2.45), or 0.0 if the ending is normal/active motion.
    
    Parameters:
      - video_path: Path to the video file
      - scan_window_sec: How many seconds before EOF to scan (default 7.0s)
      - min_freeze_sec: Minimum frozen duration to qualify as a cliffhanger pause (default 1.0s)
      - noise_tolerance: Frame pixel noise variance (0.003 allows minor compression artifacts)
    """
    try:
        dur = get_media_duration(str(video_path))
        if dur <= min_freeze_sec + 0.5:
            return 0.0
            
        scan_start = max(0.0, dur - scan_window_sec)
        window_dur = dur - scan_start

        cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-ss", f"{scan_start:.3f}",
            "-i", str(video_path),
            "-vf", f"freezedetect=n={noise_tolerance}:d={min_freeze_sec}",
            "-map", "0:v:0",
            "-f", "null",
            "-"
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            **get_silent_kwargs()
        )
        
        last_freeze_start = None
        last_freeze_end = None
        last_freeze_dur = None
        
        for line in proc.stderr.splitlines():
            if "lavfi.freezedetect.freeze_start:" in line:
                m = re.search(r"freeze_start:\s*([0-9.]+)", line)
                if m:
                    last_freeze_start = float(m.group(1))
                    last_freeze_end = None
                    last_freeze_dur = None
            elif "lavfi.freezedetect.freeze_end:" in line:
                m = re.search(r"freeze_end:\s*([0-9.]+)", line)
                if m:
                    last_freeze_end = float(m.group(1))
            elif "lavfi.freezedetect.freeze_duration:" in line:
                m = re.search(r"freeze_duration:\s*([0-9.]+)", line)
                if m:
                    last_freeze_dur = float(m.group(1))

        if last_freeze_start is None:
            return 0.0

        # Case 1: Still frozen all the way until EOF
        if last_freeze_end is None:
            freeze_tail = window_dur - last_freeze_start
            return round(freeze_tail, 2) if freeze_tail >= min_freeze_sec else 0.0

        # Case 2: Freeze ended right around EOF (container/packet rounding within 0.4s of end)
        if last_freeze_end >= (window_dur - 0.40):
            freeze_tail = last_freeze_dur if last_freeze_dur is not None else (window_dur - last_freeze_start)
            return round(freeze_tail, 2) if freeze_tail >= min_freeze_sec else 0.0

        # Case 3: Freeze happened earlier in the window, but scenes moved afterwards. Do NOT cut!
        return 0.0
    except Exception as e:
        print(f"[detect_ending_freeze_duration] Warning checking {video_path}: {e}")
        return 0.0


def merge_videos(
    video_paths: List[str],
    output_path: str,
    auto_trim_freeze: bool = True,
    return_details: bool = False
) -> Union[str, Dict[str, Any]]:
    """Merge multiple video clips / drama episodes into a single MP4 file.
    
    If auto_trim_freeze=True, automatically scans each episode using FFmpeg AI freeze detection.
    Episodes with a cliffhanger freeze (>= 1.0s still frame at the end) are trimmed losslessly.
    Episodes without frozen endings are kept 100% intact.
    """
    if not video_paths:
        raise ValueError("No video paths provided for merging.")
    
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    temp_dir = None
    processed_paths = []
    episode_details = []
    trimmed_count = 0
    total_freeze_saved = 0.0

    try:
        if auto_trim_freeze:
            temp_dir = Path(tempfile.mkdtemp(prefix="sn_freeze_trim_"))
            for idx, vp in enumerate(video_paths):
                vp_path = Path(vp).resolve()
                orig_dur = get_media_duration(str(vp_path))
                freeze_dur = detect_ending_freeze_duration(vp_path)
                
                # Check if this episode has a real freeze at the end
                if freeze_dur >= 1.0 and orig_dur > (freeze_dur + 1.0):
                    target_dur = max(0.5, orig_dur - freeze_dur)
                    temp_trimmed = temp_dir / f"ep_{idx:03d}_{vp_path.name}"
                    
                    trim_cmd = [
                        get_ffmpeg_path(),
                        "-nostdin",
                        "-y",
                        "-i", str(vp_path),
                        "-t", f"{target_dur:.3f}",
                        "-c", "copy",
                        "-avoid_negative_ts", "make_zero",
                        str(temp_trimmed)
                    ]
                    trim_proc = subprocess.run(
                        trim_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        **get_silent_kwargs()
                    )
                    
                    if trim_proc.returncode == 0 and temp_trimmed.exists() and temp_trimmed.stat().st_size > 1000:
                        processed_paths.append(str(temp_trimmed))
                        trimmed_count += 1
                        total_freeze_saved += freeze_dur
                        episode_details.append({
                            "index": idx + 1,
                            "filename": vp_path.name,
                            "original_duration": round(orig_dur, 2),
                            "freeze_duration": round(freeze_dur, 2),
                            "trimmed": True,
                            "final_duration": round(target_dur, 2)
                        })
                    else:
                        processed_paths.append(str(vp_path))
                        episode_details.append({
                            "index": idx + 1,
                            "filename": vp_path.name,
                            "original_duration": round(orig_dur, 2),
                            "freeze_duration": 0.0,
                            "trimmed": False,
                            "final_duration": round(orig_dur, 2)
                        })
                else:
                    processed_paths.append(str(vp_path))
                    episode_details.append({
                        "index": idx + 1,
                        "filename": vp_path.name,
                        "original_duration": round(orig_dur, 2),
                        "freeze_duration": 0.0,
                        "trimmed": False,
                        "final_duration": round(orig_dur, 2)
                    })
        else:
            processed_paths = [str(Path(p).resolve()) for p in video_paths]

        # Create concat list file
        list_file = out_p.parent / f"concat_list_{int(time.time())}.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for vp in processed_paths:
                f.write(f"file '{str(vp).replace(chr(92), '/')}'\n")

        cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-fflags", "+genpts",
            "-avoid_negative_ts", "make_zero",
            str(out_p)
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=7200, **get_silent_kwargs())
        if proc.returncode != 0:
            # 1. First fallback: re-encoding via concat demuxer (supports unlimited episode count cleanly)
            cmd_list_reencode = [
                get_ffmpeg_path(),
                "-nostdin",
                "-y",
                "-fflags", "+genpts",
                "-avoid_negative_ts", "make_zero",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                str(out_p)
            ]
            proc_list_re = subprocess.run(cmd_list_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=7200, **get_silent_kwargs())
            if proc_list_re.returncode != 0 and len(processed_paths) <= 60:
                # 2. Second fallback: filter_complex concat for mismatched dimensions
                inputs = []
                filter_parts = []
                for idx, vp in enumerate(processed_paths):
                    inputs.extend(["-i", str(vp)])
                    filter_parts.append(f"[{idx}:v:0][{idx}:a:0]")
                
                filter_complex = f"{''.join(filter_parts)}concat=n={len(processed_paths)}:v=1:a=1[v][a]"
                cmd_reencode = [
                    get_ffmpeg_path(),
                    "-nostdin",
                    "-y",
                    *inputs,
                    "-filter_complex", filter_complex,
                    "-map", "[v]",
                    "-map", "[a]",
                    "-c:v", "libx264",
                    "-preset", "fast",
                    "-crf", "23",
                    "-c:a", "aac",
                    str(out_p)
                ]
                subprocess.run(cmd_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=7200, **get_silent_kwargs())
    finally:
        if 'list_file' in locals() and list_file.exists():
            try:
                list_file.unlink()
            except Exception:
                pass
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    if return_details:
        return {
            "output_file": str(out_p),
            "total_episodes": len(video_paths),
            "trimmed_count": trimmed_count,
            "unaltered_count": len(video_paths) - trimmed_count,
            "total_seconds_saved": round(total_freeze_saved, 2),
            "auto_trim_freeze": auto_trim_freeze,
            "details": episode_details
        }
    return str(out_p)


def split_video(video_path: str, chunk_duration_sec: int, output_dir: str) -> List[str]:
    """Split a video into segments of chunk_duration_sec with lossless stream copy and smart re-encode fallback."""
    in_p = Path(video_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_pattern = str(out_dir / f"{in_p.stem}_EP%03d.mp4")
    # 1. Primary: Ultra-fast Lossless Stream Copy
    cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-i", str(in_p),
        "-c", "copy",
        "-map", "0",
        "-segment_time", str(chunk_duration_sec),
        "-f", "segment",
        "-reset_timestamps", "1",
        out_pattern
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1200, **get_silent_kwargs())
    parts = sorted(out_dir.glob(f"{in_p.stem}_EP*.mp4"))
    
    # 2. Resilient Fallback: If lossless copy produced 0 parts due to keyframe/timestamp mismatch, re-encode seamlessly
    if not parts or proc.returncode != 0:
        cmd_fallback = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-i", str(in_p),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-segment_time", str(chunk_duration_sec),
            "-f", "segment",
            "-reset_timestamps", "1",
            out_pattern
        ]
        subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2400, **get_silent_kwargs())
        parts = sorted(out_dir.glob(f"{in_p.stem}_EP*.mp4"))

    if not parts:
        parts = sorted(out_dir.glob(f"{in_p.stem}_part*.mp4"))
    return [str(p) for p in parts]


def batch_rename_files(file_paths: List[str], prefix: str = "Drama_EP", start_num: int = 1) -> List[Dict[str, str]]:
    """Batch rename video files to a standardized format with collision-proof 2-step renaming and adaptive zero-padding."""
    results = []
    if not file_paths:
        return results

    total_count = len(file_paths)
    max_num = start_num + total_count - 1
    pad_len = 3 if max_num >= 100 else 2

    # Step 1: Pre-calculate target names and create safe collision-free temporary mapping
    rename_plan = []
    temp_stage = []
    
    for idx, fp in enumerate(file_paths, start=start_num):
        p = Path(fp).resolve()
        new_name = f"{prefix}{idx:0{pad_len}d}{p.suffix}"
        new_path = (p.parent / new_name).resolve()
        rename_plan.append((p, new_path, new_name))

    # Step 2: Safe intermediate rename to avoid in-place collisions on Windows
    for idx, (orig_p, target_p, new_name) in enumerate(rename_plan):
        if orig_p.exists() and orig_p != target_p:
            tmp_p = orig_p.parent / f".sn_tmp_rename_{int(time.time())}_{idx:04d}_{orig_p.name}"
            try:
                orig_p.rename(tmp_p)
                temp_stage.append((tmp_p, target_p, str(orig_p), new_name))
            except Exception as e:
                results.append({"old": str(orig_p), "new": str(orig_p), "error": str(e)})
        else:
            results.append({"old": str(orig_p), "new": str(target_p), "name": new_name})

    # Step 3: Finalize to target names
    for tmp_p, target_p, old_str, new_name in temp_stage:
        try:
            if tmp_p.exists():
                tmp_p.rename(target_p)
            results.append({"old": old_str, "new": str(target_p), "name": new_name})
        except Exception as e:
            try:
                if tmp_p.exists():
                    tmp_p.rename(Path(old_str))
            except Exception:
                pass
            results.append({"old": old_str, "new": old_str, "error": str(e)})

    return results


def compress_video(video_path: str, output_path: str, crf: int = 26, preset: str = "fast", target_height: Optional[int] = None) -> str:
    """Compress video using H.264 with optimized CRF and optional downscaling."""
    in_p = Path(video_path)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-i", str(in_p)
    ]
    
    if target_height:
        cmd.extend(["-vf", f"scale=-2:{target_height}"])
        
    cmd.extend([
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", "aac",
        "-b:a", "128k",
        str(out_p)
    ])
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600, **get_silent_kwargs())
    return str(out_p)

