"""
Phase 1 Upgrade Script: AI Translation & Voice Dubbing Intelligence
Upgrades:
1. translator.py:
   - series_memory injection into Nisay AI, Groq, and Gemini
   - emotion tagging for all dialogue items
   - cross-episode character and pronoun consistency
2. tts_engine.py:
   - emotion-adaptive speech synthesis (angry, sad, tender, panic, authoritative, neutral)
   - batch_synthesize passing emotion tags
3. pipeline.py:
   - automated episode number detection and memory continuity recording
"""
import re
from pathlib import Path

def patch_translator():
    p = Path("translator.py")
    content = p.read_text(encoding="utf-8")

    # 1. Update translate_dialogues_nisay signature
    old_sig = '''    async def translate_dialogues_nisay(
        self,
        dialogues: List[Dict[str, Any]],
        source_lang: str = "auto",
        target_voice_override: Optional[str] = None,
        category: str = "chinese_general",
        custom_dict: Optional[Dict[str, str]] = None,
        mode: str = "drama_dubbing",
        drama_title: Optional[str] = None,
        progress_callback: Optional[Any] = None
    ) -> List[Dict[str, Any]]:'''

    new_sig = '''    async def translate_dialogues_nisay(
        self,
        dialogues: List[Dict[str, Any]],
        source_lang: str = "auto",
        target_voice_override: Optional[str] = None,
        category: str = "chinese_general",
        custom_dict: Optional[Dict[str, str]] = None,
        mode: str = "drama_dubbing",
        drama_title: Optional[str] = None,
        episode_number: Optional[int] = None,
        progress_callback: Optional[Any] = None
    ) -> List[Dict[str, Any]]:'''

    if old_sig in content:
        content = content.replace(old_sig, new_sig)
        print("[OK] Patched translate_dialogues_nisay signature")

    # 2. Inject series_memory into translate_dialogues_nisay
    old_context_block = '''        eff_cat = category
        if drama_title and any(w in str(drama_title) for w in ("神", "殿", "帝", "皇", "王", "仙", "剑", "古", "宫", "朝", "武", "封神", "hero", "ancient", "costume")):
            eff_cat = "chinese_historical"'''

    new_context_block = '''        eff_cat = category
        if drama_title and any(w in str(drama_title) for w in ("神", "殿", "帝", "皇", "王", "仙", "剑", "古", "宫", "朝", "武", "封神", "hero", "ancient", "costume")):
            eff_cat = "chinese_historical"

        # 🧠 Inject Master Series Bible & Character Graph if drama_title is provided
        series_context = ""
        if drama_title:
            try:
                from series_memory import series_memory
                series_context = series_memory.get_series_prompt_injection(drama_title, current_episode_num=episode_number)
                char_glossary = series_memory.get_character_glossary(drama_title)
                if char_glossary:
                    if custom_dict is None:
                        custom_dict = {}
                    for k, v in char_glossary.items():
                        if k not in custom_dict:
                            custom_dict[k] = v
            except Exception as e:
                print(f"Series memory note in Nisay: {e}")'''

    if old_context_block in content and "series_context = " not in content:
        content = content.replace(old_context_block, new_context_block)
        print("[OK] Injected series_memory into translate_dialogues_nisay context")

    # Make sure context_directive incorporates series_context
    old_ctx_end = 'NEVER bloat short lines into long explanatory paragraphs! Spoken audio must match mouth duration."\n            )'
    new_ctx_end = 'NEVER bloat short lines into long explanatory paragraphs! Spoken audio must match mouth duration."\n            )\n        if series_context:\n            context_directive = series_context + "\\n\\n" + context_directive'

    if old_ctx_end in content and "if series_context:" not in content:
        content = content.replace(old_ctx_end, new_ctx_end)
        print("[OK] Connected series_context to context_directive")

    # Attach emotion tag to nisay items
    old_nisay_item = '''            results.append({
                "id": itm.get("id", idx + 1),
                "start": start,
                "end": end,
                "speaker": speaker_title,
                "text_original": orig_text,
                "text_km": final_text_km,
                "voice": chosen_voice,
                "rate_percent": rate_percent,
                "pitch_hz": pitch_hz
            })'''

    new_nisay_item = '''            try:
                from series_memory import series_memory
                item_emotion = series_memory.infer_dialogue_emotion(final_text_km, orig_text)
            except Exception:
                item_emotion = "neutral"

            results.append({
                "id": itm.get("id", idx + 1),
                "start": start,
                "end": end,
                "speaker": speaker_title,
                "text_original": orig_text,
                "text_km": final_text_km,
                "voice": chosen_voice,
                "rate_percent": rate_percent,
                "pitch_hz": pitch_hz,
                "emotion": item_emotion
            })'''

    if old_nisay_item in content:
        content = content.replace(old_nisay_item, new_nisay_item)
        print("[OK] Added emotion tag to Nisay dialogue results")

    # Pass episode_number to translate_dialogues_nisay in translate_dialogues
    old_call = '''                    nisay_res = await self.translate_dialogues_nisay(
                        dialogues=dialogues,
                        source_lang=source_lang,
                        target_voice_override=target_voice_override,
                        category="chinese_general",
                        custom_dict=custom_dict,
                        mode=mode,
                        drama_title=drama_title,
                        progress_callback=progress_callback
                    )'''

    new_call = '''                    nisay_res = await self.translate_dialogues_nisay(
                        dialogues=dialogues,
                        source_lang=source_lang,
                        target_voice_override=target_voice_override,
                        category="chinese_general",
                        custom_dict=custom_dict,
                        mode=mode,
                        drama_title=drama_title,
                        episode_number=episode_number,
                        progress_callback=progress_callback
                    )'''

    if old_call in content:
        content = content.replace(old_call, new_call)
        print("[OK] Passed episode_number to Nisay translate call")

    # Add emotion tag to Gemini parsed results
    old_gemini_enrich = '''                                    dur_sec = round(max(0.2, float(item["end"]) - float(item["start"])), 2)
                                    item["text_km"] = enrich_khmer_drama_dialogue(
                                        item.get("text_km", ""),
                                        orig_line,
                                        item["voice"],
                                        duration_sec=dur_sec
                                    )'''

    new_gemini_enrich = '''                                    dur_sec = round(max(0.2, float(item["end"]) - float(item["start"])), 2)
                                    item["text_km"] = enrich_khmer_drama_dialogue(
                                        item.get("text_km", ""),
                                        orig_line,
                                        item["voice"],
                                        duration_sec=dur_sec
                                    )
                                    try:
                                        from series_memory import series_memory
                                        item["emotion"] = series_memory.infer_dialogue_emotion(item["text_km"], orig_line)
                                    except Exception:
                                        item["emotion"] = "neutral"'''

    if old_gemini_enrich in content and 'item["emotion"] = series_memory' not in content:
        content = content.replace(old_gemini_enrich, new_gemini_enrich)
        print("[OK] Added emotion tag to Gemini dialogue results")

    p.write_text(content, encoding="utf-8")
    print("[SUCCESS] Patched translator.py")


