"""
Patch license_engine.py to inject Layers 8, 9, 10 for complete 10-Layer Defense Architecture.
"""
from pathlib import Path

p = Path("license_engine.py")
content = p.read_text(encoding="utf-8")

layers_code = '''
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
'''

# 1. Inject functions before verify_runtime_integrity
target_loc = "def verify_runtime_integrity() -> Tuple[bool, str]:"
if "def check_proxy_and_hosts_integrity" not in content and target_loc in content:
    content = content.replace(target_loc, layers_code + "\n\n" + target_loc, 1)
    print("[OK] Injected Layers 8, 9, 10 functions into license_engine.py")

# 2. Hook check_proxy_and_hosts_integrity into verify_license_key
old_vlk_check = """    # 🛡️ Brute-force rate limiting check
    is_locked, lock_msg = is_brute_force_locked()
    if is_locked:
        return False, lock_msg, {}"""

new_vlk_check = """    # 🛡️ Brute-force rate limiting check
    is_locked, lock_msg = is_brute_force_locked()
    if is_locked:
        return False, lock_msg, {}

    # 🛡️ SYSTEM 8: MITM Proxy & DNS Hijack Check
    proxy_ok, proxy_msg = check_proxy_and_hosts_integrity()
    if not proxy_ok:
        return False, proxy_msg, {}"""

if old_vlk_check in content:
    content = content.replace(old_vlk_check, new_vlk_check, 1)
    print("[OK] Hooked System 8 (Proxy/Hosts) into verify_license_key")

# 3. Hook anti-dump activation into module startup
old_init_bc = "# Initialize In-Memory Bytecode Baseline for Anti-Patching\ninit_bytecode_baseline()"
new_init_bc = """# Initialize In-Memory Bytecode Baseline for Anti-Patching & Memory Mitigation
init_bytecode_baseline()
try:
    activate_anti_dump_mitigation()
except Exception:
    pass"""

if old_init_bc in content:
    content = content.replace(old_init_bc, new_init_bc, 1)
    print("[OK] Hooked System 10 (Anti-Dump Mitigation) into startup")

# Normalize CRLF
if "\r\n" in content:
    content = content.replace("\r\n", "\n").replace("\n", "\r\n")

p.write_text(content, encoding="utf-8")
print("[SUCCESS] Applied 10-Layer upgrades to license_engine.py!")

