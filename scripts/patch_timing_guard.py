"""
Patch verify_license_key to apply the debugger latency timing trap across ALL validation branches.
"""
from pathlib import Path

p = Path("license_engine.py")
content = p.read_text(encoding="utf-8")

# Helper check logic
timing_guard = """        if (time.perf_counter() - t_perf_start) > 1.2:
            return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}"""

# 1. Master Keys branch
old_master = """    if cleaned_key in DEFAULT_MASTER_KEYS:
        master_info = DEFAULT_MASTER_KEYS[cleaned_key]"""

new_master = f"""    if cleaned_key in DEFAULT_MASTER_KEYS:
{timing_guard}
        master_info = DEFAULT_MASTER_KEYS[cleaned_key]"""

if old_master in content:
    content = content.replace(old_master, new_master, 1)
    print("[OK] Latency trap added to Master Keys branch")

# 2. Custom Keys branch
old_custom = """                return True, "✅ Custom Key is valid and active!", rec"""
new_custom = f"""{timing_guard}
                return True, "✅ Custom Key is valid and active!", rec"""

if old_custom in content:
    content = content.replace(old_custom, new_custom, 1)
    print("[OK] Latency trap added to Custom Keys branch")

# 3. Admin History branch
old_history = """                        return True, "✅ License Key is valid and active!", record"""
new_history = f"""{timing_guard}
                        return True, "✅ License Key is valid and active!", record"""

if old_history in content:
    content = content.replace(old_history, new_history, 1)
    print("[OK] Latency trap added to Admin History branch")

# 4. Online Cloud branch
old_online = """    if online_ok:
        return True, online_msg, online_rec"""
new_online = f"""    if online_ok:
{timing_guard}
        return True, online_msg, online_rec"""

if old_online in content:
    content = content.replace(old_online, new_online, 1)
    print("[OK] Latency trap added to Online branch")

p.write_text(content, encoding="utf-8")
print("[SUCCESS] All branches reinforced with debugger latency trap!")

