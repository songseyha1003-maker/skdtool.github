"""
👑 SN TOOL - LICENSE ADMIN CONTROL CENTER (PORT 8888)
Dedicated, standalone, isolated Admin Control Center.
Completely separated from the customer-facing Studio Tool (Port 8000).
"""
import sys
import os
import json
import time
import threading
import urllib.request
import webbrowser
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory

# Base directory
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
os.chdir(str(BASE_DIR))

# Safe stdout / stderr encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from license_engine import (
    generate_license_key,
    verify_license_key,
    register_custom_key,
    revoke_license_key,
    unrevoke_license_key,
    delete_license_key_record,
    clear_all_admin_keys,
    get_revoked_keys,
    is_license_required,
    set_license_required,
    get_machine_hwid,
    calculate_key_live_status,
    sync_and_load_admin_history,
    sync_online_keys,
    extend_license_key,
    push_online_registry_async,
    ADMIN_HISTORY_FILE,
    GENERATED_KEYS_LOG,
    CUSTOM_KEYS_FILE,
    REVOKED_KEYS_FILE,
    get_heartbeat_config,
    save_heartbeat_config
)

admin_app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
admin_app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@admin_app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@admin_app.route("/")
@admin_app.route("/admin")
def serve_admin_page():
    return send_from_directory(str(STATIC_DIR), "admin.html")

@admin_app.route("/api/license/status")
def admin_license_status():
    return jsonify({
        "success": True,
        "hwid": get_machine_hwid(),
        "require_license": is_license_required()
    })

@admin_app.route("/api/admin/keys", methods=["GET"])
def admin_keys_list():
    try:
        keys = sync_and_load_admin_history()
        return jsonify({"success": True, "keys": keys})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_app.route("/api/admin/export-txt", methods=["GET"])
def admin_export_txt():
    if not GENERATED_KEYS_LOG.exists():
        GENERATED_KEYS_LOG.write_text("# SN STUDIO - Generated Keys Log\n", encoding="utf-8")
    return send_file(str(GENERATED_KEYS_LOG.resolve()), as_attachment=True, download_name="SN_STUDIO_Generated_Keys.txt")

@admin_app.route("/api/admin/generate-key", methods=["POST"])
def admin_generate_key():
    data = request.get_json(force=True) or {}
    client_name = data.get("client_name", "").strip() or "Customer"
    duration_days = int(data.get("duration_days", 0))
    hwid = data.get("hwid") or None
    plan = data.get("plan", "PRO")
    custom_key = data.get("custom_key", "").strip()

    if custom_key:
        record = register_custom_key(custom_key, client_name=client_name, duration_days=duration_days, hwid=hwid, plan=plan)
    else:
        record = generate_license_key(client_name=client_name, duration_days=duration_days, hwid=hwid, plan=plan)

    # Immediately push to GitHub registry so remote users can verify instantly
    try:
        push_online_registry_async()
    except Exception:
        pass

    enriched = calculate_key_live_status(record)
    return jsonify({"success": True, "key_record": enriched})

@admin_app.route("/api/admin/custom-key", methods=["POST"])
def admin_custom_key():
    data = request.get_json(force=True) or {}
    custom_key = data.get("custom_key", "").strip()
    if not custom_key:
        return jsonify({"success": False, "error": "Please enter Custom Key"}), 400
    client_name = data.get("client_name", "").strip() or "Customer"
    duration_days = int(data.get("duration_days", 0))
    hwid = data.get("hwid") or None
    plan = data.get("plan", "CUSTOM")
    rec = register_custom_key(custom_key, client_name, duration_days, hwid, plan)
    try:
        push_online_registry_async()
    except Exception:
        pass
    enriched = calculate_key_live_status(rec)
    return jsonify({"success": True, "key_record": enriched})

@admin_app.route("/api/admin/license-config", methods=["GET", "POST"])
def admin_license_config():
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        req = bool(data.get("require_license", True))
        set_license_required(req)
        return jsonify({"success": True, "require_license": req})
    return jsonify({"success": True, "require_license": is_license_required()})

@admin_app.route("/api/admin/revoke-key", methods=["POST"])
def admin_revoke_key():
    data = request.get_json(force=True) or {}
    key = data.get("license_key", "").strip()
    reason = data.get("reason", "Admin manual revoke")
    if not key:
        return jsonify({"success": False, "error": "Please enter Key"}), 400
    ok, msg = revoke_license_key(key, reason)
    return jsonify({"success": ok, "message": msg})

@admin_app.route("/api/admin/unrevoke-key", methods=["POST"])
def admin_unrevoke_key():
    data = request.get_json(force=True) or {}
    key = data.get("license_key", "").strip()
    if not key:
        return jsonify({"success": False, "error": "Please enter Key"}), 400
    ok, msg = unrevoke_license_key(key)
    return jsonify({"success": ok, "message": msg})

