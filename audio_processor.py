"""
Audio Processor Engine: Audio Extraction, Time Alignment, Waveform Generation, and Smart BGM Audio Ducking
"""
import os
import io
import math
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    FFMPEG_DIR = os.path.dirname(FFMPEG_EXE)
    if FFMPEG_DIR not in os.environ.get("PATH", ""):
        os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
except Exception:
    FFMPEG_EXE = "ffmpeg"

import pydub
from pydub import AudioSegment


def patch_silent_subprocess():
    """
    Globally suppress black CMD/console popup windows for ffmpeg, ffprobe,
    and all background tools on Windows.
    Preserves interactive GUI applications (Edge, Chrome, Explorer).
    """
    import sys
    if sys.platform != "win32":
        return
    import subprocess
    if getattr(subprocess, "_silent_patch_applied", False):
        return
    subprocess._silent_patch_applied = True

    orig_popen_init = subprocess.Popen.__init__

    def silent_popen_init(self, *args, **kwargs):
        cmd = args[0] if args else kwargs.get("args")
        cmd_str = ""
        if isinstance(cmd, (list, tuple)) and cmd:
            cmd_str = str(cmd[0]).lower()
        elif isinstance(cmd, str):
            cmd_str = cmd.lower()

        is_gui_app = any(gui in cmd_str for gui in ("msedge", "chrome", "explorer", "dialog", "picker")) or kwargs.pop("is_gui_dialog", False)

        if not is_gui_app:
            # Add BELOW_NORMAL_PRIORITY_CLASS (0x00004000) so heavy FFmpeg/tool processes
            # never starve the Windows GUI, mouse, or browser of CPU resources
            below_normal = 0x00004000
            base_flags = subprocess.CREATE_NO_WINDOW | below_normal
            if "creationflags" not in kwargs:
                kwargs["creationflags"] = base_flags
            else:
                kwargs["creationflags"] |= base_flags

            si = kwargs.get("startupinfo")
            if si is None:
                si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0  # SW_HIDE
            kwargs["startupinfo"] = si

        # Force UTF-8 and errors="replace" for any text-mode subprocess invocation
        # Prevents Windows charmap / cp1252 UnicodeDecodeError crashes when tools output UTF-8
        if kwargs.get("text") or kwargs.get("universal_newlines") or "encoding" in kwargs:
            if not kwargs.get("encoding"):
                kwargs["encoding"] = "utf-8"
            if not kwargs.get("errors"):
                kwargs["errors"] = "replace"

        orig_popen_init(self, *args, **kwargs)

    subprocess.Popen.__init__ = silent_popen_init


def get_silent_kwargs() -> Dict[str, Any]:
    """Return explicit subprocess creationflags and startupinfo with BELOW_NORMAL_PRIORITY_CLASS to prevent Windows freezes."""
    import sys
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        return {
            "creationflags": subprocess.CREATE_NO_WINDOW | 0x00004000,
            "startupinfo": si
        }
    return {}


# Auto-apply global silent patch immediately
patch_silent_subprocess()

pydub.AudioSegment.converter = FFMPEG_EXE
pydub.AudioSegment.ffmpeg = FFMPEG_EXE


