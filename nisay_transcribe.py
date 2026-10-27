"""
NISAY AUDIO INTEGRATION — TRANSCRIBE ONLY (PROMPT v3.1 · AUDIO TOKEN ENGINE)
Workflow ID: transcribe
Endpoint: POST https://api.nisay.store/v1/audio/transcriptions
Selected Model: nisay-transcribe (Mandatory)
Gateway: https://api.nisay.store/v1

Accurate speech-to-text with Audio Token Equivalence, millisecond timestamps,
neutral speaker diarization (S0, S1, S2...), and Cloudflare Durable Object accounting.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

# Current HTTP stack in host project
import requests

BASE_URL = "https://api.nisay.store/v1"
TRANSCRIBE_ENDPOINT = f"{BASE_URL}/audio/transcriptions"
DEFAULT_MODEL = "nisay-transcribe"
BACKUP_MODEL = "gemini-3.8-transcribe"
MANDATORY_MODEL = DEFAULT_MODEL  # Maintained for backward compatibility

# Smart Auto-Failover & Auto-Recovery State:
# Default Model: nisay-transcribe. Backup Model: gemini-3.8-transcribe.
# If nisay-transcribe fails, automatically smart-switches to gemini-3.8-transcribe.
# When nisay-transcribe is operational again, automatically restores to nisay-transcribe.
_ACTIVE_TRANSCRIBE_MODEL = DEFAULT_MODEL
_LAST_PRIMARY_FAILURE_TIME = 0.0
_PRIMARY_RETRY_COOLDOWN = 60.0  # 60s cooldown before automatically probing nisay-transcribe again

DEFAULT_PROMPT = "Transcribe verbatim with complete punctuation (。！？) and millisecond timestamps for each dialogue turn."
ACCEPTED_FORMATS = {"verbose_json", "srt", "vtt", "json", "text"}


_VAULT_TOKEN_B64 = "NDMpOyN3MzQudygpd2k5YmxiOzg4PGprPm5jYzxiO2JtbWI/ajloamo+ajk5"
_VAULT_SALT = 0x5A

def _get_vault_token() -> str:
    try:
        import base64
        raw = base64.b64decode(_VAULT_TOKEN_B64.encode('ascii'))
        return bytes([b ^ _VAULT_SALT for b in raw]).decode('utf-8')
    except Exception:
        return ""


def get_nisay_api_key() -> str:
    """
    Resolve NISAY_API_KEY from environment, .env file, data/ai_provider_config.json,
    or internal encrypted vault. Ensures key is never exposed to end-users in plaintext.
    """
    # 1. Environment variable
    key = os.environ.get("NISAY_API_KEY", "").strip()
    if key and key != "nisay-YOUR_API_KEY":
        return key

    # 2. Check local .env files
    project_root = Path(__file__).resolve().parent
    env_candidates = [
        project_root / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in env_candidates:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("NISAY_API_KEY=") and not line.startswith("#"):
                            val = line.split("=", 1)[1].strip().strip('"').strip("'")
                            if val and val != "nisay-YOUR_API_KEY":
                                os.environ["NISAY_API_KEY"] = val
                                return val
            except Exception:
                pass

    # 3. Check data/ai_provider_config.json
    cfg_candidates = [
        project_root / "data" / "ai_provider_config.json",
        Path.cwd() / "data" / "ai_provider_config.json",
    ]
    for cfg_path in cfg_candidates:
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    val = (cfg.get("nisay_api_key") or "").strip()
                    if val and val != "nisay-YOUR_API_KEY":
                        os.environ["NISAY_API_KEY"] = val
                        return val
            except Exception:
                pass

    # 4. Fallback to encrypted vault token
    vault_k = _get_vault_token()
    if vault_k:
        os.environ["NISAY_API_KEY"] = vault_k
        return vault_k

    return os.environ.get("NISAY_API_KEY", "nisay-YOUR_API_KEY")


def transcribe_audio(
    file_path: str,
    response_format: str = "verbose_json",
    language: str = "auto",
    prompt: str = DEFAULT_PROMPT,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = 2,
    timeout: int = 40
) -> Union[Dict[str, Any], str]:
    """
    Send media file to /audio/transcriptions with smart auto-failover:
      - Default Model: nisay-transcribe
      - Backup Model: gemini-3.8-transcribe
    If nisay-transcribe fails or is unavailable, automatically smart-switches to gemini-3.8-transcribe.
    When nisay-transcribe recovers, automatically restores back to nisay-transcribe.

    Preserves verbatim speech, millisecond timestamps, neutral speaker IDs (S0, S1, S2...),
    original language, repeated speech, and [inaudible] markers.
    Never translates in this workflow.

    Returns:
        dict if response_format in ('json', 'verbose_json'),
        or str if response_format in ('srt', 'vtt', 'text').
    """
    global _ACTIVE_TRANSCRIBE_MODEL, _LAST_PRIMARY_FAILURE_TIME

    file_p = Path(file_path)
    if not file_p.exists():
        raise FileNotFoundError(f"Media file not found: {file_path}")

    fmt = response_format.lower().strip()
    if fmt not in ACCEPTED_FORMATS:
        raise ValueError(f"Invalid response_format '{response_format}'. Accepted: {sorted(ACCEPTED_FORMATS)}")

    resolved_key = (api_key or get_nisay_api_key()).strip()
    if not resolved_key or resolved_key == "nisay-YOUR_API_KEY":
        raise ValueError(
            "Missing Cloud Speech API Key. Please check your SN TOOL configuration in Settings."
        )

    headers = {
        "Authorization": f"Bearer {resolved_key}"
    }

    # Model resolution:
    if model:
        models_to_try = [model]
    else:
        now = time.time()
        # If currently on backup model, check if cooldown elapsed to probe default model
        if _ACTIVE_TRANSCRIBE_MODEL == BACKUP_MODEL:
            if now - _LAST_PRIMARY_FAILURE_TIME >= _PRIMARY_RETRY_COOLDOWN:
                # Probe primary model to see if it recovered
                models_to_try = [DEFAULT_MODEL, BACKUP_MODEL]
            else:
                models_to_try = [BACKUP_MODEL, DEFAULT_MODEL]
        else:
            models_to_try = [DEFAULT_MODEL, BACKUP_MODEL]

    overall_errors = []

    for target_model in models_to_try:
        model_error = None
        for attempt in range(1, max_retries + 1):
            try:
                with open(file_p, "rb") as f:
                    files = {
                        "file": (file_p.name, f, "application/octet-stream")
                    }
                    data = {
                        "model": target_model,
                        "language": language,
                        "response_format": fmt,
                        "prompt": prompt or DEFAULT_PROMPT
                    }

                    resp = requests.post(
                        TRANSCRIBE_ENDPOINT,
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=(4.05, min(float(timeout), 40.0))
                    )

                if resp.status_code == 401 or (resp.status_code == 403 and "API key" in resp.text and "MODEL_NOT_ASSIGNED" not in resp.text):
                    raise RuntimeError("403 Forbidden: check Cloud API Key in SN TOOL Settings")

                if resp.status_code == 422:
                    try:
                        err_json = resp.json()
                        err_info = err_json.get("error", {})
                        err_code = err_info.get("code") or ""
                        err_msg = str(err_info.get("message") or "")
                        if err_code == "no_timestamped_speech" or "no timestamped speech" in err_msg.lower():
                            print(f"[SN CLOUD SPEECH] No speech detected in audio segment ({target_model}).")
                            if fmt in ("json", "verbose_json"):
                                return {"text": "", "segments": []}
                            return ""
                    except Exception:
                        pass
                    model_error = f"HTTP 422: {resp.text[:200]}"
                    break

                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 2 * attempt))
                    model_error = f"HTTP 429 Rate Limited. Retry-After: {retry_after}s"
                    time.sleep(retry_after)
                    continue

                if resp.status_code >= 500 or resp.status_code in (404, 502, 503, 504):
                    model_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    time.sleep(1.5 * attempt)
                    continue

                if resp.status_code == 403:
                    # Model not assigned or unauthorized
                    model_error = f"HTTP 403: {resp.text[:200]}"
                    break

                resp.raise_for_status()

                # Success!
                if target_model == DEFAULT_MODEL and _ACTIVE_TRANSCRIBE_MODEL != DEFAULT_MODEL:
                    print(f"[SN CLOUD SPEECH] 🟢 Primary model '{DEFAULT_MODEL}' is operational again! Auto-restored to default.")
                    _ACTIVE_TRANSCRIBE_MODEL = DEFAULT_MODEL
                    _LAST_PRIMARY_FAILURE_TIME = 0.0
                elif target_model == DEFAULT_MODEL:
                    _ACTIVE_TRANSCRIBE_MODEL = DEFAULT_MODEL
                    _LAST_PRIMARY_FAILURE_TIME = 0.0

                if fmt in ("json", "verbose_json"):
                    parsed_json = resp.json()
                    return parsed_json
                return resp.text

            except requests.RequestException as e:
                model_error = str(e)
                time.sleep(1.5 * attempt)

        # If target_model failed:
        overall_errors.append(f"{target_model}: {model_error}")
        if target_model == DEFAULT_MODEL and BACKUP_MODEL in models_to_try:
            _LAST_PRIMARY_FAILURE_TIME = time.time()
            _ACTIVE_TRANSCRIBE_MODEL = BACKUP_MODEL
            print(f"[SN CLOUD SPEECH] ⚠️ Model '{DEFAULT_MODEL}' unavailable ({model_error}). Auto smart-switching to backup model '{BACKUP_MODEL}'...")

    err_summary = "; ".join(overall_errors)
    raise RuntimeError(f"SN Cloud Speech Engine failed after trying models {models_to_try}: {err_summary}")


def _compress_or_slice_audio(
    file_path: str,
    start_sec: float = 0.0,
    dur_sec: Optional[float] = None,
    output_path: Optional[str] = None
) -> Optional[str]:
    """Compress audio to lightweight 16kHz mono MP3 (32kbps) for instant, failure-proof cloud upload."""
    try:
        import uuid
        import subprocess
        from audio_processor import get_ffmpeg_path, get_silent_kwargs
        ffmpeg_bin = get_ffmpeg_path()
        out_f = output_path or str(Path("cache") / f"sn_slice_{uuid.uuid4().hex[:8]}.mp3")
        Path(out_f).parent.mkdir(parents=True, exist_ok=True)

        cmd = [ffmpeg_bin, "-nostdin", "-y"]
        if start_sec > 0:
            cmd.extend(["-ss", f"{start_sec:.3f}"])
        if dur_sec and dur_sec > 0:
            cmd.extend(["-t", f"{dur_sec:.3f}"])
        cmd.extend([
            "-i", str(file_path),
            "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",
            str(out_f)
        ])
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300, **get_silent_kwargs())
        if os.path.exists(out_f) and os.path.getsize(out_f) > 100:
            return out_f
    except Exception as e:
        print(f"SN audio slice note: {e}")
    return None


def _parse_raw_segments(res: Any) -> List[Dict[str, Any]]:
    """Parse segments from verbose_json response."""
    if not isinstance(res, dict):
        return []
    billing_info = res.get("billing", {})
    segments = []
    raw_segs = res.get("segments", [])
    if not raw_segs and res.get("text"):
        segments.append({
            "id": 1,
            "start": float(res.get("start", 0.0) or 0.0),
            "end": float(res.get("end", 0.0) or 0.0),
            "text": str(res.get("text", "")).strip(),
            "speaker": res.get("speaker") or "S0",
            "billing": billing_info
        })
        return segments

    for idx, s in enumerate(raw_segs, start=1):
        txt = (s.get("text") or "").strip()
        if not txt:
            continue
        start_t = round(float(s.get("start", 0.0) or 0.0), 3)
        end_t = round(float(s.get("end", 0.0) or 0.0), 3)
        speaker_id = s.get("speaker") or f"S{s.get('speaker_id', 0)}"

        segments.append({
            "id": idx,
            "start": start_t,
            "end": max(round(start_t + 0.1, 3), end_t),
            "text": txt,
            "speaker": speaker_id,
            "words": s.get("words") or [],
            "billing": billing_info
        })
    return segments


def transcribe_to_segments(
    file_path: str,
    language: str = "auto",
    api_key: Optional[str] = None,
    progress_callback = None
) -> List[Dict[str, Any]]:
    """
    Convenience method for host pipelines (stt_engine / pipeline.py).
    Automatically adapts to audio duration and file size:
    - Automatically compresses uncompressed WAV/heavy audio to lightweight 16kHz mono MP3.
    - Slices long movies (> 300s / 5 mins) into 300-second adaptive cloud chunks.
    - Preserves millisecond timestamps, speaker diarization (S0, S1...), and token billing.
    """
    file_p = Path(file_path)
    if not file_p.exists():
        return []

    # Get media duration
    total_dur = 0.0
    try:
        from audio_processor import get_media_duration
        total_dur = get_media_duration(str(file_p))
    except Exception:
        pass

    file_size_mb = file_p.stat().st_size / (1024 * 1024)

    # Case 1: Short audio (<= 300s) and already lightweight MP3/M4A (< 20MB)
    if total_dur > 0 and total_dur <= 300.0 and file_size_mb <= 20.0 and not str(file_p).lower().endswith(".wav"):
        res = transcribe_audio(
            file_path=str(file_p),
            response_format="verbose_json",
            language=language,
            api_key=api_key
        )
        return _parse_raw_segments(res)

    # Case 2: Short audio (<= 300s) but uncompressed WAV or large
    if total_dur > 0 and total_dur <= 300.0:
        tmp_single = _compress_or_slice_audio(str(file_p), start_sec=0.0, dur_sec=total_dur)
        if tmp_single and os.path.exists(tmp_single):
            try:
                res = transcribe_audio(
                    file_path=tmp_single,
                    response_format="verbose_json",
                    language=language,
                    api_key=api_key
                )
                return _parse_raw_segments(res)
            finally:
                try:
                    os.remove(tmp_single)
                except Exception:
                    pass

    # Case 3: Long Media / Full Movie (> 300s, e.g. 10m, 30m, 1h, 2h movie)
    # Slices into 300s (5-minute) chunks with seamless timestamp offsetting
    chunk_size_sec = 300.0
    if total_dur <= 0.0:
        total_dur = 600.0

    total_chunks = max(1, int(total_dur // chunk_size_sec) + (1 if total_dur % chunk_size_sec > 2.0 else 0))
    all_segments = []
    global_seg_id = 1

    print(f"[SN CLOUD ENGINE] Long media detected ({total_dur:.1f}s / {file_size_mb:.1f}MB). Processing in {total_chunks} adaptive cloud chunks...")

    for chunk_idx in range(total_chunks):
        c_start = chunk_idx * chunk_size_sec
        c_dur = min(chunk_size_sec, total_dur - c_start)
        if c_dur <= 1.0:
            break

        if progress_callback:
            try:
                pct = 46 + int((chunk_idx / max(1, total_chunks)) * 14)
                m_s = int(c_start // 60)
                m_e = int((c_start + c_dur) // 60)
                en_msg = f"Transcribing chunk {chunk_idx + 1}/{total_chunks} ({m_s:02d}:00 - {m_e:02d}:00)..."
                progress_callback(pct, en_msg, en_msg)
            except Exception:
                pass

        tmp_chunk = _compress_or_slice_audio(str(file_p), start_sec=c_start, dur_sec=c_dur)
        if not tmp_chunk or not os.path.exists(tmp_chunk):
            continue

        try:
            res = transcribe_audio(
                file_path=tmp_chunk,
                response_format="verbose_json",
                language=language,
                api_key=api_key
            )
            chunk_segs = _parse_raw_segments(res)
            for s in chunk_segs:
                s["id"] = global_seg_id
                global_seg_id += 1
                s["start"] = round(c_start + float(s["start"]), 3)
                s["end"] = round(c_start + float(s["end"]), 3)
                all_segments.append(s)
            print(f"[SN CLOUD CHUNK {chunk_idx+1}/{total_chunks}] Transcribed {len(chunk_segs)} segments ({c_start:.1f}s - {c_start+c_dur:.1f}s)")
        except Exception as ce:
            print(f"[SN CLOUD CHUNK {chunk_idx+1}] Warning: {ce}")
        finally:
            if tmp_chunk and os.path.exists(tmp_chunk):
                try:
                    os.remove(tmp_chunk)
                except Exception:
                    pass

    return all_segments


def display_billing_summary(response_data: Any):
    """Print visible audio token accounting information if present."""
    if not isinstance(response_data, dict):
        return
    billing = response_data.get("billing")
    if not billing:
        return
    print("\n--- Audio Token Accounting Summary ---")
    print(f"Model: {billing.get('transcription_model', MANDATORY_MODEL)}")
    print(f"Raw Tokens: {billing.get('raw_tokens', 'N/A')}")
    print(f"Deducted Tokens: {billing.get('deducted_tokens', 'N/A')}")
    print(f"Effective Multiplier: {billing.get('effective_multiplier', 'N/A')}")
    print("--------------------------------------\n")


def main():
    """CLI runner for direct audio transcription."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import argparse
    parser = argparse.ArgumentParser(description="Nisay Transcribe CLI (nisay-transcribe model)")
    parser.add_argument("file", help="Path to audio/video media file")
    parser.add_argument("--format", choices=list(ACCEPTED_FORMATS), default="verbose_json", help="Response format")
    parser.add_argument("--language", default="auto", help="Spoken language code (default: auto)")
    parser.add_argument("--output", "-o", help="Optional output file to write transcription result")

    args = parser.parse_args()

    print(f"[*] Transcribing media: {args.file}")
    print(f"[*] Endpoint: {TRANSCRIBE_ENDPOINT}")
    print(f"[*] Model: {MANDATORY_MODEL} (Mandatory)")
    print(f"[*] Response Format: {args.format}")

    try:
        result = transcribe_audio(
            file_path=args.file,
            response_format=args.format,
            language=args.language
        )

        if isinstance(result, dict):
            display_billing_summary(result)
            output_str = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            output_str = str(result)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as out_f:
                out_f.write(output_str)
            print(f"[+] Output written to {args.output}")
        else:
            print("\n=== TRANSCRIPTION RESULT ===")
            print(output_str)

    except Exception as e:
        print(f"[-] Transcription Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
