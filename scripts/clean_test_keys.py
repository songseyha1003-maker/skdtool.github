import json
from pathlib import Path

def clean_test_users():
    history_file = Path("admin_key_history.json")
    deleted_file = Path("data/deleted_keys.json")
    deleted_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Add test keys to deleted_keys.json
    deleted_keys = ["SN-TEST-KEY-001", "SN-BRAND-NEW-KEY-999"]
    deleted_file.write_text(json.dumps(deleted_keys, indent=2), encoding="utf-8")
    print("Created data/deleted_keys.json with test keys.")

    # 2. Clean admin_key_history.json
    if history_file.exists():
        history = json.loads(history_file.read_text(encoding="utf-8"))
        cleaned_history = []
        for r in history:
            k = r.get("license_key", "").strip().upper()
            if k in deleted_keys:
                continue
            # Reset test count on Bong Nak back to pristine state
            if k == "SN-30D-5129-5580-C9CC-704A7D":
                r["use_count"] = 0
                r["last_active"] = "Never"
            cleaned_history.append(r)

        history_file.write_text(json.dumps(cleaned_history, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Cleaned admin_key_history.json: {len(cleaned_history)} real records remaining.")

    # 3. Clean data/license_keys_online.json
    online_file = Path("data/license_keys_online.json")
    if online_file.exists():
        online_data = json.loads(online_file.read_text(encoding="utf-8"))
        for k in deleted_keys:
            if k in online_data:
                del online_data[k]
        online_file.write_text(json.dumps(online_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print("Cleaned data/license_keys_online.json.")

if __name__ == "__main__":
    clean_test_users()
