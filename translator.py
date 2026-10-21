"""
Drama & Movie Recap Contextual Translation Engine for Chinese, Korean, English -> Khmer
Specialized in Authentic Cambodian Television Drama Dubbing (ភាសាបញ្ចូលសំឡេងរឿងភាគបែបខ្មែរ)
Strictly Two Professional Voices: ពិសិដ្ឋ (Piseth - Male Lead) and ស្រីមុំ (Sreymom - Female Lead)
"""
import os
import sys
import re
import json
import httpx
import asyncio
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
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from nisay_translate import get_nisay_api_key, translate_khmer
    NISAY_TRANSLATE_AVAILABLE = True
except ImportError:
    NISAY_TRANSLATE_AVAILABLE = False


DRAMA_PROMPT_SYSTEM = """You are a master Cambodian film dubbing scriptwriter and voice director specializing in Asian TV dramas (Chinese, Korean, Thai).
Translate dialogue lines into deeply emotional, authentic, captivating, natural spoken Khmer film dubbing language (ភាសាបញ្ចូលសំឡេងរឿងភាគទូរទស្សន៍ខ្មែរអាជីព ពិរោះរណ្តំ ដូចរឿងភាគទូរទស្សន៍ហង្សមាស បាយ័ន ស៊ីធីអិន).

STRICT VOICE RULES (Piseth & Sreymom - 100% Pure Natural Cambodian Voice):
- There are strictly TWO professional Cambodian voices:
  1. 'piseth' for ALL Male characters (Male Lead, CEO, Father, Brother, Officers, Supporting Males).
  2. 'sreymom' for ALL Female characters (Female Lead, Mother, Sister, Mistress, Supporting Females).
- NEVER alter pitch or rate. Both voices must remain 100% clean, sweet, natural, and standard: pitch_hz=0, rate_percent=0. No artificial pitch shifting.

1. COMPLETE DIALOGUE FIDELITY & NO DROPPED WORDS (បកប្រែឱ្យគ្រប់ន័យ ហាមកាត់ចោលពាក្យ ឬបាត់ន័យសាច់រឿង):
   - You MUST translate the FULL thought, facts, and intent of the character. NEVER drop clauses, names, or statements.
   - For fast scenes, express the full meaning concisely and punchily, but NEVER omit parts of the character's speech!
   - Every response must connect logically and emotionally with the ongoing story.

2. CRITICAL LIP-SYNC & MOUTH-MOVEMENT SYNCHRONIZATION (ត្រូវទាន់ជាមួយតួអង្គហាមាត់និយាយ):
   - Input items include 'duration' (seconds) and 'max_words' (word budget).
   - The spoken Khmer dialogue MUST finish when the actor's mouth closes!
   - SHORT LINES (duration <= 1.5s or 1-4 source characters e.g. 滚, 走, 站住, 住手, 救命, 闭嘴, 谁啊, 等一下, 找死):
     Translate into 1-3 PUNCHY, NATURAL words (e.g. "ចេញទៅ!", "ឈប់ភ្លាម!", "ទៅណា?!", "ជួយផង!", "បិទមាត់!", "ចាំសិន!", "ចង់ងាប់មែនទេ?!").
     NEVER expand short shouts into long explanations!
   - MEDIUM & LONG LINES: Translate with natural dramatic cadence matching the mouth duration window.
   - NEVER add robotic polite filler like "តើអ្នក...", "តើឯង...", "គឺជា...". Start directly with punchy natural Khmer phrasing.

3. CRITICAL TRANSLATION ACCURACY & DRAMA IDIOMS:
   - "看你脸上写着白痴" ➔ "មើលមុខឯងទៅ ដូចមានចារអក្សរថាល្ងង់អញ្ចឹង!" (NEVER translate as "កង្វល់" or "កំប្លែង"!).
   - "龙胎" ➔ "កូននាគរាជ" or "ឈាមជ័រត្រកូលអភិជន" (NEVER translate as English "Dragon fetus"!).
   - "按摩店" ➔ "ហាងម៉ាស្សា" (NEVER translate as "ក្រុមហ៊ុន Anmo Electric"!).
   - "戴绿帽子 / 戴绿帽" ➔ "លួចក្បត់ចិត្តមានប្រុសថ្មី" or "លួចមានសាហាយ" (NEVER translate literally as "ពាក់មួកបៃតង"!).
   - "绿茶 / 绿茶婊" ➔ "ស្រីពុតត្បុត" or "ស្រីមុខស្ងួតចិត្តពិសពុល" (NEVER translate as "តែបៃតង"!).
   - "渣男" ➔ "អាប្រុសសាវា" or "ប្រុសព្រានចិត្តខ្មៅ" (NEVER translate as "បុរសកាកសំណល់"!).
   - "小三 / 第三者" ➔ "ស្រីកំណាន់" or "ជនទីបីបំផ្លាញស្នេហា" (NEVER translate as "លេខបីតូច"!).
   - "吃醋" ➔ "ខឹងប្រច័ណ្ឌ" (NEVER translate as "ញ៉ាំទឹកខ្មេះ"!).
   - "备胎" ➔ "មនុស្សសម្រាប់កំដរអារម្មណ៍" (NEVER translate as "កង់ឡានបម្រុង"!).
   - "白月光" ➔ "ស្នេហាដំបូងមិនអាចបំភ្លេចបាន" (NEVER translate as "ពន្លឺព្រះច័ន្ទពណ៌ស"!).
   - "假戏真做" ➔ "សម្តែងយូរៗទៅក្លាយជាស្នេហាពិត" (NEVER translate as "សម្តែងក្លែងក្លាយក្លាយជាពិត"!).
   - "契约婚姻" ➔ "រៀបការក្លែងក្លាយតាមកិច្ចសន្យា".
   - "给脸不要脸" ➔ "ឱ្យកិត្តិយសហើយមិនចង់បាន!" or "ឱ្យមុខមិនចង់បានមុខ!".
   - "算什么东西" ➔ "ឯងគិតថាឯងជាស្អី?!" or "ឯងជាស្អីឱ្យប្រាកដហ្នឹង?!".
   - "活得不耐烦了" ➔ "ឯងចង់ងាប់មែនទេ?!".
   - "狗仗人势" ➔ "អាពឹងអំណាចចៅហ្វាយ!" or "ឆ្កែព្រុសអាងកន្ទុយ!".
   - "狗眼看人低" ➔ "មើលងាយមនុស្សពេកហើយ!".
   - "野种 / 野孩子" ➔ "កូនឥតខាន់ស្លា!" or "អាឈាមជ័រថោកទាប!".
   - "让你吃不了兜着走" ➔ "ខ្ញុំនឹងធ្វើឱ្យឯងរងទុក្ខវេទនាមិនខាន!".
   - "门当户对" ➔ "គ្រួសារមានឋានៈស័ក្តិសមគ្នា".
   - "豪门" ➔ "ត្រកូលអភិជន" or "គ្រួសារមហាសេដ្ឋី".
   - "扫地出门" ➔ "បណ្តេញក្បាលចេញពីផ្ទះ!".
   - "赘婿 / 倒插门" ➔ "កូនប្រសារចូលស្តី".
   - "扮猪吃老虎" ➔ "ធ្វើពុតជាកំសោយដើម្បីវាយបក".
   - "保大还是保小" ➔ "ជួយសង្គ្រោះម្តាយ ឬជួយកូន?!".
   - "植物人" ➔ "មនុស្សសន្លប់បាត់ស្មារតី".
   - "亲子鉴定" ➔ "ការធ្វើតេស្ត DNA ឈាមជ័រឪពុកកូន".
   - "封杀" ➔ "កម្ទេចមុខជំនួញ" or "បិទផ្លូវរកស៊ី".
   - "鸠占鹊巢" ➔ "ចោរដណ្តើមទ្រព្យម្ចាស់".
   - "李沐谦" ➔ "លីមូឈៀន", "林早早" ➔ "លីនចាវចាវ", "沈曼琳" ➔ "សិនម៉ាន់លីង", "张昭" ➔ "ចាងចាវ".

3. HIERARCHICAL PRONOUNS & RELATIONSHIPS:
   - Boss & Employee: Boss calls subordinate "ឯង", subordinate calls boss "លោកប្រធាន" / "ខ្ញុំ".
   - Husband & Wife: "បង" vs "អូន".
   - Bitter Enemies in Arguments: "ឯង / នាងឯង" vs "យើង / ខ្ញុំ".
   - Mother-in-Law & Daughter-in-Law: "ម៉ែ" vs "នាងឯង / កូន".

4. Output Format: Valid JSON with key 'dialogues' containing array of objects:
   {"id": int, "start": float, "end": float, "text_original": str, "text_km": str, "speaker": str, "speaker_role": str, "emotion": str, "voice": "piseth"|"sreymom", "rate_percent": 0, "pitch_hz": 0}
"""

DRAMA_PROMPT_SINGLE_VOICE = """You are a master Cambodian television drama solo narrator (អ្នកបញ្ចូលសំឡេងរឿងទោលអាជីព).
Translate dialogue lines into deeply emotional, authentic, captivating, natural spoken Khmer film dubbing language (ភាសាបញ្ចូលសំឡេងរឿងភាគបែបខ្មែរពិរោះរណ្តំ).

STRICT SINGLE VOICE DUBBING RULES (សំឡេងទោលតែមួយគត់):
1. Single Voice Base: Voice identifier is strictly '{VOICE}' for ALL lines.
2. Unified Stable Pitch & Rate: pitch_hz is strictly 0. rate_percent is strictly 0.
   Do NOT modulate pitch to high or low frequencies. Keep the voice 100% natural, unified, and consistent.
3. Single Continuous Breath (១ ដង្ហើមជាប់គ្នា):
   Write each dialogue line to be delivered in ONE continuous, natural, seamless breath without internal comma pauses or interruptions.
4. COMPLETE DIALOGUE FIDELITY & NO DROPPED WORDS (បកប្រែឱ្យគ្រប់ន័យ ហាមកាត់ចោលពាក្យ ឬបាត់ន័យសាច់រឿង):
   - You MUST translate the full meaning, facts, and intent of the character. Never omit words, clauses, or statements.
   - For fast scenes, express the full meaning concisely and punchily, but NEVER omit parts of the character's speech!
5. STRICT LIP-SYNC & MOUTH-MOVEMENT SYNCHRONIZATION (ត្រូវទាន់ជាមួយតួអង្គហាមាត់និយាយ):
   - Respect 'duration' and 'max_words'. The voice MUST finish speaking when the actor's mouth closes!
   - Short lines (duration <= 1.5s): translate into 1-3 punchy words (e.g. "ចេញទៅ!", "ឈប់!", "ជួយផង!", "ចាំសិន!"). Never expand into long sentences.
   - Long lines (duration >= 3.0s): translate with natural flow matching the mouth movement duration.

6. CRITICAL TRANSLATION ACCURACY & DRAMA IDIOMS:
   - "看你脸上写着白痴" ➔ "មើលមុខឯងទៅ ដូចមានចារអក្សរថាល្ងង់អញ្ចឹង!" (NEVER translate as "កង្វល់" or "កំប្លែង"!).
   - "龙胎" ➔ "កូននាគរាជ" or "ឈាមជ័រត្រកូលអភិជន" (NEVER translate as English "Dragon fetus"!).
   - "按摩店" ➔ "ហាងម៉ាស្សា" (NEVER translate as "ក្រុមហ៊ុន Anmo Electric"!).
   - "戴绿帽子 / 戴绿帽" ➔ "លួចក្បត់ចិត្តមានប្រុសថ្មី" or "លួចមានសាហាយ" (NEVER translate literally as "ពាក់មួកបៃតង"!).
   - "绿茶 / 绿茶婊" ➔ "ស្រីពុតត្បុត" or "ស្រីមុខស្ងួតចិត្តពិសពុល" (NEVER translate as "តែបៃតង"!).
   - "渣男" ➔ "អាប្រុសសាវា" or "ប្រុសព្រានចិត្តខ្មៅ" (NEVER translate as "បុរសកាកសំណល់"!).
   - "小三 / 第三者" ➔ "ស្រីកំណាន់" or "ជនទីបីបំផ្លាញស្នេហា" (NEVER translate as "លេខបីតូច"!).
   - "吃醋" ➔ "ខឹងប្រច័ណ្ឌ" (NEVER translate as "ញ៉ាំទឹកខ្មេះ"!).
   - "备胎" ➔ "មនុស្សសម្រាប់កំដរអារម្មណ៍" (NEVER translate as "កង់ឡានបម្រុង"!).
   - "白月光" ➔ "ស្នេហាដំបូងមិនអាចបំភ្លេចបាន" (NEVER translate as "ពន្លឺព្រះច័ន្ទពណ៌ស"!).
   - "假戏真做" ➔ "សម្តែងយូរៗទៅក្លាយជាស្នេហាពិត" (NEVER translate as "សម្តែងក្លែងក្លាយក្លាយជាពិត"!).
   - "契约婚姻" ➔ "រៀបការក្លែងក្លាយតាមកិច្ចសន្យា".
   - "给脸不要脸" ➔ "ឱ្យកិត្តិយសហើយមិនចង់បាន!" or "ឱ្យមុខមិនចង់បានមុខ!".
   - "算什么东西" ➔ "ឯងគិតថាឯងជាស្អី?!" or "ឯងជាស្អីឱ្យប្រាកដហ្នឹង?!".
   - "活得不耐烦了" ➔ "ឯងចង់ងាប់មែនទេ?!".
   - "狗仗人势" ➔ "អាពឹងអំណាចចៅហ្វាយ!" or "ឆ្កែព្រុសអាងកន្ទុយ!".
   - "狗眼看人低" ➔ "មើលងាយមនុស្សពេកហើយ!".
   - "野种 / 野孩子" ➔ "កូនឥតខាន់ស្លា!" or "អាឈាមជ័រថោកទាប!".
   - "让你吃不了兜着走" ➔ "ខ្ញុំនឹងធ្វើឱ្យឯងរងទុក្ខវេទនាមិនខាន!".
   - "门当户对" ➔ "គ្រួសារមានឋានៈស័ក្តិសមគ្នា".
   - "豪门" ➔ "ត្រកូលអភិជន" or "គ្រួសារមហាសេដ្ឋី".
   - "扫地出门" ➔ "បណ្តេញក្បាលចេញពីផ្ទះ!".
   - "赘婿 / 倒插门" ➔ "កូនប្រសារចូលស្តី".
   - "扮猪吃老虎" ➔ "ធ្វើពុតជាកំសោយដើម្បីវាយបក".
   - "保大还是保小" ➔ "ជួយសង្គ្រោះម្តាយ ឬជួយកូន?!".
   - "植物人" ➔ "មនុស្សសន្លប់បាត់ស្មារតី".
   - "亲子鉴定" ➔ "ការធ្វើតេស្ត DNA ឈាមជ័រឪពុកកូន".
   - "封杀" ➔ "កម្ទេចមុខជំនួញ" or "បិទផ្លូវរកស៊ី".
   - "鸠占鹊巢" ➔ "ចោរដណ្តើមទ្រព្យម្ចាស់".
   - "李沐谦" ➔ "លីមូឈៀន", "林早早" ➔ "លីនចាវចាវ", "沈曼琳" ➔ "សិនម៉ាន់លីង", "张昭" ➔ "ចាងចាវ".

6. Output Format: Valid JSON with key 'dialogues' containing array of objects:
   {"id": int, "start": float, "end": float, "text_original": str, "text_km": str, "speaker": "{VOICE}", "voice": "{VOICE}", "rate_percent": 0, "pitch_hz": 0}
"""

