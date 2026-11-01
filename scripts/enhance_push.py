from pathlib import Path

def enhance_push():
    p = Path("license_engine.py")
    content = p.read_text(encoding="utf-8")

    old_func = '''    try:
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
        return False, f"Failed to connect to Google Sheet Webhook: {e}", 0'''

    new_func = '''    try:
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
            
            # Fallback for v1.0 Apps Script (push individually)
            synced_count = 0
            for c in valid_customers:
                try:
                    c_body = json.dumps({
                        "license_key": c["license_key"],
                        "client_name": c["client_name"],
                        "hwid": c["bound_hwid"],
                        "action": "heartbeat"
                    }).encode("utf-8")
                    c_req = urllib.request.Request(
                        webhook_url,
                        data=c_body,
                        headers={"Content-Type": "application/json", "User-Agent": "SN_TOOL_Admin_Sync/2.0"},
                        method="POST"
                    )
                    with urllib.request.urlopen(c_req, timeout=6) as c_resp:
                        c_data = json.loads(c_resp.read().decode("utf-8"))
                        if c_data.get("success"):
                            synced_count += 1
                except Exception:
                    pass
            if synced_count > 0:
                return True, f"Synchronized {synced_count} customers to Google Sheet!", synced_count
            return False, data.get("error", "Google Sheet returned error"), 0
    except Exception as e:
        return False, f"Failed to connect to Google Sheet Webhook: {e}", 0'''

    assert old_func in content, "old_func not found"
    content = content.replace(old_func, new_func)
    p.write_text(content, encoding="utf-8")
    print("Enhanced push_all_to_cloud_sheet with universal fallback!")

if __name__ == "__main__":
    enhance_push()

