# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

ROOT_DIR = Path(SPECPATH).resolve()
import imageio_ffmpeg
ffmpeg_binaries_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())

import faster_whisper
import huggingface_hub
faster_whisper_dir = os.path.dirname(faster_whisper.__file__)
faster_whisper_assets = os.path.join(faster_whisper_dir, 'assets')
huggingface_hub_dir = os.path.dirname(huggingface_hub.__file__)

raw_datas = [
    ('icon.ico', '.'),
    ('license_config.json', '.'),
    ('custom_keys.json', '.'),
    ('version.json', '.'),
    ('static', 'static'),
    ('scripts', 'scripts'),
    ('data/hongguo_catalog.db', 'data'),
    ('data/shortmax_all_dramas.json', 'data'),
    ('data/reelshort_all_dramas.json', 'data'),
    ('data/ai_dramas_streams.json', 'data'),
    ('data/story_config.json', 'data'),
    ('data/drama_dictionary.json', 'data'),
    ('data/ai_provider_config.json', 'data'),
    ('data/license_keys_online.json', 'data'),
    ('data/revoked_keys.json', 'data'),
    ('data/update_config.json', 'data'),
    ('tools/Hongguo Downloader', 'tools/Hongguo Downloader'),
    ('models', 'models'),
]

datas = [(str(ROOT_DIR / p), dst) for p, dst in raw_datas if (ROOT_DIR / p).exists()]
if os.path.exists(ffmpeg_binaries_dir):
    datas.append((ffmpeg_binaries_dir, 'imageio_ffmpeg/binaries'))
if os.path.exists(faster_whisper_assets):
    datas.append((faster_whisper_assets, 'faster_whisper/assets'))
if os.path.exists(faster_whisper_dir):
    datas.append((faster_whisper_dir, 'faster_whisper'))
if os.path.exists(huggingface_hub_dir):
    datas.append((huggingface_hub_dir, 'huggingface_hub'))

a = Analysis(
    [str(ROOT_DIR / 'desktop_app.py')],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'edge_tts', 'pydub', 'flask', 'jinja2', 'soundfile', 'httpx',
        'webview', 'clr_loader', 'pythonnet', 'license_engine',
        'video_processor', 'downloader', 'tts_engine', 'translator',
        'pipeline', 'recap_engine', 'batch_engine', 'audio_processor',
        'vocal_remover', 'server', 'stt_engine', 'faster_whisper',
        'huggingface_hub', 'tokenizers', 'onnxruntime', 'ctranslate2',
        'hongguo_service', 'hongguo_db', 'shortmax_service', 'reelshort_service',
        'cryptography', 'update', 'nisay_translate', 'nisay_transcribe',
        'aiohttp', 'certifi', 'idna', 'yarl', 'multidict'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

icon_path = str(ROOT_DIR / 'icon.ico') if (ROOT_DIR / 'icon.ico').exists() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SN_TOOL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[icon_path] if icon_path else None,
    version=str(ROOT_DIR / 'scripts' / 'version_info_app.txt'),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SN_TOOL',
)