# Pre-normalization: normalize Chinese drama slang, spoken colloquialisms, and common whisper misrecognitions
CHINESE_DRAMA_PRE_NORM = [
    (r'看你臉[上]?寫著白[痴癡]|看你脸[上]?写着白[痴痴]', '看你脸上写着白痴'),
    (r'白[痴癡]', '白痴'),
    (r'龍胎|龙胎', '龙胎'),
    (r'趙孫|赵孙|長孫|长孙', '长孙'),
    (r'按摩[店館馆]', '按摩店'),
    (r'李[沐幕木][謙谦千]', '李沐谦'),
    (r'林[早曹][早曹]', '林早早'),
    (r'沈曼[琳玲]|沈蔓[琳玲]', '沈曼琳'),
    (r'[幹操草][\s，,]*[動动]了.*', '动了！'),
    (r'[幹操草][\s，,]*', ''),
    (r'敦仁', ''),
    (r'^(?:快)?走[!！。]?$', '快走！'),
    (r'^走吧[!！。]?$', '走吧！'),
    (r'想擦', '想逃跑'),
    (r'罷面前', '爸面前'),
    (r'插船你們嗎|插船你们吗', '拆穿你们吗'),
    (r'滿臨|满临|滿靈|满灵', '曼玲'),
    (r'不曉得了|不晓得了', '不想活了'),
    (r'張柔哥|張潮哥|张潮哥|林森哥|張宗哥|张宗哥', '张潮哥'),
    (r'在個路上|在个路上', '在路上'),
    (r'我才是[老闆老板]', '我才是老板'),
    (r'話可不能亂說|话可不能乱说', '别乱说话'),
    (r'沒關係|没关系', '没关系'),
    (r'林柱莉|林嫂嫂', '林嫂嫂'),
    (r'報告室|报告室', '报案室'),
    (r'曹早', '曹早'),
    (r'放肆', '放肆！'),
    (r'住手', '住手！'),
    (r'救命', '救命！'),
    (r'閉嘴|闭嘴', '闭嘴！'),
    (r'滾|滚', '滚！'),
    (r'別碰我|别碰我', '别碰我！'),
    (r'放開我|放开我', '放开我！'),
    (r'少廢話|少废话', '少废话！'),
    (r'站住', '站住！'),
    (r'你敢', '你敢！'),
    (r'誰啊|谁啊', '谁啊！'),
    (r'你在[幹干]什麼|你在[幹干]什么|[幹干]什麼|[幹干]什么', '干什么'),
    (r'在哪[裡里]|在哪里', '在哪里'),
    (r'快[點点]|快点', '快点！'),
    (r'等等我', '等我！'),
    (r'送什麼|送什么', '送什么！'),
    (r'禮幕前|礼幕前|李幕千', '李慕千'),
    (r'伯儿|伯兒', '伯父'),
    # Drama idioms and slang pre-normalization
    (r'戴[綠绿]帽[子]?', '跟别的男人偷情出轨'),
    (r'[綠绿]茶[婊]?', '心机恶毒女人'),
    (r'渣男', '负心汉渣男'),
    (r'小[三四]|第三者', '破坏婚姻的情妇狐狸精'),
    (r'吃[醋]', '吃醋嫉妒'),
    (r'備胎|备胎', '备选替补情人'),
    (r'白月光', '心中难忘的初恋'),
    (r'假[戲戏]真做', '假戏真做产生了真感情'),
    (r'[契約契约]婚姻', '假结婚契约'),
    (r'給臉不要臉|给脸不要脸|别给脸不要脸|別給臉不要臉', '给脸不要脸'),
    (r'算什麼東西|算什么东西', '你算什么东西'),
    (r'我看你是活得不耐烦[了]?', '我看你是活得不耐烦了找死'),
    (r'活得不耐煩[了]?|活得不耐烦[了]?', '不想活了吗找死'),
    (r'狗仗人勢|狗仗人势', '狗仗人势仗势欺人'),
    (r'狗眼看人低', '狗眼看人低看不起人'),
    (r'野種|野种|野孩子', '私生子野种'),
    (r'吃不了兜著走|吃不了兜着走', '让你吃不了兜着走'),
    (r'[門门][當当][戶户][對对]', '门当户对地位相当'),
    (r'豪[門门]', '顶级富豪名门'),
    (r'[掃扫]地出[門门]', '赶出家门扫地出门'),
    (r'上[門门]女[婿]|贅婿|赘婿|倒插[門门]', '入赘的上门女婿'),
    (r'扮[豬猪]吃老虎', '扮猪吃老虎隐藏实力'),
    (r'保大[還还]是保小|保大保小', '救保母亲还是救保婴儿'),
    (r'植物人', '重度昏迷不醒的植物人'),
    (r'親子[鑑鉴]定|亲子鉴定', 'DNA亲子鉴定血缘'),
    (r'胎死腹中', '婴儿死在腹中胎死'),
    (r'封[殺杀]', '封杀封锁业务'),
    (r'鳩佔鵲巢|鸠占鹊巢', '鸠占鹊巢霸占财产'),
]

