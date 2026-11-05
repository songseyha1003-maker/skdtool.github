"""
Khmer AI Drama Voice Translator & Movie Recap Studio - Native Desktop Application
Combines the backend server and embedded native desktop window.
"""
import sys
import os
import time
import threading
import multiprocessing
from pathlib import Path

# Required for PyInstaller frozen applications on Windows
multiprocessing.freeze_support()

# Protect against any accidental child process execution
if len(sys.argv) > 1 and sys.argv[1] in ("-c", "--help", "-h"):
    sys.exit(0)

# Enable native Per-Monitor V2 High DPI on Windows (crystal clear UI & dialogs)
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
# Safe stdout/stderr fallback for windowed / GUI mode where sys.stdout is None
class _SafeStream:
    def write(self, s): pass
    def flush(self): pass
    def reconfigure(self, **kwargs): pass
    def isatty(self): return False

if sys.stdout is None:
    sys.stdout = _SafeStream()
else:
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if sys.stderr is None:
    sys.stderr = _SafeStream()
else:
    try:
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Global Crash Protection Hook
def global_crash_protection(exctype, value, tb):
    import traceback
    err_text = "".join(traceback.format_exception(exctype, value, tb))
    print(f"\n[CRASH PREVENTED] {err_text}", file=sys.stderr)
    try:
        log_dir = APP_DIR / "data"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "crash_log.txt", "a", encoding="utf-8") as f:
            f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {err_text}\n")
    except Exception:
        pass

sys.excepthook = global_crash_protection
if hasattr(threading, 'excepthook'):
    threading.excepthook = lambda args: global_crash_protection(args.exc_type, args.exc_value, args.exc_traceback)

# Ensure working directory is set to app base directory
if getattr(sys, 'frozen', False):
    # Running as compiled executable (PyInstaller)
    BASE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(os.path.dirname(sys.executable))
else:
    # Running as script
    BASE_DIR = Path(__file__).resolve().parent
    APP_DIR = BASE_DIR

os.chdir(str(APP_DIR))
os.makedirs(str(APP_DIR / "cache" / "audio_cache"), exist_ok=True)
os.makedirs(str(APP_DIR / "data" / "projects"), exist_ok=True)
os.makedirs(str(APP_DIR / "data" / "uploads"), exist_ok=True)

# =========================================================================
# 🚀 DYNAMIC RUNTIME HOT-RELOAD & DISK IMPORTER PRIORITY:
# Ensures that updated .py / .pyc files on disk (from in-app updates or sync)
# are ALWAYS prioritized over PyInstaller's frozen PYZ archive!
# =========================================================================
if getattr(sys, 'frozen', False):
    import importlib.machinery
    import importlib.util
    
    app_dir_str = str(APP_DIR)
    internal_dir_str = str(APP_DIR / "_internal")
    
    for p_dir in [app_dir_str, internal_dir_str]:
        if p_dir not in sys.path:
            sys.path.insert(0, p_dir)

    class DiskPriorityFinder:
        _intercepted = {
            "server", "downloader", "translator", "pipeline", "stt_engine",
            "tts_engine", "audio_processor", "video_processor", "hongguo_service",
            "hongguo_db", "shortmax_service", "reelshort_service", "vocal_remover",
            "license_engine", "update", "batch_engine", "series_memory",
            "recap_engine", "subtitle_styler", "translate_video",
            "nisay_transcribe", "nisay_translate"
        }

        @classmethod
        def find_spec(cls, fullname, path=None, target=None):
            top_pkg = fullname.split(".")[0] if "." in fullname else fullname
            if top_pkg in cls._intercepted:
                # Search disk locations (APP_DIR first, then _internal)
                for search_dir in [APP_DIR, APP_DIR / "_internal"]:
                    rel_parts = fullname.split(".")
                    # 1. Look for .py file
                    cand_py = search_dir.joinpath(*rel_parts).with_suffix(".py")
                    if cand_py.exists():
                        return importlib.util.spec_from_file_location(fullname, str(cand_py))
                    # 2. Look for .pyc file
                    cand_pyc = search_dir.joinpath(*rel_parts).with_suffix(".pyc")
                    if cand_pyc.exists():
                        return importlib.util.spec_from_file_location(fullname, str(cand_pyc))
            return None

    sys.meta_path.insert(0, DiskPriorityFinder)

    # Self-healing binary backup against Windows Defender false-positive quarantine
    try:
        current_exe = Path(sys.executable)
        bak_exe = current_exe.with_suffix(".exe.bak")
        if current_exe.exists() and (not bak_exe.exists() or current_exe.stat().st_mtime > bak_exe.stat().st_mtime):
            import shutil
            shutil.copy2(current_exe, bak_exe)
    except Exception:
        pass

