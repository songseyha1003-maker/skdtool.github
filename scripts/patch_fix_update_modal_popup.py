"""
Fix update check behavior in static/app.js:
When already on latest version (has_update == false), do NOT open modal-update again.
Simply show a reassuring toast: "✅ You're up to date! SN Tool v2.0.2 is the latest version."
"""
from pathlib import Path

p = Path("static/app.js")
content = p.read_text(encoding="utf-8")

old_code = """        } else {
            // Already on latest official build:
            // When checked automatically on boot (manual = false), stay quiet.
            // When user explicitly clicks the update icon (manual = true), open modal to allow updating/syncing the latest patch for v${curVer}!
            if (badgeText) badgeText.textContent = "LATEST OFFICIAL BUILD & PATCH";
            if (subtitle) subtitle.textContent = `Official release v${curVer} is active. Click below to sync and re-apply the latest patch fixes and engine improvements:`;
            if (btnUpdate) btnUpdate.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> <span id="btn-do-update-text">Update / Sync Now (v${curVer})</span>`;
            if (manual) {
                openModal('modal-update');
                showToast(`SN Tool v${curVer} patch ready to sync!`);
            }
        }"""

new_code = """        } else {
            // Already on latest official build:
            if (badgeText) badgeText.textContent = "UP TO DATE";
            if (subtitle) subtitle.textContent = `SN Tool v${curVer} is currently active and fully up to date. All neural engines and features are optimal.`;
            if (btnUpdate) {
                btnUpdate.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span id="btn-do-update-text">Already Up to Date (v${curVer})</span>`;
                btnUpdate.disabled = true;
            }
            if (manual) {
                showToast(`✅ You are up to date! SN Tool v${curVer} is the latest version.`);
            }
        }"""

# Normalize CRLF
has_crlf = "\r\n" in content
if has_crlf:
    content = content.replace("\r\n", "\n")

if old_code in content:
    content = content.replace(old_code, new_code, 1)
    if has_crlf:
        content = content.replace("\n", "\r\n")
    p.write_text(content, encoding="utf-8")
    print("[SUCCESS] Fixed static/app.js update check behavior!")
else:
    print("[ERROR] Target code block not found in static/app.js")