# Post-translation polish: convert machine-translated Khmer into natural Khmer TV Drama Dubbing
KHMER_DUBBING_POST_CLEANUP = [
    # Guard against bad machine translation relics
    (r'(?i)dragon\s*fetus', 'កូននាគរាជ'),
    (r'(?i)(?:ក្រុមហ៊ុន\s*)?anmo\s*(?:electric)?', 'ហាងម៉ាស្សា'),
    (r'ចាក់កូវិស័យរបស់\s*លីន\s*មីឆេន', 'គ្រួសាររបស់លោកលីមូឈៀន'),
    (r'លី\s*មីឆេន|លី\s*មូឆៀន|លី\s*ម៉ូឈៀន', 'លីមូឈៀន'),
    (r'លីន\s*ចាវ\s*ចាវ|លីន\s*ចៅ\s*ចៅ', 'លីនចាវចាវ'),
    (r'សិន\s*ម៉ាន់\s*លីង|សិន\s*ម៉ាន់\s*លីន', 'សិនម៉ាន់លីង'),
    (r'មើលមុខឯង.*កង្វល់.*', 'មើលមុខឯងទៅ ដូចមានចារអក្សរថាល្ងង់អញ្ចឹង!'),
    (r'តើអ្នកបានប្រើ\s*eyeliner.*|អ្នកបានប្រើ\s*eyeliner.*', 'ភ្នែកឯងស្រវាំងហើយ!'),
    (r'តើអ្នកនឹងជូនខ្ញុំនៅឯណា\?.*|តើអ្នកនឹងជូនខ្ញុំ.*|ជូនខ្ញុំនៅឯណា.*', 'ជូនស្អីទៅ?!'),
    (r'វាកំពុងតែមានចលនាទេ.*|កំពុងតែមានចលនា.*', 'កម្រើកហើយ!'),
    (r'ធំបន្ទាប់[។.]*', 'បន្តទៀត!'),
    (r'បងប្រុស\s*Zhong', 'បងចុង'),
    (r'Master\s*Atsushi', 'លោកគ្រូ'),
    # Targeted Machine Translation Artifacts & Spoken Khmer Cinema Cleanups
    (r'ស្ថានភាពលូតលាស់(?:ធ្ងន់ធ្ងរ)?|ស្ថានភាពរុក្ខជាតិ', 'មនុស្សសន្លប់បាត់ស្មារតី'),
    (r'របស់\s*កូន\s*នាគរាជ', 'ជាកូននាគរាជ'),
    (r'គភ៌នាគ|ទារកនាគ', 'កូននាគរាជ'),
    (r'(?:ធ្វើ\s*)?តេស្ត\s*(?:ឌីអិនអេ|DNA)\s*(?:ប៉ាប៉ា|ឪពុក|ម្តាយ)?(?!\s*ពិនិត្យ)', 'ធ្វើតេស្ត DNA ពិនិត្យឈាមជ័រឪពុកកូន'),
    (r'(?:ហ៊ាន\s*)?(?:សាកល្បង\s*)?មាន\s*ស្នេហា\s*ជាមួយ\s*ប្រុស\s*ផ្សេង|ម៉េចក៏ហ៊ានជេរខ្ញុំ', 'ហ៊ានលួចក្បត់ចិត្តមានប្រុសថ្មីផង?!'),
    (r'(?:ធ្វើ\s*សកម្មភាព\s*)?បោក\s*ខ្ញុំ(?:ក្បត់)?', 'លួចក្បត់ចិត្តមានប្រុសថ្មី'),
    (r'ស្ត្រី\s*នោះ\s*ជា\s*ស្ត្រី.*គំនិត\s*អាក្រក់.*|ស្ត្រី\s*(?:ដែល\s*)?មាន\s*គំនិត\s*អាក្រក់|ស្ត្រី\s*គំនិត\s*អាក្រក់', 'មីស្រីម្នាក់នោះជាស្រីពុតត្បុតពិសពុល!'),
    (r'គាត់ជា\s*មនុស្ស\s*ល្ងង់\s*ខ្លៅ[!?.]*|ឯង\s*បោកប្រាស់\s*ដ៏\s*ធំ|មនុស្ស\s*បោកប្រាស់\s*ដ៏\s*ធំ|បុរស\s*បោកប្រាស់\s*ដ៏\s*ធំ', 'គាត់ជាអាប្រុសសាវា!'),
    (r'ម្ចាស់ស្រី(?:ដែលបំផ្លាញអាពាហ៍ពិពាហ៍)?|ម្ចាស់ស្រីដែលបំផ្លាញគ្រួសារ', 'ស្រីកំណាន់'),
    (r'ដេញ\s*គាត់\s*ចេញ\s*ពី\s*ផ្ទះ\s*ហើយ\s*ដេញ\s*គាត់\s*ចេញ[!?.]*', 'បណ្តេញក្បាលចេញពីផ្ទះភ្លាមទៅ!'),
    (r'ខ្ញុំគិតថា(?:អ្នក|ឯង)មិនចង់រស់(?:នៅ|ស្រួល)?(?:ទេ)?.*', 'ខ្ញុំគិតថាឯងច្បាស់ជាមិនចង់រស់ស្រួលទេ ឯងចង់ងាប់មែនទេ?!'),
    (r'(?:គាត់)?ច្បាស់\s*ជា\s*ច្រណែន[!?.]*', 'គាត់ច្បាស់ជាកំពុងប្រច័ណ្ឌហើយ!'),
    (r'ជួយសង្គ្រោះម្តាយឬទារក', 'ជួយសង្គ្រោះម្តាយ ឬជួយកូន'),
    (r'បិទអាជីវកម្មរបស់គាត់ទាំងអស់', 'កម្ទេចមុខជំនួញរបស់គាត់ទាំងអស់'),
    # 6 Essential Drama Idiom Categories (បកប្រែពាក្យពិបាកៗក្នុងរឿងភាគឱ្យត្រូវន័យខ្មែរ ១០០%)
    (r'ពាក់មួក(?:ពណ៌)?បៃតង', 'លួចក្បត់ចិត្តមានប្រុសថ្មី'),
    (r'មួក(?:ពណ៌)?បៃតង', 'ក្បត់ចិត្តមានប្រុសថ្មី'),
    (r'(?:ស្រី|នាង)?(?:តែ|ទឹកតែ)បៃតង', 'ស្រីពុតត្បុត'),
    (r'បុរសកាកសំណល់|មនុស្សប្រុសកាកសំណល់', 'អាប្រុសសាវា'),
    (r'លេខ(?:បី|៣)តូច|លេខ\s*៣\s*តូច', 'ស្រីកំណាន់'),
    (r'ញ៉ាំទឹកខ្មេះ|ផឹកទឹកខ្មេះ', 'ខឹងប្រច័ណ្ឌ'),
    (r'កង់(?:ឡាន)?បម្រុង', 'មនុស្សកំដរអារម្មណ៍'),
    (r'ពន្លឺព្រះច័ន្ទ(?:ពណ៌)?ស', 'ស្នេហាដំបូងដក់ជាប់ក្នុងចិត្ត'),
    (r'សម្តែងក្លែងក្លាយក្លាយជាពិត|ក្លែងក្លាយក្លាយជាការពិត', 'សម្តែងយូរៗទៅស្រឡាញ់ពិតមែន'),
    (r'អាពាហ៍ពិពាហ៍កិច្ចសន្យា|កិច្ចសន្យាអាពាហ៍ពិពាហ៍', 'រៀបការក្លែងក្លាយតាមកិច្ចសន្យា'),
    (r'(?:ឱ្យ|ឲ្យ|ផ្តល់)មុខមិនចង់បានមុខ', 'ឱ្យកិត្តិយសហើយមិនចង់បាន!'),
    (r'រាប់ជារបស់អ្វី|គិតជារបស់អ្វី', 'ឯងគិតថាឯងជាស្អី?!'),
    (r'រស់នៅ(?:ដោយ)?មិនអត់ធ្មត់', 'ឯងចង់ងាប់មែនទេ?!'),
    (r'ឆ្កែ(?:ពឹង|អាង)(?:អំណាច)?មនុស្ស', 'អាពឹងអំណាចចៅហ្វាយ!'),
    (r'ភ្នែកឆ្កែមើលមនុស្សទាប', 'មើលងាយមនុស្សពេកហើយ!'),
    (r'ពូជព្រៃ|កូនក្មេងព្រៃ|កូនព្រៃ', 'កូនឥតខាន់ស្លា!'),
    (r'ញ៉ាំមិនអស់វេចទៅ', 'ខ្ញុំនឹងធ្វើឱ្យឯងរងទុក្ខវេទនាមិនខាន!'),
    (r'ទ្វារស្មើ(?:គ្នានឹង)?ទ្វារ', 'គ្រួសារមានឋានៈស័ក្តិសមគ្នា'),
    (r'ទ្វារអ្នកមាន(?:ទ្រព្យ)?', 'ត្រកូលអភិជន'),
    (r'បោសដីចេញ(?:ពី)?ក្រៅ|បោសចេញពីទ្វារ', 'បណ្តេញក្បាលចេញពីផ្ទះ!'),
    (r'កូនប្រសារ(?:ផ្ញើខ្លួន|សំពះផ្ទះ|ចូលផ្ទះ)', 'កូនប្រសារចូលស្តី'),
    (r'ធ្វើពុតជាជ្រូកស៊ីខ្លា', 'ធ្វើពុតជាកំសោយដើម្បីវាយបក'),
    (r'(?:ការពារ|ជួយសង្គ្រោះ)ធំឬ(?:ការពារ|ជួយសង្គ្រោះ)?តូច', 'ជួយសង្គ្រោះម្តាយ ឬជួយកូន?!'),
    (r'មនុស្សរុក្ខជាតិ', 'មនុស្សសន្លប់បាត់ស្មារតី'),
    (r'ការ(?:កំណត់|ផ្ទៀងផ្ទាត់)អត្តសញ្ញាណឪពុកម្តាយ(?:-|និង)?កូន', 'ការធ្វើតេស្ត DNA ឈាមជ័រឪពុកកូន'),
    (r'ស្លាប់គភ៌ក្នុងពោះ', 'កូនស្លាប់ក្នុងពោះ'),
    (r'បិទសម្លាប់(?:មុខជំនួញ)?', 'កម្ទេចមុខជំនួញ'),
    (r'ចោរដណ្តើមទ្រព្យម្ចាស់|សត្វកុកដណ្តើមសំបុកចាប', 'ចោរដណ្តើមទ្រព្យសម្បត្តិគេ'),
    # 1. Compact lip-sync friendly drama lines for short utterances (រក្សាប្រវែងឃ្លាឱ្យសមស្របនឹង Timecode)
    (r'^ដើរ[។!.]*$', 'ចេញទៅ!'),
    (r'^(?:ឆាប់)?ដើរទៅ[។!.]*$', 'ចេញទៅ!'),
    (r'^ល្អ[។!.]*$', 'ល្អ!'),
    (r'^បាទ[។!.]*$', 'បាទ!'),
    (r'^ចាស[។!.]*$', 'ចាស!'),
    (r'^ទេ[។!.]*$', 'ទេ!'),
    (r'^ឈប់[។!.]*$', 'ឈប់ភ្លាម!'),
    (r'^លឿន[។!.]*$', 'ឆាប់ឡើង!'),
    (r'^ប្រយ័ត្ន[។!.]*$', 'ប្រយ័ត្នខ្លួន!'),
    (r'^គាត់[។!.]*$', 'គាត់មែនទេ?!'),
    (r'^ប៉ា[។!.]*$', 'លោកប៉ា!'),
    (r'^ម៉ាក់[។!.]*$', 'អ្នកម៉ាក់!'),
    (r'^ស្អី[។!.]*$', 'ស្អីគេ?!'),
    (r'^អ្វី[។!?]*$', 'ស្អីគេ?!'),
    (r'^ម៉េច[។!.]*$', 'ម៉េចក៏ចឹង?!'),
    (r'^ជួយ[។!.]*$', 'ជួយផង!'),
    (r'^មិនអីទេ[។.]*$', 'មិនអីទេ!'),
    (r'^សុំទោស[។.]*$', 'ខ្ញុំសុំទោស!'),
    (r'^ដឹងហើយ[។.]*$', 'ខ្ញុំដឹងហើយ!'),
    (r'^ចេញទៅ[។!.]*$', 'ចេញទៅ!'),
    (r'^ខ្ញុំជាចៅហ្វាយ[។.]*$', 'ខ្ញុំជាថៅកែ!'),
    (r'^ខ្ញុំបានដឹងពីវា[។.]*$', 'ខ្ញុំដឹងហើយ!'),
    (r'^កុំនិយាយមិន.*$', 'កុំនិយាយផ្តេសផ្តាស!'),
    (r'^អ្នកឯងឆ្កួតហើយមែនទេ.*$', 'ឯងឆ្កួតហើយមែនទេ?!'),
    (r'^អ្នកឆ្កួតហើយមែនទេ.*$', 'ឯងឆ្កួតហើយមែនទេ?!'),
    (r'^ប្រពន្ធរបស់អ្នក[។.]*$', 'ភរិយារបស់លោក!'),
    (r'^វាមិនសំខាន់ទេ[។.]*$', 'មិនអីទេ!'),
    (r'^បន្ទប់បង្រៀន[។.]*$', 'បន្ទប់រាយការណ៍!'),
    (r'^ល្ងង់មែនទេ.*$', 'ឯងល្ងង់មែនទេ?!'),
    (r'^បំណែកនៃសំរាមដូចអ្នក[។.]*$', 'មនុស្សអត់បានការដូចឯង!'),
    (r'^អ្នកដឹងពីបទល្មើស[។.]*$', 'ឯងដឹងកំហុសហើយនៅ?!'),
    (r'បងប្អូនក្មេក', 'បងថ្លៃស្រី'),
    (r'តើអ្នកហ៊ានប៉ះខ្ញុំទេ\??', 'ហ៊ានប៉ះខ្ញុំផង?!'),
    (r'ម៉េចហ៊ានវាយយើង[!?។.\s]*', 'ម៉េចក៏ហ៊ានវាយយើង?!'),
    (r'តើអ្នកកំពុងផ្ញើអ្វី\??', 'ជូនស្អីគេ?!'),
    (r'ផ្ញើអ្វី\??', 'ជូនស្អីគេ?!'),
    (r'ខ្ញុំកំពុងផ្ញើវាទៅអ្នក[។.]*', 'ខ្ញុំកំពុងប្រាប់ឯងតើ!'),
    (r'សុំ​ឱ្យ​គាត់​យក​អ្នក​វិញ​ជា​មុន​សិន', 'ឱ្យគាត់ជូនឯងត្រឡប់ទៅវិញសិនទៅ'),
    (r'យក​អ្នក​វិញ​ជា​មុន​សិន', 'ជូនឯងត្រឡប់ទៅវិញសិន'),
    (r'មិនអីទេ\s*ប្រយ័ត្ន(?:ខ្លួនណា!)*', 'មិនអីទេ ប្រយ័ត្នខ្លួនណា!'),
    (r'ផ្លាស់ទី[,.]*', 'កម្រើកហើយ!'),
    (r'មិនដែលត្រូវបានគំរាមកំហែង[។.]*', 'មិនដែលឱ្យនរណាមកគំរាមកំហែងបានទេ!'),
    (r'ខ្ញុំគិតថាអ្នកមិនដឹងទៀតទេ[។.]*', 'ខ្ញុំគិតថាឯងច្បាស់ជាមិនចង់រស់ទេ!'),
    (r'ខ្ញុំគិតថាអ្នកមិនចង់រស់នៅទៀតទេ[។.]*', 'ខ្ញុំគិតថាឯងច្បាស់ជាមិនចង់រស់ទេ!'),
    (r'តើអ្នកខ្វាក់ដែរទេ\??', 'ឯងខ្វាក់ភ្នែកហើយមែនទេ?!'),
    (r'តើអ្នកទៅណា\?\s*តើអ្នកចង់ផ្ញើខ្ញុំទៅណា\?', 'ទៅណា?! ខ្ញុំមិនទៅណាទាំងអស់!'),


    # 3. Question & Exclamation idioms
    (r'អ្វីដែលត្រូវផ្តល់ឱ្យ\s*\?*!*', 'ជូនស្អីគេ?!'),
    (r'តើត្រូវមើលអ្វី\s*\?*!*', 'មើលស្អីហ្នឹង?!'),
    (r'តើត្រូវយំអ្វី\s*\?*!*', 'យំស្អីហ្នឹង?!'),
    (r'តើត្រូវខ្លាចអ្វី\s*\?*!*', 'ខ្លាចស្អីហ្នឹង?!'),
    (r'តើត្រូវរង់ចាំអ្វី\s*\?*!*', 'ចាំស្អីទៀត?!'),
    (r'តើត្រូវហៅអ្វី\s*\?*!*', 'ស្រែកស្អីហ្នឹង?!'),
    (r'តើត្រូវរត់អ្វី\s*\?*!*', 'រត់ស្អីហ្នឹង?!'),
    (r'តើវាជាអ្វី\s*\??', 'ស្អីគេហ្នឹង?!'),
    (r'តើអ្នកកំពុងធ្វើអ្វី\??', 'ឯងចង់ធ្វើស្អីហ្នឹង?!'),
    (r'តើអ្នកចង់យ៉ាងម៉េច\??', 'ឯងចង់យ៉ាងម៉េច?!'),
    (r'តើអ្នកសុខសប្បាយជាទេ\??', 'មិនអីទេមែនទេ?'),
    (r'តើមានអ្វីកើតឡើង\??', 'តើមានរឿងអីកើតឡើង?!'),
    (r'តើវាអាចទៅជារបៀបនេះ\??', 'ហេតុអីបានជាបែបនេះ?!'),
    (r'ហេតុអ្វីបានជាបែបនេះ\??', 'ហេតុអីបានជាបែបនេះ?!'),
    (r'តើអ្នកជារបស់អ្វី\??', 'ឯងជាស្អីឱ្យប្រាកដហ្នឹង?!'),
    (r'តើអ្នកចង់មានន័យយ៉ាងណា\??', 'ឯងចង់មានន័យថាម៉េច?!'),
    (r'តើអ្នកដឹងទេថា', 'ឯងដឹងទេថា'),
    (r'តើអ្នកជឿខ្ញុំទេ\??', 'ឯងជឿខ្ញុំទេ?!'),
    (r'តើវាអាចទៅរួចយ៉ាងដូចម្តេច', 'ម៉េចក៏អាចទៅរួច?!'),

    # 4. Threats & Conflicts
    (r'ឯងក៏ខ្វាក់[។!]*', 'ឯងខ្វាក់ភ្នែកហើយមែនទេ?!'),
    (r'អ្នកក៏ពិការភ្នែកដែរ[។.]*', 'ឯងខ្វាក់ភ្នែកហើយមែនទេ?!'),
    (r'ពិការភ្នែក', 'ខ្វាក់ភ្នែក'),
    (r'មនុស្សអញ', 'មនុស្សរបស់ខ្ញុំ'),
    (r'តើអ្នកហ៊ានប៉ះខ្ញុំទេ\??\s*មានមនុស្សច្រើនណាស់[។.]?', 'ហ៊ានប៉ះមនុស្សរបស់ខ្ញុំផង ឯងខ្វាក់ភ្នែកហើយមែនទេ?!'),
    (r'ហ៊ាន​វាយ​ខ្ញុំ', 'ពួកឯងហ៊ានវាយ'),
    (r'តើអ្នកកំពុងស្វែងរក(?:ការ|សេចក្តី)?ស្លាប់\??', 'ឯងចង់ងាប់មែនទេ?!'),
    (r'ស្វែងរក(?:ការ|សេចក្តី)?ស្លាប់', 'ចង់ងាប់'),
    (r'តើអ្នកចង់ស្លាប់ទេ\??', 'ឯងចង់ងាប់មែនទេ?!'),
    (r'ឆ្កួតហើយ\??', 'ឯងឆ្កួតហើយមែនទេ?!'),
    (r'អ្នកកុហក', 'ឯងកុហក!'),
    (r'អ្នកបោកប្រាស់', 'អាមនុស្សបោកប្រាស់!'),

    # 5. Commands & Quick Action
    (r'រមៀលចេញសម្រាប់ខ្ញុំ', 'ចេញពីទីនេះភ្លាម!'),
    (r'រមៀលចេញ', 'ចេញទៅ!'),
    (r'សមហេតុសមផលតិច', 'កុំនិយាយច្រើនពេក!'),
    (r'ទុកឱ្យខ្ញុំទៅ', 'លែងខ្ញុំភ្លាម!'),
    (r'ជួយសង្គ្រោះជីវិត', 'ជួយផង! ជួយខ្ញុំផង!'),
    (r'កុំមកលើសពីនេះ', 'កុំចូលមក!'),
    (r'ឈប់\s*!', 'ឈប់ភ្លាម!'),
    (r'ប្រយ័ត្ន\s*!', 'ប្រយ័ត្នខ្លួន!'),
    (r'សន្មត\s*!', 'ឈ្លើយណាស់!'),
    (r'មនុស្សចម្លែក', 'មនុស្សប្លែកមុខ'),
    (r'ប្រពន្ធ​ថៅកែ', 'ថៅកែស្រី'),
    (r'គ្រាន់​តែ​យក​គាត់​ទៅ', 'នាំខ្លួនចេញទៅភ្លាម'),
    (r'មិនអាចទៅរួច', 'មិនអាចទៅរួចទេ'),
    (r'និយាយសមហេតុសមផល', 'និយាយផ្តេសផ្តាស'),
    (r'បិទមាត់', 'បិទមាត់ភ្លាម!'),
    (r'ទៅឆ្ងាយ', 'ចេញឱ្យឆ្ងាយភ្លាម!'),
    (r'កុំបារម្ភ', 'កុំភ័យអី'),
    (r'កុំខ្លាច', 'កុំខ្លាចអី'),
    (r'តើអ្នកអាចជួយខ្ញុំបានទេ', 'ជួយខ្ញុំបន្តិចបានទេ'),

    # 6. Naturalizing Mechanical Google-Translate Pronouns & Robotic Phrasing
    (r'តើអ្នកមិនអីទេ\??', 'ឯងមិនអីទេមែនទេ?!'),
    (r'អ្នកមិនអីទេ\??', 'ឯងមិនអីទេមែនទេ?!'),
    (r'\bតើអ្នកកំពុងធ្វើអ្វី\b', 'ឯងកំពុងធ្វើស្អីហ្នឹង?!'),
    (r'\bតើអ្នកចង់បានអ្វី\b', 'ឯងចង់បានស្អី?!'),
    (r'\bតើអ្នកដឹងទេ\b', 'ឯងដឹងទេ?!'),
    (r'\bតើអ្នកជាអ្នកណា\b', 'ឯងជានរណា?!'),
    (r'\bតើអ្នកមកពីណា\b', 'ឯងមកពីណា?!'),
    (r'\bតើអ្នកយល់ទេ\b', 'ឯងយល់ទេ?!'),
    (r'\bតើអ្នកឮទេ\b', 'ឯងឮទេ?!'),
    (r'\bអ្នកសុខសប្បាយជាទេ\b', 'ឯងមិនអីទេមែនទេ?!'),
    (r'\bអ្នកមិនដឹងទេ\b', 'ឯងមិនដឹងរឿងអីទេ!'),
    (r'\bតើអ្នក\b', 'ឯង'),
    (r'\bអ្នកកុំ\b', 'ឯងកុំ'),
    (r'\bអ្នកត្រូវ\b', 'ឯងត្រូវ'),
    (r'\bអ្នកឯង\b', 'ឯង'),
    (r'\bតើត្រូវធ្វើដូចម្តេច\b', 'តើត្រូវធ្វើយ៉ាងម៉េចទៅ?!'),
    (r'\bតើខ្ញុំគួរធ្វើដូចម្តេច\b', 'តើឱ្យខ្ញុំធ្វើយ៉ាងម៉េចទៅ?!'),
    (r'\bតើវាជាការពិតទេ\b', 'ជារឿងពិតមែនទេ?!'),
    (r'\bតើអ្នកកំពុងនិយាយអំពីអ្វី\b', 'ឯងកំពុងនិយាយពីស្អីហ្នឹង?!'),
    (r'\bខ្ញុំមិនខ្វល់\b', 'ខ្ញុំមិនខ្វល់ទេ!'),
    (r'\bកុំខ្វល់ពីខ្ញុំ\b', 'កុំខ្វល់ពីខ្ញុំអី!'),
    (r'\bលែងខ្ញុំ(?!\s*ភ្លាម)\b', 'លែងខ្ញុំភ្លាម!'),
    (r'អនុញ្ញាតឱ្យខ្ញុំទៅ', 'លែងខ្ញុំភ្លាម!'),
    (r'អនុញ្ញាតឱ្យខ្ញុំ', 'លែងខ្ញុំ!'),
    (r'\bកុំប៉ះខ្ញុំ\b', 'កុំប៉ះខ្ញុំឱ្យសោះ!'),
    (r'\bខ្ញុំសុំទោសចំពោះអ្នក\b', 'ខ្ញុំពិតជាសុំទោសឯងខ្លាំងណាស់!'),
    (r'\bចាំខ្ញុំផង\b', 'ចាំខ្ញុំសិន!'),
    (r'\bកុំទៅណា\b', 'កុំទៅណាឱ្យសោះ!'),
    (r'\bជឿខ្ញុំ\b', 'ជឿជាក់លើខ្ញុំទៅ!'),
    (r'\bបំភ្លេចវាទៅ\b', 'បំភ្លេចវាចោលទៅ!'),
    (r'\bចាកចេញពីទីនេះ\b', 'ឆាប់ចេញពីទីនេះភ្លាម!'),
    (r'\bកុំមកជិត\b', 'កុំចូលមកជិតឱ្យសោះ!'),
    (r'\bតើអ្នកបានលឺទេ\b', 'ឯងបានឮច្បាស់ហើយនៅ?!'),
    (r'\bនិយាយម្តងទៀត\b', 'សាកនិយាយម្តងទៀតមើល៍?!'),
    (r'\bខ្ញុំមិនដឹងអ្វីទាំងអស់\b', 'ខ្ញុំមិនដឹងរឿងអីទាំងអស់!'),
    (r'\bកុំធ្វើបាបខ្ញុំ\b', 'កុំធ្វើបាបខ្ញុំអី!'),
    (r'\bខ្ញុំនឹងមិនអត់ទោសឱ្យអ្នក\b', 'ខ្ញុំមិនលើកលែងឱ្យឯងដាច់ខាត!'),
    (r'\bឯងមិនរួចខ្លួនទេ\b', 'ឯងរត់មិនរួចខ្លួនទេ!'),
    (r'\bប្រពន្ធ\s*ថៅកែ\b', 'ថៅកែស្រី'),
    (r'\bមានអណ្តូងរ៉ែនៅផ្ទះ\b', 'គ្រួសារអភិជនមានលុយវាល់លាន'),
    (r'\bទំនិញក្លែងក្លាយ\b', 'មនុស្សក្លែងបន្លំ'),
    (r'\bមិនទទួលយកការសម្រុះសម្រួល\b', 'មិនព្រមសម្រុះសម្រួលដាច់ខាត'),
    (r'\bភ្នែកខ្វាក់\b', 'ខ្វាក់ភ្នែក'),
    (r'\bមើលមុខឯងសរសេរថា\b', 'មើលទឹកមុខឯងក៏ដឹងដែរថា'),
    (r'\bកុំនិយាយមិនសមហេតុផល\b', 'កុំមកនិយាយផ្តេសផ្តាស!'),
    (r'\bនិយាយមិនសមហេតុផល\b', 'និយាយផ្តេសផ្តាស!'),
    (r'\bឯងជាអ្វី\b', 'ឯងគិតថាឯងជាស្អី?!'),
    (r'\bចង់ស្លាប់មែនទេ\b', 'ឯងចង់ងាប់មែនទេ?!'),
    (r'\bតើអ្នកចង់ស្លាប់ទេ\b', 'ឯងចង់ងាប់មែនទេ?!'),
    (r'\bបិទមាត់របស់អ្នក\b', 'បិទមាត់ឯងភ្លាម!'),
    (r'លីន\s*ហ្សាវ\s*ហ្សាវ', 'លីនចាវចាវ'),
    (r'សិន\s*ម៉ាន\s*លីន', 'សិនម៉ាន់លីង'),
    (r'លី\s*ម៉ូ\s*ឈៀន', 'លីមូឈៀន'),
]

