import json
from pathlib import Path

def update_files():
    # --- 1. license_engine.py ---
    p_engine = Path("license_engine.py")
    content = p_engine.read_text(encoding="utf-8")

    old_cfg = '''def get_heartbeat_config() -> Dict[str, Any]:
    """Load Cloud Telemetry & Heartbeat configuration."""
    candidates = [
        HEARTBEAT_CONFIG_FILE,
        Path("heartbeat_config.json"),
        Path(__file__).resolve().parent / "data" / "heartbeat_config.json"
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {"enabled": True, "webhook_url": ""}'''

    new_cfg = '''DEFAULT_WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbwryQfTL5KD0w3ROhqR62o-asrCCT24GlU1X1mqpX9h-l7YPKUZd8SsNJCD91kYpFgi/exec"

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
    return {"enabled": True, "webhook_url": DEFAULT_WEBHOOK_URL}'''

    assert old_cfg in content, "old_cfg not found in license_engine.py"
    content = content.replace(old_cfg, new_cfg)

    old_touch = '''def touch_license_activity(license_key: str, hwid: Optional[str] = None):
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

    # Fire background Cloud Heartbeat ping
    send_cloud_heartbeat_async(cleaned_key, hwid=hwid)'''

    new_touch = '''def touch_license_activity(license_key: str, hwid: Optional[str] = None, client_name: Optional[str] = None):
    """Update last active timestamp and usage count when client uses the application."""
    if not license_key:
        return
    cleaned_key = license_key.strip().upper()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not client_name:
        try:
            lic_file = resolve_file_path("license.key")
            if lic_file.exists():
                with open(lic_file, "r", encoding="utf-8") as f:
                    lic_data = json.load(f)
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
    send_cloud_heartbeat_async(cleaned_key, hwid=hwid, client_name=client_name)'''

    assert old_touch in content, "old_touch not found in license_engine.py"
    content = content.replace(old_touch, new_touch)

    old_sync = '''    # Synchronize telemetry from Cloud Heartbeat Webhook if configured
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
                    r["last_active_hwid"] = hb["hwid"]'''

    new_sync = '''    # Synchronize telemetry from Cloud Heartbeat Webhook if configured
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
            if k not in seen_keys and k.strip().upper():
                cleaned_k = k.strip().upper()
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
                seen_keys.add(cleaned_k)'''

    assert old_sync in content, "old_sync not found in license_engine.py"
    content = content.replace(old_sync, new_sync)

    old_act = '''    return True, f"\U0001f389 License Key activated successfully! Welcome {final_client_name}!", data_to_save'''
    new_act = '''    # Fire immediate Cloud Heartbeat on new device activation
    send_cloud_heartbeat_async(cleaned_key, hwid=current_hwid, client_name=final_client_name)
    return True, f"\U0001f389 License Key activated successfully! Welcome {final_client_name}!", data_to_save'''

    assert old_act in content, "old_act not found in license_engine.py"
    content = content.replace(old_act, new_act)

    p_engine.write_text(content, encoding="utf-8")
    print("Updated license_engine.py successfully!")

    # --- 2. admin_dashboard.py ---
    p_dash = Path("admin_dashboard.py")
    dash_content = p_dash.read_text(encoding="utf-8")

    old_dash_gen = '''    if custom_key:
        record = register_custom_key(custom_key, client_name=client_name, duration_days=duration_days, hwid=hwid, plan=plan)
    else:
        record = generate_license_key(client_name=client_name, duration_days=duration_days, hwid=hwid, plan=plan)

    enriched = calculate_key_live_status(record)
    return jsonify({"success": True, "key_record": enriched})'''

    new_dash_gen = '''    if custom_key:
        record = register_custom_key(custom_key, client_name=client_name, duration_days=duration_days, hwid=hwid, plan=plan)
    else:
        record = generate_license_key(client_name=client_name, duration_days=duration_days, hwid=hwid, plan=plan)

    # Immediately push to GitHub registry so remote users can verify instantly
    try:
        push_online_registry_async()
    except Exception:
        pass

    enriched = calculate_key_live_status(record)
    return jsonify({"success": True, "key_record": enriched})'''

    assert old_dash_gen in dash_content, "old_dash_gen not found in admin_dashboard.py"
    dash_content = dash_content.replace(old_dash_gen, new_dash_gen)

    old_dash_cust = '''    rec = register_custom_key(custom_key, client_name, duration_days, hwid, plan)
    enriched = calculate_key_live_status(rec)
    return jsonify({"success": True, "key_record": enriched})'''

    new_dash_cust = '''    rec = register_custom_key(custom_key, client_name, duration_days, hwid, plan)
    try:
        push_online_registry_async()
    except Exception:
        pass
    enriched = calculate_key_live_status(rec)
    return jsonify({"success": True, "key_record": enriched})'''

    assert old_dash_cust in dash_content, "old_dash_cust not found in admin_dashboard.py"
    dash_content = dash_content.replace(old_dash_cust, new_dash_cust)

    p_dash.write_text(dash_content, encoding="utf-8")
    print("Updated admin_dashboard.py successfully!")

if __name__ == "__main__":
    update_files()

