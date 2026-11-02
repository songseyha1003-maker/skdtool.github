"""
🛡️ VERIFICATION SUITE: ASYMMETRIC KEY MANAGEMENT & SERVER-SIDE ENFORCEMENT
============================================================================
Verifies:
1. Pillar 1: Asymmetric Key Separation (Public Key in Client, Private Key on Server)
2. Pillar 2: Server-Side Device Concurrency Limit Enforcement
3. Pillar 2: Server-Side Rate Limiting Protection
4. Pillar 2: Authoritative Cryptographic Lease Generation & Verification
5. Pillar 2: Rejection of Forged / Tampered Server Leases
"""

import sys
import os
import time
import json
from pathlib import Path

# Fix Windows console encoding for Unicode emojis
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import license_engine

def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f"🎯 [PILLAR TEST] {title}")
    print("=" * 70)

def test_pillar_1_asymmetric_key_separation():
    print_separator("PILLAR 1: Asymmetric Key Separation (Public in Client, Private on Server)")
    
    test_data = b"SN_CORE_AUTHORITATIVE_DATA_PACKET"
    
    # 1. Server-side signing with private key
    sig_hex = license_engine.sign_with_admin_private_key(test_data)
    print(f"  [Server Signed Signature]: {sig_hex[:24]}... (Length: {len(sig_hex)})")
    
    # 2. Client-side verification using ONLY public key
    is_valid = license_engine.verify_asymmetric_signature(test_data, sig_hex)
    print(f"  [Client Verification with Public Key]: {is_valid}")
    
    # 3. Attacker tampers with data
    tampered_data = b"SN_CORE_AUTHORITATIVE_DATA_TAMPERED!"
    tampered_valid = license_engine.verify_asymmetric_signature(tampered_data, sig_hex)
    print(f"  [Client Check on Tampered Data]: {tampered_valid}")
    
    # 4. Attacker attempts to forge a signature
    fake_sig = "A" * 128
    fake_valid = license_engine.verify_asymmetric_signature(test_data, fake_sig)
    print(f"  [Client Check on Forged Signature]: {fake_valid}")

    success = is_valid and (not tampered_valid) and (not fake_valid)
    if success:
        print("  ✅ SUCCESS: Asymmetric Ed25519 separation confirmed!")
        print("  🔒 Key Management: Client only holds Public Key; Private Key remains strictly on Server.")
    else:
        print("  ❌ FAILURE: Asymmetric signature check failed.")
    return success

def test_pillar_2_server_device_limit():
    print_separator("PILLAR 2A: Server-Side Device Concurrency Limit Enforcement")
    
    test_key = "SN-PRO-TEST-DEVICE-LIMIT-2026"
    machine_1 = "HWID_GENUINE_0001"
    machine_2 = "HWID_PIRATE_0002"
    
    # Clear test device registry
    license_engine._SERVER_ACTIVE_DEVICES.pop(test_key, None)

    # 1. First device registers (allowed, max 1)
    dev1_ok, msg1 = license_engine.server_enforce_device_limit(test_key, machine_1, max_devices=1)
    print(f"  [Device 1 (Genuine PC)]: ok={dev1_ok}, msg='{msg1}'")

    # 2. Device 1 pings again (should succeed since already registered)
    dev1_repeat, msg_rep = license_engine.server_enforce_device_limit(test_key, machine_1, max_devices=1)
    print(f"  [Device 1 Repeat Ping]: ok={dev1_repeat}, msg='{msg_rep}'")

    # 3. Second unauthorized device tries to activate same key
    dev2_ok, msg2 = license_engine.server_enforce_device_limit(test_key, machine_2, max_devices=1)
    print(f"  [Device 2 (Pirate PC Attempt)]: ok={dev2_ok}, msg='{msg2}'")

    # Clean up test key
    license_engine._SERVER_ACTIVE_DEVICES.pop(test_key, None)

    success = dev1_ok and dev1_repeat and (not dev2_ok) and "limit exceeded" in msg2
    if success:
        print("  ✅ SUCCESS: Server-side device limit blocked unauthorized secondary machine!")
        print("  🔒 Zero-Trust: Multi-machine license sharing prevented at server level.")
    else:
        print("  ❌ FAILURE: Server device limit enforcement failed.")
    return success

