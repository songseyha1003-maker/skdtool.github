import os
import sys
import subprocess
from pathlib import Path

def build_installer():
    base_dir = Path(__file__).resolve().parent.parent
    installer_script = base_dir / "scripts" / "installer_gui.py"
    payload_zip = base_dir / "cache" / "setup_payload.zip"
    icon_file = base_dir / "icon.ico"
    output_dir = base_dir / "dist"
    
    print(f"[*] Packaging fresh setup payload from {base_dir / 'dist' / 'SN_TOOL'}...")
    import zipfile
    p = base_dir / "dist" / "SN_TOOL"
    payload_zip.parent.mkdir(parents=True, exist_ok=True)
    if payload_zip.exists():
        payload_zip.unlink(missing_ok=True)
    with zipfile.ZipFile(payload_zip, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=4) as zf:
        for f in p.rglob('*'):
            if f.is_file():
                if f.name.lower() == "license.key":
                    continue  # Strictly exclude license.key so clients start unactivated
                zf.write(f, f.relative_to(p))
    print(f"[OK] Payload zip ready ({payload_zip.stat().st_size / (1024*1024):.2f} MB)")
                    
    print("[*] Compiling SN_TOOL_Setup.exe via PyInstaller...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "SN_TOOL_Setup",
        f"--icon={icon_file}",
        f"--add-data={payload_zip};.",
        f"--add-data={icon_file};.",
        f"--add-data={base_dir / 'static' / 'logo.png'};.",
        f"--version-file={base_dir / 'scripts' / 'version_info_installer.txt'}",
        "--noupx",
        "--uac-admin",
        "--distpath", str(output_dir),
        "--workpath", str(base_dir / "build" / "installer_build"),
        "--specpath", str(base_dir / "build"),
        "-y",
        str(installer_script)
    ]
    
    res = subprocess.run(cmd, cwd=str(base_dir))
    if res.returncode == 0:
        exe_path = output_dir / "SN_TOOL_Setup.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("=" * 60)
            print(f"[SUCCESS] Created standalone installer: {exe_path}")
            print(f"File Size: {size_mb:.2f} MB")
            print("=" * 60)
            return True
    print("[ERROR] Compilation failed.")
    return False

if __name__ == "__main__":
    build_installer()
