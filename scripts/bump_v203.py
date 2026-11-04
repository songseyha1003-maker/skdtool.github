# -*- coding: utf-8 -*-
import json
import datetime
from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

new_ver = "2.0.3"
today_str = datetime.date.today().isoformat()
title = f"SN TOOL STUDIO PRO - Official Update v{new_ver} (False-Positive Hotfix & Stability Upgrade)"
notes = "• 🛡️ Hotfix Security Sentinel: Eliminated false-positive dbghelp.dll sandbox detection and enabled auto-healing hardware protection.\n• ⚡ Turbo Pipeline Stability: Optimized translation engine memory allocation and smooth episode processing."

# 1. Update version.json
vjson_p = BASE_DIR / "version.json"
vdata = json.loads(vjson_p.read_text(encoding="utf-8"))
vdata["version"] = new_ver
vdata["release_date"] = today_str
vdata["title"] = title
vdata["release_notes"] = notes
vjson_p.write_text(json.dumps(vdata, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"✅ Updated version.json -> {new_ver}")

# 2. Update data/cloud_manifest.json
m_p = BASE_DIR / "data" / "cloud_manifest.json"
mdata = json.loads(m_p.read_text(encoding="utf-8"))
mdata["version"] = new_ver
mdata["release_date"] = today_str
mdata["title"] = title
mdata["subtitle"] = f"Official build v{new_ver} featuring security false-positive hotfix and stable translation pipeline."
mdata["release_notes"] = notes
m_p.write_text(json.dumps(mdata, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"✅ Updated data/cloud_manifest.json -> {new_ver}")

# 3. Update update.py
up_p = BASE_DIR / "update.py"
up_text = up_p.read_text(encoding="utf-8")
up_text = up_text.replace('CURRENT_VERSION = "2.0.2"', f'CURRENT_VERSION = "{new_ver}"')
up_p.write_text(up_text, encoding="utf-8")
print(f"✅ Updated update.py -> {new_ver}")

# 4. Rebuild core manifest
sys.path.insert(0, str(BASE_DIR))
import license_engine
license_engine.build_core_manifest()
print("✅ Rebuilt core manifest")
