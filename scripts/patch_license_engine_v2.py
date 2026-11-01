from pathlib import Path

def patch_license_engine():
    p = Path("license_engine.py")
    content = p.read_text(encoding="utf-8")

    # 1. Add push_all_to_cloud_sheet function
    push_func = '''def push_all_to_cloud_sheet() -> Tuple[bool, str, int]:
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
            return False, data.get("error", "Google Sheet returned error"), 0
    except Exception as e:
        return False, f"Failed to connect to Google Sheet Webhook: {e}", 0

'''

    old_fetch = 'def fetch_cloud_heartbeats() -> Dict[str, Dict[str, Any]]:'
    assert old_fetch in content, "old_fetch not found"
    content = content.replace(old_fetch, push_func + old_fetch)

    # 2. Update delete_license_key_record to trigger cloud delete
    old_del_end = '''    try:
        sync_online_keys()
        push_online_registry_async()
    except Exception:
        pass

    return True, f"'''

    new_del_end = '''    try:
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

    return True, f"'''

    assert old_del_end in content, "old_del_end not found"
    content = content.replace(old_del_end, new_del_end)

    p.write_text(content, encoding="utf-8")
    print("Successfully patched license_engine.py with push_all_to_cloud_sheet and cloud delete!")

if __name__ == "__main__":
    patch_license_engine()

