# -*- coding: utf-8 -*-
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
dl_file = BASE_DIR / "downloader.py"
content = dl_file.read_text(encoding="utf-8")

old_method = """    def generate_drama_metadata_card(self, drama_dest_dir: Path, total_episodes: int = 0):
        \"\"\"
        Auto-generates a clean metadata package in the drama folder:
        - drama_info.json: structured metadata
        - synopsis_khmer.txt: natural Khmer synopsis ready for social media posting (Facebook/TikTok/Telegram)
        \"\"\"
        if not self.current_drama or not drama_dest_dir.exists():
            return

        d = self.current_drama
        title_cn = d.get("title_cn") or d.get("title", "Drama Series")
        title_km = d.get("title_km") or title_cn
        synopsis_raw = d.get("synopsis") or d.get("description") or ""
        platform = str(d.get("platform_id") or "Short Drama").upper()

        synopsis_km = synopsis_raw
        if any('\\u4e00' <= c <= '\\u9fff' for c in synopsis_raw):
            try:
                from nisay_translate import translate_khmer
                trans_syn = translate_khmer(synopsis_raw[:350], category="chinese_general", timeout=6.0)
                if isinstance(trans_syn, str) and trans_syn:
                    synopsis_km = trans_syn
            except Exception:
                synopsis_km = synopsis_raw

        if not synopsis_km:
            synopsis_km = f"រឿងភាគខ្លីដ៏ល្អមើល ដំណើររឿងជក់ចិត្ត និងទាក់ទាញអារម្មណ៍ ពេញលេញ {total_episodes} ភាគ ១០០%។"

        info_data = {
            "title": title_km,
            "title_original": title_cn,
            "platform": platform,
            "total_episodes": total_episodes,
            "quality": "1080p Full HD",
            "synopsis_khmer": synopsis_km,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        info_path = drama_dest_dir / "drama_info.json"
        try:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(info_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        syn_card = f\"\"\"🎬 【រឿងភាគ៖ {title_km}】
📺 ចំនួនភាគ៖ {total_episodes} ភាគ (ពេញលេញ ១០០%)
🌟 គុណភាព៖ 1080p Full HD
📱 វេទិកា៖ {platform}

📖 សង្ខេបសាច់រឿង៖
{synopsis_km}

👉 ទាញយក និងបញ្ចូលសំឡេងដោយ៖ SN TOOL - STUDIO PRO
\"\"\"
        syn_path = drama_dest_dir / "synopsis_khmer.txt"
        try:
            with open(syn_path, "w", encoding="utf-8") as f:
                f.write(syn_card.strip())
            self.add_log(f"📋 Generated Drama Social Card & Khmer Synopsis: {syn_path.name}")
        except Exception:
            pass"""

new_method = """    def generate_drama_metadata_card(self, drama_dest_dir: Path, total_episodes: int = 0):
        \"\"\"
        Disabled per user preference: preserves completely clean download folders
        containing exclusively episode video files and poster (no extra .json/.txt).
        \"\"\"
        return"""

# Normalize line endings
content_crlf = content.replace("\r\n", "\n")
old_method_crlf = old_method.replace("\r\n", "\n")

if old_method_crlf in content_crlf:
    content_crlf = content_crlf.replace(old_method_crlf, new_method)
    dl_file.write_text(content_crlf, encoding="utf-8")
    print("✅ Successfully disabled generate_drama_metadata_card in downloader.py")
else:
    print("⚠️ old_method not found in downloader.py")

# Also update test_phase2_verification.py
t2_file = BASE_DIR / "scripts" / "test_phase2_verification.py"
t2_content = t2_file.read_text(encoding="utf-8").replace("\r\n", "\n")
old_t2 = """    assert info_p.exists(), "drama_info.json was not created!"
    assert syn_p.exists(), "synopsis_khmer.txt was not created!" """
# Update test 1 in test_phase2_verification to verify clean folder (no drama_info.json or synopsis_khmer.txt created)
old_test1 = """    # 1. Test generate_drama_metadata_card
    print("\\n[TEST 1] Testing Drama Social Card & Khmer Synopsis Generation...")
    test_dir = Path("scratch/test_drama_dir")
    test_dir.mkdir(parents=True, exist_ok=True)

    mgr.current_drama = {
        "id": "sm_test_01",
        "title": "Magic Failure's Phoenix Fate",
        "title_cn": "凤落残局",
        "platform_id": "shortmax",
        "synopsis": "A banished phoenix daughter rises from the ashes to reclaim her rightful throne."
    }

    mgr.generate_drama_metadata_card(test_dir, total_episodes=50)

    info_p = test_dir / "drama_info.json"
    syn_p = test_dir / "synopsis_khmer.txt"

    assert info_p.exists(), "drama_info.json was not created!"
    assert syn_p.exists(), "synopsis_khmer.txt was not created!" """

new_test1 = """    # 1. Test clean download directory (no extra metadata/txt clutter)
    print("\\n[TEST 1] Verifying Clean Download Directory (No extra .json/.txt files)...")
    test_dir = Path("scratch/test_drama_dir")
    test_dir.mkdir(parents=True, exist_ok=True)

    mgr.current_drama = {
        "id": "sm_test_01",
        "title": "Magic Failure's Phoenix Fate",
        "title_cn": "凤落残局",
        "platform_id": "shortmax",
        "synopsis": "A banished phoenix daughter rises from the ashes to reclaim her rightful throne."
    }

    mgr.generate_drama_metadata_card(test_dir, total_episodes=50)

    info_p = test_dir / "drama_info.json"
    syn_p = test_dir / "synopsis_khmer.txt"

    assert not info_p.exists(), "drama_info.json should not be created!"
    assert not syn_p.exists(), "synopsis_khmer.txt should not be created!"
    print("  ✅ Clean download verified: No clutter files created!")"""

if old_test1 in t2_content:
    # also remove subsequent reads of info_p
    idx_end = t2_content.find("[TEST 2]")
    prefix = t2_content[:t2_content.find("    # 1. Test generate_drama_metadata_card")]
    suffix = t2_content[idx_end:]
    t2_file.write_text(prefix + new_test1 + "\n\n" + suffix, encoding="utf-8")
    print("✅ Successfully updated scripts/test_phase2_verification.py")
else:
    print("⚠️ old_test1 not found")

# Re-sign core manifest
import sys
sys.path.insert(0, str(BASE_DIR))
import license_engine
license_engine.build_core_manifest()
print("✅ Core security manifest rebuilt and re-signed!")
