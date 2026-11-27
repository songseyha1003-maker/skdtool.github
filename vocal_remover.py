import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from audio_processor import get_ffmpeg_path, get_silent_kwargs

CACHE_DIR = Path("cache/audio_separation")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _probe_mean_volume_db(audio_path: Path, start_sec: int) -> float:
    """Measure short-window mean volume in dB via FFmpeg volumedetect."""
    probe_cmd = [
        get_ffmpeg_path(),
        "-nostdin",
        "-ss", str(start_sec),
        "-t", "5",
        "-i", str(audio_path),
        "-af", "volumedetect",
        "-f", "null",
        "-"
    ]
    p_res = subprocess.run(
        probe_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        **get_silent_kwargs()
    )
    for line in (p_res.stderr or "").splitlines():
        if "mean_volume:" in line:
            try:
                return float(line.split("mean_volume:")[1].split("dB")[0].strip())
            except Exception:
                pass
    return -50.0


def separate_vocals_and_bgm(
    input_audio_path: str,
    output_dir: Optional[str] = None
) -> Tuple[str, str]:
    """
    Separate input audio into:
    1. bgm_audio_path: Background Music & Sound Effects track with vocals suppressed while preserving musical warmth.
    2. vocals_audio_path: Isolated Dialogue vocal track.
    Returns (bgm_audio_path, vocals_audio_path).
    """
    in_p = Path(input_audio_path)
    if not in_p.exists():
        raise FileNotFoundError(f"Input audio not found: {input_audio_path}")

    target_dir = Path(output_dir) if output_dir else CACHE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    bgm_output = target_dir / f"{in_p.stem}_bgm.wav"
    vocals_output = target_dir / f"{in_p.stem}_vocals.wav"

    # Stereo Mid-Side vocal cancellation with surgical formant attenuation and warmth retention:
    # Preserves sub-bass (<250Hz) and high air/SFX (>4.5kHz) while suppressing center dialogue cleanly
    stereo_phase_filter = (
        "stereotools=mlev=0.0:slev=1.35,"
        "highpass=f=35,lowpass=f=16000,"
        "equalizer=f=1050:t=q:w=1.8:g=-14,"
        "equalizer=f=2200:t=q:w=1.8:g=-14,"
        "equalizer=f=3400:t=q:w=2.0:g=-10,"
        "volume=1.6"
    )

    # Dual-mono fallback filter (when L == R so Mid-Side subtraction yields silence):
    # Targets core speech intelligibility (450Hz-3.2kHz) while retaining music bass and highs
    mono_speech_notch_filter = (
        "highpass=f=40,lowpass=f=16000,"
        "equalizer=f=450:t=q:w=1.6:g=-18,"
        "equalizer=f=1050:t=q:w=1.8:g=-26,"
        "equalizer=f=2100:t=q:w=1.8:g=-26,"
        "equalizer=f=3200:t=q:w=1.8:g=-18"
    )

    cmd_bgm = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-threads", str(min(4, max(1, (os.cpu_count() or 2) - 1))),
        "-i", str(in_p),
        "-af", stereo_phase_filter,
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        str(bgm_output)
    ]
    proc_bgm = subprocess.run(cmd_bgm, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=3600, **get_silent_kwargs())

    # 2. Check if phase cancellation produced silence (common on dual-mono audio where L == R)
    need_fallback = False
    if proc_bgm.returncode != 0 or not bgm_output.exists() or bgm_output.stat().st_size < 1000:
        need_fallback = True
    else:
        try:
            # Dual-window probe to avoid false fallbacks on quiet drama intros
            m_db = _probe_mean_volume_db(bgm_output, 12)
            if m_db < -60.0:
                m_db2 = _probe_mean_volume_db(bgm_output, 28)
                if m_db2 < -60.0:
                    print(f"Notice: Phase cancellation resulted in mono silence (mean_volume={m_db:.1f}dB, {m_db2:.1f}dB), switching to surgical speech notch filter.")
                    need_fallback = True
        except Exception:
            pass

    if need_fallback:
        cmd_bgm_fallback = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-threads", str(min(4, max(1, (os.cpu_count() or 2) - 1))),
            "-i", str(in_p),
            "-af", mono_speech_notch_filter,
            "-acodec", "pcm_s16le",
            "-ar", "44100",
            "-ac", "2",
            str(bgm_output)
        ]
        proc_fb = subprocess.run(cmd_bgm_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=3600, **get_silent_kwargs())
        if proc_fb.returncode != 0 or not bgm_output.exists():
            shutil.copy2(str(in_p), str(bgm_output))

    # Vocal isolation filter: Extract center channel dialogue and suppress stereo BGM
    vocal_filter = (
        "pan=1c|c0=0.5*c0+0.5*c1,"
        "highpass=f=80,lowpass=f=4500,"
        "equalizer=f=1200:t=q:w=1.5:g=3,"
        "equalizer=f=2500:t=q:w=1.5:g=2"
    )
    cmd_voc = [
        get_ffmpeg_path(),
        "-nostdin",
        "-y",
        "-threads", str(min(4, max(1, (os.cpu_count() or 2) - 1))),
        "-i", str(in_p),
        "-af", vocal_filter,
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(vocals_output)
    ]
    proc_voc = subprocess.run(cmd_voc, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600, **get_silent_kwargs())
    if proc_voc.returncode != 0 or not vocals_output.exists() or vocals_output.stat().st_size < 1000:
        cmd_fallback = [
            get_ffmpeg_path(),
            "-nostdin",
            "-y",
            "-threads", str(min(4, max(1, (os.cpu_count() or 2) - 1))),
            "-i", str(in_p),
            "-af", "highpass=f=80,lowpass=f=4500",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            str(vocals_output)
        ]
        subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3600, **get_silent_kwargs())

    return str(bgm_output), str(vocals_output)