import subprocess
from audio_processor import patch_silent_subprocess, get_silent_kwargs

patch_silent_subprocess()

def focus_existing_window():
    """Bring existing SN TOOL window to foreground if already running."""
    if sys.platform == "win32":
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, "SN TOOL")
            if not hwnd:
                EnumWindows = ctypes.windll.user32.EnumWindows
                EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
                found_hwnd = ctypes.c_void_p(0)
                def foreach_window(h, l):
                    length = ctypes.windll.user32.GetWindowTextLengthW(h)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(h, buff, length + 1)
                        if "SN TOOL" in buff.value:
                            found_hwnd.value = h
                            return False
                    return True
                EnumWindows(EnumWindowsProc(foreach_window), 0)
                hwnd = found_hwnd.value

            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                return True
        except Exception:
            pass
    return False

def check_and_handle_running_server():
    """
    Check if port 8000 is already running SN TOOL.
    - If a healthy visible window exists, bring it to front and return True.
    - If port 8000 is occupied by a headless / zombie process (no window visible),
      kill the zombie process immediately so this instance can launch a fresh native desktop window!
    - Under NO circumstance will it ever open in a web browser.
    """
    import urllib.request
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/license/status", headers={"User-Agent": "SN_TOOL_Launcher"})
        with urllib.request.urlopen(req, timeout=1.5) as r:
            if r.status == 200:
                # Server is responding: check if a visible native desktop window exists
                if focus_existing_window():
                    print("\n" + "=" * 65)
                    print(" ✅ SN TOOL is already running on your computer!")
                    print(" 🖥️ Bringing Desktop application window to foreground...")
                    print("=" * 65 + "\n")
                    return True
                # Port 8000 is responding but NO visible desktop window exists!
                # Clean up the hidden orphan/zombie process so we can launch cleanly:
                print("[INFO] Detected orphaned server process. Cleaning up to launch new Native Desktop window...")
    except Exception:
        pass

    # If port 8000 is occupied (by zombie/dead listener), kill it
    if sys.platform == "win32":
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                in_use = (s.connect_ex(('127.0.0.1', 8000)) == 0)
            if in_use:
                out = subprocess.check_output('netstat -ano | findstr :8000', shell=True, **get_silent_kwargs()).decode()
                current_pid = os.getpid()
                for line in out.strip().split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 5 and 'LISTENING' in line:
                        pid = int(parts[-1])
                        if pid != current_pid and pid > 0:
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **get_silent_kwargs())
                time.sleep(0.5)
        except Exception:
            pass

    return False

from server import app

def start_server():
    """Run Flask server in background thread."""
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    app.run(host="127.0.0.1", port=8000, debug=False, use_reloader=False)

_main_window = None
_user_requested_exit = False

def is_window_zoomed():
    """Check if the native window is currently maximized."""
    global _main_window
    if not _main_window:
        return False

    # 1. Native WinForms WindowState check
    try:
        if hasattr(_main_window, 'native') and _main_window.native:
            ws = getattr(_main_window.native, 'WindowState', None)
            if ws is not None:
                ws_str = str(ws)
                if 'Maximized' in ws_str or ws_str == '2':
                    return True
    except Exception:
        pass

    # 2. Windows Win32 API IsZoomed check with proper IntPtr Handle extraction
    try:
        if sys.platform == "win32":
            import ctypes
            hwnd = None
            if hasattr(_main_window, 'native') and _main_window.native:
                try:
                    h = _main_window.native.Handle
                    hwnd = int(str(h)) if hasattr(h, 'ToString') else int(h.ToInt64())
                except Exception:
                    try:
                        hwnd = int(h.ToInt32())
                    except Exception:
                        pass
            if not hwnd:
                hwnd = ctypes.windll.user32.FindWindowW(None, "SN TOOL")
            if hwnd:
                return bool(ctypes.windll.user32.IsZoomed(hwnd))
    except Exception:
        pass

    # 3. Geometry check against primary monitor screen bounds
    try:
        import webview
        screens = getattr(webview, 'screens', None)
        s = screens[0] if screens else None
        if s and hasattr(_main_window, 'width') and hasattr(_main_window, 'height'):
            if _main_window.width >= (s.width - 35) and _main_window.height >= (s.height - 75):
                return True
    except Exception:
        pass

    return False