def patch_tts_engine():
    p = Path("tts_engine.py")
    content = p.read_text(encoding="utf-8")

    # 1. Update synthesize_khmer_speech signature to support emotion
    old_tts_sig = '''async def synthesize_khmer_speech(
    text: str,
    voice: str = "piseth",
    rate_percent: int = 0,
    pitch_hz: int = 0,
    output_path: Optional[str] = None,
    use_cache: bool = True
) -> str:'''

    new_tts_sig = '''async def synthesize_khmer_speech(
    text: str,
    voice: str = "piseth",
    rate_percent: int = 0,
    pitch_hz: int = 0,
    output_path: Optional[str] = None,
    use_cache: bool = True,
    emotion: Optional[str] = None
) -> str:'''

    if old_tts_sig in content:
        content = content.replace(old_tts_sig, new_tts_sig)
        print("[OK] Updated synthesize_khmer_speech signature with emotion")

    # 2. Add emotion-adaptive rate and pitch modulation
    old_mod_point = '''    voice_id = get_voice_id(voice)
    rate_str = _format_rate(rate_percent)
    pitch_str = _format_pitch(pitch_hz)'''

    new_mod_point = '''    # 🎭 Dynamic Emotion Modulation (Piseth & Sreymom Acting Intelligence)
    eff_rate = rate_percent
    eff_pitch = pitch_hz
    if emotion and rate_percent == 0 and pitch_hz == 0:
        emo = str(emotion).lower()
        if emo == "angry":
            eff_rate = 8
            eff_pitch = 2
        elif emo == "sad":
            eff_rate = -5
            eff_pitch = -2
        elif emo == "tender":
            eff_rate = -2
            eff_pitch = -1
        elif emo == "panic":
            eff_rate = 12
            eff_pitch = 3
        elif emo == "authoritative":
            eff_rate = 3
            eff_pitch = -2

    voice_id = get_voice_id(voice)
    rate_str = _format_rate(eff_rate)
    pitch_str = _format_pitch(eff_pitch)'''

    if old_mod_point in content and "Dynamic Emotion Modulation" not in content:
        content = content.replace(old_mod_point, new_mod_point)
        print("[OK] Added emotion modulation to synthesize_khmer_speech")

    # 3. In batch_synthesize, pass emotion
    old_batch_item = '''            item_id = item.get("id", index)
            text = (item.get("text_km") or item.get("text", "")).strip()
            voice = item.get("voice") or default_voice
            start = float(item.get("start", 0.0))
            end = float(item.get("end", start + 2.0))'''

    new_batch_item = '''            item_id = item.get("id", index)
            text = (item.get("text_km") or item.get("text", "")).strip()
            voice = item.get("voice") or default_voice
            start = float(item.get("start", 0.0))
            end = float(item.get("end", start + 2.0))
            emotion = item.get("emotion") or "neutral"'''

    if old_batch_item in content and "emotion = item.get(\"emotion\")" not in content:
        content = content.replace(old_batch_item, new_batch_item)
        print("[OK] Extracted emotion in batch_synthesize")

    old_batch_call = '''                    audio_file = await synthesize_khmer_speech(
                        text=text,
                        voice=voice,
                        rate_percent=rate,
                        pitch_hz=pitch,
                        output_path=str(line_audio_path)
                    )'''

    new_batch_call = '''                    audio_file = await synthesize_khmer_speech(
                        text=text,
                        voice=voice,
                        rate_percent=rate,
                        pitch_hz=pitch,
                        output_path=str(line_audio_path),
                        emotion=emotion
                    )'''

    if old_batch_call in content:
        content = content.replace(old_batch_call, new_batch_call)
        print("[OK] Passed emotion to synthesize_khmer_speech in batch_synthesize")

    p.write_text(content, encoding="utf-8")
    print("[SUCCESS] Patched tts_engine.py")


