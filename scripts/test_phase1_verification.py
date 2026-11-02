# -*- coding: utf-8 -*-
import sys
import os
import asyncio
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from series_memory import series_memory
from translator import DramaTranslator
from tts_engine import synthesize_khmer_speech, is_valid_audible_audio

async def run_tests():
    print("=" * 60)
    print("🧪 RUNNING PHASE 1 VERIFICATION TESTS")
    print("=" * 60)

    # 1. Test Series Memory Bible Creation
    print("\n[TEST 1] Testing Series Memory & Character Knowledge Graph...")
    test_title = "《总裁的替嫁娇妻》EP01"
    bible = series_memory.get_or_create_series_bible(test_title, synopsis="顾北辰是千亿总裁，林浅替姐姐替嫁过去。")
    assert bible is not None, "Failed to create series bible"
    print(f"  ✅ Series ID: {bible['series_id']}")
    print(f"  ✅ Male Lead: {bible['male_lead']['name_km']} (Voice: {bible['male_lead']['voice']})")
    print(f"  ✅ Female Lead: {bible['female_lead']['name_km']} (Voice: {bible['female_lead']['voice']})")
    print(f"  ✅ Tropes Detected: {bible['genre_tropes']}")

    # 2. Test Emotion Inference
    print("\n[TEST 2] Testing Dialogue Emotion Inference...")
    test_lines = [
        ("អាគម្រក់! ឯងចង់ងាប់មែនទេ?! ចេញទៅភ្លាម!", "混蛋！给我滚！", "angry"),
        ("សូមអង្វរ... កុំយកកូនខ្ញុំទៅអី... ខ្ញុំឈឺចាប់ណាស់...", "求求你...别把孩子带走...", "sad"),
        ("បងស្រឡាញ់អូន... កុំបារម្ភអី ប្រពន្ធសម្លាញ់", "我爱你，别怕", "tender"),
        ("លោកប្រធានបញ្ជាឱ្យទិញយកក្រុមហ៊ុននេះភ្លាម", "总裁吩咐立刻收购这家公司", "authoritative")
    ]
    for km, zh, expected_emo in test_lines:
        inferred = series_memory.infer_dialogue_emotion(km, zh)
        print(f"  [{inferred.upper()}] Line: {km[:35]}... (Expected: {expected_emo})")
        assert inferred == expected_emo, f"Expected {expected_emo}, got {inferred}"
    print("  ✅ All emotions classified accurately!")

    # 3. Test Episode Continuity Summary
    print("\n[TEST 3] Testing Cross-Episode Continuity & Recap Injection...")
    sample_dialogues = [
        {"text_km": "លោកប្រធានគូប៉ីឆេនបានដឹងការពិតហើយ", "text_original": "顾总知道了真相"},
        {"text_km": "នាងលីនឈៀនរត់គេចខ្លួនបាត់ទៅហើយ", "text_original": "林浅已经逃走了"}
    ]
    series_memory.record_episode_summary(test_title, 1, sample_dialogues)
    injection = series_memory.get_series_prompt_injection(test_title, current_episode_num=2)
    assert "PREVIOUS EPISODE (ភាគ 1) RECAP" in injection, "Recap injection missing in Episode 2!"
    print("  ✅ Cross-episode continuity injection verified successfully!")

    # 4. Test Translation with Series Continuity
    print("\n[TEST 4] Testing Translation with Series Memory Integration...")
    translator = DramaTranslator()
    mock_dialogues = [
        {"id": 1, "start": 0.0, "end": 2.5, "text": "顾北辰，你这个混蛋！给我滚！"},
        {"id": 2, "start": 3.0, "end": 5.5, "text": "求求你放过我吧，我求你了。"}
    ]
    trans_res = await translator.translate_dialogues(
        mock_dialogues,
        drama_title=test_title,
        episode_number=1
    )
    assert len(trans_res) == 2, "Translation returned incorrect item count"
    assert "emotion" in trans_res[0], "Missing emotion tag in item 1"
    assert "emotion" in trans_res[1], "Missing emotion tag in item 2"
    print(f"  ✅ Item 1 [{trans_res[0].get('emotion')}]: {trans_res[0].get('text_km')} ({trans_res[0].get('speaker')})")
    print(f"  ✅ Item 2 [{trans_res[1].get('emotion')}]: {trans_res[1].get('text_km')} ({trans_res[1].get('speaker')})")

    # 5. Test Emotion-Modulated TTS Synthesis
    print("\n[TEST 5] Testing Emotion-Modulated Voice Synthesis (TTS)...")
    out_angry = Path("scratch/test_angry.mp3")
    out_angry.parent.mkdir(exist_ok=True)
    res_angry = await synthesize_khmer_speech(
        text="ឈប់ភ្លាម! ឯងចង់ងាប់មែនទេ?!",
        voice="piseth",
        output_path=str(out_angry),
        emotion="angry"
    )
    assert is_valid_audible_audio(res_angry), "Angry audio failed"
    print(f"  ✅ Angry speech synthesized: {res_angry} (Audible: True)")

    out_sad = Path("scratch/test_sad.mp3")
    res_sad = await synthesize_khmer_speech(
        text="សូមអង្វរ... កុំទៅចោលខ្ញុំអី...",
        voice="sreymom",
        output_path=str(out_sad),
        emotion="sad"
    )
    assert is_valid_audible_audio(res_sad), "Sad audio failed"
    print(f"  ✅ Sad speech synthesized: {res_sad} (Audible: True)")

    # Clean up test audio
    if out_angry.exists():
        out_angry.unlink()
    if out_sad.exists():
        out_sad.unlink()

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 1 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
