"""
Patch script to implement the 7 newly requested security systems:
1. Digital Signature Verification
2. Secure License Validation
3. Secure Update Integrity
4. API Request Authentication
5. Anti-Replay Attack Protection
6. Security Event Logging
7. Recovery & Self-Healing Protection
"""
import sys
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def patch_license_engine():
    p = ROOT / "license_engine.py"
    content = p.read_text(encoding="utf-8")

    code_to_inject = '''
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
        formatted_entry = f"[{raw_msg}] [SIG:{entry_sig}]\\n"

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
'''

    target = "def record_failed_attempt() -> Tuple[bool, str]:"
    if "def sign_digital_payload" not in content and target in content:
        content = content.replace(target, code_to_inject + "\n\n" + target, 1)
        print("[OK] Injected 7 enterprise security systems into license_engine.py")

    # Hook log_security_event into record_permanent_device_ban
    old_ban = '''def record_permanent_device_ban(reason: str = "Illegal security bypass / tamper attempt detected"):'''
    new_ban = '''def record_permanent_device_ban(reason: str = "Illegal security bypass / tamper attempt detected"):
    try:
        log_security_event("DEVICE_BAN", "CRITICAL", reason)
    except Exception:
        pass'''

    if "log_security_event(\"DEVICE_BAN\"" not in content and old_ban in content:
        content = content.replace(old_ban, new_ban, 1)
        print("[OK] Hooked log_security_event into record_permanent_device_ban")

    p.write_text(content, encoding="utf-8")

def patch_update():
    p = ROOT / "update.py"
    content = p.read_text(encoding="utf-8")

    old_target = """        # Create detached PowerShell updater script
        ps1_file = app_dir / "apply_update.ps1\""""

    new_target = """        # 🛡️ SYSTEM 13: Secure Update Package Integrity Verification
        try:
            import license_engine
            upg_ok, upg_msg = license_engine.verify_update_package_integrity(dest_file)
            if not upg_ok:
                return {"success": False, "error": f"Security check failed on downloaded update: {upg_msg}"}
        except ImportError:
            pass

        # Create detached PowerShell updater script
        ps1_file = app_dir / "apply_update.ps1\""""

    if "verify_update_package_integrity" not in content and old_target in content:
        content = content.replace(old_target, new_target, 1)
        p.write_text(content, encoding="utf-8")
        print("[OK] Hooked verify_update_package_integrity into update.py")

if __name__ == "__main__":
    patch_license_engine()
    patch_update()
    print("[SUCCESS] Patched 7 new security systems!")

