import sys
import os
import subprocess
import webbrowser
import threading
import time

# Enable utf-8 output in Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from audio_processor import patch_silent_subprocess, get_silent_kwargs

patch_silent_subprocess()

from desktop_app import check_and_handle_running_server

from server import app

def launch_native_window(url="http://127.0.0.1:8000", title="SN TOOL"):
    """
    Launch SN TOOL as a dedicated native desktop software window:
    1. Try pywebview (Native Edge WebView2 window)
    2. Try Standalone App Window Mode via Microsoft Edge or Chrome (--app=)
    3. Fallback to default browser
    """
    time.sleep(1.0)
    # 1. Try pywebview
    try:
        import webview
        from desktop_app import NativeWindowApi, is_window_zoomed, get_standard_window_geometry, enforce_center_window

        win_w, win_h, x, y = get_standard_window_geometry()
        api = NativeWindowApi()
        window = webview.create_window(
            title=title,
            url=url,
            frameless=True,
            easy_drag=False,
            shadow=True,
            maximized=False,
            width=win_w,
            height=win_h,
            x=x,  # Explicitly centered X coordinate
            y=y,  # Explicitly centered Y coordinate
            resizable=True,
            min_size=(960, 580),
            background_color="#08090d",
            text_select=True,
            zoomable=True,
            js_api=api
        )

        try:
            orig_move = window.move
            def safe_window_move(mx, my):
                try:
                    if is_window_zoomed() or api._is_maximized:
                        return
                except Exception:
                    pass
                return orig_move(mx, my)
            window.move = safe_window_move
        except Exception:
            pass

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
                        color = ctypes.c_int(0x0015CCFA)
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd, DWMWA_BORDER_COLOR, ctypes.byref(color), ctypes.sizeof(color)
                        )
                        enforce_center_window(hwnd)
                        threading.Timer(0.15, lambda: enforce_center_window(hwnd)).start()
                        threading.Timer(0.30, lambda: enforce_center_window(hwnd)).start()
                except Exception:
                    pass

        webview.start(on_gui_ready, window, private_mode=False, gui='edgechromium')
        return
    except Exception as e:
        print(f"pywebview notice: {e}")

    # 2. Try Native Desktop App Mode via Edge or Chrome (Standalone window, zero browser chrome/tabs)
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
                cmd = [exe, f"--app={url}", "--window-size=1360,860"]
                t0 = time.time()
                proc = subprocess.Popen(cmd)
                proc.wait()
                if time.time() - t0 > 3.0:
                    return
            except Exception as e:
                print(f"App window mode notice: {e}")

    # 3. Clean exit
    os._exit(0)

if __name__ == "__main__":
    if check_and_handle_running_server():
        time.sleep(1.5)
        sys.exit(0)

    os.makedirs("cache/audio_cache", exist_ok=True)
    os.makedirs("data/projects", exist_ok=True)
    os.makedirs("data/uploads", exist_ok=True)

    print("\n========================================================")
    print(" 🎬 Starting SN TOOL (Native Desktop App)...")
    print(" 🎙️ Official Voiceover Models: Piseth (Male Solo) & Sreymom (Female Solo)")
    print(" 🌐 Server Address: http://127.0.0.1:8000")
    print("========================================================\n")

    # Run server in daemon thread
    server_thread = threading.Thread(target=lambda: app.run(host="127.0.0.1", port=8000, debug=False, use_reloader=False), daemon=True)
    server_thread.start()

    # Launch native desktop application window
    launch_native_window()

    print("\n[INFO] កម្មវិធីកំពុងដំណើរការ! (ចុច Ctrl+C ដើម្បីបិទកម្មវិធី)\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nកំពុងបិទកម្មវិធី...")