class NativeWindowApi:
    def __init__(self):
        self._is_maximized = False

    def minimize_window(self):
        global _main_window
        if _main_window:
            try:
                _main_window.minimize()
            except Exception:
                pass

    def maximize_window(self):
        global _main_window
        if _main_window:
            try:
                was_zoomed = is_window_zoomed() or self._is_maximized
                if was_zoomed:
                    _main_window.restore()
                    self._is_maximized = False
                    return {"maximized": False}
                else:
                    _main_window.maximize()
                    self._is_maximized = True
                    return {"maximized": True}
            except Exception:
                try:
                    _main_window.maximize()
                    self._is_maximized = True
                    return {"maximized": True}
                except Exception:
                    pass
        return {"maximized": False}

    def is_window_maximized(self):
        return is_window_zoomed() or self._is_maximized

    def toggle_fullscreen(self):
        global _main_window
        if _main_window:
            try:
                _main_window.toggle_fullscreen()
            except Exception:
                pass

    def force_maximize(self):
        global _main_window
        if _main_window:
            try:
                _main_window.maximize()
                self._is_maximized = True
            except Exception:
                pass

    def close_window(self):
        global _main_window, _user_requested_exit
        _user_requested_exit = True
        if _main_window:
            try:
                _main_window.destroy()
            except Exception:
                pass

