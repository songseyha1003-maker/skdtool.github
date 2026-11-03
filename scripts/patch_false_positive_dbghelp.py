# -*- coding: utf-8 -*-
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
lic_file = BASE_DIR / "license_engine.py"
content = lic_file.read_text(encoding="utf-8")

# 1. Remove dbghelp.dll from sandbox detection
old_sb = 'for mod_name in ("sbiedll.dll", "dbghelp.dll", "snxhk.dll"):'
new_sb = 'for mod_name in ("sbiedll.dll", "snxhk.dll", "cmdvhook.dll", "api_log.dll", "dir_watch.dll"):'
if old_sb in content:
    content = content.replace(old_sb, new_sb)
    print("✅ Removed dbghelp.dll from check_sandbox_environment")
else:
    print("⚠️ old_sb not found")

# 2. Add auto-heal in is_current_device_banned for registry
old_reg = 'if val == expected_sig:\n                    return True, reason or "Security tamper attempt detected"'
new_reg = '''if val == expected_sig:
                    if "dbghelp.dll" in (reason or ""):
                        unban_device(current_hwid, "SN-ADMIN-MASTER-UNBAN-2026")
                        return False, ""
                    return True, reason or "Security tamper attempt detected"'''
if old_reg in content:
    content = content.replace(old_reg, new_reg)
    print("✅ Added auto-heal to registry ban check")
else:
    # Try with CRLF
    old_reg_crlf = old_reg.replace('\n', '\r\n')
    new_reg_crlf = new_reg.replace('\n', '\r\n')
    if old_reg_crlf in content:
        content = content.replace(old_reg_crlf, new_reg_crlf)
        print("✅ Added auto-heal to registry ban check (CRLF)")
    else:
        print("⚠️ old_reg not found")

# 3. Add auto-heal in is_current_device_banned for vault
old_vlt = 'if vault_data.get("signature") == expected_sig:\n                    return True, vault_data.get("reason", "Security tamper attempt detected")'
new_vlt = '''if vault_data.get("signature") == expected_sig:
                    ban_reason = vault_data.get("reason", "Security tamper attempt detected")
                    if "dbghelp.dll" in (ban_reason or ""):
                        unban_device(current_hwid, "SN-ADMIN-MASTER-UNBAN-2026")
                        return False, ""
                    return True, ban_reason'''
if old_vlt in content:
    content = content.replace(old_vlt, new_vlt)
    print("✅ Added auto-heal to vault ban check")
else:
    old_vlt_crlf = old_vlt.replace('\n', '\r\n')
    new_vlt_crlf = new_vlt.replace('\n', '\r\n')
    if old_vlt_crlf in content:
        content = content.replace(old_vlt_crlf, new_vlt_crlf)
        print("✅ Added auto-heal to vault ban check (CRLF)")
    else:
        print("⚠️ old_vlt not found")

lic_file.write_text(content, encoding="utf-8")

# 4. Patch desktop_app.py
desktop_file = BASE_DIR / "desktop_app.py"
d_content = desktop_file.read_text(encoding="utf-8")
old_d = 'banned, reason = is_current_device_banned()'
new_d = '''banned, reason = is_current_device_banned()
        if banned and "dbghelp.dll" in str(reason):
            from license_engine import unban_device
            unban_device(get_machine_hwid(), "SN-ADMIN-MASTER-UNBAN-2026")
            banned = False'''
if old_d in d_content:
    d_content = d_content.replace(old_d, new_d)
    desktop_file.write_text(d_content, encoding="utf-8")
    print("✅ Added auto-heal to desktop_app.py")
else:
    print("⚠️ old_d not found in desktop_app.py")

# 5. Re-sign core manifest
sys.path.insert(0, str(BASE_DIR))
import license_engine
license_engine.build_core_manifest()
print("✅ Core security manifest rebuilt and cryptographically re-signed!")
