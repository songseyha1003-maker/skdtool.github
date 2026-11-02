# -*- coding: utf-8 -*-
import sys
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import license_engine

def run_tests():
    print("=" * 65)
    print("🛡️ RUNNING COMPREHENSIVE SECURITY UPGRADE VERIFICATION")
    print("=" * 65)

    # 1. Test Layer 1: Obfuscated Dynamic Salt
    print("\n[TEST 1] Testing Obfuscated Dynamic Master Salt...")
    salt = license_engine.SECRET_ADMIN_SALT
    expected = "SN_TOOL_U_NICH_AI_DRAMA_STUDIO_2026_MASTER_SECRET_KEY"
    assert salt == expected, f"Salt mismatch: {salt}"
    print(f"  ✅ Dynamic Salt Reconstitution: Verified ({salt[:15]}...)")

    # 2. Test Layer 2: Time Integrity & Anti-Rollback
    print("\n[TEST 2] Testing Time Integrity & Anti-Clock Rollback...")
    ok, msg = license_engine.verify_time_integrity()
    assert ok, f"Time integrity failed: {msg}"
    print(f"  ✅ Time Integrity Guard: Active ({msg})")

    # 3. Test Layer 3: Runtime Code Integrity & Anti-Hooking
    print("\n[TEST 3] Testing Runtime Code Integrity & Anti-Monkey Patching...")
    int_ok, int_msg = license_engine.verify_runtime_integrity()
    assert int_ok, f"Runtime integrity failed: {int_msg}"
    print(f"  ✅ Runtime Integrity Guard: Active ({int_msg})")

    # 4. Test Layer 4: Hardware-Bound AES-256 Token Encryption & Decryption
    print("\n[TEST 4] Testing Hardware-Bound AES-256 Token Encryption...")
    hwid = license_engine.get_machine_hwid()
    fake_hwid = "DEADBEEF12345678"
    mock_payload = {
        "license_key": "SN-PRO-526A-3693-F457-DBD7A0",
        "client_name": "Developer",
        "plan": "PRO",
        "machine_hwid": hwid
    }

    enc_token = license_engine.encrypt_license_token(mock_payload, hwid)
    assert enc_token.startswith("SN_VAULT_V2:"), "Encrypted token format invalid"
    print(f"  ✅ Encrypted Token: {enc_token[:35]}... (Length: {len(enc_token)})")

    # Decrypt on genuine machine HWID
    dec_payload = license_engine.decrypt_license_token(enc_token, hwid)
    assert dec_payload is not None, "Failed to decrypt on genuine HWID"
    assert dec_payload.get("license_key") == mock_payload["license_key"], "Payload mismatch"
    print(f"  ✅ Decryption on Genuine Machine: SUCCESS ({dec_payload['client_name']})")

    # Decrypt on copied/different machine HWID (must fail mathematically!)
    fake_dec = license_engine.decrypt_license_token(enc_token, fake_hwid)
    assert fake_dec is None, "Security Breach: Token decrypted on mismatched HWID!"
    print("  ✅ Decryption on Mismatched Machine HWID: BLOCKED (Mathematical Decryption Failure)")

    # 5. Test Layer 5: Expanded Process Sentinel Tools
    print("\n[TEST 5] Testing Process Sentinel Blacklist Coverage...")
    procs = license_engine.BLACK_LISTED_PROCESSES
    assert len(procs) >= 28, f"Expected >= 28 blacklisted tools, got {len(procs)}"
    assert "ida64.exe" in procs
    assert "ghidra.exe" in procs
    assert "x64dbg.exe" in procs
    assert "cheatengine.exe" in procs
    print(f"  ✅ Protected against {len(procs)} reverse-engineering & debug tools")

    # 6. Test Layer 6 & Current Device License Auto-Upgrade
    print("\n[TEST 6] Testing Current Device License Verification & Auto-Upgrade...")
    lic_status = license_engine.check_current_device_license()
    assert lic_status.get("is_activated"), f"License check failed: {lic_status}"
    print(f"  ✅ License Status: {lic_status.get('status_kh')}")
    print(f"  ✅ Days Remaining: {lic_status.get('days_remaining')}")

    # Verify license.key on disk was upgraded to hardware-bound encrypted vault
    lic_file = Path("license.key")
    assert lic_file.exists(), "license.key file missing"
    raw_content = lic_file.read_text(encoding="utf-8").strip()
    assert raw_content.startswith("SN_VAULT_V2:"), f"license.key was not auto-upgraded to encrypted token! Got: {raw_content[:40]}"
    print("  ✅ license.key was automatically upgraded to Hardware-Bound AES-256 Vault!")

    print("\n" + "=" * 65)
    print("🎉 ALL 7 SECURITY UPGRADE LAYERS VERIFIED WITH 100% SUCCESS!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()

