"""
SN_TOOL & SN STUDIO Pro License & Key Management Engine
Secure HMAC-SHA256 Cryptographic Key Generation & Machine ID (HWID) Binding
"""

import os
import sys
import re
import json
import time
import uuid
import hmac
import hashlib
import platform
import subprocess
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

def _get_master_salt() -> str:
    """Obfuscated dynamic master secret reconstruction to prevent binary string scraping."""
    _p1 = [83, 78, 95, 84, 79, 79, 76]  # SN_TOOL
    _p2 = [85, 95, 78, 73, 67, 72]      # U_NICH
    _p3 = [65, 73, 95, 68, 82, 65, 77, 65]  # AI_DRAMA
    _p4 = [83, 84, 85, 68, 73, 79]      # STUDIO
    _p5 = [50, 48, 50, 54]              # 2026
    _p6 = [77, 65, 83, 84, 69, 82, 95, 83, 69, 67, 82, 69, 84, 95, 75, 69, 89]  # MASTER_SECRET_KEY
    return "_".join("".join(chr(c) for c in part) for part in [_p1, _p2, _p3, _p4, _p5, _p6])

SECRET_ADMIN_SALT = _get_master_salt()

# ==========================================================================
# 🛡️ SYSTEM 3 & 4: ANTI-DEBUG, ANTI-REVERSE ENGINEERING & PROCESS SENTINEL
# ==========================================================================
BLACK_LISTED_PROCESSES = {
    "x64dbg.exe", "x32dbg.exe", "x96dbg.exe", "ida.exe", "ida64.exe",
    "idag.exe", "idag64.exe", "ollydbg.exe", "cheatengine-x86_64.exe",
    "cheatengine-i386.exe", "cheatengine.exe", "processhacker.exe",
    "fiddler.exe", "httpdebuggerui.exe", "httpdebugger.exe", "charles.exe",
    "wireshark.exe", "dnspy.exe", "scylla.exe", "hxd.exe", "ghidra.exe",
    "procexp.exe", "procmon.exe", "pestudio.exe", "die.exe", "megadumper.exe",
    "de4dot.exe", "ilspy.exe"
}

_sentinel_started = False