@admin_app.route("/api/admin/delete-key", methods=["POST"])
def admin_delete_key():
    data = request.get_json(force=True) or {}
    key = data.get("license_key", "").strip()
    if not key:
        return jsonify({"success": False, "error": "Please enter Key"}), 400
    ok, msg = delete_license_key_record(key)
    return jsonify({"success": ok, "message": msg})

@admin_app.route("/api/admin/clear-all-keys", methods=["POST"])
def admin_clear_all_keys():
    try:
        ok, msg = clear_all_admin_keys()
        return jsonify({"success": ok, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@admin_app.route("/api/admin/extend-key", methods=["POST"])
def admin_extend_key():
    data = request.get_json(force=True) or {}
    key = data.get("license_key", "").strip()
    additional_days = int(data.get("additional_days", 30))
    plan = data.get("plan")
    auto_push = bool(data.get("auto_push", True))

    if not key:
        return jsonify({"success": False, "error": "Please enter License Key"}), 400

    ok, msg, enriched = extend_license_key(key, additional_days=additional_days, plan=plan)
    if ok and auto_push:
        push_online_registry_async()

    return jsonify({"success": ok, "message": msg, "key_record": enriched})

@admin_app.route("/api/admin/sync-online", methods=["POST", "GET"])
def admin_sync_online():
    try:
        keys = sync_online_keys()
        return jsonify({
            "success": True,
            "message": f"Successfully synced {len(keys)} keys to Online Registry!",
            "count": len(keys)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@admin_app.route("/api/admin/heartbeat-config", methods=["GET", "POST"])
def admin_heartbeat_config():
    if request.method == "POST":
        data = request.get_json(force=True) or {}
        cfg = {
            "enabled": bool(data.get("enabled", True)),
            "webhook_url": str(data.get("webhook_url", "")).strip()
        }
        ok = save_heartbeat_config(cfg)
        return jsonify({"success": ok, "config": cfg})
    return jsonify({"success": True, "config": get_heartbeat_config()})


@admin_app.route("/api/admin/test-heartbeat", methods=["POST"])
def admin_test_heartbeat():
    data = request.get_json(force=True) or {}
    url = str(data.get("webhook_url", "")).strip()
    if not url:
        cfg = get_heartbeat_config()
        url = cfg.get("webhook_url", "").strip()
    if not url:
        return jsonify({"success": False, "error": "No Webhook URL configured"}), 400

    try:
        import urllib.request
        delimiter = "&" if "?" in url else "?"
        req_url = f"{url}{delimiter}action=ping"
        req = urllib.request.Request(req_url, headers={"User-Agent": "SN_TOOL_Admin_Test/2.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            raw = resp.read().decode("utf-8")
            return jsonify({
                "success": True,
                "message": "Successfully reached Cloud Webhook endpoint!",
                "raw_response": raw[:200]
            })
    except Exception as e:
        return jsonify({"success": False, "error": f"Connection test failed: {e}"}), 500

ADMIN_PORT = 8888
ADMIN_URL = f"http://127.0.0.1:{ADMIN_PORT}/admin"

def is_admin_server_running() -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{ADMIN_PORT}/api/license/status", timeout=1) as r:
            return r.status == 200
    except Exception:
        return False

def open_browser_when_ready():
    for _ in range(30):
        if is_admin_server_running():
            print(f"\n[OK] Admin Dashboard is ready! Opening browser: {ADMIN_URL}")
            try:
                webbrowser.open(ADMIN_URL)
            except Exception:
                pass
            return
        time.sleep(0.2)
    try:
        webbrowser.open(ADMIN_URL)
    except Exception:
        pass

def main():
    print("=" * 68)
    print(" 👑 SN TOOL - LICENSE ADMIN CONTROL CENTER (ISOLATED)")
    print(f" 🌐 Dedicated Admin Address: {ADMIN_URL}")
    print(" 🛡️  Port: 8888 (Dedicated Admin Control Center - Isolated from Port 8000)")
    print("=" * 68)

    if is_admin_server_running():
        print(f"[OK] Admin Server is already running on Port {ADMIN_PORT}.")
        print(f"[OK] Opening browser: {ADMIN_URL}")
        webbrowser.open(ADMIN_URL)
        return

    threading.Thread(target=open_browser_when_ready, daemon=True).start()

    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    print(f"[OK] Admin Server started on http://127.0.0.1:{ADMIN_PORT}")
    print("👉 Admin Dashboard is ready for key management! (Press Ctrl+C to stop)")
    try:
        admin_app.run(host="127.0.0.1", port=ADMIN_PORT, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        print("\nAdmin Server stopped.")

if __name__ == "__main__":
    main()
