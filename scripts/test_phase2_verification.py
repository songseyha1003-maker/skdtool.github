# -*- coding: utf-8 -*-
import sys
import os
import json
import shutil
from pathlib import Path

# Ensure root directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import downloader
from downloader import DramaDownloadManager

def run_phase2_tests():
    print("=" * 60)
    print("🧪 RUNNING PHASE 2 VERIFICATION TESTS (DOWNLOADER ENGINE)")
    print("=" * 60)

    mgr = DramaDownloadManager()

    # 1. Test clean download directory (no extra metadata/txt clutter)
    print("\n[TEST 1] Verifying Clean Download Directory (No extra .json/.txt files)...")
    test_dir = Path("scratch/test_drama_dir")
    test_dir.mkdir(parents=True, exist_ok=True)

    mgr.current_drama = {
        "id": "sm_test_01",
        "title": "Magic Failure's Phoenix Fate",
        "title_cn": "凤落残局",
        "platform_id": "shortmax",
        "synopsis": "A banished phoenix daughter rises from the ashes to reclaim her rightful throne."
    }

    mgr.generate_drama_metadata_card(test_dir, total_episodes=50)

    info_p = test_dir / "drama_info.json"
    syn_p = test_dir / "synopsis_khmer.txt"

    assert not info_p.exists(), "drama_info.json should not be created!"
    assert not syn_p.exists(), "synopsis_khmer.txt should not be created!"
    print("  ✅ Clean download verified: No clutter files created!")

    # 2. Test Stream Resolution with Smart Fallback
    print("\n[TEST 2] Testing Smart Stream Resolution across Platforms...")
    d_shortmax = {"id": "sm_000001", "platform_id": "shortmax", "title": "Magic Failure's Phoenix Fate"}
    eps = downloader.get_drama_episodes(d_shortmax, resolve_streams=True)
    assert len(eps) > 0, "Failed to resolve ShortMax episodes"
    assert eps[0].get("stream_url"), "ShortMax stream_url missing"
    print(f"  ✅ ShortMax resolved: {len(eps)} episodes (Stream: {eps[0]['stream_url'][:45]}...)")

    # Clean up test artifacts
    if test_dir.exists():
        shutil.rmtree(test_dir, ignore_errors=True)

    print("\n" + "=" * 60)
    print("🎉 ALL PHASE 2 TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 60)

if __name__ == "__main__":
    run_phase2_tests()