def get_standard_window_geometry():
    """
    Calculate ideal desktop window size & centered coordinates.
    Provides standard desktop app dimensions (similar to CapCut, Photoshop, Telegram, Filmora):
    - Width: ~76-78% of work area width
    - Height: ~86-88% of work area height
    - Centered on primary monitor
    - Taskbar completely visible and unobstructed
    """
    sw, sh = 1920, 1080
    wa_left = 0
    wa_top = 0

    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            class RECT(ctypes.Structure):
                _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG), ('right', wintypes.LONG), ('bottom', wintypes.LONG)]
            wa = RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(wa), 0)
            wa_left = wa.left
            wa_top = wa.top
            sw = max(1024, wa.right - wa.left)
            sh = max(650, wa.bottom - wa.top)
        except Exception:
            pass
    else:
        try:
            import webview
            screens = getattr(webview, 'screens', None)
            if screens and len(screens) > 0:
                sw = screens[0].width
                sh = screens[0].height
        except Exception:
            pass

    # Generous Pro Studio desktop window dimensions:
    target_w = min(1520, max(1240, int(sw * 0.82)))
    target_h = min(920, max(750, int(sh * 0.86)))

    x = wa_left + max(0, (sw - target_w) // 2)
    y = wa_top + max(0, (sh - target_h) // 2)

    return target_w, target_h, x, y

def enforce_center_window(target_hwnd):
    """Ensure the native window is positioned dead center on the primary monitor work area with plenty of margin."""
    if sys.platform != "win32" or not target_hwnd:
        return
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG), ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

        wa = RECT()
        user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(wa), 0)
        wa_w = wa.right - wa.left
        wa_h = wa.bottom - wa.top

        w = min(1520, max(1240, int(wa_w * 0.82)))
        h = min(920, max(750, int(wa_h * 0.86)))

        cx = wa.left + max(0, (wa_w - w) // 2)
        cy = wa.top + max(0, (wa_h - h) // 2)

        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_SHOWWINDOW = 0x0040
        user32.SetWindowPos(target_hwnd, 0, cx, cy, w, h, SWP_NOZORDER | SWP_SHOWWINDOW)
    except Exception:
        pass

def launch_native_window(url="http://127.0.0.1:8000", title="SN TOOL"):
    """
    Open application in a dedicated standalone native desktop window:
    1. Try pywebview (Edge WebView2 native embed) in standard centered desktop window size
    2. Try Standalone App Window Mode via Microsoft Edge or Google Chrome (--app=) centered
    3. Fallback to default browser
    """
    win_w, win_h, x, y = get_standard_window_geometry()

    # 1. Try pywebview
    try:
        import webview
        global _main_window

        api = NativeWindowApi()
        window = webview.create_window(
            title=title,
            url=url,
            frameless=True,
            easy_drag=False,  # Prevent pywebview's buggy global mousedown listener from moving window on right-click or arbitrary clicks
            shadow=True,
            maximized=False,
            width=win_w,
            height=win_h,
            x=x,  # Explicitly centered X coordinate
            y=y,  # Explicitly centered Y coordinate
            resizable=True,
            min_size=(1180, 680),
            background_color="#08090d",
            text_select=True,
            zoomable=True,
            js_api=api
        )
        _main_window = window

        # Safeguard move calls: NEVER move or drag window when it is maximized
        try:
            orig_move = window.move
            def safe_window_move(mx, my):
                try:
                    if is_window_zoomed() or api._is_maximized:
                        return  # Window is MAXIMIZED: strictly block any dragging/movement!
                except Exception:
                    pass
                return orig_move(mx, my)
            window.move = safe_window_move
        except Exception:
            pass

        # Native event listeners to synchronize maximized state to frontend immediately
        def on_window_maximized():
            try:
                api._is_maximized = True
                window.evaluate_js("setWindowMaximizedState(true)")
            except Exception:
                pass

        def on_window_restored():
            try:
                api._is_maximized = False
                window.evaluate_js("setWindowMaximizedState(false)")
            except Exception:
                pass

        try:
            window.events.maximized += on_window_maximized
            window.events.restored += on_window_restored
        except Exception:
            pass

        def on_gui_ready(w):
            try:
                w.move(x, y)
            except Exception:
                pass

            if sys.platform == "win32":
                try:
                    import ctypes
                    hwnd = None
                    if hasattr(w, 'native') and w.native:
                        try:
                            h = w.native.Handle
                            hwnd = int(str(h)) if hasattr(h, 'ToString') else int(h.ToInt64())
                        except Exception:
                            try:
                                hwnd = int(w.native.Handle.ToInt32())
                            except Exception:
                                pass

                        try:
                            w.native.CenterToScreen()
                        except Exception:
                            pass

                    if not hwnd:
                        hwnd = ctypes.windll.user32.FindWindowW(None, title)
                    if hwnd:
                        DWMWA_WINDOW_CORNER_PREFERENCE = 33
                        DWMWCP_ROUND = 2
                        pref = ctypes.c_int(DWMWCP_ROUND)
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(pref), ctypes.sizeof(pref)
                        )
                        DWMWA_BORDER_COLOR = 34
                        # Apple Pro Dark Obsidian Frame (#1e2430 -> R:0x1E, G:0x24, B:0x30 -> BGR: 0x0030241E)
                        color = ctypes.c_int(0x0030241E)
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd, DWMWA_BORDER_COLOR, ctypes.byref(color), ctypes.sizeof(color)
                        )
                        # Set official high-res application icon on window and Windows Taskbar
                        try:
                            icon_candidates = [
                                str(Path("icon.ico").resolve()),
                                str(Path(__file__).resolve().parent / "icon.ico"),
                                str(Path("static/favicon.ico").resolve())
                            ]
                            icon_p = next((p for p in icon_candidates if os.path.exists(p)), "")
                            if icon_p:
                                IMAGE_ICON = 1
                                LR_LOADFROMFILE = 0x00000010
                                WM_SETICON = 0x0080
                                ICON_SMALL = 0
                                ICON_BIG = 1
                                h_icon_big = ctypes.windll.user32.LoadImageW(None, icon_p, IMAGE_ICON, 48, 48, LR_LOADFROMFILE)
                                h_icon_sm = ctypes.windll.user32.LoadImageW(None, icon_p, IMAGE_ICON, 24, 24, LR_LOADFROMFILE)
                                if h_icon_big:
                                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                                if h_icon_sm:
                                    ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_sm)
                                if hasattr(w, 'native') and w.native:
                                    try:
                                        import System.Drawing
                                        w.native.Icon = System.Drawing.Icon(icon_p)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        # Center window on primary monitor work area immediately
                        enforce_center_window(hwnd)
                        # Repeat after 150ms and 300ms to guarantee precision after WebView2 layout
                        threading.Timer(0.15, lambda: enforce_center_window(hwnd)).start()
                        threading.Timer(0.30, lambda: enforce_center_window(hwnd)).start()
                except Exception:
                    pass

        # Ensure closing window completely terminates all background threads and processes
        def on_window_closed():
            os._exit(0)

        try:
            window.events.closed += on_window_closed
        except Exception:
            pass

        webview.start(on_gui_ready, window, private_mode=False, gui='edgechromium', debug=False)
        # Window closed cleanly: exit application immediately
        os._exit(0)
    except Exception as e:
        print(f"[Native App] pywebview notice: {e}")

    # 2. Fallback: Standalone Desktop App Window Mode via Microsoft Edge or Google Chrome
    # (Pure dedicated application window: NO tabs, NO address bar, zero browser chrome)
    app_browsers = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for exe in app_browsers:
        if os.path.exists(exe):
            try:
                cmd = [
                    exe,
                    f"--app={url}",
                    f"--window-size={win_w},{win_h}",
                    f"--window-position={x},{y}",
                    "--disable-features=Translate",
                    "--disable-extensions",
                    "--class=SN_TOOL",
                    "--name=SN TOOL"
                ]
                proc = subprocess.Popen(cmd)
                proc.wait()
                os._exit(0)
            except Exception as e:
                print(f"[Native App] Standalone app mode notice: {e}")

    # 3. If no native rendering engine exists on system, alert user with native Win32 dialog
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                "SN TOOL ត្រូវការ Microsoft Edge WebView2 ដើម្បីដំណើរការជាកម្មវិធី Desktop Native។\nសូមដំឡើង Microsoft Edge WebView2 រួចបើកកម្មវិធីម្តងទៀត។",
                "SN TOOL - Native Desktop Engine Required",
                0x10 | 0x00010000  # MB_ICONERROR | MB_SETFOREGROUND
            )
        except Exception:
            pass
    os._exit(1)