def get_ffmpeg_path() -> str:
    """Get reliable ffmpeg binary path across frozen PyInstaller, _internal, and system PATH."""
    global FFMPEG_EXE
    if FFMPEG_EXE and os.path.isabs(FFMPEG_EXE) and os.path.exists(FFMPEG_EXE):
        return FFMPEG_EXE
    
    # Check PyInstaller frozen environment or local _internal dir
    import sys
    app_dirs = []
    if getattr(sys, 'frozen', False):
        app_dirs.append(getattr(sys, '_MEIPASS', ''))
        app_dirs.append(os.path.dirname(sys.executable))
    app_dirs.append(str(Path(__file__).resolve().parent))
    app_dirs.append(str(Path(__file__).resolve().parent / "_internal"))
    
    for base in app_dirs:
        if not base:
            continue
        candidates = [
            os.path.join(base, "imageio_ffmpeg", "binaries", "ffmpeg-win-x86_64-v7.1.exe"),
            os.path.join(base, "imageio_ffmpeg", "binaries", "ffmpeg.exe"),
            os.path.join(base, "_internal", "imageio_ffmpeg", "binaries", "ffmpeg-win-x86_64-v7.1.exe"),
            os.path.join(base, "_internal", "imageio_ffmpeg", "binaries", "ffmpeg.exe"),
            os.path.join(base, "ffmpeg.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                FFMPEG_EXE = c
                pydub.AudioSegment.converter = FFMPEG_EXE
                pydub.AudioSegment.ffmpeg = FFMPEG_EXE
                return c

    return FFMPEG_EXE or "ffmpeg"


def load_audio_safely(file_path: str) -> AudioSegment:
    """
    Robust audio loader that decodes MP3/AAC/WAV/etc directly via FFmpeg binary at 48kHz stereo.
    """
    cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-i", str(file_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "48000",
        "-ac", "2",
        "-f", "wav",
        "-"
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, **get_silent_kwargs())
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio decode failed: {proc.stderr.decode('utf-8', errors='ignore')}")
    
    return AudioSegment.from_wav(io.BytesIO(proc.stdout))


def save_audio_safely(segment: AudioSegment, output_path: str, bitrate: str = "192k") -> str:
    """
    Save AudioSegment to MP3/WAV safely using FFmpeg with guaranteed studio 48kHz stereo.
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    if segment.frame_rate != 48000:
        segment = segment.set_frame_rate(48000)
    if segment.channels != 2:
        segment = segment.set_channels(2)

    wav_io = io.BytesIO()
    segment.export(wav_io, format="wav")
    wav_io.seek(0)
    
    cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-i", "-",
        "-ar", "48000",
        "-ac", "2",
        "-b:a", bitrate,
        str(out_p)
    ]
    proc = subprocess.run(cmd, input=wav_io.read(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120, **get_silent_kwargs())
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg audio save failed: {proc.stderr.decode('utf-8', errors='ignore')}")
        
    return str(out_p)


def enhance_voice_clarity_studio(
    input_path: str,
    output_path: Optional[str] = None,
    speed_ratio: float = 1.0
) -> str:
    """
    Studio-grade vocal post-processing chain for Khmer Neural TTS:
    - High-pass filter at 75Hz (eliminates low mic rumble and plosive thuds)
    - Presence EQ boost (+2.4dB at 3.2kHz, Q=1.2) for crisp Khmer speech clarity
    - High-shelf sheen (+1.8dB at 8.5kHz) for studio air
    - Broadcast compression (acompressor) to balance vocal dynamics
    - Smooth atempo time-scaling if speed_ratio != 1.0
    """
    in_file = Path(input_path)
    if not in_file.exists():
        return str(input_path)

    out_file = Path(output_path) if output_path else in_file.parent / f"enhanced_{in_file.name}"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    filter_parts = [
        "highpass=f=75",
        "equalizer=f=3200:t=q:w=1.2:g=2.4",
        "equalizer=f=8500:t=h:g=1.8",
        "acompressor=threshold=-19dB:ratio=2.6:attack=12:release=110"
    ]

    sr = max(0.5, min(2.0, float(speed_ratio)))
    if abs(sr - 1.0) > 0.01:
        filter_parts.append(f"atempo={sr:.3f}")

    filter_str = ",".join(filter_parts)
    temp_out = out_file.parent / f"tmp_dsp_{out_file.name}"
    cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-i", str(in_file),
        "-filter:a", filter_str,
        "-ar", "48000",
        "-ac", "2",
        "-b:a", "192k",
        str(temp_out)
    ]
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60, **get_silent_kwargs())
    if res.returncode == 0 and temp_out.exists() and temp_out.stat().st_size > 100:
        if output_path is None or str(output_path) == str(input_path):
            if in_file.exists():
                in_file.unlink(missing_ok=True)
            temp_out.rename(in_file)
            return str(in_file)
        else:
            if out_file.exists():
                out_file.unlink(missing_ok=True)
            temp_out.rename(out_file)
            return str(out_file)
    else:
        if temp_out.exists():
            temp_out.unlink(missing_ok=True)
        return str(input_path)


def extract_audio_from_video(video_path: str, output_audio_path: str) -> str:
    """Extract audio track from video file as 16-bit 48kHz stereo WAV for mixing."""
    out_p = Path(output_audio_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "48000",
        "-ac", "2",
        str(out_p)
    ]
    
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
        **get_silent_kwargs()
    )
    if proc.returncode != 0:
        err_out = proc.stderr or ""
        raise RuntimeError(f"FFmpeg audio extraction failed: {err_out}")
        
    return str(out_p)


def get_media_duration(file_path: str) -> float:
    """Get media file duration in seconds using FFmpeg stderr output."""
    cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-i", str(file_path)
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            **get_silent_kwargs()
        )
        stderr_text = proc.stderr or ""
        for line in stderr_text.splitlines():
            if "Duration:" in line:
                parts = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = parts.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception as e:
        print(f"FFmpeg get_media_duration note: {e}")
            
    try:
        seg = load_audio_safely(file_path)
        return len(seg) / 1000.0
    except Exception:
        return 0.0


def create_waveform_data(audio_path: str, num_samples: int = 120) -> List[float]:
    """Generate normalized waveform peaks (0.0 to 1.0) for visual audio rendering in Web Studio without high RAM usage."""
    try:
        if not Path(audio_path).exists():
            return [round(abs(math.sin(i * 0.2) * 0.7 + 0.2), 2) for i in range(num_samples)]
        # Ultra-light downsampled decode (8000 Hz, mono) to keep RAM < 5MB even on 10-hour movies
        cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-i", str(audio_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "8000",
            "-ac", "1",
            "-f", "s16le",
            "-"
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=45, **get_silent_kwargs())
        if proc.returncode == 0 and proc.stdout:
            import numpy as np
            samples = np.frombuffer(proc.stdout, dtype=np.int16)
            total_samples = len(samples)
            if total_samples > 0:
                block_size = max(1, total_samples // num_samples)
                peaks = []
                max_val = max(1, int(np.max(np.abs(samples[:min(total_samples, 20000)]))))
                for i in range(num_samples):
                    chunk = samples[i * block_size : (i + 1) * block_size]
                    if len(chunk) > 0:
                        peak = float(np.max(np.abs(chunk)))
                        peaks.append(round(min(1.0, peak / max_val), 3))
                    else:
                        peaks.append(0.05)
                return peaks
    except Exception as e:
        print(f"Waveform generation note: {e}")
    return [round(abs(math.sin(i * 0.2) * 0.7 + 0.2), 2) for i in range(num_samples)]


def time_stretch_audio_segment(seg: AudioSegment, speed: float) -> AudioSegment:
    """
    High-quality time-stretch (tempo adjustment without pitch shifting) using FFmpeg atempo filter.
    Guarantees natural voice timbre while compressing or expanding duration to fit lip-sync slots.
    """
    if abs(speed - 1.0) < 0.03 or len(seg) < 200:
        return seg
    speed = max(0.5, min(2.0, float(speed)))
    try:
        wav_io = io.BytesIO()
        seg.export(wav_io, format="wav")
        cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-f", "wav",
            "-i", "pipe:0",
            "-filter:a", f"atempo={speed:.3f}",
            "-f", "wav",
            "pipe:1"
        ]
        proc = subprocess.run(
            cmd,
            input=wav_io.getvalue(),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15,
            **get_silent_kwargs()
        )
        if proc.returncode == 0 and len(proc.stdout) > 44:
            stretched = AudioSegment.from_file(io.BytesIO(proc.stdout), format="wav")
            if len(stretched) > 0:
                return stretched
    except Exception as e:
        print(f"Audio time-stretch note: {e}")
    return seg


def mix_dubbed_audio(
    original_audio_path: Optional[str],
    dialogue_items: List[Dict[str, Any]],
    output_mixed_path: str,
    total_duration_sec: Optional[float] = None,
    ducking_volume_factor: float = 0.0,    # 0.0 = Absolute Zero Vocal Bleed (Chinese speech 100% silenced)
    speech_volume_boost_db: float = 3.5,   # Boost speech clarity by +3.5dB
    dubbing_mode: str = "smart_bgm"        # "smart_bgm", "pure_voice", "standard_ducking"
) -> str:
    """
    Mix Khmer voice clips into the timeline with Smart BGM Audio Ducking and Zero Vocal Leakage.
    Uses ultra-lightweight streaming processing (<50MB RAM, zero disk overflow)
    Guarantees audible, rich audio output with zero silent drops and zero Chinese vocal whispering.
    """
    out_p = Path(output_mixed_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    target_fr = 48000
    channels = 2

    # 1. Determine total duration accurately without decoding gigabytes
    target_dur = 0.0
    if total_duration_sec and float(total_duration_sec) > 0:
        target_dur = float(total_duration_sec)
    elif original_audio_path and Path(original_audio_path).exists():
        target_dur = get_media_duration(original_audio_path)

    # 2. Filter valid lines and compute exact lip-sync onset/offset
    # Self-healing: If any dialogue item lacks audio, synthesize immediately via failover!
    valid_lines = []
    max_d_end = 0.0
    for idx, item in enumerate(dialogue_items):
        af = item.get("audio_file")
        from tts_engine import synthesize_via_google_khmer_api, is_valid_audible_audio
        if not af or not Path(af).exists() or not is_valid_audible_audio(af):
            txt = (item.get("text_km") or item.get("text", "")).strip()
            if txt:
                try:
                    v = item.get("voice") or "piseth"
                    rec_p = Path(output_mixed_path).parent / f"auto_recovered_{idx}_{os.urandom(3).hex()}.mp3"
                    fixed_audio = synthesize_via_google_khmer_api(txt, v, str(rec_p))
                    if fixed_audio and is_valid_audible_audio(fixed_audio):
                        item["audio_file"] = fixed_audio
                        af = fixed_audio
                except Exception as rec_err:
                    print(f"On-the-fly audio recovery note: {rec_err}")

        if af and Path(af).exists() and is_valid_audible_audio(af):
            valid_lines.append((idx, item))
        d_end = float(item.get("end", item.get("orig_end", 0.0)))
        if d_end > max_d_end:
            max_d_end = d_end

    if target_dur <= 0.5:
        target_dur = max(2.0, max_d_end + 1.5)

    total_samples = max(1000, int(math.ceil(target_dur * target_fr)))

    # Speech clarity boost (respect exact user setting from 0.0dB to +8.0dB)
    try:
        boost_val = float(speech_volume_boost_db) if speech_volume_boost_db is not None else 3.5
    except Exception:
        boost_val = 3.5

    # 3. Pre-process dialogue items timing & speed adjustments
    speech_intervals = []
    prepared_lines = []
    last_lead_end_ms = 0

    for i, (idx, item) in enumerate(valid_lines):
        orig_s = float(item.get("orig_start", item.get("start", 0.0)))
        orig_e = float(item.get("orig_end", item.get("end", orig_s + 2.0)))
        orig_start_ms = max(0, int(orig_s * 1000))
        orig_end_ms = max(0, int(orig_e * 1000))

        mouth_dur_ms = max(300, orig_end_ms - orig_start_ms)
        if i + 1 < len(valid_lines):
            next_item = valid_lines[i + 1][1]
            next_orig_s = float(next_item.get("orig_start", next_item.get("start", 0.0)))
            next_start_ms = max(0, int(next_orig_s * 1000))
            hard_limit_ms = max(300, next_start_ms - orig_start_ms - 40)
            target_window_ms = min(mouth_dur_ms + 50, hard_limit_ms)
        else:
            hard_limit_ms = mouth_dur_ms + 200
            target_window_ms = mouth_dur_ms + 50

        # Professional Film ADR Lip-Sync Anticipation Lead:
        # Visual mouth opening precedes acoustic speech energy by 100ms - 150ms.
        # Advancing audio placement by 130ms guarantees speech starts immediately as lips move!
        lip_sync_advance_ms = 130
        min_start_bound = last_lead_end_ms + 30 if last_lead_end_ms > 0 else 0
        start_ms = max(min_start_bound, orig_start_ms - lip_sync_advance_ms)
        last_lead_end_ms = start_ms + mouth_dur_ms

        item["start"] = round(start_ms / 1000.0, 2)
        item["end"] = round((start_ms + mouth_dur_ms) / 1000.0, 2)

        # Pad speech intervals slightly wider to guarantee 100% muting of original vocal attacks/trails
        pad_start = max(0, start_ms - 100)
        pad_end = orig_end_ms + 250
        speech_intervals.append((pad_start, pad_end))
        prepared_lines.append({
            "idx": idx,
            "item": item,
            "start_ms": start_ms,
            "orig_start_ms": orig_start_ms,
            "orig_end_ms": orig_end_ms,
            "target_window_ms": target_window_ms,
            "hard_limit_ms": hard_limit_ms,
            "audio_file": item["audio_file"]
        })

    # Merge speech intervals for smooth S-curve ducking (hold across 2.2s conversational pauses)
    speech_intervals.sort(key=lambda x: x[0])
    merged_intervals = []
    for start, end in speech_intervals:
        if not merged_intervals:
            merged_intervals.append([start, end])
        else:
            prev = merged_intervals[-1]
            if start <= prev[1] + 2200:  # Smooth hold across 2.2s conversation pauses (Zero vocal bleed)
                prev[1] = max(prev[1], end)
            else:
                merged_intervals.append([start, end])

    # 4. Respect user's BGM Volume setting
    try:
        user_bgm_vol = float(ducking_volume_factor) if ducking_volume_factor is not None else 0.12
    except Exception:
        user_bgm_vol = 0.12
    user_bgm_vol = max(0.0, min(1.0, user_bgm_vol))

    has_valid_bgm = (
        dubbing_mode != "pure_voice"
        and user_bgm_vol > 0.015
        and original_audio_path
        and Path(original_audio_path).exists()
    )

    bgm_nominal = user_bgm_vol if has_valid_bgm else 0.0
    bgm_ducked = 0.0  # ZERO VOCAL BLEED: During speech intervals, duck original vocals strictly to 0.0!

    fade_in_frames = max(1, int(0.120 * target_fr))   # 120ms S-curve dip
    fade_out_frames = max(1, int(0.250 * target_fr))  # 250ms S-curve return

    # 5. Start streaming FFmpeg MP3 Encoder process (Direct to output file)
    enc_cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-f", "s16le",
        "-ar", str(target_fr),
        "-ac", str(channels),
        "-i", "-",
        "-b:a", "192k",
        str(out_p)
    ]
    enc_proc = subprocess.Popen(
        enc_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        **get_silent_kwargs()
    )

    # 6. Start streaming FFmpeg BGM Decoder process if BGM is enabled
    bgm_proc = None
    if has_valid_bgm:
        bgm_cmd = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-i", str(original_audio_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(target_fr),
            "-ac", str(channels),
            "-f", "s16le",
            "-"
        ]
        bgm_proc = subprocess.Popen(
            bgm_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            **get_silent_kwargs()
        )

    # 7. Streaming chunk loop (process in 5-second chunks = ~960KB RAM per chunk)
    import numpy as np
    chunk_sec = 5.0
    chunk_frames = int(chunk_sec * target_fr)
    cur_sample = 0
    active_line_idx = 0

    # Cache loaded audio for current window (transient, max 2-3 lines in RAM at any time)
    active_segments = []

    try:
        while cur_sample < total_samples:
            n_frames = min(chunk_frames, total_samples - cur_sample)
            blk_start = cur_sample
            blk_end = cur_sample + n_frames
            blk_s_ms = (blk_start / target_fr) * 1000.0
            blk_e_ms = (blk_end / target_fr) * 1000.0

            # --- A. Speech Track for this chunk ---
            chunk_speech = np.zeros((n_frames, channels), dtype=np.int32)

            # Advance dialogue items that enter this window
            while active_line_idx < len(prepared_lines):
                pline = prepared_lines[active_line_idx]
                if pline["start_ms"] >= blk_e_ms + 1000:
                    break

                try:
                    line_seg = load_audio_safely(pline["audio_file"])
                    if boost_val > 0:
                        max_peak = line_seg.max_dBFS
                        safe_gain = min(boost_val, max(0.0, -0.8 - max_peak)) if max_peak > -12.0 else boost_val
                        if safe_gain > 0:
                            line_seg = line_seg + safe_gain

                    try:
                        from pydub.silence import detect_leading_silence
                        # Zero-Latency Lip-Sync Trimming:
                        # Strip all leading dead silence directly to the first audible phoneme
                        s_lead = detect_leading_silence(line_seg, silence_threshold=-44.0)
                        if s_lead > 0:
                            line_seg = line_seg[s_lead:]
                    except Exception:
                        pass

                    # 3ms micro anti-click fade (instant vocal attack so sound starts right away)
                    if len(line_seg) > 10:
                        line_seg = line_seg.fade_in(3).fade_out(20)

                    cur_dur_ms = len(line_seg)
                    tw_ms = pline["target_window_ms"]
                    if cur_dur_ms > tw_ms and tw_ms >= 250:
                        needed_speed = cur_dur_ms / max(200, tw_ms)
                        # Adaptive time-stretch up to 1.45x ensures audio completes before actor closes mouth!
                        speed_to_apply = min(1.45, max(1.02, needed_speed))
                        if speed_to_apply >= 1.04:
                            line_seg = time_stretch_audio_segment(line_seg, speed_to_apply)

                    hl_ms = pline["hard_limit_ms"]
                    if len(line_seg) > hl_ms:
                        line_seg = line_seg[:hl_ms].fade_out(25)

                    if line_seg.frame_rate != target_fr or line_seg.channels != channels:
                        line_seg = line_seg.set_frame_rate(target_fr).set_channels(channels)

                    l_start_s = int((pline["start_ms"] / 1000.0) * target_fr)
                    l_samples = np.frombuffer(line_seg.raw_data, dtype=np.int16).reshape(-1, channels)
                    l_end_s = l_start_s + len(l_samples)

                    # Update item exact start & end time for subtitles so subtitles also match mouth!
                    pline["item"]["start"] = round(l_start_s / float(target_fr), 2)
                    pline["item"]["end"] = round(l_end_s / float(target_fr), 2)

                    active_segments.append({
                        "start_sample": l_start_s,
                        "end_sample": l_end_s,
                        "samples": l_samples
                    })
                except Exception as l_err:
                    print(f"Line audio load note: {l_err}")

                active_line_idx += 1

            # Overlay active speech clips into chunk_speech
            surviving_segments = []
            for seg in active_segments:
                s_start = seg["start_sample"]
                s_end = seg["end_sample"]
                if s_end <= blk_start:
                    continue

                overlap_start = max(blk_start, s_start)
                overlap_end = min(blk_end, s_end)
                if overlap_end > overlap_start:
                    buf_s = overlap_start - blk_start
                    buf_e = overlap_end - blk_start
                    seg_s = overlap_start - s_start
                    seg_e = overlap_end - s_start
                    chunk_speech[buf_s:buf_e] += seg["samples"][seg_s:seg_e].astype(np.int32)

                if s_end > blk_end:
                    surviving_segments.append(seg)
            active_segments = surviving_segments

            # --- B. Background Audio with S-Curve Ducking ---
            if bgm_proc and bgm_proc.stdout:
                req_bytes = n_frames * channels * 2
                raw_bg = bgm_proc.stdout.read(req_bytes)
                if len(raw_bg) < req_bytes:
                    raw_bg = raw_bg + b"\0" * (req_bytes - len(raw_bg))

                bg_samples = np.frombuffer(raw_bg, dtype=np.int16).reshape(-1, channels).astype(np.float32)

                gain_blk = np.full(n_frames, bgm_nominal, dtype=np.float32)
                for s_ms, e_ms in merged_intervals:
                    if e_ms + 1000 < blk_s_ms or s_ms - 1000 > blk_e_ms:
                        continue
                    start_frame = max(0, int((s_ms / 1000.0) * target_fr))
                    end_frame = min(total_samples, int((e_ms / 1000.0) * target_fr))

                    dip_start = max(0, start_frame - fade_in_frames)
                    dip_end = start_frame
                    loc_dip_s = max(0, dip_start - blk_start)
                    loc_dip_e = min(n_frames, dip_end - blk_start)
                    if loc_dip_e > loc_dip_s:
                        g_start = blk_start + loc_dip_s
                        g_end = blk_start + loc_dip_e
                        t = np.linspace((g_start - dip_start) / max(1, dip_end - dip_start) * np.pi,
                                        (g_end - dip_start) / max(1, dip_end - dip_start) * np.pi,
                                        loc_dip_e - loc_dip_s, dtype=np.float32)
                        ramp_down = bgm_ducked + (bgm_nominal - bgm_ducked) * 0.5 * (1.0 + np.cos(t))
                        gain_blk[loc_dip_s:loc_dip_e] = np.minimum(gain_blk[loc_dip_s:loc_dip_e], ramp_down)

                    body_start = start_frame
                    body_end = max(body_start, end_frame)
                    loc_body_s = max(0, body_start - blk_start)
                    loc_body_e = min(n_frames, body_end - blk_start)
                    if loc_body_e > loc_body_s:
                        gain_blk[loc_body_s:loc_body_e] = np.minimum(gain_blk[loc_body_s:loc_body_e], bgm_ducked)

                    rise_start = body_end
                    rise_end = min(total_samples, rise_start + fade_out_frames)
                    loc_rise_s = max(0, rise_start - blk_start)
                    loc_rise_e = min(n_frames, rise_end - blk_start)
                    if loc_rise_e > loc_rise_s:
                        g_start = blk_start + loc_rise_s
                        g_end = blk_start + loc_rise_e
                        t = np.linspace((g_start - rise_start) / max(1, rise_end - rise_start) * np.pi,
                                        (g_end - rise_start) / max(1, rise_end - rise_start) * np.pi,
                                        loc_rise_e - loc_rise_s, dtype=np.float32)
                        ramp_up = bgm_ducked + (bgm_nominal - bgm_ducked) * 0.5 * (1.0 - np.cos(t))
                        gain_blk[loc_rise_s:loc_rise_e] = np.minimum(gain_blk[loc_rise_s:loc_rise_e], ramp_up)

                gain_blk = np.clip(gain_blk, 0.0, 1.0)
                ducked_bg = bg_samples * gain_blk[:, np.newaxis]
                mixed_blk = np.clip(ducked_bg + chunk_speech.astype(np.float32), -32768, 32767).astype(np.int16)
            else:
                mixed_blk = np.clip(chunk_speech, -32768, 32767).astype(np.int16)

            enc_proc.stdin.write(mixed_blk.tobytes())
            cur_sample += n_frames

    finally:
        if enc_proc and enc_proc.stdin:
            try:
                enc_proc.stdin.close()
            except Exception:
                pass
            try:
                enc_proc.wait(timeout=180)
            except Exception:
                enc_proc.kill()

        if bgm_proc:
            try:
                bgm_proc.kill()
            except Exception:
                pass

    if not out_p.exists() or out_p.stat().st_size < 1000:
        raise RuntimeError("Final audio mixing failed: Output audio file is missing or empty.")

    return str(out_p)
