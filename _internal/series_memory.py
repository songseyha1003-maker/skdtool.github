"""
Full Drama Series Auto-Bible & Cross-Episode Continuity Engine
Ensures 100% Character Name, Pronoun, Relationship & Narrative Consistency
from Episode 01 to Episode 100+ without drift or dropped words.
"""
import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

SERIES_BIBLE_DIR = Path("data/series_bibles")
SERIES_BIBLE_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_series_id(raw_name: str) -> str:
    """Normalize drama title or folder name into a clean, safe filename."""
    if not raw_name:
        return "drama_series"
    # Remove 《》, brackets, symbols
    clean = re.sub(r'[\\/*?:"<>|《》【】「」『』\(\)\[\]]', '_', str(raw_name))
    # Remove episode numbers like EP01, EP_01, 第1集
    clean = re.sub(r'(?i)(?:EP|Episode|Part|第)?[\s_\-]*\d+[\s_\-]*(?:集|話|部)?', '', clean)
    clean = re.sub(r'[\s_\-]+', '_', clean).strip('_')
    return clean[:40] or "drama_series"


class DramaSeriesMemory:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_bible_path(self, series_id: str) -> Path:
        safe_id = sanitize_series_id(series_id)
        return SERIES_BIBLE_DIR / f"{safe_id}.json"

    def get_or_create_series_bible(
        self,
        drama_title: str,
        sample_dialogues: Optional[List[Dict[str, Any]]] = None,
        synopsis: str = ""
    ) -> Dict[str, Any]:
        """
        Retrieve existing Series Bible or intelligently infer characters,
        relationship roles, and terms for the entire 100-episode series.
        """
        series_id = sanitize_series_id(drama_title)
        bible_p = self.get_bible_path(series_id)

        if series_id in self._cache:
            return self._cache[series_id]

        if bible_p.exists():
            try:
                with open(bible_p, "r", encoding="utf-8") as f:
                    bible = json.load(f)
                    self._cache[series_id] = bible
                    return bible
            except Exception:
                pass

        # Intelligently infer Series Profile from drama title, synopsis, and early dialogues
        raw_text_corpus = f"{drama_title} {synopsis}"
        if sample_dialogues:
            sample_lines = " ".join([d.get("text", "") or d.get("text_original", "") for d in sample_dialogues[:30]])
            raw_text_corpus += f" {sample_lines}"

        # 1. Detect Character Names & Tropes
        male_lead = "តួប្រុស (ពិសិដ្ឋ)"
        female_lead = "តួស្រី (ស្រីមុំ)"
        roles_detected = []
        glossary = {}

        # Boss / CEO Tropes
        if re.search(r'总裁|董事长|老板|少爷|傅总|顾总|陆总|沈总|江总|裴总|霍总', raw_text_corpus):
            roles_detected.append("CEO / ប្រធានក្រុមហ៊ុនអភិជន")
            glossary["总裁"] = "លោកប្រធាន"
            glossary["董事长"] = "លោកប្រធានក្រុមប្រឹក្សា"
            glossary["少爷"] = "អ្នកប្រុសធំ"

        # War God / Dragon King Tropes
        if re.search(r'战神|龙王|殿主|统帅|将军|兵王|修罗', raw_text_corpus):
            roles_detected.append("War God / មេទ័ពកំពូលនាគរាជ")
            glossary["战神"] = "មេទ័ពកំពូល"
            glossary["龙王"] = "ស្តេចនាគរាជ"
            glossary["殿主"] = "ម្ចាស់វិមាន"

        # Fake Marriage / Contract Tropes
        if re.search(r'契约|假结婚|替嫁|入赘|赘婿|闪婚', raw_text_corpus):
            roles_detected.append("Contract Marriage / រៀបការតាមកិច្ចសន្យា")
            glossary["契约婚姻"] = "រៀបការក្លែងក្លាយតាមកិច្ចសន្យា"
            glossary["替嫁"] = "រៀបការជំនួស"
            glossary["入赘"] = "កូនប្រសារចូលស្តី"

        # Revenge & Face-slapping Tropes
        if re.search(r'打脸|逆袭|首富|神豪|扮猪吃虎|退婚|隐形首富|白眼狼', raw_text_corpus):
            roles_detected.append("Revenge & Face-slapping / សងសឹកវាយបក")
            glossary["打脸"] = "ទះកំផ្លៀងមុខឱ្យបាក់មុខកណ្តាលវាល"
            glossary["逆袭"] = "ក្រោកឈរវាយបកយកជ័យជម្នះ"
            glossary["首富"] = "មហាសេដ្ឋីលំដាប់ប្រទេស"
            glossary["白眼狼"] = "មនុស្សរមិលគុណស៊ីបាយបោកឆ្នាំង"

        # Family & Mother-in-Law Tropes
        if re.search(r'婆婆|恶婆婆|丈母娘|扫地出门|断绝关系|家产|分家', raw_text_corpus):
            roles_detected.append("Family In-Law Feud / ជម្លោះគ្រួសារម្តាយក្មេក")
            glossary["婆婆"] = "ម្តាយក្មេក"
            glossary["扫地出门"] = "បណ្តេញក្បាលចេញពីផ្ទះ!"
            glossary["断绝关系"] = "កាត់កាលចោលឈប់រាប់អាន!"

        # Secret Child & Reunion Tropes
        if re.search(r'带球跑|萌宝|怀了|怀孕|打掉孩子|两道杠|亲子鉴定', raw_text_corpus):
            roles_detected.append("Secret Pregnancy / ពពោះកូនរត់គេចខ្លួន")
            glossary["带球跑"] = "ពពោះកូនរត់គេចខ្លួន"
            glossary["萌宝"] = "កូនឆ្លាតវៃ"
            glossary["亲子鉴定"] = "ការធ្វើតេស្ត DNA ឈាមជ័រឪពុកកូន"

        # Extract specific Chinese names if present
        name_matches = re.findall(r'([李张王刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈顾陆霍江裴][\u4e00-\u9fff]{1,2})', raw_text_corpus)
        unique_names = []
        for n in name_matches:
            if n not in unique_names and n not in ("总裁", "董事长", "少爷", "夫人", "小姐", "老婆", "老公"):
                unique_names.append(n)

        # Build initial Drama Series Bible
        bible = {
            "series_id": series_id,
            "title": drama_title,
            "created_at": time.time(),
            "genre_tropes": roles_detected or ["Drama Dubbing"],
            "male_lead": {
                "name": unique_names[0] if len(unique_names) > 0 else "តួឯកប្រុស",
                "voice": "piseth",
                "persona": "Male Lead (ពិសិដ្ឋ)",
                "pronoun_self": "ខ្ញុំ / បង",
                "pronoun_call_female_lead": "អូន / នាង"
            },
            "female_lead": {
                "name": unique_names[1] if len(unique_names) > 1 else "តួឯកស្រី",
                "voice": "sreymom",
                "persona": "Female Lead (ស្រីមុំ)",
                "pronoun_self": "ខ្ញុំ / អូន",
                "pronoun_call_male_lead": "បង / លោក"
            },
            "villain_or_rival": {
                "name": unique_names[2] if len(unique_names) > 2 else "តួឈ្នានីស",
                "voice": "sreymom" if "女" in raw_text_corpus else "piseth",
                "persona": "Antagonist / ជនទីបី"
            },
            "glossary": glossary,
            "episode_summaries": {}  # "1": "Summary of EP 1", "2": "Summary of EP 2"
        }

        try:
            with open(bible_p, "w", encoding="utf-8") as f:
                json.dump(bible, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        self._cache[series_id] = bible
        return bible

    def record_episode_summary(
        self,
        drama_title: str,
        episode_num: int,
        dialogues: List[Dict[str, Any]]
    ):
        """
        Record a concise 1-sentence synopsis of what happened in this episode
        so subsequent episodes retain emotional momentum and story memory.
        """
        if not dialogues:
            return

        series_id = sanitize_series_id(drama_title)
        bible = self.get_or_create_series_bible(drama_title)

        # Extract 2-3 key Khmer dialogue lines to form natural episode synopsis
        key_lines = []
        for d in dialogues[:12]:
            km = (d.get("text_km") or "").strip()
            if len(km) >= 6 and km not in key_lines:
                key_lines.append(km)
            if len(key_lines) >= 2:
                break

        summary = " | ".join(key_lines) if key_lines else "សាច់រឿងបន្តពីភាគមុន"
        bible["episode_summaries"][str(episode_num)] = summary[:180]

        # Save to disk
        bible_p = self.get_bible_path(series_id)
        try:
            with open(bible_p, "w", encoding="utf-8") as f:
                json.dump(bible, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_series_prompt_injection(
        self,
        drama_title: str,
        current_episode_num: Optional[int] = None
    ) -> str:
        """
        Builds the strict Master Drama Series Bible prompt instruction
        to ensure 100% naming consistency and zero vocabulary deviation.
        """
        bible = self.get_or_create_series_bible(drama_title)
        m_lead = bible.get("male_lead", {})
        f_lead = bible.get("female_lead", {})
        glossary = bible.get("glossary", {})

        # Previous episode context if available
        context_str = ""
        if current_episode_num and current_episode_num > 1:
            prev_ep = current_episode_num - 1
            prev_sum = bible.get("episode_summaries", {}).get(str(prev_ep))
            if prev_sum:
                context_str = f"\n- PREVIOUS EPISODE (ភាគ {prev_ep}) RECAP: \"{prev_sum}\". Continue dialogue seamlessly with matching emotional tone!"

        glossary_items = [f"'{k}' ➔ '{v}'" for k, v in glossary.items()]
        glossary_str = f"\n- SERIES VOCABULARY: {', '.join(glossary_items)}" if glossary_items else ""

        injection = f"""
=== 📖 MASTER DRAMA SERIES BIBLE (រក្សាឈ្មោះ និងតួនាទីតួអង្គត្រឹមត្រូវ ១០០% គ្រប់ភាគ) ===
Drama Series: 《{drama_title}》
- MALE LEAD (តួឯកប្រុស): {m_lead.get('name', 'តួប្រុស')} (Voice: Piseth | Self: '{m_lead.get('pronoun_self', 'ខ្ញុំ')}', Calls Female Lead: '{m_lead.get('pronoun_call_female_lead', 'អូន')}')
- FEMALE LEAD (តួឯកស្រី): {f_lead.get('name', 'តួស្រី')} (Voice: Sreymom | Self: '{f_lead.get('pronoun_self', 'ខ្ញុំ')}', Calls Male Lead: '{f_lead.get('pronoun_call_male_lead', 'បង')}')
- RELATIONSHIPS: Spouses/Lovers use 'បង/អូន'; Boss/Employee use 'លោកប្រធាន/ខ្ញុំ'; Enemies/Arguments use 'ឯង/យើង'.
- STRICT CONSISTENCY: Maintain these exact character names and pronouns across all episodes! NEVER invent different names!{context_str}{glossary_str}
========================================================================================
"""
        return injection


# Global singleton instance
series_memory = DramaSeriesMemory()
