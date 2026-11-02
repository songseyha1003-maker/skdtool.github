"""
Military-Grade Fortress Security Upgrade Script for license_engine.py
Upgrades:
1. Anti-Brute Force Attack Rate Limiter & Cooldown Lockout
2. In-Memory Bytecode Checksum & Anti-Opcode Patching Guard
3. Anti-Sandbox & Automated Crack VM Analysis Detection
4. Debugger Latency Timing Guard (Anti-Single Stepping)
5. Multi-Vector Hardware Integrity Verification
"""
from pathlib import Path
import re

def patch_security():
    p = Path("license_engine.py")
    content = p.read_text(encoding="utf-8")

    # 1. Add Brute-Force & Bytecode & Sandbox Guards in helper section
    helpers = '''
# ==========================================================================
# 🛡️ SYSTEM 7+: BRUTE-FORCE LOCKOUT, IN-MEMORY BYTECODE INTEGRITY & SANDBOX TRAP
# ==========================================================================
_FAILED_ATTEMPTS: List[float] = []
_BRUTE_FORCE_LOCKOUT_UNTIL: float = 0.0
_VERIFY_CODE_HASH: Optional[str] = None
_CHECK_CODE_HASH: Optional[str] = None

def record_failed_attempt() -> Tuple[bool, str]:
    """Track invalid license attempts and enforce automated brute-force cooldown."""
    global _BRUTE_FORCE_LOCKOUT_UNTIL
    now = time.time()
    _FAILED_ATTEMPTS[:] = [t for t in _FAILED_ATTEMPTS if now - t < 90.0]
    _FAILED_ATTEMPTS.append(now)
    if len(_FAILED_ATTEMPTS) >= 8:
        _BRUTE_FORCE_LOCKOUT_UNTIL = now + 90.0  # 90 second lockout
        return True, "⚠️ Too many invalid attempts. Brute-force lockout active for 90 seconds."
    return False, ""

def is_brute_force_locked() -> Tuple[bool, str]:
    """Check if brute-force lockout is currently active."""
    now = time.time()
    if now < _BRUTE_FORCE_LOCKOUT_UNTIL:
        rem = max(1, int(_BRUTE_FORCE_LOCKOUT_UNTIL - now))
        return True, f"⚠️ Brute-force protection: Too many invalid key attempts. Please wait {rem} seconds."
    return False, ""

def init_bytecode_baseline():
    """Anchor authentic compiled bytecode hash of core security routines in memory."""
    global _VERIFY_CODE_HASH, _CHECK_CODE_HASH
    try:
        fn1 = globals().get("verify_license_key")
        fn2 = globals().get("check_current_device_license")
        if fn1 and hasattr(fn1, "__code__"):
            _VERIFY_CODE_HASH = hashlib.sha256(fn1.__code__.co_code).hexdigest()
        if fn2 and hasattr(fn2, "__code__"):
            _CHECK_CODE_HASH = hashlib.sha256(fn2.__code__.co_code).hexdigest()
    except Exception:
        pass

def verify_bytecode_integrity() -> Tuple[bool, str]:
    """Verify that in-memory opcodes have not been patched or replaced by a crack tool."""
    try:
        fn1 = globals().get("verify_license_key")
        fn2 = globals().get("check_current_device_license")
        if not fn1 or not hasattr(fn1, "__code__"):
            return False, "Missing core routine in memory"
        if _VERIFY_CODE_HASH:
            current_h1 = hashlib.sha256(fn1.__code__.co_code).hexdigest()
            if current_h1 != _VERIFY_CODE_HASH:
                return False, "In-memory opcode modification detected"
        if _CHECK_CODE_HASH and fn2 and hasattr(fn2, "__code__"):
            current_h2 = hashlib.sha256(fn2.__code__.co_code).hexdigest()
            if current_h2 != _CHECK_CODE_HASH:
                return False, "In-memory license verification patch detected"
        return True, "Bytecode intact"
    except Exception as e:
        return False, f"Bytecode inspection error: {e}"

def check_sandbox_environment() -> Tuple[bool, str]:
    """Detect if executing inside an automated malware-analysis / crack sandbox."""
    if sys.platform != "win32":
        return False, ""
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        for mod_name in ("sbiedll.dll", "dbghelp.dll", "snxhk.dll"):
            h = kernel32.GetModuleHandleW(mod_name)
            if h != 0:
                return True, f"Automated sandbox module ({mod_name}) detected"
        for env_k in ("CUCKOO", "SANDBOX", "VBOX_SHARED", "ANYRUN"):
            if env_k in os.environ:
                return True, f"Automated analysis environment ({env_k}) detected"
    except Exception:
        pass
    return False, ""
'''

    # Place helpers before verify_runtime_integrity
    target_integrity = "def verify_runtime_integrity() -> Tuple[bool, str]:"
    if target_integrity in content and "def record_failed_attempt" not in content:
        content = content.replace(target_integrity, helpers + "\n" + target_integrity, 1)
        print("[OK] Injected Brute-Force Guard, Bytecode Integrity & Sandbox Detectors")

    # Update verify_runtime_integrity to include bytecode check
    old_v_runtime = '''    try:
        import types
        fn = globals().get("verify_license_key")
        if fn and (not isinstance(fn, types.FunctionType) or fn.__code__.co_name != "verify_license_key"):
            return False, "Security module function hook detected"

        fn2 = globals().get("check_current_device_license")
        if fn2 and (not isinstance(fn2, types.FunctionType) or fn2.__code__.co_name != "check_current_device_license"):
            return False, "License engine hook detected"

        return True, "Runtime integrity OK"
    except Exception as e:'''

    new_v_runtime = '''    try:
        import types
        fn = globals().get("verify_license_key")
        if fn and (not isinstance(fn, types.FunctionType) or fn.__code__.co_name != "verify_license_key"):
            return False, "Security module function hook detected"

        fn2 = globals().get("check_current_device_license")
        if fn2 and (not isinstance(fn2, types.FunctionType) or fn2.__code__.co_name != "check_current_device_license"):
            return False, "License engine hook detected"

        bc_ok, bc_msg = verify_bytecode_integrity()
        if not bc_ok:
            return False, bc_msg

        return True, "Runtime integrity OK"
    except Exception as e:'''

    if old_v_runtime in content:
        content = content.replace(old_v_runtime, new_v_runtime, 1)
        print("[OK] Linked Bytecode Integrity check into verify_runtime_integrity")

    # Update verify_license_key to check brute force, latency timing, and record failed attempts
    old_verify_start = '''    cleaned_key = input_key.strip().upper()
    if not cleaned_key:
        return False, "Please enter License Key", {}

    if not current_hwid:'''

    new_verify_start = '''    cleaned_key = input_key.strip().upper()
    if not cleaned_key:
        return False, "Please enter License Key", {}

    # 🛡️ Brute-force rate limiting check
    is_locked, lock_msg = is_brute_force_locked()
    if is_locked:
        return False, lock_msg, {}

    t_perf_start = time.perf_counter()

    if not current_hwid:'''

    if old_verify_start in content:
        content = content.replace(old_verify_start, new_verify_start, 1)
        print("[OK] Added brute-force lockout & timing start to verify_license_key")

    old_verify_end = '''        return True, "✅ License Key is valid and active!", {
            "license_key": cleaned_key,
            "client_name": "User",
            "plan": f"PRO_{plan_tag}",
            "expires_at": expiry_str,
            "expiry_timestamp": expiry_ts,
            "bound_hwid": current_hwid if hwid_tag not in ("9999", "AAAA") else "ANY",
            "status": "ACTIVE"
        }

    return False, "❌ Invalid License Key. Please contact Admin to get a valid key.", {}'''

    new_verify_end = '''        # Anti-Single Stepping Latency Trap
        if (time.perf_counter() - t_perf_start) > 1.2:
            return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}

        return True, "✅ License Key is valid and active!", {
            "license_key": cleaned_key,
            "client_name": "User",
            "plan": f"PRO_{plan_tag}",
            "expires_at": expiry_str,
            "expiry_timestamp": expiry_ts,
            "bound_hwid": current_hwid if hwid_tag not in ("9999", "AAAA") else "ANY",
            "status": "ACTIVE"
        }

    record_failed_attempt()
    return False, "❌ Invalid License Key. Please contact Admin to get a valid key.", {}'''

    if old_verify_end in content:
        content = content.replace(old_verify_end, new_verify_end, 1)
        print("[OK] Added timing trap & failed attempt recorder to verify_license_key")

    # Add init_bytecode_baseline() call at end of license_engine.py
    if "init_bytecode_baseline()" not in content:
        content = content.rstrip() + "\n\n# Initialize In-Memory Bytecode Baseline for Anti-Patching\ninit_bytecode_baseline()\n"
        print("[OK] Added init_bytecode_baseline() initialization at bottom of license_engine.py")

    p.write_text(content, encoding="utf-8")
    print("[SUCCESS] Fortress security upgrades applied to license_engine.py!")

if __name__ == "__main__":
    patch_security()

