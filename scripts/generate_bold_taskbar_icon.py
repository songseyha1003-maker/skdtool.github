# -*- coding: utf-8 -*-
"""
Generate ultra-crisp, full-bleed multi-resolution Windows Icon (.ico)
Eliminates massive transparent padding so the icon appears 2x larger and bolder on Windows Taskbars.
"""
import shutil
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent

def build_icon():
    src_logo = BASE_DIR / "static" / "logo.png"
    if not src_logo.exists():
        src_logo = BASE_DIR / "static" / "sn_logo_badge.png"

    print(f"[*] Loading source logo: {src_logo.name}")
    src_img = Image.open(src_logo).convert("RGBA")

    # 1. Crop tight bounding box of visible pixels
    bbox = src_img.getbbox()
    cropped = src_img.crop(bbox)
    print(f"[*] Cropped visible logo area: {cropped.size} (aspect ratio: {cropped.width / cropped.height:.3f})")

    # 2. Build multi-resolution frames
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    frames = []

    for size_w, size_h in icon_sizes:
        # Create transparent square canvas
        canvas = Image.new("RGBA", (size_w, size_h), (0, 0, 0, 0))

        # 95% fill (2.5% safe margin to prevent OS clipping while maximizing visual presence)
        fill_factor = 0.96 if size_w >= 48 else 0.98
        target_h = int(size_h * fill_factor)
        target_w = int(target_h * (cropped.width / cropped.height))

        # Ensure width doesn't exceed canvas
        if target_w > size_w:
            target_w = int(size_w * fill_factor)
            target_h = int(target_w * (cropped.height / cropped.width))

        scaled = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # For smaller sizes (taskbar 16, 24, 32), slightly sharpen and boost contrast for maximum punch
        if size_w <= 32:
            enhancer = ImageEnhance.Contrast(scaled)
            scaled = enhancer.enhance(1.15)
            sat_enhancer = ImageEnhance.Color(scaled)
            scaled = sat_enhancer.enhance(1.10)
            sharp_enhancer = ImageEnhance.Sharpness(scaled)
            scaled = sharp_enhancer.enhance(1.20)

        # Center on canvas
        pos_x = (size_w - target_w) // 2
        pos_y = (size_h - target_h) // 2
        canvas.paste(scaled, (pos_x, pos_y), scaled)
        frames.append(canvas)

    # 3. Save master icon.ico with all frames
    target_ico = BASE_DIR / "icon.ico"
    target_favicon = BASE_DIR / "static" / "favicon.ico"

    # Pillow saves frames when save is called on first frame
    frames[0].save(
        target_ico,
        format="ICO",
        sizes=icon_sizes,
        append_images=frames[1:]
    )
    print(f"✅ Generated new full-bleed icon.ico ({target_ico.stat().st_size} bytes)")

    # Also save favicon.ico
    frames[0].save(
        target_favicon,
        format="ICO",
        sizes=icon_sizes,
        append_images=frames[1:]
    )
    print(f"✅ Generated new static/favicon.ico")

    # 4. Sync across all dist & internal folders
    sync_targets = [
        BASE_DIR / "_internal" / "static" / "favicon.ico",
        BASE_DIR / "dist" / "SN_TOOL" / "icon.ico",
        BASE_DIR / "dist" / "SN_TOOL" / "static" / "favicon.ico",
        BASE_DIR / "dist" / "SN_TOOL" / "_internal" / "icon.ico",
        BASE_DIR / "dist" / "SN_TOOL" / "_internal" / "static" / "favicon.ico",
        BASE_DIR / "dist" / "ADMIN_KEY_GENERATOR" / "icon.ico",
        BASE_DIR / "dist" / "ADMIN_KEY_GENERATOR" / "static" / "favicon.ico",
        BASE_DIR / "dist" / "ADMIN_KEY_GENERATOR" / "_internal" / "static" / "favicon.ico",
    ]

    for dest in sync_targets:
        if dest.parent.exists():
            shutil.copy2(target_ico if dest.name == "icon.ico" else target_favicon, dest)
            print(f"  ✔ Synced to {dest.relative_to(BASE_DIR)}")

    print("\n🎉 All icon assets have been upgraded to 2x Bolder, Full-Bleed visuals!")

if __name__ == "__main__":
    build_icon()
