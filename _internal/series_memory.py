"""
Full Drama Series Auto-Bible, Character Knowledge Graph & Cross-Episode Continuity Engine v2.0
Ensures 100% Character Name, Pronoun, Relationship & Narrative Consistency
from Episode 01 to Episode 100+ without drift, dropped words, or mismatched voices.
"""
import os
import re
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

SERIES_BIBLE_DIR = Path("data/series_bibles")
SERIES_BIBLE_DIR.mkdir(parents=True, exist_ok=True)

# Common Chinese drama surnames and given names phonetic Khmer mapping
COMMON_NAME_PHONETICS = {
    "顾北辰": "គូប៉ីឆេន",
    "陆霆骁": "លូធីងសៀវ",
    "傅景川": "ភូជីងឆួន",
    "沈曼琳": "ស៊ិនម៉ាន់លីន",
    "林早早": "លីនចាវចាវ",
    "李沐谦": "លីមូឈៀន",
    "江辰": "ជាំងឆេន",
    "楚辞": "ឈូឆឺ",
    "苏晴": "ស៊ូឈីង",
    "白洛": "ប៉ៃឡូ",
    "霍司爵": "ហួស៊ឺជាវ",
    "裴墨": "ផីមូ",
    "萧楚": "សៀវឈូ",
    "叶天": "យៀកធាន",
    "秦南": "ឈីនណាន",
    "宁夏": "នីងសៀ",
    "唐柔": "ថាងរ៉ូ",
    "张昭": "ចាងចាវ",
    "林浅": "លីនឈៀន",
    "顾南烟": "គូណានយ៉ាន",
    "薄夜": "ប៉ោយៀក",
    "战北寒": "ចាន់ប៉ីហាន",
    "云舒": "យុនស៊ូ",
    "宋温暖": "សុងវិននួន",
    "温婉": "វិនវ៉ាន់",
}

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

    def infer_character_roster(self, raw_corpus: str) -> Dict[str, Any]:
        """
        Deep analysis of drama corpus to identify characters, archetypes, and voices.
        """
        extracted_names = []

        # 1. First priority: Check known character names directly
        for known_name in COMMON_NAME_PHONETICS:
            if known_name in raw_corpus and known_name not in extracted_names:
                extracted_names.append(known_name)

        # 2. Extract Chinese character names (2-3 chars) and strip trailing verbs/particles
        name_matches = re.findall(
            r'([李张王刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈顾陆霍江裴厉楚秦叶苏白温][\u4e00-\u9fff]{1,2})',
            raw_corpus
        )
        invalid_words = {
            "总裁", "董事长", "少爷", "夫人", "小姐", "老婆", "老公", "爸爸", "妈妈",
            "爷爷", "奶奶", "战神", "龙王", "殿主", "修罗", "神医", "首富", "秘书",
            "助理", "先生", "女士", "姐姐", "妹妹", "哥哥", "弟弟", "老头", "管家",
            "短剧", "全集", "大结局", "高清", "原声", "合集", "热播", "推荐"
        }
        trailing_verbs = {"替", "的", "被", "在", "说", "道", "嫁", "娶", "死", "走", "了", "去", "到", "把", "是", "有", "给", "看", "要", "想", "追", "求", "和", "跟", "等", "及", "与"}
        for n in name_matches:
            cand = n.strip()
            if len(cand) == 3 and cand[-1] in trailing_verbs:
                cand = cand[:2]
            if cand not in extracted_names and cand not in invalid_words and len(cand) in (2, 3):
                extracted_names.append(cand)

        # Male Lead
        male_lead_name = extracted_names[0] if len(extracted_names) > 0 else "តួឯកប្រុស"
        male_km = COMMON_NAME_PHONETICS.get(male_lead_name, male_lead_name)

        # Female Lead
        female_lead_name = extracted_names[1] if len(extracted_names) > 1 else "តួឯកស្រី"
        female_km = COMMON_NAME_PHONETICS.get(female_lead_name, female_lead_name)

        # Antagonist / Villain
        villain_name = extracted_names[2] if len(extracted_names) > 2 else "តួឈ្នានីស"
        villain_km = COMMON_NAME_PHONETICS.get(villain_name, villain_name)

        # Elders
        elder_name = extracted_names[3] if len(extracted_names) > 3 else "ចាស់ទុំក្នុងគ្រួសារ"
        elder_km = COMMON_NAME_PHONETICS.get(elder_name, elder_name)

        return {
            "male_lead": {
                "name_zh": male_lead_name,
                "name_km": male_km,
                "voice": "piseth",
                "role": "Male Lead (តួឯកប្រុស)",
                "pronoun_self": "ខ្ញុំ / បង",
                "pronoun_call_female_lead": "អូន / នាង"
            },
            "female_lead": {
                "name_zh": female_lead_name,
                "name_km": female_km,
                "voice": "sreymom",
                "role": "Female Lead (តួឯកស្រី)",
                "pronoun_self": "ខ្ញុំ / អូន",
                "pronoun_call_male_lead": "បង / លោក"
            },
            "villain_or_rival": {
                "name_zh": villain_name,
                "name_km": villain_km,
                "voice": "sreymom" if any(w in raw_corpus for w in ("女配", "表妹", "前女友", "绿茶", "闺蜜")) else "piseth",
                "role": "Antagonist / Rival (តួកាច/តួឈ្នានីស)",
                "pronoun_call_leads": "ឯង / មីស្រីថោកទាប / អាគម្រក់"
            },
            "elder": {
                "name_zh": elder_name,
                "name_km": elder_km,
                "voice": "sreymom" if any(w in raw_corpus for w in ("婆婆", "老夫人", "母亲", "妈")) else "piseth",
                "role": "Elder / Parent (ចាស់ទុំ/ឪពុកម្តាយ)",
                "pronoun_call_leads": "កូន / ឯង / កូនប្រសា"
            }
        }

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
            sample_lines = " ".join([d.get("text", "") or d.get("text_original", "") for d in sample_dialogues[:40]])
            raw_text_corpus += f" {sample_lines}"

        roles_detected = []
        glossary: Dict[str, str] = {}

        # 1. Modern CEO / Billionaire / Dominant Boss
        if re.search(r'总裁|董事长|老板|少爷|傅总|顾总|陆总|沈总|江总|裴总|霍总|厉总|千亿|豪门', raw_text_corpus):
            roles_detected.append("Billionaire CEO / មហាសេដ្ឋីប្រធានក្រុមហ៊ុន")
            glossary["总裁"] = "លោកប្រធាន"
            glossary["董事长"] = "លោកប្រធានក្រុមប្រឹក្សា"
            glossary["少爷"] = "អ្នកប្រុសធំ"
            glossary["夫人"] = "លោកស្រីធំ"
            glossary["特助"] = "ជំនួយការពិសេស"

        # 2. War God / Dragon King / Martial Supreme
        if re.search(r'战神|龙王|殿主|统帅|将军|兵王|修罗|至尊|龙殿|阎王', raw_text_corpus):
            roles_detected.append("War God / មេទ័ពកំពូលនាគរាជ")
            glossary["战神"] = "មេទ័ពកំពូល"
            glossary["龙王"] = "ស្តេចនាគរាជ"
            glossary["殿主"] = "ម្ចាស់វិមាន"
            glossary["统帅"] = "មេទ័ពធំ"
            glossary["修罗"] = "ស្តេចអសុរា"

        # 3. Contract Marriage / Secret Wedding / Stand-in Bride
        if re.search(r'契约|假结婚|替嫁|入赘|赘婿|闪婚|隐婚|前夫|民政局', raw_text_corpus):
            roles_detected.append("Contract Marriage / រៀបការតាមកិច្ចសន្យា")
            glossary["契约婚姻"] = "រៀបការក្លែងក្លាយតាមកិច្ចសន្យា"
            glossary["替嫁"] = "រៀបការជំនួស"
            glossary["入赘"] = "កូនប្រសារចូលស្តី"
            glossary["赘婿"] = "កូនប្រសារអាស្រ័យផ្ទះ"
            glossary["闪婚"] = "រៀបការផ្លេកបន្ទោរ"
            glossary["民政局"] = "ការិយាល័យចុះសំបុត្រអាពាហ៍ពិពាហ៍"

        # 4. Revenge / Face-slapping / Underdog Triumph
        if re.search(r'打脸|逆袭|首富|神豪|扮猪吃虎|退婚|隐形首富|白眼狼|清算', raw_text_corpus):
            roles_detected.append("Revenge & Face-slapping / សងសឹកវាយបក")
            glossary["打脸"] = "ទះកំផ្លៀងមុខឱ្យបាក់មុខកណ្តាលវាល"
            glossary["逆袭"] = "ក្រោកឈរវាយបកយកជ័យជម្នះ"
            glossary["首富"] = "មហាសេដ្ឋីលំដាប់ប្រទេស"
            glossary["白眼狼"] = "មនុស្សរមិលគុណស៊ីបាយបោកឆ្នាំង"
            glossary["退婚"] = "ផ្តាច់ពាក្យបណ្តេញចេញ"

        # 5. Mother-in-Law Feud / Family In-Laws
        if re.search(r'婆婆|恶婆婆|丈母娘|扫地出门|断绝关系|家产|分家|彩礼', raw_text_corpus):
            roles_detected.append("Family In-Law Feud / ជម្លោះគ្រួសារម្តាយក្មេក")
            glossary["婆婆"] = "ម្តាយក្មេក"
            glossary["丈母娘"] = "ម្តាយក្មេក"
            glossary["扫地出门"] = "បណ្តេញក្បាលចេញពីផ្ទះ!"
            glossary["断绝关系"] = "កាត់កាលចោលឈប់រាប់អាន!"
            glossary["彩礼"] = "ថ្លៃបណ្ណាការជំនូន"

        # 6. Secret Pregnancy / Cute Baby / DNA Paternity Test
        if re.search(r'带球跑|萌宝|怀了|怀孕|打掉孩子|两道杠|亲子鉴定|野种|生父', raw_text_corpus):
            roles_detected.append("Secret Pregnancy / ពពោះកូនរត់គេចខ្លួន")
            glossary["带球跑"] = "ពពោះកូនរត់គេចខ្លួន"
            glossary["萌宝"] = "កូនឆ្លាតវៃ"
            glossary["亲子鉴定"] = "ការធ្វើតេស្ត DNA ឈាមជ័រឪពុកកូន"
            glossary["打掉孩子"] = "រំលូតកូនក្នុងពោះចោល"

        # 7. Ancient Costume / Palace Intrigue / Reincarnation / Cultivation
        if re.search(r'陛下|皇上|本宫|贵妃|臣妾|王爷|王妃|穿越|重生|修真|仙尊', raw_text_corpus):
            roles_detected.append("Ancient Palace / Reincarnation / រឿងបុរាណជាតិមុន")
            glossary["皇上"] = "ព្រះរាជា"
            glossary["陛下"] = "ព្រះករុណា"
            glossary["本宫"] = "យើងជាម្ចាស់ក្សត្រី"
            glossary["臣妾"] = "ទូលបង្គំជាម្ចាស់"
            glossary["王爷"] = "ទ្រង់ព្រះអង្គម្ចាស់"
            glossary["重生"] = "កើតឡើងវិញជាតិថ្មី"
            glossary["穿越"] = "ឆ្លងភពឆ្លងសម័យ"

        # Infer Character Roster
        roster = self.infer_character_roster(raw_text_corpus)

        # Merge names into glossary
        for char_key, char_info in roster.items():
            zh = char_info.get("name_zh", "")
            km = char_info.get("name_km", "")
            if zh and km and zh not in ("តួឯកប្រុស", "តួឯកស្រី", "តួឈ្នានីស", "ចាស់ទុំក្នុងគ្រួសារ"):
                glossary[zh] = km

        bible = {
            "series_id": series_id,
            "title": drama_title,
            "created_at": time.time(),
            "genre_tropes": roles_detected or ["Drama Dubbing"],
            "character_roster": roster,
            "male_lead": roster["male_lead"],
            "female_lead": roster["female_lead"],
            "villain_or_rival": roster["villain_or_rival"],
            "elder": roster["elder"],
            "glossary": glossary,
            "episode_summaries": {}
        }

        try:
            with open(bible_p, "w", encoding="utf-8") as f:
                json.dump(bible, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        self._cache[series_id] = bible
        return bible

    def get_character_glossary(self, drama_title: str) -> Dict[str, str]:
        """Return pure dictionary glossary for entity replacement & Nisay entity_glossary."""
        bible = self.get_or_create_series_bible(drama_title)
        return dict(bible.get("glossary", {}))

    def record_episode_summary(
        self,
        drama_title: str,
        episode_num: int,
        dialogues: List[Dict[str, Any]]
    ):
        """
        Record a concise synopsis of what happened in this episode
        so subsequent episodes retain emotional momentum and story memory.
        """
        if not dialogues:
            return

        series_id = sanitize_series_id(drama_title)
        bible = self.get_or_create_series_bible(drama_title)

        key_lines = []
        for d in dialogues[:15]:
            km = (d.get("text_km") or "").strip()
            if len(km) >= 6 and km not in key_lines:
                key_lines.append(km)
            if len(key_lines) >= 3:
                break

        summary = " | ".join(key_lines) if key_lines else "សាច់រឿងបន្តពីភាគមុន"
        bible["episode_summaries"][str(episode_num)] = summary[:220]

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
        villain = bible.get("villain_or_rival", {})
        glossary = bible.get("glossary", {})
        tropes = ", ".join(bible.get("genre_tropes", ["Drama"]))

        # Previous episode context if available
        context_str = ""
        if current_episode_num and current_episode_num > 1:
            prev_ep = current_episode_num - 1
            prev_sum = bible.get("episode_summaries", {}).get(str(prev_ep))
            if prev_sum:
                context_str = f"\n- PREVIOUS EPISODE (ភាគ {prev_ep}) RECAP: \"{prev_sum}\". Continue dialogue seamlessly with matching emotional tone!"

        glossary_items = [f"'{k}' ➔ '{v}'" for k, v in list(glossary.items())[:25]]
        glossary_str = f"\n- SERIES VOCABULARY & NAMES: {', '.join(glossary_items)}" if glossary_items else ""

        injection = f"""
=== 📖 MASTER DRAMA SERIES BIBLE & CHARACTER GRAPH (រក្សាឈ្មោះ និងតួនាទីតួអង្គត្រឹមត្រូវ ១០០% គ្រប់ភាគ) ===
Drama Series: 《{drama_title}》 (Theme: {tropes})
- MALE LEAD (តួឯកប្រុស): {m_lead.get('name_km', m_lead.get('name', 'តួប្រុស'))} (Voice: Piseth | Self: '{m_lead.get('pronoun_self', 'ខ្ញុំ')}', Calls Female Lead: '{m_lead.get('pronoun_call_female_lead', 'អូន')}')
- FEMALE LEAD (តួឯកស្រី): {f_lead.get('name_km', f_lead.get('name', 'តួស្រី'))} (Voice: Sreymom | Self: '{f_lead.get('pronoun_self', 'ខ្ញុំ')}', Calls Male Lead: '{f_lead.get('pronoun_call_male_lead', 'បង')}')
- VILLAIN / RIVAL (តួកាច): {villain.get('name_km', villain.get('name', 'តួឈ្នានីស'))} (Uses arrogant/hostile tone)
- RELATIONSHIP PRONOUNS: 
  * Spouses/Lovers: បង / អូន
  * Boss/Employee: លោកប្រធាន / ខ្ញុំ
  * Palace/Royalty: ព្រះរាជា / ទូលបង្គំ
  * Family In-laws: ម៉ាក់ក្មេក / កូន / កូនប្រសា
  * Adversaries/Fights: ឯង / យើង / អាគម្រក់ / មីស្រីពិសពុល
- STRICT CONSISTENCY: Maintain these exact character names and pronouns across ALL episodes! NEVER invent or alter names!{context_str}{glossary_str}
========================================================================================
"""
        return injection.strip()

    @staticmethod
    def infer_dialogue_emotion(text_km: str, text_orig: str = "") -> str:
        """
        Dynamically infer emotional tone of a dialogue line for natural voice modulation:
        - angry: shout, threat, confrontation (ខឹង/គំរាម)
        - sad: cry, heartbreak, begging (យំ/សោកសៅ)
        - tender: love, romantic, comfort (ផ្អែមល្ហែម/ស្នេហា)
        - panic: fear, urgency, alarm (ភ័យ/តក់ស្លុត)
        - authoritative: command, boss declaration (ម៉ឺងម៉ាត់/បញ្ជា)
        - neutral: standard conversational (ធម្មតា)
        """
        c = f"{text_km} {text_orig}".lower()

        # 1. Angry / Threat / Confrontation
        if any(w in c for w in ("បិទមាត់", "អាគម្រក់", "ចង់ងាប់", "ចេញទៅ", "ឆ្កួត", "ទះ", "សម្លាប់", "混蛋", "找死", "闭嘴", "滚", "弄死", "!")):
            if any(w in c for w in ("បិទមាត់", "អាគម្រក់", "ចង់ងាប់", "ចេញទៅ", "ឆ្កួត", "ទះ", "សម្លាប់", "混蛋", "找死", "闭嘴", "滚")):
                return "angry"

        # 2. Sad / Cry / Begging
        if any(w in c for w in ("សូមអង្វរ", "កុំទៅចោល", "អាណិត", "សុំទោស", "យំ", "ស្លាប់", "ឈឺចាប់", "求求", "呜呜", "放过", "对不起", "痛")):
            return "sad"

        # 3. Tender / Romance / Sweet
        if any(w in c for w in ("បងស្រឡាញ់អូន", "អូនស្រឡាញ់បង", "សម្លាញ់", "កុំបារម្ភ", "ស្រឡាញ់", "ប្តីសម្លាញ់", "ប្រពន្ធ", "爱", "宝贝", "乖", "别怕")):
            return "tender"

        # 4. Panic / Fear
        if any(w in c for w in ("ជួយផង", "ភ័យ", "តក់ស្លុត", "កើតអី", "មានរឿងអី", "救命", "快来人", "怎么回事")):
            return "panic"

        # 5. Authoritative / Boss
        if any(w in c for w in ("បញ្ជា", "លោកប្រធាន", "ចុះកិច្ចសន្យា", "ទិញយក", "រំលាយចោល", "给我查", "签了", "收购")):
            return "authoritative"

        return "neutral"


# Global singleton instance
series_memory = DramaSeriesMemory()
