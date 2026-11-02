"""
Implementation patch for:
1. Asymmetric Ed25519 Key Separation (Public Key in Client, Private Key strictly in Server)
2. Authoritative Server-Side Enforcement (Device Limit, Rate Limit, Signed Leases)
3. Honest & Realistic Security Posture Architecture
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def patch_license_engine():
    p = ROOT / "license_engine.py"
    content = p.read_text(encoding="utf-8")

    asymmetric_code = '''
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
'''

    target = "def record_failed_attempt() -> Tuple[bool, str]:"
    if "def verify_asymmetric_signature" not in content and target in content:
        content = content.replace(target, asymmetric_code + "\n\n" + target, 1)
        print("[OK] Injected Asymmetric Ed25519 Key Infrastructure & Server Lease Enforcement into license_engine.py")

    p.write_text(content, encoding="utf-8")

def patch_admin_dashboard():
    p = ROOT / "admin_dashboard.py"
    content = p.read_text(encoding="utf-8")

    server_route = '''
@admin_app.route("/api/server/authorize-lease", methods=["POST"])
def server_authorize_lease():
    data = request.get_json(force=True) or {}
    key = data.get("license_key", "").strip()
    hwid = data.get("hwid", "").strip()
    plan = data.get("plan", "PRO")

    if not key or not hwid:
        return jsonify({"success": False, "error": "Missing license_key or hwid"}), 400

    if key in get_revoked_keys():
        return jsonify({"success": False, "error": "License key revoked by administrator"}), 403

    is_valid, msg, rec = verify_license_key(key, hwid)
    if not is_valid:
        return jsonify({"success": False, "error": msg}), 403

    res = generate_server_lease_token(key, hwid, plan=rec.get("plan", plan))
    return jsonify(res)
'''

    if "/api/server/authorize-lease" not in content:
        content = content.rstrip() + "\n" + server_route + "\n"
        p.write_text(content, encoding="utf-8")
        print("[OK] Injected /api/server/authorize-lease endpoint into admin_dashboard.py")

if __name__ == "__main__":
    patch_license_engine()
    patch_admin_dashboard()
    print("[SUCCESS] Asymmetric and Server Enforcement architecture applied!")

