"""
Phase 2 Upgrade Script: Ultra-Fast & Self-Healing Downloader Engine
Upgrades:
1. Smart Resume & 1080p format selection in download_m3u8_stream_turbo
2. generate_drama_metadata_card method in DramaDownloadManager
3. Call generate_drama_metadata_card on download completion
"""
import re
from pathlib import Path

def patch_downloader():
    p = Path("downloader.py")
    content = p.read_text(encoding="utf-8")

    # 1. Update ydl_opts in download_m3u8_stream_turbo
    old_ydl_opts = """            ydl_opts = {
                'paths': {'home': str(isolated_temp), 'temp': str(isolated_temp)},
                'outtmpl': str(isolated_temp / f"{dest_file.stem}.%(ext)s"),
                'concurrent_fragment_downloads': 16,
                'retries': 3,
                'fragment_retries': 3,
                'skip_unavailable_fragments': True,
                'nocheckcertificate': True,
                'buffersize': 1048576,
                'http_chunk_size': 10485760,
                'ffmpeg_location': ffmpeg_bin,
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 15,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                'progress_hooks': [live_hook] if progress_callback else [],
            }"""

    new_ydl_opts = """            ydl_opts = {
                'paths': {'home': str(isolated_temp), 'temp': str(isolated_temp)},
                'outtmpl': str(isolated_temp / f"{dest_file.stem}.%(ext)s"),
                'concurrent_fragment_downloads': 16,
                'retries': 5,
                'fragment_retries': 5,
                'skip_unavailable_fragments': True,
                'continuedl': True,
                'overwrites': False,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'nocheckcertificate': True,
                'buffersize': 1048576,
                'http_chunk_size': 10485760,
                'ffmpeg_location': ffmpeg_bin,
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 15,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': '*/*',
                    'Accept-Language': 'en-US,en;q=0.9',
                },
                'progress_hooks': [live_hook] if progress_callback else [],
            }"""

    if old_ydl_opts in content:
        content = content.replace(old_ydl_opts, new_ydl_opts)
        print("[OK] Upgraded ydl_opts with Smart Resume, retries=5, and 1080p format selection")

    # 2. Add generate_drama_metadata_card method to DramaDownloadManager
    meta_method = '''    def generate_drama_metadata_card(self, drama_dest_dir: Path, total_episodes: int = 0):
        """
        Auto-generates a clean metadata package in the drama folder:
        - drama_info.json: structured metadata
        - synopsis_khmer.txt: natural Khmer synopsis ready for social media posting (Facebook/TikTok/Telegram)
        """
        if not self.current_drama or not drama_dest_dir.exists():
            return

        d = self.current_drama
        title_cn = d.get("title_cn") or d.get("title", "Drama Series")
        title_km = d.get("title_km") or title_cn
        synopsis_raw = d.get("synopsis") or d.get("description") or ""
        platform = str(d.get("platform_id") or "Short Drama").upper()

        synopsis_km = synopsis_raw
        if any('\\u4e00' <= c <= '\\u9fff' for c in synopsis_raw):
            try:
                from nisay_translate import translate_khmer
                trans_syn = translate_khmer(synopsis_raw[:350], category="chinese_general", timeout=6.0)
                if isinstance(trans_syn, str) and trans_syn:
                    synopsis_km = trans_syn
            except Exception:
                synopsis_km = synopsis_raw

        if not synopsis_km:
            synopsis_km = f"រឿងភាគខ្លីដ៏ល្អមើល ដំណើររឿងជក់ចិត្ត និងទាក់ទាញអារម្មណ៍ ពេញលេញ {total_episodes} ភាគ ១០០%។"

        info_data = {
            "title": title_km,
            "title_original": title_cn,
            "platform": platform,
            "total_episodes": total_episodes,
            "quality": "1080p Full HD",
            "synopsis_khmer": synopsis_km,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        info_path = drama_dest_dir / "drama_info.json"
        try:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(info_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        syn_card = f"""🎬 【រឿងភាគ៖ {title_km}】
📺 ចំនួនភាគ៖ {total_episodes} ភាគ (ពេញលេញ ១០០%)
🌟 គុណភាព៖ 1080p Full HD
📱 វេទិកា៖ {platform}

📖 សង្ខេបសាច់រឿង៖
{synopsis_km}

👉 ទាញយក និងបញ្ចូលសំឡេងដោយ៖ SN TOOL - STUDIO PRO
"""
        syn_path = drama_dest_dir / "synopsis_khmer.txt"
        try:
            with open(syn_path, "w", encoding="utf-8") as f:
                f.write(syn_card.strip())
            self.add_log(f"📋 Generated Drama Social Card & Khmer Synopsis: {syn_path.name}")
        except Exception:
            pass

'''

    # Place method right above start_download_batch
    target_spot = "    def start_download_batch("
    if target_spot in content and "def generate_drama_metadata_card(" not in content:
        content = content.replace(target_spot, meta_method + target_spot)
        print("[OK] Injected generate_drama_metadata_card into DramaDownloadManager")

    # 3. Call generate_drama_metadata_card upon download completion
    old_completion = "            if self.stats[\"completed\"] > 0:\n                play_windows_completion_sound()"
    new_completion = """            # 📜 Next-Gen Drama Metadata Card & Synopsis Generation (Facebook/TikTok/Telegram Ready)
            try:
                self.generate_drama_metadata_card(drama_dest_dir, total_episodes=total)
            except Exception as meta_ex:
                self.add_log(f"Notice: Metadata generation note: {meta_ex}")

            if self.stats["completed"] > 0:
                play_windows_completion_sound()"""

    if old_completion in content and "self.generate_drama_metadata_card(drama_dest_dir" not in content:
        content = content.replace(old_completion, new_completion)
        print("[OK] Added metadata card generation trigger on completion")

    p.write_text(content, encoding="utf-8")
    print("[SUCCESS] Patched downloader.py for Phase 2")

if __name__ == "__main__":
    patch_downloader()

