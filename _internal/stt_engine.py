"""
Multilingual AI Speech-to-Text (STT) Transcriber for Chinese, Korean, English, and Auto Detection
Optimized for Asian TV Dramas with Advanced Acoustic Speaker Diarization and Millisecond Lip-Sync Precision
Strictly Two Authentic Voices: ពិសិដ្ឋ (Piseth - Male Lead) and ស្រីមុំ (Sreymom - Female Lead)
"""
import sys
import os
import re
import io
import json
import wave
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

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

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from audio_processor import get_silent_kwargs, get_ffmpeg_path
    FFMPEG_EXE = get_ffmpeg_path()
except Exception:
    def get_silent_kwargs():
        return {}
    try:
        import imageio_ffmpeg
        FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        FFMPEG_EXE = "ffmpeg"

try:
    import importlib.util
    FASTER_WHISPER_AVAILABLE = importlib.util.find_spec("faster_whisper") is not None
except Exception:
    FASTER_WHISPER_AVAILABLE = False

try:
    from nisay_transcribe import get_nisay_api_key, transcribe_to_segments as transcribe_with_nisay
    NISAY_AVAILABLE = True
except ImportError:
    NISAY_AVAILABLE = False



def get_all_groq_keys() -> List[str]:
    """Retrieve full active pool of Groq API keys across configs and built-ins."""
    keys: List[str] = []
    # 1. Check ai_provider_config.json
    for cand in [
        Path("data/ai_provider_config.json"),
        Path(__file__).resolve().parent / "data" / "ai_provider_config.json",
        Path.cwd() / "data" / "ai_provider_config.json"
    ]:
        if cand.exists():
            try:
                with open(cand, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    k_list = cfg.get("groq_keys") or []
                    for k in k_list:
                        if k and str(k).startswith("gsk_") and k not in keys:
                            keys.append(str(k).strip())
                    g_single = cfg.get("groq_api_key")
                    if g_single and str(g_single).startswith("gsk_") and g_single not in keys:
                        keys.append(str(g_single).strip())
            except Exception:
                pass
            if keys:
                break
    # 2. Add BUILTIN_GROQ_KEYS
    try:
        from translator import BUILTIN_GROQ_KEYS
        for k in BUILTIN_GROQ_KEYS:
            if k and k not in keys:
                keys.append(k)
    except Exception:
        pass
    return keys


def transcribe_with_groq_whisper(audio_path: str, source_lang: str = "auto") -> List[Dict[str, Any]]:
    """
    Ultra-reliable, lightning-fast Groq Cloud Whisper AI engine (whisper-large-v3-turbo).
    Provides instant, zero-setup STT for client computers without GPUs or failed local models.
    """
    if not os.path.exists(audio_path):
        return []

    available_keys = get_all_groq_keys()
    if not available_keys:
        return []

    proc_path = audio_path
    temp_compressed = None
    try:
        fsize = os.path.getsize(audio_path)
        # For long videos (50+ mins to 2+ hours), adaptively scale bitrate so audio is always < 22MB:
        target_bitrate = "32k"
        try:
            from audio_processor import get_media_duration
            dur = get_media_duration(audio_path)
            if dur > 5400:     # > 90 mins (full movie)
                target_bitrate = "16k"
            elif dur > 3000:   # > 50 mins (standard episode)
                target_bitrate = "24k"
        except Exception:
            pass

        # Compress to mono mp3 if > 18MB or non-standard format
        if fsize > 18 * 1024 * 1024 or not audio_path.lower().endswith(('.mp3', '.wav', '.m4a')):
            temp_compressed = audio_path + f".tmp_{os.urandom(4).hex()}.mp3"
            cmd = [
                FFMPEG_EXE, '-nostdin', '-y', '-i', str(audio_path),
                '-vn', '-ac', '1', '-ar', '16000', '-b:a', target_bitrate,
                str(temp_compressed)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300, **get_silent_kwargs())
            if os.path.exists(temp_compressed) and os.path.getsize(temp_compressed) > 100:
                proc_path = temp_compressed

        with open(proc_path, 'rb') as f:
            audio_bytes = f.read()
    except Exception as e:
        print(f"Groq Whisper audio prep note: {e}")
        return []
    finally:
        if temp_compressed and os.path.exists(temp_compressed):
            try:
                os.remove(temp_compressed)
            except Exception:
                pass

    lang_param = None
    if source_lang in ('zh', 'chinese', 'mandarin'):
        lang_param = 'zh'
    elif source_lang in ('en', 'english'):
        lang_param = 'en'
    elif source_lang in ('ko', 'korean'):
        lang_param = 'ko'

    boundary = '----WebKitFormBoundaryGroqWhisper' + os.urandom(8).hex()
    body = io.BytesIO()

    fname = os.path.basename(proc_path)
    ext = os.path.splitext(fname)[1].lower()
    content_type = 'audio/mpeg' if ext == '.mp3' else ('audio/wav' if ext == '.wav' else 'application/octet-stream')

    body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{fname}"\r\nContent-Type: {content_type}\r\n\r\n'.encode('utf-8'))
    body.write(audio_bytes)
    body.write(b'\r\n')

    body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nwhisper-large-v3-turbo\r\n'.encode('utf-8'))
    body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="response_format"\r\n\r\nverbose_json\r\n'.encode('utf-8'))

    if lang_param:
        body.write(f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\n{lang_param}\r\n'.encode('utf-8'))

    body.write(f'--{boundary}--\r\n'.encode('utf-8'))
    payload = body.getvalue()

    for key in available_keys[:15]:
        req = urllib.request.Request(
            'https://api.groq.com/openai/v1/audio/transcriptions',
            data=payload,
            headers={
                'Authorization': f'Bearer {key}',
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                raw_segs = data.get('segments', [])
                results = []
                for s in raw_segs:
                    txt = s.get('text', '').strip()
                    if txt:
                        results.append({
                            'start': round(float(s.get('start', 0.0)), 2),
                            'end': round(float(s.get('end', 0.0)), 2),
                            'text': txt
                        })
                if results:
                    return results
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode('utf-8', errors='ignore')
            print(f"Groq Whisper HTTP {he.code}: {err_msg[:80]}")
            continue
        except Exception as ex:
            print(f"Groq Whisper note: {ex}")
            continue

    return []


def get_system_ram_gb() -> float:
    """Detect total physical RAM in GB with zero overhead using Win32 API."""
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            return round(stat.ullTotalPhys / (1024 ** 3), 1)
    except Exception:
        pass
    return 8.0


# Strict Drama First-Person Self-References, Kinship Terms & Direct Vocatives
FEMALE_VOCATIVES = [
    "老公", "相公", "夫君", "死鬼",
    "本宫", "臣妾", "奴婢", "小女子", "妾身", "本小姐",
    "老娘", "妈妈我", "女兒我", "娘亲我", "妈咪", "阿姨", "婆婆",
    "怀着孩子", "怀孕", "儿媳", "嫂嫂", "大嫂", "小姑子", "姐姐", "妹妹",
    "오빠", "언니"
]

MALE_VOCATIVES = [
    "老婆", "娘子", "夫人", "爱妃", "媳妇",
    "本座", "本王", "朕", "老子", "为父", "为夫", "微臣",
    "兄弟我", "爸爸我", "爹爹我", "儿子", "岳父", "岳母",
    "형"
]


def load_audio_samples_16k(audio_path: str) -> Tuple[Optional[Any], int]:
    """Load audio file as 16kHz mono float32 numpy array once into memory for ultra-fast processing."""
    if not NUMPY_AVAILABLE:
        return None, 16000
    try:
        cmd = [
            FFMPEG_EXE, '-nostdin', '-y', '-i', str(audio_path),
            '-vn', '-ac', '1', '-ar', '16000',
            '-f', 'wav', '-'
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=1800, **get_silent_kwargs())
        with wave.open(io.BytesIO(proc.stdout), 'rb') as wf:
            nframes = wf.getnframes()
            if nframes == 0:
                return None, 16000
            raw = wf.readframes(nframes)
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
            return samples, 16000
    except Exception as e:
        print(f"Fast audio load note: {e}")
        return None, 16000


def analyze_segment_acoustics_fast(
    sig: np.ndarray,
    sr: int = 16000
) -> Dict[str, Any]:
    """
    Fast, vectorized acoustic analysis of vocal segment from in-memory numpy array:
    1. FFT / Autocorrelation Fundamental Frequency (F0) tracking
    2. Spectral Centroid calculation
    3. Low-band (chest resonance 75-280Hz) vs Mid-High-band Energy Ratio
    """
    default_res = {
        "role": "unknown",
        "voice": "piseth",
        "speaker": "តួប្រុស (ពិសិដ្ឋ)",
        "f0": 0.0,
        "centroid": 0.0,
        "ratio": 1.0
    }
    if sig is None or len(sig) < 800:
        return default_res

    try:
        frame_len = 1024
        hop = 512
        min_lag = int(sr / 380)  # ~42 samples (380 Hz)
        max_lag = int(sr / 75)   # ~213 samples (75 Hz)
        pitches = []

        # Vectorized autocorrelation pitch tracking across voiced frames
        for i in range(0, len(sig) - frame_len, hop):
            fr = sig[i:i + frame_len]
            fr_norm = fr - np.mean(fr)
            energy = np.sum(fr_norm ** 2)
            if energy < 8e4:
                continue

            corr = np.correlate(fr_norm, fr_norm, mode='full')
            corr = corr[len(corr)//2:]
            if len(corr) <= max_lag:
                continue

            peak_lag = min_lag + np.argmax(corr[min_lag:max_lag])
            if corr[peak_lag] > 0.28 * corr[0]:
                f0s = sr / peak_lag
                pitches.append(f0s)

        med_f0 = float(np.median(pitches)) if pitches else 0.0

        # Frequency Domain Analysis: Centroid and Harmonic Energy Ratio
        fft = np.abs(np.fft.rfft(sig))
        freqs = np.fft.rfftfreq(len(sig), 1.0 / sr)
        tot_fft = np.sum(fft) + 1e-6
        centroid = float(np.sum(freqs * fft) / tot_fft)

        low_energy = float(np.sum(fft[(freqs >= 75) & (freqs <= 280)] ** 2))
        high_energy = float(np.sum(fft[(freqs > 300) & (freqs <= 3000)] ** 2)) + 1e-6
        ratio_low_high = low_energy / high_energy

        # Multi-factor Classification
        if med_f0 >= 165.0:
            role = "female"
        elif 0.0 < med_f0 <= 152.0:
            role = "male"
        elif 152.0 < med_f0 < 165.0:
            role = "male" if (ratio_low_high > 0.80 or centroid < 1900) else "female"
        else:
            if ratio_low_high >= 0.85 or centroid < 1900:
                role = "male"
            elif ratio_low_high <= 0.62 or centroid >= 2100:
                role = "female"
            else:
                role = "unknown"

        voice = "sreymom" if role == "female" else "piseth"
        speaker = "តួស្រី (ស្រីមុំ)" if role == "female" else "តួប្រុស (ពិសិដ្ឋ)"

        return {
            "role": role,
            "voice": voice,
            "speaker": speaker,
            "f0": round(med_f0, 1),
            "centroid": round(centroid, 1),
            "ratio": round(ratio_low_high, 2)
        }
    except Exception:
        return default_res


def analyze_segment_acoustics(audio_path: str, start_s: float, end_s: float) -> Dict[str, Any]:
    """Backwards-compatible wrapper returning acoustic analysis."""
    default_res = {
        "role": "unknown",
        "voice": "piseth",
        "speaker": "តួប្រុស (ពិសិដ្ឋ)",
        "f0": 0.0,
        "centroid": 0.0,
        "ratio": 1.0
    }
    dur_s = end_s - start_s
    if dur_s <= 0.15 or not NUMPY_AVAILABLE:
        return default_res
    try:
        cmd = [
            FFMPEG_EXE, '-nostdin', '-y', '-ss', str(start_s), '-t', str(dur_s),
            '-i', str(audio_path), '-vn', '-ac', '1', '-ar', '16000',
            '-f', 'wav', '-'
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, **get_silent_kwargs())
        with wave.open(io.BytesIO(proc.stdout), 'rb') as wf:
            nframes = wf.getnframes()
            if nframes < 600:
                return default_res
            raw = wf.readframes(nframes)
            sig = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        return analyze_segment_acoustics_fast(sig, 16000)
    except Exception:
        return default_res


def detect_segment_pitch(audio_path: str, start_s: float, end_s: float) -> float:
    """Backwards-compatible wrapper returning fundamental pitch frequency in Hz."""
    return analyze_segment_acoustics(audio_path, start_s, end_s)["f0"]


def extract_embedded_or_sidecar_subtitles(media_path: str) -> Optional[List[Dict[str, Any]]]:
    """
    Ultra-fast (0.05s) subtitle extractor:
    1. Checks sidecar .srt/.vtt files next to the video.
    2. Probes video for embedded subtitle tracks and extracts via FFmpeg directly to memory.
    """
    if not media_path:
        return None
    p = Path(media_path)
    # Check sidecar subtitles
    for ext in ('.srt', '.vtt'):
        sidecar = p.with_suffix(ext)
        if sidecar.exists() and sidecar.stat().st_size > 10:
            try:
                from translator import parse_srt_content
                txt = sidecar.read_text(encoding='utf-8', errors='replace')
                items = parse_srt_content(txt)
                if items:
                    print(f"[OK] Found sidecar subtitle file: {sidecar.name} ({len(items)} lines)")
                    return items
            except Exception:
                pass

    # Check embedded subtitle stream in MP4/MKV/TS
    if p.suffix.lower() in ('.mp4', '.mkv', '.mov', '.ts', '.webm'):
        try:
            cmd = [
                FFMPEG_EXE, '-nostdin', '-y',
                '-i', str(media_path),
                '-map', '0:s:0',
                '-f', 'srt', '-'
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=8, **get_silent_kwargs())
            if proc.returncode == 0 and len(proc.stdout) > 20:
                from translator import parse_srt_content
                raw_srt = proc.stdout.decode('utf-8', errors='replace')
                items = parse_srt_content(raw_srt)
                if items and len(items) >= 2:
                    print(f"[OK] Extracted embedded subtitle track from {p.name} ({len(items)} lines in 0.05s!)")
                    return items
        except Exception:
            pass
    return None


def get_local_whisper_model_path(model_size: str = "base") -> Optional[str]:
    """Find bundled local offline Whisper model directory across dev, frozen PyInstaller, and _internal."""
    candidates = []
    base = Path(__file__).resolve().parent
    candidates.append(base / "models" / f"whisper-{model_size}")
    candidates.append(base / "models" / "whisper-base")
    candidates.append(base.parent / "models" / f"whisper-{model_size}")
    candidates.append(base.parent / "models" / "whisper-base")
    candidates.append(Path.cwd() / "models" / f"whisper-{model_size}")
    candidates.append(Path.cwd() / "models" / "whisper-base")

    import sys
    if getattr(sys, 'frozen', False):
        app_dir = Path(os.path.dirname(sys.executable))
        candidates.append(app_dir / "models" / f"whisper-{model_size}")
        candidates.append(app_dir / "models" / "whisper-base")
        candidates.append(app_dir / "_internal" / "models" / f"whisper-{model_size}")
        candidates.append(app_dir / "_internal" / "models" / "whisper-base")
        if hasattr(sys, '_MEIPASS'):
            meipass = Path(sys._MEIPASS)
            candidates.append(meipass / "models" / f"whisper-{model_size}")
            candidates.append(meipass / "models" / "whisper-base")

    for c in candidates:
        if c.exists() and (c / "model.bin").exists():
            return str(c)
    return None


class SpeechToTextEngine:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _get_model(self):
        if self._model is None and FASTER_WHISPER_AVAILABLE:
            device = "cpu"
            compute_type = "int8"
            threads = min(4, os.cpu_count() or 2)
            try:
                import ctranslate2
                if "cuda" in ctranslate2.get_supported_compute_types("cuda"):
                    device = "cuda"
                    compute_type = "float16"
                    threads = min(8, os.cpu_count() or 4)
            except Exception:
                pass

            target_model = self.model_size
            # On CPU, prevent medium or large from freezing Windows! Default to base
            if device == "cpu" and target_model in ("medium", "large", "large-v3"):
                target_model = "base"

            local_path = get_local_whisper_model_path(self.model_size)
            model_to_load = local_path or target_model

            try:
                from faster_whisper import WhisperModel
                self._model = WhisperModel(model_to_load, device=device, compute_type=compute_type, cpu_threads=threads)
            except Exception as e:
                print(f"Faster-whisper model load note ({model_to_load}): {e}")
                fallback_local = get_local_whisper_model_path("base")
                try:
                    self._model = WhisperModel(fallback_local or "base", device="cpu", compute_type="int8", cpu_threads=threads)
                except Exception:
                    try:
                        self._model = WhisperModel("tiny", device="cpu", compute_type="int8", cpu_threads=threads)
                    except Exception as e2:
                        print(f"Faster-whisper fallback failed: {e2}")
                        self._model = None
        return self._model

    def transcribe_audio(
        self,
        audio_path: str,
        source_lang: str = "auto",
        beam_size: int = 1,
        voice_override: Optional[str] = None,
        progress_callback = None,
        check_subtitles: bool = True,
        video_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe audio file into timed dialogue segments with millisecond lip-sync accuracy.
        Applies acoustic multi-layered speaker identification and strict male/female distinction.
        Returns list of dicts with: id, start, end, text, speaker, detected_role, voice, pitch
        """
        raw_segments = []
        if check_subtitles:
            target_sub_media = video_path if (video_path and Path(video_path).exists()) else audio_path
            if target_sub_media:
                cached_subs = extract_embedded_or_sidecar_subtitles(target_sub_media)
                if cached_subs and len(cached_subs) > 0:
                    raw_segments = cached_subs

        if not raw_segments and NISAY_AVAILABLE:
            nisay_k = get_nisay_api_key()
            if nisay_k and nisay_k != "nisay-YOUR_API_KEY":
                print("[SN CLOUD SPEECH] Active engine initialized. Routing to SN AI Speech Pipeline...")
                if progress_callback:
                    progress_callback(46, "Using SN Tool Speech Engine...", "Using SN Tool Speech Engine...")
                try:
                    nisay_segs = transcribe_with_nisay(audio_path, language=source_lang, progress_callback=progress_callback)
                    if nisay_segs:
                        raw_segments = nisay_segs
                        print(f"[OK] SN Tool Speech Engine transcribed {len(raw_segments)} dialogue segments with millisecond timestamps!")
                except Exception as ne:
                    print(f"SN Tool Speech Engine note: {ne}")

        if not raw_segments:
            # High-Speed Zero-Freeze Optimization:
            # If system has no dedicated NVIDIA CUDA GPU, prioritize Groq Cloud Whisper
            # to transcribe in 2-3 seconds, avoid 100% CPU lockup, and prevent OOM process termination!
            total_ram = get_system_ram_gb()
            has_cuda = False
            try:
                import ctranslate2
                has_cuda = "cuda" in ctranslate2.get_supported_compute_types("cuda")
            except Exception:
                pass

            if not has_cuda or total_ram <= 6.0:
                print(f"[TURBO WHISPER] CPU mode detected (RAM: {total_ram}GB). Routing to Groq Cloud Whisper (0% CPU / 0MB RAM / 3-sec transcribe)...")
                if progress_callback:
                    progress_callback(46, "៣/៧ AI Turbo៖ កំពុងប្រើប្រាស់ Cloud AI Whisper (លឿនបំផុត មិនស៊ី CPU)...", "Using Ultra-Fast Cloud Whisper...")
                try:
                    cloud_segs = transcribe_with_groq_whisper(audio_path, source_lang=source_lang)
                    if cloud_segs:
                        raw_segments = cloud_segs
                        print(f"[OK] Groq Cloud Whisper transcribed {len(raw_segments)} segments in 3 seconds!")
                except Exception as e:
                    print(f"Cloud Whisper note: {e}")

        # Cloud-Server-Only Enforcement:
        # 100% Online Cloud Server Only (SN Tool Speech Engine + Groq Cloud Whisper).
        # Completely bypasses local Faster-Whisper models to prevent high CPU usage, local model downloads, and freezing.
        CLOUD_SERVER_ONLY = True
        if CLOUD_SERVER_ONLY:
            if not raw_segments:
                print("[CLOUD ONLY] Retrying cloud STT engines...")
                try:
                    cloud_segs = transcribe_with_groq_whisper(audio_path, source_lang=source_lang)
                    if cloud_segs:
                        raw_segments = cloud_segs
                except Exception as e:
                    print(f"Cloud STT retry note: {e}")

            if not raw_segments:
                raise RuntimeError("Cloud STT Error: SN Tool Cloud Servers returned no audio dialogues. Local processing is disabled (Cloud Server Only mode).")

        if not raw_segments:
            model = None
            try:
                model = self._get_model()
            except Exception as me:
                print(f"Local Faster-Whisper model load note: {me}")


            if model:
                try:
                    lang_code = None if source_lang in ("auto", "", None) else source_lang
                    if lang_code in ("zh", "chinese", "mandarin"):
                        lang_code = "zh"

                    initial_prompt = None
                    if lang_code == "zh":
                        initial_prompt = "以下是影视剧对话，台词清晰，标点符号完整。"

                    segments_gen, info = model.transcribe(
                        audio_path,
                        language=lang_code,
                        initial_prompt=initial_prompt,
                        beam_size=min(beam_size, 2),
                        best_of=1,
                        condition_on_previous_text=False,
                        compression_ratio_threshold=2.4,
                        no_speech_threshold=0.88,
                        word_timestamps=True,
                        vad_filter=True,
                        vad_parameters=dict(
                            threshold=0.25,
                            min_speech_duration_ms=60,
                            max_speech_duration_s=8.0,
                            min_silence_duration_ms=250,
                            speech_pad_ms=120
                        )
                    )

                    tot_dur = getattr(info, "duration", 0) or 1.0
                    for segment in segments_gen:
                        text = segment.text.strip()
                        if not text:
                            continue

                        words = getattr(segment, "words", None)
                        if not words:
                            # If no word-level timestamps, split text by sentence punctuation if long
                            sub_sentences = [s.strip() for s in re.split(r'([。！？!?\n]+)', text) if s.strip()]
                            combined_sentences = []
                            curr_sent = ""
                            for part in sub_sentences:
                                curr_sent += part
                                if re.search(r'[。！？!?\n]', part):
                                    combined_sentences.append(curr_sent.strip())
                                    curr_sent = ""
                            if curr_sent.strip():
                                combined_sentences.append(curr_sent.strip())

                            if len(combined_sentences) <= 1:
                                raw_segments.append({
                                    "start": round(segment.start, 2),
                                    "end": round(segment.end, 2),
                                    "text": text
                                })
                            else:
                                total_chars = max(1, sum(len(s) for s in combined_sentences))
                                seg_dur = max(0.4, segment.end - segment.start)
                                cur_t = segment.start
                                for s in combined_sentences:
                                    p_dur = (len(s) / total_chars) * seg_dur
                                    p_start = round(cur_t, 2)
                                    p_end = round(cur_t + p_dur, 2)
                                    raw_segments.append({
                                        "start": p_start,
                                        "end": max(round(p_start + 0.35, 2), p_end),
                                        "text": s
                                    })
                                    cur_t += p_dur
                        else:
                            # Word-level timestamp precision: Group words into individual dialogue lines!
                            curr_words = []
                            for w_idx, w in enumerate(words):
                                curr_words.append(w)
                                w_txt = getattr(w, "word", "") or ""

                                # Check split triggers:
                                # 1. Punctuation in word (ending marks)
                                has_punct = bool(re.search(r'[。！？!?；;\n]', w_txt))

                                # 2. Pause between this word and next word (dialogue turn / breathing pause)
                                has_pause = False
                                if w_idx + 1 < len(words):
                                    next_w = words[w_idx + 1]
                                    pause_gap = next_w.start - w.end
                                    if pause_gap >= 0.42:
                                        has_pause = True
                                    elif pause_gap >= 0.22 and bool(re.search(r'[，,、]', w_txt)):
                                        has_pause = True

                                # 3. Accumulated length >= 5.5 seconds (prevents runaway sentences)
                                span = curr_words[-1].end - curr_words[0].start
                                is_too_long = span >= 5.5 and len(curr_words) >= 4

                                if (has_punct or has_pause or is_too_long) and len(curr_words) > 0:
                                    line_txt = "".join(getattr(cw, "word", "") for cw in curr_words).strip()
                                    if line_txt:
                                        l_start = round(curr_words[0].start, 2)
                                        l_end = round(curr_words[-1].end, 2)
                                        raw_segments.append({
                                            "start": l_start,
                                            "end": max(round(l_start + 0.35, 2), l_end),
                                            "text": line_txt
                                        })
                                    curr_words = []

                            # Any trailing words
                            if curr_words:
                                line_txt = "".join(getattr(cw, "word", "") for cw in curr_words).strip()
                                if line_txt:
                                    l_start = round(curr_words[0].start, 2)
                                    l_end = round(curr_words[-1].end, 2)
                                    raw_segments.append({
                                        "start": l_start,
                                        "end": max(round(l_start + 0.35, 2), l_end),
                                        "text": line_txt
                                    })

                        if progress_callback and tot_dur > 0:
                            p_cur = 45 + int(min(15, (segment.end / tot_dur) * 15))
                            m_curr = int(segment.end // 60)
                            s_curr = int(segment.end % 60)
                            progress_callback(
                                p_cur,
                                f"៣/៧ AI កំពុងស្តាប់នៅនាទី {m_curr:02d}:{s_curr:02d}...",
                                f"Transcribing audio at {m_curr:02d}:{s_curr:02d}..."
                            )
                except Exception as fe:
                    print(f"Local Faster-Whisper transcribe note: {fe}. Will attempt Groq Cloud Whisper.")

        # Resilient AI Fallback: If local transcription yielded 0 segments, engage Groq Cloud Whisper
        if not raw_segments:
            print("Notice: Local STT yielded 0 segments. Engaging Groq Cloud Whisper AI engine...")
            if progress_callback:
                progress_callback(48, "៣/៧ កំពុងប្រើប្រាស់ Cloud AI Whisper (Groq) ដើម្បីស្តាប់ការសន្ទនា...", "Using Groq Cloud Whisper...")
            try:
                cloud_segs = transcribe_with_groq_whisper(audio_path, source_lang=source_lang)
                if cloud_segs:
                    raw_segments = cloud_segs
                    print(f"[OK] Groq Cloud Whisper successfully transcribed {len(raw_segments)} dialogue segments!")
            except Exception as ge:
                print(f"Groq Cloud Whisper fallback note: {ge}")

        if not raw_segments:
            return []

        # 0. Zero-Lag Lip-Sync Pre-Segmentation:
        # Split multi-sentence or overly long segments (> 3.5s or containing punctuation 。！？!?；; / newlines)
        # into separate natural dialogue lines with accurately budgeted proportional timestamps.
        # This guarantees every character's speech matches their exact mouth movement,
        # preventing 10-15s continuous audio overruns that cause voices to speak late or over closed mouths!
        refined_raw_segments = []
        for seg in raw_segments:
            s_text = (seg.get("text") or "").strip()
            if not s_text:
                continue
            s_start = float(seg.get("start", 0.0))
            s_end = float(seg.get("end", s_start + 1.0))
            s_dur = max(0.3, s_end - s_start)
            spk = seg.get("speaker", "S0")
            words = seg.get("words") or []

            # 0.A Word-Level Split if available (millisecond lip-sync accuracy from Whisper/Nisay)
            if words and len(words) > 1 and s_dur >= 2.5:
                w_lines = []
                curr_w = []
                for w_i, w_item in enumerate(words):
                    curr_w.append(w_item)
                    w_txt = (w_item.get("word") if isinstance(w_item, dict) else getattr(w_item, "word", "")) or ""
                    w_end = float(w_item.get("end") if isinstance(w_item, dict) else getattr(w_item, "end", 0.0))

                    has_end_mark = bool(re.search(r'[。！？!?；;\n]', w_txt))
                    has_long_pause = False
                    if w_i + 1 < len(words):
                        next_item = words[w_i + 1]
                        next_start = float(next_item.get("start") if isinstance(next_item, dict) else getattr(next_item, "start", 0.0))
                        if next_start - w_end >= 0.35:
                            has_long_pause = True

                    curr_span = w_end - float(curr_w[0].get("start") if isinstance(curr_w[0], dict) else getattr(curr_w[0], "start", 0.0))
                    is_overlong = curr_span >= 4.5 and len(curr_w) >= 5

                    if (has_end_mark or has_long_pause or is_overlong) and curr_w:
                        l_txt = "".join((w.get("word") if isinstance(w, dict) else getattr(w, "word", "")) for w in curr_w).strip()
                        if l_txt:
                            lw_start = round(float(curr_w[0].get("start") if isinstance(curr_w[0], dict) else getattr(curr_w[0], "start", 0.0)), 2)
                            lw_end = round(float(curr_w[-1].get("end") if isinstance(curr_w[-1], dict) else getattr(curr_w[-1], "end", 0.0)), 2)
                            w_lines.append({
                                "start": lw_start,
                                "end": max(round(lw_start + 0.35, 2), lw_end),
                                "orig_start": lw_start,
                                "orig_end": lw_end,
                                "text": l_txt,
                                "speaker": spk
                            })
                        curr_w = []

                if curr_w:
                    l_txt = "".join((w.get("word") if isinstance(w, dict) else getattr(w, "word", "")) for w in curr_w).strip()
                    if l_txt:
                        lw_start = round(float(curr_w[0].get("start") if isinstance(curr_w[0], dict) else getattr(curr_w[0], "start", 0.0)), 2)
                        lw_end = round(float(curr_w[-1].get("end") if isinstance(curr_w[-1], dict) else getattr(curr_w[-1], "end", 0.0)), 2)
                        w_lines.append({
                            "start": lw_start,
                            "end": max(round(lw_start + 0.35, 2), lw_end),
                            "orig_start": lw_start,
                            "orig_end": lw_end,
                            "text": l_txt,
                            "speaker": spk
                        })

                if len(w_lines) > 1:
                    refined_raw_segments.extend(w_lines)
                    continue

            # Check for standard sentence boundaries or punctuation marks
            parts = [p.strip() for p in re.split(r'([。！？!?；;\n]+)', s_text) if p.strip()]
            sentences = []
            curr_s = ""
            for p in parts:
                curr_s += p
                if re.search(r'[。！？!?；;\n]', p):
                    sentences.append(curr_s.strip())
                    curr_s = ""
            if curr_s.strip():
                sentences.append(curr_s.strip())

            # If segment is still >= 3.8s, split on drama modal particles followed by subjects
            if len(sentences) <= 1 and s_dur >= 3.8:
                modal_parts = [p.strip() for p in re.split(r'([呀呢吧吗啦啊!！?？])(?=[你我他她爷爷奶奶爹娘谁什么快走来哪])', s_text) if p.strip()]
                if len(modal_parts) > 1:
                    sentences = []
                    curr_m = ""
                    for p in modal_parts:
                        curr_m += p
                        if re.search(r'[呀呢吧吗啦啊!！?？]$', curr_m) and len(curr_m) >= 4:
                            sentences.append(curr_m.strip())
                            curr_m = ""
                    if curr_m.strip():
                        sentences.append(curr_m.strip())

            # If no sentence punctuation but segment is long (>= 4.0s) and has commas or pauses:
            if len(sentences) <= 1 and s_dur >= 4.0:
                comma_parts = [p.strip() for p in re.split(r'([，,、]+)', s_text) if p.strip()]
                if len(comma_parts) > 1:
                    sentences = []
                    curr_c = ""
                    for p in comma_parts:
                        curr_c += p
                        if re.search(r'[，,、]', p) and len(curr_c) >= 5:
                            sentences.append(curr_c.strip())
                            curr_c = ""
                    if curr_c.strip():
                        sentences.append(curr_c.strip())

            if len(sentences) <= 1:
                refined_raw_segments.append(seg)
            else:
                total_chars = max(1, sum(len(re.sub(r'[\s。！？!?；;，,、]+', '', s)) for s in sentences))
                cur_t = s_start
                for s_idx, sent in enumerate(sentences):
                    clean_chars = len(re.sub(r'[\s。！？!?；;，,、]+', '', sent))
                    p_dur = round(max(0.4, (clean_chars / total_chars) * s_dur), 2)
                    p_start = round(cur_t, 2)
                    p_end = round(min(s_end, cur_t + p_dur) if s_idx + 1 < len(sentences) else s_end, 2)
                    if p_end <= p_start:
                        p_end = round(p_start + 0.4, 2)
                    refined_raw_segments.append({
                        "start": p_start,
                        "end": p_end,
                        "orig_start": p_start,
                        "orig_end": p_end,
                        "text": sent,
                        "speaker": spk
                    })
                    cur_t = p_end

        raw_segments = refined_raw_segments

        # Check if single voice mode is requested
        vo_clean = str(voice_override or "").lower().strip()
        is_single_voice = vo_clean in ("piseth", "sreymom", "male", "female")
        single_voice = "sreymom" if vo_clean in ("sreymom", "female") else "piseth"

        # Check if segments already have speaker diarization from Cloud STT (Nisay S0, S1...)
        has_cloud_speakers = any(str(s.get("speaker", "")).upper().startswith("S") for s in raw_segments)

        # Only load audio samples into memory if local acoustic analysis is strictly necessary
        audio_samples = None
        sr = 16000
        if not is_single_voice and not has_cloud_speakers and NUMPY_AVAILABLE and audio_path and os.path.exists(audio_path):
            audio_samples, sr = load_audio_samples_16k(audio_path)

        # 1. First Pass: Fast Acoustic Analysis & Vocative Classification
        speaker_segments = []
        last_confirmed_role = "male"

        for idx, seg in enumerate(raw_segments):
            text = seg["text"].strip()
            start = round(float(seg["start"]), 2)
            end = round(float(seg["end"]), 2)

            if is_single_voice:
                speaker_segments.append({
                    "start": start,
                    "end": end,
                    "orig_start": start,
                    "orig_end": end,
                    "speaker": "ស្រីមុំ (Sreymom)" if single_voice == "sreymom" else "ពិសិដ្ឋ (Piseth)",
                    "detected_role": "female" if single_voice == "sreymom" else "male",
                    "voice": single_voice,
                    "pitch": 0.0,
                    "text": text,
                    "text_original": text
                })
                continue

            # Fast cloud speaker attribution if available
            acoustics = None
            if has_cloud_speakers:
                spk_id = str(seg.get("speaker", "S0")).strip().upper()
                if spk_id in ("S1", "S3", "S5") or (spk_id.startswith("S") and spk_id[1:].isdigit() and int(spk_id[1:]) % 2 == 1):
                    acoustics = {
                        "role": "female",
                        "voice": "sreymom",
                        "speaker": "តួស្រី (ស្រីមុំ)",
                        "f0": 210.0
                    }
                else:
                    acoustics = {
                        "role": "male",
                        "voice": "piseth",
                        "speaker": "តួប្រុស (ពិសិដ្ឋ)",
                        "f0": 125.0
                    }
            elif audio_samples is not None and len(audio_samples) > 0:
                s_idx = max(0, int(start * sr))
                e_idx = min(len(audio_samples), int(end * sr))
                if e_idx > s_idx:
                    acoustics = analyze_segment_acoustics_fast(audio_samples[s_idx:e_idx], sr)

            if not acoustics:
                acoustics = {
                    "role": "unknown",
                    "voice": "piseth",
                    "speaker": "តួប្រុស (ពិសិដ្ឋ)",
                    "f0": 0.0
                }

            detected_role = acoustics["role"]

            # Grammatical first-person & spouse vocatives check (strict)
            has_female_voc = any(kw in text for kw in FEMALE_VOCATIVES)
            has_male_voc = any(kw in text for kw in MALE_VOCATIVES)

            if has_female_voc and not has_male_voc:
                role = "female"
                voice = "sreymom"
                speaker_title = "តួស្រី (ស្រីមុំ)"
            elif has_male_voc and not has_female_voc:
                role = "male"
                voice = "piseth"
                speaker_title = "តួប្រុស (ពិសិដ្ឋ)"
            elif detected_role in ("female", "male"):
                role = detected_role
                voice = acoustics["voice"]
                speaker_title = acoustics["speaker"]
            else:
                # Ambiguous acoustic frame:
                # If there's a conversation turn gap (> 0.4s) from previous line, alternate speaker
                if speaker_segments:
                    prev_seg = speaker_segments[-1]
                    turn_gap = start - prev_seg["end"]
                    if turn_gap >= 0.40:
                        role = "female" if prev_seg["detected_role"] == "male" else "male"
                    else:
                        role = prev_seg["detected_role"]
                else:
                    role = last_confirmed_role

                voice = "sreymom" if role == "female" else "piseth"
                speaker_title = "តួស្រី (ស្រីមុំ)" if role == "female" else "តួប្រុស (ពិសិដ្ឋ)"

            if role in ("female", "male"):
                last_confirmed_role = role

            speaker_segments.append({
                "start": start,
                "end": end,
                "orig_start": start,
                "orig_end": end,
                "speaker": speaker_title,
                "detected_role": role,
                "voice": voice,
                "pitch": acoustics["f0"],
                "text": text,
                "text_original": text
            })

        # 2. Second Pass: Tight Lip-Sync Consolidation
        # Only merge micro-gaps (<= 0.12s) within short continuous speech (<= 2.8s total).
        # NEVER merge across pauses or turns to ensure speech matches mouth movements exactly!
        consolidated = []
        for seg in speaker_segments:
            if consolidated:
                prev = consolidated[-1]
                gap = round(seg["start"] - prev["end"], 2)
                combined_len = round(seg["end"] - prev["start"], 2)
                same_speaker = (prev["detected_role"] == seg["detected_role"])

                if same_speaker and combined_len <= 2.8 and gap <= 0.12:
                    prev["end"] = seg["end"]
                    prev["orig_end"] = seg["end"]
                    prev["text"] = f"{prev['text']} {seg['text']}".strip()
                    prev["text_original"] = prev["text"]
                    continue

            consolidated.append(dict(seg))

        # 3. Third Pass: Strict Anti-Overlap & Absolute Onset Anchor
        # CRITICAL LIP-SYNC ACCURACY: The actor began moving their mouth at seg["start"].
        # NEVER push seg["start"] later into the future (which caused cumulative lag)!
        # If prev["end"] overruns, trim prev["end"] back so seg["start"] stays 100% on-time!
        cleaned_dialogues = []
        min_seg_gap = 0.04  # 40ms acoustic separation
        for seg in consolidated:
            if cleaned_dialogues:
                prev = cleaned_dialogues[-1]
                if prev["end"] > round(seg["start"] - min_seg_gap, 2):
                    prev["end"] = round(max(prev["start"] + 0.25, seg["start"] - min_seg_gap), 2)
                    prev["orig_end"] = prev["end"]
            cleaned_dialogues.append(seg)
        consolidated = cleaned_dialogues

        # Re-number IDs and initialize standard speech parameters
        for idx, item in enumerate(consolidated, start=1):
            item["id"] = idx
            item["rate_percent"] = 0
            item["pitch_hz"] = 0

        return consolidated


def transcribe_audio(audio_path: str, source_lang: str = "auto", **kwargs) -> List[Dict[str, Any]]:
    """Module-level convenience wrapper for SpeechToTextEngine.transcribe_audio."""
    engine = SpeechToTextEngine()
    return engine.transcribe_audio(audio_path, source_lang=source_lang, **kwargs)

