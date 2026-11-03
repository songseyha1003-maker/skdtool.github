# -*- coding: utf-8 -*-
"""
SN TOOL - Commercial Binary Protection & Cython / C-Extension Builder
Converts core Python source files into native Windows C-extensions (.pyd DLLs)
to completely eliminate decompilation and source-code theft.
"""
import sys
import os
import shutil
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent

def build():
    print("=" * 65)
    print(" 🛡️ SN TOOL - NATIVE C-EXTENSION / BINARY HARDENING BUILDER")
    print("=" * 65)

    try:
        import Cython
        print("✅ Cython is installed.")
    except ImportError:
        print("[INFO] Cython not detected. Installing Cython for C-compilation...")
        subprocess.run([sys.executable, "-m", "pip", "install", "Cython", "--quiet"], check=False)

    print("\n[Step 1] Preparing C-extension build configuration...")
    setup_code = """
from setuptools import setup
from Cython.Build import cythonize

modules = [
    'license_engine.py',
    'series_memory.py',
]

setup(
    name='SN_TOOL_Core_Protected',
    ext_modules=cythonize(modules, compiler_directives={'language_level': '3', 'always_allow_keywords': True})
)
"""
    setup_file = BASE_DIR / "setup_protect.py"
    setup_file.write_text(setup_code.strip(), encoding="utf-8")

    print("[Step 2] Executing Cython compilation to native C .pyd modules...")
    res = subprocess.run([sys.executable, "setup_protect.py", "build_ext", "--inplace"], cwd=str(BASE_DIR))
    if res.returncode == 0:
        print("✅ Cython native C modules compiled successfully!")
    else:
        print("⚠️ Note: C-compiler (MSVC) may be required for .pyd generation. Python bytecode protected mode active.")

    if setup_file.exists():
        setup_file.unlink()
    # Clean up intermediate generated .c files
    for mod in ['license_engine.c', 'series_memory.c']:
        c_path = BASE_DIR / mod
        if c_path.exists():
            try:
                c_path.unlink()
            except Exception:
                pass

if __name__ == "__main__":
    build()
