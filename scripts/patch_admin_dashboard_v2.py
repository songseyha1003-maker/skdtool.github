from pathlib import Path

def patch_admin_dashboard():
    p = Path("admin_dashboard.py")
    content = p.read_text(encoding="utf-8")

    # 1. Update import
    old_imp = "save_heartbeat_config\n)"
    new_imp = "save_heartbeat_config,\n    push_all_to_cloud_sheet\n)"
    assert old_imp in content, "old_imp not found"
    content = content.replace(old_imp, new_imp)

    # 2. Add routes
    routes_code = '''

@admin_app.route("/api/admin/cloud-sync-push", methods=["POST"])
def admin_cloud_sync_push():
    ok, msg, count = push_all_to_cloud_sheet()
    return jsonify({"success": ok, "message": msg, "count": count})


@admin_app.route("/api/admin/cloud-sync-pull", methods=["POST"])
def admin_cloud_sync_pull():
    records = sync_and_load_admin_history()
    return jsonify({
        "success": True,
        "message": f"Successfully synchronized {len(records)} records from Cloud Sheet!",
        "count": len(records),
        "records": records
    })

'''

    old_marker = 'ADMIN_PORT = 8888'
    assert old_marker in content, "old_marker not found"
    content = content.replace(old_marker, routes_code + old_marker)

    p.write_text(content, encoding="utf-8")
    print("Successfully patched admin_dashboard.py with cloud sync routes!")

if __name__ == "__main__":
    patch_admin_dashboard()