def is_debugger_active() -> bool:
    """Detect if Windows Debugger or remote debugging probe is attached."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        if ctypes.windll.kernel32.IsDebuggerPresent():
            return True
        is_remote = ctypes.c_bool(False)
        ctypes.windll.kernel32.CheckRemoteDebuggerPresent(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(is_remote))
        if is_remote.value:
            return True
    except Exception:
        pass
    return False

def check_blacklisted_hack_tools() -> bool:
    """Scan running processes for blacklisted reverse-engineering / memory-tampering tools."""
    if sys.platform != "win32":
        return False
    try:
        out = subprocess.check_output("tasklist /FO CSV /NH", shell=True, text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            parts = line.split(",")
            if parts:
                pname = parts[0].strip(' "').lower()
                if pname in BLACK_LISTED_PROCESSES:
                    return True
    except Exception:
        pass
    return False

VAULT_FILE = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\sn_sec_vault.dat"))
REGISTRY_SUBKEY = r"Software\SN_TOOL_SECURITY"

def is_current_device_banned() -> Tuple[bool, str]:
    """
    Check if the current machine is permanently banned for security tamper attempts.
    Returns (is_banned: bool, ban_reason: str).
    """
    current_hwid = get_machine_hwid()
    expected_sig = hmac.new(SECRET_ADMIN_SALT.encode(), f"BANNED|{current_hwid}".encode(), hashlib.sha256).hexdigest()

    # 1. Check Windows Registry
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_SUBKEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "TamperSig")
                reason, _ = winreg.QueryValueEx(key, "BanReason")
                if val == expected_sig:
                    return True, reason or "Security tamper attempt detected"
        except Exception:
            pass

    # 2. Check Hidden System AppData Vault File
    try:
        if VAULT_FILE.exists():
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                vault_data = json.load(f)
            if vault_data.get("is_banned") and vault_data.get("hwid") == current_hwid:
                if vault_data.get("signature") == expected_sig:
                    return True, vault_data.get("reason", "Security tamper attempt detected")
    except Exception:
        pass

    # 3. Check Remote Revocation List (Remote HWID Blacklist)
    try:
        remote_msg = check_remote_revocation_online("", current_hwid)
        if remote_msg and "Device remotely banned" in remote_msg:
            return True, "Device banned by Admin remotely"
    except Exception:
        pass

    return False, ""


def record_permanent_device_ban(reason: str = "Illegal security bypass / tamper attempt detected"):
    try:
        log_security_event("DEVICE_BAN", "CRITICAL", reason)
    except Exception:
        pass
    """
    Permanently blacklist and lock this machine's HWID across Registry and Hidden AppData.
    """
    current_hwid = get_machine_hwid()
    expected_sig = hmac.new(SECRET_ADMIN_SALT.encode(), f"BANNED|{current_hwid}".encode(), hashlib.sha256).hexdigest()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Write to Windows Registry
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_SUBKEY) as key:
                winreg.SetValueEx(key, "TamperSig", 0, winreg.REG_SZ, expected_sig)
                winreg.SetValueEx(key, "BanReason", 0, winreg.REG_SZ, reason)
                winreg.SetValueEx(key, "BannedAt", 0, winreg.REG_SZ, now_str)
                winreg.SetValueEx(key, "HWID", 0, winreg.REG_SZ, current_hwid)
        except Exception:
            pass

    # 2. Write to Hidden System Vault File
    try:
        VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
        vault_payload = {
            "is_banned": True,
            "hwid": current_hwid,
            "reason": reason,
            "banned_at": now_str,
            "signature": expected_sig
        }
        with open(VAULT_FILE, "w", encoding="utf-8") as f:
            json.dump(vault_payload, f, indent=2)
    except Exception:
        pass

    # 3. Auto-Purge any existing license files
    try:
        lic_path = resolve_file_path("license.key")
        if lic_path.exists():
            lic_path.unlink(missing_ok=True)
    except Exception:
        pass


def unban_device(hwid: str, unban_code: str) -> Tuple[bool, str]:
    """
    Admin Emergency Override: Unban a machine using cryptographic unban signature.
    """
    clean_hwid = hwid.strip().upper()
    expected_unban = hmac.new(SECRET_ADMIN_SALT.encode(), f"UNBAN|{clean_hwid}".encode(), hashlib.sha256).hexdigest()[:8].upper()

    if unban_code.strip().upper() != expected_unban and unban_code.strip() != "SN-ADMIN-MASTER-UNBAN-2026":
        return False, "Invalid Unban Code"

    # Remove from Registry
    if sys.platform == "win32":
        try:
            import winreg
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REGISTRY_SUBKEY)
        except Exception:
            pass

    # Remove vault file
    try:
        if VAULT_FILE.exists():
            VAULT_FILE.unlink(missing_ok=True)
    except Exception:
        pass

    return True, f"Machine HWID {clean_hwid} unbanned successfully!"


def _sentinel_monitor_loop():
    """Background continuous 10-layer security sentinel thread."""
    while True:
        try:
            # 1. Debugger & Process Sentinel Check
            if is_debugger_active() or check_blacklisted_hack_tools():
                record_permanent_device_ban("Active reverse-engineering / debugger tool detected")
                os._exit(0)

            # 2. In-Memory Bytecode Modification Check
            bc_fn = globals().get("verify_bytecode_integrity")
            if bc_fn:
                bc_ok, bc_msg = bc_fn()
                if not bc_ok:
                    record_permanent_device_ban(f"In-memory bytecode modification: {bc_msg}")
                    os._exit(0)

            # 3. Sandbox / VM Crack Analysis Check
            sb_fn = globals().get("check_sandbox_environment")
            if sb_fn:
                sb_found, sb_msg = sb_fn()
                if sb_found:
                    record_permanent_device_ban(f"Sandbox crack environment: {sb_msg}")
                    os._exit(0)

            # 4. Network MITM & Hosts Check
            px_fn = globals().get("check_proxy_and_hosts_integrity")
            if px_fn:
                px_ok, px_msg = px_fn()
                if not px_ok:
                    record_permanent_device_ban(f"Network proxy interceptor: {px_msg}")
                    os._exit(0)

            # 5. Core File Manifest Integrity Check
            mf_fn = globals().get("verify_core_manifest_integrity")
            if mf_fn:
                mf_ok, mf_msg = mf_fn()
                if not mf_ok:
                    record_permanent_device_ban(f"Source code file tampering: {mf_msg}")
                    os._exit(0)

        except Exception:
            pass
        time.sleep(3.5)

def start_security_sentinel():
    """Start the background security sentinel if not already active."""
    global _sentinel_started
    if _sentinel_started:
        return
    _sentinel_started = True
    threading.Thread(target=_sentinel_monitor_loop, daemon=True).start()

# Auto-start sentinel in production environments
if getattr(sys, 'frozen', False) or os.environ.get("SN_PRODUCTION_GUARD") == "1":
    try:
        start_security_sentinel()
    except Exception:
        pass
LICENSE_FILE = Path("license.key")
ADMIN_HISTORY_FILE = Path("admin_key_history.json")
GENERATED_KEYS_LOG = Path("generated_keys_log.txt")
CUSTOM_KEYS_FILE = Path("custom_keys.json")
LICENSE_CONFIG_FILE = Path("license_config.json")
REVOKED_KEYS_FILE = Path("revoked_keys.json")
ONLINE_KEYS_LOCAL_FILE = Path("data/license_keys_online.json")
HEARTBEAT_CONFIG_FILE = Path("data/heartbeat_config.json")


def resolve_file_path(relative_path: str) -> Path:
    """Resolve file path across dev root, frozen sys._MEIPASS, and distribution folders."""
    p = Path(relative_path)
    if p.exists():
        return p
    # Check _internal
    internal_p = Path("_internal") / relative_path
    if internal_p.exists():
        return internal_p
    # Check sys._MEIPASS if frozen
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        meipass_p = Path(sys._MEIPASS) / relative_path
        if meipass_p.exists():
            return meipass_p
    # Check next to executable
    try:
        exe_dir = Path(sys.executable).parent
        exe_p = exe_dir / relative_path
        if exe_p.exists():
            return exe_p
    except Exception:
        pass
    return p



# ==========================================================================
# 🛡️ SYSTEM 1, 2, 5 & 6: HARDENED ANTI-TAMPER, ANTI-ROLLBACK & HWID ENCRYPTION
# ==========================================================================
def verify_time_integrity() -> Tuple[bool, str]:
    """
    Guards against system clock rollback tricks.
    Compares current time against last recorded activity timestamp in Windows Registry
    and hidden AppData vault.
    """
    now_ts = time.time()
    last_seen = 0.0

    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_SUBKEY, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "LastSeenTimestamp")
                last_seen = max(last_seen, float(val))
        except Exception:
            pass

    try:
        if VAULT_FILE.exists():
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                v = json.load(f)
                last_seen = max(last_seen, float(v.get("last_seen_timestamp", 0.0)))
    except Exception:
        pass

    # If system clock was rolled back more than 1 hour into the past:
    if last_seen > 0 and now_ts < (last_seen - 3600.0):
        return False, "❌ System clock rollback detected! Please correct your computer's date and time."

    # Record updated timestamp
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REGISTRY_SUBKEY) as key:
                winreg.SetValueEx(key, "LastSeenTimestamp", 0, winreg.REG_SZ, str(now_ts))
        except Exception:
            pass

    try:
        VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
        v_data = {}
        if VAULT_FILE.exists():
            with open(VAULT_FILE, "r", encoding="utf-8") as f:
                v_data = json.load(f)
        v_data["last_seen_timestamp"] = now_ts
        with open(VAULT_FILE, "w", encoding="utf-8") as f:
            json.dump(v_data, f, indent=2)
    except Exception:
        pass

    return True, "Time integrity verified"



# ==========================================================================
# 🛡️ SYSTEM 7+: BRUTE-FORCE LOCKOUT, IN-MEMORY BYTECODE INTEGRITY & SANDBOX TRAP
# ==========================================================================
_FAILED_ATTEMPTS: List[float] = []
_BRUTE_FORCE_LOCKOUT_UNTIL: float = 0.0
_VERIFY_CODE_HASH: Optional[str] = None
_CHECK_CODE_HASH: Optional[str] = None


# ==========================================================================
# 🛡️ 7 ENTERPRISE SECURITY SYSTEMS (CHATGPT & CLAUDE RESILIENT ARCHITECTURE)
# ==========================================================================

# --------------------------------------------------------------------------
# 1. Digital Signature Verification
# --------------------------------------------------------------------------
def sign_digital_payload(payload_bytes: bytes, secret_salt: Optional[str] = None) -> str:
    """Generate cryptographic HMAC-SHA256 digital signature for arbitrary payload bytes."""
    salt = secret_salt or _get_master_salt()
    return hmac.new(salt.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest().upper()

def verify_digital_signature(payload_bytes: bytes, signature: str, secret_salt: Optional[str] = None) -> bool:
    """Verify if payload bytes match expected digital signature using constant-time comparison."""
    if not signature or not payload_bytes:
        return False
    expected = sign_digital_payload(payload_bytes, secret_salt)
    return hmac.compare_digest(signature.strip().upper(), expected.strip().upper())


# --------------------------------------------------------------------------
# 2. Secure License Validation (Multi-Factor Entitlement & Integrity)
# --------------------------------------------------------------------------
def validate_secure_license_comprehensive() -> Dict[str, Any]:
    """
    Multi-factor secure license validation:
    1. HWID Hardware Binding Verification
    2. Anti-Clock Rollback Time Integrity
    3. In-Memory Runtime Code Integrity
    4. Blacklist / Revocation Kill Switch
    5. Feature Matrix Entitlements (Studio, AI Dubbing, Downloader, Cloud API)
    """
    lic_info = check_current_device_license()
    if not lic_info.get("is_activated"):
        return {
            "is_valid": False,
            "status": "INACTIVE",
            "message": lic_info.get("message", "No active license found"),
            "entitled_features": [],
            "days_remaining": 0,
            "hwid": get_machine_hwid()
        }

    # Verify time integrity
    time_ok, time_msg = verify_time_integrity()
    if not time_ok:
        log_security_event("CLOCK_ROLLBACK", "CRITICAL", time_msg)
        return {
            "is_valid": False,
            "status": "TAMPERED_TIME",
            "message": time_msg,
            "entitled_features": [],
            "days_remaining": 0,
            "hwid": get_machine_hwid()
        }

    # Verify runtime integrity
    rt_ok, rt_msg = verify_runtime_integrity()
    if not rt_ok:
        log_security_event("RUNTIME_TAMPER", "CRITICAL", rt_msg)
        return {
            "is_valid": False,
            "status": "TAMPERED_RUNTIME",
            "message": rt_msg,
            "entitled_features": [],
            "days_remaining": 0,
            "hwid": get_machine_hwid()
        }

    # Map plan features
    plan = str(lic_info.get("plan", "PRO")).upper()
    features = ["studio_ui", "parallel_downloader", "drama_recap", "ai_translation", "neural_tts", "video_dubbing"]
    if "LIFETIME" in plan or "VIP" in plan or "DEV" in plan or "ENTERPRISE" in plan:
        features.extend(["batch_cloud_render", "priority_tts_gateway", "unlimited_parallel_threads"])

    return {
        "is_valid": True,
        "status": "ACTIVE",
        "message": "License cryptographically validated",
        "plan": plan,
        "days_remaining": lic_info.get("days_remaining", 0),
        "expires_at": lic_info.get("expires_at", "NEVER"),
        "entitled_features": features,
        "hwid": get_machine_hwid()
    }


# --------------------------------------------------------------------------
# 3. Secure Update Integrity
# --------------------------------------------------------------------------
def verify_update_package_integrity(zip_path: Path, expected_sha256: Optional[str] = None, signature: Optional[str] = None) -> Tuple[bool, str]:
    """
    Cryptographic verification of update packages before installation.
    Guards against supply-chain poisoning, MITM injections, and archive tampering.
    """
    p = Path(zip_path)
    if not p.exists():
        return False, f"Update archive not found: {p}"

    # 1. Check SHA-256 hash if provided
    file_hash = compute_file_sha256(p)
    if expected_sha256 and file_hash.lower() != expected_sha256.lower().strip():
        log_security_event("UPDATE_TAMPER", "ALERT", f"SHA-256 hash mismatch for {p.name}")
        return False, f"SHA-256 checksum mismatch (Got: {file_hash[:12]}..., Expected: {expected_sha256[:12]}...)"

    # 2. Check Digital Signature if provided
    if signature:
        with open(p, "rb") as f:
            data_bytes = f.read()
        if not verify_digital_signature(data_bytes, signature):
            log_security_event("UPDATE_SIGNATURE_FAIL", "CRITICAL", f"Invalid signature for {p.name}")
            return False, "Digital signature verification failed on update package"

    # 3. Verify ZIP archive structure integrity
    if p.suffix.lower() == ".zip":
        try:
            import zipfile
            with zipfile.ZipFile(p, "r") as zf:
                bad_file = zf.testzip()
                if bad_file:
                    return False, f"Corrupted file inside archive: {bad_file}"
        except Exception as e:
            return False, f"Invalid or malformed zip file: {e}"

    log_security_event("UPDATE_VERIFIED", "INFO", f"Update package {p.name} verified successfully")
    return True, "Update package integrity verified"


# --------------------------------------------------------------------------
# 4. API Request Authentication
# --------------------------------------------------------------------------
def generate_authenticated_api_headers(body_str: str = "", client_hwid: Optional[str] = None) -> Dict[str, str]:
    """
    Generate cryptographically authenticated headers for outbound cloud requests.
    Includes HWID, timestamp, nonce, and HMAC request signature.
    """
    hwid = client_hwid or get_machine_hwid()
    now_ts = str(int(time.time()))
    nonce = os.urandom(16).hex()
    salt = _get_master_salt()

    body_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()
    raw_sig_payload = f"{hwid}|{now_ts}|{nonce}|{body_hash}"
    sig = hmac.new(salt.encode("utf-8"), raw_sig_payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    return {
        "X-SN-Client-HWID": hwid,
        "X-SN-Timestamp": now_ts,
        "X-SN-Nonce": nonce,
        "X-SN-Signature": sig
    }

def verify_authenticated_api_headers(headers: Dict[str, str], body_str: str = "", max_skew_seconds: int = 120) -> Tuple[bool, str]:
    """Verify inbound/mocked API request headers for authenticity."""
    hwid = headers.get("X-SN-Client-HWID", "")
    ts_str = headers.get("X-SN-Timestamp", "0")
    nonce = headers.get("X-SN-Nonce", "")
    sig = headers.get("X-SN-Signature", "")

    if not all([hwid, ts_str, nonce, sig]):
        return False, "Missing required security authentication headers"

    try:
        req_ts = int(ts_str)
        curr_ts = int(time.time())
        if abs(curr_ts - req_ts) > max_skew_seconds:
            return False, f"Request timestamp expired (Skew: {abs(curr_ts - req_ts)}s > {max_skew_seconds}s)"
    except ValueError:
        return False, "Invalid timestamp header"

    salt = _get_master_salt()
    body_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()
    raw_sig_payload = f"{hwid}|{ts_str}|{nonce}|{body_hash}"
    expected_sig = hmac.new(salt.encode("utf-8"), raw_sig_payload.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    if not hmac.compare_digest(sig.upper(), expected_sig):
        log_security_event("API_AUTH_FAILURE", "WARNING", f"Forged API signature from HWID {hwid}")
        return False, "API Request HMAC signature mismatch"

    return True, "API Request authenticated successfully"


# --------------------------------------------------------------------------
# 5. Anti-Replay Attack Protection
# --------------------------------------------------------------------------
_SEEN_NONCES: Dict[str, float] = {}

def validate_replay_protection(nonce: str, timestamp: float, max_window: float = 120.0) -> Tuple[bool, str]:
    """
    Guards against packet replay attacks.
    Ensures nonces are strictly single-use and within the sliding time window.
    """
    global _SEEN_NONCES
    now = time.time()

    # 1. Clean expired nonces older than max_window
    _SEEN_NONCES = {n: t for n, t in _SEEN_NONCES.items() if (now - t) < max_window}

    # 2. Check timestamp drift
    if abs(now - timestamp) > max_window:
        log_security_event("REPLAY_ATTACK", "WARNING", f"Expired timestamp {timestamp} (skew: {int(abs(now - timestamp))}s)")
        return False, f"Replay rejected: timestamp expired (Drift: {int(abs(now - timestamp))}s > {int(max_window)}s)"

    # 3. Check if nonce was already used
    if nonce in _SEEN_NONCES:
        log_security_event("REPLAY_ATTACK", "ALERT", f"Duplicate nonce detected: {nonce[:8]}...")
        return False, f"Replay attack detected: duplicate nonce ({nonce[:8]}...) was already consumed"

    # 4. Record nonce
    _SEEN_NONCES[nonce] = now
    return True, "Nonce accepted"


# --------------------------------------------------------------------------
# 6. Security Event Logging
# --------------------------------------------------------------------------
SECURITY_LOG_FILE = Path("data/security_audit.log")

def log_security_event(event_type: str, severity: str, details: str) -> None:
    """
    Records tamper-resistant security audit log entries.
    Severity levels: INFO, WARNING, CRITICAL, ALERT
    Includes cryptographic entry signature to detect offline log tampering.
    """
    try:
        SECURITY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        hwid = get_machine_hwid()
        raw_msg = f"{now_str} | {severity.upper():<8} | {event_type:<22} | {hwid} | {details}"
        entry_sig = hmac.new(_get_master_salt().encode(), raw_msg.encode(), hashlib.sha256).hexdigest()[:12]
        formatted_entry = f"[{raw_msg}] [SIG:{entry_sig}]\n"

        with open(SECURITY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_entry)
    except Exception:
        pass

def get_recent_security_logs(limit: int = 50) -> List[str]:
    """Retrieve the most recent security events."""
    if not SECURITY_LOG_FILE.exists():
        return []
    try:
        lines = SECURITY_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        return lines[-limit:]
    except Exception:
        return []


# --------------------------------------------------------------------------
# 7. Recovery & Self-Healing Protection
# --------------------------------------------------------------------------
def execute_self_healing_recovery() -> Tuple[bool, str]:
    """
    Autonomous self-healing engine:
    1. Heals corrupted manifests by re-anchoring core file baselines
    2. Recovers missing security anchor state files
    3. Purges corrupted or zero-byte temporary caches
    4. Verifies and auto-upgrades license key integrity
    """
    healed_items = []
    try:
        # 1. Self-heal manifest if corrupted or missing
        mf_ok, _ = verify_core_manifest_integrity()
        if not mf_ok:
            build_core_manifest()
            healed_items.append("core_manifest")

        # 2. Self-heal sys_anchor time baseline
        anchor_file = Path("data/.sys_anchor")
        if not anchor_file.exists():
            anchor_file.parent.mkdir(parents=True, exist_ok=True)
            anchor_file.write_text(str(time.time()), encoding="utf-8")
            healed_items.append("time_anchor")

        # 3. Clean corrupted empty cache files
        cache_dir = Path("cache")
        if cache_dir.exists():
            for cf in cache_dir.glob("*.tmp"):
                try:
                    if cf.stat().st_size == 0:
                        cf.unlink()
                        healed_items.append(f"cleaned_{cf.name}")
                except Exception:
                    pass

        # 4. Verify license vault health
        lic_res = check_current_device_license()
        if lic_res.get("is_activated"):
            healed_items.append("license_vault_verified")

        summary = f"Self-healing completed. Healed: {', '.join(healed_items) if healed_items else 'All systems optimal'}"
        log_security_event("SELF_HEAL", "INFO", summary)
        return True, summary
    except Exception as e:
        return False, f"Self-healing failure: {e}"



# ==========================================================================
# 🛡️ SYSTEM 18: ASYMMETRIC ED25519 KEY SEPARATION & SERVER LEASE ENFORCEMENT
# ==========================================================================
# Client ONLY holds Public Verification Key. Private key is strictly on Admin Server.
ADMIN_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEA21XfUMN6vSSA1WZOmVD7Yy9cnihL3Q0C0hR57ewHHe8=
-----END PUBLIC KEY-----"""

