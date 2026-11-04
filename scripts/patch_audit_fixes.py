# -*- coding: utf-8 -*-
"""
Auditing & Hardening Script: Fixes all undefined names and missing imports across the project.
"""
import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# 1. pipeline.py: Ensure 'import time' is present
pipe_path = BASE_DIR / "pipeline.py"
pipe_txt = pipe_path.read_text(encoding="utf-8")
if "import time\n" not in pipe_txt:
    pipe_txt = pipe_txt.replace("import asyncio\n", "import asyncio\nimport time\n")
    pipe_path.write_text(pipe_txt, encoding="utf-8")
    print("[OK] Added 'import time' to pipeline.py")
else:
    print("[SKIP] pipeline.py already has 'import time'")

# 2. batch_engine.py: Ensure 'import json' is present
batch_path = BASE_DIR / "batch_engine.py"
batch_txt = batch_path.read_text(encoding="utf-8")
if "import json\n" not in batch_txt:
    batch_txt = batch_txt.replace("import sys\n", "import sys\nimport json\n")
    batch_path.write_text(batch_txt, encoding="utf-8")
    print("[OK] Added 'import json' to batch_engine.py")
else:
    print("[SKIP] batch_engine.py already has 'import json'")

# 3. server.py: Ensure 'import hongguo_service' and 'import reelshort_service' are present
srv_path = BASE_DIR / "server.py"
srv_txt = srv_path.read_text(encoding="utf-8")
if "import hongguo_service\n" not in srv_txt:
    srv_txt = srv_txt.replace("import shortmax_service\n", "import shortmax_service\nimport hongguo_service\nimport reelshort_service\n")
    srv_path.write_text(srv_txt, encoding="utf-8")
    print("[OK] Added 'import hongguo_service' to server.py")
else:
    print("[SKIP] server.py already has 'import hongguo_service'")

# 4. admin_dashboard.py: Ensure 'generate_server_lease_token' is imported
admin_path = BASE_DIR / "admin_dashboard.py"
if admin_path.exists():
    admin_txt = admin_path.read_text(encoding="utf-8")
    if "generate_server_lease_token," not in admin_txt:
        admin_txt = admin_txt.replace(
            "    generate_license_key,\n",
            "    generate_license_key,\n    generate_server_lease_token,\n"
        )
        admin_path.write_text(admin_txt, encoding="utf-8")
        print("[OK] Added 'generate_server_lease_token' to admin_dashboard.py")

# 5. hongguo_db.py: Define 'base' inside init_db()
hdb_path = BASE_DIR / "hongguo_db.py"
hdb_txt = hdb_path.read_text(encoding="utf-8")
if "base = Path(__file__).resolve().parent" not in hdb_txt:
    hdb_txt = hdb_txt.replace(
        "def init_db():\n    \"\"\"Create tables and populate initial catalog if missing.\"\"\"\n",
        "def init_db():\n    \"\"\"Create tables and populate initial catalog if missing.\"\"\"\n    base = Path(__file__).resolve().parent\n"
    )
    hdb_path.write_text(hdb_txt, encoding="utf-8")
    print("[OK] Defined 'base' inside init_db() in hongguo_db.py")
else:
    print("[SKIP] hongguo_db.py already defines 'base' in init_db()")

# 6. nisay_translate.py: Ensure _fallback_single is defined before the cache verification loop
nisay_path = BASE_DIR / "nisay_translate.py"
nisay_txt = nisay_path.read_text(encoding="utf-8")
# Normalize line endings for replacement
nisay_crlf = "\r\n" in nisay_txt
nisay_clean = nisay_txt.replace("\r\n", "\n")

fallback_func = '''    def _fallback_single(src_t: str) -> str:
        s_clean = (src_t or "").strip()
        if not s_clean:
            return ""
        if entity_glossary:
            for k, v in entity_glossary.items():
                if k and v and k in s_clean:
                    s_clean = s_clean.replace(k, v)
        try:
            import urllib.request
            import urllib.parse
            url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=km&dt=t&q=" + urllib.parse.quote(s_clean)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                fb_data = json.loads(r.read().decode('utf-8'))
                if fb_data and isinstance(fb_data, list) and fb_data[0]:
                    joined = "".join([part[0] for part in fb_data[0] if part and part[0]]).strip()
                    if joined:
                        return joined
        except Exception:
            pass
        return s_clean

'''

cache_verif_target = "    # ⚡ 2. Save translated lines into cache with per-line integrity verification"
old_fallback_def = '''    def _fallback_single(src_t: str) -> str:
        s_clean = (src_t or "").strip()
        if not s_clean:
            return ""
        if entity_glossary:
            for k, v in entity_glossary.items():
                if k and v and k in s_clean:
                    s_clean = s_clean.replace(k, v)
        try:
            import urllib.request
            import urllib.parse
            url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=km&dt=t&q=" + urllib.parse.quote(s_clean)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            with urllib.request.urlopen(req, timeout=10) as r:
                fb_data = json.loads(r.read().decode('utf-8'))
                if fb_data and isinstance(fb_data, list) and fb_data[0]:
                    joined = "".join([part[0] for part in fb_data[0] if part and part[0]]).strip()
                    if joined:
                        return joined
        except Exception:
            pass
        return s_clean'''

if cache_verif_target in nisay_clean and old_fallback_def in nisay_clean:
    nisay_clean = nisay_clean.replace(old_fallback_def, "    # (_fallback_single pre-defined above)")
    nisay_clean = nisay_clean.replace(cache_verif_target, fallback_func + cache_verif_target)
    if nisay_crlf:
        nisay_clean = nisay_clean.replace("\n", "\r\n")
    nisay_path.write_text(nisay_clean, encoding="utf-8")
    print("[OK] Repositioned _fallback_single before verification loop in nisay_translate.py")
else:
    print("[SKIP/CHECK] nisay_translate.py target pattern match failed or already applied")

print("[DONE] All audit patches applied successfully!")