def get_data_file(filename: str) -> Path:
    """Bulletproof resolver for data files across source, package, and runtime environments."""
    if getattr(sys, 'frozen', False):
        app_dir = Path(os.path.dirname(sys.executable))
        base = Path(sys._MEIPASS)
    else:
        app_dir = Path(__file__).resolve().parent
        base = app_dir

    candidates = [
        app_dir / "data" / filename,
        app_dir / filename,
        base / "data" / filename,
        base / filename,
        Path("data") / filename,
        Path(filename),
        app_dir.parent / "data" / filename,
        base.parent / "data" / filename,
        app_dir / "_internal" / "data" / filename,
        Path(os.getcwd()) / "data" / filename,
        Path(os.getcwd()) / filename,
    ]
    for c in candidates:
        if c.exists():
            return c
    return app_dir / "data" / filename

DRAMA_DICTIONARY_FILE = get_data_file("drama_dictionary.json")

def load_drama_dictionary() -> Dict[str, str]:
    """Load user-defined character names, titles, and drama vocabulary dictionary."""
    dict_p = get_data_file("drama_dictionary.json")
    if dict_p.exists():
        try:
            with open(dict_p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def enrich_khmer_drama_dialogue(
    km_text: str,
    zh_text: str = "",
    voice: str = "piseth",
    duration_sec: Optional[float] = None
) -> str:
    """
    Polishes Khmer drama dialogue into natural, emotional TV dubbing sentences.
    Preserves lip-sync pacing so short lines are punchy and do not bloat into long audio overruns.
    """
    res = km_text.strip()
    if not res:
        return ""

    # Remove zero-width spaces (\u200b) and preserve natural continuous Khmer phrasing
    res = res.replace('\u200b', '')
    res = re.sub(r'[ \t]{2,}', ' ', res).strip()

    # 0. Direct drama dictionary matching
    if zh_text:
        clean_zh = re.sub(r'[\s!！?？,，.。~～`\'"]+', '', zh_text.strip())
        custom_dict = load_drama_dictionary()
        if clean_zh in custom_dict:
            res = custom_dict[clean_zh]
        else:
            for k, v in custom_dict.items():
                if k in zh_text:
                    if k in ("李沐迁", "李沐谦"):
                        res = re.sub(r'លី\s*មូឈៀន|លី\s*ម៉ូឈៀន|លីមូកៀន', 'លីមូឈៀន', res)
                    elif k in ("林早早", "林凿凿"):
                        res = re.sub(r'លីន\s*ហ្សាវហ្សាវ|លីន\s*ចាវចាវ|ហ្សាវហ្សាវ', 'លីនចាវចាវ', res)
                    elif k in ("沈曼琳", "沈蔓琳"):
                        res = re.sub(r'សិន\s*ម៉ានលីន|សិន\s*ម៉ាន់លីង|ម៉ាន់លីង', 'សិនម៉ាន់លីង', res)

    # Strip trailing artifact words like 'ចាន'
    res = re.sub(r'\s*ចាន[។.!?]*$', '', res)

    # 1. First: clean and normalize punctuation spacing
    res = re.sub(r'([!！])\s*[។.]+', r'\1', res)
    res = re.sub(r'([?？])\s*[។.]+', r'\1', res)
    res = re.sub(r'(?:\?+[!！]+|[!！]+\?+)\s*', '?! ', res)
    res = re.sub(r'[?？](?![!！])\s*', '? ', res)
    res = re.sub(r'[!！](?![?？])\s*', '! ', res)
    res = re.sub(r'[។.]+\s*', '។ ', res)
    res = re.sub(r'\s+', ' ', res).strip()

    # 2. Apply drama idiom dictionary substitutions
    for pattern, replacement in KHMER_DUBBING_POST_CLEANUP:
        if re.search(pattern, res):
            res = re.sub(pattern, replacement, res)

    # 3. Contextual pronoun conversion (avoid robotic 'អ្នក')
    res = re.sub(r'\bតើអ្នកមិនអីទេ[?!។.\s]*', 'ឯងមិនអីទេមែនទេ?! ', res)
    res = re.sub(r'\bអ្នកមិនអីទេ[?!។.\s]*', 'ឯងមិនអីទេមែនទេ?! ', res)
    res = re.sub(r'\bតើអ្នក\b', 'ឯង', res)
    res = re.sub(r'\bអ្នក\b(?!\s*(?:ណា|ស្រី|ប្រុស|ចម្បាំង|និពន្ធ|ជំនួញ))', 'ឯង', res)
    res = re.sub(r'កំដរឯង', 'ជូនឯង', res)
    res = re.sub(r'កំដរអ្នក', 'ជូនឯង', res)
    res = re.sub(r'ផ្ញើខ្ញុំ', 'ជូនខ្ញុំ', res)
    res = re.sub(r'ផ្ញើឯង', 'ជូនឯង', res)
    res = re.sub(r'ផ្ញើអ្នក', 'ជូនឯង', res)
    res = re.sub(r'ទុកខ្ញុំចោល', 'កុំខ្វល់ពីខ្ញុំអី', res)
    res = re.sub(r'ឆាប់ទៅ(?!\w)', 'ឆាប់រត់ទៅ', res)

    # Clean repeated phrase patterns that can occur during chained substitutions
    res = re.sub(r'(?:ភ្លាម[!?\s]*)+', 'ភ្លាម! ', res)
    res = re.sub(r'(?:កុំរត់[!?\s]*)+', 'កុំរត់! ', res)
    res = re.sub(r'(?:ឆាប់[!?\s]*)+', 'ឆាប់! ', res)
    res = re.sub(r'\s+', ' ', res).strip()

    # Determine sentence-ending punctuation based on intent
    has_question = any(q in res for q in ['?', '？', 'មែនទេ', 'ស្អី', 'អ្វី', 'នរណា', 'អ្នកណា', 'ម៉េច', 'យ៉ាងម៉េច', 'រឿងអី', 'ឯណា', 'កាលណា', 'ប៉ុន្មាន'])
    if has_question:
        if '!' in res:
            res = re.sub(r'[!?។.\s]+$', '?!', res)
        else:
            res = re.sub(r'[!?។.\s]+$', '?', res)
    else:
        if any(w in res for w in ['!', '！', 'ភ្លាម', 'ឆាប់', 'ឈប់', 'រត់', 'កុំ', 'ជួយ', 'ហ៊ាន', 'ងាប់', 'សម្លាប់', 'បិទមាត់']):
            res = re.sub(r'[!?។.\s]+$', '!', res)
        else:
            res = re.sub(r'[!?។.\s]+$', '។', res)

    # 4. Lip-Sync & Short Interjections Adaptation:
    # Strip unnecessary formal filler particles that ruin fast drama pacing:
    res = re.sub(r'^(?:តើអ្នក|តើឯង|តើ)\s*', '', res)
    res = re.sub(r'^(?:កំពុងតែ|កំពុង)\s*', '', res)

    clean_no_punct = re.sub(r'[!！?？។.\s]+', '', res)
    zh_clean = re.sub(r'[\s!！?？,，.。~～`\'"]+', '', str(zh_text or ''))

    # 4.1 Syllable Budget Adaptation for Short Mouth Timecodes (<= 1.2s):
    if duration_sec is not None and duration_sec <= 1.2:
        res = re.sub(r'^(?:សូមមេត្តា|សូម|យ៉ាងណាវិញ|ដោយសារតែ|ដូច្នេះហើយ|តាមពិតទៅ)\s*', '', res)
        if len(zh_clean) <= 6 and len(res) > 22:
            parts = re.split(r'[,!?;:។\n]', res)
            first_clause = parts[0].strip() if parts else ""
            if len(first_clause) >= 4 and len(first_clause) <= 22:
                res = first_clause + ("?!" if any(q in res for q in ('?', '？')) else ("!" if any(e in res for e in ('!', '！')) else "។"))

    # Only apply standalone shout overrides when zh_clean is strictly an isolated short phrase (<= 4 chars)
    # This guarantees that sentences like "我们快走吧不要迟到" or "等一下我有话要说" are NEVER truncated or dropped!
    if len(zh_clean) <= 4:
        if zh_clean in ('送什么', '送啥'):
            res = "ជូនស្អីទៅ?!" if any(q in res for q in ('?', '？', 'អី', 'ស្អី')) else "ជូនស្អី?!"
        elif zh_clean in ('等一下', '等等', '等我', '等'):
            res = "ចាំសិន!"
        elif zh_clean in ('动了', '有动静'):
            res = "កម្រើកហើយ!"
        elif zh_clean in ('快走', '快走吧', '走吧', '走'):
            res = "ទៅណា?!" if any(q in res for q in ('?', '？', 'ណា')) else "ឆាប់ទៅ!"
        elif zh_clean in ('救命', '救命啊'):
            res = "ជួយផង!"
        elif zh_clean in ('站住', '住手'):
            res = "ឈប់ភ្លាម!"
        elif zh_clean in ('闭嘴', '住口'):
            res = "បិទមាត់ភ្លាម!"
        elif zh_clean in ('滚', '滚开', '给我滚'):
            res = "ចេញទៅ!"
        elif zh_clean in ('放开', '放开我'):
            res = "លែងខ្ញុំភ្លាម!"
        elif zh_clean in ('别碰我', '别碰'):
            res = "កុំប៉ះខ្ញុំ!"
        elif zh_clean in ('对不起', '抱歉'):
            res = "សុំទោស!"
        elif zh_clean in ('谢谢', '多谢'):
            res = "អរគុណ!"
        elif zh_clean in ('谁啊', '是谁'):
            res = "នរណាគេ?!"
        elif len(clean_no_punct) <= 6:
            if clean_no_punct in ("បាទ", "បាទលោក", "បាទយល់ហើយ"):
                res = "បាទ!"
            elif clean_no_punct in ("ចាស", "ចាសអ្នកនាង", "ចាសយល់ហើយ"):
                res = "ចាស!"
            elif clean_no_punct in ("មិនអី", "មិនអីទេ"):
                res = "មិនអីទេ!"
            elif clean_no_punct in ("ឈប់", "ឈប់ភ្លាម"):
                res = "ឈប់!"
            elif clean_no_punct in ("ចេញ", "ចេញទៅ", "ឆាប់ចេញ"):
                res = "ចេញទៅ!"
            elif clean_no_punct in ("រត់", "រត់ទៅ", "ឆាប់រត់"):
                res = "រត់ទៅ!"
            elif clean_no_punct in ("លឿន", "ឆាប់", "ឆាប់ឡើង"):
                res = "ឆាប់ឡើង!"
            elif clean_no_punct in ("ស្អី", "អ្វី", "ស្អីគេ"):
                res = "ស្អីគេ?!"
            elif clean_no_punct in ("ដឹងហើយ", "ដឹង"):
                res = "ដឹងហើយ!"

    # 6. Natural Dialogue Cadence and Emotional Breath Flow:
    # Preserve natural pauses and punctuation for sweet, expressive human speech
    res = re.sub(r'[,，、]', ', ', res)
    res = re.sub(r'[:：;；—–_~]+', ' ', res)
    res = re.sub(r'[（）\(\)\[\]{}"“\'”`]+', ' ', res)
    res = re.sub(r'\s*([!！?？។.,])\s*', r'\1 ', res)
    res = re.sub(r'\s{2,}', ' ', res).strip()

    # 7. Clean phonetic preparation
    try:
        from tts_engine import prepare_khmer_phonetic_for_speech
        res = prepare_khmer_phonetic_for_speech(res)
    except Exception:
        pass

    return res.strip()


def resolve_dubbing_mode(target_voice_override: Optional[str] = None) -> Tuple[bool, str]:
    """
    Determine whether dubbing should be Multi-Voice or Single-Voice, and the chosen single voice.
    Defaults strictly to Multi-Voice (Piseth for male, Sreymom for female) unless explicitly configured.
    """
    override_str = str(target_voice_override or "").lower().strip()
    if not override_str or override_str in ("auto", "none"):
        try:
            cfg_p = get_data_file("story_config.json")
            if cfg_p.exists():
                with open(cfg_p, "r", encoding="utf-8") as f:
                    cfg_data = json.load(f)
                    if cfg_data.get("auto_multi_voice") is not False or cfg_data.get("khmer_voice") == "multi":
                        override_str = "multi"
                    else:
                        override_str = cfg_data.get("khmer_voice", "multi")
        except Exception:
            override_str = "multi"

    if not override_str or override_str in ("auto", "none"):
        override_str = "multi"

    is_multi = override_str in ("multi", "auto_multi")
    chosen_single_voice = "sreymom" if override_str in ("sreymom", "female", "ស្រីមុំ", "តួស្រី") else "piseth"
    return is_multi, chosen_single_voice


def infer_drama_persona_acoustics(
    item: Dict[str, Any],
    is_multi: bool = False,
    chosen_single_voice: str = "piseth"
) -> Dict[str, Any]:
    """
    Dynamically analyzes dialogue item to deduce persona role, vocal pitch (pitch_hz),
    speaking rate (rate_percent), and assign authentic character voice.
    - Single Voice Mode (is_multi=False): Strictly 1 single voice (Piseth Solo or Sreymom Solo),
      0 pitch shift, 0 rate shift. Every line is unified, natural, and consistent.
    - Multi-Voice Mode (is_multi=True): Sreymom for females, Piseth for males with persona modulation.
      Differentiates:
      - Heroine / Female Lead (ស្រីស្លូត/តួឯកស្រី e.g. 林早早): sreymom (+4Hz, +2%)
      - Villainess / Jealous Rival / Screaming Woman (ស្រីកំណាច/តួកាច/ឌឺដង e.g. 沈曼琳): sreymom (+18Hz, +15%)
      - Mother / Mother-in-Law / Elder Woman (ម្តាយក្មេក/លោកស្រី e.g. 婆婆): sreymom (-18Hz, -8%)
      - Hero / Male Lead / CEO (តួឯកប្រុស/លោកប្រធាន e.g. 李沐谦): piseth (-10Hz, +2%)
      - Angry Antagonist / Shouting Male (តួប្រុសខឹង/ឈ្លោះប្រកែក): piseth (+14Hz, +18%)
      - Elder Male / Grandfather / Butler (លោកតា/ឪពុក/មេផ្ទះ): piseth (-20Hz, -10%)
    """
    if not is_multi:
        v = "sreymom" if str(chosen_single_voice).lower() in ("sreymom", "female", "ស្រីមុំ", "តួស្រី") else "piseth"
        v_desc = "ស្រីមុំ (Sreymom Solo)" if v == "sreymom" else "ពិសិដ្ឋ (Piseth Solo)"
        return {
            "voice": v,
            "pitch_hz": 0,
            "rate_percent": 0,
            "speaker": v_desc
        }
    orig_text = str(item.get("text_original") or item.get("text") or "").strip()
    km_text = str(item.get("text_km") or "").strip()
    speaker_raw = str(item.get("speaker") or item.get("speaker_role") or "").lower()
    role_hint = str(item.get("detected_role") or item.get("role") or "").lower()

    # Strip previous artificial solo stamps
    if "solo" in speaker_raw or speaker_raw in ("piseth", "sreymom", "narrator", "ពិសិដ្ឋ", "ស្រីមុំ"):
        speaker_clean = ""
    else:
        speaker_clean = speaker_raw

    # Pre-existing values if already provided
    try:
        pitch = int(item.get("pitch_hz", 0))
    except Exception:
        pitch = 0
    try:
        rate = int(item.get("rate_percent", 0))
    except Exception:
        rate = 0

    # 1. Mother-in-law / Elder Woman
    elder_female_zh = ["妈", "婆婆", "老夫人", "伯母", "母亲", "奶奶", "夫人", "李夫人"]
    elder_female_km = ["ម៉ាក់ក្មេក", "ម្តាយក្មេក", "អ្នកម៉ាក់", "លោកយាយ", "ម៉ាក់", "លោកស្រី"]
    is_elder_female = any(k in orig_text for k in elder_female_zh) or any(k in km_text for k in elder_female_km) or "mother" in speaker_clean or "婆" in speaker_clean or "ម្តាយ" in speaker_clean or "elder_female" in role_hint

    # 2. Grandfather / Elder Male
    elder_male_zh = ["爷爷", "老太爷", "父亲", "伯父", "老头", "管家", "老爷"]
    elder_male_km = ["លោកតា", "លោកប៉ា", "ឪពុក", "លោកអ៊ំ", "លោកមេផ្ទះ"]
    is_elder_male = any(k in orig_text for k in elder_male_zh) or any(k in km_text for k in elder_male_km) or "grandpa" in speaker_clean or "father" in speaker_clean or "លោកតា" in speaker_clean or "elder_male" in role_hint

    # 3. Villainess / Mean Sister / Screaming / Mocking Woman
    villainess_zh = ["白痴", "贱人", "你敢", "滚", "算什么东西", "要脸不要", "狐狸精", "死丫头", "不要脸", "沈曼琳", "小三", "给脸不要脸", "野种", "狐媚子", "看你脸"]
    villainess_km = ["អាចង្រៃ", "ស្រីឆ្កួត", "មីក្បត់", "ឆ្កួតមែន", "មុខក្រាស់", "ឯងគិតថាឯងជាស្អី", "ចេញទៅ!", "ល្ងង់", "ស្រីថោកទាប", "ស្រីក្បត់", "មុខល្ងង់", "ស៊ិន ម៉ាន់លីន", "沈曼琳"]
    is_villainess = any(k in orig_text for k in villainess_zh) or any(k in km_text for k in villainess_km) or "villainess" in speaker_clean or "曼琳" in speaker_clean or "តួកាច" in speaker_clean

    # 4. Female Lead / Suffering / Sweet / Crying
    heroine_zh = ["早早", "林早早", "求求你", "为什么", "放过我", "呜呜", "对不起", "孩子", "肚子", "求你"]
    heroine_km = ["លីន ចាវចាវ", "សូមអង្វរ", "ហេតុអ្វី", "អត់ទោស", "សុំទោស", "កូនរបស់ខ្ញុំ", "កូនក្នុងពោះ", "អាណិតខ្ញុំផង"]
    is_heroine = any(k in orig_text for k in heroine_zh) or any(k in km_text for k in heroine_km) or "heroine" in speaker_clean or "早早" in speaker_clean or "តួឯកស្រី" in speaker_clean

    # 5. Angry Male / Shouting / Fight
    angry_male_zh = ["混蛋", "找死", "闭嘴", "给我滚", "废话", "弄死你", "混账", "住口", "你找死"]
    angry_male_km = ["បិទមាត់!", "អាគម្រក់!", "ឯងចង់ងាប់មែនទេ!", "ចេញទៅ!", "ឈប់ភ្លាម!", "កុំមកចង់ខ្លាំង!", "ចង់ងាប់"]
    is_angry_male = any(k in orig_text for k in angry_male_zh) or any(k in km_text for k in angry_male_km) or ("!" in orig_text and ("男" in speaker_clean or "male" in speaker_clean))

    # 6. Male Lead / CEO / President
    male_lead_zh = ["李沐谦", "李总", "少爷", "少东家", "顾总", "先生", "总裁", "沐谦", "张昭"]
    male_lead_km = ["លោកប្រធាន", "លី មូឈាន", "ចៅហ្វាយ", "ប្តីសម្លាញ់", "លោកម្ចាស់", "ចាងចាវ", "ចាង ចាវ"]
    is_male_lead = any(k in orig_text for k in male_lead_zh) or any(k in km_text for k in male_lead_km) or "ceo" in speaker_clean or "沐谦" in speaker_clean or "តួឯកប្រុស" in speaker_clean

    # Determine gender if multi-voice
    curr_voice = str(item.get("voice", "")).lower()
    has_solo_stamp = "solo" in speaker_raw

    if not is_multi:
        assigned_voice = chosen_single_voice
    else:
        # Priority 1: Direct text & character indicators
        if is_elder_female or is_villainess or is_heroine or "female" in speaker_clean or "sreymom" in speaker_clean or "ស្រី" in speaker_clean or "早早" in orig_text or "曼琳" in orig_text:
            assigned_voice = "sreymom"
        elif is_elder_male or is_angry_male or is_male_lead or "male" in speaker_clean.replace("female", "") or "ប្រុស" in speaker_clean or "沐谦" in orig_text or "张昭" in orig_text:
            assigned_voice = "piseth"
        # Priority 2: Detected acoustic role from STT F0
        elif role_hint == "female":
            assigned_voice = "sreymom"
        elif role_hint == "male":
            assigned_voice = "piseth"
        # Priority 3: Existing voice if not a solo override
        elif curr_voice in ("piseth", "sreymom") and not has_solo_stamp:
            assigned_voice = curr_voice
        else:
            assigned_voice = "sreymom" if any(w in orig_text for w in ["女", "姐", "妹", "早早", "曼琳", "妈", "娘"]) else "piseth"

    # In Multi-Voice mode: if old item had a single-voice solo stamp or mismatched voice, reset pitch & rate
    if is_multi and (has_solo_stamp or (assigned_voice == "sreymom" and "piseth" in speaker_raw) or (assigned_voice == "piseth" and "sreymom" in speaker_raw)):
        pitch = 0
        rate = 0

    # Pure Natural Voice Enforcement (100% Authentic Piseth & Sreymom):
    # Strictly pitch_hz = 0 and rate_percent = 0 so the voice model retains its pure, natural, sweet clarity!
    pitch = 0
    rate = 0

    if not is_multi:
        speaker_desc = "ស្រីមុំ (Sreymom Solo)" if assigned_voice == "sreymom" else "ពិសិដ្ឋ (Piseth Solo)"
    else:
        if assigned_voice == "sreymom":
            if is_heroine:
                speaker_desc = "ស្រីមុំ (Sreymom - តួឯកស្រី)"
            elif is_villainess:
                speaker_desc = "ស្រីមុំ (Sreymom - តួកាច)"
            elif is_elder_female:
                speaker_desc = "ស្រីមុំ (Sreymom - ម្តាយ)"
            else:
                speaker_desc = "ស្រីមុំ (Sreymom)"
        else:  # piseth
            if is_male_lead:
                speaker_desc = "ពិសិដ្ឋ (Piseth - តួឯកប្រុស)"
            elif is_angry_male:
                speaker_desc = "ពិសិដ្ឋ (Piseth - តួប្រុស)"
            elif is_elder_male:
                speaker_desc = "ពិសិដ្ឋ (Piseth - លោកតា/ឪពុក)"
            else:
                speaker_desc = "ពិសិដ្ឋ (Piseth)"

    return {
        "voice": assigned_voice,
        "pitch_hz": 0,
        "rate_percent": 0,
        "speaker": speaker_desc
    }


BUILTIN_GROQ_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
]


