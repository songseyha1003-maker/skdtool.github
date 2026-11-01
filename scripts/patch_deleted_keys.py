from pathlib import Path

def patch_deleted_keys_support():
    engine_path = Path("license_engine.py")
    content = engine_path.read_text(encoding="utf-8")

    # 1. Add deleted keys helpers
    helper_code = '''DELETED_KEYS_FILE = Path("data/deleted_keys.json")

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

'''

    old_del = '''def delete_license_key_record(target_key: str) -> Tuple[bool, str]:
    """Delete a key record completely from history, custom keys, and revocations."""
    cleaned = target_key.strip().upper()
    if not cleaned:
        return False, "Please select Key to delete"'''

    new_del = helper_code + '''def delete_license_key_record(target_key: str) -> Tuple[bool, str]:
    """Delete a key record completely from history, custom keys, and revocations."""
    cleaned = target_key.strip().upper()
    if not cleaned:
        return False, "Please select Key to delete"
    record_deleted_key(cleaned)'''

    assert old_del in content, "old_del not found in license_engine.py"
    content = content.replace(old_del, new_del)

    # 2. Update sync_and_load_admin_history to use deleted_keys
    old_sync_start = '''def sync_and_load_admin_history() -> List[Dict[str, Any]]:
    """
    Load admin key history, sync missing items from generated_keys_log.txt and custom_keys.json,
    and compute live dynamic expiry status & remaining days.
    """
    history: List[Dict[str, Any]] = []
    seen_keys = set()'''

    new_sync_start = '''def sync_and_load_admin_history() -> List[Dict[str, Any]]:
    """
    Load admin key history, sync missing items from generated_keys_log.txt and custom_keys.json,
    and compute live dynamic expiry status & remaining days.
    """
    history: List[Dict[str, Any]] = []
    seen_keys = set()
    deleted_keys = get_deleted_keys()'''

    assert old_sync_start in content, "old_sync_start not found"
    content = content.replace(old_sync_start, new_sync_start)

    old_hist_filter = '''                        if k and k not in seen_keys:
                            history.append(r)
                            seen_keys.add(k)'''

    new_hist_filter = '''                        if k and k not in seen_keys and k not in deleted_keys:
                            history.append(r)
                            seen_keys.add(k)'''

    assert old_hist_filter in content, "old_hist_filter not found"
    content = content.replace(old_hist_filter, new_hist_filter)

    old_cloud_loop = '''        # Also add any new users recorded in Cloud Heartbeat that were not previously in history
        for k, hb in cloud_heartbeats.items():
            if k not in seen_keys and k.strip().upper():
                cleaned_k = k.strip().upper()'''

    new_cloud_loop = '''        # Also add any new users recorded in Cloud Heartbeat that were not previously in history
        for k, hb in cloud_heartbeats.items():
            cleaned_k = k.strip().upper()
            if cleaned_k and cleaned_k not in seen_keys and cleaned_k not in deleted_keys:'''

    assert old_cloud_loop in content, "old_cloud_loop not found"
    content = content.replace(old_cloud_loop, new_cloud_loop)

    engine_path.write_text(content, encoding="utf-8")
    print("Successfully patched license_engine.py with deleted_keys support!")

if __name__ == "__main__":
    patch_deleted_keys_support()
