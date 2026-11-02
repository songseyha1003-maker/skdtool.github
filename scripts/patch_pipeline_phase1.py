# -*- coding: utf-8 -*-
from pathlib import Path
import re

p = Path("pipeline.py")
c = p.read_text(encoding="utf-8")

old_call = """        try:
            translated = await self.translator.translate_dialogues(
                dialogues=dialogues,
                mode=mode,
                source_lang=source_lang,
                target_voice_override=v_override,
                drama_title=proj_title,
                progress_callback=on_trans_prog
            )"""

new_call = """        # 🧠 Parse episode number for cross-episode series continuity
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
            )"""

if old_call in c:
    c = c.replace(old_call, new_call, 1)
    print("[OK] Patched translate call in pipeline.py")
else:
    print("old_call not found in pipeline.py")

old_done = """        update_prog(70, "៤/៧ AI បានបកប្រែសាច់រឿងរួចរាល់ 100%...", "AI script translation completed 100%")"""
new_done = """        # 📖 Auto-record episode summary into Drama Series Memory for cross-episode continuity
        try:
            from series_memory import series_memory
            series_memory.record_episode_summary(proj_title, ep_num, translated)
        except Exception as se:
            print(f"Series summary record note: {se}")

        update_prog(70, "៤/៧ AI បានបកប្រែសាច់រឿងរួចរាល់ 100%...", "AI script translation completed 100%")"""

if old_done in c:
    c = c.replace(old_done, new_done, 1)
    print("[OK] Patched summary record in pipeline.py")
else:
    print("old_done not found in pipeline.py")

p.write_text(c, encoding="utf-8")
print("[SUCCESS] pipeline.py updated successfully")