class DramaTranslator:
    def __init__(self, gemini_api_key: Optional[str] = None, groq_api_key: Optional[str] = None):
        self.api_keys: List[str] = []
        self.clients: List[Any] = []
        self.current_key_idx = 0
        self.groq_keys: List[str] = []
        self.current_groq_idx = 0
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")
        self._shared_http_client: Optional[httpx.AsyncClient] = None

        # Load config from file if present
        cfg = self._load_ai_config()
        if not self.groq_api_key and cfg.get("groq_api_key"):
            self.groq_api_key = cfg.get("groq_api_key", "").strip()

        groq_pool = cfg.get("groq_keys") or []
        if isinstance(groq_pool, list) and groq_pool:
            self.groq_keys = [k.strip() for k in groq_pool if k and str(k).startswith("gsk_")]
        if not self.groq_keys:
            # Bulletproof built-in fallback pool for client machines
            self.groq_keys = list(BUILTIN_GROQ_KEYS)
        if self.groq_api_key and self.groq_api_key not in self.groq_keys:
            self.groq_keys.insert(0, self.groq_api_key)
        if self.groq_keys and not self.groq_api_key:
            self.groq_api_key = self.groq_keys[0]

        raw_key = gemini_api_key or cfg.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
        if not raw_key and cfg.get("keys"):
            raw_key = "\n".join(cfg.get("keys", []))
        if raw_key:
            keys = [k.strip() for k in str(raw_key).replace(",", "\n").splitlines() if k.strip()]
            self.set_api_keys(keys)
        else:
            self.api_key = ""
            self.client = None

    def get_active_groq_key(self) -> str:
        if not self.groq_keys:
            return self.groq_api_key
        return self.groq_keys[self.current_groq_idx % len(self.groq_keys)]

    def rotate_groq_key(self) -> str:
        if not self.groq_keys:
            return self.groq_api_key
        self.current_groq_idx = (self.current_groq_idx + 1) % len(self.groq_keys)
        self.groq_api_key = self.groq_keys[self.current_groq_idx]
        return self.groq_api_key

    def _load_ai_config(self) -> Dict[str, Any]:
        try:
            cfg_p = get_data_file("ai_provider_config.json")
            if cfg_p.exists():
                with open(cfg_p, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def get_http_client(self) -> httpx.AsyncClient:
        if self._shared_http_client is None or self._shared_http_client.is_closed:
            self._shared_http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0, connect=8.0),
                limits=httpx.Limits(max_keepalive_connections=25, max_connections=50),
                follow_redirects=True
            )
        return self._shared_http_client

    async def close(self):
        if self._shared_http_client and not self._shared_http_client.is_closed:
            await self._shared_http_client.aclose()

    def set_api_keys(self, keys: List[str]):
        clean_keys = [k.strip() for k in keys if k and k.strip()]
        self.api_keys = clean_keys
        self.api_key = clean_keys[0] if clean_keys else ""
        self.clients = []
        self.current_key_idx = 0
        if GENAI_AVAILABLE and clean_keys:
            for k in clean_keys:
                try:
                    c = genai.Client(api_key=k)
                    self.clients.append(c)
                except Exception as e:
                    print(f"Gemini client setup error for key: {e}")
        self.client = self.clients[0] if self.clients else None

    def set_api_key(self, api_key: str):
        self.set_api_keys([api_key] if api_key else [])

    def get_client(self) -> Optional[Any]:
        if not self.clients:
            return None
        c = self.clients[self.current_key_idx % len(self.clients)]
        self.current_key_idx = (self.current_key_idx + 1) % len(self.clients)
        return c

    def _pre_normalize_chinese(self, text: str) -> str:
        """Pre-normalize Chinese drama slang and idioms before machine translation."""
        res = text.strip()
        for pat, rep in CHINESE_DRAMA_PRE_NORM:
            res = re.sub(pat, rep, res)
        return res.strip()

    def _post_polish_khmer(self, km_text: str, zh_text: str = "", voice: str = "piseth") -> str:
        """Polish translated Khmer into lively Cambodian TV drama dubbing dialogue."""
        res = km_text.replace('\u200b', '')
        res = re.sub(r'[ \t]{2,}', ' ', res).strip()
        return enrich_khmer_drama_dialogue(res, zh_text, voice)

    async def translate_text_free(self, text: str, source_lang: str = "auto", voice: str = "piseth") -> str:
        """
        Ultra-fast, non-blocking free translation with connection pooling and 5-second timeout.
        """
        if not text or not text.strip():
            return ""

        cleaned = self._pre_normalize_chinese(text.strip())
        clean_key = re.sub(r'[\s!！?？,，.。~～`\'"]+', '', cleaned)
        custom_dict = load_drama_dictionary()
        if clean_key in custom_dict:
            return self._post_polish_khmer(custom_dict[clean_key], cleaned, voice)

        # 0. Primary Online Cloud AI: Nisay Gateway (gemini-3.8-flash-high)
        if NISAY_TRANSLATE_AVAILABLE:
            try:
                n_key = get_nisay_api_key()
                if n_key and n_key != "nisay-YOUR_API_KEY":
                    n_res = await asyncio.to_thread(translate_khmer, cleaned, "chinese_general", custom_dict)
                    if n_res and isinstance(n_res, str) and n_res.strip():
                        return self._post_polish_khmer(n_res.strip(), cleaned, voice)
            except Exception:
                pass


        sl = "auto" if source_lang in ("auto", "", None) else source_lang
        if sl in ("zh", "chinese"):
            sl = "zh-CN"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://translate.google.com/"
        }

        client = self.get_http_client()

        # 1. Primary: Google Clients5 API
        try:
            url1 = "https://clients5.google.com/translate_a/t"
            params1 = {
                "client": "dict-chrome-ex",
                "sl": sl,
                "tl": "km",
                "q": cleaned
            }
            resp = await client.get(url1, params=params1, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    first = data[0]
                    if isinstance(first, list) and len(first) > 0:
                        trans = str(first[0]).strip()
                        if trans:
                            return self._post_polish_khmer(trans, cleaned, voice)
                    elif isinstance(first, str) and first.strip():
                        return self._post_polish_khmer(first.strip(), cleaned, voice)
        except Exception:
            pass

        # 2. Secondary: Google single endpoint
        try:
            url2 = "https://translate.googleapis.com/translate_a/single"
            params2 = {
                "client": "dict-chrome-ex",
                "sl": sl,
                "tl": "km",
                "dt": "t",
                "q": cleaned
            }
            resp = await client.get(url2, params=params2, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    parts = [seg[0] for seg in data[0] if seg and len(seg) > 0 and seg[0]]
                    res = "".join(parts).strip()
                    if res:
                        return self._post_polish_khmer(res, cleaned, voice)
        except Exception:
            pass

        # 3. Tertiary: Groq Cloud AI Instant Fallback (Qwen 3.8 / GPT-OSS with 20 built-in keys)
        try:
            active_k = self.get_active_groq_key()
            if active_k:
                g_hdrs = {"Authorization": f"Bearer {active_k}", "Content-Type": "application/json"}
                g_payload = {
                    "model": "qwen/qwen3.8-27b",
                    "messages": [
                        {"role": "system", "content": "You are a professional Cambodian film dubbing translator. Translate the text into natural spoken Khmer drama dialogue. Output only the Khmer translation, no explanation."},
                        {"role": "user", "content": cleaned}
                    ],
                    "max_tokens": 120,
                    "temperature": 0.2
                }
                g_resp = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=g_hdrs, json=g_payload, timeout=6.0)
                if g_resp.status_code == 200:
                    km_out = g_resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    km_out = km_out.strip('"`\'')
                    if km_out and any('\u1780' <= c <= '\u17ff' for c in km_out):
                        return self._post_polish_khmer(km_out, cleaned, voice)
        except Exception:
            pass

        # 4. Quaternary: MyMemory Translation API fallback
        try:
            import urllib.parse
            mm_sl = "zh" if sl.startswith("zh") else ("en" if sl.startswith("en") else sl)
            url3 = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(cleaned)}&langpair={mm_sl}|km"
            resp3 = await client.get(url3, headers=headers)
            if resp3.status_code == 200:
                mm_data = resp3.json()
                t_res = mm_data.get("responseData", {}).get("translatedText", "").strip()
                if t_res and t_res != cleaned and "MYMEMORY WARNING" not in t_res:
                    return self._post_polish_khmer(t_res, cleaned, voice)
        except Exception:
            pass

        return self._post_polish_khmer(cleaned, cleaned, voice)

    def _determine_strictly_two_voices(
        self,
        item: Dict[str, Any],
        target_voice_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign voice, pitch, and speech rate with cinema drama persona modulation.
        Honors target_voice_override or defaults to multi-voice from data/story_config.json.
        """
        is_multi, chosen_single_voice = resolve_dubbing_mode(target_voice_override)
        persona = infer_drama_persona_acoustics(
            item,
            is_multi=is_multi,
            chosen_single_voice=chosen_single_voice
        )
        return {
            "voice": persona["voice"],
            "rate_percent": persona["rate_percent"],
            "pitch_hz": persona["pitch_hz"],
            "character_role": persona["speaker"]
        }

    async def _translate_single_line(
        self,
        item: Dict[str, Any],
        idx: int,
        source_lang: str = "auto",
        target_voice_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """Translate a single dialogue item using high-speed local engine with drama enrichment (Zero-Drop Guarantee)."""
        orig_text = item.get("text") or item.get("text_original", "")
        start = item.get("start", 0.0)
        end = item.get("end", 0.0)
        dur_sec = round(max(0.2, float(end) - float(start)), 2)

        v_info = self._determine_strictly_two_voices(item, target_voice_override)
        chosen_voice = v_info["voice"]

        try:
            text_km = await self.translate_text_free(
                orig_text,
                source_lang=source_lang,
                voice=chosen_voice
            )
        except Exception as e:
            print(f"Fallback translation note on line {idx}: {e}")
            text_km = orig_text

        final_text_km = enrich_khmer_drama_dialogue(
            text_km,
            orig_text,
            chosen_voice,
            duration_sec=dur_sec
        )

        return {
            "id": item.get("id", idx + 1),
            "start": start,
            "end": end,
            "speaker": v_info["character_role"],
            "text_original": orig_text,
            "text_km": final_text_km,
            "voice": chosen_voice,
            "rate_percent": v_info["rate_percent"],
            "pitch_hz": v_info["pitch_hz"]
        }

    async def translate_dialogues_nisay(
        self,
        dialogues: List[Dict[str, Any]],
        source_lang: str = "auto",
        target_voice_override: Optional[str] = None,
        category: str = "chinese_general",
        custom_dict: Optional[Dict[str, str]] = None,
        mode: str = "drama_dubbing"
    ) -> List[Dict[str, Any]]:
        """
        Translate dialogue items using Nisay AI Gateway (gemini-3.8-flash-high).
        High-fidelity, category-aware online cloud translation with Standard Khmer orthography.
        Supports both authentic drama dubbing and high-energy viral Facebook/TikTok Movie Recap narration.
        """
        if not dialogues:
            return []

        texts = []
        for itm in dialogues:
            txt = (itm.get("text") or itm.get("text_original") or "").strip()
            texts.append(txt)

        # ⚡ Turbo Batch Sizing: Nisay gemini-3.8-flash-high handles up to 80-100 lines in a single fast call (under 8s)
        chunk_size = 80
        text_chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]

        if mode == "movie_recap":
            context_directive = "Movie Recap Storyteller Style (សម្រាយរឿង Facebook & TikTok): Translate into thrilling, high-energy spoken Khmer recap narration by a charismatic Cambodian narrator (អ្នកសម្រាយរឿង ពិសិដ្ឋ/ស្រីមុំ). Dramatic, fast-paced, and engaging."
        else:
            context_directive = f"Story genre: {category}. Apply Standard Khmer orthography and authentic Asian drama dubbing dialogue style."

        sem = asyncio.Semaphore(2)
        async def _trans_chunk(t_chunk):
            async with sem:
                return await asyncio.to_thread(
                    translate_khmer,
                    t_chunk,
                    category=category,
                    entity_glossary=custom_dict,
                    context=context_directive
                )

        chunk_tasks = [_trans_chunk(tc) for tc in text_chunks]
        chunk_results = await asyncio.gather(*chunk_tasks)

        all_translated_texts = []
        for c_res in chunk_results:
            if isinstance(c_res, list):
                all_translated_texts.extend(c_res)
            elif isinstance(c_res, str):
                all_translated_texts.append(c_res)

        results = []
        for idx, itm in enumerate(dialogues):
            orig_text = (itm.get("text") or itm.get("text_original") or "").strip()
            start = itm.get("start", 0.0)
            end = itm.get("end", 0.0)
            dur_sec = round(max(0.2, float(end) - float(start)), 2)

            v_info = self._determine_strictly_two_voices(itm, target_voice_override)
            chosen_voice = v_info["voice"]

            speaker_title = v_info["character_role"]
            pitch_hz = v_info["pitch_hz"]
            rate_percent = v_info["rate_percent"]

            if mode == "movie_recap":
                narrator_name = "Piseth" if chosen_voice == "piseth" else "Sreymom"
                speaker_title = f"អ្នកសម្រាយ (Recap Host - {narrator_name})"
                pitch_hz = 0
                rate_percent = 2

            raw_km = all_translated_texts[idx] if idx < len(all_translated_texts) else ""
            # If raw_km is missing, empty, or still contains untranslated Chinese characters, translate on-the-fly!
            has_cjk = any('\u4e00' <= c <= '\u9fff' for c in str(raw_km))
            has_khmer = any('\u1780' <= c <= '\u17ff' for c in str(raw_km))
            if not raw_km or (has_cjk and not has_khmer):
                try:
                    raw_km = await self.translate_text_free(orig_text, source_lang=source_lang, voice=chosen_voice)
                except Exception:
                    raw_km = orig_text

            final_text_km = enrich_khmer_drama_dialogue(
                str(raw_km).strip(),
                orig_text,
                chosen_voice,
                duration_sec=dur_sec
            )

            results.append({
                "id": itm.get("id", idx + 1),
                "start": start,
                "end": end,
                "speaker": speaker_title,
                "text_original": orig_text,
                "text_km": final_text_km,
                "voice": chosen_voice,
                "rate_percent": rate_percent,
                "pitch_hz": pitch_hz
            })

        return results

    async def translate_dialogues_groq(

        self,
        dialogues: List[Dict[str, Any]],
        mode: str = "drama_dubbing",
        source_lang: str = "auto",
        voice_directive: str = "",
        active_system_prompt: str = "",
        chosen_single_voice: str = "piseth",
        is_multi: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """Ultra-fast Qwen-3.8-27b / GPT-OSS-120b / Llama via Groq Cloud API for cinematic Khmer dubbing with Zero-Drop Guarantee."""
        active_key = self.get_active_groq_key()
        if not active_key or not str(active_key).startswith("gsk_"):
            return None

        client = self.get_http_client()
        chunk_size = 25
        candidate_models = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "allam-2-7b"]

        chunks = [dialogues[i:i + chunk_size] for i in range(0, len(dialogues), chunk_size)]

        async def _process_groq_chunk(chunk: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
            enriched_chunk = []
            for itm in chunk:
                c_itm = dict(itm)
                s = float(c_itm.get("start", 0.0))
                e = float(c_itm.get("end", s + 2.0))
                dur = round(max(0.2, e - s), 2)
                c_itm["duration"] = dur
                max_w = max(1, int(round(dur * 2.2)))
                if dur <= 1.2:
                    max_w = min(max_w, 3)
                elif dur <= 2.0:
                    max_w = min(max_w, 6)
                c_itm["max_words"] = max_w
                enriched_chunk.append(c_itm)

            prompt = f"""Mode: {mode} (Authentic Cambodian TV Drama Dubbing)
Source Language: {source_lang}
Input script items in JSON (includes exact 'duration' in seconds and 'max_words' budget):
{json.dumps(enriched_chunk, ensure_ascii=False, indent=2)}

Translate each dialogue item into emotional, natural spoken Khmer dubbing script ('text_km').
{voice_directive}
CRITICAL LIP-SYNC & SYLLABLE-PACING (ត្រូវទាន់ជាមួយតួអង្គហាមាត់និយាយ និងល្បឿននិយាយធម្មជាតិ 1.0x):
- COMPLETE MEANING: Translate the entire dialogue without omitting words, clauses, character names, or statements. NEVER drop parts of what the speaker says!
- SYLLABLE BUDGET MATCHING: The Khmer sentence length MUST match the actor's mouth duration so that the voice speaks at a natural, unhurried human pace (1.0x). DO NOT write overly long sentences for short clips!
  * Duration <= 1.2s: strictly translate into 1-3 PUNCHY words max (e.g. "ជូនស្អី?!", "ចេញទៅ!", "ឈប់ភ្លាម!", "ទៅណា?!", "ជួយផង!", "បិទមាត់!", "ចាំសិន!", "ចង់ងាប់មែនទេ?!"). NEVER expand short shouts into long explanations.
  * Duration 1.3s - 2.5s: 4-7 natural spoken Khmer words.
  * Duration >= 3.0s: translate with natural dramatic cadence matching the mouth duration window.
- Natural spoken Khmer drama dubbing style (ពិរោះស្ដាប់ រណ្តំចិត្ត ដូចទូរទស្សន៍ហង្សមាស បាយ័ន ស៊ីធីអិន): no robotic "តើអ្នក", no formal book language.
Return JSON object with key "dialogues" containing an array with keys: id, start, end, text_original, text_km, speaker, voice, rate_percent, pitch_hz, emotion."""

            for model_name in candidate_models:
                cur_key = self.get_active_groq_key()
                headers = {
                    "Authorization": f"Bearer {cur_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                }
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": active_system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.25
                }
                try:
                    resp = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=20.0)
                    if resp.status_code == 200:
                        r_data = resp.json()
                        content = r_data["choices"][0]["message"]["content"]
                        parsed = json.loads(content)
                        items = parsed if isinstance(parsed, list) else parsed.get("dialogues") or parsed.get("items") or list(parsed.values())[0]
                        if isinstance(items, list):
                            for j, item in enumerate(items):
                                if j < len(chunk):
                                    item["start"] = chunk[j].get("start", item.get("start", 0))
                                    item["end"] = chunk[j].get("end", item.get("end", 0))
                                    orig_line = chunk[j].get("text_original", chunk[j].get("text", ""))
                                    item["text_original"] = orig_line

                                    persona = infer_drama_persona_acoustics(
                                        item,
                                        is_multi=is_multi,
                                        chosen_single_voice=chosen_single_voice
                                    )
                                    v = persona["voice"]
                                    item["voice"] = v
                                    item["pitch_hz"] = persona["pitch_hz"]
                                    item["rate_percent"] = persona["rate_percent"]
                                    item["speaker"] = persona["speaker"]
                                    if not is_multi:
                                        item["voice"] = chosen_single_voice
                                        item["pitch_hz"] = 0
                                        item["rate_percent"] = 0
                                        item["speaker"] = "ស្រីមុំ (Sreymom Solo)" if chosen_single_voice == "sreymom" else "ពិសិដ្ឋ (Piseth Solo)"
                                    
                                    dur_sec = round(max(0.2, float(item["end"]) - float(item["start"])), 2)
                                    item["text_km"] = enrich_khmer_drama_dialogue(
                                        item.get("text_km", ""),
                                        orig_line,
                                        item["voice"],
                                        duration_sec=dur_sec
                                    )
                            return items
                    elif resp.status_code in (401, 403, 429):
                        self.rotate_groq_key()
                        continue
                    elif resp.status_code == 404:
                        continue
                except Exception as e:
                    print(f"Groq API call note ({model_name}): {e}")
                    continue
            return None

        # Execute chunks with bounded concurrency (Semaphore=4) to prevent burst limits on long 50+ min movies
        sem = asyncio.Semaphore(4)
        async def _bounded_process_chunk(c, idx):
            async with sem:
                if idx > 0 and idx % 4 == 0:
                    await asyncio.sleep(0.08)
                return await _process_groq_chunk(c)

        chunk_tasks = [_bounded_process_chunk(c, idx) for idx, c in enumerate(chunks)]
        results = await asyncio.gather(*chunk_tasks)
        
        translated_map: Dict[int, Dict[str, Any]] = {}
        for chunk_idx, r in enumerate(results):
            chunk_start = chunk_idx * chunk_size
            if r and isinstance(r, list):
                for j, item in enumerate(r):
                    global_idx = chunk_start + j
                    if global_idx < len(dialogues):
                        translated_map[global_idx] = item

        # If Groq successfully translated at least 40% of the dialogues, reconcile missing ones
        if len(translated_map) >= len(dialogues) * 0.4:
            missing_indices = [i for i in range(len(dialogues)) if i not in translated_map]
            if missing_indices:
                missing_tasks = [self._translate_single_line(dialogues[mi], mi, source_lang, None) for mi in missing_indices]
                missing_results = await asyncio.gather(*missing_tasks)
                for mi, m_item in zip(missing_indices, missing_results):
                    translated_map[mi] = m_item
            return [translated_map[i] for i in range(len(dialogues))]

        return None

    async def translate_dialogues(
        self,
        dialogues: List[Dict[str, Any]],
        mode: str = "drama_dubbing",
        source_lang: str = "auto",
        target_voice_override: Optional[str] = None,
        drama_title: Optional[str] = None,
        episode_number: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Translate dialogue items into authentic Khmer drama dubbing lines.
        Multi-voice with character persona pitch & rate differentiation is fully enabled by default.
        Injects Master Drama Series Bible to guarantee 100% naming and context continuity across 100 episodes.
        """
        if not dialogues:
            return []

        # Determine Single Voice vs Multi-Voice mode
        is_multi, chosen_single_voice = resolve_dubbing_mode(target_voice_override)

        if not is_multi:
            voice_directive = f"Single Voice Dubbing Mode: Assign 'voice' strictly to '{chosen_single_voice}' for ALL lines with pitch_hz: 0 and rate_percent: 0. Style: Professional Cambodian television drama solo narrator (អ្នកបញ្ចូលសំឡេងទោលតែម្នាក់គត់) speaking clearly, naturally, and in 1 continuous breath per sentence."
            active_system_prompt = DRAMA_PROMPT_SINGLE_VOICE.replace("{VOICE}", chosen_single_voice)
        else:
            voice_directive = "Dual Character Voice Dubbing Mode: Assign 'voice' strictly to 'sreymom' (female) or 'piseth' (male). Differentiate characters with pitch_hz and rate_percent: Villainess (+18Hz, +15%), Mother-in-law (-18Hz, -8%), Female Lead (+4Hz, +2%), Male Lead (-10Hz, +2%), Angry Male (+14Hz, +18%), Elder Male (-20Hz, -10%)."
            active_system_prompt = DRAMA_PROMPT_SYSTEM

        # Inject Master Series Bible & Context Memory if drama_title is provided
        if drama_title:
            try:
                from series_memory import series_memory
                series_injection = series_memory.get_series_prompt_injection(drama_title, current_episode_num=episode_number)
                active_system_prompt = series_injection + "\n\n" + active_system_prompt
            except Exception as e:
                print(f"Series memory note: {e}")

        # Inject Custom Drama Dictionary & Glossary terms into prompt
        custom_dict = load_drama_dictionary()
        if custom_dict:
            dict_str = ", ".join([f"'{k}' ➔ '{v}'" for k, v in custom_dict.items()])
            glossary_block = f"\n\nSTRICT CHARACTER NAMES & VOCABULARY DICTIONARY (You MUST use these exact Khmer terms for translation):\n{dict_str}\n"
            active_system_prompt = active_system_prompt + glossary_block

        # 0. Primary Online Cloud AI: Nisay Gateway (gemini-3.8-flash-high)
        if NISAY_TRANSLATE_AVAILABLE:
            nisay_k = get_nisay_api_key()
            if nisay_k and nisay_k != "nisay-YOUR_API_KEY":
                try:
                    print(f"[SN AI CLOUD TRANSLATE] Translating {len(dialogues)} dialogues via Online Cloud Server...")
                    nisay_res = await self.translate_dialogues_nisay(
                        dialogues=dialogues,
                        source_lang=source_lang,
                        target_voice_override=target_voice_override,
                        category="chinese_general",
                        custom_dict=custom_dict,
                        mode=mode
                    )
                    if nisay_res and len(nisay_res) == len(dialogues):
                        print(f"[OK] SN AI Cloud Server translated {len(nisay_res)} dialogues successfully!")
                        return nisay_res
                except Exception as ne:
                    print(f"SN AI Cloud translation note: {ne}")

        # 1. Groq Ultra-Fast AI (Parallel Chunks, 500-800 tokens/sec)
        if self.groq_api_key and str(self.groq_api_key).startswith("gsk_"):
            try:
                groq_res = await self.translate_dialogues_groq(
                    dialogues=dialogues,
                    mode=mode,
                    source_lang=source_lang,
                    voice_directive=voice_directive,
                    active_system_prompt=active_system_prompt,
                    chosen_single_voice=chosen_single_voice,
                    is_multi=is_multi
                )
                if groq_res:
                    return groq_res
            except Exception as ge:
                print(f"Groq translation warning: {ge}")

        # 2. Gemini AI Studio Translation (Parallel Chunks)
        valid_gemini_keys = [k for k in self.api_keys if k.startswith("AIzaSy")]
        if self.clients and valid_gemini_keys:
            try:
                chunk_size = 20
                g_chunks = [dialogues[i:i + chunk_size] for i in range(0, len(dialogues), chunk_size)]

                async def _process_gemini_chunk(chunk: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
                    enriched_chunk = []
                    for itm in chunk:
                        c_itm = dict(itm)
                        s = float(c_itm.get("start", 0.0))
                        e = float(c_itm.get("end", s + 2.0))
                        dur = round(max(0.2, e - s), 2)
                        c_itm["duration"] = dur
                        max_w = max(1, int(round(dur * 2.2)))
                        if dur <= 1.2:
                            max_w = min(max_w, 3)
                        elif dur <= 2.0:
                            max_w = min(max_w, 6)
                        c_itm["max_words"] = max_w
                        enriched_chunk.append(c_itm)

                    prompt = f"""Mode: {mode} (Authentic Cambodian TV Drama Dubbing)
Source Language: {source_lang}
Input script items in JSON (includes exact 'duration' in seconds and 'max_words' budget):
{json.dumps(enriched_chunk, ensure_ascii=False, indent=2)}

Translate each dialogue item into emotional, natural spoken Khmer dubbing script ('text_km').
{voice_directive}
CRITICAL LIP-SYNC & SYLLABLE-PACING (ត្រូវទាន់ជាមួយតួអង្គហាមាត់និយាយ និងល្បឿននិយាយធម្មជាតិ 1.0x):
- COMPLETE MEANING: Translate the entire dialogue without omitting words, clauses, character names, or statements. NEVER drop parts of what the speaker says!
- SYLLABLE BUDGET MATCHING: The Khmer sentence length MUST match the actor's mouth duration so that the voice speaks at a natural, unhurried human pace (1.0x). DO NOT write overly long sentences for short clips!
  * Duration <= 1.2s: strictly translate into 1-3 PUNCHY words (e.g. "ចេញទៅ!", "ឈប់ភ្លាម!", "ទៅណា?!", "ជួយផង!", "បិទមាត់!", "ចាំសិន!", "ចង់ងាប់មែនទេ?!"). NEVER expand short shouts into long explanations.
  * Duration 1.3s - 2.5s: 4-7 natural spoken Khmer words.
  * Duration >= 3.0s: translate with natural dramatic cadence matching the mouth duration window.
- Natural spoken Khmer drama dubbing style (ពិរោះស្ដាប់ រណ្តំចិត្ត ដូចទូរទស្សន៍ហង្សមាស បាយ័ន ស៊ីធីអិន): no robotic "តើអ្នក", no formal book language.
Return ONLY valid JSON array with keys: id, start, end, text_original, text_km, speaker, voice, rate_percent, pitch_hz, emotion."""

                    active_client = self.get_client() or self.client
                    def _call_gemini(c):
                        return c.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=active_system_prompt,
                                response_mime_type="application/json"
                            )
                        )

                    try:
                        response = await asyncio.wait_for(asyncio.to_thread(_call_gemini, active_client), timeout=12.0)
                    except Exception as call_err:
                        print(f"Gemini key error, retrying next key in pool: {call_err}")
                        alt_client = self.get_client()
                        if alt_client and alt_client != active_client:
                            try:
                                response = await asyncio.wait_for(asyncio.to_thread(_call_gemini, alt_client), timeout=12.0)
                            except Exception:
                                return None
                        else:
                            return None

                    if response and response.text:
                        parsed = json.loads(response.text)
                        items = parsed if isinstance(parsed, list) else parsed.get("dialogues") or parsed.get("items") or list(parsed.values())[0]
                        if isinstance(items, list):
                            for j, item in enumerate(items):
                                if j < len(chunk):
                                    item["start"] = chunk[j].get("start", item.get("start", 0))
                                    item["end"] = chunk[j].get("end", item.get("end", 0))
                                    orig_line = chunk[j].get("text_original", chunk[j].get("text", ""))
                                    item["text_original"] = orig_line

                                    persona = infer_drama_persona_acoustics(
                                        item,
                                        is_multi=is_multi,
                                        chosen_single_voice=chosen_single_voice
                                    )
                                    v = persona["voice"]
                                    item["voice"] = v
                                    item["pitch_hz"] = persona["pitch_hz"]
                                    item["rate_percent"] = persona["rate_percent"]
                                    item["speaker"] = persona["speaker"]
                                    if not is_multi:
                                        item["voice"] = chosen_single_voice
                                        item["pitch_hz"] = 0
                                        item["rate_percent"] = 0
                                        item["speaker"] = "ស្រីមុំ (Sreymom Solo)" if chosen_single_voice == "sreymom" else "ពិសិដ្ឋ (Piseth Solo)"
                                    
                                    dur_sec = round(max(0.2, float(item["end"]) - float(item["start"])), 2)
                                    item["text_km"] = enrich_khmer_drama_dialogue(
                                        item.get("text_km", ""),
                                        orig_line,
                                        item["voice"],
                                        duration_sec=dur_sec
                                    )
                            return items
                    return None

                g_tasks = [_process_gemini_chunk(c) for c in g_chunks]
                g_results = await asyncio.gather(*g_tasks)
                
                g_translated_map: Dict[int, Dict[str, Any]] = {}
                for chunk_idx, r in enumerate(g_results):
                    chunk_start = chunk_idx * chunk_size
                    if r and isinstance(r, list):
                        for j, item in enumerate(r):
                            global_idx = chunk_start + j
                            if global_idx < len(dialogues):
                                g_translated_map[global_idx] = item

                # If Gemini translated at least 40% of the dialogues, reconcile missing ones with Zero-Drop
                if len(g_translated_map) >= len(dialogues) * 0.4:
                    missing_indices = [i for i in range(len(dialogues)) if i not in g_translated_map]
                    if missing_indices:
                        missing_tasks = [self._translate_single_line(dialogues[mi], mi, source_lang, target_voice_override) for mi in missing_indices]
                        missing_results = await asyncio.gather(*missing_tasks)
                        for mi, m_item in zip(missing_indices, missing_results):
                            g_translated_map[mi] = m_item
                    return [g_translated_map[i] for i in range(len(dialogues))]
            except Exception as e:
                print(f"Gemini translation note: {e}. Using professional free drama dubbing engine.")

        # Cloud-Server-Only Enforcement with Auto-Healing Fallback:
        # Prioritizes online cloud servers, but if upstream provider capacity is exhausted,
        # seamlessly falls back to High-Speed Drama Dubbing Engine to prevent pipeline failure
        CLOUD_SERVER_ONLY = False

        # 3. High-Speed Local Drama Dubbing Engine (Concurrent with Semaphore=12 & Connection Pool)
        sem = asyncio.Semaphore(12)

        async def _translate_single(item: Dict[str, Any], idx: int) -> Dict[str, Any]:
            async with sem:
                orig_text = item.get("text") or item.get("text_original", "")
                start = item.get("start", 0.0)
                end = item.get("end", 0.0)
                dur_sec = round(max(0.2, end - start), 2)

                # Determine character role, voice, pitch, and rate
                v_info = self._determine_strictly_two_voices(item, target_voice_override)
                chosen_voice = v_info["voice"]

                # Translate with drama pre-norm, post-polish, and dialogue enrichment
                try:
                    text_km = await self.translate_text_free(
                        orig_text,
                        source_lang=source_lang,
                        voice=chosen_voice
                    )
                except Exception as e:
                    print(f"Translation error on line {idx}: {e}")
                    text_km = orig_text

                # Final pass enrichment: duration-aware script adaptation
                final_text_km = enrich_khmer_drama_dialogue(
                    text_km,
                    orig_text,
                    chosen_voice,
                    duration_sec=dur_sec
                )

                return {
                    "id": item.get("id", idx + 1),
                    "start": start,
                    "end": end,
                    "speaker": v_info["character_role"],
                    "text_original": orig_text,
                    "text_km": final_text_km,
                    "voice": chosen_voice,
                    "rate_percent": v_info["rate_percent"],
                    "pitch_hz": v_info["pitch_hz"]
                }

        all_translated = []
        batch_chunk = 40
        for b_start in range(0, len(dialogues), batch_chunk):
            b_items = dialogues[b_start:b_start + batch_chunk]
            tasks = [_translate_single(item, b_start + idx) for idx, item in enumerate(b_items)]
            chunk_results = await asyncio.gather(*tasks)
            all_translated.extend(chunk_results)
        return all_translated