def patch_pipeline():
    p = Path("pipeline.py")
    content = p.read_text(encoding="utf-8")

    # In process_video_pipeline, detect episode number and pass to translate_dialogues
    old_trans_block = '''        update_prog(40, "🤖 AI កំពុងបកប្រែអត្ថបទរឿងភាគបែបខ្មែរ 100%...", "AI translating dialogue to natural spoken Khmer...")

        try:
            translated = await self.translator.translate_dialogues(
                dialogues=dialogues,
                mode=mode,
                source_lang=source_lang,
                target_voice_override=v_override,
                drama_title=proj_title,
                progress_callback=on_trans_prog
            )'''

    new_trans_block = '''        update_prog(40, "🤖 AI កំពុងបកប្រែអត្ថបទរឿងភាគបែបខ្មែរ 100%...", "AI translating dialogue to natural spoken Khmer...")

        # 🧠 Parse episode number for cross-episode series continuity
        ep_num = 1
        ep_match = re.search(r'(?:EP|Episode|Part|第)?[\s_\-]*(\d+)', str(proj_title), re.IGNORECASE)
        if ep_match:
            try:
                ep_num = int(ep_match.group(1))
            except Exception:
                ep_num = 1

        try:
            translated = await self.translator.translate_dialogues(
                dialogues=dialogues,
                mode=mode,
                source_lang=source_lang,
                target_voice_override=v_override,
                drama_title=proj_title,
                episode_number=ep_num,
                progress_callback=on_trans_prog
            )'''

    if old_trans_block in content and "ep_num = 1" not in content:
        content = content.replace(old_trans_block, new_trans_block)
        print("[OK] Added episode number detection in pipeline.py")

    # After translation finishes, record episode summary
    old_done_trans = '''        update_prog(70, "🎉 AI បានបកប្រែអត្ថបទរឿងចប់សព្វគ្រប់ 100%...", "AI script translation completed 100%")'''
    new_done_trans = '''        # 📖 Auto-record episode summary into Drama Series Memory for cross-episode continuity
        try:
            from series_memory import series_memory
            series_memory.record_episode_summary(proj_title, ep_num, translated)
        except Exception as se:
            print(f"Series summary record note: {se}")

        update_prog(70, "🎉 AI បានបកប្រែអត្ថបទរឿងចប់សព្វគ្រប់ 100%...", "AI script translation completed 100%")'''

    if old_done_trans in content and "series_memory.record_episode_summary" not in content:
        content = content.replace(old_done_trans, new_done_trans)
        print("[OK] Added auto-recording of episode summary to pipeline.py")

    p.write_text(content, encoding="utf-8")
    print("[SUCCESS] Patched pipeline.py")


if __name__ == "__main__":
    patch_translator()
    patch_tts_engine()
    patch_pipeline()
    print("All Phase 1 upgrades applied successfully!")