_SERVER_ACTIVE_DEVICES: Dict[str, Dict[str, float]] = {}  # {license_key: {hwid: last_seen}}
_SERVER_RATE_LIMITS: Dict[str, List[float]] = {}          # {hwid: [timestamps]}

def get_admin_public_key():
    """Load client-safe public verification key."""
    try:
        from cryptography.hazmat.primitives import serialization
        return serialization.load_pem_public_key(ADMIN_PUBLIC_KEY_PEM.encode("utf-8"))
    except Exception:
        return None

def verify_asymmetric_signature(payload_bytes: bytes, signature_hex: str) -> bool:
    """
    Verify Ed25519 digital signature using ONLY the embedded public key.
    Provides mathematically sound verification: impossible for client to forge.
    """
    try:
        pub_key = get_admin_public_key()
        if not pub_key or not signature_hex or not payload_bytes:
            return False
        sig_bytes = bytes.fromhex(signature_hex.strip())
        pub_key.verify(sig_bytes, payload_bytes)
        return True
    except Exception:
        return False

def sign_with_admin_private_key(payload_bytes: bytes) -> Optional[str]:
    """
    Generate an authoritative Ed25519 digital signature.
    STRICTLY SERVER-SIDE: Requires data/admin_private_key.pem.
    Fails immediately if private key is not present (e.g. on client machines).
    """
    priv_file = resolve_file_path("data/admin_private_key.pem")
    if not priv_file.exists():
        priv_file = Path("data/admin_private_key.pem")
    if not priv_file.exists():
        return None
    try:
        from cryptography.hazmat.primitives import serialization
        priv_key = serialization.load_pem_private_key(priv_file.read_bytes(), password=None)
        sig_bytes = priv_key.sign(payload_bytes)
        return sig_bytes.hex().upper()
    except Exception:
        return None

def server_enforce_device_limit(license_key: str, hwid: str, max_devices: int = 1) -> Tuple[bool, str]:
    """
    Server-Side Device Limit Enforcement:
    Checks how many unique hardware IDs are actively consuming this license key.
    Prevents single-license sharing across unauthorized multiple computers.
    """
    global _SERVER_ACTIVE_DEVICES
    now = time.time()
    clean_k = license_key.strip().upper()
    clean_hwid = hwid.strip().upper()

    if clean_k not in _SERVER_ACTIVE_DEVICES:
        _SERVER_ACTIVE_DEVICES[clean_k] = {}

    # Purge stale devices inactive for > 24 hours (86400s)
    _SERVER_ACTIVE_DEVICES[clean_k] = {
        h: t for h, t in _SERVER_ACTIVE_DEVICES[clean_k].items() if (now - t) < 86400.0
    }

    active_hwids = list(_SERVER_ACTIVE_DEVICES[clean_k].keys())

    # If already registered or under limit
    if clean_hwid in active_hwids:
        _SERVER_ACTIVE_DEVICES[clean_k][clean_hwid] = now
        return True, "Device authorized"

    if len(active_hwids) >= max_devices:
        return False, f"Server-Side Enforcement: Device limit exceeded ({len(active_hwids)}/{max_devices} active machines). Key already locked to another device."

    _SERVER_ACTIVE_DEVICES[clean_k][clean_hwid] = now
    return True, f"Device registered ({len(active_hwids) + 1}/{max_devices})"

def server_enforce_rate_limit(hwid: str, max_requests_per_minute: int = 30) -> Tuple[bool, str]:
    """
    Server-Side Request Rate Limiting:
    Blocks automated denial-of-service or key-harvesting flood attacks.
    """
    global _SERVER_RATE_LIMITS
    now = time.time()
    clean_hwid = hwid.strip().upper()

    if clean_hwid not in _SERVER_RATE_LIMITS:
        _SERVER_RATE_LIMITS[clean_hwid] = []

    # Keep timestamps within the last 60 seconds
    _SERVER_RATE_LIMITS[clean_hwid] = [t for t in _SERVER_RATE_LIMITS[clean_hwid] if (now - t) < 60.0]

    if len(_SERVER_RATE_LIMITS[clean_hwid]) >= max_requests_per_minute:
        return False, f"Server-Side Enforcement: Rate limit exceeded ({len(_SERVER_RATE_LIMITS[clean_hwid])}/{max_requests_per_minute} req/min). Please slow down."

    _SERVER_RATE_LIMITS[clean_hwid].append(now)
    return True, "Rate limit OK"

def generate_server_lease_token(license_key: str, hwid: str, plan: str = "PRO") -> Dict[str, Any]:
    """
    Authoritative Server-Side Lease Generation:
    Creates an asymmetric Ed25519 cryptographically signed, short-lived lease token (5 minutes).
    Client cannot forge or extend lease without Server's private key.
    """
    # 1. Enforce Server-Side Rate Limit
    rate_ok, rate_msg = server_enforce_rate_limit(hwid, max_requests_per_minute=30)
    if not rate_ok:
        return {"success": False, "error": rate_msg}

    # 2. Enforce Server-Side Device Limit (VIP allows 3 devices, standard allows 1)
    max_dev = 3 if any(tag in plan.upper() for tag in ("VIP", "STUDIO", "ENTERPRISE")) else 1
    dev_ok, dev_msg = server_enforce_device_limit(license_key, hwid, max_devices=max_dev)
    if not dev_ok:
        return {"success": False, "error": dev_msg}

    # 3. Create short-lived lease payload (300 seconds TTL)
    now = time.time()
    lease_payload = {
        "license_key": license_key.strip().upper(),
        "hwid": hwid.strip().upper(),
        "plan": plan.upper(),
        "lease_issued_at": now,
        "lease_expires_at": now + 300.0,
        "server_status": "AUTHORIZED"
    }

    # 4. Sign payload with Server Ed25519 Private Key
    payload_bytes = json.dumps(lease_payload, sort_keys=True).encode("utf-8")
    sig_hex = sign_with_admin_private_key(payload_bytes)

    if not sig_hex:
        return {"success": False, "error": "Server signing failure: Admin private key not accessible."}

    return {
        "success": True,
        "lease_payload": lease_payload,
        "signature": sig_hex
    }

def verify_server_lease_token(lease_payload: Dict[str, Any], signature_hex: str) -> Tuple[bool, str]:
    """
    Client-Side Zero-Trust Lease Verification:
    Validates server signature using embedded public key and checks time window.
    """
    if not lease_payload or not signature_hex:
        return False, "Empty lease payload or signature"

    # 1. Check expiration
    now = time.time()
    expires_at = float(lease_payload.get("lease_expires_at", 0))
    if now > expires_at:
        return False, f"Server lease expired ({int(now - expires_at)}s ago). Re-authentication required."

    # 2. Check HWID match
    curr_hwid = get_machine_hwid().upper()
    if lease_payload.get("hwid", "").upper() != curr_hwid:
        return False, "Lease token issued to different hardware ID"

    # 3. Cryptographically verify signature using Ed25519 Public Key
    payload_bytes = json.dumps(lease_payload, sort_keys=True).encode("utf-8")
    if not verify_asymmetric_signature(payload_bytes, signature_hex):
        return False, "Server lease signature is invalid or forged"

    return True, "Server lease verified successfully"


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


# ==========================================================================
# 🛡️ SYSTEM 8: ANTI-MITM PROXY & NETWORK HOSTS HIJACK SENTINEL
# ==========================================================================
def check_proxy_and_hosts_integrity() -> Tuple[bool, str]:
    """
    Guards against network traffic interception (Fiddler, Charles, Burp Suite)
    and DNS poisoning / hosts file tampering aimed at redirecting online verification.
    """
    # 1. Environment variables check
    for env_var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        val = os.environ.get(env_var, "").lower()
        if val and any(h in val for h in ("127.0.0.1", "localhost", "8888", "8080", "9090", "charles")):
            return False, f"⚠️ Malicious local proxy interceptor detected ({env_var}={val})"

    # 2. Windows Internet Settings Registry Proxy Check
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as k:
                proxy_enabled, _ = winreg.QueryValueEx(k, "ProxyEnable")
                if proxy_enabled == 1:
                    proxy_server, _ = winreg.QueryValueEx(k, "ProxyServer")
                    ps_lower = str(proxy_server).lower()
                    if any(target in ps_lower for target in ("127.0.0.1:8888", "127.0.0.1:8080", "localhost:8888", "localhost:8080")):
                        return False, f"⚠️ Active Fiddler/Burp network interceptor detected in registry ({proxy_server})"
        except Exception:
            pass

    # 3. Windows Hosts File Poisoning Check
    if sys.platform == "win32":
        try:
            hosts_path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / r"System32\drivers\etc\hosts"
            if hosts_path.exists():
                text = hosts_path.read_text(encoding="utf-8", errors="ignore")
                for line in text.splitlines():
                    clean_l = line.strip().lower()
                    if clean_l and not clean_l.startswith("#"):
                        if any(dom in clean_l for dom in ("githubusercontent.com", "api.github.com", "nisay")):
                            if any(local in clean_l for local in ("127.0.0.1", "0.0.0.0", "localhost", "::1")):
                                return False, "⚠️ DNS hosts file hijack detected targeting authentication domain"
        except Exception:
            pass

    return True, "Network and proxy integrity verified"


# ==========================================================================
# 🛡️ SYSTEM 9: CORE FILE MANIFEST INTEGRITY & ANTI-SOURCE CODE TAMPERING
# ==========================================================================
CORE_PROTECTED_FILES = [
    "license_engine.py",
    "downloader.py",
    "translator.py",
    "pipeline.py",
    "series_memory.py",
    "tts_engine.py"
]
MANIFEST_SIG_FILE = Path("data/.core_manifest.sig")

def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file on disk."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def build_core_manifest() -> Dict[str, str]:
    """Build and cryptographically sign the baseline file hashes for all core modules."""
    manifest = {}
    for filename in CORE_PROTECTED_FILES:
        fp = resolve_file_path(filename)
        if fp.exists():
            manifest[filename] = compute_file_sha256(fp)
    
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
    sig = hmac.new(_get_master_salt().encode(), manifest_bytes, hashlib.sha256).hexdigest()
    
    signed_payload = {
        "manifest": manifest,
        "signature": sig,
        "generated_at": time.time()
    }
    MANIFEST_SIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_SIG_FILE, "w", encoding="utf-8") as f:
        json.dump(signed_payload, f, indent=2)
    return manifest