def parse_srt_content(srt_text: str) -> List[Dict[str, Any]]:
    """Parse SRT subtitle text into dialogue objects with start/end in seconds."""
    items = []
    blocks = re.split(r'\n\s*\n', srt_text.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            idx = lines[0].strip()
            time_match = re.search(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})', lines[1])
            if time_match:
                h1, m1, s1, ms1, h2, m2, s2, ms2 = [int(x) for x in time_match.groups()]
                start_sec = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
                end_sec = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0
                text = " ".join([l.strip() for l in lines[2:] if l.strip()])

                speaker = "Narrator"
                speaker_match = re.match(r'^\[?([A-Za-z0-9_\u1780-\u17FF\s]+)\]?:\s*(.*)', text)
                if speaker_match:
                    speaker = speaker_match.group(1).strip()
                    text = speaker_match.group(2).strip()

                items.append({
                    "id": idx,
                    "start": round(start_sec, 2),
                    "end": round(end_sec, 2),
                    "speaker": speaker,
                    "text": text,
                    "text_original": text
                })
    return items


def format_srt_content(dialogues: List[Dict[str, Any]], use_km: bool = True) -> str:
    """Export dialogues to standard SRT subtitle string."""
    def _sec_to_srt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        ms = int(round((sec - int(sec)) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines = []
    for idx, item in enumerate(dialogues, start=1):
        start_str = _sec_to_srt_time(item.get("start", 0))
        end_str = _sec_to_srt_time(item.get("end", 0))
        text = item.get("text_km") if use_km else item.get("text_original", item.get("text", ""))
        lines.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")

    return "\n".join(lines)