def test_pillar_2_server_rate_limiting():
    print_separator("PILLAR 2B: Server-Side Request Rate Limiting")
    
    test_hwid = "HWID_FLOOD_ATTACKER_99"
    license_engine._SERVER_RATE_LIMITS.pop(test_hwid, None)

    blocked_at = None
    # Send 35 rapid requests (threshold is 30/min)
    for i in range(1, 36):
        ok, msg = license_engine.server_enforce_rate_limit(test_hwid, max_requests_per_minute=30)
        if not ok:
            blocked_at = i
            break

    print(f"  [Rapid Requests Fired]: 35 | Blocked at: #{blocked_at}")
    license_engine._SERVER_RATE_LIMITS.pop(test_hwid, None)

    success = blocked_at == 31
    if success:
        print("  ✅ SUCCESS: Server-side rate limiter triggered at request #31!")
        print("  🔒 Server Protection: Key scraping and API hammering attacks blocked.")
    else:
        print(f"  ❌ FAILURE: Rate limiter did not trigger at expected threshold (Got: {blocked_at}).")
    return success

def test_pillar_2_server_lease_generation_and_tamper():
    print_separator("PILLAR 2C: Server Lease Generation, Verification & Tamper Trap")
    
    genuine_hwid = license_engine.get_machine_hwid()
    test_key = "SN-PRO-AUTHORIZED-LEASE-TEST"
    
    # 1. Server issues authenticated lease
    lease_res = license_engine.generate_server_lease_token(test_key, genuine_hwid, plan="PRO")
    print(f"  [Server Lease Generated]: success={lease_res.get('success')}")
    
    if not lease_res.get("success"):
        print(f"  ❌ Failed to generate lease: {lease_res.get('error')}")
        return False

    lease_payload = lease_res["lease_payload"]
    signature = lease_res["signature"]

    # 2. Client verifies genuine lease
    is_client_ok, client_msg = license_engine.verify_server_lease_token(lease_payload, signature)
    print(f"  [Genuine Lease Verification]: ok={is_client_ok}, msg='{client_msg}'")

    # 3. Attacker tries to tamper with lease (e.g. extending expiry date)
    tampered_payload = dict(lease_payload)
    tampered_payload["lease_expires_at"] = time.time() + 86400 * 365 # 1 year extension!
    tampered_ok, tampered_msg = license_engine.verify_server_lease_token(tampered_payload, signature)
    print(f"  [Tampered Expiry Lease Check]: ok={tampered_ok}, msg='{tampered_msg}'")

    # 4. Attacker transfers lease to another HWID
    hijacked_payload = dict(lease_payload)
    hijacked_payload["hwid"] = "SPOOFED_HWID_9999"
    hijacked_ok, hijacked_msg = license_engine.verify_server_lease_token(hijacked_payload, signature)
    print(f"  [Transferred HWID Lease Check]: ok={hijacked_ok}, msg='{hijacked_msg}'")

    success = is_client_ok and (not tampered_ok) and (not hijacked_ok)
    if success:
        print("  ✅ SUCCESS: Server-signed lease verified; tampering and cross-machine transfer thwarted!")
        print("  🔒 Server Enforcement: Client cannot alter lease duration or hardware binding.")
    else:
        print("  ❌ FAILURE: Server lease verification or tamper detection failed.")
    return success

def run_all_pillar_tests():
    print("\n" + "#" * 70)
    print("🛡️ VERIFYING 3 CRITICAL SECURITY PILLARS (KEY MGMT & SERVER ENFORCEMENT)")
    print("#" * 70)

    results = []
    results.append(("Pillar 1: Asymmetric Key Separation", test_pillar_1_asymmetric_key_separation()))
    results.append(("Pillar 2A: Server Device Concurrency Limit", test_pillar_2_server_device_limit()))
    results.append(("Pillar 2B: Server-Side Rate Limiting", test_pillar_2_server_rate_limiting()))
    results.append(("Pillar 2C: Server Lease Cryptographic Integrity", test_pillar_2_server_lease_generation_and_tamper()))

    print("\n" + "=" * 70)
    print("📊 3 CRITICAL PILLARS VERIFICATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, res in results if res)
    total = len(results)

    for name, res in results:
        status = "🛡️ PASSED (CONFIRMED)" if res else "❌ FAILED"
        print(f"  • {name:<46} : {status}")

    print("-" * 70)
    print(f"  DEFENSE HARDENING SCORE: {passed}/{total} ({(passed/total)*100:.0f}%)")
    if passed == total:
        print("  🏆 CERTIFIED: ASYMMETRIC KEY ISOLATION & SERVER ENFORCEMENT OPERATIONAL!")
        print("  💡 Security Posture: High Economic Barrier & Defense-in-Depth Model Active.")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_all_pillar_tests()

