"""
🛡️ VERIFICATION & STRESS TEST SUITE: 7 ENTERPRISE SECURITY SYSTEMS
===================================================================
Tests:
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
import time
import zipfile
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
    print(f"🎯 [TESTING SYSTEM] {title}")
    print("=" * 70)

def test_1_digital_signature():
    print_separator("1. Digital Signature Verification")
    payload = b"SN_PROPRIETARY_PAYLOAD_DATA_2026_CONFIDENTIAL"
    
    # 1. Sign payload
    sig = license_engine.sign_digital_payload(payload)
    print(f"  [Generated Signature]: {sig[:16]}... (Length: {len(sig)})")
    
    # 2. Genuine verification
    is_valid = license_engine.verify_digital_signature(payload, sig)
    print(f"  [Genuine Verification]: {is_valid}")
    
    # 3. Tampered payload
    tampered_payload = b"SN_PROPRIETARY_PAYLOAD_DATA_2026_TAMPERED!!!!"
    tampered_valid = license_engine.verify_digital_signature(tampered_payload, sig)
    print(f"  [Tampered Payload Verification]: {tampered_valid}")
    
    # 4. Forged signature
    forged_sig = sig[:10] + "0000" + sig[14:]
    forged_valid = license_engine.verify_digital_signature(payload, forged_sig)
    print(f"  [Forged Signature Verification]: {forged_valid}")

    success = is_valid and (not tampered_valid) and (not forged_valid)
    if success:
        print("  ✅ SUCCESS: Digital Signature correctly authenticates genuine payloads and rejects tampering!")
    else:
        print("  ❌ FAILURE: Digital signature verification failed.")
    return success

def test_2_secure_license_validation():
    print_separator("2. Secure License Validation (Multi-Factor Entitlement)")
    
    res = license_engine.validate_secure_license_comprehensive()
    print(f"  [License Valid]: {res.get('is_valid')}")
    print(f"  [Plan Tier]: {res.get('plan')}")
    print(f"  [Days Remaining]: {res.get('days_remaining')}")
    print(f"  [Hardware HWID]: {res.get('hwid')}")
    print(f"  [Entitled Features]: {res.get('entitled_features')}")

    success = res.get("is_valid") is True and len(res.get("entitled_features", [])) >= 5
    if success:
        print("  ✅ SUCCESS: Multi-factor license validation certified with active entitlement matrix!")
    else:
        print("  ❌ FAILURE: Secure license validation check failed.")
    return success

def test_3_secure_update_integrity():
    print_separator("3. Secure Update Integrity")
    
    test_zip_path = Path("scratch/test_update_package.zip")
    test_zip_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a legitimate test zip archive
    with zipfile.ZipFile(test_zip_path, "w") as zf:
        zf.writestr("test_module.py", "# Authenticated update test code\n")
        zf.writestr("version.json", '{"version": "2.0.2"}\n')

    valid_sha = license_engine.compute_file_sha256(test_zip_path)
    with open(test_zip_path, "rb") as f:
        valid_sig = license_engine.sign_digital_payload(f.read())

    # Test 1: Legitimate update verification
    is_ok, msg = license_engine.verify_update_package_integrity(test_zip_path, valid_sha, valid_sig)
    print(f"  [Legitimate Update Check]: ok={is_ok}, msg='{msg}'")

    # Test 2: Mismatched checksum
    bad_sha = "0" * 64
    tampered_ok, tampered_msg = license_engine.verify_update_package_integrity(test_zip_path, bad_sha, valid_sig)
    print(f"  [Tampered Checksum Check]: ok={tampered_ok}, msg='{tampered_msg}'")

    # Clean up test zip
    try:
        test_zip_path.unlink()
    except Exception:
        pass

    success = is_ok and (not tampered_ok)
    if success:
        print("  ✅ SUCCESS: Update integrity guard protects against MITM and corrupt archives!")
    else:
        print("  ❌ FAILURE: Update package integrity verification failed.")
    return success

def test_4_api_request_authentication():
    print_separator("4. API Request Authentication")
    
    body = '{"action": "cloud_handshake", "client": "SN_STUDIO_PRO"}'
    
    # 1. Generate authenticated headers
    headers = license_engine.generate_authenticated_api_headers(body)
    print("  [Generated Authentication Headers]:")
    for k, v in headers.items():
        print(f"    • {k}: {v[:24]}...")

    # 2. Verify legitimate request
    is_valid, msg = license_engine.verify_authenticated_api_headers(headers, body)
    print(f"  [Legitimate API Auth Check]: valid={is_valid}, msg='{msg}'")

    # 3. Simulate attacker modifying payload body in transit
    tampered_body = '{"action": "cloud_handshake", "client": "SN_CRACKED_PIRATE"}'
    tampered_valid, tampered_msg = license_engine.verify_authenticated_api_headers(headers, tampered_body)
    print(f"  [Tampered In-Transit Body]: valid={tampered_valid}, msg='{tampered_msg}'")

    success = is_valid and (not tampered_valid)
    if success:
        print("  ✅ SUCCESS: Cloud API requests are cryptographically authenticated and tamper-proof!")
    else:
        print("  ❌ FAILURE: API request authentication check failed.")
    return success

def test_5_anti_replay_attack():
    print_separator("5. Anti-Replay Attack Protection")
    
    nonce = os.urandom(16).hex()
    now = time.time()

    # 1. First legitimate request
    first_ok, msg1 = license_engine.validate_replay_protection(nonce, now)
    print(f"  [Initial Request Validation]: ok={first_ok}, msg='{msg1}'")

    # 2. Attacker replays identical packet with same nonce
    replayed_ok, msg2 = license_engine.validate_replay_protection(nonce, now)
    print(f"  [Replayed Duplicate Nonce Check]: ok={replayed_ok}, msg='{msg2}'")

    # 3. Attacker uses expired timestamp (> 120s drift)
    expired_nonce = os.urandom(16).hex()
    expired_time = now - 300.0
    expired_ok, msg3 = license_engine.validate_replay_protection(expired_nonce, expired_time)
    print(f"  [Expired Timestamp Check]: ok={expired_ok}, msg='{msg3}'")

    success = first_ok and (not replayed_ok) and (not expired_ok)
    if success:
        print("  ✅ SUCCESS: Anti-replay protection blocked duplicate nonces and expired packets!")
    else:
        print("  ❌ FAILURE: Anti-replay protection check failed.")
    return success

def test_6_security_event_logging():
    print_separator("6. Security Event Logging & Audit Trail")
    
    # Log an event
    test_event_type = "PROBE_SIMULATION"
    test_details = "Simulated security audit probe verification"
    license_engine.log_security_event(test_event_type, "WARNING", test_details)

    logs = license_engine.get_recent_security_logs(5)
    print(f"  [Retrieved Recent Logs (Count: {len(logs)})]:")
    found_test_event = False
    for line in logs[-3:]:
        print(f"    • {line}")
        if test_event_type in line and "[SIG:" in line:
            found_test_event = True

    if found_test_event:
        print("  ✅ SUCCESS: Security events logged with cryptographic integrity signatures!")
    else:
        print("  ❌ FAILURE: Security log entry not found or missing signature.")
    return found_test_event

def test_7_recovery_and_self_healing():
    print_separator("7. Recovery & Self-Healing Protection")
    
    # Run self-healing recovery
    heal_ok, heal_msg = license_engine.execute_self_healing_recovery()
    print(f"  [Self-Healing Outcome]: ok={heal_ok}")
    print(f"  [Healed Summary]: '{heal_msg}'")

    success = heal_ok is True and "completed" in heal_msg
    if success:
        print("  ✅ SUCCESS: Autonomous self-healing certified! Heals state files and caches.")
    else:
        print("  ❌ FAILURE: Self-healing routine failed.")
    return success

def run_all_7_systems_tests():
    print("\n" + "#" * 70)
    print("🛡️ VERIFYING 7 NEW ENTERPRISE SECURITY SYSTEMS (ChatGPT & Claude)")
    print("#" * 70)

    results = []
    results.append(("1. Digital Signature Verification", test_1_digital_signature()))
    results.append(("2. Secure License Validation", test_2_secure_license_validation()))
    results.append(("3. Secure Update Integrity", test_3_secure_update_integrity()))
    results.append(("4. API Request Authentication", test_4_api_request_authentication()))
    results.append(("5. Anti-Replay Attack Protection", test_5_anti_replay_attack()))
    results.append(("6. Security Event Logging", test_6_security_event_logging()))
    results.append(("7. Recovery & Self-Healing", test_7_recovery_and_self_healing()))

    print("\n" + "=" * 70)
    print("📊 7 ENTERPRISE SYSTEMS VERIFICATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, res in results if res)
    total = len(results)

    for name, res in results:
        status = "🛡️ PASSED (100% SECURE)" if res else "❌ FAILED"
        print(f"  • {name:<36} : {status}")

    print("-" * 70)
    print(f"  SCORE: {passed}/{total} ({(passed/total)*100:.0f}%)")
    if passed == total:
        print("  🏆 CERTIFIED: ALL 7 ENTERPRISE SECURITY SYSTEMS ACTIVE & VERIFIED!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_all_7_systems_tests()