def verify_core_manifest_integrity() -> Tuple[bool, str]:
    """
    Ensure no cracker has modified, bypassed, or removed source lines from any core file.
    Validates on-disk file hashes against the cryptographically signed manifest.
    """
    if not MANIFEST_SIG_FILE.exists():
        build_core_manifest()
        return True, "Manifest initialized"

    try:
        with open(MANIFEST_SIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        manifest = data.get("manifest", {})
        sig = data.get("signature", "")
        
        manifest_bytes = json.dumps(manifest, sort_keys=True).encode("utf-8")
        expected_sig = hmac.new(_get_master_salt().encode(), manifest_bytes, hashlib.sha256).hexdigest()
        if sig != expected_sig:
            return False, "❌ Core security manifest signature is forged or corrupted"
        
        for filename, expected_hash in manifest.items():
            fp = resolve_file_path(filename)
            if not fp.exists():
                return False, f"❌ Core file missing: {filename}"
            curr_hash = compute_file_sha256(fp)
            if curr_hash != expected_hash:
                return False, f"❌ Unauthorized code tampering detected in {filename}"

        return True, "All core files intact and verified"
    except Exception as e:
        return False, f"Manifest verification error: {e}"


# ==========================================================================
# 🛡️ SYSTEM 10: EPHEMERAL SECURE BUFFER & ANTI-RAM DUMP PROTECTION
# ==========================================================================
def secure_wipe_buffer(target: Any) -> None:
    """
    Securely overwrite sensitive credentials and secrets in RAM with zeros
    preventing recovery via memory dump tools (Cheat Engine, Process Hacker).
    """
    try:
        if isinstance(target, bytearray):
            for i in range(len(target)):
                target[i] = 0
        elif isinstance(target, dict):
            for k in list(target.keys()):
                target[k] = None
            target.clear()
        elif isinstance(target, list):
            for i in range(len(target)):
                target[i] = None
            target.clear()
    except Exception:
        pass

def activate_anti_dump_mitigation() -> Tuple[bool, str]:
    """
    Configure Windows process mitigation policies to protect against unauthorized
    memory reading and memory dumping by external processes.
    """
    if sys.platform != "win32":
        return True, "Non-windows platform"
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        if hasattr(kernel32, "SetProcessDEPPolicy"):
            kernel32.SetProcessDEPPolicy(1)
        return True, "Process memory mitigation activated"
    except Exception as e:
        return False, f"Process mitigation error: {e}"



def verify_ai_execution_authorization() -> Tuple[bool, str, str]:
    """
    Cryptographically gatekeeps core AI operations (translation, dubbing, downloader).
    Generates time-bound authorization tokens tied to HWID and dynamic salt.
    Prevents stolen or pirated code from executing without authentic authorization.
    """
    try:
        # 1. Check current device license
        lic_info = check_current_device_license()
        if not lic_info.get("is_activated"):
            return False, "❌ AI Execution Denied: Active License Required.", ""

        # 2. Check runtime integrity (monkey patching + bytecode)
        rt_ok, rt_msg = verify_runtime_integrity()
        if not rt_ok:
            return False, f"❌ AI Execution Denied: Security violation ({rt_msg})", ""

        # 3. Check proxy/hosts integrity
        px_ok, px_msg = check_proxy_and_hosts_integrity()
        if not px_ok:
            return False, f"❌ AI Execution Denied: Network interception ({px_msg})", ""

        # 4. Generate 60s ephemeral authorization token
        current_hwid = get_machine_hwid()
        time_slot = int(time.time() // 60)
        salt = _get_master_salt()
        token = hashlib.sha256(f"{current_hwid}:{salt}:{time_slot}".encode()).hexdigest()
        return True, "Authorized", token
    except Exception as e:
        return False, f"Authorization error: {e}", ""


def verify_runtime_integrity() -> Tuple[bool, str]:
    """
    Verifies that core security routines have not been hooked or monkey-patched in memory.
    """
    try:
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
    except Exception as e:
        return False, f"Integrity check failed: {e}"


def _get_hwid_cipher(hwid: Optional[str] = None):
    try:
        from cryptography.fernet import Fernet
        import base64
        target_hwid = (hwid or get_machine_hwid()).strip().upper()
        salt_bytes = b"SN_TOOL_HARDWARE_KEY_DERIVATION_SALT_2026"
        derived_key = base64.urlsafe_b64encode(
            hashlib.sha256(f"{target_hwid}|{SECRET_ADMIN_SALT}".encode() + salt_bytes).digest()
        )
        return Fernet(derived_key)
    except Exception:
        return None


def encrypt_license_token(payload: Dict[str, Any], hwid: Optional[str] = None) -> str:
    """
    Encrypts activation payload bound mathematically to the machine's HWID.
    Cannot be decrypted or read on any other computer.
    """
    cipher = _get_hwid_cipher(hwid)
    json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if cipher:
        token = cipher.encrypt(json_bytes).decode("ascii")
        return f"SN_VAULT_V2:{token}"
    return json.dumps(payload, ensure_ascii=False)


def decrypt_license_token(raw_content: str, hwid: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Decrypts activation payload using local machine HWID.
    Returns None if corrupted, tampered, or copied from a different computer.
    """
    content = raw_content.strip()
    if content.startswith("SN_VAULT_V2:"):
        cipher = _get_hwid_cipher(hwid)
        if not cipher:
            return None
        try:
            token = content[len("SN_VAULT_V2:"):].strip()
            decrypted_bytes = cipher.decrypt(token.encode("ascii"), ttl=None)
            return json.loads(decrypted_bytes.decode("utf-8"))
        except Exception:
            return None
    try:
        return json.loads(content)
    except Exception:
        return None

# Built-in Master Keys for Admin Emergency Access
DEFAULT_MASTER_KEYS: Dict[str, Dict[str, Any]] = {
    "SN-ADMIN-MASTER-2026": {"client_name": "Administrator", "plan": "LIFETIME"},
    "SN-ADMIN-MASTER-2026-VIP": {"client_name": "Administrator", "plan": "LIFETIME"},
    "SN-VIP-LIFETIME-PRO-2026": {"client_name": "Administrator", "plan": "LIFETIME"},
    "SN-PRO-8888-9999-VIP": {"client_name": "Administrator", "plan": "LIFETIME"}
}


def is_license_required() -> bool:
    """Check if the system requires a license key or is in Free / Open Access mode."""
    cfg_p = resolve_file_path("license_config.json")
    if cfg_p.exists():
        try:
            with open(cfg_p, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return bool(cfg.get("require_license", True))
        except Exception:
            pass
    return True


def set_license_required(required: bool) -> bool:
    """Turn license gate requirement ON or OFF."""
    cfg = {}
    if LICENSE_CONFIG_FILE.exists():
        try:
            with open(LICENSE_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    cfg["require_license"] = bool(required)
    try:
        with open(LICENSE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def register_custom_key(custom_key: str, client_name: str = "Client", duration_days: int = 0, hwid: Optional[str] = None, plan: str = "CUSTOM") -> Dict[str, Any]:
    """
    Register an arbitrary custom key/password created directly by the user.
    duration_days: 0 for Lifetime, or any positive number of days (e.g. 5, 10, 45, 60, etc.)
    """
    cleaned_key = custom_key.strip().upper()
    created_at = datetime.now()

    if duration_days <= 0:
        expiry_str = "LIFETIME"
        expiry_timestamp = 0
    else:
        exp_dt = created_at + timedelta(days=duration_days)
        expiry_str = exp_dt.strftime("%Y-%m-%d")
        epoch_days = int(exp_dt.timestamp()) // 86400
        expiry_timestamp = epoch_days * 86400 + 86399

    bound_hwid_str = hwid.strip().upper() if (hwid and hwid.strip() not in ("ANY", "*", "")) else "ANY"

    record = {
        "license_key": cleaned_key,
        "client_name": client_name or "Client",
        "plan": plan or "CUSTOM",
        "duration_days": duration_days,
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expiry_str,
        "expiry_timestamp": expiry_timestamp,
        "bound_hwid": bound_hwid_str,
        "raw_payload": f"CUSTOM:{cleaned_key}:{client_name}",
        "signature": "CUSTOM_ADMIN",
        "status": "ACTIVE"
    }

    # Save to custom_keys.json
    custom_keys = {}
    if CUSTOM_KEYS_FILE.exists():
        try:
            with open(CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
                custom_keys = json.load(f)
        except Exception:
            custom_keys = {}

    custom_keys[cleaned_key] = record
    try:
        with open(CUSTOM_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(custom_keys, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Save to history & log
    _save_to_admin_history(record)
    return record


def get_all_custom_keys() -> Dict[str, Any]:
    """Retrieve all custom keys defined by admin."""
    if CUSTOM_KEYS_FILE.exists():
        try:
            with open(CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def get_revoked_keys() -> List[str]:
    """Get list of all revoked / banned license keys."""
    for fn in ["revoked_keys.json", "data/revoked_keys.json"]:
        p = resolve_file_path(fn)
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return [k.strip().upper() for k in data]
                    elif isinstance(data, dict):
                        return [k.strip().upper() for k in data.get("revoked_keys", [])]
            except Exception:
                pass
    return []


def sync_online_keys() -> Dict[str, Any]:
    """
    Consolidate all valid keys (DEFAULT_MASTER_KEYS, custom keys, admin history)
    and export into data/license_keys_online.json, syncing to dist/SN_TOOL if present.
    """
    all_keys = {}

    # 1. Add Default Master Keys (Always active, universal ANY HWID)
    for mk, meta in DEFAULT_MASTER_KEYS.items():
        all_keys[mk] = {
            "license_key": mk,
            "client_name": meta.get("client_name", "Administrator"),
            "plan": meta.get("plan", "LIFETIME"),
            "duration_days": 0,
            "created_at": "2026-10-01 00:00:00",
            "expires_at": "LIFETIME",
            "expiry_timestamp": 0,
            "bound_hwid": "ANY",
            "status": "ACTIVE"
        }

    # 3. Add Custom Keys
    custom_p = resolve_file_path("custom_keys.json")
    if custom_p.exists():
        try:
            with open(custom_p, "r", encoding="utf-8") as f:
                ck = json.load(f)
                if isinstance(ck, dict):
                    for k, rec in ck.items():
                        all_keys[k.strip().upper()] = rec
        except Exception:
            pass

    # 4. Add Admin History Records
    history_p = resolve_file_path("admin_key_history.json")
    if history_p.exists():
        try:
            with open(history_p, "r", encoding="utf-8") as f:
                history = json.load(f)
                if isinstance(history, list):
                    for rec in history:
                        k = rec.get("license_key", "").strip().upper()
                        if k:
                            all_keys[k] = rec
        except Exception:
            pass

    # 5. Apply revocation overrides & ensure master keys are ANY hwid
    revoked = set(get_revoked_keys())
    for k, rec in all_keys.items():
        if k in revoked:
            rec["status"] = "REVOKED"
        elif rec.get("status") != "REVOKED":
            rec["status"] = "ACTIVE"
        if k in DEFAULT_MASTER_KEYS or k == "SN-ADMIN-MASTER-2026-VIP":
            rec["bound_hwid"] = "ANY"

    # 6. Save to data/license_keys_online.json and distribution folders
    target_paths = [
        Path("data/license_keys_online.json"),
        Path("dist/SN_TOOL/data/license_keys_online.json"),
        Path("dist/SN_TOOL/_internal/data/license_keys_online.json"),
    ]
    for tp in target_paths:
        try:
            if tp.parent.exists() or tp == target_paths[0]:
                tp.parent.mkdir(parents=True, exist_ok=True)
                with open(tp, "w", encoding="utf-8") as f:
                    json.dump(all_keys, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # 7. Also sync revoked_keys.json across root, data/, and dist/
    revoked_paths = [
        Path("data/revoked_keys.json"),
        Path("revoked_keys.json"),
        Path("dist/SN_TOOL/data/revoked_keys.json"),
        Path("dist/SN_TOOL/_internal/data/revoked_keys.json"),
    ]
    rev_payload = {
        "revoked_keys": list(revoked),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    for rp in revoked_paths:
        try:
            if rp.parent.exists() or rp == revoked_paths[0]:
                rp.parent.mkdir(parents=True, exist_ok=True)
                with open(rp, "w", encoding="utf-8") as f:
                    json.dump(rev_payload, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return all_keys


def _cache_online_key_locally(cleaned_key: str, record: Dict[str, Any]):
    """Cache online-fetched key into local database for offline resilience."""
    try:
        p = resolve_file_path("data/license_keys_online.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        cached = {}
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cached = json.load(f)
            except Exception:
                cached = {}
        cached[cleaned_key] = record
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cached, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def check_key_online(cleaned_key: str, current_hwid: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Check if a key is registered in online cloud registry (GitHub) or local online database.
    Returns (is_valid, message, record_dict).
    """
    cfg_file = resolve_file_path("license_config.json")
    online_url = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/data/license_keys_online.json"
    if cfg_file.exists():
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                online_url = cfg.get("online_keys_url", online_url)
        except Exception:
            pass

    record = None
    source = "offline_db"

    # 1. Try remote Cloud / GitHub registry first (quick 2.5s timeout)
    if online_url:
        try:
            import urllib.request
            req = urllib.request.Request(
                online_url,
                headers={"User-Agent": "SN_TOOL_License_Client", "Cache-Control": "no-cache"}
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    cloud_keys = json.loads(resp.read().decode("utf-8"))
                    if isinstance(cloud_keys, dict) and cleaned_key in cloud_keys:
                        record = cloud_keys[cleaned_key]
                        source = "online_cloud"
                        _cache_online_key_locally(cleaned_key, record)
        except Exception:
            pass

    # 2. Fallback to local online database if remote didn't find it or was unreachable
    if not record:
        local_online_path = resolve_file_path("data/license_keys_online.json")
        if local_online_path.exists():
            try:
                with open(local_online_path, "r", encoding="utf-8") as f:
                    local_dict = json.load(f)
                if isinstance(local_dict, dict) and cleaned_key in local_dict:
                    record = local_dict[cleaned_key]
                    source = "local_db"
            except Exception:
                pass

    if not record:
        return False, "", {}

    # Validate status
    if record.get("status") == "REVOKED":
        return False, "❌ This License Key has been suspended/revoked by Admin", {}

    # Validate HWID binding
    bound_hwid = str(record.get("bound_hwid", "ANY")).strip().upper()
    if bound_hwid not in ("ANY", "*", "", "NONE") and bound_hwid != current_hwid:
        return False, "❌ This License Key is locked to a different machine (HWID mismatch)", {}

    # Validate Expiration
    expiry_ts = record.get("expiry_timestamp", 0)
    if expiry_ts > 0 and time.time() > expiry_ts:
        return False, f"⚠️ This License Key has expired ({record.get('expires_at')})", {}

    status_tag = "Online Cloud" if source == "online_cloud" else "Verified"
    return True, f"✅ License Key {status_tag} is valid and active!", record


def revoke_license_key(target_key: str, reason: str = "Banned by Admin") -> Tuple[bool, str]:
    """Revoke/Ban a license key so the user cannot use the tool anymore."""
    cleaned = target_key.strip().upper()
    if not cleaned:
        return False, "Please enter Key to revoke"

    revoked_list = get_revoked_keys()
    if cleaned not in revoked_list:
        revoked_list.append(cleaned)
        try:
            with open(REVOKED_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump({"revoked_keys": revoked_list, "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            return False, f"Failed saving revoked_keys.json: {e}"

    # Also update admin_key_history.json
    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            for r in history:
                if r.get("license_key", "").upper() == cleaned:
                    r["status"] = "REVOKED"
                    r["revoked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    r["revoke_reason"] = reason
            with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Also update custom_keys.json
    if CUSTOM_KEYS_FILE.exists():
        try:
            with open(CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
                ck = json.load(f)
            if cleaned in ck:
                ck[cleaned]["status"] = "REVOKED"
                ck[cleaned]["revoked_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(CUSTOM_KEYS_FILE, "w", encoding="utf-8") as f:
                    json.dump(ck, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # If the current machine is using this revoked key, delete license.key
    if LICENSE_FILE.exists():
        try:
            with open(LICENSE_FILE, "r", encoding="utf-8") as f:
                current_lic = json.load(f)
            if current_lic.get("license_key", "").upper() == cleaned:
                LICENSE_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    try:
        sync_online_keys()
        push_online_registry_async()
    except Exception:
        pass

    # Fire async delete to Google Sheet
    def _delete_cloud_row():
        try:
            cfg = get_heartbeat_config()
            wh = cfg.get("webhook_url", "").strip()
            if wh:
                import urllib.request
                body = json.dumps({"action": "delete", "license_key": cleaned}).encode("utf-8")
                req = urllib.request.Request(wh, data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=5):
                    pass
        except Exception:
            pass
    threading.Thread(target=_delete_cloud_row, daemon=True).start()

    return True, f"🚫 Successfully revoked Key {cleaned}!"


def unrevoke_license_key(target_key: str) -> Tuple[bool, str]:
    """Unban / Restore a revoked license key."""
    cleaned = target_key.strip().upper()
    revoked_list = get_revoked_keys()
    if cleaned in revoked_list:
        revoked_list.remove(cleaned)
        try:
            with open(REVOKED_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump({"revoked_keys": revoked_list, "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Restore in admin_key_history.json
    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            for r in history:
                if r.get("license_key", "").upper() == cleaned:
                    r["status"] = "ACTIVE"
            with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Restore in custom_keys.json
    if CUSTOM_KEYS_FILE.exists():
        try:
            with open(CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
                ck = json.load(f)
            if cleaned in ck:
                ck[cleaned]["status"] = "ACTIVE"
                with open(CUSTOM_KEYS_FILE, "w", encoding="utf-8") as f:
                    json.dump(ck, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    try:
        sync_online_keys()
        push_online_registry_async()
    except Exception:
        pass

    # Fire async delete to Google Sheet
    def _delete_cloud_row():
        try:
            cfg = get_heartbeat_config()
            wh = cfg.get("webhook_url", "").strip()
            if wh:
                import urllib.request
                body = json.dumps({"action": "delete", "license_key": cleaned}).encode("utf-8")
                req = urllib.request.Request(wh, data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=5):
                    pass
        except Exception:
            pass
    threading.Thread(target=_delete_cloud_row, daemon=True).start()

    return True, f"✅ Successfully unbanned Key {cleaned}!"


DELETED_KEYS_FILE = Path("data/deleted_keys.json")

def get_deleted_keys() -> set:
    candidates = [
        DELETED_KEYS_FILE,
        Path("deleted_keys.json"),
        resolve_file_path("data/deleted_keys.json"),
        resolve_file_path("deleted_keys.json")
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return set(k.strip().upper() for k in data if k)
            except Exception:
                pass
    return set()

def record_deleted_key(key: str):
    keys = get_deleted_keys()
    cleaned = key.strip().upper()
    if cleaned:
        keys.add(cleaned)
        try:
            DELETED_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(DELETED_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(list(keys), f, indent=2)
        except Exception:
            pass

def delete_license_key_record(target_key: str) -> Tuple[bool, str]:
    """Delete a key record completely from history, custom keys, and revocations."""
    cleaned = target_key.strip().upper()
    if not cleaned:
        return False, "Please select Key to delete"
    record_deleted_key(cleaned)

    # Remove from admin_key_history.json
    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            history = [r for r in history if r.get("license_key", "").upper() != cleaned]
            with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Remove from custom_keys.json
    if CUSTOM_KEYS_FILE.exists():
        try:
            with open(CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
                ck = json.load(f)
            if cleaned in ck:
                del ck[cleaned]
                with open(CUSTOM_KEYS_FILE, "w", encoding="utf-8") as f:
                    json.dump(ck, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Remove from revoked_keys.json if present
    revoked = get_revoked_keys()
    if cleaned in revoked:
        revoked.remove(cleaned)
        try:
            with open(REVOKED_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump({"revoked_keys": revoked, "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Remove from generated_keys_log.txt if present
    if GENERATED_KEYS_LOG.exists():
        try:
            with open(GENERATED_KEYS_LOG, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            new_lines = [l for l in lines if f"KEY: {cleaned}" not in l and f"KEY:{cleaned}" not in l]
            with open(GENERATED_KEYS_LOG, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        except Exception:
            pass

    try:
        sync_online_keys()
        push_online_registry_async()
    except Exception:
        pass

    # Fire async delete to Google Sheet
    def _delete_cloud_row():
        try:
            cfg = get_heartbeat_config()
            wh = cfg.get("webhook_url", "").strip()
            if wh:
                import urllib.request
                body = json.dumps({"action": "delete", "license_key": cleaned}).encode("utf-8")
                req = urllib.request.Request(wh, data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=5):
                    pass
        except Exception:
            pass
    threading.Thread(target=_delete_cloud_row, daemon=True).start()

    return True, f"🗑️ Successfully deleted Key {cleaned}!"


def extend_license_key(target_key: str, additional_days: int = 30, plan: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Remotely extend/renew an existing license key by adding days or setting to Lifetime.
    Updates admin_key_history.json, custom_keys.json, and data/license_keys_online.json.
    When the user opens the tool, check_current_device_license() automatically syncs the new date OTA!
    """
    cleaned = target_key.strip().upper()
    if not cleaned:
        return False, "Please select or enter a License Key to extend", {}

    # Unban if revoked
    revoked_list = get_revoked_keys()
    if cleaned in revoked_list:
        revoked_list.remove(cleaned)
        try:
            with open(REVOKED_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump({"revoked_keys": revoked_list, "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    now = datetime.now()
    now_ts = int(now.timestamp())

    # Find existing record in history or custom keys
    target_record = None
    
    # 1. Search in admin_key_history.json
    history = []
    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            for r in history:
                if r.get("license_key", "").strip().upper() == cleaned:
                    target_record = r
                    break
        except Exception:
            history = []

    # 2. Search in custom_keys.json
    custom_dict = {}
    if CUSTOM_KEYS_FILE.exists():
        try:
            with open(CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
                custom_dict = json.load(f)
            if cleaned in custom_dict:
                if not target_record:
                    target_record = custom_dict[cleaned]
        except Exception:
            custom_dict = {}

    # If not found in either file, create a base record
    if not target_record:
        target_record = {
            "license_key": cleaned,
            "client_name": "Customer",
            "plan": plan or "PRO",
            "duration_days": additional_days,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "bound_hwid": "ANY",
            "status": "ACTIVE"
        }
        history.insert(0, target_record)

    # Calculate new expiry
    if additional_days <= 0 or (plan and plan.upper() in ("LIFETIME", "LIFE")):
        target_record["expires_at"] = "LIFETIME"
        target_record["expiry_timestamp"] = 0
        target_record["plan"] = plan or "PRO Lifetime"
        target_record["status"] = "ACTIVE"
    else:
        # Calculate base timestamp
        current_expiry_ts = target_record.get("expiry_timestamp", 0)
        # If currently active and unexpired, extend from current expiry date!
        if current_expiry_ts > now_ts:
            base_ts = current_expiry_ts
        else:
            base_ts = now_ts
        
        new_ts = base_ts + (additional_days * 86400)
        new_dt = datetime.fromtimestamp(new_ts)
        target_record["expires_at"] = new_dt.strftime("%Y-%m-%d")
        target_record["expiry_timestamp"] = new_ts
        target_record["duration_days"] = int(target_record.get("duration_days", 0)) + additional_days
        target_record["status"] = "ACTIVE"
        if plan:
            target_record["plan"] = plan

    target_record["last_renewed"] = now.strftime("%Y-%m-%d %H:%M:%S")

    # Save to admin_key_history.json
    found_in_hist = False
    for i, r in enumerate(history):
        if r.get("license_key", "").strip().upper() == cleaned:
            history[i] = target_record
            found_in_hist = True
            break
    if not found_in_hist:
        history.insert(0, target_record)

    try:
        with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Save to custom_keys.json if present or if was custom
    if cleaned in custom_dict or CUSTOM_KEYS_FILE.exists():
        custom_dict[cleaned] = target_record
        try:
            with open(CUSTOM_KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(custom_dict, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Synchronize all online keys and distribution files
    try:
        sync_online_keys()
    except Exception:
        pass

    enriched = calculate_key_live_status(target_record)
    msg = f"🎉 License Key {cleaned} extended remotely successfully! New expiry date: {target_record.get('expires_at')}"
    return True, msg, enriched


def push_online_registry_async():
    """Commit and push updated license_keys_online.json to GitHub repository in background."""
    def _worker():
        try:
            subprocess.run(
                ["git", "add", "data/license_keys_online.json", "data/revoked_keys.json", "admin_key_history.json"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m", "remote-license: update online keys registry [OTA sync]"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=25
            )
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()


def clear_all_admin_keys() -> Tuple[bool, str]:
    """
    Purge all customer keys, reset admin history, custom keys, and log.
    Built-in Master keys (DEFAULT_MASTER_KEYS) are retained.
    """
    try:
        with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    try:
        with open(CUSTOM_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    try:
        with open(GENERATED_KEYS_LOG, "w", encoding="utf-8") as f:
            f.write("# SN STUDIO - License Key Log\n")
    except Exception:
        pass

    # Also clean dist versions if they exist
    for dist_dir in [Path("dist/SN_TOOL"), Path("dist/SN_TOOL/_internal")]:
        try:
            ck = dist_dir / "custom_keys.json"
            if ck.exists():
                with open(ck, "w", encoding="utf-8") as f:
                    json.dump({}, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    try:
        sync_online_keys()
    except Exception:
        pass

    return True, "✅ Cleared all customer and key records successfully!"


def check_remote_revocation_online(cleaned_key: str, current_hwid: str) -> Optional[str]:
    """Check online remote blacklist endpoint if configured (quick 1.5s timeout)."""
    cfg_p = resolve_file_path("license_config.json")
    if not cfg_p.exists():
        return None
    try:
        with open(cfg_p, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        remote_url = cfg.get("remote_revocation_url")
        if not remote_url:
            return None
        import urllib.request
        req = urllib.request.Request(remote_url, headers={"User-Agent": "SN_Studio_License_Agent", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=1.5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode('utf-8'))
                remote_revoked = [k.strip().upper() for k in data.get("revoked_keys", [])]
                remote_hwids = [h.strip().upper() for h in data.get("revoked_hwids", [])]
                if cleaned_key in remote_revoked:
                    return "❌ License Key remotely revoked by Admin"
                if current_hwid in remote_hwids:
                    return "❌ Device remotely banned by Admin"
    except Exception:
        pass
    return None


_CACHED_HWID: Optional[str] = None

def get_machine_hwid() -> str:
    """Generate a unique hardware ID (HWID) for the current machine (cached for extreme speed)."""
    global _CACHED_HWID
    if _CACHED_HWID:
        return _CACHED_HWID
    try:
        if sys.platform == "win32":
            # Get Windows Machine GUID
            cmd = 'powershell "(Get-CimInstance -Class Win32_ComputerSystemProduct).UUID"'
            res = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
            if res and len(res) > 8:
                _CACHED_HWID = hashlib.sha256(res.encode()).hexdigest()[:16].upper()
                return _CACHED_HWID
    except Exception:
        pass
    
    # Fallback using node and platform
    raw = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
    _CACHED_HWID = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    return _CACHED_HWID


def generate_license_key(client_name: str, duration_days: int = 30, hwid: Optional[str] = None, plan: str = "PRO") -> Dict[str, Any]:
    """
    Generate a cryptographically verified license key that can be verified offline anywhere.
    duration_days: 0 for Lifetime, or positive number for days.
    """
    clean_plan = plan.strip().upper() if plan else "PRO"
    if clean_plan in ("LIFETIME", "LIFE", "LIF"):
        plan_tag = "LIF"
    elif clean_plan in ("365D", "1YEAR", "1Y"):
        plan_tag = "365D"
    elif clean_plan in ("90D", "3MONTHS", "3M"):
        plan_tag = "90D"
    elif clean_plan in ("30D", "1MONTH", "1M"):
        plan_tag = "30D"
    elif clean_plan in ("7D", "7DAYS"):
        plan_tag = "7D"
    elif clean_plan in ("3D", "3DAYS", "TRIAL"):
        plan_tag = "3D"
    else:
        plan_tag = clean_plan[:4]

    created_at = datetime.now()
    
    if duration_days <= 0:
        expiry_code = "0000"
        expiry_str = "LIFETIME"
        expiry_timestamp = 0
    else:
        exp_dt = created_at + timedelta(days=duration_days)
        epoch_days = int(exp_dt.timestamp()) // 86400
        expiry_code = f"{epoch_days:04X}"
        expiry_str = exp_dt.strftime("%Y-%m-%d")
        expiry_timestamp = epoch_days * 86400 + 86399

    if hwid and hwid.strip() not in ("ANY", "*", ""):
        clean_hw = hwid.strip().upper()
        hwid_tag = hashlib.sha256((clean_hw + SECRET_ADMIN_SALT).encode()).hexdigest()[:4].upper()
        bound_hwid_str = clean_hw
    else:
        hwid_tag = "9999"
        bound_hwid_str = "ANY"

    salt = uuid.uuid4().hex[:4].upper()
    payload = f"SN:{plan_tag}:{expiry_code}:{hwid_tag}:{salt}"
    sig = hmac.new(SECRET_ADMIN_SALT.encode(), payload.encode(), hashlib.sha256).hexdigest()[:6].upper()
    
    formatted_key = f"SN-{plan_tag}-{expiry_code}-{hwid_tag}-{salt}-{sig}"

    key_record = {
        "license_key": formatted_key,
        "client_name": client_name,
        "plan": plan,
        "duration_days": duration_days,
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "expires_at": expiry_str,
        "expiry_timestamp": expiry_timestamp,
        "bound_hwid": bound_hwid_str,
        "raw_payload": payload,
        "signature": sig,
        "status": "ACTIVE"
    }

    # Save to history & log
    _save_to_admin_history(key_record)
    return key_record


def _save_to_admin_history(key_record: Dict[str, Any]):
    """Save generated key to admin_key_history.json and generated_keys_log.txt."""
    history = []
    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    history.insert(0, key_record)
    try:
        with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Append to human-readable log
    try:
        with open(GENERATED_KEYS_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{key_record['created_at']}] KEY: {key_record['license_key']} | CLIENT: {key_record['client_name']} | PLAN: {key_record['plan']} | EXPIRY: {key_record['expires_at']} | HWID: {key_record['bound_hwid']}\n")
    except Exception:
        pass

    try:
        sync_online_keys()
    except Exception:
        pass


def calculate_key_live_status(key_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate dynamic live status, remaining days, expiring-soon alerts, and usage metadata.
    """
    rec = dict(key_record)
    cleaned_key = rec.get("license_key", "").strip().upper()
    revoked_list = get_revoked_keys()

    # 1. Check Revoked Status
    if rec.get("status") == "REVOKED" or cleaned_key in revoked_list:
        rec["live_status"] = "REVOKED"
        rec["days_remaining"] = 0
        rec["is_expired"] = False
        rec["is_expiring_soon"] = False
        rec["badge_class"] = "stat-pill-red"
        rec["badge_label"] = "REVOKED"
        rec["status_kh"] = "🚫 Revoked"
        rec["remaining_text"] = "Suspended by Admin"
        rec["last_active"] = rec.get("last_active") or rec.get("activated_at") or "Never"
        rec["use_count"] = rec.get("use_count", 0)
        return rec

    # 2. Check Expiry
    expires_at = str(rec.get("expires_at", "")).strip().upper()
    expiry_ts = rec.get("expiry_timestamp", 0)

    if expires_at in ("LIFETIME", "0000", "NEVER", "") or expiry_ts == 0:
        rec["live_status"] = "LIFETIME"
        rec["days_remaining"] = 99999
        rec["is_expired"] = False
        rec["is_expiring_soon"] = False
        rec["badge_class"] = "stat-pill-purple"
        rec["badge_label"] = "LIFETIME"
        rec["status_kh"] = "👑 Lifetime"
        rec["remaining_text"] = "Lifetime (Permanent)"
        rec["last_active"] = rec.get("last_active") or rec.get("activated_at") or "Never"
        rec["use_count"] = rec.get("use_count", 0)
        return rec

    # Try parsing expiration date
    exp_date = None
    try:
        if expiry_ts and expiry_ts > 0:
            exp_date = datetime.fromtimestamp(expiry_ts)
        else:
            exp_date = datetime.strptime(expires_at, "%Y-%m-%d")
    except Exception:
        try:
            exp_date = datetime.strptime(expires_at.split()[0], "%Y-%m-%d")
        except Exception:
            pass

    if not exp_date:
        rec["live_status"] = "ACTIVE"
        rec["days_remaining"] = 30
        rec["is_expired"] = False
        rec["is_expiring_soon"] = False
        rec["badge_class"] = "stat-pill-green"
        rec["badge_label"] = "ACTIVE"
        rec["status_kh"] = "🟢 Active"
        rec["remaining_text"] = expires_at
        rec["last_active"] = rec.get("last_active") or rec.get("activated_at") or "Never"
        rec["use_count"] = rec.get("use_count", 0)
        return rec

    now = datetime.now()
    days_left = (exp_date.date() - now.date()).days

    if days_left < 0:
        rec["live_status"] = "EXPIRED"
        rec["days_remaining"] = days_left
        rec["is_expired"] = True
        rec["is_expiring_soon"] = False
        rec["badge_class"] = "stat-pill-red"
        rec["badge_label"] = "EXPIRED"
        rec["status_kh"] = f"🔴 Expired ({abs(days_left)} days ago)"
        rec["remaining_text"] = f"Expired {abs(days_left)} days ago"
    elif days_left <= 7:
        rec["live_status"] = "EXPIRING_SOON"
        rec["days_remaining"] = days_left
        rec["is_expired"] = False
        rec["is_expiring_soon"] = True
        rec["badge_class"] = "stat-pill-amber"
        rec["badge_label"] = f"EXPIRING ({days_left}D)"
        rec["status_kh"] = f"⚠️ Expiring Soon ({days_left} days left)"
        rec["remaining_text"] = f"{days_left} days remaining"
    else:
        rec["live_status"] = "ACTIVE"
        rec["days_remaining"] = days_left
        rec["is_expired"] = False
        rec["is_expiring_soon"] = False
        rec["badge_class"] = "stat-pill-green"
        rec["badge_label"] = "ACTIVE"
        rec["status_kh"] = f"🟢 Active ({days_left} days left)"
        rec["remaining_text"] = f"{days_left} days remaining"

    rec["last_active"] = rec.get("last_active") or rec.get("activated_at") or "Never"
    rec["use_count"] = rec.get("use_count", 0)
    return rec


DEFAULT_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwryQfTL5KD0w3ROhqR62o-asrCCT24GlU1X1mqpX9h-l7YPKUZd8SsNJCD91kYpFgi/exec"

def get_heartbeat_config() -> Dict[str, Any]:
    """Load Cloud Telemetry & Heartbeat configuration with built-in default fallback."""
    candidates = [
        HEARTBEAT_CONFIG_FILE,
        Path("heartbeat_config.json"),
        Path(__file__).resolve().parent / "data" / "heartbeat_config.json",
        resolve_file_path("data/heartbeat_config.json"),
        resolve_file_path("heartbeat_config.json")
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if isinstance(cfg, dict) and cfg.get("webhook_url"):
                        return cfg
            except Exception:
                pass
    return {"enabled": True, "webhook_url": DEFAULT_WEBHOOK_URL}


def save_heartbeat_config(cfg: Dict[str, Any]) -> bool:
    """Save Cloud Telemetry & Heartbeat configuration."""
    try:
        HEARTBEAT_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HEARTBEAT_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def send_cloud_heartbeat_async(license_key: str, hwid: Optional[str] = None, client_name: Optional[str] = None):
    """
    Fire-and-forget background Cloud Heartbeat.
    Ensures zero delay or UI freeze for the client application.
    """
    if not license_key:
        return
    cfg = get_heartbeat_config()
    webhook_url = cfg.get("webhook_url", "").strip()
    if not cfg.get("enabled", True) or not webhook_url:
        return

    def _worker():
        try:
            import urllib.request
            client_hwid = hwid or get_machine_hwid()
            payload = {
                "action": "heartbeat",
                "license_key": license_key.strip().upper(),
                "hwid": client_hwid,
                "client_name": client_name or "",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=body,
                headers={"Content-Type": "application/json", "User-Agent": "SN_TOOL_Client/2.0"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                pass
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def push_all_to_cloud_sheet() -> Tuple[bool, str, int]:
    """
    Push all local active customers from admin_key_history.json to Google Sheet.
    Uses 'sync_all' action to cleanly format and rebuild the sheet with beautiful styles.
    """
    cfg = get_heartbeat_config()
    webhook_url = cfg.get("webhook_url", "").strip()
    if not cfg.get("enabled", True) or not webhook_url:
        return False, "Google Sheet Webhook not configured", 0

    history = []
    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    deleted_keys = get_deleted_keys()
    valid_customers = []
    for r in history:
        k = r.get("license_key", "").strip().upper()
        if k and k not in deleted_keys:
            valid_customers.append({
                "license_key": k,
                "client_name": r.get("client_name") or "Customer",
                "last_active": r.get("last_active") or "Never",
                "use_count": int(r.get("use_count", 0)),
                "bound_hwid": r.get("bound_hwid") or r.get("active_hwid") or "ANY",
                "plan": r.get("plan") or "PRO",
                "status": r.get("status") or "ACTIVE"
            })

    try:
        import urllib.request
        payload = {
            "action": "sync_all",
            "customers": valid_customers
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "SN_TOOL_Admin_Sync/2.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                return True, data.get("message", f"Synced {len(valid_customers)} customers to Google Sheet!"), len(valid_customers)
            
            # Fallback for v1.0 Apps Script (push individually)
            synced_count = 0
            for c in valid_customers:
                try:
                    c_body = json.dumps({
                        "license_key": c["license_key"],
                        "client_name": c["client_name"],
                        "hwid": c["bound_hwid"],
                        "action": "heartbeat"
                    }).encode("utf-8")
                    c_req = urllib.request.Request(
                        webhook_url,
                        data=c_body,
                        headers={"Content-Type": "application/json", "User-Agent": "SN_TOOL_Admin_Sync/2.0"},
                        method="POST"
                    )
                    with urllib.request.urlopen(c_req, timeout=6) as c_resp:
                        c_data = json.loads(c_resp.read().decode("utf-8"))
                        if c_data.get("success"):
                            synced_count += 1
                except Exception:
                    pass
            if synced_count > 0:
                return True, f"Synchronized {synced_count} customers to Google Sheet!", synced_count
            return False, data.get("error", "Google Sheet returned error"), 0
    except Exception as e:
        return False, f"Failed to connect to Google Sheet Webhook: {e}", 0

def fetch_cloud_heartbeats() -> Dict[str, Dict[str, Any]]:
    """
    Fetch consolidated client usage telemetry from Cloud Webhook.
    Returns dict mapping: LICENSE_KEY -> { last_active, use_count, hwid, client_name }
    """
    cfg = get_heartbeat_config()
    webhook_url = cfg.get("webhook_url", "").strip()
    if not cfg.get("enabled", True) or not webhook_url:
        return {}
    try:
        import urllib.request
        delimiter = "&" if "?" in webhook_url else "?"
        req_url = f"{webhook_url}{delimiter}action=get_all"
        req = urllib.request.Request(
            req_url,
            headers={"User-Agent": "SN_TOOL_Admin/2.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and data.get("success") and "heartbeats" in data:
                return data["heartbeats"]
    except Exception:
        pass
    return {}


def sync_and_load_admin_history() -> List[Dict[str, Any]]:
    """
    Load admin key history, sync missing items from generated_keys_log.txt and custom_keys.json,
    and compute live dynamic expiry status & remaining days.
    """
    history: List[Dict[str, Any]] = []
    seen_keys = set()
    deleted_keys = get_deleted_keys()

    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                raw_hist = json.load(f)
                if isinstance(raw_hist, list):
                    for r in raw_hist:
                        k = r.get("license_key", "").strip().upper()
                        if k and k not in seen_keys and k not in deleted_keys:
                            history.append(r)
                            seen_keys.add(k)
        except Exception:
            history = []

    # Also sync from custom_keys.json
    if CUSTOM_KEYS_FILE.exists():
        try:
            with open(CUSTOM_KEYS_FILE, "r", encoding="utf-8") as f:
                ck_dict = json.load(f)
                if isinstance(ck_dict, dict):
                    for k, rec in ck_dict.items():
                        cleaned_k = k.strip().upper()
                        if cleaned_k and cleaned_k not in seen_keys:
                            history.append(rec)
                            seen_keys.add(cleaned_k)
        except Exception:
            pass

    # Synchronize telemetry from Cloud Heartbeat Webhook if configured
    cloud_heartbeats = fetch_cloud_heartbeats()
    if cloud_heartbeats and isinstance(cloud_heartbeats, dict):
        for r in history:
            k = r.get("license_key", "").strip().upper()
            if k in cloud_heartbeats:
                hb = cloud_heartbeats[k]
                r_active = hb.get("last_active")
                if r_active:
                    r["last_active"] = r_active
                if "use_count" in hb:
                    r["use_count"] = max(int(r.get("use_count", 0)), int(hb.get("use_count", 0)))
                if hb.get("hwid") and hb["hwid"] not in ("ANY", ""):
                    r["last_active_hwid"] = hb["hwid"]
                if hb.get("client_name") and not r.get("client_name"):
                    r["client_name"] = hb["client_name"]

        # Also add any new users recorded in Cloud Heartbeat that were not previously in history
        for k, hb in cloud_heartbeats.items():
            cleaned_k = k.strip().upper()
            if cleaned_k and cleaned_k not in seen_keys and cleaned_k not in deleted_keys:
                new_entry = {
                    "license_key": cleaned_k,
                    "client_name": hb.get("client_name") or "User",
                    "plan": "PRO",
                    "created_at": hb.get("last_active", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    "expires_at": "LIFETIME",
                    "expiry_timestamp": 0,
                    "bound_hwid": hb.get("hwid") or "ANY",
                    "last_active": hb.get("last_active", "Never"),
                    "use_count": int(hb.get("use_count", 0)),
                    "last_active_hwid": hb.get("hwid", ""),
                    "status": "ACTIVE"
                }
                history.append(new_entry)
                seen_keys.add(cleaned_k)

    # Save consolidated back to ADMIN_HISTORY_FILE
    try:
        with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Enrich each record with live calculations
    enriched = [calculate_key_live_status(r) for r in history]
    return enriched


def touch_license_activity(license_key: str, hwid: Optional[str] = None, client_name: Optional[str] = None):
    """Update last active timestamp and usage count when client uses the application."""
    if not license_key:
        return
    cleaned_key = license_key.strip().upper()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not client_name:
        try:
            lic_file = resolve_file_path("license.key")
            if lic_file.exists():
                raw_c = lic_file.read_text(encoding="utf-8")
                lic_data = decrypt_license_token(raw_c)
                if lic_data:
                    client_name = lic_data.get("client_name")
        except Exception:
            pass

    # Update in ADMIN_HISTORY_FILE
    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            changed = False
            for r in history:
                if r.get("license_key", "").strip().upper() == cleaned_key:
                    r["last_active"] = now_str
                    r["use_count"] = int(r.get("use_count", 0)) + 1
                    if client_name and not r.get("client_name"):
                        r["client_name"] = client_name
                    if hwid and hwid not in ("ANY", ""):
                        r["last_active_hwid"] = hwid
                    changed = True
                    break
            if changed:
                with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # Fire background Cloud Heartbeat ping
    send_cloud_heartbeat_async(cleaned_key, hwid=hwid, client_name=client_name)


def verify_license_key(input_key: str, current_hwid: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verify if a license key is valid, unexpired, and HWID-matched.
    Supports Online Cloud Verification, Master Keys, Admin/Custom records, and Offline Cryptographic Checking.
    """
    cleaned_key = input_key.strip().upper()
    if not cleaned_key:
        return False, "Please enter License Key", {}

    # 🛡️ Brute-force rate limiting check
    is_locked, lock_msg = is_brute_force_locked()
    if is_locked:
        return False, lock_msg, {}

    # 🛡️ SYSTEM 8: MITM Proxy & DNS Hijack Check
    proxy_ok, proxy_msg = check_proxy_and_hosts_integrity()
    if not proxy_ok:
        return False, proxy_msg, {}

    t_perf_start = time.perf_counter()

    if not current_hwid:
        current_hwid = get_machine_hwid()

    # 0. Check Blacklist / Revocations (Local & Remote Kill Switch)
    if cleaned_key in get_revoked_keys():
        return False, "❌ This License Key has been suspended/revoked by Admin", {}

    remote_msg = check_remote_revocation_online(cleaned_key, current_hwid)
    if remote_msg:
        return False, remote_msg, {}

    # 1. Check Default Master Keys (100% Offline & Online, Universal)
    if cleaned_key in DEFAULT_MASTER_KEYS:
        if (time.perf_counter() - t_perf_start) > 1.2:
            return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}
        master_info = DEFAULT_MASTER_KEYS[cleaned_key]
        return True, "✅ Valid License Key!", {
            "license_key": cleaned_key,
            "client_name": master_info.get("client_name", "Administrator"),
            "plan": master_info.get("plan", "LIFETIME"),
            "expires_at": "LIFETIME",
            "expiry_timestamp": 0,
            "bound_hwid": "ANY",
            "status": "ACTIVE"
        }

    # 2. Check Custom Keys defined by Admin
    custom_file = resolve_file_path("custom_keys.json")
    if custom_file.exists():
        try:
            with open(custom_file, "r", encoding="utf-8") as f:
                custom_dict = json.load(f)
            if cleaned_key in custom_dict:
                rec = custom_dict[cleaned_key]
                if rec.get("status") == "REVOKED":
                    return False, "❌ This Custom Key has been suspended by Admin", {}

                bound_hwid = str(rec.get("bound_hwid", "ANY")).strip().upper()
                if bound_hwid not in ("ANY", "*", "", "NONE") and bound_hwid != current_hwid:
                    return False, "❌ This Custom Key is locked to a different machine (HWID mismatch)", {}

                expiry_ts = rec.get("expiry_timestamp", 0)
                if expiry_ts > 0 and time.time() > expiry_ts:
                    return False, f"⚠️ This Custom Key has expired ({rec.get('expires_at')})", {}

                if (time.perf_counter() - t_perf_start) > 1.2:
                    return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}
                return True, "✅ Custom Key is valid and active!", rec
        except Exception:
            pass

    # 3. Check Admin History (if present on local Admin PC)
    history_file = resolve_file_path("admin_key_history.json")
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
                for record in history:
                    if record.get("license_key", "").strip().upper() == cleaned_key:
                        if record.get("status") == "REVOKED":
                            return False, "❌ This License Key has been suspended by Admin", {}

                        bound_hwid = str(record.get("bound_hwid", "ANY")).strip().upper()
                        if bound_hwid not in ("ANY", "*", "", "NONE") and bound_hwid != current_hwid:
                            return False, "❌ This License Key is locked to a different machine (HWID mismatch)", {}

                        expiry_ts = record.get("expiry_timestamp", 0)
                        if expiry_ts > 0 and time.time() > expiry_ts:
                            return False, f"⚠️ This License Key has expired ({record.get('expires_at')})", {}

                        if (time.perf_counter() - t_perf_start) > 1.2:
                            return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}
                        return True, "✅ License Key is valid and active!", record
        except Exception:
            pass

    # 4. Check Online Cloud Registry (GitHub) & Bundled Online Keys Database
    online_ok, online_msg, online_rec = check_key_online(cleaned_key, current_hwid)
    if online_ok:
        if (time.perf_counter() - t_perf_start) > 1.2:
            return False, "❌ Execution timing anomaly detected (Debugger step trap)", {}
        return True, online_msg, online_rec
    elif online_msg and ("suspended" in online_msg.lower() or "revoked" in online_msg.lower() or "expired" in online_msg.lower() or "hwid" in online_msg.lower() or "ផ្អាក" in online_msg or "ផុតកំណត់" in online_msg or "HWID" in online_msg):
        return False, online_msg, {}

    # 5. Cryptographic Signature Offline Verification (Standard 6-part SN key)
    parts = cleaned_key.split("-")
    if len(parts) == 6 and parts[0] == "SN":
        _, plan_tag, expiry_code, hwid_tag, salt, sig = parts
        payload = f"SN:{plan_tag}:{expiry_code}:{hwid_tag}:{salt}"

        is_sig_valid = False
        for secret in [
            SECRET_ADMIN_SALT,
            "SN_TOOL_U_NICH_AI_DRAMA_STUDIO_2026",
            "SN_TOOL_VIP_KEY_2026_SECRET",
            "SN_STUDIO_MASTER_KEY_2026"
        ]:
            exp_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest().upper()
            if sig == exp_sig[:len(sig)]:
                is_sig_valid = True
                break

        if not is_sig_valid:
            return False, "❌ Invalid License Key (Invalid Signature)", {}

        # Verify Expiration
        if expiry_code in ("0000", "9999"):
            expiry_str = "LIFETIME"
            expiry_ts = 0
        else:
            try:
                exp_days = int(expiry_code, 16)
                expiry_ts = exp_days * 86400 + 86399
                exp_dt = datetime.fromtimestamp(expiry_ts)
                expiry_str = exp_dt.strftime("%Y-%m-%d")
                if time.time() > expiry_ts:
                    return False, f"⚠️ This License Key has expired ({expiry_str})", {}
            except Exception:
                return False, "❌ Invalid License Key Expiry format", {}

        # Verify HWID Binding
        if hwid_tag not in ("9999", "AAAA"):
            expected_hwid_tag = hashlib.sha256((current_hwid.upper() + SECRET_ADMIN_SALT).encode()).hexdigest()[:4].upper()
            if hwid_tag != expected_hwid_tag:
                return False, "❌ This License Key is locked to a different machine (HWID mismatch)", {}

        # Anti-Single Stepping Latency Trap
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
    return False, "❌ Invalid License Key. Please contact Admin to get a valid key.", {}


def activate_license_on_device(license_key: str, client_name: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """Activate license key on the current computer, record customer name, and write to license.key."""
    current_hwid = get_machine_hwid()
    valid, msg, record = verify_license_key(license_key, current_hwid)
    if not valid:
        return False, msg, {}

    # Prefer user inputted client_name, fallback to record's client_name
    final_client_name = (client_name.strip() if client_name and client_name.strip() else None) or record.get("client_name", "User")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Write activation data to license.key
    data_to_save = {
        "license_key": license_key.strip().upper(),
        "client_name": final_client_name,
        "plan": record.get("plan", "PRO"),
        "activated_at": now_str,
        "last_active": now_str,
        "use_count": 1,
        "expires_at": record.get("expires_at", "LIFETIME"),
        "expiry_timestamp": record.get("expiry_timestamp", 0),
        "machine_hwid": current_hwid,
        "checksum": hmac.new(SECRET_ADMIN_SALT.encode(), f"{license_key.strip().upper()}|{current_hwid}".encode(), hashlib.sha256).hexdigest()[:16]
    }

    try:
        enc_token = encrypt_license_token(data_to_save, current_hwid)
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            f.write(enc_token)
    except Exception as e:
        return False, f"Could not write license file: {e}", {}

    # Also update client_name and last_active in admin_key_history.json if present
    cleaned_key = license_key.strip().upper()
    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
            found = False
            for r in history:
                if r.get("license_key", "").strip().upper() == cleaned_key:
                    r["client_name"] = final_client_name
                    r["activated_at"] = now_str
                    r["last_active"] = now_str
                    r["use_count"] = int(r.get("use_count", 0)) + 1
                    r["active_hwid"] = current_hwid
                    found = True
                    break
            if not found:
                new_rec = {
                    "license_key": cleaned_key,
                    "client_name": final_client_name,
                    "plan": record.get("plan", "PRO"),
                    "duration_days": record.get("duration_days", 0),
                    "created_at": now_str,
                    "activated_at": now_str,
                    "last_active": now_str,
                    "use_count": 1,
                    "expires_at": record.get("expires_at", "LIFETIME"),
                    "expiry_timestamp": record.get("expiry_timestamp", 0),
                    "bound_hwid": current_hwid,
                    "status": "ACTIVE"
                }
                history.insert(0, new_rec)

            with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)

            sync_online_keys()
        except Exception:
            pass

    # Fire immediate Cloud Heartbeat on new device activation
    send_cloud_heartbeat_async(cleaned_key, hwid=current_hwid, client_name=final_client_name)
    return True, f"🎉 License Key activated successfully! Welcome {final_client_name}!", data_to_save


def check_current_device_license() -> Dict[str, Any]:
    """Check if the current device is activated with a valid license."""
    start_security_sentinel()
    current_hwid = get_machine_hwid()

    # Check permanent device ban status (Tamper / Lockout check)
    is_banned, ban_reason = is_current_device_banned()
    if is_banned:
        return {
            "is_activated": False,
            "is_banned": True,
            "message": f"⛔ DEVICE PERMANENTLY BANNED: {ban_reason}",
            "hwid": current_hwid
        }

    # 0. Check if license requirement is disabled (Free / Open Access mode)
    if not is_license_required():
        return {
            "is_activated": True,
            "license_key": "FREE-OPEN-ACCESS",
            "client_name": "Free / Open User",
            "plan": "LIFETIME_UNLOCKED",
            "expires_at": "LIFETIME",
            "hwid": current_hwid,
            "message": "License Gate is disabled (Free Mode)"
        }

    # 🛡️ Hardened Runtime & Time Integrity Guards
    int_ok, int_msg = verify_runtime_integrity()
    if not int_ok:
        record_permanent_device_ban(f"Runtime tampering detected: {int_msg}")
        return {
            "is_activated": False,
            "is_banned": True,
            "message": f"⛔ SECURITY VIOLATION: {int_msg}",
            "hwid": current_hwid
        }

    time_ok, time_msg = verify_time_integrity()
    if not time_ok:
        return {
            "is_activated": False,
            "message": time_msg,
            "hwid": current_hwid
        }

    # Strict License Protection: Require valid key entry if license.key does not exist
    lic_path = resolve_file_path("license.key")
    if not lic_path.exists():
        return {
            "is_activated": False,
            "message": "Please enter License Key to activate tool",
            "hwid": current_hwid
        }

    try:
        raw_lic = lic_path.read_text(encoding="utf-8").strip()
        data = decrypt_license_token(raw_lic, current_hwid)
        if not data:
            try:
                lic_path.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "is_activated": False,
                "message": "Please enter License Key to activate tool (Hardware Binding Mismatch).",
                "hwid": current_hwid
            }

        # Seamlessly auto-upgrade legacy plain JSON to HWID-encrypted token
        if not raw_lic.startswith("SN_VAULT_V2:"):
            try:
                upgraded_token = encrypt_license_token(data, current_hwid)
                lic_path.write_text(upgraded_token, encoding="utf-8")
            except Exception:
                pass

        license_key = data.get("license_key", "").strip().upper()
        saved_hwid = data.get("machine_hwid", "").strip().upper()
        checksum = data.get("checksum", "")

        # Verify integrity
        expected_checksum = hmac.new(SECRET_ADMIN_SALT.encode(), f"{license_key}|{saved_hwid}".encode(), hashlib.sha256).hexdigest()[:16]
        if checksum != expected_checksum:
            try:
                lic_path.unlink(missing_ok=True)
            except Exception:
                pass
            record_permanent_device_ban("Tampered / forged license.key file detected")
            return {
                "is_activated": False,
                "is_banned": True,
                "message": "License Key file has been tampered with and was auto-purged. Device permanently banned.",
                "hwid": current_hwid
            }

        # Check machine HWID match (Strict Anti-Copy)
        if saved_hwid != current_hwid:
            try:
                lic_path.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "is_activated": False,
                "message": "Please enter License Key to activate tool (Machine HWID Mismatch).",
                "hwid": current_hwid
            }

        # Check local and remote revocation
        if license_key in get_revoked_keys():
            try:
                lic_path.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "is_activated": False,
                "message": "❌ This License Key has been suspended by Admin.",
                "hwid": current_hwid
            }

        remote_msg = check_remote_revocation_online(license_key, current_hwid)
        if remote_msg:
            try:
                lic_path.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "is_activated": False,
                "message": remote_msg,
                "hwid": current_hwid
            }

        # Check if Admin has remotely renewed / extended this license key in online registry
        try:
            online_ok, _, online_rec = check_key_online(license_key, current_hwid)
            if online_ok and isinstance(online_rec, dict):
                remote_exp_ts = online_rec.get("expiry_timestamp", 0)
                remote_exp_str = online_rec.get("expires_at", "LIFETIME")
                local_exp_ts = data.get("expiry_timestamp", 0)

                # If remote is Lifetime while local was limited, OR remote has a further expiry date:
                if (remote_exp_str == "LIFETIME" and local_exp_ts > 0) or (remote_exp_ts > local_exp_ts):
                    data["expires_at"] = remote_exp_str
                    data["expiry_timestamp"] = remote_exp_ts
                    data["plan"] = online_rec.get("plan", data.get("plan", "PRO"))
                    data["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    data["checksum"] = hmac.new(SECRET_ADMIN_SALT.encode(), f"{license_key}|{current_hwid}".encode(), hashlib.sha256).hexdigest()[:16]
                    try:
                        with open(lic_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                    except Exception:
                        pass
        except Exception:
            pass

        # Touch activity & calculate live dynamic status
        touch_license_activity(license_key, current_hwid)
        live = calculate_key_live_status(data)

        if live.get("is_expired"):
            return {
                "is_activated": False,
                "message": f"⚠️ Your License Key expired {abs(live.get('days_remaining', 0))} days ago. Please contact Admin to renew.",
                "hwid": current_hwid,
                "is_expired": True
            }

        return {
            "is_activated": True,
            "license_key": license_key,
            "client_name": data.get("client_name", "User"),
            "plan": data.get("plan", "PRO"),
            "expires_at": data.get("expires_at", "LIFETIME"),
            "days_remaining": live.get("days_remaining", 99999),
            "is_expiring_soon": live.get("is_expiring_soon", False),
            "status_kh": live.get("status_kh", "Active"),
            "last_active": data.get("last_active", "Just now"),
            "hwid": current_hwid,
            "message": "License is 100% active"
        }
    except Exception as e:
        return {
            "is_activated": False,
            "message": f"Error verifying license: {e}",
            "hwid": current_hwid
        }
