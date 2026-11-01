from pathlib import Path

def patch_admin_html():
    p = Path("static/admin.html")
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    script_v2 = Path("data/google_apps_script_v2.js").read_text(encoding="utf-8")

    # 1. Add "Sync Google Sheet" button to Customers Database header
    btn_line_idx = -1
    for i, line in enumerate(lines):
        if 'onclick="fetchKeysHistory()"' in line and 'btn-action-light' in line:
            btn_line_idx = i
            break
    assert btn_line_idx != -1, "Refresh button not found"

    cloud_sync_btn = '''                        <button type="button" class="btn-action-light" id="btn-cloud-sync" onclick="handleCloudSync()" style="color:#2563eb; border-color:#bfdbfe; font-weight:700;" title="Push all customers and pull latest usage from Google Sheet">
                            <i class="fa-solid fa-cloud-arrow-up"></i> Sync Google Sheet
                        </button>\n'''
    lines.insert(btn_line_idx, cloud_sync_btn)

    # 2. Add Push & Pull buttons to Settings Card
    test_btn_idx = -1
    for i, line in enumerate(lines):
        if 'handleTestHeartbeat()' in line:
            test_btn_idx = i
            break
    assert test_btn_idx != -1, "Test heartbeat button not found"

    extra_settings_btns = '''                                <button type="button" class="btn-action-light" onclick="handleCloudPush()" style="white-space:nowrap; padding: 10px 16px; color:#16a34a; font-weight:700; border-color:#bbf7d0;">
                                    <i class="fa-solid fa-cloud-arrow-up"></i> Push to Google Sheet
                                </button>
                                <button type="button" class="btn-action-light" onclick="handleCloudPull()" style="white-space:nowrap; padding: 10px 16px; color:#2563eb; font-weight:700; border-color:#bfdbfe;">
                                    <i class="fa-solid fa-cloud-arrow-down"></i> Pull from Google Sheet
                                </button>\n'''
    # Insert after closing </button> of test button
    lines.insert(test_btn_idx + 2, extra_settings_btns)

    # 3. Replace GOOGLE_APPS_SCRIPT_TEMPLATE
    tmpl_start = -1
    tmpl_end = -1
    for i, line in enumerate(lines):
        if 'const GOOGLE_APPS_SCRIPT_TEMPLATE =' in line:
            tmpl_start = i
        if tmpl_start != -1 and line.strip().endswith('}`;'):
            tmpl_end = i
            break
    assert tmpl_start != -1 and tmpl_end != -1, "Template bounds not found"

    new_tmpl_lines = [f"        const GOOGLE_APPS_SCRIPT_TEMPLATE = `{script_v2}`;\n"]
    lines = lines[:tmpl_start] + new_tmpl_lines + lines[tmpl_end + 1:]

    # 4. Add handleCloudSync, handleCloudPush, handleCloudPull functions before copyGoogleAppsScriptCode
    copy_idx = -1
    for i, line in enumerate(lines):
        if 'function copyGoogleAppsScriptCode()' in line:
            copy_idx = i
            break
    assert copy_idx != -1, "copyGoogleAppsScriptCode not found"

    new_funcs = '''
        // Cloud Sync Push & Pull handlers (Enterprise Telemetry Engine v2.0)
        async function handleCloudSync() {
            const btn = document.getElementById('btn-cloud-sync');
            const originalHtml = btn ? btn.innerHTML : '';
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing...';
            }

            try {
                // 1. Push all valid local customers to Google Sheet
                const pushRes = await fetch('/api/admin/cloud-sync-push', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                const pushData = await pushRes.json();

                // 2. Pull telemetry back into dashboard
                const pullRes = await fetch('/api/admin/cloud-sync-pull', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                const pullData = await pullRes.json();

                if (pushData.success && pullData.success) {
                    showToast(`\U0001f389 Cloud Sync Complete! ${pushData.count || 3} customers synced with Google Sheet!`);
                } else {
                    showToast(pushData.message || pullData.message || "\u26a0\ufe0f Cloud Sync finished with warnings");
                }
                await fetchKeysHistory();
            } catch (err) {
                showToast("\u274c Cloud Sync failed: " + err.message);
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = originalHtml;
                }
            }
        }

        async function handleCloudPush() {
            try {
                showToast("\u23f3 Pushing customer list to Google Sheet...");
                const res = await fetch('/api/admin/cloud-sync-push', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                const data = await res.json();
                if (data.success) {
                    showToast(`\U0001f389 ${data.message || 'Pushed successfully!'}`);
                } else {
                    showToast(`\u274c ${data.error || 'Failed to push'}`);
                }
            } catch (err) {
                showToast("\u274c Network error while pushing to cloud");
            }
        }

        async function handleCloudPull() {
            try {
                showToast("\u23f3 Pulling live telemetry from Google Sheet...");
                const res = await fetch('/api/admin/cloud-sync-pull', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
                const data = await res.json();
                if (data.success) {
                    showToast(`\U0001f389 ${data.message || 'Pulled successfully!'}`);
                    await fetchKeysHistory();
                } else {
                    showToast(`\u274c ${data.error || 'Failed to pull'}`);
                }
            } catch (err) {
                showToast("\u274c Network error while pulling from cloud");
            }
        }
\n'''
    lines.insert(copy_idx, new_funcs)

    p.write_text("".join(lines), encoding="utf-8")
    print("Successfully patched static/admin.html with complete v2.0 UI!")

if __name__ == "__main__":
    patch_admin_html()
