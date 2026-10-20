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

SECRET_ADMIN_SALT = "SN_TOOL_U_NICH_AI_DRAMA_STUDIO_2026_MASTER_SECRET_KEY"

# ==========================================================================
# 🛡️ SYSTEM 3 & 4: ANTI-DEBUG, ANTI-REVERSE ENGINEERING & PROCESS SENTINEL
# ==========================================================================
BLACK_LISTED_PROCESSES = {
    "x64dbg.exe", "x32dbg.exe", "x96dbg.exe", "ida.exe", "ida64.exe",
    "idag.exe", "idag64.exe", "ollydbg.exe", "cheatengine-x86_64.exe",
    "cheatengine-i386.exe", "cheatengine.exe", "processhacker.exe",
    "fiddler.exe", "httpdebuggerui.exe", "httpdebugger.exe",
    "wireshark.exe", "dnspy.exe", "scylla.exe", "hxd.exe"
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
    """Background security sentinel thread."""
    while True:
        try:
            if is_debugger_active() or check_blacklisted_hack_tools():
                record_permanent_device_ban("Active reverse-engineering / debugger tool detected")
                os._exit(0)
        except Exception:
            pass
        time.sleep(4.0)

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
    except Exception:
        pass

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
    except Exception:
        pass

    return True, f"✅ Successfully unbanned Key {cleaned}!"


def delete_license_key_record(target_key: str) -> Tuple[bool, str]:
    """Delete a key record completely from history, custom keys, and revocations."""
    cleaned = target_key.strip().upper()
    if not cleaned:
        return False, "Please select Key to delete"

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
    except Exception:
        pass

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


def sync_and_load_admin_history() -> List[Dict[str, Any]]:
    """
    Load admin key history, sync missing items from generated_keys_log.txt and custom_keys.json,
    and compute live dynamic expiry status & remaining days.
    """
    history: List[Dict[str, Any]] = []
    seen_keys = set()

    if ADMIN_HISTORY_FILE.exists():
        try:
            with open(ADMIN_HISTORY_FILE, "r", encoding="utf-8") as f:
                raw_hist = json.load(f)
                if isinstance(raw_hist, list):
                    for r in raw_hist:
                        k = r.get("license_key", "").strip().upper()
                        if k and k not in seen_keys:
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

    # Save consolidated back to ADMIN_HISTORY_FILE
    try:
        with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Enrich each record with live calculations
    enriched = [calculate_key_live_status(r) for r in history]
    return enriched


def touch_license_activity(license_key: str, hwid: Optional[str] = None):
    """Update last active timestamp and usage count when client uses the application."""
    if not license_key:
        return
    cleaned_key = license_key.strip().upper()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                    if hwid and hwid not in ("ANY", ""):
                        r["last_active_hwid"] = hwid
                    changed = True
                    break
            if changed:
                with open(ADMIN_HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


def verify_license_key(input_key: str, current_hwid: Optional[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Verify if a license key is valid, unexpired, and HWID-matched.
    Supports Online Cloud Verification, Master Keys, Admin/Custom records, and Offline Cryptographic Checking.
    """
    cleaned_key = input_key.strip().upper()
    if not cleaned_key:
        return False, "Please enter License Key", {}

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

                        return True, "✅ License Key is valid and active!", record
        except Exception:
            pass

    # 4. Check Online Cloud Registry (GitHub) & Bundled Online Keys Database
    online_ok, online_msg, online_rec = check_key_online(cleaned_key, current_hwid)
    if online_ok:
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

        return True, "✅ License Key is valid and active!", {
            "license_key": cleaned_key,
            "client_name": "User",
            "plan": f"PRO_{plan_tag}",
            "expires_at": expiry_str,
            "expiry_timestamp": expiry_ts,
            "bound_hwid": current_hwid if hwid_tag not in ("9999", "AAAA") else "ANY",
            "status": "ACTIVE"
        }

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
        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
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

    # Strict License Protection: Require valid key entry if license.key does not exist
    lic_path = resolve_file_path("license.key")
    if not lic_path.exists():
        return {
            "is_activated": False,
            "message": "Please enter License Key to activate tool",
            "hwid": current_hwid
        }

    try:
        with open(lic_path, "r", encoding="utf-8") as f:
            data = json.load(f)

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