def main():
    print("========================================================")
    print(" 🎬 Starting SN TOOL (Native Desktop App)...")
    print(" 🎙️ Official Voiceover Models: Piseth (Male Solo) & Sreymom (Female Solo)")
    print(" 🖥️ Window Mode: Dedicated Standalone Native Application")
    print("========================================================")

    # 0. Check Hardware Ban / Tamper Lockout
    try:
        from license_engine import is_current_device_banned, get_machine_hwid
        banned, reason = is_current_device_banned()
        if banned and "dbghelp.dll" in str(reason):
            from license_engine import unban_device
            unban_device(get_machine_hwid(), "SN-ADMIN-MASTER-UNBAN-2026")
            banned = False
        if banned:
            hwid = get_machine_hwid()
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"⛔ ឧបករណ៍កុំព្យូទ័រនេះត្រូវបានចាក់សោរជាអចិន្ត្រៃយ៍ (PERMANENT HARDWARE BAN)!\n\n"
                    f"⚠️ មូលហេតុ: {reason}\n"
                    f"🔒 Machine HWID: {hwid}\n\n"
                    f"កម្មវិធីនឹងមិនអាចដំណើរការនៅលើកុំព្យូទ័រនេះបានទៀតឡើយ។\n"
                    f"ប្រសិនបើនេះជាការភាន់ច្រឡំ សូមទាក់ទងមក Admin ផ្ទាល់ដើម្បីស្នើសុំដោះសោរ។",
                    "SN TOOL - HARDWARE SECURITY LOCKOUT",
                    0x10 | 0x00010000  # MB_ICONSTOP | MB_SETFOREGROUND
                )
            sys.exit(1)
    except Exception:
        pass

    # 1. Check if server is already running - if healthy window exists, focus it; if orphan, clean it
    if check_and_handle_running_server():
        time.sleep(1.0)
        return

    # 2. Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1.0)

    # 3. Launch native window (blocks until user closes the window)
    try:
        launch_native_window()
    except Exception as e:
        print(f"[Error] Failed to launch native window: {e}")

    # 4. Clean exit
    os._exit(0)

if __name__ == "__main__":
    main()
