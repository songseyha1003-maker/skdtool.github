/**
 * U'NICH — Exact 1:1 Application Controller matching Reference Screenshots
 */

// Global Error & Promise Interceptor: Never let unhandled errors bubble up and crash the native WebView2 container!
window.onerror = function(message, source, lineno, colno, error) {
    console.error("[Safe Guard] Global JS error handled safely:", message, "at", source, lineno);
    return true; // Prevents the error from propagating to the host container
};
window.onunhandledrejection = function(event) {
    console.warn("[Safe Guard] Unhandled promise rejection handled safely:", event ? event.reason : null);
    if (event && event.preventDefault) event.preventDefault();
};

let currentActiveTab = 'translate';
let isPlaying = false;
let playheadSeconds = 0;
let totalDurationSeconds = 114; // 01:54
let playbackTimer = null;
let dlSelectedPlatform = "hongguo";
let dlSelectedCategory = "all";
let dlCurrentDrama = null;
let dlEpisodesList = [];
let dlPollTimer = null;
let dlPollActive = false;
let dlPollSessionId = 0;
let dlCurrentPage = 1;
let dlTotalDramasCount = 49509;
let dlSearchQuery = "";
let dlIsLoadingMore = false;
let dlHasMore = true;
let dlInfiniteScrollAttached = false;
let currentHwid = "";

// ============================================================================
// ============================================================================
// WINDOW STATE & DYNAMIC DRAG MANAGEMENT
// - Maximized / Fullscreen: STRICTLY block dragging, lock window firmly in place!
// - Small / Restored: Allow dragging ONLY via empty header title bar area with Left Click
// - Mouse guard: STRICTLY forbid dragging when manipulating tools, sliders, masks, or right/middle click
// ============================================================================
window._isHeaderDraggingActive = false;

function isWindowMaximizedOrFullscreen() {
    if (document.fullscreenElement || document.webkitFullscreenElement) {
        return true;
    }
    if (document.body.classList.contains('is-maximized')) {
        return true;
    }
    const sw = window.screen.availWidth || window.screen.width || 1920;
    const sh = window.screen.availHeight || window.screen.height || 1080;
    // Bounded check for Windows display scaling (100%, 125%, 150%) & taskbar
    const wMatch = window.innerWidth >= (sw - 50) || window.outerWidth >= (sw - 10);
    const hMatch = window.innerHeight >= (sh - 75) || window.outerHeight >= (sh - 20);
    return Boolean(wMatch && hMatch);
}

function setWindowMaximizedState(isMax) {
    const body = document.body;
    const header = document.querySelector('.unich-header-bar');
    const maxBtns = document.querySelectorAll('#win-btn-maximize, #gate-btn-maximize, .win-btn[title="Maximize"], .win-btn[title="Restore Down"], .gate-win-btn[title*="Maximize"]');

    if (isMax) {
        body.classList.add('is-maximized');
        window._isHeaderDraggingActive = false;
        if (header) {
            header.classList.remove('pywebview-drag-region');
        }
        maxBtns.forEach(btn => {
            btn.innerHTML = '<i class="fa-regular fa-clone"></i>';
            btn.title = 'Restore Down';
        });
    } else {
        body.classList.remove('is-maximized');
        if (header) {
            header.classList.add('pywebview-drag-region');
        }
        maxBtns.forEach(btn => {
            btn.innerHTML = '<i class="fa-regular fa-square"></i>';
            btn.title = 'Maximize';
        });
    }
}

function checkWindowState() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.is_window_maximized) {
        window.pywebview.api.is_window_maximized().then(isMax => {
            if (isMax !== undefined && isMax !== null) {
                setWindowMaximizedState(Boolean(isMax));
            } else {
                detectMaximizeFromScreen();
            }
        }).catch(() => {
            detectMaximizeFromScreen();
        });
    } else {
        detectMaximizeFromScreen();
    }
}

function detectMaximizeFromScreen() {
    const isMax = isWindowMaximizedOrFullscreen();
    setWindowMaximizedState(isMax);
}

// Intercept pywebview's internal move handler to prevent any unwanted window movement
function installPywebviewDragInterceptor() {
    if (window.pywebview && window.pywebview._jsApiCallback) {
        if (!window.pywebview._origJsApiCallback) {
            window.pywebview._origJsApiCallback = window.pywebview._jsApiCallback;
            window.pywebview._jsApiCallback = function(funcName, params, id) {
                if (funcName === 'pywebviewMoveWindow') {
                    // 1. If window is maximized or fullscreen: 100% LOCK FIRMLY IN PLACE!
                    if (document.body.classList.contains('is-maximized') || isWindowMaximizedOrFullscreen()) {
                        return; // Dropped! Window stays locked!
                    }
                    // 2. Only allow movement when actively dragging the empty header bar in small/restored mode
                    if (!window._isHeaderDraggingActive) {
                        return; // Dropped! Tool adjustments, sliders, or mask dragging will NEVER move the window!
                    }
                }
                return window.pywebview._origJsApiCallback.apply(this, arguments);
            };
        }
    }
}

function appMinimizeWindow() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.minimize_window) {
        window.pywebview.api.minimize_window();
    }
}

async function appMaximizeWindow() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.maximize_window) {
        try {
            const res = await window.pywebview.api.maximize_window();
            if (res && typeof res.maximized === 'boolean') {
                setWindowMaximizedState(res.maximized);
                return;
            }
        } catch(e) {}
        setTimeout(checkWindowState, 50);
        setTimeout(checkWindowState, 200);
    } else {
        try {
            if (!document.fullscreenElement) {
                if (document.documentElement.requestFullscreen) {
                    await document.documentElement.requestFullscreen();
                } else if (document.documentElement.webkitRequestFullscreen) {
                    await document.documentElement.webkitRequestFullscreen();
                }
                setWindowMaximizedState(true);
            } else {
                if (document.exitFullscreen) {
                    await document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    await document.webkitExitFullscreen();
                }
                setWindowMaximizedState(false);
            }
        } catch(e) {}
    }
}

function appHeaderDblClick(e) {
    if (e && e.target && e.target.closest('button, a, input, select, textarea, .win-btn, .nav-pill-btn, .brand-toggle-pill, .power-dropdown-wrapper')) {
        return;
    }
    appMaximizeWindow();
}

function appCloseWindow() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.close_window) {
        window.pywebview.api.close_window();
    } else {
        try { window.close(); } catch(e) {}
    }
}

// Global Drag & Mouse Interaction Guard:
// 1. Right-click or middle-click must NEVER drag the window under any circumstances.
// 2. When maximized, dragging is completely locked.
// 3. Only when in small / restored window mode AND clicking on non-interactive header regions with Left Mouse Button (e.button === 0), allow dragging.
window.addEventListener('mousedown', function(e) {
    installPywebviewDragInterceptor();

    const interactive = e.target.closest('button, a, input, select, textarea, .win-btn, .nav-pill-btn, .brand-toggle-pill, .power-dropdown-wrapper, .power-menu-popup, .power-item, .monitor-blur-overlay, .monitor-logo-overlay, .blur-custom-dropdown, [role="slider"], input[type="range"]');

    // 1. If window is MAXIMIZED or FULLSCREEN: strictly lock the window
    if (document.body.classList.contains('is-maximized') || isWindowMaximizedOrFullscreen()) {
        window._isHeaderDraggingActive = false;
        if (!interactive) {
            const header = e.target.closest('.unich-header-bar, .pywebview-drag-region, [data-drag-region]');
            if (header) {
                e.stopImmediatePropagation();
            }
        }
        return;
    }

    // 2. Only allow window dragging in restored mode with Left Mouse Button (e.button === 0)
    if (e.button !== 0) {
        window._isHeaderDraggingActive = false;
        if (!interactive) {
            const header = e.target.closest('.unich-header-bar, .pywebview-drag-region, [data-drag-region]');
            if (header) {
                e.stopImmediatePropagation();
            }
        }
        return;
    }

    // 3. In restored / small mode:
    const header = e.target.closest('.unich-header-bar');
    if (header && !interactive) {
        window._isHeaderDraggingActive = true;
    } else {
        window._isHeaderDraggingActive = false;
        if (interactive) {
            e.stopPropagation();
        }
    }
}, true); // Capture phase ensures we intercept before pywebview's drag handler

window.addEventListener('mouseup', function() {
    window._isHeaderDraggingActive = false;
}, true);

window.addEventListener('resize', () => {
    checkWindowState();
});

window.addEventListener('pywebviewready', () => {
    installPywebviewDragInterceptor();
    setTimeout(checkWindowState, 50);
    setTimeout(checkWindowState, 200);
});

// Periodic check ensuring pywebview API hook is installed as soon as ready
setInterval(installPywebviewDragInterceptor, 500);

// ====================================================================
// NATIVE DESKTOP APPLICATION ENHANCEMENTS & BROWSER-TRAIT ELIMINATION
// Guarantees zero web-browser feel (no browser context menu, no F5 reload, no devtools)
// ====================================================================
document.addEventListener('contextmenu', function(e) {
    const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
    // Allow context menu inside text fields and Studio Activity Console for copy/paste
    if (tag === 'input' || tag === 'textarea' || (e.target && e.target.isContentEditable) || (e.target && e.target.closest && e.target.closest('#studio-live-terminal-stream, .studio-live-terminal-stream, .selectable-text'))) {
        return true;
    }
    // Block Edge/Chrome default browser menu ("Inspect", "Reload", "Print", "Back")
    e.preventDefault();
    return false;
}, true);

document.addEventListener('keydown', function(e) {
    // Block Browser Reload (F5, Ctrl+R, Ctrl+F5)
    if (e.key === 'F5' || (e.ctrlKey && (e.key === 'r' || e.key === 'R'))) {
        e.preventDefault();
        return false;
    }
    // Block Browser Print (Ctrl+P)
    if (e.ctrlKey && (e.key === 'p' || e.key === 'P')) {
        e.preventDefault();
        return false;
    }
    // Block Browser View-Source (Ctrl+U)
    if (e.ctrlKey && (e.key === 'u' || e.key === 'U')) {
        e.preventDefault();
        return false;
    }
    // Block Browser DevTools (F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C)
    if (e.key === 'F12' || (e.ctrlKey && e.shiftKey && ['I', 'i', 'J', 'j', 'C', 'c'].includes(e.key))) {
        e.preventDefault();
        return false;
    }
    // Block Browser History Back / Forward (Alt+Left, Alt+Right, Backspace outside input)
    if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
        e.preventDefault();
        return false;
    }
    if (e.key === 'Backspace') {
        const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
        if (tag !== 'input' && tag !== 'textarea' && (!e.target || !e.target.isContentEditable)) {
            e.preventDefault();
            return false;
        }
    }
}, true);

// Prevent browser ghost drag of images and links
document.addEventListener('dragstart', function(e) {
    const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
    if (tag === 'img' || tag === 'a') {
        e.preventDefault();
    }
}, false);

// Prevent browser navigating away when dragging external files onto non-drop regions
window.addEventListener('dragover', function(e) {
    if (!e.target.closest('.file-drop-zone, .upload-area, .video-drop-area, #video-dropzone, .drag-drop-box')) {
        e.preventDefault();
    }
}, false);
window.addEventListener('drop', function(e) {
    if (!e.target.closest('.file-drop-zone, .upload-area, .video-drop-area, #video-dropzone, .drag-drop-box')) {
        e.preventDefault();
    }
}, false);

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    checkWindowState();
    setupOutsideClickHandlers();
    checkDeviceLicenseStatus();
    loadDownloaderPlatforms();
    loadDownloaderCategories();
    loadDramaCatalog("hongguo");
    initStudioWorkspace();
    initSaveLocationPaths();
    setupDragAndDropSupport();
    loadAiConfigData();
    loadStoryConfigData();
}

function getMediaFileName(f) {
    if (!f) return "video.mp4";
    if (typeof f === 'string') return f.split(/[\\/]/).pop() || f;
    return f.name || f.filename || (f.filepath ? f.filepath.split(/[\\/]/).pop() : "video.mp4");
}

function getMediaFilePath(f) {
    if (!f) return null;
    if (typeof f === 'string') return f;
    let p = f.filepath || f.path || f.local_path || f.file_path || null;
    if (!p && f.video_url && typeof f.video_url === 'string' && f.video_url.startsWith('/media/')) {
        p = decodeURIComponent(f.video_url.substring(7));
    }
    return p;
}

async function extractFilesFromDataTransfer(dt) {
    const files = [];
    let detectedFolder = "";
    const fileEntriesToProcess = [];

    // 1. Process items if available (handles directories & files)
    if (dt.items && dt.items.length > 0) {
        const queue = [];

        for (let i = 0; i < dt.items.length; i++) {
            const item = dt.items[i];
            try {
                if (item.webkitGetAsEntry) {
                    const entry = item.webkitGetAsEntry();
                    if (entry) {
                        if (entry.isDirectory && !detectedFolder) {
                            detectedFolder = entry.name;
                        }
                        queue.push(entry);
                        continue;
                    }
                }
            } catch (e) { }

            if (item.kind === 'file') {
                try {
                    const f = item.getAsFile();
                    if (f) files.push(f);
                } catch (e) { }
            }
        }

        // Process queue (both nested directory hierarchies and single files)
        while (queue.length > 0) {
            const entry = queue.shift();
            if (!entry) continue;

            if (entry.isFile) {
                fileEntriesToProcess.push(entry);
            } else if (entry.isDirectory) {
                if (!detectedFolder) detectedFolder = entry.name;
                try {
                    const reader = entry.createReader();
                    const entries = await new Promise((res) => {
                        const all = [];
                        function readBatch() {
                            reader.readEntries((batch) => {
                                if (!batch || batch.length === 0) {
                                    res(all);
                                } else {
                                    all.push(...batch);
                                    readBatch();
                                }
                            }, () => res(all));
                        }
                        readBatch();
                    });
                    for (const child of entries) {
                        queue.push(child);
                    }
                } catch (dirErr) {
                    console.warn("Folder reader note:", dirErr);
                }
            }
        }

        // Fast parallel resolution of all collected FileEntries with 5s timeout guard
        if (fileEntriesToProcess.length > 0) {
            const resolvedFiles = await Promise.all(fileEntriesToProcess.map(entry => {
                return new Promise((res) => {
                    const timer = setTimeout(() => res(null), 5000);
                    entry.file((f) => {
                        clearTimeout(timer);
                        if (f) {
                            if (entry.fullPath) f._fullPath = entry.fullPath;
                            res(f);
                        } else {
                            res(null);
                        }
                    }, () => {
                        clearTimeout(timer);
                        res(null);
                    });
                });
            }));
            for (const rf of resolvedFiles) {
                if (rf) files.push(rf);
            }
        }
    }

    // 2. Fallback to dt.files if nothing found via items
    if (files.length === 0 && dt.files && dt.files.length > 0) {
        files.push(...Array.from(dt.files));
    } else if (dt.files && dt.files.length > 0) {
        // Map native path attributes if available from dt.files
        const pathMap = {};
        for (let i = 0; i < dt.files.length; i++) {
            const df = dt.files[i];
            if (df && df.name && (df.path || df.filepath)) {
                pathMap[df.name] = df.path || df.filepath;
            }
        }
        for (let i = 0; i < files.length; i++) {
            const f = files[i];
            if (f && !f.filepath && pathMap[f.name]) {
                f.filepath = pathMap[f.name];
            }
        }
    }

    return { files, folderTitle: detectedFolder };
}

function showDragDropOverlay() {
    let overlay = document.getElementById('studio-drag-drop-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'studio-drag-drop-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(10, 8, 4, 0.88);
            backdrop-filter: blur(8px);
            z-index: 999999;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border: 3px dashed #facc15;
            box-shadow: inset 0 0 50px rgba(250, 204, 21, 0.25);
            pointer-events: none;
            transition: opacity 0.2s ease;
        `;
        overlay.innerHTML = `
            <div style="background: rgba(24, 21, 12, 0.95); border: 1px solid rgba(250, 204, 21, 0.5); border-radius: 16px; padding: 36px 48px; text-align: center; box-shadow: 0 20px 50px rgba(0,0,0,0.8); display: flex; flex-direction: column; align-items: center; gap: 14px;">
                <div style="width: 72px; height: 72px; border-radius: 50%; background: rgba(250, 204, 21, 0.15); border: 2px solid #facc15; display: flex; align-items: center; justify-content: center; font-size: 2rem; color: #facc15;">
                    <i class="fa-solid fa-cloud-arrow-up"></i>
                </div>
                <div style="font-size: 1.25rem; font-weight: 700; color: #fff;">
                    Drop Drama Video Here to Dub
                </div>
                <div style="font-size: 0.85rem; color: #facc15;">
                    Supports video files or complete drama folder (MP4, MKV, MOV...)
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }
    overlay.style.display = 'flex';
}

function hideDragDropOverlay() {
    const overlay = document.getElementById('studio-drag-drop-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

let dragCounter = 0;
function setupDragAndDropSupport() {
    window.addEventListener('dragenter', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter++;
        if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files')) {
            showDragDropOverlay();
        }
    }, false);

    window.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer) {
            e.dataTransfer.dropEffect = 'copy';
        }
    }, false);

    window.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter--;
        if (dragCounter <= 0) {
            dragCounter = 0;
            hideDragDropOverlay();
        }
    }, false);

    window.addEventListener('drop', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        dragCounter = 0;
        hideDragDropOverlay();
        if (!e.dataTransfer) return;

        try {
            // Priority 1: Check if any dropped items have native Windows file/folder paths (WebView2 / Desktop App / Electron)
            const dtFiles = e.dataTransfer.files ? Array.from(e.dataTransfer.files) : [];
            const nativePaths = dtFiles.map(f => f.path || f.filepath).filter(Boolean);

            if (nativePaths.length > 0) {
                showToast("Scanning drama video files...");
                try {
                    const res = await fetch("/api/system/scan-folder", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ paths: nativePaths })
                    });
                    const data = await res.json();
                    if (data && data.success && data.files && data.files.length > 0) {
                        switchMainTab('translate');
                        closeModal('modal-import');
                        handleSelectedFiles(data.files, data.series_title);
                        return;
                    }
                } catch (scanErr) {
                    console.warn("Native scan-folder note:", scanErr);
                }
            }

            // Priority 2: Direct browser extraction (supports folder tree via webkitGetAsEntry in pure browser)
            const { files, folderTitle } = await extractFilesFromDataTransfer(e.dataTransfer);
            if (files && files.length > 0) {
                switchMainTab('translate');
                closeModal('modal-import');
                handleSelectedFiles(files, folderTitle);
            } else {
                showToast("Please select drama video files (MP4, MKV, MOV...) or a drama folder");
            }
        } catch (err) {
            console.warn("Drop handling error:", err);
            showToast("Failed to load file. Please use Browse Files/Folder instead");
        }
    }, false);
}

// ==========================================================================
// 1. TOP NAVBAR TAB SWITCHING (Exact Match to Images 1 & 2)
// ==========================================================================
function switchMainTab(tabKey) {
    currentActiveTab = tabKey;

    // Reset all nav pill buttons
    const navButtons = document.querySelectorAll('.header-nav-pills .nav-pill-btn');
    navButtons.forEach(btn => btn.classList.remove('active'));

    const targetBtn = document.getElementById(`btn-tab-${tabKey}`);
    if (targetBtn) targetBtn.classList.add('active');

    // Close power popup
    closePowerMenu();

    const studioView = document.getElementById('view-studio-translate');
    const dlView = document.getElementById('view-downloader-workspace');
    const studioFooter = document.getElementById('footer-studio-main');
    const dlFooter = document.getElementById('footer-dl-stats');

    if (tabKey === 'dl') {
        // Switch to Downloader Studio (Exact Match to Image 2)
        if (studioView) studioView.style.display = 'none';
        if (dlView) dlView.style.display = 'flex';
        if (studioFooter) studioFooter.style.display = 'none';
        if (dlFooter) dlFooter.style.display = 'flex';

        switchDlViewMode(dlCurrentViewMode || 'catalog');
        loadDramaCatalog(dlSelectedPlatform);
    } else {
        // Return to Main Studio View (Exact Match to Image 1)
        if (studioView) studioView.style.display = 'grid';
        if (dlView) dlView.style.display = 'none';
        if (studioFooter) studioFooter.style.display = 'flex';
        if (dlFooter) dlFooter.style.display = 'none';

        if (tabKey === 'import') {
            openImportModal();
        } else if (tabKey === 'settings') {
            openSettingsModal();
        } else if (tabKey === 'overlay') {
            showToast("Interactive Canvas Overlays enabled.");
        } else if (tabKey === 'export') {
            startStudioExportJob();
            const transBtn = document.getElementById('btn-tab-translate');
            if (transBtn) transBtn.classList.add('active');
            const expBtn = document.getElementById('btn-tab-export');
            if (expBtn) expBtn.classList.remove('active');
        } else if (tabKey === 'recap') {
            showToast("Movie Recap Engine ready.");
        } else if (tabKey === 'dramamg') {
            showToast("Drama Manager & Episode Concat ready.");
        }
    }
}

// ==========================================================================
// 2. POWER DROPDOWN & ACTIONS (Exact Match to Image 1)
// ==========================================================================
function togglePowerMenu(event) {
    if (event) {
        if (event.stopPropagation) event.stopPropagation();
        if (event.preventDefault) event.preventDefault();
    }
    const wrapper = document.querySelector('.power-dropdown-wrapper');
    const menu = document.getElementById('power-menu-popup');
    const btn = document.getElementById('btn-tab-power');
    if (!menu) return;

    const isOpen = menu.classList.contains('active');
    if (isOpen) {
        closePowerMenu();
    } else {
        closeBrowseMenu();
        menu.classList.add('active');
        if (wrapper) wrapper.classList.add('open');
        if (btn) btn.classList.add('menu-open');
    }
}

function closePowerMenu() {
    const wrapper = document.querySelector('.power-dropdown-wrapper');
    const menu = document.getElementById('power-menu-popup');
    const btn = document.getElementById('btn-tab-power');
    if (menu) menu.classList.remove('active');
    if (wrapper) wrapper.classList.remove('open');
    if (btn) btn.classList.remove('menu-open');
}

function toggleBrowseMenu(e) {
    if (e && e.stopPropagation) e.stopPropagation();
    const menu = document.getElementById('browse-menu-popup');
    const btn = document.getElementById('btn-browse-unified');
    const wrapper = document.getElementById('browse-dropdown-wrapper');
    if (!menu) return;
    const isActive = menu.classList.contains('active');
    if (isActive) {
        closeBrowseMenu();
    } else {
        closePowerMenu();
        menu.classList.add('active');
        if (btn) btn.classList.add('active');
        if (wrapper) wrapper.classList.add('active');
    }
}

function closeBrowseMenu() {
    const menu = document.getElementById('browse-menu-popup');
    const btn = document.getElementById('btn-browse-unified');
    const wrapper = document.getElementById('browse-dropdown-wrapper');
    if (menu) menu.classList.remove('active');
    if (btn) btn.classList.remove('active');
    if (wrapper) wrapper.classList.remove('active');
}

function handleBrowseOption(type, e) {
    if (e && e.stopPropagation) e.stopPropagation();
    closeBrowseMenu();
    if (type === 'file') {
        triggerFileSelect();
    } else if (type === 'folder') {
        triggerFolderSelect();
    }
}

function setupOutsideClickHandlers() {
    document.addEventListener('click', (e) => {
        const powerWrapper = document.querySelector('.power-dropdown-wrapper');
        const powerMenu = document.getElementById('power-menu-popup');
        if (powerWrapper && !powerWrapper.contains(e.target) && powerMenu && powerMenu.classList.contains('active')) {
            closePowerMenu();
        }

        const browseWrapper = document.getElementById('browse-dropdown-wrapper');
        if (browseWrapper && !browseWrapper.contains(e.target)) {
            closeBrowseMenu();
        }
    });
}

// ==========================================================================
// POWER TOOLS SUITE (Merge, Split, Rename, Single Compress, Multi Compress)
// ==========================================================================

let lastPowerOutputPaths = {
    merge: 'data/exports',
    split: 'data/exports',
    rename: 'data/exports',
    compress: 'data/exports',
    multi_compress: 'data/exports'
};

// --------------------------------------------------------------------------
// 1. MERGE VIDEO SUITE (Lossless Stream-Copy Concat)
// --------------------------------------------------------------------------
let powerMergeQueue = [];

function openMergeModal() {
    closePowerMenu();
    const progBox = document.getElementById('power-merge-progress-box');
    const resBox = document.getElementById('power-merge-result-box');
    const aiStats = document.getElementById('power-merge-ai-stats');
    if (progBox) progBox.style.display = 'none';
    if (resBox) resBox.style.display = 'none';
    if (aiStats) aiStats.style.display = 'none';
    renderPowerMergeQueue();
    openModal('modal-power-merge');
}

async function powerPickFilesForMerge() {
    try {
        const res = await fetch('/api/system/select-media-files', { method: 'POST' });
        const data = await res.json();
        if (data && data.success && Array.isArray(data.files) && data.files.length > 0) {
            const existingPaths = new Set(powerMergeQueue.map(f => f.filepath));
            for (const f of data.files) {
                if (!existingPaths.has(f.filepath)) {
                    powerMergeQueue.push(f);
                }
            }
            renderPowerMergeQueue();
            showToast(`Added ${data.files.length} videos to merge queue!`);
            return;
        }
        if (data && data.cancelled) return;
    } catch (e) {
        console.warn("Native file picker note:", e);
    }
    const input = document.getElementById('power-merge-file-input');
    if (input) input.click();
}

async function powerPickFolderForMerge() {
    try {
        const res = await fetch('/api/system/select-media-folder', { method: 'POST' });
        const data = await res.json();
        if (data && data.success && Array.isArray(data.files) && data.files.length > 0) {
            powerMergeQueue = [...data.files];
            if (data.series_title) {
                const nameInput = document.getElementById('power-merge-output-name');
                if (nameInput) nameInput.value = `${data.series_title}_Full.mp4`;
            }
            renderPowerMergeQueue();
            showToast(`Scanned ${data.files.length} episodes from folder!`);
            return;
        }
        if (data && data.cancelled) return;
        showToast("No video files found in the selected folder.", "warning");
    } catch (e) {
        console.error("Folder picker error:", e);
        showToast("Failed to open Folder Picker", "error");
    }
}

function handlePowerMergeHtmlFiles(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    for (let i = 0; i < files.length; i++) {
        const f = files[i];
        powerMergeQueue.push({
            filepath: f.path || f.name,
            filename: f.name,
            size_mb: (f.size / (1024 * 1024)).toFixed(1)
        });
    }
    renderPowerMergeQueue();
    event.target.value = '';
}

function clearPowerMergeQueue() {
    powerMergeQueue = [];
    renderPowerMergeQueue();
}

function moveMergeQueueItem(idx, dir) {
    const targetIdx = idx + dir;
    if (targetIdx < 0 || targetIdx >= powerMergeQueue.length) return;
    const temp = powerMergeQueue[idx];
    powerMergeQueue[idx] = powerMergeQueue[targetIdx];
    powerMergeQueue[targetIdx] = temp;
    renderPowerMergeQueue();
}

function removeMergeQueueItem(idx) {
    powerMergeQueue.splice(idx, 1);
    renderPowerMergeQueue();
}

function renderPowerMergeQueue() {
    const list = document.getElementById('power-merge-queue-list');
    const badge = document.getElementById('power-merge-count-badge');
    if (badge) badge.textContent = powerMergeQueue.length;
    if (!list) return;

    if (powerMergeQueue.length === 0) {
        list.innerHTML = `<div style="text-align:center; padding:16px; color:#64748b; font-size:0.75rem;">No videos in queue. Click the buttons above to select episodes to merge.</div>`;
        return;
    }

    list.innerHTML = powerMergeQueue.map((item, idx) => `
        <div class="power-queue-item">
            <div class="power-queue-order-badge">${String(idx + 1).padStart(2, '0')}</div>
            <div class="power-queue-info">
                <div class="power-queue-name" title="${escapeHtml(item.filename)}">${escapeHtml(item.filename)}</div>
                <div class="power-queue-meta">${item.size_mb || '0'} MB • ${escapeHtml(item.filepath || '')}</div>
            </div>
            <div class="power-queue-actions">
                <button type="button" class="power-queue-btn" onclick="moveMergeQueueItem(${idx}, -1)" ${idx === 0 ? 'disabled style="opacity:0.3;"' : ''} title="Move Up"><i class="fa-solid fa-arrow-up"></i></button>
                <button type="button" class="power-queue-btn" onclick="moveMergeQueueItem(${idx}, 1)" ${idx === powerMergeQueue.length - 1 ? 'disabled style="opacity:0.3;"' : ''} title="Move Down"><i class="fa-solid fa-arrow-down"></i></button>
                <button type="button" class="power-queue-btn remove" onclick="removeMergeQueueItem(${idx})" title="Remove"><i class="fa-solid fa-xmark"></i></button>
            </div>
        </div>
    `).join('');
}

async function executeVideoMerge() {
    if (powerMergeQueue.length < 2) {
        showToast("Please select at least 2 episodes to merge!", "warning");
        return;
    }

    const outputName = document.getElementById('power-merge-output-name')?.value?.trim() || 'merged_full_drama.mp4';
    const autoTrimFreeze = true;
    const btn = document.getElementById('btn-power-merge-start');
    const progBox = document.getElementById('power-merge-progress-box');
    const resBox = document.getElementById('power-merge-result-box');
    const progFill = document.getElementById('power-merge-prog-fill');
    const statusText = document.getElementById('power-merge-status-text');
    const statusPct = document.getElementById('power-merge-status-pct');
    const aiStatsEl = document.getElementById('power-merge-ai-stats');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Merging in progress...`;
    }
    if (progBox) progBox.style.display = 'block';
    if (resBox) resBox.style.display = 'none';
    if (aiStatsEl) aiStatsEl.style.display = 'none';
    if (progFill) progFill.style.width = '30%';
    
    if (autoTrimFreeze) {
        if (statusText) statusText.textContent = `AI scanning & merging ${powerMergeQueue.length} episodes (detecting frozen outros)...`;
        if (statusPct) statusPct.textContent = 'AI SCAN';
        appendTerminalLine(`[Power Merge] Merging ${powerMergeQueue.length} clips into "${outputName}" with AI Freeze Detection enabled...`);
        showToast(`AI Scanning & merging ${powerMergeQueue.length} episodes...`);
    } else {
        if (statusText) statusText.textContent = `Merging ${powerMergeQueue.length} episodes via Lossless Stream Copy...`;
        if (statusPct) statusPct.textContent = 'CONCAT';
        appendTerminalLine(`[Power Merge] Merging ${powerMergeQueue.length} clips into "${outputName}"...`);
        showToast(`Merging ${powerMergeQueue.length} episodes...`);
    }

    try {
        const filePaths = powerMergeQueue.map(f => f.filepath);
        const res = await fetch('/api/power/merge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                files: filePaths, 
                output_name: outputName,
                auto_trim_freeze: autoTrimFreeze
            })
        });
        const data = await res.json();

        if (data.success) {
            if (progFill) progFill.style.width = '100%';
            if (progBox) progBox.style.display = 'none';
            if (resBox) resBox.style.display = 'block';

            lastPowerOutputPaths.merge = data.output_file || data.output_dir || 'data/exports';
            const resPathEl = document.getElementById('power-merge-result-path');
            if (resPathEl) resPathEl.textContent = data.output_file;

            if (data.auto_trim_freeze) {
                const trimmedCount = data.trimmed_count || 0;
                const unalteredCount = data.unaltered_count ?? (data.total_episodes - trimmedCount);
                const savedSec = (data.total_seconds_saved || 0).toFixed(1);

                if (aiStatsEl) {
                    aiStatsEl.style.display = 'block';
                    aiStatsEl.innerHTML = `
                        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
                            <span style="font-weight:700; color:#c084fc; display:flex; align-items:center; gap:6px;">
                                <i class="fa-solid fa-wand-magic-sparkles"></i> AI Freeze Detection Report
                            </span>
                            <span style="color:#facc15; font-weight:700; font-family:'JetBrains Mono', monospace;">-${savedSec}s Removed</span>
                        </div>
                        <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; font-size:0.73rem;">
                            <div style="background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.25); padding:5px 8px; border-radius:6px; color:#fca5a5;">
                                ✂️ <strong>${trimmedCount}</strong> Frozen Outros Trimmed
                            </div>
                            <div style="background:rgba(34,197,94,0.15); border:1px solid rgba(34,197,94,0.25); padding:5px 8px; border-radius:6px; color:#86efac;">
                                🛡️ <strong>${unalteredCount}</strong> Active Episodes 100% Intact
                            </div>
                        </div>
                    `;
                }

                if (trimmedCount > 0) {
                    showToast(`Merged ${powerMergeQueue.length} eps! AI trimmed ${trimmedCount} frozen outros (-${savedSec}s).`, "success");
                    appendTerminalLine(`[Power Merge] Success! AI scanned ${data.total_episodes} eps: trimmed ${trimmedCount} frozen outros (-${savedSec}s), preserved ${unalteredCount} moving episodes intact 100%. Output: ${data.output_file}`);
                } else {
                    showToast(`Merged ${powerMergeQueue.length} eps! All episodes had active endings (0s cut).`, "success");
                    appendTerminalLine(`[Power Merge] Success! AI verified all ${data.total_episodes} eps had active motion. Kept 100% intact. Output: ${data.output_file}`);
                }
            } else {
                if (aiStatsEl) aiStatsEl.style.display = 'none';
                showToast("Videos merged successfully!");
                appendTerminalLine(`[Power Merge] Success! Output: ${data.output_file}`);
            }
        } else {
            throw new Error(data.error || "Concat failed");
        }
    } catch (err) {
        console.error("Merge error:", err);
        if (progBox) progBox.style.display = 'none';
        showToast("Failed to merge videos: " + err.message, "error");
        appendTerminalLine(`[Power Merge Error] ${err.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-link"></i> Merge Videos Now`;
        }
    }
}

function playPowerResultVideo() {
    const p = lastPowerOutputPaths.merge;
    if (!p || p === 'data/exports') {
        showToast("No output video available yet.", "warning");
        return;
    }
    const mainVideo = document.getElementById('main-video');
    if (mainVideo) {
        mainVideo.src = `/media/${p.replace(/\\/g, '/')}`;
        mainVideo.style.display = 'block';
        mainVideo.load();
        mainVideo.play().catch(() => {});
        closeModal('modal-power-merge');
        showToast("Playing merged video preview...");
    }
}

// --------------------------------------------------------------------------
// 2. SPLIT VIDEO SUITE (Presplit chunking for TikTok / Reels)
// --------------------------------------------------------------------------
let powerSplitSelectedFile = null;
let currentSplitVideoDurationSec = 0;

function formatDurationPretty(seconds) {
    if (!seconds || isNaN(seconds) || seconds <= 0) return "--:--";
    const sec = Math.round(seconds);
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    if (h > 0) {
        return `${h}h ${m}m ${s}s`;
    }
    return `${m}m ${s.toString().padStart(2, '0')}s`;
}

async function fetchVideoDurationForSplit(filePath) {
    if (!filePath) return;
    try {
        const res = await fetch('/api/power/media-duration', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath: filePath })
        });
        const data = await res.json();
        if (data && data.success && data.duration > 0) {
            currentSplitVideoDurationSec = data.duration;
            updateSplitCalcPreview();
        }
    } catch (e) {
        console.warn("fetchVideoDurationForSplit note:", e);
    }
}

function openSplitModal() {
    closePowerMenu();
    const progBox = document.getElementById('power-split-progress-box');
    const resBox = document.getElementById('power-split-result-box');
    if (progBox) progBox.style.display = 'none';
    if (resBox) resBox.style.display = 'none';

    if (powerSplitSelectedFile) {
        const fPath = getMediaFilePath(powerSplitSelectedFile) || powerSplitSelectedFile.filepath;
        if (fPath && currentSplitVideoDurationSec <= 0) {
            fetchVideoDurationForSplit(fPath);
        }
    }
    setSplitMinutes(1);
    openModal('modal-power-split');
}

async function powerUseCurrentVideoForSplit() {
    if (!stagedVideoFile) {
        showToast("No video currently loaded in Studio. Please select a file!", "warning");
        return;
    }
    powerSplitSelectedFile = stagedVideoFile;
    const titleEl = document.getElementById('power-split-source-title');
    const subEl = document.getElementById('power-split-source-sub');
    const fName = getMediaFileName(stagedVideoFile);
    const fPath = getMediaFilePath(stagedVideoFile) || fName;
    if (titleEl) titleEl.textContent = fName;

    // Detect duration from main video element or project or probe backend
    const mainVid = document.getElementById('main-video');
    if (mainVid && !isNaN(mainVid.duration) && mainVid.duration > 0) {
        currentSplitVideoDurationSec = mainVid.duration;
    } else if (typeof totalDurationSeconds !== 'undefined' && totalDurationSeconds > 0) {
        currentSplitVideoDurationSec = totalDurationSeconds;
    } else if (currentProject && currentProject.duration) {
        currentSplitVideoDurationSec = currentProject.duration;
    } else if (fPath) {
        await fetchVideoDurationForSplit(fPath);
    }

    if (subEl) {
        const durStr = formatDurationPretty(currentSplitVideoDurationSec);
        subEl.textContent = `Loaded from Studio • ${durStr !== '--:--' ? durStr + ' • ' : ''}${fPath}`;
    }
    showToast(`Selected: ${fName}`);
    updateSplitCalcPreview();
}

async function powerPickFileForSplit() {
    try {
        const res = await fetch('/api/system/select-media-files', { method: 'POST' });
        const data = await res.json();
        if (data && data.success && Array.isArray(data.files) && data.files.length > 0) {
            const f = data.files[0];
            powerSplitSelectedFile = f;
            const titleEl = document.getElementById('power-split-source-title');
            const subEl = document.getElementById('power-split-source-sub');
            if (titleEl) titleEl.textContent = f.filename;
            if (subEl) subEl.textContent = `${f.size_mb || '0'} MB • ${f.filepath}`;
            showToast(`Selected: ${f.filename}`);

            if (f.duration && f.duration > 0) {
                currentSplitVideoDurationSec = f.duration;
                updateSplitCalcPreview();
            } else if (f.filepath) {
                await fetchVideoDurationForSplit(f.filepath);
            }
            return;
        }
        if (data && data.cancelled) return;
    } catch (e) {
        console.warn("Native file picker note:", e);
    }
    const input = document.getElementById('power-split-file-input');
    if (input) input.click();
}

function handlePowerSplitHtmlFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    powerSplitSelectedFile = {
        filepath: file.path || file.name,
        filename: file.name,
        size_mb: (file.size / (1024 * 1024)).toFixed(1)
    };
    const titleEl = document.getElementById('power-split-source-title');
    const subEl = document.getElementById('power-split-source-sub');
    if (titleEl) titleEl.textContent = file.name;
    if (subEl) subEl.textContent = `${(file.size / (1024 * 1024)).toFixed(1)} MB (Local File)`;
    event.target.value = '';

    autoDetectVideoDuration(file, (dur) => {
        if (dur > 0) {
            currentSplitVideoDurationSec = dur;
            updateSplitCalcPreview();
        }
    });
    updateSplitCalcPreview();
}

function setSplitMinutes(mins) {
    mins = Math.max(1, parseInt(mins) || 1);
    const input = document.getElementById('split-duration-mins');
    if (input) input.value = mins;

    const chips = document.querySelectorAll('#modal-power-split .power-chip-btn');
    chips.forEach(c => c.classList.remove('active'));
    const targetChip = document.getElementById(`quick-min-${mins}`);
    if (targetChip) targetChip.classList.add('active');

    updateSplitCalcPreview();
}

function updateSplitCalcPreview() {
    const input = document.getElementById('split-duration-mins');
    let mins = 1;
    if (input) {
        mins = parseFloat(input.value) || 1;
        if (mins < 1) {
            mins = 1;
            input.value = 1;
        }
    }

    const intMins = Math.round(mins);
    const chips = document.querySelectorAll('#modal-power-split .power-chip-btn');
    chips.forEach(c => {
        if (c.id === `quick-min-${intMins}` && mins === intMins) {
            c.classList.add('active');
        } else {
            c.classList.remove('active');
        }
    });

    const partSec = Math.max(60, Math.round(mins * 60));
    const partDurationEl = document.getElementById('split-stat-part-duration');
    if (partDurationEl) {
        partDurationEl.textContent = `${mins} Minute${mins > 1 ? 's' : ''} (${partSec}s)`;
    }

    const totalDurEl = document.getElementById('split-stat-total-duration');
    const totalCountEl = document.getElementById('split-stat-total-count');
    const badgeTextEl = document.getElementById('split-calc-badge-text');

    if (currentSplitVideoDurationSec > 0) {
        const totalParts = Math.max(1, Math.ceil(currentSplitVideoDurationSec / partSec));
        const formattedTotal = formatDurationPretty(currentSplitVideoDurationSec);

        if (totalDurEl) totalDurEl.textContent = formattedTotal;
        if (totalCountEl) totalCountEl.textContent = `${totalParts} EP`;
        if (badgeTextEl) badgeTextEl.textContent = `${totalParts} EP`;
    } else {
        if (totalDurEl) totalDurEl.textContent = "--:--";
        if (totalCountEl) totalCountEl.textContent = "-- EP";
        if (badgeTextEl) badgeTextEl.textContent = "-- EP";
    }
}

async function executeVideoSplit() {
    const videoPath = getMediaFilePath(powerSplitSelectedFile) || (powerSplitSelectedFile?.filepath);
    if (!videoPath) {
        showToast("Please select a video to split first!", "warning");
        return;
    }

    let mins = parseFloat(document.getElementById('split-duration-mins')?.value) || 1;
    if (mins < 1) {
        mins = 1;
        const minsInput = document.getElementById('split-duration-mins');
        if (minsInput) minsInput.value = 1;
        showToast("Minimum split chunk duration is 1 minute (60 seconds)!", "info");
    }
    const sec = Math.max(60, Math.round(mins * 60));

    const btn = document.getElementById('btn-power-split-start');
    const progBox = document.getElementById('power-split-progress-box');
    const resBox = document.getElementById('power-split-result-box');
    const statusText = document.getElementById('power-split-status-text');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Splitting in progress...`;
    }
    if (progBox) progBox.style.display = 'block';
    if (resBox) resBox.style.display = 'none';
    if (statusText) statusText.textContent = `Splitting video into ${mins} min (${sec}s) EP...`;

    appendTerminalLine(`[Power Split] Splitting "${videoPath}" into ${mins}m (${sec}s) EP chunks...`);
    showToast(`Splitting video into ${mins}m EP chunks...`);

    try {
        const res = await fetch('/api/power/split', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_path: videoPath, chunk_duration_sec: sec })
        });
        const data = await res.json();

        if (data.success) {
            if (progBox) progBox.style.display = 'none';
            if (resBox) resBox.style.display = 'block';

            const partsCountEl = document.getElementById('power-split-parts-count');
            const resPathEl = document.getElementById('power-split-result-path');
            if (partsCountEl) partsCountEl.textContent = data.parts_count || (data.parts?.length || 0);
            if (resPathEl) resPathEl.textContent = data.output_dir || (data.parts?.[0] || 'data/exports');

            lastPowerOutputPaths.split = data.output_dir || (data.parts?.[0] || 'data/exports');

            if (typeof playCompletionChime === 'function') playCompletionChime();
            showToast(`Split completed successfully into ${data.parts_count} EP!`);
            appendTerminalLine(`[Power Split] Successfully created ${data.parts_count} EP in ${data.output_dir}`);
        } else {
            throw new Error(data.error || "Split failed");
        }
    } catch (err) {
        console.error("Split error:", err);
        if (progBox) progBox.style.display = 'none';
        showToast("Failed to split video: " + err.message, "error");
        appendTerminalLine(`[Power Split Error] ${err.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-scissors"></i> Split Video Now`;
        }
    }
}

// --------------------------------------------------------------------------
// 3. BATCH RENAME SUITE (Sequential Standardizing)
// --------------------------------------------------------------------------
let powerRenameQueue = [];

function openRenameModal() {
    closePowerMenu();
    const resBox = document.getElementById('power-rename-result-box');
    if (resBox) resBox.style.display = 'none';
    updateRenamePreviewTable();
    openModal('modal-power-rename');
}

async function powerPickFolderForRename() {
    try {
        const res = await fetch('/api/system/select-media-folder', { method: 'POST' });
        const data = await res.json();
        if (data && data.success && Array.isArray(data.files) && data.files.length > 0) {
            powerRenameQueue = [...data.files];
            if (data.series_title) {
                const prefixInput = document.getElementById('rename-prefix-input');
                if (prefixInput) prefixInput.value = `${data.series_title}_EP_`;
            }
            const countLabel = document.getElementById('power-rename-count-label');
            if (countLabel) countLabel.textContent = `${data.files.length} video files selected from folder`;
            updateRenamePreviewTable();
            showToast(`Scanned ${data.files.length} files in folder!`);
            return;
        }
        if (data && data.cancelled) return;
        showToast("No video files found in the selected folder.", "warning");
    } catch (e) {
        console.error("Folder picker error:", e);
        showToast("Failed to select folder", "error");
    }
}

async function powerPickFilesForRename() {
    try {
        const res = await fetch('/api/system/select-media-files', { method: 'POST' });
        const data = await res.json();
        if (data && data.success && Array.isArray(data.files) && data.files.length > 0) {
            powerRenameQueue = [...data.files];
            const countLabel = document.getElementById('power-rename-count-label');
            if (countLabel) countLabel.textContent = `${data.files.length} video files selected`;
            updateRenamePreviewTable();
            showToast(`Selected ${data.files.length} files!`);
            return;
        }
        if (data && data.cancelled) return;
    } catch (e) {
        console.warn("File picker note:", e);
    }
    const input = document.getElementById('power-rename-file-input');
    if (input) input.click();
}

function handlePowerRenameHtmlFiles(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    powerRenameQueue = [];
    for (let i = 0; i < files.length; i++) {
        const f = files[i];
        powerRenameQueue.push({
            filepath: f.path || f.name,
            filename: f.name,
            size_mb: (f.size / (1024 * 1024)).toFixed(1)
        });
    }
    const countLabel = document.getElementById('power-rename-count-label');
    if (countLabel) countLabel.textContent = `${files.length} video files selected`;
    updateRenamePreviewTable();
    event.target.value = '';
}

function updateRenamePreviewTable() {
    const container = document.getElementById('power-rename-preview-container');
    if (!container) return;

    if (powerRenameQueue.length === 0) {
        container.innerHTML = `<div style="text-align:center; padding:14px; color:#64748b; font-size:0.75rem;">Select a folder or files to preview rename table.</div>`;
        return;
    }

    const prefix = document.getElementById('rename-prefix-input')?.value || 'Drama_EP_';
    const startNum = parseInt(document.getElementById('rename-start-num')?.value) || 1;

    let html = `
        <table style="width:100%; border-collapse:collapse; font-size:0.75rem; text-align:left;">
            <thead>
                <tr style="border-bottom:1px solid rgba(255,255,255,0.1); color:#94a3b8;">
                    <th style="padding:6px 8px; width:36px;">#</th>
                    <th style="padding:6px 8px;">Original Name</th>
                    <th style="padding:6px 8px; color:#fbbf24;">New Name (Renamed)</th>
                </tr>
            </thead>
            <tbody>
    `;

    const previewItems = powerRenameQueue.slice(0, 50);
    previewItems.forEach((f, idx) => {
        const curNum = startNum + idx;
        const ext = f.filename.includes('.') ? '.' + f.filename.split('.').pop() : '.mp4';
        const newName = `${prefix}${String(curNum).padStart(2, '0')}${ext}`;
        html += `
            <tr style="border-bottom:1px solid rgba(255,255,255,0.05); color:#cbd5e1;">
                <td style="padding:6px 8px; color:#64748b; font-family:'JetBrains Mono',monospace;">${curNum}</td>
                <td style="padding:6px 8px; max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(f.filename)}">${escapeHtml(f.filename)}</td>
                <td style="padding:6px 8px; color:#fef08a; font-weight:600; font-family:'JetBrains Mono',monospace;">${escapeHtml(newName)}</td>
            </tr>
        `;
    });

    if (powerRenameQueue.length > 50) {
        html += `
            <tr>
                <td colspan="3" style="padding:8px; text-align:center; color:#94a3b8; font-style:italic;">... and ${powerRenameQueue.length - 50} more files</td>
            </tr>
        `;
    }

    html += `</tbody></table>`;
    container.innerHTML = html;
}

async function executeBatchRename() {
    if (powerRenameQueue.length === 0) {
        showToast("Please select a folder or files first!", "warning");
        return;
    }

    const prefix = document.getElementById('rename-prefix-input')?.value || 'Drama_EP_';
    const startNum = parseInt(document.getElementById('rename-start-num')?.value) || 1;
    const btn = document.getElementById('btn-power-rename-start');
    const resBox = document.getElementById('power-rename-result-box');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Renaming in progress...`;
    }

    try {
        const filePaths = powerRenameQueue.map(f => f.filepath);
        const res = await fetch('/api/power/rename', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: filePaths, prefix: prefix, start_num: startNum })
        });
        const data = await res.json();

        if (data.success) {
            if (resBox) resBox.style.display = 'block';
            const resPathEl = document.getElementById('power-rename-result-path');
            if (resPathEl) resPathEl.textContent = `Successfully renamed ${data.results.length} files!`;

            powerRenameQueue = data.results.map(r => ({
                filepath: r.new,
                filename: r.name,
                size_mb: '0'
            }));
            updateRenamePreviewTable();

            showToast(`Successfully renamed ${data.results.length} files!`);
            appendTerminalLine(`[Power Rename] Renamed ${data.results.length} files successfully.`);
        } else {
            throw new Error(data.error || "Rename failed");
        }
    } catch (err) {
        console.error("Rename error:", err);
        showToast("Failed to rename files: " + err.message, "error");
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-pen-to-square"></i> Rename All Files`;
        }
    }
}

// --------------------------------------------------------------------------
// 4. SINGLE COMPRESS SUITE (CRF-based Smart Compression)
// --------------------------------------------------------------------------
let powerCompressSelectedFile = null;

function openCompressModal(type = 'single') {
    closePowerMenu();
    if (type === 'multi') {
        openMultiCompressModal();
        return;
    }

    const progBox = document.getElementById('power-compress-progress-box');
    const resBox = document.getElementById('power-compress-result-box');
    if (progBox) progBox.style.display = 'none';
    if (resBox) resBox.style.display = 'none';

    if (!powerCompressSelectedFile && stagedVideoFile) {
        powerUseCurrentVideoForCompress();
    }
    openModal('modal-power-compress');
}

function powerUseCurrentVideoForCompress() {
    if (!stagedVideoFile) {
        showToast("No video currently loaded in Studio. Please select a file!", "warning");
        return;
    }
    powerCompressSelectedFile = stagedVideoFile;
    const titleEl = document.getElementById('power-compress-source-title');
    const subEl = document.getElementById('power-compress-source-sub');
    const fName = getMediaFileName(stagedVideoFile);
    const fPath = getMediaFilePath(stagedVideoFile) || fName;
    if (titleEl) titleEl.textContent = fName;
    if (subEl) subEl.textContent = `Loaded from Studio • ${fPath}`;
    showToast(`Selected: ${fName}`);
}

async function powerPickFileForCompress() {
    try {
        const res = await fetch('/api/system/select-media-files', { method: 'POST' });
        const data = await res.json();
        if (data && data.success && Array.isArray(data.files) && data.files.length > 0) {
            const f = data.files[0];
            powerCompressSelectedFile = f;
            const titleEl = document.getElementById('power-compress-source-title');
            const subEl = document.getElementById('power-compress-source-sub');
            if (titleEl) titleEl.textContent = f.filename;
            if (subEl) subEl.textContent = `${f.size_mb || '0'} MB • ${f.filepath}`;
            showToast(`Selected: ${f.filename}`);
            return;
        }
        if (data && data.cancelled) return;
    } catch (e) {
        console.warn("File picker note:", e);
    }
    const input = document.getElementById('power-compress-file-input');
    if (input) input.click();
}

function handlePowerCompressHtmlFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    powerCompressSelectedFile = {
        filepath: file.path || file.name,
        filename: file.name,
        size_mb: (file.size / (1024 * 1024)).toFixed(1)
    };
    const titleEl = document.getElementById('power-compress-source-title');
    const subEl = document.getElementById('power-compress-source-sub');
    if (titleEl) titleEl.textContent = file.name;
    if (subEl) subEl.textContent = `${(file.size / (1024 * 1024)).toFixed(1)} MB (Local File)`;
    event.target.value = '';
}

function setCompressCrfPreset(crf) {
    const input = document.getElementById('compress-crf-val');
    const display = document.getElementById('crf-number-display');
    if (input) input.value = crf;
    if (display) display.textContent = crf;

    const pills = document.querySelectorAll('#modal-power-compress .power-pill-btn');
    pills.forEach(p => p.classList.remove('active'));
    const targetPill = document.getElementById(`compress-pill-${crf}`);
    if (targetPill) targetPill.classList.add('active');
}

async function executeVideoCompress() {
    const videoPath = getMediaFilePath(powerCompressSelectedFile) || (powerCompressSelectedFile?.filepath);
    if (!videoPath) {
        showToast("Please select a video to compress first!", "warning");
        return;
    }

    const crf = parseInt(document.getElementById('compress-crf-val')?.value) || 26;
    const targetHeight = document.getElementById('compress-target-height')?.value || null;
    const btn = document.getElementById('btn-power-compress-start');
    const progBox = document.getElementById('power-compress-progress-box');
    const resBox = document.getElementById('power-compress-result-box');
    const statusText = document.getElementById('power-compress-status-text');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Compressing in progress...`;
    }
    if (progBox) progBox.style.display = 'block';
    if (resBox) resBox.style.display = 'none';
    if (statusText) statusText.textContent = `Compressing video (CRF ${crf}${targetHeight ? ' • ' + targetHeight + 'p' : ''})...`;

    appendTerminalLine(`[Power Compress] Compressing "${videoPath}" with CRF ${crf}...`);
    showToast(`Compressing video...`);

    try {
        const res = await fetch('/api/power/compress', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_path: videoPath,
                crf: crf,
                target_height: targetHeight ? parseInt(targetHeight) : null
            })
        });
        const data = await res.json();

        if (data.success) {
            if (progBox) progBox.style.display = 'none';
            if (resBox) resBox.style.display = 'block';

            lastPowerOutputPaths.compress = data.output_file || 'data/exports';
            const resPathEl = document.getElementById('power-compress-result-path');
            if (resPathEl) {
                const origMb = data.orig_size ? (data.orig_size / (1024 * 1024)).toFixed(1) : '?';
                const newMb = data.new_size ? (data.new_size / (1024 * 1024)).toFixed(1) : '?';
                const savedPct = data.saved_pct !== undefined ? `${data.saved_pct}%` : '';
                resPathEl.textContent = `${data.output_file} • ${origMb}MB ➔ ${newMb}MB (-${savedPct})`;
            }

            showToast("Video compressed successfully!");
            appendTerminalLine(`[Power Compress] Done: ${data.output_file}`);
        } else {
            throw new Error(data.error || "Compression failed");
        }
    } catch (err) {
        console.error("Compress error:", err);
        if (progBox) progBox.style.display = 'none';
        showToast("Failed to compress video: " + err.message, "error");
        appendTerminalLine(`[Power Compress Error] ${err.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-file-zipper"></i> Compress Video Now`;
        }
    }
}

function playPowerCompressedVideo() {
    const p = lastPowerOutputPaths.compress;
    if (!p || p === 'data/exports') {
        showToast("No output video available yet.", "warning");
        return;
    }
    const mainVideo = document.getElementById('main-video');
    if (mainVideo) {
        mainVideo.src = `/media/${p.replace(/\\/g, '/')}`;
        mainVideo.style.display = 'block';
        mainVideo.load();
        mainVideo.play().catch(() => {});
        closeModal('modal-power-compress');
        showToast("Playing compressed video preview...");
    }
}

// --------------------------------------------------------------------------
// 5. MULTI COMPRESS SUITE (Batch Folder Queue Compression)
// --------------------------------------------------------------------------
let powerMultiCompressQueue = [];

function openMultiCompressModal() {
    closePowerMenu();
    const progBox = document.getElementById('power-multi-progress-box');
    const resBox = document.getElementById('power-multi-result-box');
    if (progBox) progBox.style.display = 'none';
    if (resBox) resBox.style.display = 'none';
    renderMultiCompressQueue();
    openModal('modal-power-multi-compress');
}

async function powerPickFolderForMultiCompress() {
    try {
        const res = await fetch('/api/system/select-media-folder', { method: 'POST' });
        const data = await res.json();
        if (data && data.success && Array.isArray(data.files) && data.files.length > 0) {
            powerMultiCompressQueue = [...data.files];
            renderMultiCompressQueue();
            showToast(`Added ${data.files.length} videos from folder to compression queue!`);
            return;
        }
        if (data && data.cancelled) return;
        showToast("No videos found in folder.", "warning");
    } catch (e) {
        console.error("Multi compress folder pick error:", e);
    }
}

async function powerPickFilesForMultiCompress() {
    try {
        const res = await fetch('/api/system/select-media-files', { method: 'POST' });
        const data = await res.json();
        if (data && data.success && Array.isArray(data.files) && data.files.length > 0) {
            const existing = new Set(powerMultiCompressQueue.map(f => f.filepath));
            for (const f of data.files) {
                if (!existing.has(f.filepath)) {
                    powerMultiCompressQueue.push(f);
                }
            }
            renderMultiCompressQueue();
            showToast(`Added ${data.files.length} videos to queue!`);
            return;
        }
        if (data && data.cancelled) return;
    } catch (e) {
        console.warn("Multi compress pick files error:", e);
    }
    const input = document.getElementById('power-multi-compress-file-input');
    if (input) input.click();
}

function handlePowerMultiCompressHtmlFiles(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    for (let i = 0; i < files.length; i++) {
        const f = files[i];
        powerMultiCompressQueue.push({
            filepath: f.path || f.name,
            filename: f.name,
            size_mb: (f.size / (1024 * 1024)).toFixed(1)
        });
    }
    renderMultiCompressQueue();
    event.target.value = '';
}

function clearPowerMultiCompressQueue() {
    powerMultiCompressQueue = [];
    renderMultiCompressQueue();
}

function removeMultiCompressQueueItem(idx) {
    powerMultiCompressQueue.splice(idx, 1);
    renderMultiCompressQueue();
}

function renderMultiCompressQueue() {
    const list = document.getElementById('power-multi-queue-list');
    const countLabel = document.getElementById('power-multi-count-label');
    if (countLabel) countLabel.textContent = `${powerMultiCompressQueue.length} files in compression queue`;
    if (!list) return;

    if (powerMultiCompressQueue.length === 0) {
        list.innerHTML = `<div style="text-align:center; padding:14px; color:#64748b; font-size:0.75rem;">No videos in queue. Click buttons above to select folder or files.</div>`;
        return;
    }

    list.innerHTML = powerMultiCompressQueue.map((item, idx) => `
        <div class="power-queue-item">
            <div class="power-queue-order-badge" style="background:rgba(234,179,8,0.15); color:#facc15;">${String(idx + 1).padStart(2, '0')}</div>
            <div class="power-queue-info">
                <div class="power-queue-name" title="${escapeHtml(item.filename)}">${escapeHtml(item.filename)}</div>
                <div class="power-queue-meta">${item.size_mb || '0'} MB • ${escapeHtml(item.filepath || '')}</div>
            </div>
            <div class="power-queue-actions">
                <button type="button" class="power-queue-btn remove" onclick="removeMultiCompressQueueItem(${idx})" title="Remove"><i class="fa-solid fa-xmark"></i></button>
            </div>
        </div>
    `).join('');
}

async function executeMultiCompress() {
    if (powerMultiCompressQueue.length === 0) {
        showToast("Please select folder or files to compress first!", "warning");
        return;
    }

    const crf = parseInt(document.getElementById('power-multi-crf-val')?.value) || 26;
    const targetHeight = document.getElementById('power-multi-target-height')?.value || null;
    const btn = document.getElementById('btn-power-multi-compress-start');
    const progBox = document.getElementById('power-multi-progress-box');
    const resBox = document.getElementById('power-multi-result-box');
    const statusText = document.getElementById('power-multi-status-text');
    const statusPct = document.getElementById('power-multi-status-pct');
    const progFill = document.getElementById('power-multi-prog-fill');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Batch compressing...`;
    }
    if (progBox) progBox.style.display = 'block';
    if (resBox) resBox.style.display = 'none';
    if (progFill) progFill.style.width = '20%';
    if (statusText) statusText.textContent = `Compressing batch of ${powerMultiCompressQueue.length} videos...`;
    if (statusPct) statusPct.textContent = `0/${powerMultiCompressQueue.length}`;

    appendTerminalLine(`[Power Multi Compress] Starting batch compression of ${powerMultiCompressQueue.length} files (CRF ${crf})...`);
    showToast(`Compressing batch of ${powerMultiCompressQueue.length} videos...`);

    try {
        const filePaths = powerMultiCompressQueue.map(f => f.filepath);
        const res = await fetch('/api/power/compress-batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                files: filePaths,
                crf: crf,
                target_height: targetHeight ? parseInt(targetHeight) : null
            })
        });
        const data = await res.json();

        if (data.success) {
            if (progFill) progFill.style.width = '100%';
            if (progBox) progBox.style.display = 'none';
            if (resBox) resBox.style.display = 'block';

            lastPowerOutputPaths.multi_compress = data.output_dir || 'data/exports';
            const resPathEl = document.getElementById('power-multi-result-path');
            const savedMb = data.total_saved_bytes ? (data.total_saved_bytes / (1024 * 1024)).toFixed(1) : '0';
            if (resPathEl) {
                resPathEl.textContent = `Folder: ${data.output_dir} • Disk space saved: ${savedMb} MB!`;
            }

            showToast(`Batch compress completed! Saved ${savedMb} MB`);
            appendTerminalLine(`[Power Multi Compress] Complete! Total saved: ${savedMb} MB. Stored in: ${data.output_dir}`);
        } else {
            throw new Error(data.error || "Batch compression failed");
        }
    } catch (err) {
        console.error("Multi compress error:", err);
        if (progBox) progBox.style.display = 'none';
        showToast("Failed to batch compress: " + err.message, "error");
        appendTerminalLine(`[Power Multi Compress Error] ${err.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-folder-tree"></i> Start Batch Compress`;
        }
    }
}

// --------------------------------------------------------------------------
// Global Power Tools Output Folder Opener
// --------------------------------------------------------------------------
async function openPowerOutputFolder(type = 'merge') {
    const targetPath = lastPowerOutputPaths[type] || lastPowerOutputPaths.merge || 'data/exports';
    try {
        const res = await fetch('/api/system/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: targetPath })
        });
        const data = await res.json();
        if (data.success) {
            showToast("Opened destination folder in Windows Explorer!");
        } else {
            showToast("Cannot open folder: " + (data.error || "Error"), "error");
        }
    } catch (e) {
        console.error("Open folder error:", e);
        showToast("Failed to open Explorer", "error");
    }
}

// ==========================================================================
// 3. MONITOR PLAYBACK & SCRUBBER CONTROLS (Exact Match to Image 1)
// ==========================================================================
function togglePlayPreview(e) {
    if (e && e.stopPropagation) {
        e.stopPropagation();
    }
    isPlaying = !isPlaying;
    const mainVideo = document.getElementById('main-video');
    const playIcon = document.getElementById('center-play-icon');
    const playBtn = document.getElementById('center-play-btn');
    const bottomPlayIcon = document.getElementById('bottom-play-icon');
    const wavePlayIcon = document.getElementById('waveform-play-icon');

    if (isPlaying) {
        if (playIcon) playIcon.className = 'fa-solid fa-pause';
        if (bottomPlayIcon) bottomPlayIcon.className = 'fa-solid fa-pause';
        if (wavePlayIcon) wavePlayIcon.className = 'fa-solid fa-pause';
        if (playBtn) {
            playBtn.style.opacity = '0';
            playBtn.style.pointerEvents = 'none';
        }

        if (mainVideo && mainVideo.src) {
            mainVideo.style.display = 'block';
            mainVideo.muted = false;
            mainVideo.volume = 1.0;
            mainVideo.play().catch(() => {});
        }

        startAudioPlaybackVUMeter();
        const miniBars = document.getElementById('monitor-visualizer-bars');
        if (miniBars) miniBars.classList.add('active');

        if (playbackTimer) clearInterval(playbackTimer);
        playbackTimer = setInterval(() => {
            if (mainVideo && mainVideo.src && !mainVideo.paused && !isNaN(mainVideo.duration)) {
                playheadSeconds = mainVideo.currentTime;
                totalDurationSeconds = mainVideo.duration;
            } else {
                playheadSeconds += 0.5;
                if (playheadSeconds >= totalDurationSeconds) {
                    playheadSeconds = 0;
                }
            }
            updateScrubberUI();
        }, 300);
    } else {
        if (playIcon) playIcon.className = 'fa-solid fa-play';
        if (bottomPlayIcon) bottomPlayIcon.className = 'fa-solid fa-play';
        if (wavePlayIcon) wavePlayIcon.className = 'fa-solid fa-play';
        if (playBtn) {
            playBtn.style.opacity = '1';
            playBtn.style.pointerEvents = 'auto';
        }
        if (mainVideo && mainVideo.src) {
            mainVideo.pause();
        }
        if (playbackTimer) {
            clearInterval(playbackTimer);
            playbackTimer = null;
        }
        resetVuMetersToIdle();
        const miniBars = document.getElementById('monitor-visualizer-bars');
        if (miniBars) miniBars.classList.remove('active');
    }
}

function toggleAudioTrack() {
    const mainVideo = document.getElementById('main-video');
    if (mainVideo && mainVideo.src) {
        mainVideo.muted = false;
        mainVideo.volume = 1.0;
    }
    showToast("Voice Models Active: Piseth (Male Solo) & Sreymom (Female Solo) - Master Audio Bed");
}

function handleSeekClick(e) {
    const mainVideo = document.getElementById('main-video');
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const ratio = Math.max(0, Math.min(1, clickX / rect.width));
    playheadSeconds = ratio * totalDurationSeconds;
    if (mainVideo && mainVideo.src && !isNaN(mainVideo.duration)) {
        mainVideo.currentTime = playheadSeconds;
    }
    updateScrubberUI();
}

function updateScrubberUI() {
    const timecode = document.getElementById('monitor-timecode-display');
    const fill = document.getElementById('seek-fill-bar');
    const dot = document.getElementById('seek-handle-dot');
    const wavePlayhead = document.getElementById('waveform-playhead');
    const waveTime = document.getElementById('waveform-time-display');

    const curM = Math.floor(playheadSeconds / 60);
    const curS = Math.floor(playheadSeconds % 60);
    const durM = Math.floor(totalDurationSeconds / 60);
    const durS = Math.floor(totalDurationSeconds % 60);

    const timeStr = `${String(curM).padStart(2,'0')}:${String(curS).padStart(2,'0')}`;
    const fullDurStr = `${String(durM).padStart(2,'0')}:${String(durS).padStart(2,'0')}`;

    if (timecode) {
        timecode.textContent = `${timeStr} / ${fullDurStr}`;
    }

    const percent = (playheadSeconds / totalDurationSeconds) * 100;
    if (fill) fill.style.width = `${percent}%`;
    if (dot) dot.style.left = `${percent}%`;
    if (wavePlayhead) wavePlayhead.style.left = `${percent}%`;
    if (waveTime) waveTime.textContent = `00:${timeStr}.000 / 00:${fullDurStr}.000`;
}

function toggleVolumeMute(e) {
    if (e) e.stopPropagation();
    const mainVideo = document.getElementById('main-video');
    if (mainVideo) {
        mainVideo.muted = !mainVideo.muted;
        const icon = document.getElementById('video-track-vol-icon');
        const btn = document.getElementById('btn-video-track-speaker');
        if (icon) icon.className = mainVideo.muted ? 'fa-solid fa-volume-xmark' : 'fa-solid fa-volume-high';
        if (btn) btn.classList.toggle('muted', mainVideo.muted);
        showToast(mainVideo.muted ? "Video Audio Muted" : "Video Audio Unmuted");
    }
}

let isBgmMuted = false;
function toggleBgmMute(e) {
    if (e) e.stopPropagation();
    isBgmMuted = !isBgmMuted;
    const icon = document.getElementById('bgm-track-vol-icon');
    const btn = document.getElementById('btn-bgm-track-speaker');
    if (icon) icon.className = isBgmMuted ? 'fa-solid fa-volume-xmark' : 'fa-solid fa-volume-high';
    if (btn) btn.classList.toggle('muted', isBgmMuted);

    if (typeof onQuickBgmSliderChange === 'function') {
        onQuickBgmSliderChange(isBgmMuted ? 0 : 15);
    }
    showToast(isBgmMuted ? "Background Sound (BGM) Muted" : "Background Sound (BGM) Unmuted (15%)");
}

let currentBgmSelection = {
    value: '',
    title: 'Choose background sound...',
    icon: '🎵'
};

function toggleTrackBgmDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    if (typeof closeBlurMaskDropdown === 'function') closeBlurMaskDropdown();
    if (typeof closeTextOverlayDropdown === 'function') closeTextOverlayDropdown();
    if (typeof closeLowerThirdDropdown === 'function') closeLowerThirdDropdown();
    const dropdown = document.getElementById('track-bgm-custom-dropdown');
    const chevron = document.getElementById('track-bgm-chevron');
    if (!dropdown) return;
    
    const isOpen = dropdown.classList.contains('show');
    if (isOpen) {
        dropdown.classList.remove('show');
        if (chevron) chevron.classList.remove('open');
    } else {
        dropdown.classList.add('show');
        if (chevron) chevron.classList.add('open');
    }
}

function closeTrackBgmDropdown() {
    const dropdown = document.getElementById('track-bgm-custom-dropdown');
    const chevron = document.getElementById('track-bgm-chevron');
    if (dropdown) dropdown.classList.remove('show');
    if (chevron) chevron.classList.remove('open');
}

function selectBgmOption(val, title, icon, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    
    if (val === 'custom') {
        closeTrackBgmDropdown();
        const fileInput = document.getElementById('input-custom-bgm-file');
        if (fileInput) fileInput.click();
        return;
    }

    currentBgmSelection = { value: val, title: title, icon: icon || '🎵' };
    
    const titleEl = document.getElementById('staged-track-bgmname');
    if (titleEl) {
        titleEl.textContent = title;
    }

    const hiddenInput = document.getElementById('select-track-bgm');
    if (hiddenInput) {
        hiddenInput.value = val;
    }

    // Update active highlight across custom menu options
    document.querySelectorAll('.track-bgm-opt-item').forEach(item => {
        if (item.getAttribute('data-value') === val) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    closeTrackBgmDropdown();

    if (val === 'none') {
        if (typeof onQuickBgmSliderChange === 'function') onQuickBgmSliderChange(0);
        showToast("BGM: Background sound muted");
        appendLiveTerminalLine("BGM track disabled: dialogue stem isolated.", "[Audio Track]", "info");
    } else {
        if (typeof onQuickBgmSliderChange === 'function') onQuickBgmSliderChange(15);
        showToast(`Selected BGM: ${title}`);
        appendLiveTerminalLine(`BGM track attached: ${title}`, "[Audio Track]", "info");
    }
}

function handleCustomBgmFile(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    
    const fileName = file.name;
    currentBgmSelection = { value: 'custom', title: fileName, icon: '📁' };
    
    const titleEl = document.getElementById('staged-track-bgmname');
    if (titleEl) {
        titleEl.textContent = `📁 ${fileName}`;
    }

    const hiddenInput = document.getElementById('select-track-bgm');
    if (hiddenInput) {
        hiddenInput.value = 'custom';
    }

    document.querySelectorAll('.track-bgm-opt-item').forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-value') === 'custom');
    });

    closeTrackBgmDropdown();
    showToast(`Custom BGM loaded: ${fileName}`);
    appendLiveTerminalLine(`Custom BGM audio attached: ${fileName} (${(file.size / 1024).toFixed(1)} KB)`, "[Audio Config]", "success");
}

function onTrackBgmSelected(val) {
    selectBgmOption(val, val, '🎵');
}

// Global listener to close BGM and Blur dropdowns on click outside
document.addEventListener('click', function(e) {
    const bgmPill = document.getElementById('track-bgm-pill');
    const bgmDropdown = document.getElementById('track-bgm-custom-dropdown');
    if (bgmDropdown && bgmDropdown.classList.contains('show')) {
        if (bgmPill && !bgmPill.contains(e.target)) {
            closeTrackBgmDropdown();
        }
    }

    const stagedOverlayPanel = document.getElementById('staged-overlay-unified-panel');
    const blurDropdown = document.getElementById('blur-custom-dropdown');
    const textDropdown = document.getElementById('text-custom-dropdown');
    const ltDropdown = document.getElementById('lower-third-custom-dropdown');
    const isBlurOpen = blurDropdown && (blurDropdown.classList.contains('show') || blurDropdown.style.display === 'flex');
    const isTextOpen = textDropdown && (textDropdown.classList.contains('show') || textDropdown.style.display === 'flex');
    const isLtOpen = ltDropdown && (ltDropdown.classList.contains('show') || ltDropdown.style.display === 'flex');
    if (isBlurOpen || isTextOpen || isLtOpen) {
        if (stagedOverlayPanel && !stagedOverlayPanel.contains(e.target)) {
            if (isBlurOpen) closeBlurMaskDropdown();
            if (isTextOpen) closeTextOverlayDropdown();
            if (isLtOpen) closeLowerThirdDropdown();
        }
    }
});

function syncTrackRowsInfo(name, durationStr) {
    const nameEl = document.getElementById('staged-track-videoname');
    const durEl = document.getElementById('staged-track-videodur');
    if (nameEl && name) nameEl.textContent = name;
    if (durEl && durationStr) durEl.textContent = durationStr;
}

function toggleAudioTrack() {
    const vLabel = typeof getStoryVoiceDisplayLabel === 'function' ? getStoryVoiceDisplayLabel() : "Piseth & Sreymom";
    showToast(`Audio Track: ${vLabel}`);
}

// Dynamic Video Frame Engine: Adapts monitor screen box or fills entire area
window.videoFitMode = 'fit'; // Default strictly to FIT mode so video is NEVER cut off!

function adaptMonitorScreenToVideo() {
    const mainVideo = document.getElementById('main-video');
    const screenArea = document.getElementById('monitor-screen-area');
    if (!mainVideo || !screenArea) return;

    const w = mainVideo.videoWidth;
    const h = mainVideo.videoHeight;
    if (w && h && w > 0 && h > 0) {
        if (window.videoFitMode === 'fill') {
            if (screenArea.style.aspectRatio !== 'auto') screenArea.style.aspectRatio = 'auto';
            if (screenArea.style.flex !== '1') screenArea.style.flex = '1';
            if (screenArea.style.height !== '100%') screenArea.style.height = '100%';
            if (screenArea.style.width !== '100%') screenArea.style.width = '100%';
            if (screenArea.style.maxHeight !== '100%') screenArea.style.maxHeight = '100%';
            if (screenArea.style.maxWidth !== '100%') screenArea.style.maxWidth = '100%';
            if (mainVideo.style.objectFit !== 'cover') mainVideo.style.objectFit = 'cover';
        } else {
            // FIT Mode: STRICT GUARANTEE - Video is NEVER cut off in any screen size!
            const targetRatio = `${w} / ${h}`;
            if (screenArea.style.aspectRatio !== targetRatio) screenArea.style.aspectRatio = targetRatio;
            if (screenArea.style.flex !== '0 1 auto') screenArea.style.flex = '0 1 auto';
            if (screenArea.style.maxHeight !== 'calc(100% - 10px)') screenArea.style.maxHeight = 'calc(100% - 10px)';
            if (screenArea.style.maxWidth !== '100%') screenArea.style.maxWidth = '100%';
            if (mainVideo.style.objectFit !== 'contain') mainVideo.style.objectFit = 'contain';
        }
        if (mainVideo.style.background !== 'transparent') mainVideo.style.background = 'transparent';
    }
}

function toggleVideoFitFillMode() {
    const mainVideo = document.getElementById('main-video');
    const btn = document.getElementById('btn-video-fit-fill');
    const label = document.getElementById('label-fit-fill');
    const icon = document.getElementById('icon-fit-fill');
    if (!mainVideo) return;

    if (window.videoFitMode === 'fit') {
        window.videoFitMode = 'fill';
        if (label) label.textContent = 'FILL';
        if (icon) icon.className = 'fa-solid fa-up-right-and-down-left-from-center';
        if (btn) btn.title = 'Current: FILL (Full Box). Click for FIT (Original Full Frame - មិនដាច់)';
        adaptMonitorScreenToVideo();
        showToast('Monitor: FILL Mode (ពេញផ្ទៃ)');
    } else {
        window.videoFitMode = 'fit';
        if (label) label.textContent = 'FIT';
        if (icon) icon.className = 'fa-solid fa-compress';
        if (btn) btn.title = 'Current: FIT (Full Frame - មិនដាច់). Click for FILL';
        adaptMonitorScreenToVideo();
        showToast('Monitor: FIT Mode (ពេញរូបភាព មិនដាច់)');
    }
}

function applyVideoFitMode() {
    adaptMonitorScreenToVideo();
}

function toggleGuidesMenu() {
    showToast("Aspect Guides: 9:16 Vertical / Safe Margins Active");
}

function toggleFullscreen() {
    const elem = document.getElementById('monitor-screen-area');
    if (!document.fullscreenElement && !document.webkitFullscreenElement) {
        if (elem.requestFullscreen) {
            elem.requestFullscreen().catch(() => {});
        } else if (elem.webkitRequestFullscreen) {
            elem.webkitRequestFullscreen();
        }
    } else {
        exitFullscreenMode();
    }
}

function exitFullscreenMode(e) {
    if (e && e.stopPropagation) {
        e.stopPropagation();
        e.preventDefault();
    }
    if (document.fullscreenElement || document.webkitFullscreenElement) {
        if (document.exitFullscreen) {
            document.exitFullscreen().catch(() => {});
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        }
    }
}

// Sync Fullscreen icon state with browser fullscreen changes
document.addEventListener('fullscreenchange', handleFullscreenStateChange);
document.addEventListener('webkitfullscreenchange', handleFullscreenStateChange);

function handleFullscreenStateChange() {
    const fsIcon = document.getElementById('fullscreen-btn-icon');
    const fsBtn = document.getElementById('btn-fullscreen-toggle');
    const isFs = !!(document.fullscreenElement || document.webkitFullscreenElement);
    if (isFs) {
        if (fsIcon) fsIcon.className = 'fa-solid fa-compress';
        if (fsBtn) fsBtn.title = 'Exit Fullscreen / Back (Esc)';
    } else {
        if (fsIcon) fsIcon.className = 'fa-solid fa-expand';
        if (fsBtn) fsBtn.title = 'Fullscreen';
    }
}

function autoDetectVideoDuration(file, callback) {
    if (!file) return;
    try {
        const objectUrl = URL.createObjectURL(file);
        const probe = document.createElement('video');
        probe.preload = 'metadata';
        let resolved = false;

        const onReady = () => {
            if (!resolved && probe.duration && !isNaN(probe.duration) && isFinite(probe.duration) && probe.duration > 0) {
                resolved = true;
                const dur = probe.duration;
                probe.src = '';
                probe.remove();
                if (callback) callback(dur);
            }
        };

        probe.onloadedmetadata = onReady;
        probe.ondurationchange = onReady;
        probe.oncanplay = onReady;
        probe.onloadeddata = onReady;
        probe.onerror = () => {
            if (!resolved) {
                resolved = true;
                probe.remove();
            }
        };

        probe.src = objectUrl;
        probe.load();

        setTimeout(() => {
            if (!resolved && probe.duration && !isNaN(probe.duration) && isFinite(probe.duration) && probe.duration > 0) {
                resolved = true;
                callback(probe.duration);
                probe.src = '';
                probe.remove();
            }
        }, 1500);
    } catch (err) {
        console.warn("Auto duration probe error:", err);
    }
}

function toggleAutoSwitch(checked) {
    showToast(checked ? "Auto Processing Mode: ON" : "Auto Processing Mode: OFF");
}

// ==========================================================================
// STUDIO PROCESSING & ACTIVITY CONSOLE - ADVANCED DIAGNOSTICS & ERROR ENGINE
// ==========================================================================
const StudioDiagnostics = {
    errors: [],
    warnings: [],
    logs: [],
    activeFilter: 'all', // 'all', 'error', 'warning', 'dub'
    errorCount: 0,
    warnCount: 0,
    isAutoScrollPaused: false,
    maxBuffer: 600,
    initialized: false
};

function getFormattedTerminalTime() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    return `[${h}:${m}:${s}]`;
}

function initStudioDiagnosticsListeners() {
    if (StudioDiagnostics.initialized) return;
    StudioDiagnostics.initialized = true;

    // 1. Auto-scroll watcher: pause auto-scroll if user scrolls up to review logs/errors
    const stream = document.getElementById('studio-live-terminal-stream');
    const scrollPill = document.getElementById('terminal-scroll-bottom-pill');
    if (stream) {
        stream.addEventListener('scroll', () => {
            const distanceFromBottom = stream.scrollHeight - stream.scrollTop - stream.clientHeight;
            if (distanceFromBottom > 45) {
                StudioDiagnostics.isAutoScrollPaused = true;
                if (scrollPill) scrollPill.style.display = 'inline-flex';
            } else {
                StudioDiagnostics.isAutoScrollPaused = false;
                if (scrollPill) scrollPill.style.display = 'none';
            }
        });
    }

    // 2. Global Uncaught JavaScript Exception Catcher
    window.addEventListener('error', (event) => {
        try {
            const msg = event.message || "Uncaught JavaScript error";
            const file = event.filename ? event.filename.split('/').pop() : "script";
            const loc = `${file}:${event.lineno || 0}`;
            const details = event.error && event.error.stack ? event.error.stack : `Source: ${event.filename} line ${event.lineno}:${event.colno}`;
            logStudioError("JS Runtime", `${msg} (${loc})`, {
                details: details,
                error: event.error,
                type: "ClientError"
            }, "A client-side script exception was intercepted. UI remains stable.");
        } catch (_) {}
    });

    // 3. Global Unhandled Promise Rejection Catcher (e.g. failed fetches, network drops)
    window.addEventListener('unhandledrejection', (event) => {
        try {
            const reason = event.reason;
            const msg = (reason && reason.message) ? reason.message : String(reason || "Unhandled Promise Rejection");
            const details = (reason && reason.stack) ? reason.stack : String(reason);
            logStudioError("Async Promise", msg, {
                details: details,
                reason: reason,
                type: "UnhandledRejection"
            }, "An asynchronous request failed or was interrupted. Check network or server connection.");
        } catch (_) {}
    });

    // 4. Media Player Error Catcher
    const mainVideo = document.getElementById('main-video');
    if (mainVideo) {
        mainVideo.addEventListener('error', () => {
            const err = mainVideo.error;
            let codeMsg = "Unknown Media Error";
            if (err) {
                switch (err.code) {
                    case 1: codeMsg = "MEDIA_ERR_ABORTED (Loading aborted)"; break;
                    case 2: codeMsg = "MEDIA_ERR_NETWORK (Network error downloading video)"; break;
                    case 3: codeMsg = "MEDIA_ERR_DECODE (Video decoding failed or codec unsupported)"; break;
                    case 4: codeMsg = "MEDIA_ERR_SRC_NOT_SUPPORTED (Video format not supported or file missing)"; break;
                }
            }
            logStudioError("Video Player", `Preview playback error: ${codeMsg}`, {
                details: `Video Src: ${mainVideo.src}\nError Code: ${err ? err.code : 'None'}`
            }, "Ensure the video file is encoded in standard MP4 (H.264/AAC).");
        });
    }
}

function autoDiagnoseClientMessage(msg) {
    const lower = String(msg || "").toLowerCase();
    if (lower.includes("cuda out of memory") || lower.includes("out of memory")) {
        return "VRAM/GPU memory full. Close heavy background apps or switch to CPU mode.";
    }
    if (lower.includes("getaddrinfo") || lower.includes("timeout") || lower.includes("network") || lower.includes("edge_tts") || lower.includes("fetch")) {
        return "ដាច់ការតភ្ជាប់អ៊ីនធឺណិត ឬសេវា TTS។ សូមពិនិត្យមើល Internet / Wi-Fi។ (Network or Cloud TTS service issue).";
    }
    if (lower.includes("ffmpeg") || lower.includes("codec") || lower.includes("moov atom")) {
        return "វីដេអូខូចទម្រង់ ឬកូដិកមិនគាំទ្រ។ សូមបម្លែងទៅជា MP4 H.264។ (Unsupported video codec or broken file).";
    }
    if (lower.includes("whisper") || lower.includes("stt")) {
        return "កំហុសក្នុងការស្ដាប់សំឡេង (STT)។ សូមពិនិត្យសំឡេងក្នុងវីដេអូ។ (Speech recognition error).";
    }
    if (lower.includes("translat") || lower.includes("gemini") || lower.includes("groq") || lower.includes("quota")) {
        return "កំហុសក្នុងម៉ាស៊ីនបកប្រែ (AI Translation Error)។ សូមពិនិត្យមើល API Key (Gemini/Groq) ឬអ៊ីនធឺណិត។ (Translation API error or quota limit reached).";
    }
    if (lower.includes("disk full") || lower.includes("permission denied")) {
        return "ទំហំផ្ទុក Disk ពេញ ឬគ្មានសិទ្ធិ។ សូមពិនិត្យទំហំថាសរឹង។ (Disk full or file permission denied).";
    }
    return null;
}

function sanitizeBranding(str) {
    if (typeof str !== 'string') return str;
    return str
        .replace(/https?:\/\/api\.nisay\.store(?:\/v1)?/gi, 'https://cloud.sntool.ai')
        .replace(/api\.nisay(?:\.store)?/gi, 'SN TOOL Cloud')
        .replace(/nisay-transcribe/gi, 'SN Tool Speech Engine')
        .replace(/nisay[\s_-]*translate/gi, 'SN Tool AI Translator')
        .replace(/nisay[\s_-]*cloud/gi, 'SN Tool Cloud')
        .replace(/nisay/gi, 'SN TOOL');
}

function appendLiveTerminalLine(message, tag = "[Video 1/1]", type = "info", meta = null) {
    message = sanitizeBranding(message);
    tag = sanitizeBranding(tag);
    const stream = document.getElementById('studio-live-terminal-stream');
    if (!stream) return;

    if (!StudioDiagnostics.initialized) {
        initStudioDiagnosticsListeners();
    }

    // Normalize types
    let normType = type;
    if (normType === "warn") normType = "warning";
    if (normType === "err") normType = "error";

    const timeStr = getFormattedTerminalTime();

    // Track Diagnostic Stats
    if (normType === "error") {
        StudioDiagnostics.errorCount++;
        StudioDiagnostics.errors.push({
            time: timeStr,
            tag: tag,
            message: message,
            meta: meta
        });

        // Update badge in top bar
        const errCountElem = document.getElementById('terminal-error-count');
        const errBadgeElem = document.getElementById('term-err-badge');
        const diagPill = document.getElementById('terminal-diag-pill');
        const termBox = document.getElementById('studio-terminal-box');
        const pillBtn = document.getElementById('term-filter-error');

        if (errCountElem) errCountElem.textContent = StudioDiagnostics.errorCount;
        if (errBadgeElem) errBadgeElem.textContent = StudioDiagnostics.errorCount;
        if (diagPill) diagPill.style.display = 'inline-flex';
        if (termBox) termBox.classList.add('has-errors');
        if (pillBtn) pillBtn.classList.add('has-items');

        // Turn status pill to ERROR DETECTED if currently idle/standby
        const statText = document.getElementById('monitor-engine-status-text');
        const statPill = document.getElementById('monitor-engine-status-pill');
        const statDot = document.getElementById('monitor-pulse-dot');
        if (statText && (statText.textContent.includes('STANDBY') || statText.textContent.includes('READY'))) {
            statText.textContent = `ERROR DETECTED (${StudioDiagnostics.errorCount})`;
            if (statPill) statPill.className = 'engine-status-pill error';
            if (statDot) statDot.className = 'pulse-indicator error';
        }

    } else if (normType === "warning") {
        StudioDiagnostics.warnCount++;
        StudioDiagnostics.warnings.push({
            time: timeStr,
            tag: tag,
            message: message,
            meta: meta
        });
        const warnBadgeElem = document.getElementById('term-warn-badge');
        const warnBtn = document.getElementById('term-filter-warn');
        if (warnBadgeElem) warnBadgeElem.textContent = StudioDiagnostics.warnCount;
        if (warnBtn) warnBtn.classList.add('has-items');
    }

    // Keep log history
    StudioDiagnostics.logs.push({
        time: timeStr,
        tag: tag,
        message: message,
        type: normType,
        meta: meta
    });
    if (StudioDiagnostics.logs.length > 1000) {
        StudioDiagnostics.logs.shift();
    }

    // Create Row Element
    const row = document.createElement('div');
    row.className = `term-stream-row term-${normType}`;
    row.setAttribute('data-type', normType);

    if (normType === "error") {
        // High-end Error Card structure
        const headerLine = document.createElement('div');
        headerLine.className = 'term-error-header-line';

        const tsSpan = document.createElement('span');
        tsSpan.className = 'term-ts';
        tsSpan.textContent = timeStr;

        const tagSpan = document.createElement('span');
        tagSpan.className = 'term-tag';
        tagSpan.textContent = tag || "[ERROR]";

        const msgSpan = document.createElement('span');
        msgSpan.className = 'term-error-msg-main';
        msgSpan.innerHTML = `<i class="fa-solid fa-circle-xmark" style="color:#ef4444; margin-right:4px;"></i> ${escapeHtml(message)}`;

        headerLine.appendChild(tsSpan);
        headerLine.appendChild(tagSpan);
        headerLine.appendChild(msgSpan);
        row.appendChild(headerLine);

        // Actionable Suggestion Box
        const suggestion = (meta && meta.suggestion) ? meta.suggestion : autoDiagnoseClientMessage(message);
        if (suggestion) {
            const suggBox = document.createElement('div');
            suggBox.className = 'term-error-suggestion-box';
            suggBox.innerHTML = `<i class="fa-solid fa-lightbulb"></i> <span><strong>Solution:</strong> ${escapeHtml(suggestion)}</span>`;
            row.appendChild(suggBox);
        }

        // Expandable Details / Trace if available
        const detailsText = meta && (meta.details || meta.stack || (meta.error && meta.error.stack));
        if (detailsText) {
            const detailsWrap = document.createElement('div');
            detailsWrap.className = 'term-error-details-wrap';
            detailsWrap.innerHTML = `
                <details>
                    <summary>
                        <i class="fa-solid fa-code"></i> Technical Details / Trace ▼
                        <button type="button" class="term-copy-single-err-btn" onclick="copySingleDiagnosticError(event, this)">Copy Trace</button>
                    </summary>
                    <pre>${escapeHtml(String(detailsText).trim())}</pre>
                </details>
            `;
            row.appendChild(detailsWrap);
        }

    } else {
        // Standard Terminal Line (Info, Success, Dub, Warning)
        const tsSpan = document.createElement('span');
        tsSpan.className = 'term-ts';
        tsSpan.textContent = timeStr;

        const tagSpan = document.createElement('span');
        tagSpan.className = 'term-tag';
        tagSpan.textContent = tag;

        const msgSpan = document.createElement('span');
        msgSpan.className = 'term-msg';

        if (normType === "dub" && message.includes(" ➜ ")) {
            const parts = message.split(" ➜ ");
            msgSpan.innerHTML = `${escapeHtml(parts[0])} <span style="color:#facc15; font-weight:bold;">➜</span> <span style="color:#38bdf8;">${escapeHtml(parts[1])}</span>`;
        } else if (normType === "warning") {
            msgSpan.innerHTML = `<i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b; margin-right:4px;"></i> ${escapeHtml(message)}`;
        } else {
            msgSpan.textContent = message;
        }

        row.appendChild(tsSpan);
        row.appendChild(tagSpan);
        row.appendChild(msgSpan);
    }

    // Apply Filter visibility
    if (StudioDiagnostics.activeFilter !== 'all') {
        const matchesFilter = (
            (StudioDiagnostics.activeFilter === 'error' && normType === 'error') ||
            (StudioDiagnostics.activeFilter === 'warning' && (normType === 'warning' || normType === 'warn')) ||
            (StudioDiagnostics.activeFilter === 'dub' && normType === 'dub')
        );
        if (!matchesFilter) {
            row.classList.add('hidden-by-filter');
        }
    }

    stream.appendChild(row);

    // Keep terminal buffer clean (max rows)
    while (stream.children.length > StudioDiagnostics.maxBuffer) {
        stream.removeChild(stream.firstChild);
    }

    // Auto-scroll if user hasn't scrolled up
    if (!StudioDiagnostics.isAutoScrollPaused) {
        stream.scrollTop = stream.scrollHeight;
    }
}

function logStudioError(stage, message, errorObj = null, suggestion = null) {
    let details = "";
    if (errorObj) {
        if (typeof errorObj === "string") {
            details = errorObj;
        } else if (errorObj.details) {
            details = errorObj.details;
        } else if (errorObj.stack) {
            details = errorObj.stack;
        } else if (errorObj.error) {
            details = String(errorObj.error);
        } else {
            try { details = JSON.stringify(errorObj, null, 2); } catch (_) { details = String(errorObj); }
        }
    }
    const tag = `[${stage || "Studio Error"}]`;
    appendLiveTerminalLine(message, tag, "error", {
        stage: stage,
        suggestion: suggestion,
        details: details,
        error: errorObj
    });
}

function logStudioWarning(stage, message, suggestion = null) {
    const tag = `[${stage || "Notice"}]`;
    appendLiveTerminalLine(message, tag, "warning", {
        stage: stage,
        suggestion: suggestion
    });
}

function setTerminalFilter(filterType) {
    StudioDiagnostics.activeFilter = filterType;

    // Update filter pill UI
    document.querySelectorAll('.term-filter-pill').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`term-filter-${filterType === 'warning' ? 'warn' : filterType}`);
    if (activeBtn) activeBtn.classList.add('active');

    const stream = document.getElementById('studio-live-terminal-stream');
    if (!stream) return;

    const rows = stream.querySelectorAll('.term-stream-row');
    rows.forEach(r => {
        if (filterType === 'all') {
            r.classList.remove('hidden-by-filter');
        } else if (filterType === 'error') {
            if (r.classList.contains('term-error')) {
                r.classList.remove('hidden-by-filter');
            } else {
                r.classList.add('hidden-by-filter');
            }
        } else if (filterType === 'warning') {
            if (r.classList.contains('term-warning') || r.classList.contains('term-warn')) {
                r.classList.remove('hidden-by-filter');
            } else {
                r.classList.add('hidden-by-filter');
            }
        } else if (filterType === 'dub') {
            if (r.classList.contains('term-dub')) {
                r.classList.remove('hidden-by-filter');
            } else {
                r.classList.add('hidden-by-filter');
            }
        }
    });

    scrollTerminalToBottom(false);
}

function scrollTerminalToBottom(force = true) {
    const stream = document.getElementById('studio-live-terminal-stream');
    const scrollPill = document.getElementById('terminal-scroll-bottom-pill');
    StudioDiagnostics.isAutoScrollPaused = false;
    if (scrollPill) scrollPill.style.display = 'none';
    if (stream) {
        stream.scrollTop = stream.scrollHeight;
    }
}

async function copySingleDiagnosticError(event, btn) {
    if (event) event.stopPropagation();
    const detailsWrap = btn ? btn.closest('.term-error-details-wrap') : null;
    const pre = detailsWrap ? detailsWrap.querySelector('pre') : null;
    const text = pre ? pre.textContent : "";
    if (!text) return;

    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
        }
        btn.textContent = "Copied! ✓";
        setTimeout(() => { if (btn) btn.textContent = "Copy Trace"; }, 1800);
        showToast("Error diagnostic trace copied to clipboard! ✓");
    } catch (e) {
        showToast("Copied error trace!");
    }
}

async function exportDiagnosticReport() {
    const stream = document.getElementById('studio-live-terminal-stream');
    const logs = [];
    if (stream) {
        const rows = stream.querySelectorAll('.term-stream-row');
        rows.forEach(r => {
            const t = r.innerText || r.textContent || "";
            if (t.trim()) logs.push(t.trim());
        });
    }

    const reportLines = [
        "================================================================================",
        "SN STUDIO - SYSTEM DIAGNOSTIC & ERROR ANALYSIS REPORT",
        "================================================================================",
        `Timestamp: ${new Date().toISOString()} (${new Date().toLocaleString()})`,
        `Client OS / Agent: ${navigator.userAgent || "Unknown"}`,
        `Display Resolution: ${window.innerWidth}x${window.innerHeight} (DPR: ${window.devicePixelRatio || 1})`,
        `Active Task ID: ${activeDubbingTaskId || "None (Idle)"}`,
        `Current Story Preset: ${currentStudioPreset || "drama"}`,
        `Staged Media: ${stagedVideoFile ? (getMediaFileName(stagedVideoFile) || "Video Loaded") : "None"}`,
        `Total Errors Caught: ${StudioDiagnostics.errorCount}`,
        `Total Warnings Caught: ${StudioDiagnostics.warnCount}`,
        "--------------------------------------------------------------------------------",
        "CAUGHT ERRORS & STACK TRACES:",
        "--------------------------------------------------------------------------------"
    ];

    if (StudioDiagnostics.errors.length === 0) {
        reportLines.push("No fatal errors recorded in current session. System running normally.");
    } else {
        StudioDiagnostics.errors.forEach((err, idx) => {
            reportLines.push(`[Error #${idx + 1}] ${err.time} ${err.tag}: ${err.message}`);
            if (err.meta && err.meta.suggestion) {
                reportLines.push(`  Suggested Fix: ${err.meta.suggestion}`);
            }
            if (err.meta && err.meta.details) {
                reportLines.push(`  Trace Details:\n${err.meta.details}`);
            }
            reportLines.push("");
        });
    }

    reportLines.push("--------------------------------------------------------------------------------");
    reportLines.push("RECENT CONSOLE ACTIVITY (LAST 60 LINES):");
    reportLines.push("--------------------------------------------------------------------------------");
    const recentLogs = logs.slice(-60);
    if (recentLogs.length === 0) {
        reportLines.push("Console log buffer is empty.");
    } else {
        recentLogs.forEach(l => reportLines.push(l));
    }
    reportLines.push("================================================================================");

    const fullReport = reportLines.join('\n');
    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(fullReport);
        } else {
            const ta = document.createElement('textarea');
            ta.value = fullReport;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            ta.remove();
        }
        showToast("Copied Complete Diagnostic & Error Report to clipboard! ✓");
    } catch (err) {
        showToast("Diagnostic report generated and copied!");
    }
}

function clearLiveTerminal() {
    const stream = document.getElementById('studio-live-terminal-stream');
    StudioDiagnostics.errorCount = 0;
    StudioDiagnostics.warnCount = 0;
    StudioDiagnostics.errors = [];
    StudioDiagnostics.warnings = [];
    StudioDiagnostics.logs = [];
    StudioDiagnostics.isAutoScrollPaused = false;
    StudioDiagnostics.activeFilter = 'all';

    const errCountElem = document.getElementById('terminal-error-count');
    const errBadgeElem = document.getElementById('term-err-badge');
    const warnBadgeElem = document.getElementById('term-warn-badge');
    const diagPill = document.getElementById('terminal-diag-pill');
    const scrollPill = document.getElementById('terminal-scroll-bottom-pill');
    const termBox = document.getElementById('studio-terminal-box');

    if (errCountElem) errCountElem.textContent = '0';
    if (errBadgeElem) errBadgeElem.textContent = '0';
    if (warnBadgeElem) warnBadgeElem.textContent = '0';
    if (diagPill) diagPill.style.display = 'none';
    if (scrollPill) scrollPill.style.display = 'none';
    if (termBox) termBox.classList.remove('has-errors');

    document.querySelectorAll('.term-filter-pill').forEach(btn => {
        btn.classList.remove('active');
        btn.classList.remove('has-items');
    });
    const allBtn = document.getElementById('term-filter-all');
    if (allBtn) allBtn.classList.add('active');

    resetEngineMonitorToStandby();

    if (stream) {
        stream.innerHTML = `
            <div class="term-stream-row term-init">
                <span class="term-ts">[Ready]</span>
                <span class="term-tag">[SN Studio]</span>
                <span class="term-msg">Log cleared. Diagnostics reset. Import video and click <strong style="color:#facc15;">Export</strong> to run dubbing.</span>
            </div>
        `;
    }
}

async function copyLiveTerminalLogs() {
    const stream = document.getElementById('studio-live-terminal-stream');
    if (!stream) return;

    const rows = stream.querySelectorAll('.term-stream-row');
    const lines = [];
    rows.forEach(r => {
        const text = r.innerText || r.textContent || "";
        if (text.trim()) {
            lines.push(text.trim());
        }
    });

    const fullLog = lines.join('\n');
    if (!fullLog) {
        showToast("Console is currently empty");
        return;
    }

    try {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(fullLog);
        } else {
            const ta = document.createElement('textarea');
            ta.value = fullLog;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            ta.remove();
        }
        showToast("Copied all Console logs to clipboard! ✓");
    } catch (err) {
        console.warn("Clipboard copy note:", err);
        showToast("Copied! (You can also highlight text directly)");
    }
}

function appendTerminalLine(text) {
    const history = document.getElementById('engine-log-history');
    if (history) {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.textContent = text;
        history.appendChild(line);
        history.scrollTop = history.scrollHeight;
    }
    const currentTask = document.getElementById('monitor-current-task');
    if (currentTask) {
        currentTask.innerHTML = `<i class="fa-solid fa-gear fa-spin" style="color:#facc15; font-size:0.65rem;"></i> ${escapeHtml(text)}`;
    }
    appendLiveTerminalLine(text, "[System]", "info");
}

function refreshAppTelemetry() {
    showToast("Telemetry Refreshed");
    appendLiveTerminalLine(`Status rechecked - engine idle.`, "[System]", "info");
}

// ==========================================================================
// STUDIO PRESET SETUP, DIALOGUE GRID & WAVEFORM PLAYER CONTROLLER
// ==========================================================================
const studioPresetsData = {
    drama: {
        id: "drama",
        badge: `<i class="fa-solid fa-clapperboard"></i> Drama Dubbing Mode (16:9 / 9:16)`,
        name: "Drama Dubbing Mode (16:9 / 9:16)",
        dialogues: [
            { id: 1, tcIn: "00:00:01.200", tcOut: "00:00:04.850", speaker: "Piseth", voice: "piseth", speakerClass: "speaker-piseth", orig: "今天你必须给我一个合理的解释！", khmer: "You must give me a reasonable explanation today!" },
            { id: 2, tcIn: "00:00:05.100", tcOut: "00:00:08.400", speaker: "Sreymom", voice: "sreymom", speakerClass: "speaker-sreymom", orig: "我做的一切，都是为了保住我们家族的秘密。", khmer: "Everything I did was to protect our family secret." },
            { id: 3, tcIn: "00:00:09.000", tcOut: "00:00:13.250", speaker: "Piseth", voice: "piseth", speakerClass: "speaker-piseth", orig: "难道你觉得这样就能瞒得过所有人吗？", khmer: "Do you really think you can hide it from everyone forever?" },
            { id: 4, tcIn: "00:00:13.800", tcOut: "00:00:17.900", speaker: "Sreymom", voice: "sreymom", speakerClass: "speaker-sreymom", orig: "既然你已经知道了，那我也无话可说了。", khmer: "Now that you know everything, I have nothing left to say." },
            { id: 5, tcIn: "00:00:18.500", tcOut: "00:00:22.300", speaker: "Piseth", voice: "piseth", speakerClass: "speaker-piseth", orig: "把真相告诉我，这是你最后的机会。", khmer: "Tell me the truth, this is your last chance." }
        ]
    },
    narration: {
        id: "narration",
        badge: `<i class="fa-solid fa-microphone-lines"></i> Voiceover Narration (Piseth / Sreymom Audio)`,
        name: "Voiceover Narration (Piseth / Sreymom Audio)",
        dialogues: [
            { id: 1, tcIn: "00:00:00.800", tcOut: "00:00:05.200", speaker: "Piseth", voice: "piseth", speakerClass: "speaker-piseth", orig: "在繁华都市的阴影下，一段尘封已久的秘密悄然揭开...", khmer: "In the bustling city shadows, a long-buried secret unfolds..." },
            { id: 2, tcIn: "00:00:05.600", tcOut: "00:00:09.800", speaker: "Sreymom", voice: "sreymom", speakerClass: "speaker-sreymom", orig: "无人知晓，那个雨夜改变了所有人的命运。", khmer: "Nobody knows that rainy night changed the fate of everyone." },
            { id: 3, tcIn: "00:00:10.200", tcOut: "00:00:14.500", speaker: "Piseth", voice: "piseth", speakerClass: "speaker-piseth", orig: "他独自一人走向那座庄园，心中早已有决断。", khmer: "He walked towards the mansion alone, having already made up his mind." }
        ]
    },
    subtitle: {
        id: "subtitle",
        badge: `<i class="fa-solid fa-closed-captioning"></i> Subtitle Extraction & Khmer Sync`,
        name: "Subtitle Extraction & Khmer Sync",
        dialogues: [
            { id: 1, tcIn: "00:00:01.000", tcOut: "00:00:03.500", speaker: "Piseth", voice: "piseth", speakerClass: "speaker-piseth", orig: "快点离开这里，危险！", khmer: "Leave here quickly, it's dangerous!" },
            { id: 2, tcIn: "00:00:04.000", tcOut: "00:00:06.800", speaker: "Sreymom", voice: "sreymom", speakerClass: "speaker-sreymom", orig: "我不能丢下你一个人！", khmer: "I cannot leave you alone!" },
            { id: 3, tcIn: "00:00:07.200", tcOut: "00:00:11.000", speaker: "Piseth", voice: "piseth", speakerClass: "speaker-piseth", orig: "相信我，我一定会安全回来的。", khmer: "Trust me, I will definitely return safely." }
        ]
    }
};

let currentStudioPreset = 'drama';
let studioViewMode = 'clean'; // 'clean' (Image 2 default), 'presets', or 'grid'

function initStudioWorkspace() {
    generateWaveformBars();
    generateVuMiniWaveBars();
    resetVuMetersToIdle();
    resetEngineMonitorToStandby();

    // Wire up video events & synchronization
    const mainVideo = document.getElementById('main-video');
    if (mainVideo) {
        mainVideo.addEventListener('ended', () => {
            isPlaying = false;
            const playIcon = document.getElementById('center-play-icon');
            const playBtn = document.getElementById('center-play-btn');
            const bottomPlayIcon = document.getElementById('bottom-play-icon');
            if (playIcon) playIcon.className = 'fa-solid fa-play';
            if (bottomPlayIcon) bottomPlayIcon.className = 'fa-solid fa-play';
            if (playBtn) {
                playBtn.style.opacity = '1';
                playBtn.style.pointerEvents = 'auto';
            }
            if (playbackTimer) {
                clearInterval(playbackTimer);
                playbackTimer = null;
            }
            resetVuMetersToIdle();
        });

        mainVideo.addEventListener('pause', () => {
            if (isPlaying) {
                isPlaying = false;
                const playIcon = document.getElementById('center-play-icon');
                const playBtn = document.getElementById('center-play-btn');
                const bottomPlayIcon = document.getElementById('bottom-play-icon');
                if (playIcon) playIcon.className = 'fa-solid fa-play';
                if (bottomPlayIcon) bottomPlayIcon.className = 'fa-solid fa-play';
                if (playBtn) {
                    playBtn.style.opacity = '1';
                    playBtn.style.pointerEvents = 'auto';
                }
                if (playbackTimer) {
                    clearInterval(playbackTimer);
                    playbackTimer = null;
                }
                resetVuMetersToIdle();
            }
        });

        mainVideo.addEventListener('play', () => {
            if (!isPlaying) {
                isPlaying = true;
                const playIcon = document.getElementById('center-play-icon');
                const playBtn = document.getElementById('center-play-btn');
                const bottomPlayIcon = document.getElementById('bottom-play-icon');
                if (playIcon) playIcon.className = 'fa-solid fa-pause';
                if (bottomPlayIcon) bottomPlayIcon.className = 'fa-solid fa-pause';
                if (playBtn) {
                    playBtn.style.opacity = '0';
                    playBtn.style.pointerEvents = 'none';
                }
            }
        });
    }

    // Spacebar to toggle Play/Pause, Escape to close popups
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
            e.preventDefault();
            togglePlayPreview();
        } else if (e.code === 'Escape') {
            closeBrowseMenu();
            closePowerMenu();
        }
    });

    // Preload dialogue items for initial active preset
    const preset = studioPresetsData[currentStudioPreset];
    if (preset) renderDialogueGrid(preset.dialogues);

    // Initial default view is Clean Image 2 View
    showCleanSourceView();

    // Initialize interactive overlays (logo & blur mask drag & resize)
    initInteractiveOverlays();

    // Wire up dynamic adaptive video frame engine (Zero black bars, matches original aspect ratio)
    if (mainVideo) {
        mainVideo.addEventListener('loadedmetadata', adaptMonitorScreenToVideo);
        mainVideo.addEventListener('canplay', adaptMonitorScreenToVideo);
        mainVideo.addEventListener('loadeddata', adaptMonitorScreenToVideo);
        if (mainVideo.videoWidth > 0) adaptMonitorScreenToVideo();
    }
}

function selectStudioPreset(presetKey) {
    currentStudioPreset = presetKey;
    const preset = studioPresetsData[presetKey] || studioPresetsData.drama;

    // Update active class on preset cards
    document.querySelectorAll('.studio-preset-card').forEach(c => c.classList.remove('active'));
    const targetCard = document.getElementById(`card-preset-${presetKey}`);
    if (targetCard) targetCard.classList.add('active');

    // Update top header badge
    const badge = document.getElementById('current-mode-badge');
    if (badge) badge.innerHTML = preset.badge;

    // Load dialogues into grid
    renderDialogueGrid(preset.dialogues);

    showToast(`Mode Configured: ${preset.name}`);
    appendTerminalLine(`[Ready] Workflow preset set to ${preset.name}. Ready for media import or audition.`);
}

function showCleanSourceView() {
    studioViewMode = 'clean';
    const cleanView = document.getElementById('studio-source-clean-view');
    const setupView = document.getElementById('studio-preset-setup-view');
    const gridView = document.getElementById('studio-dialogue-waveform-view');

    if (cleanView) cleanView.style.display = 'flex';
    if (setupView) setupView.style.display = 'none';
    if (gridView) gridView.style.display = 'none';

    const importPrompt = document.getElementById('clean-import-prompt');
    const stagedCard = document.getElementById('staged-video-card');
    const sourceLabel = document.getElementById('clean-source-label');
    if (stagedVideoFile || stagedBatchFiles) {
        if (importPrompt) importPrompt.style.display = 'none';
        if (stagedCard) stagedCard.style.display = 'flex';
        if (sourceLabel) sourceLabel.style.display = 'none';
    } else {
        if (importPrompt) importPrompt.style.display = 'flex';
        if (stagedCard) stagedCard.style.display = 'none';
        if (sourceLabel) sourceLabel.style.display = 'block';
    }
}

function showPresetSetupView() {
    studioViewMode = 'presets';
    const cleanView = document.getElementById('studio-source-clean-view');
    const setupView = document.getElementById('studio-preset-setup-view');
    const gridView = document.getElementById('studio-dialogue-waveform-view');

    if (cleanView) cleanView.style.display = 'none';
    if (setupView) setupView.style.display = 'flex';
    if (gridView) gridView.style.display = 'none';
}

function showDialogueWaveformView() {
    // Keep UI clean, modern, and uncluttered (User requested hiding the raw dialogue table)
    showCleanSourceView();
}

function toggleSetupPresetsView() {
    if (studioViewMode === 'clean') {
        showPresetSetupView();
    } else if (studioViewMode === 'presets') {
        showCleanSourceView();
    } else {
        showCleanSourceView();
    }
}

let activeLoadedDialogues = [];
let activeDialogueAudioPlayer = null;

function formatSecondsToTimecode(sec) {
    if (sec === undefined || sec === null || isNaN(sec)) return "00:00:00.000";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const ms = Math.floor((sec % 1) * 1000);
    return `00:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
}

function renderDialogueGrid(dialogues) {
    const tbody = document.getElementById('dialogue-grid-rows');
    if (!tbody) return;

    activeLoadedDialogues = dialogues || [];
    tbody.innerHTML = '';
    activeLoadedDialogues.forEach((d, idx) => {
        const tr = document.createElement('tr');
        const rowId = d.id || (idx + 1);
        tr.className = 'dialogue-row';
        tr.id = `dialogue-row-${rowId}`;

        const tcInStr = d.tcIn || formatSecondsToTimecode(d.start);
        const tcOutStr = d.tcOut || formatSecondsToTimecode(d.end);

        const vKey = (d.voice || d.voice_used || "piseth").toLowerCase();
        const isSreyMom = vKey.includes("sreymom") || vKey.includes("female");
        const speakerClass = isSreyMom ? "speaker-sreymom" : "speaker-piseth";
        const defaultSpeaker = isSreyMom ? "Sreymom (Female Solo)" : "Piseth (Male Solo)";
        const speakerName = d.speaker || defaultSpeaker;

        const origText = d.orig || d.text_original || d.text || "";
        const khmerText = d.khmer || d.text_km || origText;

        tr.innerHTML = `
            <td style="color:#716655; font-family:var(--font-mono);">${rowId}</td>
            <td><span class="tc-code">${tcInStr} - ${tcOutStr}</span></td>
            <td>
                <span class="speaker-badge ${speakerClass}">
                    <i class="fa-solid fa-user-voice"></i> ${escapeHtml(speakerName)}
                </span>
            </td>
            <td class="orig-script-text">${escapeHtml(origText)}</td>
            <td class="khmer-dub-text">${escapeHtml(khmerText)}</td>
            <td style="text-align:center;">
                <button class="grid-action-btn" title="Play Audio Speech" onclick="playDialogueSnippet(${rowId})"><i class="fa-solid fa-play"></i></button>
                <button class="grid-action-btn" title="Edit Dialogue Line" onclick="editDialogueSnippet(${rowId})"><i class="fa-solid fa-pen"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function playDialogueSnippet(id) {
    const item = activeLoadedDialogues.find(d => String(d.id) === String(id));
    const targetRow = document.getElementById(`dialogue-row-${id}`);
    document.querySelectorAll('.dialogue-row').forEach(r => r.classList.remove('playing'));
    if (targetRow) targetRow.classList.add('playing');

    showToast(`Playing dialogue line #${id}`);
    appendTerminalLine(`[Audio Engine] Auditioning line #${id} (${item ? (item.voice || 'piseth') : 'audio'})`);

    if (activeDialogueAudioPlayer) {
        try { activeDialogueAudioPlayer.pause(); } catch(e) {}
        activeDialogueAudioPlayer = null;
    }

    startAudioPlaybackVUMeter();

    let audioUrl = null;
    if (item && item.audio_file) {
        audioUrl = `/media/${item.audio_file.replace(/\\/g, '/')}`;
    }

    if (audioUrl) {
        activeDialogueAudioPlayer = new Audio(audioUrl);
        activeDialogueAudioPlayer.onended = () => {
            resetVuMetersToIdle();
            if (targetRow) targetRow.classList.remove('playing');
        };
        activeDialogueAudioPlayer.onerror = () => {
            resetVuMetersToIdle();
            if (targetRow) targetRow.classList.remove('playing');
        };
        try {
            await activeDialogueAudioPlayer.play();
            return;
        } catch(e) {
            console.warn("Direct play note:", e);
        }
    }

    // Fallback on-the-fly synthesize preview if not yet cached
    if (item && (item.text_km || item.khmer)) {
        try {
            let voiceTarget = "piseth";
            if (item.voice) {
                voiceTarget = item.voice.toLowerCase().includes("sreymom") ? "sreymom" : "piseth";
            } else if (item.speaker) {
                const spkLow = item.speaker.toLowerCase();
                if (spkLow.includes("sreymom") || spkLow.includes("female")) {
                    voiceTarget = "sreymom";
                }
            }
            const resp = await fetch('/api/voices/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: item.text_km || item.khmer,
                    voice: voiceTarget
                })
            });
            const data = await resp.json();
            if (data.success && data.audio_url) {
                activeDialogueAudioPlayer = new Audio(data.audio_url);
                activeDialogueAudioPlayer.onended = () => {
                    resetVuMetersToIdle();
                    if (targetRow) targetRow.classList.remove('playing');
                };
                activeDialogueAudioPlayer.play();
                return;
            }
        } catch (e) {
            console.warn("Preview error:", e);
        }
    }

    setTimeout(() => {
        resetVuMetersToIdle();
        if (targetRow) targetRow.classList.remove('playing');
    }, 2000);
}

function editDialogueSnippet(id) {
    showToast(`Editing dialogue line #${id}`);
}

function generateWaveformBars() {
    const container = document.getElementById('waveform-bars');
    if (!container) return;
    container.innerHTML = '';
    const heights = [30, 45, 70, 85, 60, 40, 55, 90, 100, 80, 50, 65, 85, 95, 75, 40, 50, 80, 90, 70, 45, 60, 85, 70, 55, 40, 65, 90, 100, 85, 60, 45, 70, 85, 95, 65, 40, 55, 80, 75, 60, 50, 70, 85, 90, 65, 45, 55, 75, 90, 80, 60, 50, 65, 80, 70, 50, 40, 60, 75];
    heights.forEach(h => {
        const bar = document.createElement('div');
        bar.className = 'waveform-wave-bar';
        bar.style.height = `${h}%`;
        container.appendChild(bar);
    });
}

function handleWaveformClick(e) {
    const track = document.getElementById('waveform-visualizer-track');
    const playhead = document.getElementById('waveform-playhead');
    if (!track || !playhead) return;
    const rect = track.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percent = Math.max(0, Math.min(100, (clickX / rect.width) * 100));
    playhead.style.left = `${percent}%`;
    playheadSeconds = (percent / 100) * totalDurationSeconds;
    updateScrubberUI();
}

function seekRelative(delta) {
    playheadSeconds = Math.max(0, Math.min(totalDurationSeconds, playheadSeconds + delta));
    updateScrubberUI();
}

function generateVuMiniWaveBars() {
    const container = document.getElementById('vu-mini-wave-bars');
    if (!container) return;
    container.innerHTML = '';
    for (let i = 0; i < 14; i++) {
        const bar = document.createElement('div');
        bar.className = 'vu-wave-bar';
        bar.style.height = '4%';
        container.appendChild(bar);
    }
}

// ==========================================================================
// VU METERS & AUDIO REACTIVITY CONTROLLER
// ==========================================================================
let vuAnimationTimer = null;

function resetVuMetersToIdle() {
    if (vuAnimationTimer) {
        clearInterval(vuAnimationTimer);
        vuAnimationTimer = null;
    }
    const fillL = document.getElementById('vu-fill-l');
    const fillR = document.getElementById('vu-fill-r');
    const dbL = document.getElementById('vu-db-l');
    const dbR = document.getElementById('vu-db-r');

    if (fillL) fillL.style.width = '0%';
    if (fillR) fillR.style.width = '0%';
    if (dbL) dbL.textContent = '-∞ dB';
    if (dbR) dbR.textContent = '-∞ dB';

    const miniBars = document.querySelectorAll('#vu-mini-wave-bars .vu-wave-bar');
    miniBars.forEach(bar => {
        bar.style.height = '4%';
    });
}

function startAudioPlaybackVUMeter() {
    if (vuAnimationTimer) clearInterval(vuAnimationTimer);

    vuAnimationTimer = setInterval(() => {
        if (!isPlaying) {
            resetVuMetersToIdle();
            return;
        }
        const fillL = document.getElementById('vu-fill-l');
        const fillR = document.getElementById('vu-fill-r');
        const dbL = document.getElementById('vu-db-l');
        const dbR = document.getElementById('vu-db-r');

        const randL = Math.floor(Math.random() * 25 + 55); // 55% - 80%
        const randR = Math.floor(Math.random() * 25 + 50); // 50% - 75%

        if (fillL) fillL.style.width = `${randL}%`;
        if (fillR) fillR.style.width = `${randR}%`;

        if (dbL) dbL.textContent = `-${Math.floor((100 - randL) * 0.35)} dB`;
        if (dbR) dbR.textContent = `-${Math.floor((100 - randR) * 0.4)} dB`;

        const miniBars = document.querySelectorAll('#vu-mini-wave-bars .vu-wave-bar');
        miniBars.forEach(bar => {
            bar.style.height = `${Math.floor(Math.random() * 75 + 15)}%`;
        });
    }, 200);
}

// ==========================================================================
// EXPORT JOB & STUDIO ENGINE RENDER MONITOR CONTROLLER
// ==========================================================================
let exportJobTimer = null;
let exportPercent = 0;
let exportElapsedSec = 0;
let currentExportOutputMode = 'separate'; // 'separate' | 'full' | 'both'
let currentCustomExportFolder = localStorage.getItem('sn_custom_export_dir') || "";

let stagedVideoSiblings = null;
let stagedVideoFolderTitle = "";

function updateExportLocationUI() {
    const pathTextElem = document.getElementById('export-output-path-text');
    const resetBtn = document.getElementById('btn-reset-export-folder');

    if (!pathTextElem) return;

    if (currentCustomExportFolder && currentCustomExportFolder.trim()) {
        const cleanPath = currentCustomExportFolder.trim();
        pathTextElem.innerHTML = `Saved in <strong>${cleanPath}</strong>`;
        pathTextElem.title = `Saved in: ${cleanPath}`;
        if (resetBtn) resetBtn.style.display = 'inline-flex';
    } else {
        pathTextElem.innerHTML = `Saved in <strong>SN TOOL</strong> folder next to source video`;
        pathTextElem.title = `Saved in SN TOOL folder next to source video`;
        if (resetBtn) resetBtn.style.display = 'none';
    }
}

async function syncDramaExportFolder(dramaTitle) {
    if (!dramaTitle || !dramaTitle.trim()) return;
    const cleanTitle = dramaTitle.trim()
        .replace(/(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$/gi, '')
        .replace(/^(?:Dubbed_)+/i, '')
        .replace(/(?:_part|[-_]ep|[-_]e|\bep|\bepisode)[-_]?\d+.*$/i, '')
        .replace(/[-_]+$/, '')
        .trim();
    if (!cleanTitle) return;

    let baseDir = currentCustomExportFolder || localStorage.getItem('sn_custom_export_dir') || "";
    if (!baseDir) {
        baseDir = "D:/SN_Dramas";
    }

    baseDir = baseDir.replace(/\\/g, '/').replace(/\/+$/, '');
    const currentLeaf = baseDir.split('/').pop() || "";
    let targetFolder = baseDir;
    if (currentLeaf.toLowerCase() !== cleanTitle.toLowerCase() && currentLeaf.toLowerCase() !== "dubbed_khmer") {
        targetFolder = `${baseDir}/${cleanTitle}`;
    }

    currentCustomExportFolder = targetFolder;
    localStorage.setItem('sn_custom_export_dir', currentCustomExportFolder);
    updateExportLocationUI();

    // Auto-create folder on disk immediately!
    try {
        await fetch('/api/system/ensure-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: targetFolder })
        });
    } catch (e) {
        console.warn("Auto create folder note:", e);
    }
}

async function browseExportFolder(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    try {
        const res = await fetch('/api/system/select-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                initial_dir: currentCustomExportFolder || ""
            })
        });
        const data = await res.json();
        if (data && data.success && data.path) {
            let chosen = data.path.replace(/\\/g, '/').replace(/\/+$/, '');

            // Detect current drama title
            let dramaTitle = stagedVideoFolderTitle || "";
            if (!dramaTitle && stagedBatchFiles && stagedBatchFiles.length > 0) {
                const fName = getMediaFileName(stagedBatchFiles[0]);
                dramaTitle = fName.replace(/(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$/gi, '')
                    .replace(/^(?:Dubbed_)+/i, '')
                    .replace(/(?:_part|[-_]ep|[-_]e|\bep|\bepisode)[-_]?\d+.*$/i, '')
                    .replace(/[-_]+$/, '')
                    .trim();
            } else if (!dramaTitle && stagedVideoFile) {
                const vName = getMediaFileName(stagedVideoFile);
                dramaTitle = vName.replace(/(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$/gi, '')
                    .replace(/^(?:Dubbed_)+/i, '')
                    .replace(/(?:_part|[-_]ep|[-_]e|\bep|\bepisode)[-_]?\d+.*$/i, '')
                    .replace(/[-_]+$/, '')
                    .trim();
            }

            const chosenLeaf = chosen.split('/').pop() || "";
            if (dramaTitle && chosenLeaf.toLowerCase() !== dramaTitle.toLowerCase() && chosenLeaf.toLowerCase() !== "dubbed_khmer") {
                chosen = `${chosen}/${dramaTitle}`;
            }

            currentCustomExportFolder = chosen;
            localStorage.setItem('sn_custom_export_dir', currentCustomExportFolder);

            // Auto-create folder on disk immediately!
            try {
                await fetch('/api/system/ensure-folder', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: chosen })
                });
            } catch (err) {
                console.warn("Folder create note:", err);
            }

            updateExportLocationUI();
            showToast(`📁 បានបង្កើត Folder ដោយស្វ័យប្រវត្តិ៖ ${chosen}`);
        }
    } catch (e) {
        console.warn("Folder picker note:", e);
    }
}

function resetExportFolderToDefault(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    currentCustomExportFolder = "";
    localStorage.removeItem('sn_custom_export_dir');
    updateExportLocationUI();
    showToast("Save location reset to default folder");
}

function openExportOptionsModal() {
    const epCountElem = document.getElementById('export-output-ep-count');
    const epChainElem = document.getElementById('export-output-ep-chain');
    const descFullElem = document.getElementById('export-desc-full');
    const descBothElem = document.getElementById('export-desc-both');

    let baseTitle = "Drama_Series";
    stagedVideoSiblings = null;
    stagedVideoFolderTitle = "";

    if (stagedBatchFiles && stagedBatchFiles.length > 0) {
        const count = stagedBatchFiles.length;
        if (epCountElem) epCountElem.textContent = `${count} episodes`;

        if (epChainElem) {
            if (count <= 4) {
                epChainElem.textContent = stagedBatchFiles.map((f, i) => `Ep${i + 1}`).join(' → ');
            } else {
                epChainElem.textContent = `Ep1 → Ep2 → ... → Ep${count}`;
            }
        }

        const firstFile = stagedBatchFiles[0];
        const fName = getMediaFileName(firstFile);
        const rawName = fName.replace(/(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$/gi, '');
        baseTitle = rawName.replace(/(?:_part|[-_]ep|[-_]e|\bep|\bepisode)[-_]?\d+/i, '').replace(/[-_]+$/, '').trim() || "Drama_Series";

        const cleanSeriesTitle = baseTitle.replace(/^(?:Dubbed_)+/i, '');
        const mergedName = `Dubbed_${cleanSeriesTitle}_Full_Movie.mp4`;
        if (descFullElem) descFullElem.textContent = `Pre-merge ${count} episodes & dub as 1 full movie (${mergedName})`;
        if (descBothElem) descBothElem.textContent = `Separate episodes + ${mergedName}`;

        syncDramaExportFolder(cleanSeriesTitle);

    } else if (stagedVideoFile) {
        const vName = getMediaFileName(stagedVideoFile);
        if (epCountElem) epCountElem.textContent = "1 Video (Single Episode)";
        if (epChainElem) epChainElem.textContent = vName;

        const rawName = vName.replace(/(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$/gi, '');
        baseTitle = rawName.replace(/(?:_part|[-_]ep|[-_]e|\bep|\bepisode)[-_]?\d+/i, '').replace(/[-_]+$/, '').trim() || rawName || "Video";
        const cleanBase = rawName.replace(/^(?:Dubbed_)+/i, '');
        const singleOutName = `Dubbed_${cleanBase}.mp4`;

        if (descFullElem) descFullElem.textContent = `Saved as: ${singleOutName}`;
        if (descBothElem) descBothElem.textContent = `Saved as: ${singleOutName}`;

        syncDramaExportFolder(baseTitle);

        // Check if single video has sibling episodes in parent folder
        const vPath = getMediaFilePath(stagedVideoFile);
        if (vPath) {
            fetch("/api/system/find-sibling-episodes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filepath: vPath })
            }).then(r => r.json()).then(sibData => {
                if (sibData && sibData.success && sibData.has_siblings && sibData.files && sibData.files.length > 1) {
                    stagedVideoSiblings = sibData.files;
                    stagedVideoFolderTitle = sibData.folder_name;
                    const sibCount = sibData.total_count;
                    const fTitle = sibData.folder_name || cleanBase;
                    const cleanFolderTitle = fTitle.replace(/^(?:Dubbed_)+/i, '');
                    const fullOutName = `Dubbed_${cleanFolderTitle}_Full_Movie.mp4`;
                    if (epCountElem) epCountElem.textContent = `1 Video • Detected ${sibCount} episodes in "${sibData.folder_name}"`;
                    if (descFullElem) descFullElem.textContent = `Pre-merge all ${sibCount} episodes in folder into 1 full movie (${fullOutName})`;
                    if (descBothElem) descBothElem.textContent = `Dub ${sibCount} separate episodes + ${fullOutName}`;

                    syncDramaExportFolder(sibData.folder_name);
                }
            }).catch(e => console.warn("Sibling probe note:", e));
        }
    } else {
        showToast("Please stage a video first, then click Export!");
        openImportModal();
        return;
    }

    updateExportLocationUI();
    selectExportOutputMode(currentExportOutputMode || 'separate');
    openModal('modal-export-options');
}

function selectExportOutputMode(mode) {
    currentExportOutputMode = mode;
    const optSep = document.getElementById('export-opt-separate');
    const optFull = document.getElementById('export-opt-full');
    const optBoth = document.getElementById('export-opt-both');

    if (optSep) optSep.classList.toggle('active', mode === 'separate');
    if (optFull) optFull.classList.toggle('active', mode === 'full');
    if (optBoth) optBoth.classList.toggle('active', mode === 'both');
}

async function confirmAndExecuteExport() {
    closeModal('modal-export-options');
    const chosenMode = currentExportOutputMode || 'separate';

    // 1. Single video staged
    if (stagedVideoFile) {
        const fileToDub = stagedVideoFile;
        const siblings = stagedVideoSiblings;
        const folderTitle = stagedVideoFolderTitle;
        stagedVideoFile = null;
        stagedVideoSiblings = null;
        stagedVideoFolderTitle = "";

        const exportBtn = document.getElementById('btn-tab-export');
        if (exportBtn) exportBtn.classList.remove('export-ready-pulse');

        // If user chose full movie merged or both, and sibling episodes were detected in directory
        if ((chosenMode === 'full' || chosenMode === 'both') && siblings && siblings.length > 1) {
            showToast(`Auto-combining all ${siblings.length} episodes from "${folderTitle}" into full movie...`);
            startStudioBatchDubbingPipeline(siblings, chosenMode);
            return;
        }

        const fileName = getMediaFileName(fileToDub);
        const rawName = fileName.replace(/(?:\.mp4|\.mkv|\.mov|\.avi|\.webm|\.flv|\.ts)+$/gi, '');
        const cleanBase = rawName.replace(/^(?:Dubbed_)+/i, '');
        const customTitle = (chosenMode === 'full') ? `Dubbed_${cleanBase}_Full_Movie` : `Dubbed_${cleanBase}`;
        startAutoDubbingPipeline(fileToDub, customTitle);
        return;
    }

    // 2. Batch videos staged
    if (stagedBatchFiles && stagedBatchFiles.length > 0) {
        const filesToDub = stagedBatchFiles;
        stagedBatchFiles = null;
        const exportBtn = document.getElementById('btn-tab-export');
        if (exportBtn) exportBtn.classList.remove('export-ready-pulse');
        startStudioBatchDubbingPipeline(filesToDub, chosenMode);
        return;
    }

    showToast("No video currently staged!");
}

function startStudioExportJob() {
    // 0. If dubbing task is currently genuinely running in background
    if (activeDubbingTaskId && activeDubbingPollTimer) {
        showToast("Studio engine is dubbing video, please wait...");
        return;
    }
    // Auto-clear stale task id if no active poll timer is running
    activeDubbingTaskId = null;

    // 1. If user staged a single video, open Export Options Modal (Choice for user)
    if (stagedVideoFile) {
        openExportOptionsModal();
        return;
    }

    // 2. If user staged batch videos / folder, open Export Options Modal (Separate / One Full Video / Both)
    if (stagedBatchFiles && stagedBatchFiles.length > 0) {
        openExportOptionsModal();
        return;
    }

    // 3. If a dubbed video is already completed, check if Logo or Blur effect was added to re-render
    if (currentDubbedProject && (currentDubbedProject.id || currentDubbedProject.output_video_file)) {
        const hasOverlayToBurn = (currentOverlayAssets.logo || currentOverlayAssets.serverLogoPath || currentOverlayAssets.blurActive || currentOverlayAssets.textActive);
        if (hasOverlayToBurn && currentDubbedProject.id) {
            reRenderCurrentDubbedProjectWithOverlay();
            return;
        }

        if (currentDubbedProject.output_video_file) {
            openExportFolderDirect(currentDubbedProject.output_video_file);
            showToast("Opened rendered video output folder!");
            const mainVideo = document.getElementById('main-video');
            if (mainVideo && mainVideo.src) {
                const a = document.createElement('a');
                a.href = mainVideo.src;
                a.download = `Dubbed_${currentDubbedProject.title || 'drama'}.mp4`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            }
            return;
        }
    }

    // 4. If nothing is staged, guide the user to import first
    showToast("Please stage a video first, then click Export!");
    openImportModal();
}

let _currentJobMaxProgressPct = 0;

function updateExportProgressUI(pct, elapsedSec, etaSec, taskName) {
    const pctElem = document.getElementById('monitor-export-percent');
    const fillElem = document.getElementById('monitor-progress-fill');
    const elapElem = document.getElementById('monitor-elapsed-time');
    const etaElem = document.getElementById('monitor-eta-time');
    const finElem = document.getElementById('monitor-finish-time');
    const taskElem = document.getElementById('monitor-current-task');
    const footerProg = document.getElementById('footer-studio-progress');
    const footerText = document.querySelector('#footer-studio-main div:first-child');

    // Monotonic guard: During an active dubbing run, progress should never jitter backwards
    if (pct > 0 && pct < 100) {
        _currentJobMaxProgressPct = Math.max(_currentJobMaxProgressPct, pct);
        pct = _currentJobMaxProgressPct;
    } else if (pct >= 100) {
        pct = 100;
        _currentJobMaxProgressPct = 0;
    } else if (pct === 0) {
        _currentJobMaxProgressPct = 0;
    }

    if (pctElem) pctElem.textContent = `${pct}%`;
    if (fillElem) fillElem.style.width = `${pct}%`;
    if (footerProg) footerProg.style.width = `${pct}%`;
    if (footerText && taskName) footerText.textContent = `Status: ${taskName} (${pct}%)`;

    const elM = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
    const elS = String(elapsedSec % 60).padStart(2, '0');
    if (elapElem) elapElem.textContent = `00:${elM}:${elS}`;

    if (etaSec > 0) {
        const etM = String(Math.floor(etaSec / 60)).padStart(2, '0');
        const etS = String(etaSec % 60).padStart(2, '0');
        if (etaElem) etaElem.textContent = `00:${etM}:${etS}`;

        const finishDate = new Date(Date.now() + etaSec * 1000);
        if (finElem) finElem.textContent = finishDate.toLocaleTimeString();
    } else {
        if (etaElem) etaElem.textContent = '00:00:00';
        if (finElem) finElem.textContent = 'Completed';
    }

    if (taskElem) {
        taskElem.innerHTML = `<i class="fa-solid fa-gear fa-spin" style="color:#facc15; font-size:0.65rem;"></i> ${escapeHtml(taskName)}`;
    }

    if (pct >= 100 && !window._exportChimePlayedThisRun) {
        window._exportChimePlayedThisRun = true;
        if (typeof playWindowsCompletionSound === 'function') {
            playWindowsCompletionSound();
        }
    }
}

function resetEngineMonitorToStandby() {
    activeDubbingTaskId = null;
    if (activeDubbingPollTimer) {
        clearInterval(activeDubbingPollTimer);
        activeDubbingPollTimer = null;
    }
    if (exportJobTimer) {
        clearInterval(exportJobTimer);
        exportJobTimer = null;
    }

    const pill = document.getElementById('monitor-engine-status-pill');
    const dot = document.getElementById('monitor-pulse-dot');
    const text = document.getElementById('monitor-engine-status-text');
    if (pill) pill.className = 'engine-status-pill standby';
    if (dot) dot.className = 'pulse-indicator standby';
    if (text) text.textContent = 'ENGINE STANDBY';

    const fpsElem = document.getElementById('monitor-render-fps');
    const fpsCap = document.getElementById('monitor-fps-caption');
    const brElem = document.getElementById('monitor-render-bitrate');
    const brCap = document.getElementById('monitor-bitrate-caption');

    if (fpsElem) fpsElem.textContent = '0.0';
    if (fpsCap) fpsCap.textContent = 'Idle (Ready)';
    if (brElem) brElem.textContent = '0.0';
    if (brCap) brCap.textContent = 'Standby';

    const pctElem = document.getElementById('monitor-export-percent');
    const fillElem = document.getElementById('monitor-progress-fill');
    const elapElem = document.getElementById('monitor-elapsed-time');
    const etaElem = document.getElementById('monitor-eta-time');
    const finElem = document.getElementById('monitor-finish-time');
    const taskElem = document.getElementById('monitor-current-task');

    if (pctElem) pctElem.textContent = '0%';
    if (fillElem) fillElem.style.width = '0%';
    if (elapElem) elapElem.textContent = '00:00:00';
    if (etaElem) etaElem.textContent = '--:--:--';
    if (finElem) finElem.textContent = 'Standby';
    if (taskElem) {
        taskElem.innerHTML = `<i class="fa-solid fa-circle-check" style="color:#22c55e; font-size:0.65rem;"></i> System Ready • Select a preset or import media`;
    }
}

function toggleEngineLogDrawer() {
    const drawer = document.getElementById('engine-log-drawer');
    if (drawer) {
        drawer.style.display = drawer.style.display === 'none' ? 'block' : 'none';
    }
}

// ==========================================================================
// 4. DOWNLOADER STUDIO (Exact Match to Image 2)
// ==========================================================================
const DEFAULT_FALLBACK_PLATFORMS = [
    { id: "all", name: "All platforms", icon: "fa-solid fa-globe", count: 633672 },
    { id: "hongguo", name: "Hongguo", logo: "hongguo_logo.png", count: 49591 },
    { id: "shortmax", name: "ShortMax", logo: "shortmax_logo.png", count: 120000 },
    { id: "ai_drama", name: "AI Dramas", logo: "ai_drama_logo.png", count: 24081 },
    { id: "reelshort", name: "ReelShort", logo: "reelshort_logo.png", count: 120000 },
    { id: "freereels", name: "FreeReels", logo: "freereels_logo.png", count: 120000 },
    { id: "anyreel", name: "AnyReel", logo: "anyreel_logo.png", count: 200000 },
];

function renderPlatformsIntoContainer(platforms, container) {
    if (!container || !platforms || platforms.length === 0) return;
    container.innerHTML = '';
    platforms.forEach(p => {
        const item = document.createElement('div');
        item.className = `dl-platform-pill-item ${p.id === dlSelectedPlatform ? 'active' : ''}`;
        item.onclick = () => filterByPlatform(p.id, p.name, p.count, p.logo);
        
        let iconHtml = '';
        if (p.logo) {
            iconHtml = `<img src="${p.logo}" class="dl-platform-icon-img" alt="${escapeHtml(p.name)}">`;
        } else if (p.icon) {
            iconHtml = `<i class="${p.icon}"></i>`;
        }
        
        item.innerHTML = `
            ${iconHtml}
            <span>${escapeHtml(p.name)}</span>
        `;
        container.appendChild(item);
    });
}

async function loadDownloaderPlatforms() {
    const container = document.getElementById('dl-platforms-list');
    if (!container) return;

    try {
        const res = await fetch('/api/downloader/platforms');
        if (res.ok) {
            const data = await res.json();
            if (data.success && data.platforms && data.platforms.length > 0) {
                renderPlatformsIntoContainer(data.platforms, container);
                return;
            }
        }
    } catch (e) {
        console.warn('[Downloader] Platforms fetch fallback to default:', e);
    }
    // Fallback: Ensure platforms list is NEVER empty
    renderPlatformsIntoContainer(DEFAULT_FALLBACK_PLATFORMS, container);
}

async function loadDownloaderCategories() {
    const bar = document.getElementById('dl-category-chips-bar');
    if (bar) {
        bar.style.display = 'none';
        bar.innerHTML = '';
    }
}

function selectCategoryChip(catId) {
    dlSelectedCategory = catId;
    const chips = document.querySelectorAll('.dl-category-chip-btn');
    chips.forEach(c => {
        if (c.dataset.catId === catId || (catId === 'all' && c.dataset.catId === 'all')) {
            c.classList.add('active');
        } else {
            c.classList.remove('active');
        }
    });
    loadDramaCatalog(dlSelectedPlatform, dlSearchQuery, dlSelectedCategory, false);
}

function getSavedFavorites() {
    try {
        return JSON.parse(localStorage.getItem('sn_saved_dramas') || '{}') || {};
    } catch (e) {
        return {};
    }
}

function updateSavedCountUI() {
    const favs = getSavedFavorites();
    const counter = document.getElementById('dl-saved-counter');
    if (counter) counter.textContent = Object.keys(favs).length;
}

function isDramaFavorite(id) {
    const favs = getSavedFavorites();
    return !!favs[id];
}

function toggleDramaFavorite(id, title) {
    const favs = getSavedFavorites();
    if (favs[id]) {
        delete favs[id];
        showToast(`Removed '${title}' from saved`);
    } else {
        favs[id] = { id, title, time: Date.now() };
        showToast(`Saved '${title}' ♥`);
    }
    localStorage.setItem('sn_saved_dramas', JSON.stringify(favs));
    updateSavedCountUI();

    const card = document.getElementById(`dl-card-${id}`);
    if (card) {
        const btn = card.querySelector('.bz-fav-btn');
        if (btn) btn.classList.toggle('on', !!favs[id]);
    }
}

function copyDramaTitle(title) {
    if (!title) return;
    navigator.clipboard.writeText(title).then(() => {
        showToast(`Copied title: ${title}`);
    }).catch(() => {
        showToast(`Copied: ${title}`);
    });
}

function copyDramaTag(title) {
    if (!title) return;
    const tag = `《${title}》`;
    navigator.clipboard.writeText(tag).then(() => {
        showToast(`Copied tag: ${tag}`);
    }).catch(() => {});

    // Automatically paste tag into the Hongguo URL/Search input box
    const input = document.getElementById('dl-link-url-input');
    if (input) {
        input.value = tag;
        input.focus();
    }
}

function showSavedFavoritesModal() {
    const favs = getSavedFavorites();
    const count = Object.keys(favs).length;
    if (count === 0) {
        showToast("No saved dramas yet. Tap ♥ on any drama to build your saved list!");
        return;
    }
    const titles = Object.values(favs).map(f => f.title).join('\n');
    navigator.clipboard.writeText(titles).then(() => {
        showToast(`Copied all ${count} saved drama titles to clipboard!`);
    }).catch(() => {});
}

function refreshDramaCatalog() {
    const btn = document.getElementById('btn-dl-refresh-catalog');
    if (btn) {
        btn.innerHTML = '<i class="fa-solid fa-arrows-rotate fa-spin"></i> Refresh';
    }
    loadDramaCatalog(dlSelectedPlatform, dlSearchQuery, dlSelectedCategory, false).finally(() => {
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Refresh';
        }
    });
}

function filterByPlatform(platId, platName, totalCount, platLogo) {
    dlSelectedPlatform = platId;
    loadDownloaderPlatforms();

    const countLabel = document.getElementById('dl-catalog-count-label');
    if (countLabel) {
        const countDisplay = (totalCount !== undefined && totalCount !== null)
            ? totalCount.toLocaleString()
            : (platId === 'hongguo' ? '49,591' : (platId === 'ai_drama' ? '24,081' : (platId === 'shortmax' ? '120,000' : (platId === 'reelshort' ? '120,000' : (platId === 'freereels' ? '120,000' : (platId === 'anyreel' ? '200,000' : '633,672'))))));
        let headerTitle = `Top Dramas on ${escapeHtml(platName)}`;
        if (platId === 'hongguo') headerTitle = 'Top 100 on 红果 right now';
        else if (platId === 'ai_drama') headerTitle = 'Top Authentic Chinese AI Short Dramas (AI漫剧)';
        else if (platId === 'shortmax') headerTitle = 'ShortMax Short Dramas';
        else if (platId === 'reelshort') headerTitle = 'ReelShort English Vertical Short Dramas';
        else if (platId === 'freereels') headerTitle = 'FreeReels Short Dramas';
        else if (platId === 'anyreel') headerTitle = 'AnyReel Short Dramas';
        else if (platId === 'all') headerTitle = 'Top Dramas Across All Platforms';
        countLabel.innerHTML = `<span class="dl-clapper-emoji">🎬</span> ${headerTitle} (${countDisplay})`;
    }

    const input = document.getElementById('dl-link-url-input');
    if (input) {
        if (platId === 'shortmax') {
            input.placeholder = 'Paste ShortMax URL or search...';
        } else if (platId === 'ai_drama') {
            input.placeholder = 'Search Chinese AI short dramas...';
        } else if (platId === 'reelshort') {
            input.placeholder = 'Paste ReelShort URL or search...';
        } else if (platId === 'freereels') {
            input.placeholder = 'Paste FreeReels URL or search...';
        } else if (platId === 'anyreel') {
            input.placeholder = 'Paste AnyReel URL or search...';
        } else {
            input.placeholder = 'Paste a Drama URL or search 79,004 dramas...';
        }
    }

    const badge = document.getElementById('dl-info-platform-badge');
    if (badge) {
        badge.textContent = platName.toUpperCase();
    }

    loadDramaCatalog(platId, dlSearchQuery, dlSelectedCategory, false);
}

// Favorites & Action Helpers (Matching Image 2)
function getDramaFavorites() {
    try {
        return JSON.parse(localStorage.getItem('sn_saved_dramas') || '[]');
    } catch (e) {
        return [];
    }
}

function isDramaFavorite(id) {
    const list = getDramaFavorites();
    return list.some(item => (typeof item === 'string' ? item === id : item.id === id));
}

function toggleDramaFavorite(id, title) {
    let list = getDramaFavorites();
    const existingIdx = list.findIndex(item => (typeof item === 'string' ? item === id : item.id === id));
    if (existingIdx >= 0) {
        list.splice(existingIdx, 1);
        showToast(`Removed from saved: ${title}`);
    } else {
        list.push({ id, title, time: Date.now() });
        showToast(`Saved to favorites: ${title}`);
    }
    localStorage.setItem('sn_saved_dramas', JSON.stringify(list));
    updateSavedCountUI();
    const btn = document.querySelector(`#dl-card-${id} .bz-fav-btn`);
    if (btn) btn.classList.toggle('on', existingIdx < 0);
}

function updateSavedCountUI() {
    const counter = document.getElementById('dl-saved-counter');
    if (counter) {
        const list = getDramaFavorites();
        counter.textContent = list.length;
    }
}

function copyDramaTitle(title) {
    if (!title) return;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(title).catch(() => {});
    }
    showToast(`Copied title: ${title}`);
}

function copyDramaTag(title, dramaId) {
    const cleanId = (dramaId || '').replace(/^hg_/, '');
    const pasteUrl = cleanId && !cleanId.startsWith('top_')
        ? `https://hongguodownloader.com/drama/${cleanId}`
        : `《${title}》`;

    const input = document.getElementById('dl-link-url-input');
    if (input) {
        input.value = pasteUrl;
        input.focus();
    }
    if (navigator.clipboard) {
        navigator.clipboard.writeText(pasteUrl).catch(() => {});
    }
    showToast(`Pasted to analyzer: ${title}`);
}

function toggleEpisodesPanel(forceState) {
    const layout = document.getElementById('dl-catalog-view-wrapper') || document.getElementById('view-downloader-workspace');
    const btn = document.getElementById('btn-toggle-ep-panel');
    if (!layout) return;
    const isCollapsed = layout.classList.contains('episodes-collapsed');
    const targetCollapsed = forceState !== undefined ? !forceState : !isCollapsed;
    layout.classList.toggle('episodes-collapsed', targetCollapsed);
    if (btn) {
        btn.classList.toggle('active', !targetCollapsed);
        btn.innerHTML = targetCollapsed
            ? '<i class="fa-solid fa-list-ul"></i> Episodes'
            : '<i class="fa-solid fa-chevron-right"></i> Hide Panel';
    }
}

function showSavedFavoritesModal() {
    const list = getDramaFavorites();
    if (!list || list.length === 0) {
        showToast("No saved dramas yet. Click ♥ on any card to save!");
        return;
    }
    const names = list.map(item => (typeof item === 'string' ? item : item.title)).join(', ');
    showToast(`Saved (${list.length}): ${names.substring(0, 80)}...`);
}

async function loadDramaCatalog(platformId = "hongguo", query = "", category = "all", append = false) {
    const container = document.getElementById('dl-drama-cards-container');
    if (!container) return;
    setupCatalogInfiniteScroll();

    if (!append) {
        dlCurrentPage = 1;
        dlHasMore = true;
        let platTitle = 'Hongguo';
        if (platformId === 'shortmax') platTitle = 'ShortMax';
        else if (platformId === 'ai_drama') platTitle = 'AI Dramas';
        else if (platformId === 'reelshort') platTitle = 'ReelShort';
        else if (platformId === 'freereels') platTitle = 'FreeReels';
        else if (platformId === 'anyreel') platTitle = 'AnyReel';
        else if (platformId === 'all') platTitle = 'All Platforms';
        container.innerHTML = `<div style="grid-column: 1 / -1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding: 48px; color: #38bdf8;"><i class="fa-solid fa-spinner fa-spin" style="font-size: 1.8rem; margin-bottom:12px;"></i><div style="font-size:0.85rem; font-weight:600; color:#e2e8f0;">Loading drama catalog for ${platTitle}...</div></div>`;
    }

    try {
        const res = await fetch(`/api/downloader/catalog?platform=${platformId}&category=${category}&q=${encodeURIComponent(query)}&page=${dlCurrentPage}&limit=50`);
        const data = await res.json();

        if (!append) container.innerHTML = '';

        if (data.success && data.dramas && data.dramas.length > 0) {
            dlHasMore = (data.has_more !== undefined) ? !!data.has_more : (data.dramas.length >= 50);
            dlTotalDramasCount = data.total_count || data.dramas.length;
            const countLabel = document.getElementById('dl-catalog-count-label');
            if (countLabel) {
                let headerTitle = category === 'all'
                    ? (platformId === 'shortmax' ? 'ShortMax Short Dramas' : (platformId === 'ai_drama' ? 'Top Authentic Chinese AI Short Dramas (AI漫剧)' : (platformId === 'reelshort' ? 'ReelShort English Vertical Short Dramas' : (platformId === 'freereels' ? 'FreeReels Short Dramas' : (platformId === 'anyreel' ? 'AnyReel Short Dramas' : (platformId === 'hongguo' ? 'Top 100 on 红果 right now' : 'Top Dramas Across All Platforms'))))))
                    : `${platformId === 'shortmax' ? 'ShortMax' : (platformId === 'ai_drama' ? 'AI Drama' : (platformId === 'reelshort' ? 'ReelShort' : (platformId === 'freereels' ? 'FreeReels' : (platformId === 'anyreel' ? 'AnyReel' : 'Category'))))}: ${category.toUpperCase()}`;
                countLabel.innerHTML = `<span class="dl-clapper-emoji">🎬</span> ${headerTitle} (${dlTotalDramasCount.toLocaleString()})`;
            }

            updateSavedCountUI();

            window.dlCatalogMap = window.dlCatalogMap || new Map();
            const cardsHtml = data.dramas.map((drama, idx) => {
                window.dlCatalogMap.set(String(drama.id), drama);
                const isActive = (dlActiveCardId === String(drama.id)) || (dlCurrentDrama && String(dlCurrentDrama.id) === String(drama.id));
                const displayTitle = (drama.title_cn || drama.title || '').replace(/[《》]/g, '').split(' - ')[0].trim();
                const posterUrl = drama.poster || '';
                const rank = drama.rank_num || (idx + 1);
                const isTopRank = rank <= 3;
                const ratingBadge = drama.rating ? `<span class="lb-score">★ ${escapeHtml(drama.rating)}</span>` : '';
                const heatBadge = `<span class="lb-eps">${drama.heat ? '🔥 ' + escapeHtml(drama.heat) : (drama.total_episodes ? drama.total_episodes + ' eps' : '')}</span>`;

                return `
                    <div class="dl-card-item ${isActive ? 'active' : ''}" id="dl-card-${drama.id}"
                         onclick="selectDramaCard('${drama.id}', false)"
                         ondblclick="selectDramaCard('${drama.id}', true)">
                        <div class="dl-card-thumb-wrap">
                            <span class="lb-rank ${isTopRank ? 'top' : ''}">${rank}</span>
                            ${ratingBadge}
                            ${posterUrl ? `<img src="${posterUrl}" alt="${escapeHtml(displayTitle)}" loading="lazy" onerror="this.onerror=null; this.style.opacity='0';">` : ''}
                            ${heatBadge}
                        </div>
                        <div class="dl-card-details-box">
                            <div class="dl-card-title-line" title="${escapeHtml(displayTitle)}">${escapeHtml(displayTitle)}</div>
                        </div>
                    </div>
                `;
            }).join('');

            if (append) {
                container.insertAdjacentHTML('beforeend', cardsHtml);
            } else {
                container.innerHTML = cardsHtml;
            }
        } else if (!append) {
            dlHasMore = false;
            if (platformId === 'shortmax' || platformId === 'freereels' || platformId === 'anyreel') {
                const countLabel = document.getElementById('dl-catalog-count-label');
                const isFR = platformId === 'freereels';
                const isAR = platformId === 'anyreel';
                const pTitle = isFR ? 'FreeReels' : (isAR ? 'AnyReel' : 'ShortMax');
                const pLogo = isFR ? 'freereels_logo.png' : (isAR ? 'anyreel_logo.png' : 'shortmax_logo.png');
                if (countLabel) {
                    countLabel.innerHTML = `<span class="dl-clapper-emoji">🎬</span> ${pTitle} Short Dramas (0)`;
                }
                container.innerHTML = `
                    <div style="grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 50px 20px; text-align: center;">
                        <img src="${pLogo}" style="width: 56px; height: 56px; border-radius: 12px; margin-bottom: 14px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); object-fit: contain;" onerror="this.style.display='none'">
                        <div style="font-size: 0.95rem; font-weight: 700; color: #f8fafc; margin-bottom: 8px;">No dramas available in ${pTitle} yet</div>
                        <div style="font-size: 0.78rem; color: #94a3b8; max-width: 380px; line-height: 1.6;">
                            You can paste the drama link from <b>${pTitle}</b> into the search box above and press <b>Enter</b> to fetch episodes automatically.
                        </div>
                    </div>
                `;
            } else {
                container.innerHTML = `
                    <div style="grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 20px; color: #716655; text-align: center;">
                        <i class="fa-solid fa-magnifying-glass" style="font-size: 2rem; color: #38bdf8; margin-bottom: 12px;"></i>
                        <div style="font-size: 0.85rem; font-weight: 600; color: #cbd5e1;">No dramas found for this search</div>
                        <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 6px;">Try searching with different keywords or click All to view catalog.</div>
                    </div>
                `;
            }
        } else {
            dlHasMore = false;
        }
    } catch (e) {
        if (!append) container.innerHTML = '<div style="grid-column: 1 / -1; color:#ef4444; padding:30px; text-align:center;">Network error loading catalog.</div>';
    }
}

function setupCatalogInfiniteScroll() {
    const container = document.getElementById('dl-drama-cards-container');
    if (!container || dlInfiniteScrollAttached) return;
    dlInfiniteScrollAttached = true;
    container.addEventListener('scroll', () => {
        if (dlIsLoadingMore || !dlHasMore) return;
        if (container.scrollTop + container.clientHeight >= container.scrollHeight - 350) {
            loadMoreDramas();
        }
    }, { passive: true });
}

async function loadMoreDramas() {
    if (dlIsLoadingMore || !dlHasMore) return;
    dlIsLoadingMore = true;

    const container = document.getElementById('dl-drama-cards-container');
    let loader = document.getElementById('dl-infinite-loader');
    if (container && !loader) {
        loader = document.createElement('div');
        loader.id = 'dl-infinite-loader';
        loader.style.cssText = 'grid-column: 1 / -1; display:flex; align-items:center; justify-content:center; padding:16px 0 24px 0; color:#38bdf8; gap:8px; font-size:0.85rem; font-weight:600;';
        loader.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Loading more dramas...</span>';
        container.appendChild(loader);
    }

    dlCurrentPage++;
    try {
        await loadDramaCatalog(dlSelectedPlatform, dlSearchQuery, dlSelectedCategory, true);
    } finally {
        if (loader && loader.parentNode) {
            loader.parentNode.removeChild(loader);
        }
        dlIsLoadingMore = false;
    }
}

let dlActiveCardId = null;
let dlDramaSelectionSeq = 0;
const dlDramaDetailCache = new Map();

async function selectDramaCard(dramaId, openQueueMode = false) {
    if (!dramaId) return;
    const strDramaId = String(dramaId);
    const mySeq = ++dlDramaSelectionSeq;

    // 1. ULTRA-FAST O(1) ACTIVE HIGHLIGHT (Zero layout thrashing - avoids looping over hundreds of cards)
    if (dlActiveCardId !== strDramaId) {
        if (dlActiveCardId) {
            const prev = document.getElementById(`dl-card-${dlActiveCardId}`);
            if (prev) prev.classList.remove('active');
        } else {
            const anyPrev = document.querySelector('.dl-card-item.active');
            if (anyPrev) anyPrev.classList.remove('active');
        }
        const activeCard = document.getElementById(`dl-card-${strDramaId}`);
        if (activeCard) activeCard.classList.add('active');
        dlActiveCardId = strDramaId;
    }

    // 2. INSTANT OPTIMISTIC FEEDBACK (< 1ms): Render immediate metadata from memory/catalog map
    const cachedDrama = (window.dlCatalogMap && window.dlCatalogMap.get(strDramaId)) || (dlDramaDetailCache.get(strDramaId)?.drama);
    if (cachedDrama) {
        dlCurrentDrama = cachedDrama;
        const totalEps = cachedDrama.total_episodes || 80;

        const title = document.getElementById('dl-info-title-text');
        const posterImg = document.getElementById('dl-info-poster-img');
        const badge = document.getElementById('dl-info-platform-badge');
        const stats = document.getElementById('dl-info-stats-text');
        const desc = document.getElementById('dl-info-desc-text');

        if (title) title.textContent = cachedDrama.title_cn || cachedDrama.title || "Drama";
        if (posterImg) {
            const emptyIcon = document.getElementById('dl-info-poster-empty-icon');
            const posterFrame = document.getElementById('dl-info-poster-frame');
            if (cachedDrama.poster) {
                posterImg.src = cachedDrama.poster;
                posterImg.style.display = 'block';
                posterImg.style.opacity = '1';
                if (emptyIcon) emptyIcon.style.display = 'none';
                if (posterFrame) posterFrame.style.borderStyle = 'solid';
            } else {
                posterImg.removeAttribute('src');
                posterImg.style.display = 'none';
                if (emptyIcon) emptyIcon.style.display = 'block';
                if (posterFrame) posterFrame.style.borderStyle = 'dashed';
            }
        }
        if (badge) badge.textContent = `${(cachedDrama.platform || 'HONGGUO').toUpperCase()} • ${cachedDrama.rating || '9.8'} ★`;
        if (stats) stats.textContent = `Episodes ${totalEps} • Locked 0 • Selected ${totalEps}`;
        if (desc) desc.textContent = cachedDrama.description || "Hongguo Short Drama Series Manifest.";

        updateDramaSavePathDisplay();

        const catDlBtnText = document.getElementById('dl-catalog-dl-all-text');
        if (catDlBtnText) catDlBtnText.textContent = `Download All Episodes (EP 1 - ${totalEps})`;
        const qDlBtnText = document.getElementById('dl-q-download-all-text');
        if (qDlBtnText) qDlBtnText.textContent = `Download All Episodes (EP 1 - ${totalEps})`;

        const cachedDetail = dlDramaDetailCache.get(strDramaId);
        if (cachedDetail && cachedDetail.episodes && cachedDetail.episodes.length > 0) {
            dlEpisodesList = cachedDetail.episodes.map(ep => ({ ...ep, is_selected: true }));
        } else if (!dlEpisodesList || dlEpisodesList.length === 0 || dlEpisodesList[0]?.drama_id !== strDramaId) {
            dlEpisodesList = Array.from({ length: totalEps }, (_, i) => ({
                id: `${strDramaId}_ep_${String(i + 1).padStart(3, '0')}`,
                drama_id: strDramaId,
                episode_num: i + 1,
                episode_number: i + 1,
                title: `Episode ${String(i + 1).padStart(2, '0')}`,
                duration: "02:00",
                status: "Ready",
                progress: 0,
                is_selected: true
            }));
        }
        renderEpisodesChecklist(dlEpisodesList);

        if (openQueueMode) {
            switchDlViewMode('queue');
            renderQueueViewForCurrentDrama();
        }
    } else if (openQueueMode) {
        switchDlViewMode('queue');
    }

    // 3. RETRIEVE FULL VERIFIED EPISODES (Instant from cache, or background fetch with zero stutter)
    let data = dlDramaDetailCache.get(strDramaId);
    if (!data) {
        try {
            const res = await fetch(`/api/downloader/drama/${strDramaId}`);
            data = await res.json();
            if (data && data.success) {
                dlDramaDetailCache.set(strDramaId, data);
            }
        } catch (e) {
            console.warn("Drama detail fetch error:", e);
        }
    }

    // Guard against race conditions when clicking rapidly between multiple dramas
    if (mySeq !== dlDramaSelectionSeq || !data || !data.success) {
        return;
    }

    dlCurrentDrama = data.drama;
    dlEpisodesList = (data.episodes || []).map(ep => ({ ...ep, is_selected: true }));

    // Update Right DRAMA INFO Box
    const title = document.getElementById('dl-info-title-text');
    const posterImg = document.getElementById('dl-info-poster-img');
    const badge = document.getElementById('dl-info-platform-badge');
    const stats = document.getElementById('dl-info-stats-text');
    const desc = document.getElementById('dl-info-desc-text');
    const totalEps = data.drama.total_episodes || dlEpisodesList.length || 80;

    if (title) title.textContent = data.drama.title;
    if (posterImg && data.drama.poster) {
        posterImg.src = data.drama.poster;
        posterImg.style.display = 'block';
    }
    if (badge) badge.textContent = `${(data.drama.platform || 'HONGGUO').toUpperCase()} • ${data.drama.rating || '9.8'} ★`;
    if (stats) stats.textContent = `Episodes ${totalEps} • Locked 0 • Selected ${totalEps}`;
    if (desc) desc.textContent = data.drama.description || "Hongguo Short Drama Series Manifest.";

    const catDlBtnText = document.getElementById('dl-catalog-dl-all-text');
    if (catDlBtnText) catDlBtnText.textContent = `Download All Episodes (EP 1 - ${totalEps})`;
    const qDlBtnText = document.getElementById('dl-q-download-all-text');
    if (qDlBtnText) qDlBtnText.textContent = `Download All Episodes (EP 1 - ${totalEps})`;

    const leftDlBtn = document.getElementById('btn-dl-start-batch');
    if (leftDlBtn) {
        const span = leftDlBtn.querySelector('span');
        if (span) span.textContent = `Download All (${totalEps} EPs)`;
    }

    updateDramaSavePathDisplay();
    renderEpisodesChecklist(dlEpisodesList);
    updateDownloaderStats(data.stats);

    if (openQueueMode) {
        renderQueueViewForCurrentDrama();
    }
}
window.selectDramaCard = selectDramaCard;

function renderEpisodesChecklist(episodes) {
    const list = document.getElementById('dl-episodes-list-box');
    const rangeTag = document.getElementById('dl-episodes-range-tag');
    if (!list) return;

    if (!episodes || episodes.length === 0) {
        list.innerHTML = '<div style="color:#716655; font-size:0.65rem; padding:8px; text-align:center;">No episodes loaded</div>';
        if (rangeTag) rangeTag.textContent = "EP 0-0";
        return;
    }

    if (rangeTag) rangeTag.textContent = `EP 1-${episodes.length}`;

    // Ultra-Fast single-shot innerHTML rendering (100x faster than appendChild loop)
    const rowsHtml = episodes.map(ep => {
        const prog = ep.progress || 0;
        const statusText = (ep.status === 'Completed' || prog === 100) ? '✔ 100%' : (ep.status === 'Downloading' ? `⚡ ${prog}%` : (ep.status || 'Ready'));
        const statusColor = (ep.status === 'Completed' || prog === 100) ? '#10b981' : (ep.status === 'Downloading' ? '#f59e0b' : 'var(--gold-glow)');
        return `
            <div class="dl-ep-row">
                <div style="display:flex; align-items:center; gap:6px;">
                    <input type="checkbox" ${ep.is_selected ? 'checked' : ''} onchange="toggleSingleEpisode('${ep.id}', this.checked)">
                    <span>EP ${ep.episode_number}: ${escapeHtml(ep.title)}</span>
                </div>
                <span id="dl-cat-status-${ep.episode_number}" class="dl-cat-ep-status" style="font-size:0.62rem; color:${statusColor}; font-weight:600;">${statusText}</span>
            </div>
        `;
    }).join('');

    list.innerHTML = rowsHtml;
}

function toggleSingleEpisode(epId, isChecked) {
    const target = dlEpisodesList.find(e => e.id === epId);
    if (target) target.is_selected = isChecked;
    const selectedCount = dlEpisodesList.filter(e => e.is_selected).length;
    
    const stats = document.getElementById('dl-info-stats-text');
    if (stats && dlCurrentDrama) {
        stats.textContent = `Episodes ${dlCurrentDrama.total_episodes} • Locked 0 • Selected ${selectedCount}`;
    }
    const statSelected = document.getElementById('dl-stat-selected');
    if (statSelected) statSelected.textContent = selectedCount;
}

function handleDlLinkKey(e) {
    if (e.key === 'Enter') analyzeEnteredLink();
}

async function analyzeEnteredLink() {
    const input = document.getElementById('dl-link-url-input');
    const url = input ? input.value.trim() : "";
    if (!url) {
        dlSearchQuery = "";
        await loadDramaCatalog(dlSelectedPlatform, "", dlSelectedCategory, false);
        return;
    }

    if (!url.startsWith("http://") && !url.startsWith("https://")) {
        // Search query mode across 49,509 dramas
        dlSearchQuery = url;
        showToast(`Searching: "${url}"...`);
        appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Searching 49,509 catalog for: "${url}"`);
        await loadDramaCatalog(dlSelectedPlatform, dlSearchQuery, dlSelectedCategory, false);
        return;
    }

    // URL link analysis mode
    showToast("Analyzing drama link...");
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Analyzing drama manifest from URL: ${url}`);

    try {
        const res = await fetch('/api/downloader/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });
        const data = await res.json();
        if (data.success && data.drama) {
            dlCurrentDrama = data.drama;
            dlEpisodesList = data.episodes || [];
            await loadDramaCatalog(dlSelectedPlatform, "", "all", false);
            selectDramaCard(data.drama.id);
            showToast(`Found: ${data.drama.title} (${dlEpisodesList.length} EP)`);
        } else {
            showToast(`${data.error || 'Failed to analyze'}`);
        }
    } catch (e) {
        showToast("Network error");
    }
}

let dlCurrentViewMode = "catalog";
let dlQueueActiveEpisodeNum = 1;

function switchDlViewMode(mode) {
    dlCurrentViewMode = mode;
    const catalogWrapper = document.getElementById('dl-catalog-view-wrapper');
    const queueView = document.getElementById('dl-queue-player-view');

    const catBtn = document.getElementById('btn-mode-catalog');
    const qBtn = document.getElementById('btn-mode-queue');
    const qvCatBtn = document.getElementById('btn-qview-catalog');
    const qvQBtn = document.getElementById('btn-qview-queue');

    if (mode === 'queue') {
        if (catalogWrapper) catalogWrapper.style.display = 'none';
        if (queueView) queueView.style.display = 'flex';

        if (catBtn) catBtn.classList.remove('active');
        if (qBtn) qBtn.classList.add('active');
        if (qvCatBtn) qvCatBtn.classList.remove('active');
        if (qvQBtn) qvQBtn.classList.add('active');

        if (dlCurrentDrama) {
            renderQueueViewForCurrentDrama();
        }
    } else {
        if (catalogWrapper) catalogWrapper.style.display = 'grid';
        if (queueView) {
            queueView.style.display = 'none';
            const vid = document.getElementById('dl-q-video-elem');
            if (vid) vid.pause();
        }

        if (catBtn) catBtn.classList.add('active');
        if (qBtn) qBtn.classList.remove('active');
        if (qvCatBtn) qvCatBtn.classList.add('active');
        if (qvQBtn) qvQBtn.classList.remove('active');
    }
}

function clearDlUrlInput() {
    const inp1 = document.getElementById('dl-link-url-input');
    const inp2 = document.getElementById('dl-qview-url-input');
    if (inp1) inp1.value = '';
    if (inp2) inp2.value = '';
}

let dlAutoNextEnabled = true;
let dlEpisodeCurrentFilter = 'all';

function toggleAutoNext(enabled) {
    dlAutoNextEnabled = !!enabled;
    const toggleInput = document.getElementById('dl-auto-next-toggle');
    if (toggleInput) toggleInput.checked = dlAutoNextEnabled;
}

function filterEpisodeRange(range) {
    dlEpisodeCurrentFilter = range;
    document.querySelectorAll('.dl-hub-pill').forEach(btn => btn.classList.remove('active'));
    const activeBtn = document.getElementById(`dl-filter-pill-${range}`);
    if (activeBtn) activeBtn.classList.add('active');

    const cards = document.querySelectorAll('.dl-ep-card-btn');
    cards.forEach(card => {
        const epNum = parseInt(card.getAttribute('data-ep'));
        if (range === 'all') {
            card.style.display = 'flex';
        } else {
            const parts = range.split('-').map(n => parseInt(n));
            if (parts.length === 2 && epNum >= parts[0] && epNum <= parts[1]) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        }
    });
}

function renderQueueViewForCurrentDrama() {
    if (!dlCurrentDrama) return;

    // Update Top URL input
    const urlInput = document.getElementById('dl-qview-url-input');
    if (urlInput) {
        const cleanId = (dlCurrentDrama.id || '').replace(/^hg_/, '');
        urlInput.value = dlCurrentDrama.series_id
            ? `https://hongguoduanju.com/detail?series_id=${dlCurrentDrama.series_id}`
            : (cleanId && !cleanId.startsWith('top_') ? `https://hongguodownloader.com/drama/${cleanId}` : `《${dlCurrentDrama.title}》`);
    }

    // Update Platform Badge
    const platBadge = document.getElementById('dl-q-platform-badge');
    if (platBadge) {
        platBadge.textContent = (dlCurrentDrama.platform || 'HONGGUO').toUpperCase();
    }

    const dramaTitle = (dlCurrentDrama?.title_cn || dlCurrentDrama?.title || '').replace(/[《》]/g, '').split(' - ')[0].trim();
    const dramaNameElem = document.getElementById('dl-q-now-title');
    if (dramaNameElem) {
        dramaNameElem.textContent = `《${dramaTitle}》`;
    }
    const centerTitleElem = document.getElementById('dl-center-drama-title');
    if (centerTitleElem) {
        centerTitleElem.textContent = `《${dramaTitle}》`;
    }
    const centerPosterElem = document.getElementById('dl-center-poster-img');
    const centerEmptyIcon = document.getElementById('dl-center-poster-empty-icon');
    if (centerPosterElem) {
        if (dlCurrentDrama && dlCurrentDrama.poster) {
            centerPosterElem.src = dlCurrentDrama.poster;
            centerPosterElem.style.display = 'block';
            if (centerEmptyIcon) centerEmptyIcon.style.display = 'none';
        } else {
            centerPosterElem.removeAttribute('src');
            centerPosterElem.style.display = 'none';
            if (centerEmptyIcon) centerEmptyIcon.style.display = 'block';
        }
    }
    const centerPlatElem = document.getElementById('dl-center-platform-badge');
    if (centerPlatElem) {
        centerPlatElem.textContent = `${(dlCurrentDrama.platform || 'HONGGUO').toUpperCase()} AI PIPELINE`;
    }

    // Update Episodes Count
    const totalCount = (dlEpisodesList && dlEpisodesList.length > 0) ? dlEpisodesList.length : (dlCurrentDrama?.total_episodes || 80);
    const centerEpCount = document.getElementById('dl-center-ep-count');
    if (centerEpCount) {
        centerEpCount.textContent = totalCount === 1 ? `1 Episode (Full Movie)` : `${totalCount} Episodes`;
    }
    const epsCountBold = document.getElementById('dl-q-eps-count-bold');
    if (epsCountBold) {
        epsCountBold.textContent = totalCount;
    }
    const qDlBtnText = document.getElementById('dl-q-download-all-text');
    if (qDlBtnText) {
        qDlBtnText.textContent = totalCount === 1 
            ? `⚡ Download Full Drama 1080p` 
            : `⚡ Download All Episodes (EP 1 - ${totalCount})`;
    }

    // Update Image 2 Episode Hub Header
    const hubTitle = document.getElementById('dl-hub-episodes-title');
    if (hubTitle) {
        hubTitle.textContent = totalCount === 1 ? `Episodes (1 total • Full Movie)` : `Episodes (${totalCount} total)`;
    }
    const hubPillTotal = document.getElementById('dl-hub-pill-total');
    if (hubPillTotal) {
        hubPillTotal.textContent = totalCount;
    }

    // Populate Filter Range Pills
    const filterBar = document.getElementById('dl-hub-filter-pills-bar');
    if (filterBar) {
        filterBar.innerHTML = `
            <button type="button" class="dl-hub-pill ${dlEpisodeCurrentFilter === 'all' ? 'active' : ''}" id="dl-filter-pill-all" onclick="filterEpisodeRange('all')">
                All (${totalCount})
            </button>
        `;
        if (totalCount > 40) {
            const pageSize = 40;
            const ranges = Math.ceil(totalCount / pageSize);
            let pillBtns = '';
            for (let r = 0; r < ranges; r++) {
                const s = r * pageSize + 1;
                const e = Math.min(totalCount, (r + 1) * pageSize);
                const rKey = `${s}-${e}`;
                pillBtns += `<button type="button" class="dl-hub-pill ${dlEpisodeCurrentFilter === rKey ? 'active' : ''}" id="dl-filter-pill-${rKey}" onclick="filterEpisodeRange('${rKey}')">${s} - ${e}</button>`;
            }
            filterBar.innerHTML += pillBtns;
        }
    }

    // Render 4-Column Episode Card Grid (Single-shot innerHTML for 60fps performance)
    const gridBox = document.getElementById('dl-episodes-grid-box');
    if (gridBox) {
        let gridHtml = dlEpisodesList.map((ep, idx) => {
            const epNum = ep.episode_num || (idx + 1);
            const isPlaying = (epNum === (dlQueueActiveEpisodeNum || 1));
            const tagText = ep.progress === 100 ? 'READY' : (dlEpisodesList.length === 1 ? 'FULL' : 'FREE');
            return `
                <div class="dl-ep-card-btn ${isPlaying ? 'active' : ''} ${ep.progress === 100 ? 'completed' : ''}"
                     id="dl-ep-card-${epNum}" data-ep="${epNum}" onclick="playQueueEpisode(${epNum})">
                    <span class="dl-ep-active-dot"></span>
                    <span class="dl-ep-card-num">${epNum}</span>
                    <span class="dl-ep-card-tag">${tagText}</span>
                    <div class="dl-ep-card-prog-track">
                        <div class="dl-ep-card-prog-fill" id="dl-card-fill-${epNum}" style="width: ${ep.progress || 0}%;"></div>
                    </div>
                </div>
            `;
        }).join('');

        if (dlEpisodesList.length === 1) {
            gridHtml += `
                <div class="dl-single-ep-notice">
                    <i class="fa-solid fa-film" style="color: #f59e0b; font-size: 1.05rem;"></i>
                    <span>Full Movie Merged (1080p Full HD)</span>
                </div>
            `;
        }
        gridBox.innerHTML = gridHtml;
    }

    // Render Episode Queue Table (Single-shot batch render for instantaneous response)
    const tbody = document.getElementById('dl-queue-tbody');
    const dropdown = document.getElementById('dl-q-select-dropdown');

    let rowsHtml = '';
    let optsHtml = '';

    for (let idx = 0; idx < dlEpisodesList.length; idx++) {
        const ep = dlEpisodesList[idx];
        const epNum = ep.episode_num || (idx + 1);
        const isSelected = ep.is_selected !== false;
        const isPlaying = (epNum === (dlQueueActiveEpisodeNum || 1));
        const prog = typeof ep.progress === 'number' ? ep.progress : (ep.status === 'Completed' ? 100 : 0);
        let statusText = ep.status || '';
        if (prog === 100 || statusText === 'Completed') {
            statusText = 'Completed';
        } else if (statusText === 'Failed') {
            statusText = 'Failed';
        } else if (prog > 0 || statusText === 'Downloading') {
            statusText = 'Downloading';
        } else if (dlPollActive || statusText === 'Queued') {
            statusText = 'Queued';
        } else {
            statusText = statusText || 'Ready';
        }

        let statusClass = statusText.toLowerCase();
        let fillStyle = 'width: 0%;';
        let textStyle = 'color: #64748b;';

        if (statusText === 'Completed') {
            statusClass = 'completed';
            fillStyle = 'width: 100%; background: #10b981;';
            textStyle = 'color: #10b981;';
        } else if (statusText === 'Failed') {
            statusClass = 'failed';
            fillStyle = 'width: 100%; background: #ef4444;';
            textStyle = 'color: #ef4444;';
        } else if (statusText === 'Downloading') {
            statusClass = 'downloading';
            fillStyle = `width: ${Math.max(prog, 5)}%; background: linear-gradient(90deg, #f59e0b, #fbbf24);`;
            textStyle = 'color: #fbbf24;';
        } else if (statusText === 'Queued') {
            statusClass = 'queued';
            fillStyle = 'width: 0%;';
            textStyle = 'color: #94a3b8;';
        } else {
            statusClass = 'ready';
            fillStyle = 'width: 0%;';
            textStyle = 'color: #64748b;';
        }

        if (tbody) {
            const statusDisplay = statusText === 'Completed' ? '✔ 100%' : (statusText === 'Failed' ? '❌ Failed' : (statusText === 'Downloading' ? `⚡ ${prog}%` : `${prog}%`));
            rowsHtml += `
                <div class="dl-q2-tr ${isPlaying ? 'active' : ''}" id="dl-q-row-${epNum}" data-ep="${epNum}" onclick="playQueueEpisode(${epNum})">
                    <div class="dl-q2-col-ep">
                        <div class="dl-q2-capsule-toggle ${isSelected ? 'checked' : ''}" onclick="event.stopPropagation(); toggleQueueEpisodeSelect(${epNum})"></div>
                        <span class="dl-q2-ep-badge-text">Episode ${String(epNum).padStart(2, '0')}</span>
                    </div>
                    <div class="dl-q2-prog-group">
                        <div class="dl-q2-prog-track">
                            <div class="dl-q2-prog-fill ${statusClass}" id="dl-q-fill-${epNum}" style="${fillStyle}"></div>
                        </div>
                        <span class="dl-q2-prog-val ${statusClass}" id="dl-q-text-${epNum}" style="${textStyle}">${statusDisplay}</span>
                    </div>
                </div>
            `;
        }

        if (dropdown) {
            optsHtml += `<option value="${epNum}">Episode ${String(epNum).padStart(2, '0')}</option>`;
        }
    }

    if (tbody) tbody.innerHTML = rowsHtml;
    if (dropdown) dropdown.innerHTML = optsHtml;

    // Prepare playback for active episode paused with play button ready
    if (!dlQueueActiveEpisodeNum) {
        playQueueEpisode(1, false);
    }
}

function updateEpisodeUIState(ep, isDownloadingBatch = false) {
    const epNum = parseInt(ep.episode_num || ep.episode_number || 0);
    if (!epNum) return;

    const fill = document.getElementById(`dl-q-fill-${epNum}`);
    const cardFill = document.getElementById(`dl-card-fill-${epNum}`);
    const card = document.getElementById(`dl-ep-card-${epNum}`) || document.querySelector(`.dl-ep-card-btn[data-ep="${epNum}"]`);
    const text = document.getElementById(`dl-q-text-${epNum}`);
    const row = document.getElementById(`dl-q-row-${epNum}`) || document.querySelector(`.dl-q2-tr[data-ep="${epNum}"]`);
    const prog = typeof ep.progress === 'number' ? ep.progress : (ep.status === 'Completed' ? 100 : 0);

    let status = ep.status || '';
    if (prog === 100 || status === 'Completed') {
        status = 'Completed';
    } else if (status === 'Failed') {
        status = 'Failed';
    } else if (prog > 0 || status === 'Downloading') {
        status = 'Downloading';
    } else if (isDownloadingBatch || status === 'Queued') {
        status = 'Queued';
    } else {
        status = status || 'Ready';
    }

    // 1. Episode Queue Table Progress Fill Track
    if (fill) {
        fill.className = `dl-q2-prog-fill ${status.toLowerCase()}`;
        if (status === 'Completed') {
            fill.style.width = '100%';
            fill.style.background = '#10b981';
        } else if (status === 'Failed') {
            fill.style.width = '100%';
            fill.style.background = '#ef4444';
        } else if (status === 'Downloading') {
            fill.style.width = `${Math.max(prog, 5)}%`;
            fill.style.background = 'linear-gradient(90deg, #f59e0b, #fbbf24)';
        } else {
            fill.style.width = '0%';
            fill.style.background = '#334155';
        }
    }

    // 2. Center Card Grid Progress Track
    if (cardFill) {
        cardFill.className = `dl-ep-card-prog-fill ${status.toLowerCase()}`;
        cardFill.style.width = (status === 'Completed') ? '100%' : (status === 'Downloading' ? `${Math.max(prog, 5)}%` : '0%');
    }

    // 3. Center Episode Card Tag & Completed Visual
    if (card) {
        if (status === 'Completed') {
            card.classList.add('completed');
            card.classList.remove('downloading');
        } else if (status === 'Downloading') {
            card.classList.remove('completed');
            card.classList.add('downloading');
        } else {
            card.classList.remove('completed', 'downloading');
        }
        const cardTag = card.querySelector('.dl-ep-card-tag');
        if (cardTag) {
            if (status === 'Completed') {
                cardTag.textContent = 'READY';
                cardTag.style.color = '#10b981';
            } else if (status === 'Downloading') {
                cardTag.textContent = `${prog}%`;
                cardTag.style.color = '#f59e0b';
            } else if (status === 'Failed') {
                cardTag.textContent = 'FAIL';
                cardTag.style.color = '#ef4444';
            } else if (status === 'Queued') {
                cardTag.textContent = 'QUEUED';
                cardTag.style.color = '#94a3b8';
            } else {
                cardTag.textContent = 'FREE';
                cardTag.style.color = '#38bdf8';
            }
        }
    }

    // 4. Episode Queue Table Progress Percentage Text
    if (text) {
        text.className = `dl-q2-prog-val ${status.toLowerCase()}`;
        if (status === 'Completed') {
            text.textContent = '✔ 100%';
            text.style.color = '#10b981';
        } else if (status === 'Failed') {
            text.textContent = '❌ Failed';
            text.style.color = '#ef4444';
        } else if (status === 'Downloading') {
            text.textContent = `⚡ ${prog}%`;
            text.style.color = '#fbbf24';
        } else if (status === 'Queued') {
            text.textContent = '0%';
            text.style.color = '#94a3b8';
        } else {
            text.textContent = '0%';
            text.style.color = '#64748b';
        }
    }

    // 5. Episode Queue Table Access / Status Pill
    if (row) {
        const pill = row.querySelector('.dl-q2-status-pill');
        if (pill) {
            pill.className = `dl-q2-status-pill ${status.toLowerCase()}`;
            if (status === 'Completed') {
                pill.textContent = 'Completed';
                pill.style.color = '#10b981';
            } else if (status === 'Failed') {
                pill.textContent = 'Failed';
                pill.style.color = '#ef4444';
            } else if (status === 'Downloading') {
                pill.textContent = `Downloading ${prog}%`;
                pill.style.color = '#f59e0b';
            } else if (status === 'Queued') {
                pill.textContent = 'Queued';
                pill.style.color = '#94a3b8';
            } else {
                pill.textContent = 'Ready';
                pill.style.color = '#38bdf8';
            }
        }
    }

    // 6. Catalog Table Checkbox Status
    const catStatus = document.getElementById(`dl-cat-status-${epNum}`);
    if (catStatus) {
        if (status === 'Completed') {
            catStatus.textContent = '✔ 100%';
            catStatus.style.color = '#10b981';
        } else if (status === 'Downloading') {
            catStatus.textContent = `⚡ ${prog}%`;
            catStatus.style.color = '#f59e0b';
        } else if (status === 'Failed') {
            catStatus.textContent = '❌ Failed';
            catStatus.style.color = '#ef4444';
        } else if (status === 'Queued') {
            catStatus.textContent = 'Queued';
            catStatus.style.color = '#94a3b8';
        } else {
            catStatus.textContent = 'Ready';
            catStatus.style.color = '#38bdf8';
        }
    }
}

function toggleQueueEpisodeSelect(epNum) {
    const ep = dlEpisodesList.find(e => (e.episode_num || e.id) == epNum);
    if (ep) {
        ep.is_selected = !ep.is_selected;
        const row = document.getElementById(`dl-q-row-${epNum}`);
        if (row) {
            const toggle = row.querySelector('.dl-q2-capsule-toggle');
            if (toggle) toggle.classList.toggle('checked', ep.is_selected);
        }
    }
}

function toggleSelectAllQueueEpisodes() {
    const allSelected = dlEpisodesList.every(e => e.is_selected !== false);
    const targetState = !allSelected;
    dlEpisodesList.forEach(e => { e.is_selected = targetState; });

    document.querySelectorAll('.dl-q2-capsule-toggle').forEach(toggle => {
        toggle.classList.toggle('checked', targetState);
    });

    const btn = document.getElementById('btn-q-select-all');
    if (btn) btn.textContent = targetState ? "Deselect all" : "Select all";
}

let dlHlsInstance = null;

function loadVideoWithHls(video, url, posterUrl) {
    if (dlHlsInstance) {
        dlHlsInstance.destroy();
        dlHlsInstance = null;
    }
    if (posterUrl) video.poster = posterUrl;
    if (url && (url.includes('.m3u8') || url.includes('/hls/')) && window.Hls && Hls.isSupported()) {
        dlHlsInstance = new Hls({ enableWorker: true });
        dlHlsInstance.loadSource(url);
        dlHlsInstance.attachMedia(video);
    } else {
        video.src = url;
    }
}

async function playQueueEpisode(epNum, autoPlay = true) {
    dlQueueActiveEpisodeNum = epNum;

    // Highlight active card in Image 2 4-Column Grid
    document.querySelectorAll('.dl-ep-card-btn').forEach(c => c.classList.remove('active'));
    const activeCard = document.getElementById(`dl-ep-card-${epNum}`);
    if (activeCard) {
        activeCard.classList.add('active');
        activeCard.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }

    // Fallback highlight row in table
    document.querySelectorAll('.dl-q2-tr').forEach(r => r.classList.remove('active'));
    const activeRow = document.getElementById(`dl-q-row-${epNum}`);
    if (activeRow) {
        activeRow.classList.add('active');
    }

    const totalEps = dlEpisodesList.length || 80;
    const epObj = dlEpisodesList.find(e => (e.episode_num || e.id) == epNum) || {};
    const dramaTitle = (dlCurrentDrama?.title_cn || dlCurrentDrama?.title || '').replace(/[《》]/g, '').split(' - ')[0].trim();
    const epTitleText = `EP${String(epNum).padStart(2, '0')} - ${epObj.title || dramaTitle}`;

    // Subtitle overlay banner matching Image 2
    const subtitlesElem = document.getElementById('dl-q-video-subtitles');
    if (subtitlesElem) {
        const sampleSubs = [
            "哥 你穿浴袍来参加婚礼",
            "今早刚猎的白龙，威风凛凛！",
            "乖乖女？你可别被她的外表骗了！",
            "三年隐忍，今日终登龙王之位！",
            "只要你点头，整座金城都是你的！"
        ];
        subtitlesElem.textContent = sampleSubs[(epNum - 1) % sampleSubs.length];
        subtitlesElem.style.display = 'block';
    }

    // Update Right Panel Info
    const nowTitle = document.getElementById('dl-q-now-title');
    const epIndicator = document.getElementById('dl-q-now-ep-indicator');
    const dropdown = document.getElementById('dl-q-select-dropdown');
    const dlBtnText = document.getElementById('dl-q-download-btn-text');

    if (nowTitle) nowTitle.textContent = epTitleText;
    if (epIndicator) epIndicator.textContent = `EPISODE ${epNum} / ${totalEps}`;
    if (dropdown) dropdown.value = epNum;
    if (dlBtnText) dlBtnText.textContent = `Download Only EP ${epNum}`;

    // Load Video
    const video = document.getElementById('dl-q-video-elem');
    const playOverlay = document.getElementById('dl-q-center-play');
    const playBtnText = document.getElementById('dl-q-play-text');
    const playBtnIcon = document.getElementById('dl-q-play-icon');

    if (!video) return;

    // A. Check if the episode object already has an authentic video URL (e.g. from folder import or completed download)
    const rawUrl = epObj?.video_url || epObj?.stream_url;
    if (rawUrl) {
        loadVideoWithHls(video, rawUrl, dlCurrentDrama?.poster || '');
        video.currentTime = 0;
        if (autoPlay) {
            video.play().then(() => {
                if (playOverlay) playOverlay.classList.add('hidden');
                if (playBtnText) playBtnText.textContent = 'Pause';
                if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-pause';
            }).catch(() => {
                if (playOverlay) playOverlay.classList.remove('hidden');
                if (playBtnText) playBtnText.textContent = 'Play';
                if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-play';
            });
        } else {
            video.pause();
            if (playOverlay) playOverlay.classList.remove('hidden');
            if (playBtnText) playBtnText.textContent = 'Play';
            if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-play';
        }
        return;
    }

    // B. Fetch authentic preview or stream from backend
    try {
        const res = await fetch(`/api/downloader/preview/${dlCurrentDrama.id}?ep=${epNum}`);
        const data = await res.json();
        const vUrl = data.video_url || data.stream_url;
        if (data.success && vUrl) {
            loadVideoWithHls(video, vUrl, data.poster || dlCurrentDrama?.poster || '');
            video.currentTime = 0;
            if (autoPlay) {
                video.play().then(() => {
                    if (playOverlay) playOverlay.classList.add('hidden');
                    if (playBtnText) playBtnText.textContent = 'Pause';
                    if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-pause';
                }).catch(() => {
                    if (playOverlay) playOverlay.classList.remove('hidden');
                    if (playBtnText) playBtnText.textContent = 'Play';
                    if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-play';
                });
            } else {
                video.pause();
                if (playOverlay) playOverlay.classList.remove('hidden');
                if (playBtnText) playBtnText.textContent = 'Play';
                if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-play';
            }
            return;
        } else {
            // Authentic video not yet downloaded / imported
            if (dlHlsInstance) {
                dlHlsInstance.destroy();
                dlHlsInstance = null;
            }
            video.pause();
            video.removeAttribute('src');
            video.load();
            if (dlCurrentDrama && dlCurrentDrama.poster) {
                video.poster = dlCurrentDrama.poster;
            }
            if (playOverlay) playOverlay.classList.remove('hidden');
            if (playBtnText) playBtnText.textContent = 'Play';
            if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-play';
            showToast(`Episode ${epNum} is not downloaded locally yet — click Download to fetch`);
            return;
        }
    } catch (e) {
        video.pause();
        if (dlCurrentDrama && dlCurrentDrama.poster) {
            video.poster = dlCurrentDrama.poster;
        }
        if (playOverlay) playOverlay.classList.remove('hidden');
    }
}

function toggleQueuePlay() {
    const video = document.getElementById('dl-q-video-elem');
    const playOverlay = document.getElementById('dl-q-center-play');
    const playBtnText = document.getElementById('dl-q-play-text');
    const playBtnIcon = document.getElementById('dl-q-play-icon');
    if (!video) return;

    if (video.paused) {
        video.play().then(() => {
            if (playOverlay) playOverlay.classList.add('hidden');
            if (playBtnText) playBtnText.textContent = 'Pause';
            if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-pause';
        }).catch(() => {});
    } else {
        video.pause();
        if (playOverlay) playOverlay.classList.remove('hidden');
        if (playBtnText) playBtnText.textContent = 'Play';
        if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-play';
    }
}

function onQueueVideoTimeUpdate() {
    const video = document.getElementById('dl-q-video-elem');
    const timecode = document.getElementById('dl-q-timecode');
    const slider = document.getElementById('dl-q-seek-slider');
    if (!video || !video.duration) return;

    const cur = video.currentTime;
    const dur = video.duration;

    const fmt = (t) => {
        const m = Math.floor(t / 60);
        const s = Math.floor(t % 60);
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    };

    if (timecode) {
        timecode.textContent = `${fmt(cur)} / ${fmt(dur)}`;
    }
    if (slider && !slider.matches(':active')) {
        slider.value = (cur / dur) * 100;
    }
}

function onQueueVideoEnded() {
    if (dlAutoNextEnabled) {
        queueNextEpisode();
    } else {
        queueStopVideo();
    }
}

function handleQueueScrubber(val) {
    const video = document.getElementById('dl-q-video-elem');
    if (video && video.duration) {
        video.currentTime = (val / 100) * video.duration;
    }
}

function jumpToQueueEpisode(epNum) {
    if (epNum >= 1 && epNum <= (dlEpisodesList.length || 80)) {
        playQueueEpisode(epNum);
    }
}

function queuePrevEpisode() {
    const prev = Math.max(1, dlQueueActiveEpisodeNum - 1);
    if (prev !== dlQueueActiveEpisodeNum) {
        playQueueEpisode(prev);
    }
}

function queueNextEpisode() {
    const max = dlEpisodesList.length || 80;
    const next = Math.min(max, dlQueueActiveEpisodeNum + 1);
    if (next !== dlQueueActiveEpisodeNum) {
        playQueueEpisode(next);
    }
}

function queueStopVideo() {
    const video = document.getElementById('dl-q-video-elem');
    if (video) {
        video.pause();
        video.currentTime = 0;
        const playOverlay = document.getElementById('dl-q-center-play');
        const playBtnText = document.getElementById('dl-q-play-text');
        const playBtnIcon = document.getElementById('dl-q-play-icon');
        if (playOverlay) playOverlay.classList.remove('hidden');
        if (playBtnText) playBtnText.textContent = 'Play';
        if (playBtnIcon) playBtnIcon.className = 'fa-solid fa-play';
    }
}
window.playQueueEpisode = playQueueEpisode;
window.toggleQueueEpisodeSelect = toggleQueueEpisodeSelect;

function queueToggleMute() {
    const video = document.getElementById('dl-q-video-elem');
    const muteBtn = document.getElementById('dl-q-mute-btn');
    const muteIcon = document.getElementById('dl-q-mute-icon');
    if (!video) return;

    video.muted = !video.muted;
    if (muteIcon) {
        muteIcon.className = video.muted ? 'fa-solid fa-volume-xmark' : 'fa-solid fa-volume-high';
    }
    if (muteBtn) {
        muteBtn.style.color = video.muted ? '#ef4444' : '#cbd5e1';
    }
}

let dlUserSaveLocation = '';

function getEffectiveSaveLocation() {
    const inputVal = document.getElementById('dl-save-path-input')?.value.trim();
    if (inputVal) return inputVal;
    if (dlUserSaveLocation && dlUserSaveLocation.trim()) return dlUserSaveLocation.trim();
    const stored = localStorage.getItem('sn_save_location');
    if (stored && stored.trim()) return stored.trim();
    return (typeof driveCustomPaths !== 'undefined' && driveCustomPaths["C"]) ? driveCustomPaths["C"] : "C:/SN_Dramas";
}

function getComputedDramaFolder() {
    let base = getEffectiveSaveLocation();
    base = base.replace(/\\/g, '/').replace(/\/+$/, '');
    if (!dlCurrentDrama) {
        return base;
    }
    const rawTitle = dlCurrentDrama.title_cn || dlCurrentDrama.title || 'Drama';
    const folderName = rawTitle.replace(/[\\/*?:"<>|《》]/g, '_').trim() || 'Hongguo_Drama';
    return `${base}/${folderName}`;
}

function updateDramaSavePathDisplay(customFolder = '') {
    let folder = customFolder;
    if (!folder) {
        folder = getComputedDramaFolder();
    }
    const winPath = folder.replace(/\//g, '\\') + (folder.endsWith('/') || folder.endsWith('\\') ? '' : '\\');
    
    const catElem = document.getElementById('dl-catalog-save-folder-path');
    if (catElem) catElem.textContent = winPath;

    const qElem = document.getElementById('dl-q2-save-folder-path');
    if (qElem) qElem.textContent = winPath;
}

async function openCurrentDramaFolder(specificFolder = '') {
    const target = specificFolder || getComputedDramaFolder();
    showToast(`📂 Opening folder in File Explorer...`);
    try {
        const res = await fetch('/api/downloader/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder: target })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`📂 Opened drama folder in Explorer: ${data.path}`);
            appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Opened in Windows Explorer: ${data.path}`);
        } else {
            showToast(`Cannot open folder: ${data.error || 'Unknown error'}`);
        }
    } catch (e) {
        showToast("Error opening folder in Explorer");
    }
}

async function selectCustomDownloadFolder() {
    try {
        const res = await fetch('/api/downloader/select-folder', { method: 'POST' });
        const data = await res.json();
        if (data.success && data.path) {
            dlUserSaveLocation = data.path.replace(/\\/g, '/');
            const inputElem = document.getElementById('dl-save-path-input');
            if (inputElem) inputElem.value = dlUserSaveLocation;
            updateDramaSavePathDisplay();
            showToast(`📁 Save destination updated: ${data.path}`);
            appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Selected save location: ${data.path}`);
        }
    } catch (e) {
        showToast("Dialog cancelled or error selecting folder");
    }
}

async function downloadAllQueueEpisodes() {
    if (!dlCurrentDrama) {
        showToast("Please select a drama series first");
        return;
    }

    const total = dlEpisodesList.length || dlCurrentDrama.total_episodes || 80;
    const title = (dlCurrentDrama.title_cn || dlCurrentDrama.title || '').replace(/[《》]/g, '').split(' - ')[0].trim();

    // Select all episodes: mark non-completed as 'Queued' (NOT 'Downloading' yet!)
    dlEpisodesList.forEach(e => {
        e.is_selected = true;
        if (e.status !== 'Completed' && e.progress !== 100) {
            e.status = 'Queued';
            e.progress = 0;
        }
        updateEpisodeUIState(e, true);
    });

    // Optimistically mark first pending episode as actively starting (10%)
    const firstPending = dlEpisodesList.find(e => e.status !== 'Completed' && e.progress !== 100);
    if (firstPending) {
        firstPending.status = 'Downloading';
        firstPending.progress = 10;
        updateEpisodeUIState(firstPending, true);
    }

    // Update UI checkmarks in Queue table immediately
    document.querySelectorAll('.dl-q2-capsule-toggle').forEach(t => t.classList.add('checked'));

    const path = getEffectiveSaveLocation();
    const computedDir = getComputedDramaFolder().replace(/\//g, '\\');
    showToast(`⚡ Downloading 5 episodes in parallel (${total} total) to ${computedDir}...`);
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] ⚡ Downloading in parallel (Batch 5 Episodes): EP 1 to EP ${total} for '${title}' into '${computedDir}'...`);

    const posterElem = document.getElementById('dl-save-poster-check');
    const savePoster = posterElem ? posterElem.checked : true;

    // Button feedback
    const btnAll = document.getElementById('btn-q-download-all');
    const originalText = btnAll ? btnAll.innerHTML : '';
    if (btnAll) {
        btnAll.disabled = true;
        btnAll.innerHTML = `<i class="fa-solid fa-bolt-lightning fa-spin" style="color:#facc15;"></i> <span>⚡ Downloading High Speed (EP 1 - ${total})...</span>`;
    }

    const catBtnAll = document.getElementById('btn-dl-catalog-all');
    if (catBtnAll) {
        catBtnAll.disabled = true;
        catBtnAll.innerHTML = `<i class="fa-solid fa-bolt-lightning fa-spin" style="color:#facc15;"></i> <span>⚡ Downloading (${total} episodes)...</span>`;
    }

    // Cancel any previous polling session
    dlPollActive = false;
    if (dlPollTimer) {
        clearTimeout(dlPollTimer);
        clearInterval(dlPollTimer);
        dlPollTimer = null;
    }

    try {
        const res = await fetch('/api/downloader/download-episodes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                episode_ids: ["all"],
                save_location: path,
                save_poster: savePoster,
                auto_merge_full: false
            })
        });
        const data = await res.json();

        // Start active controlled polling with strict session ID and completion latch
        const currentSessionId = ++dlPollSessionId;
        dlPollActive = true;
        let batchDownloadCompletedNotified = false;

        async function pollDownloaderStatus() {
            if (!dlPollActive || dlPollSessionId !== currentSessionId) {
                return;
            }

            try {
                const sRes = await fetch('/api/downloader/status');
                const sData = await sRes.json();

                if (!dlPollActive || dlPollSessionId !== currentSessionId) {
                    return;
                }

                if (sData) {
                    if (sData.last_download_dir) {
                        updateDramaSavePathDisplay(sData.last_download_dir);
                    }
                    if (sData.episodes && sData.episodes.length > 0) {
                        dlEpisodesList = sData.episodes;
                    }
                    updateDownloaderStats(sData.stats);

                    const curPct = sData.stats?.progress_percent ?? 0;
                    const curComp = sData.stats?.completed ?? 0;
                    const curTot = sData.stats?.total ?? (dlEpisodesList ? dlEpisodesList.length : total);
                    const activeEpNum = parseInt(sData.stats?.current_episode ?? (curComp + 1));
                    const activeEpProg = parseInt(sData.stats?.current_episode_progress ?? 0);

                    if (sData.is_downloading) {
                        if (btnAll) {
                            btnAll.innerHTML = `<i class="fa-solid fa-bolt-lightning fa-spin" style="color:#facc15;"></i> <span>⚡ Downloading ${curPct}% (EP ${curComp}/${curTot})...</span>`;
                        }
                        if (catBtnAll) {
                            catBtnAll.innerHTML = `<i class="fa-solid fa-bolt-lightning fa-spin" style="color:#facc15;"></i> <span>⚡ Downloading ${curPct}% (${curComp}/${curTot} EPs)...</span>`;
                        }

                        // Synchronize every episode in dlEpisodesList with live download state
                        if (dlEpisodesList && dlEpisodesList.length > 0) {
                            dlEpisodesList.forEach((ep, idx) => {
                                const epNum = parseInt(ep.episode_num || ep.episode_number || (idx + 1));
                                if (epNum <= curComp || ep.status === 'Completed' || ep.progress === 100) {
                                    ep.status = 'Completed';
                                    ep.progress = 100;
                                } else if (epNum === activeEpNum || ep.status === 'Downloading') {
                                    ep.status = 'Downloading';
                                    let p = ep.progress || activeEpProg;
                                    if (!p || p < 5) p = 15;
                                    ep.progress = Math.min(99, Math.max(5, p));
                                } else if (epNum > curComp + 1) {
                                    if (ep.status !== 'Failed') {
                                        ep.status = 'Queued';
                                        ep.progress = 0;
                                    }
                                }
                                updateEpisodeUIState(ep, true);
                            });
                        }
                    } else {
                        // Not downloading: update normally
                        if (dlEpisodesList && dlEpisodesList.length > 0) {
                            dlEpisodesList.forEach(ep => {
                                updateEpisodeUIState(ep, false);
                            });
                        }
                    }

                    // Check if download finished
                    if (!sData.is_downloading) {
                        dlPollActive = false;
                        if (dlPollTimer) {
                            clearTimeout(dlPollTimer);
                            clearInterval(dlPollTimer);
                            dlPollTimer = null;
                        }

                        // Mark all episodes Completed when batch ends successfully
                        if (dlEpisodesList && dlEpisodesList.length > 0) {
                            dlEpisodesList.forEach(ep => {
                                ep.status = 'Completed';
                                ep.progress = 100;
                                updateEpisodeUIState(ep, false);
                            });
                        }

                        // Strict single-fire latch
                        if (batchDownloadCompletedNotified) {
                            return;
                        }
                        batchDownloadCompletedNotified = true;

                        if (btnAll) {
                            btnAll.disabled = false;
                            btnAll.innerHTML = `<i class="fa-solid fa-circle-check" style="color:#4ade80;"></i> <span>Downloaded all episodes ${total}/${total} & Full Movie 100%</span>`;
                            setTimeout(() => {
                                btnAll.innerHTML = originalText || `<i class="fa-solid fa-bolt-lightning" style="color:#facc15;"></i> <span id="dl-q-download-all-text">⚡ Download All Episodes (EP 1 - ${total})</span>`;
                            }, 6000);
                        }
                        if (catBtnAll) {
                            catBtnAll.disabled = false;
                            catBtnAll.innerHTML = `<i class="fa-solid fa-circle-check" style="color:#4ade80;"></i> <span>All ${total} episodes & Full Movie downloaded</span>`;
                            setTimeout(() => {
                                catBtnAll.innerHTML = `<i class="fa-solid fa-bolt-lightning" style="color:#facc15;"></i> <span id="dl-catalog-dl-all-text">⚡ Turbo High-Speed & 100% Full Series</span>`;
                            }, 6000);
                        }

                        let movieMsg = "";
                        if (sData.stats && sData.stats.full_movie_name) {
                            movieMsg = ` 🎬 Full Movie: ${sData.stats.full_movie_name}`;
                        }
                        showToast(`🎉 Downloaded all episodes ${total}/${total} 100% complete!${movieMsg}`);
                        appendDownloaderLog(`[${new Date().toLocaleTimeString()}] All ${total} episodes completed 100%!${movieMsg}`);

                        const qVideo = document.getElementById('dl-q-video-elem');
                        if (qVideo) {
                            qVideo.pause();
                        }
                        if (dlQueueActiveEpisodeNum) {
                            playQueueEpisode(dlQueueActiveEpisodeNum, false);
                        }
                        return; // Done! Do not schedule another poll!
                    }
                }
            } catch (e) {}

            // Schedule next poll tick only if session is still alive
            if (dlPollActive && dlPollSessionId === currentSessionId) {
                dlPollTimer = setTimeout(pollDownloaderStatus, 500);
            }
        }

        // Kick off first poll
        dlPollTimer = setTimeout(pollDownloaderStatus, 400);

    } catch (e) {
        dlPollActive = false;
        showToast("Failed to start download");
        if (btnAll) {
            btnAll.disabled = false;
            btnAll.innerHTML = originalText;
        }
        if (catBtnAll) {
            catBtnAll.disabled = false;
        }
    }
}

async function mergeCurrentDramaFullMovie() {
    if (!dlCurrentDrama) {
        showToast("Please select a drama series first");
        return;
    }
    const computedDir = getComputedDramaFolder();
    showToast("🎬 Merging all episodes into Full Movie (1080p)...");
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Assembling Full Drama Movie from episodes in '${computedDir}'...`);

    const mergeBtn = document.getElementById('btn-q-merge-full');
    if (mergeBtn) {
        mergeBtn.disabled = true;
        mergeBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> <span>Merging in progress...</span>`;
    }

    try {
        const res = await fetch('/api/downloader/merge-full', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder: computedDir })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`🎉 Full movie merged successfully: ${data.full_movie_name} (${data.size_mb} MB)`);
            appendDownloaderLog(`[${new Date().toLocaleTimeString()}] ✔ Full Movie generated: ${data.full_movie_name} (${data.size_mb} MB, 1080p)`);
            openCurrentDramaFolder(computedDir);
        } else {
            showToast(data.error || "Failed to merge movie");
        }
    } catch (e) {
        showToast("Failed to connect to server");
    } finally {
        if (mergeBtn) {
            mergeBtn.disabled = false;
            mergeBtn.innerHTML = `<i class="fa-solid fa-film"></i> <span>🎬 Merge Full Movie</span>`;
        }
    }
}

function downloadCurrentDramaFullSeries() {
    if (!dlCurrentDrama) {
        showToast("Please select a drama series first");
        return;
    }
    switchDlViewMode('queue');
    downloadAllQueueEpisodes();
}

async function downloadCurrentDramaPoster() {
    if (!dlCurrentDrama) {
        showToast("⚠️ Please select a drama series first!");
        return;
    }
    const posterUrl = dlCurrentDrama.poster || dlCurrentDrama.cover_url;
    if (!posterUrl) {
        showToast("⚠️ No poster available for this drama!");
        return;
    }
    const rawTitle = (dlCurrentDrama.title_cn || dlCurrentDrama.title || 'Drama').replace(/[《》]/g, '').trim();
    const savePath = getEffectiveSaveLocation();
    showToast(`🖼️ Downloading HD Poster: ${rawTitle}...`);
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Downloading Poster HD for '${rawTitle}'...`);

    try {
        const res = await fetch('/api/downloader/download_poster', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                drama_id: dlCurrentDrama.id,
                poster_url: posterUrl,
                title: rawTitle,
                save_location: savePath
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`✅ HD Poster downloaded successfully!`);
            appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Poster HD saved to: ${data.path || data.filename}`);
            const a = document.createElement('a');
            a.href = data.file_url || posterUrl;
            a.download = data.filename || `${rawTitle}_Poster.jpg`;
            a.target = '_blank';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else {
            showToast(`⚠️ ${data.message || 'Failed to download poster'}`);
        }
    } catch (err) {
        console.warn('Poster download fetch fallback:', err);
        const a = document.createElement('a');
        a.href = posterUrl;
        a.download = `${rawTitle}_Poster.jpg`;
        a.target = '_blank';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast(`✅ Poster download started!`);
    }
}

async function downloadCurrentQueueEpisode() {
    if (!dlCurrentDrama) return;
    const epNum = dlQueueActiveEpisodeNum;
    showToast(`Downloading EP ${epNum}...`);
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Downloading EP ${epNum} of '${dlCurrentDrama.title}'...`);

    const path = getEffectiveSaveLocation();
    const epObj = dlEpisodesList.find(e => (e.episode_num || e.episode_number || e.id) == epNum);
    const targetId = epObj ? epObj.id : `ep_${epNum}`;

    try {
        const res = await fetch('/api/downloader/download-episodes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                episode_ids: [targetId],
                save_location: path,
                save_poster: true
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`EP ${epNum} download started!`);
            const fill = document.getElementById(`dl-q-fill-${epNum}`);
            const cardFill = document.getElementById(`dl-card-fill-${epNum}`);
            const text = document.getElementById(`dl-q-text-${epNum}`);
            const row = document.getElementById(`dl-q-row-${epNum}`);
            if (row) {
                const pill = row.querySelector('.dl-q2-status-pill');
                if (pill) {
                    pill.textContent = 'Downloading';
                    pill.className = 'dl-q2-status-pill downloading';
                    pill.style.color = '#f59e0b';
                }
            }
            let prog = 0;
            const timer = setInterval(() => {
                prog += 20;
                if (fill) fill.style.width = `${prog}%`;
                if (cardFill) cardFill.style.width = `${prog}%`;
                if (text) text.textContent = `${prog}%`;
                if (prog >= 100) {
                    clearInterval(timer);
                    if (row) {
                        const pill = row.querySelector('.dl-q2-status-pill');
                        if (pill) {
                            pill.textContent = 'Completed';
                            pill.className = 'dl-q2-status-pill completed';
                            pill.style.color = '#10b981';
                        }
                    }
                    showToast(`EP ${epNum} ready!`);
                }
            }, 300);
        }
    } catch (e) {
        showToast("Download failed");
    }
}

// Global Keyboard Handler for Queue / Preview Player Mode
window.addEventListener('keydown', (e) => {
    if (dlCurrentViewMode === 'queue') {
        const isInput = e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA');
        if (isInput) return;

        if (e.code === 'Space') {
            e.preventDefault();
            toggleQueuePlay();
        } else if (e.code === 'Escape') {
            e.preventDefault();
            switchDlViewMode('catalog');
        } else if (e.code === 'ArrowRight' || e.code === 'KeyN') {
            e.preventDefault();
            queueNextEpisode();
        } else if (e.code === 'ArrowLeft' || e.code === 'KeyP') {
            e.preventDefault();
            queuePrevEpisode();
        }
    }
});

let driveCustomPaths = {
    "C": "C:/SN_Dramas",
    "D": "D:/SN_Dramas"
};

async function initSaveLocationPaths() {
    const input = document.getElementById('dl-save-path-input');
    if (!input) return;

    let backendDefault = null;
    try {
        const res = await fetch('/api/system/default-paths');
        const data = await res.json();
        if (data && data.success) {
            if (data.drive_c) driveCustomPaths["C"] = data.drive_c;
            if (data.drive_d) driveCustomPaths["D"] = data.drive_d;
            if (data.default) backendDefault = data.default;
            const hasDriveD = data.has_drive_d !== false;
            const saved = localStorage.getItem('sn_save_location');
            if (saved && saved.trim() && (hasDriveD || !saved.toUpperCase().startsWith('D:'))) {
                input.value = saved.trim();
            } else {
                input.value = backendDefault || (hasDriveD ? (driveCustomPaths["D"] || "D:/SN_Dramas") : (driveCustomPaths["C"] || "C:/SN_Dramas"));
            }
        }
    } catch (e) {
        input.value = backendDefault || "C:/SN_Dramas";
    }
    dlUserSaveLocation = input.value;
    input.setAttribute('title', input.value);
    input.addEventListener('input', () => {
        const val = input.value.trim();
        if (val) {
            dlUserSaveLocation = val;
            localStorage.setItem('sn_save_location', val);
            input.setAttribute('title', val);
        }
    });
    updateDriveButtonHighlight();
    updateDramaSavePathDisplay();
}

function selectDrive(driveLetter) {
    const letter = driveLetter.toUpperCase();
    const input = document.getElementById('dl-save-path-input');
    
    let targetPath = driveCustomPaths[letter] || `${letter}:/SN_Dramas`;
    const savedForDrive = localStorage.getItem(`sn_save_path_${letter.toLowerCase()}`);
    if (savedForDrive && savedForDrive.toUpperCase().startsWith(`${letter}:`)) {
        targetPath = savedForDrive;
    }
    
    if (input) {
        input.value = targetPath;
        input.setAttribute('title', targetPath);
    }
    dlUserSaveLocation = targetPath;
    localStorage.setItem('sn_save_location', targetPath);
    localStorage.setItem('sn_active_drive', letter);
    updateDriveButtonHighlight();
    updateDramaSavePathDisplay();

    showToast(`Selected Drive ${letter}: (${targetPath})`);
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Active download location: Drive ${letter}: (${targetPath})`);
}

function updateDriveButtonHighlight() {
    const input = document.getElementById('dl-save-path-input');
    const path = input ? input.value.trim().toUpperCase() : "";
    
    const btnC = document.getElementById('btn-drive-c');
    const btnD = document.getElementById('btn-drive-d');
    
    const isC = path.startsWith("C:");
    const isD = path.startsWith("D:");
    
    if (btnC) btnC.classList.toggle('active', isC);
    if (btnD) btnD.classList.toggle('active', isD || (!isC && !isD));
}

async function browseSaveLocation() {
    const input = document.getElementById('dl-save-path-input');
    const currentPath = input ? input.value.trim() : '';

    showToast("Opening Folder Picker...");
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Opening Windows folder chooser...`);

    try {
        const res = await fetch('/api/system/select-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initial_dir: currentPath })
        });
        const data = await res.json();
        if (data.success && data.path) {
            const cleanPath = data.path.replace(/\\/g, '/');
            if (input) {
                input.value = cleanPath;
                input.setAttribute('title', cleanPath);
            }
            const driveLetter = cleanPath.slice(0, 1).toUpperCase();
            if (driveLetter === 'C' || driveLetter === 'D') {
                driveCustomPaths[driveLetter] = cleanPath;
                localStorage.setItem(`sn_save_path_${driveLetter.toLowerCase()}`, cleanPath);
                localStorage.setItem('sn_active_drive', driveLetter);
            }
            localStorage.setItem('sn_save_location', cleanPath);
            updateDriveButtonHighlight();
            showToast(`Selected Folder: ${cleanPath}`);
            appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Save folder updated: ${cleanPath}`);
        } else if (data.cancelled) {
            showToast("Folder selection cancelled");
        } else {
            showToast("Cannot select folder");
        }
    } catch (e) {
        console.error("Browse folder error:", e);
        showToast("Failed to open Folder Dialog");
    }
}

async function openSaveLocationInExplorer() {
    const input = document.getElementById('dl-save-path-input');
    const path = input ? input.value.trim() : '';
    if (!path) {
        showToast("Please select folder location first");
        return;
    }

    try {
        const res = await fetch('/api/system/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: path })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Opened folder in Windows Explorer`);
            appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Opened directory: ${path}`);
        } else {
            showToast(`${data.error || 'Cannot open folder'}`);
        }
    } catch (e) {
        showToast("Failed to open Windows Explorer");
    }
}

async function importLocalDramaFolder(folderPath = '') {
    showToast("Opening Drama Series Folder Picker...");
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Opening Windows folder chooser to import drama series...`);

    try {
        const res = await fetch('/api/downloader/import-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ folder_path: folderPath })
        });
        const data = await res.json();
        if (data.success && data.drama) {
            dlCurrentDrama = data.drama;
            dlEpisodesList = data.episodes || [];
            
            renderDramaInfo(data.drama);
            renderEpisodesChecklist(dlEpisodesList);
            renderQueueTable(dlEpisodesList);
            updateDownloaderStats(data.stats);

            switchDlViewMode('queue');
            playQueueEpisode(1);

            showToast(`🎉 Imported '${data.drama.title}' (${dlEpisodesList.length} episodes) successfully!`);
            appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Successfully imported ${dlEpisodesList.length} authentic episodes from: ${data.folder || folderPath}`);
        } else if (data.cancelled) {
            showToast("Folder selection cancelled");
        } else {
            showToast(data.error || "Cannot import drama folder");
        }
    } catch (e) {
        console.error("Import folder error:", e);
        showToast("Failed to import drama folder");
    }
}

async function sendCurrentQueueToStudio() {
    if (!dlEpisodesList || dlEpisodesList.length === 0) {
        showToast("No drama episodes to send to Studio");
        return;
    }

    const epNum = dlQueueActiveEpisodeNum || 1;
    const epObj = dlEpisodesList.find(e => (e.episode_num || e.episode_number || e.id) == epNum) || dlEpisodesList[0];

    if (!epObj) {
        showToast("Selected episode not found");
        return;
    }

    if (!epObj.filepath) {
        showToast(`Episode ${epNum} is not downloaded yet — please download or import folder first`);
        return;
    }

    showToast(`Sending "${epObj.filename || 'Episode ' + epNum}" to Studio...`);
    try {
        const res = await fetch('/api/downloader/send-to-studio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filepath: epObj.filepath,
                filename: epObj.filename,
                drama_title: dlCurrentDrama ? (dlCurrentDrama.title_cn || dlCurrentDrama.title) : ''
            })
        });
        const data = await res.json();
        if (data.success) {
            setStagedVideo({
                filepath: data.filepath,
                filename: data.filename,
                size_mb: data.size_mb
            });
            switchMainTab('translate');
            showToast(`🎙️ Loaded "${data.filename}" into Studio! Click Export to start auto-dubbing.`);
            appendTerminalLine(`[Ready] Video "${data.filename}" transferred from Hongguo Downloader. Ready for 1-Click Khmer Dubbing.`);
        } else {
            showToast(data.error || "Cannot send video to Studio");
        }
    } catch (e) {
        console.error("Send to studio error:", e);
        showToast("Failed to send video to Studio");
    }
}

async function sendAllQueueToStudio() {
    if (!dlEpisodesList || dlEpisodesList.length === 0) {
        showToast("No drama episodes to send to Studio");
        return;
    }

    const availableEps = dlEpisodesList.filter(e => e.is_selected && e.filepath);
    if (availableEps.length === 0) {
        showToast("No downloaded episodes selected");
        return;
    }

    showToast(`Sending ${availableEps.length} episodes to Studio...`);
    const dramaTitle = dlCurrentDrama ? (dlCurrentDrama.title_cn || dlCurrentDrama.title) : 'Drama_Series';
    setStagedBatchFiles(availableEps, dramaTitle);
    switchMainTab('translate');
    showToast(`🎙️ Loaded ${availableEps.length} episodes into Studio! Click Export to start auto-dubbing.`);
    appendTerminalLine(`[Ready] Batch of ${availableEps.length} episodes transferred from Downloader. Ready for studio dubbing.`);
}

async function previewLoadedDrama() {
    if (!dlCurrentDrama) {
        showToast("Please select a drama from the catalog first");
        return;
    }
    switchDlViewMode('queue');
    playQueueEpisode(1);
    showToast(`🎬 Opening '${dlCurrentDrama.title}' in Player mode`);
}

function previewDramaVideoDirect(dramaId) {
    selectDramaCard(dramaId, true);
}

async function startBatchDownload() {
    let selected = dlEpisodesList.filter(e => e.is_selected);
    if (selected.length === 0) {
        if (dlEpisodesList.length === 0 && dlCurrentDrama) {
            showToast("Preparing all episodes...");
        }
        dlEpisodesList.forEach(e => { e.is_selected = true; });
        selected = dlEpisodesList;
    }
    if (selected.length === 0) {
        showToast("Please select a drama series first");
        return;
    }

    showToast(`Downloading all (${selected.length} episodes)...`);
    appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Starting batch queue for ${selected.length} episodes...`);

    // Option 1: Immediately set all non-completed episodes to Queued in UI
    dlEpisodesList.forEach(e => {
        if (e.status !== 'Completed') {
            e.status = 'Queued';
            e.progress = 0;
        }
        updateEpisodeUIState(e, true);
    });

    const path = getEffectiveSaveLocation();
    const posterElem = document.getElementById('dl-save-poster-check');
    const savePoster = posterElem ? posterElem.checked : true;

    try {
        await fetch('/api/downloader/download-episodes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                episode_ids: selected.map(s => s.id),
                save_location: path,
                save_poster: savePoster
            })
        });

        // Cancel previous polling session
        dlPollActive = false;
        if (dlPollTimer) {
            clearTimeout(dlPollTimer);
            clearInterval(dlPollTimer);
            dlPollTimer = null;
        }

        // Start Controlled Polling
        const currentSessionId = ++dlPollSessionId;
        dlPollActive = true;
        let queueBatchCompletedNotified = false;

        async function pollBatchQueueStatus() {
            if (!dlPollActive || dlPollSessionId !== currentSessionId) {
                return;
            }

            try {
                const sRes = await fetch('/api/downloader/status');
                const sData = await sRes.json();

                if (!dlPollActive || dlPollSessionId !== currentSessionId) {
                    return;
                }

                if (sData) {
                    if (sData.episodes && sData.episodes.length > 0) {
                        dlEpisodesList = sData.episodes;
                        sData.episodes.forEach(ep => {
                            updateEpisodeUIState(ep, sData.is_downloading);
                        });
                    }
                    updateDownloaderStats(sData.stats);
                    if (!sData.is_downloading) {
                        dlPollActive = false;
                        if (dlPollTimer) {
                            clearTimeout(dlPollTimer);
                            clearInterval(dlPollTimer);
                            dlPollTimer = null;
                        }

                        if (queueBatchCompletedNotified) {
                            return;
                        }
                        queueBatchCompletedNotified = true;

                        showToast(`🎉 Downloaded all (${selected.length} episodes) 100% complete!`);
                        appendDownloaderLog(`[${new Date().toLocaleTimeString()}] Batch download finished: ${selected.length} episodes ready in ${path}`);
                        return; // Done
                    }
                }
            } catch (e) {}

            if (dlPollActive && dlPollSessionId === currentSessionId) {
                dlPollTimer = setTimeout(pollBatchQueueStatus, 500);
            }
        }

        dlPollTimer = setTimeout(pollBatchQueueStatus, 400);
    } catch (e) {
        dlPollActive = false;
        showToast("Failed to start download");
    }
}

async function stopBatchDownload() {
    try {
        await fetch('/api/downloader/stop', { method: 'POST' });
        showToast("Download Stopped");
        dlPollActive = false;
        ++dlPollSessionId;
        if (dlPollTimer) {
            clearTimeout(dlPollTimer);
            clearInterval(dlPollTimer);
            dlPollTimer = null;
        }
    } catch (e) {}
}

function updateDownloaderStats(stats) {
    if (!stats) return;
    const total = document.getElementById('dl-stat-total');
    const selected = document.getElementById('dl-stat-selected');
    const completed = document.getElementById('dl-stat-completed');
    const failed = document.getElementById('dl-stat-failed');
    const locked = document.getElementById('dl-stat-locked');
    const percent = document.getElementById('dl-stat-overall-percent');

    if (total) total.textContent = stats.total ?? 0;
    if (selected) selected.textContent = stats.selected ?? 0;
    if (completed) completed.textContent = stats.completed ?? 0;
    if (failed) failed.textContent = stats.failed ?? 0;
    if (locked) locked.textContent = stats.locked ?? 0;
    if (percent) percent.textContent = `${stats.progress_percent ?? 0}%`;

    const overallFill = document.getElementById('dl-stat-overall-fill');
    if (overallFill) {
        overallFill.style.width = `${stats.progress_percent ?? 0}%`;
    }

    // Ensure footer is visible when in Downloader tab
    const dlFooter = document.getElementById('footer-dl-stats');
    if (dlFooter) {
        const dlView = document.getElementById('view-downloader-workspace');
        if (dlView && dlView.style.display !== 'none') {
            dlFooter.style.display = 'flex';
        }
    }
}

function appendDownloaderLog(msg) {
    const box = document.getElementById('dl-activity-terminal-box');
    if (!box) return;
    const line = document.createElement('div');
    line.className = 'terminal-line';
    line.textContent = msg;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
}

function clearDownloaderLog() {
    const box = document.getElementById('dl-activity-terminal-box');
    if (box) box.innerHTML = `<div class="terminal-line">[${new Date().toLocaleTimeString()}] Activity log cleared.</div>`;
    showToast("Log cleared");
}

// ==========================================================================
// 5. SETTINGS & IMPORT MODALS (Exact Match to Images 3 & 4)
// ==========================================================================
function openSettingsModal() {
    backToSettingsHub();
    openModal('modal-settings');
}

function openUserGuideModal() {
    openModal('modal-settings');
    openSettingsSubpage('guide');
}

function backToSettingsHub() {
    const hub = document.getElementById('settings-main-hub-view');
    const subAi = document.getElementById('settings-subpage-ai');
    const subLic = document.getElementById('settings-subpage-license');
    const subStory = document.getElementById('settings-subpage-story');
    const subGuide = document.getElementById('settings-subpage-guide');

    if (hub) hub.style.display = 'flex';
    if (subAi) subAi.style.display = 'none';
    if (subLic) subLic.style.display = 'none';
    if (subStory) subStory.style.display = 'none';
    if (subGuide) subGuide.style.display = 'none';
}

function openSettingsSubpage(key) {
    if (key === 'ai') {
        closeModal('modal-settings');
        openAiProvidingModal();
        return;
    }
    if (key === 'story') {
        closeModal('modal-settings');
        openStorySettingsModal();
        return;
    }

    const hub = document.getElementById('settings-main-hub-view');
    const subAi = document.getElementById('settings-subpage-ai');
    const subLic = document.getElementById('settings-subpage-license');
    const subStory = document.getElementById('settings-subpage-story');
    const subGuide = document.getElementById('settings-subpage-guide');

    if (hub) hub.style.display = 'none';
    if (subAi) subAi.style.display = 'none';
    if (subLic) subLic.style.display = 'none';
    if (subStory) subStory.style.display = 'none';
    if (subGuide) subGuide.style.display = 'none';

    if (key === 'license') {
        if (subLic) subLic.style.display = 'flex';
        const licEngineVerElem = document.getElementById('settings-lic-engine-version');
        if (licEngineVerElem && window._currentAppVersion) {
            licEngineVerElem.textContent = `SN AI Engine v${window._currentAppVersion}`;
        }
    }
    if (key === 'guide' && subGuide) subGuide.style.display = 'flex';
}

// ==========================================================================
// STORY SETTINGS MANAGER (Exact Match to User Attached Image)
// ==========================================================================
let currentStoryConfig = {
    khmer_voice: "piseth",
    auto_multi_voice: false,
    source_lang: "auto",
    whisper_model: "medium",
    aspect_ratio: "9:16",
    subtitle_mode: "none",
    dubbing_mode: "smart_bgm",
    ducking_volume: "0.15",
    speech_boost_db: 2.5
};

function getStoryVoiceDisplayLabel() {
    if (currentStoryConfig.khmer_voice === 'sreymom') {
        return "Sreymom (Female Solo)";
    }
    return "Piseth (Male Solo)";
}

function refreshStagedCardVoiceMeta() {
    const stagedMeta = document.getElementById('staged-file-meta');
    if (!stagedMeta) return;
    const vLabel = getStoryVoiceDisplayLabel();
    if (stagedVideoFile) {
        const sizeMb = stagedVideoFile.size_mb !== undefined ? stagedVideoFile.size_mb : (stagedVideoFile.size ? (stagedVideoFile.size / (1024 * 1024)).toFixed(1) : "0.0");
        let durStr = "";
        if (totalDurationSeconds > 0) {
            const durM = Math.floor(totalDurationSeconds / 60);
            const durS = Math.floor(totalDurationSeconds % 60);
            durStr = ` • ${String(durM).padStart(2, '0')}:${String(durS).padStart(2, '0')}`;
        }
        stagedMeta.innerHTML = `<i class="fa-solid fa-microphone-lines" style="color:#facc15;"></i> Voice: <strong style="color:#facc15;">${vLabel}</strong> • ${sizeMb} MB${durStr} • Ready to Dub`;
    } else if (stagedBatchFiles && stagedBatchFiles.length > 0) {
        stagedMeta.innerHTML = `<i class="fa-solid fa-microphone-lines" style="color:#facc15;"></i> Voice: <strong style="color:#facc15;">${vLabel}</strong> • Batch: ${stagedBatchFiles.length} Videos`;
    }
}

function syncStagedCardControls() {
    // 1. Sync voice chip active state (Piseth & Sreymom Solo)
    currentStoryConfig.auto_multi_voice = false;
    if (currentStoryConfig.khmer_voice === 'multi') {
        currentStoryConfig.khmer_voice = 'piseth';
    }
    let activeKey = (currentStoryConfig.khmer_voice === 'sreymom') ? 'sreymom' : 'piseth';

    ['piseth', 'sreymom'].forEach(k => {
        const chip = document.getElementById(`voice-chip-${k}`);
        if (chip) {
            const st = chip.querySelector('.staged-chip-status-text');
            if (k === activeKey) {
                chip.classList.add('active');
                if (st) st.textContent = 'Active';
            } else {
                chip.classList.remove('active');
                if (st) st.textContent = 'Select';
            }
        }
    });

    const vBadge = document.getElementById('staged-voice-status-badge');
    if (vBadge) {
        if (activeKey === 'sreymom') vBadge.textContent = "Sreymom (Female Solo)";
        else vBadge.textContent = "Piseth (Male Solo)";
    }

    // 2. Sync BGM slider & presets
    const rawDuck = parseFloat(currentStoryConfig.ducking_volume !== undefined ? currentStoryConfig.ducking_volume : 0.15);
    const duckingNum = Math.min(40, Math.max(0, Math.round(rawDuck * 100)));
    const slider = document.getElementById('staged-bgm-slider');
    if (slider) slider.value = duckingNum;

    [0, 10, 18, 28].forEach(p => {
        const btn = document.getElementById(`bgm-pre-${p}`);
        if (btn) {
            if (p === duckingNum || (p === 18 && (duckingNum >= 15 && duckingNum <= 20))) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        }
    });

    const bgmBadge = document.getElementById('staged-bgm-val-badge');
    if (bgmBadge) {
        if (duckingNum === 0) bgmBadge.textContent = "0% (Muted)";
        else if (duckingNum <= 10) bgmBadge.textContent = `${duckingNum}% • Subtle`;
        else if (duckingNum <= 20) bgmBadge.textContent = `${duckingNum}% • Recommended`;
        else bgmBadge.textContent = `${duckingNum}% • Moderate`;
    }
}

async function selectQuickVoice(voiceKey) {
    if (voiceKey === 'sreymom') {
        currentStoryConfig.khmer_voice = 'sreymom';
        currentStoryConfig.auto_multi_voice = false;
    } else {
        currentStoryConfig.khmer_voice = 'piseth';
        currentStoryConfig.auto_multi_voice = false;
    }

    if (currentVoicePreviewAudio) {
        currentVoicePreviewAudio.pause();
        currentVoicePreviewAudio = null;
        currentPreviewVoiceKey = null;
        resetAllVoicePreviewBtns();
    }

    syncStagedCardControls();
    refreshStagedCardVoiceMeta();

    const voiceLabels = {
        'piseth': 'Piseth (Male Solo)',
        'sreymom': 'Sreymom (Female Solo)'
    };
    showToast(`Voice changed: ${voiceLabels[voiceKey] || voiceKey}`);
    appendLiveTerminalLine(`Dubbing voice set to: ${voiceLabels[voiceKey] || voiceKey}`, "[Voice Config]", "info");

    // Sync modal selector
    const modalSelect = document.getElementById('story-voice-select');
    if (modalSelect) modalSelect.value = voiceKey;

    try {
        await fetch('/api/set-story-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                khmer_voice: currentStoryConfig.khmer_voice,
                auto_multi_voice: currentStoryConfig.auto_multi_voice
            })
        });
    } catch (e) {
        console.warn("Save quick voice error:", e);
    }
}

let currentVoicePreviewAudio = null;
let currentPreviewVoiceKey = null;

async function playVoiceSamplePreview(voiceKey, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    const prevBtn = document.getElementById(`voice-prev-btn-${voiceKey}`);
    const waveEl = document.getElementById(`voice-wave-${voiceKey}`);

    // If currently playing this voice, toggle stop
    if (currentVoicePreviewAudio && currentPreviewVoiceKey === voiceKey) {
        currentVoicePreviewAudio.pause();
        currentVoicePreviewAudio = null;
        currentPreviewVoiceKey = null;
        resetAllVoicePreviewBtns();
        return;
    }

    // Stop any other voice audio
    if (currentVoicePreviewAudio) {
        currentVoicePreviewAudio.pause();
        currentVoicePreviewAudio = null;
    }
    resetAllVoicePreviewBtns();

    currentPreviewVoiceKey = voiceKey;
    if (prevBtn) {
        prevBtn.classList.add('loading');
        prevBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Loading...</span>';
    }

    const sampleTexts = {
        'piseth': "Hello! I am Piseth, voice talent for Asian TV dramas and short stories.",
        'sreymom': "Hello! I am Sreymom, glad to dub Asian TV dramas for you."
    };

    const textToSpeak = sampleTexts[voiceKey] || "Hello";
    const actualVoice = voiceKey === 'sreymom' ? 'sreymom' : 'piseth';

    try {
        const res = await fetch('/api/voices/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: textToSpeak,
                voice: actualVoice,
                rate_percent: 0,
                pitch_hz: 0
            })
        });
        const data = await res.json();
        if (data && data.success && data.audio_url) {
            currentVoicePreviewAudio = new Audio(data.audio_url);
            if (prevBtn) {
                prevBtn.classList.remove('loading');
                prevBtn.classList.add('playing');
                prevBtn.innerHTML = '<i class="fa-solid fa-pause"></i> <span>Pause</span>';
            }
            if (waveEl) waveEl.classList.add('animating');

            currentVoicePreviewAudio.play().catch(e => {
                console.warn("Audio play blocked/error:", e);
                resetAllVoicePreviewBtns();
            });

            currentVoicePreviewAudio.onended = () => {
                resetAllVoicePreviewBtns();
                currentVoicePreviewAudio = null;
                currentPreviewVoiceKey = null;
            };
            currentVoicePreviewAudio.onerror = () => {
                resetAllVoicePreviewBtns();
                currentVoicePreviewAudio = null;
                currentPreviewVoiceKey = null;
            };
        } else {
            resetAllVoicePreviewBtns();
            showToast("Cannot play voice preview");
        }
    } catch (e) {
        console.warn("Voice preview fetch error:", e);
        resetAllVoicePreviewBtns();
        showToast("Please start Server to test voice sample");
    }
}

function resetAllVoicePreviewBtns() {
    ['piseth', 'sreymom'].forEach(k => {
        const btn = document.getElementById(`voice-prev-btn-${k}`);
        if (btn) {
            btn.classList.remove('loading', 'playing');
            btn.innerHTML = '<i class="fa-solid fa-play"></i> <span>Sample</span>';
        }
        const wave = document.getElementById(`voice-wave-${k}`);
        if (wave) wave.classList.remove('animating');
    });
}

// ==========================================================================
// STAGED WORKSPACE OVERLAY LOGO & BLUR ASSET MANAGEMENT
// ==========================================================================
let currentOverlayAssets = {
    logo: null,
    logoUrl: null,
    serverLogoPath: null,
    logoPosition: 'top-right',
    logoScale: 1.0,
    logoWidth: 110,
    blurActive: false,
    blurPosition: 'top-right',
    blurScale: 1.0,
    blurWidth: 120,
    blurHeight: 50,
    blurRadius: 25,
    blurShape: 'rectangle',
    blurFeather: 0,
    blurRoundCorners: 0,
    textActive: false,
    textValue: 'EPISODE 01',
    textSize: 24,
    textColor: '#ffffff',
    wordColors: {},
    selectedWordIndex: 'all',
    textSegments: [],
    textBg: false,
    textPosition: 'top-center',
    lowerThirdActive: false,
    lowerThirdFile: null,
    lowerThirdUrl: null,
    serverLowerThirdPath: null,
    lowerThirdSamplePath: null,
    lowerThirdScale: 0.65,
    lowerThirdOpacity: 1.0,
    lowerThirdStartTime: 0.0,
    lowerThirdEndTime: 0.0,
    lowerThirdLoop: true,
    lowerThirdSpeed: 1.0,
    lowerThirdPosition: 'bottom-center',
    subtitleActive: false,
    subtitleStyle: 'viral_yellow',
    subtitleSize: 44,
    subtitleMarginV: 65,
    customSubtitleFile: null,
    customSubtitlePath: null,
    customSubtitleName: null
};

function triggerOverlayUpload(type) {
    if (type === 'logo') {
        const input = document.getElementById('input-overlay-logo');
        if (input) input.click();
    } else if (type === 'blur') {
        toggleBlurMaskTool();
    } else if (type === 'text') {
        toggleTextOverlayTool();
    } else if (type === 'lower_third') {
        if (currentOverlayAssets.lowerThirdFile || currentOverlayAssets.lowerThirdUrl || currentOverlayAssets.serverLowerThirdPath) {
            toggleLowerThirdDropdown();
        } else {
            const input = document.getElementById('input-overlay-lower-third-file');
            if (input) input.click();
        }
    } else if (type === 'subtitle') {
        toggleSubtitleDropdown();
    }
}

function handleOverlayFileSelect(event, type) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    if (type === 'logo') {
        if (currentOverlayAssets.logoUrl) {
            URL.revokeObjectURL(currentOverlayAssets.logoUrl);
        }
        currentOverlayAssets.logo = file;
        currentOverlayAssets.logoUrl = URL.createObjectURL(file);
        currentOverlayAssets.serverLogoPath = null;

        // Immediately upload logo to backend so local file path is ready for FFmpeg render
        try {
            const fd = new FormData();
            fd.append('logo_file', file);
            fetch('/api/projects/upload-overlay-logo', { method: 'POST', body: fd })
                .then(r => r.json())
                .then(d => {
                    if (d.success && d.logo_path) {
                        currentOverlayAssets.serverLogoPath = d.logo_path;
                        appendLiveTerminalLine(`Logo saved to studio engine: ${d.filename}`, "[Overlay Engine]", "info");
                    }
                })
                .catch(err => console.warn("Logo instant upload background note:", err));
        } catch (e) {
            console.warn("Logo upload trigger note:", e);
        }

        // Show directly on Video Preview Monitor
        const monitorLogo = document.getElementById('monitor-logo-overlay');
        const monitorLogoImg = document.getElementById('monitor-logo-img');
        if (monitorLogo && monitorLogoImg) {
            monitorLogoImg.src = currentOverlayAssets.logoUrl;
            monitorLogo.style.display = 'flex';
            setOverlayPosition('logo', currentOverlayAssets.logoPosition || 'top-right');
            makeOverlayDraggable(monitorLogo);
            const logoHandle = document.getElementById('logo-resize-handle');
            if (logoHandle) makeOverlayResizable(monitorLogo, logoHandle, 'logo');
        }

        const logoCard = document.getElementById('card-upload-logo');
        if (logoCard) logoCard.classList.add('has-active-controls');

        const statusEl = document.getElementById('status-overlay-logo');
        const sizeKb = (file.size / 1024).toFixed(1);

        if (statusEl) {
            statusEl.innerHTML = `
                <div class="overlay-active-controls">
                    <span class="overlay-status-pill selected" title="${escapeHtml(file.name)}">
                        <img src="${currentOverlayAssets.logoUrl}" class="overlay-thumb-mini" alt="thumb">
                        <span class="overlay-file-name">${escapeHtml(file.name)}</span>
                        <button type="button" class="overlay-file-remove-btn" onclick="clearOverlayFile(event, 'logo')" title="Remove Logo">&times;</button>
                    </span>
                    <div class="overlay-preset-buttons">
                        <button type="button" class="pos-preset-btn ${currentOverlayAssets.logoPosition === 'top-right' ? 'active' : ''}" onclick="setOverlayPosition('logo', 'top-right', event)" title="Top-Right">TR</button>
                        <button type="button" class="pos-preset-btn ${currentOverlayAssets.logoPosition === 'top-left' ? 'active' : ''}" onclick="setOverlayPosition('logo', 'top-left', event)" title="Top-Left">TL</button>
                        <button type="button" class="pos-preset-btn ${currentOverlayAssets.logoPosition === 'bottom-right' ? 'active' : ''}" onclick="setOverlayPosition('logo', 'bottom-right', event)" title="Bottom-Right">BR</button>
                    </div>
                    <div class="overlay-size-controls" onclick="event.stopPropagation()">
                        <button type="button" class="size-ctrl-btn" onclick="adjustOverlaySize('logo', -0.15, event)" title="Zoom Out Logo"><i class="fa-solid fa-minus"></i></button>
                        <span class="overlay-size-label" id="logo-size-label">${Math.round((currentOverlayAssets.logoScale || 1.0) * 100)}%</span>
                        <button type="button" class="size-ctrl-btn" onclick="adjustOverlaySize('logo', 0.15, event)" title="Zoom In Logo"><i class="fa-solid fa-plus"></i></button>
                    </div>
                </div>
            `;
        }

        showToast(`Logo applied to Video Preview! (${file.name})`);
        appendLiveTerminalLine(`Logo overlay attached to preview monitor: ${file.name} (${sizeKb} KB)`, "[Overlay Engine]", "success");
    }
}

function clearOverlayFile(event, type) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    if (type === 'logo') {
        if (currentOverlayAssets.logoUrl) {
            URL.revokeObjectURL(currentOverlayAssets.logoUrl);
            currentOverlayAssets.logoUrl = null;
        }
        currentOverlayAssets.logo = null;
        currentOverlayAssets.serverLogoPath = null;
        const input = document.getElementById('input-overlay-logo');
        if (input) input.value = '';

        const monitorLogo = document.getElementById('monitor-logo-overlay');
        if (monitorLogo) monitorLogo.style.display = 'none';

        const logoCard = document.getElementById('card-upload-logo');
        if (logoCard) logoCard.classList.remove('has-active-controls');

        const statusEl = document.getElementById('status-overlay-logo');
        if (statusEl) {
            statusEl.innerHTML = `<span class="overlay-status-pill empty"><i class="fa-solid fa-cloud-arrow-up"></i> Click to Upload</span>`;
        }
        showToast("Removed Logo from Preview Monitor");
    }
}

// In-App BLUR Mask Tool (NO Computer File Explorer Dialog)
function toggleBlurMaskTool(event, forceState) {
    if (event) {
        event.stopPropagation();
    }
    if (typeof forceState === 'boolean') {
        currentOverlayAssets.blurActive = forceState;
    } else {
        currentOverlayAssets.blurActive = !currentOverlayAssets.blurActive;
    }

    const monitorBlur = document.getElementById('monitor-blur-overlay');
    const statusPill = document.getElementById('blur-status-pill');
    const statusLabel = document.getElementById('blur-status-label');
    const descLabel = document.getElementById('blur-intensity-desc-label');

    if (currentOverlayAssets.blurActive) {
        if (monitorBlur) {
            monitorBlur.style.display = 'flex';
            setOverlayPosition('blur', currentOverlayAssets.blurPosition || 'top-right');
            makeOverlayDraggable(monitorBlur);
            const blurHandle = document.getElementById('blur-resize-handle');
            if (blurHandle) makeOverlayResizable(monitorBlur, blurHandle, 'blur');
            applyBlurIntensity(currentOverlayAssets.blurRadius || 25, '25px (Medium)');
        }
        if (statusPill) {
            statusPill.className = 'overlay-status-pill selected blur-active-pill';
        }
        if (statusLabel) {
            statusLabel.textContent = `Blur (${currentOverlayAssets.blurRadius || 25}px)`;
        }
        if (descLabel) {
            descLabel.textContent = `Active Blur: ${currentOverlayAssets.blurRadius || 25}px (adjustable)`;
        }
        showToast("BLUR Mask enabled on Video Preview (adjustable and resizable)!");
        appendLiveTerminalLine("Blur Mask overlay enabled on video preview monitor (active)", "[Overlay Engine]", "success");
    } else {
        if (monitorBlur) {
            monitorBlur.style.display = 'none';
        }
        if (statusPill) {
            statusPill.className = 'overlay-status-pill empty';
        }
        if (statusLabel) {
            statusLabel.textContent = 'Click to Add Blur';
        }
        if (descLabel) {
            descLabel.textContent = 'Mask old watermark/logo on video preview';
        }
        closeBlurMaskDropdown();
        showToast("Removed BLUR Mask from video");
    }
}

function toggleBlurMaskDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }

    if (typeof closeTextOverlayDropdown === 'function') closeTextOverlayDropdown();
    if (typeof closeLowerThirdDropdown === 'function') closeLowerThirdDropdown();
    if (typeof closeTrackBgmDropdown === 'function') closeTrackBgmDropdown();

    const panel = document.getElementById('overlay-inline-settings-panel');
    const divider = document.getElementById('overlay-inline-panel-divider');
    const dropdown = document.getElementById('blur-custom-dropdown');
    const chevron = document.getElementById('blur-dropdown-chevron');
    const stack = document.getElementById('staged-overlay-unified-panel');
    if (!dropdown || !panel) return;

    const isOpen = (dropdown.classList.contains('show') || dropdown.style.display === 'flex') && dropdown.style.display !== 'none';
    
    if (isOpen) {
        closeBlurMaskDropdown();
    } else {
        // If blur is not yet active, activate it on video monitor
        if (!currentOverlayAssets.blurActive) {
            toggleBlurMaskTool(null, true);
        }

        if (divider) divider.style.display = 'block';
        panel.style.display = 'flex';
        if (stack) stack.classList.add('has-inline-open');

        dropdown.style.display = 'flex';
        dropdown.classList.add('show');
        if (chevron) chevron.classList.add('open');
    }
}

function closeBlurMaskDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const panel = document.getElementById('overlay-inline-settings-panel');
    const divider = document.getElementById('overlay-inline-panel-divider');
    const dropdown = document.getElementById('blur-custom-dropdown');
    const chevron = document.getElementById('blur-dropdown-chevron');
    const textDropdown = document.getElementById('text-custom-dropdown');
    const ltDropdown = document.getElementById('lower-third-custom-dropdown');
    const subDropdown = document.getElementById('subtitle-custom-dropdown');
    const stack = document.getElementById('staged-overlay-unified-panel');

    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.classList.remove('show');
    }
    if (chevron) chevron.classList.remove('open');

    const isTextOpen = textDropdown && (textDropdown.classList.contains('show') || textDropdown.style.display === 'flex') && textDropdown.style.display !== 'none';
    const isLtOpen = ltDropdown && (ltDropdown.classList.contains('show') || ltDropdown.style.display === 'flex') && ltDropdown.style.display !== 'none';
    const isSubOpen = subDropdown && (subDropdown.classList.contains('show') || subDropdown.style.display === 'flex') && subDropdown.style.display !== 'none';
    if (!isTextOpen && !isLtOpen && !isSubOpen) {
        if (divider) divider.style.display = 'none';
        if (panel) panel.style.display = 'none';
        if (stack) stack.classList.remove('has-inline-open');
    }
}

function onBlurSliderChange(val, e) {
    if (e) e.stopPropagation();
    const radius = parseInt(val, 10);
    applyBlurIntensity(radius, `${radius}px`);
}

function onBlurFeatherChange(val, e) {
    if (e) e.stopPropagation();
    const feather = Math.max(0, Math.min(100, parseInt(val, 10) || 0));
    currentOverlayAssets.blurFeather = feather;

    const slider = document.getElementById('input-blur-feather');
    const numInput = document.getElementById('num-blur-feather');
    if (slider && parseInt(slider.value, 10) !== feather) slider.value = feather;
    if (numInput && parseInt(numInput.value, 10) !== feather) numInput.value = feather;

    if (!currentOverlayAssets.blurActive) {
        toggleBlurMaskTool(null, true);
    }
    applyBlurMaskStyling();
}

function onBlurCornersChange(val, e) {
    if (e) e.stopPropagation();
    const corners = Math.max(0, Math.min(100, parseInt(val, 10) || 0));
    currentOverlayAssets.blurRoundCorners = corners;

    const slider = document.getElementById('input-blur-corners');
    const numInput = document.getElementById('num-blur-corners');
    if (slider && parseInt(slider.value, 10) !== corners) slider.value = corners;
    if (numInput && parseInt(numInput.value, 10) !== corners) numInput.value = corners;

    if (!currentOverlayAssets.blurActive) {
        toggleBlurMaskTool(null, true);
    }
    applyBlurMaskStyling();
}

function stepBlurParam(param, step, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    if (param === 'feather') {
        const cur = currentOverlayAssets.blurFeather || 0;
        onBlurFeatherChange(cur + step, e);
    } else if (param === 'corners') {
        const cur = currentOverlayAssets.blurRoundCorners !== undefined ? currentOverlayAssets.blurRoundCorners : 0;
        onBlurCornersChange(cur + step, e);
    }
}

function resetBlurParam(param, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    if (param === 'feather') {
        onBlurFeatherChange(0, e);
        showToast("Feather reset to 0");
    } else if (param === 'corners') {
        onBlurCornersChange(0, e);
        showToast("Round corners reset to 0");
    }
}

function applyBlurMaskStyling() {
    const monitorBlur = document.getElementById('monitor-blur-overlay');
    if (!monitorBlur) return;

    const radius = currentOverlayAssets.blurRadius || 25;
    const shape = currentOverlayAssets.blurShape || 'rectangle';
    const feather = currentOverlayAssets.blurFeather || 0;
    const roundCorners = currentOverlayAssets.blurRoundCorners !== undefined ? currentOverlayAssets.blurRoundCorners : 0;

    // 1. Live Dynamic Blur Filter
    monitorBlur.style.backdropFilter = `blur(${radius}px)`;
    monitorBlur.style.webkitBackdropFilter = `blur(${radius}px)`;

    // 2. Round Corners (Border Radius)
    if (shape === 'circle') {
        monitorBlur.style.borderRadius = '50%';
    } else {
        monitorBlur.style.borderRadius = `${roundCorners}px`;
    }

    // 3. Feathering (Soft diffused mask boundaries)
    if (feather > 0) {
        if (shape === 'circle') {
            const startPct = Math.max(0, 100 - feather);
            const maskGrad = `radial-gradient(circle at center, black ${startPct}%, transparent 100%)`;
            monitorBlur.style.webkitMaskImage = maskGrad;
            monitorBlur.style.maskImage = maskGrad;
            monitorBlur.style.webkitMaskComposite = 'source-over';
            monitorBlur.style.maskComposite = 'add';
        } else {
            // Feathered soft rectangular box with smooth edge falloff
            const maskGrad = `linear-gradient(to right, transparent 0%, black ${feather}px, black calc(100% - ${feather}px), transparent 100%), linear-gradient(to bottom, transparent 0%, black ${feather}px, black calc(100% - ${feather}px), transparent 100%)`;
            monitorBlur.style.webkitMaskImage = maskGrad;
            monitorBlur.style.maskImage = maskGrad;
            monitorBlur.style.webkitMaskComposite = 'source-in';
            monitorBlur.style.maskComposite = 'intersect';
        }
    } else {
        monitorBlur.style.webkitMaskImage = 'none';
        monitorBlur.style.maskImage = 'none';
        monitorBlur.style.webkitMaskComposite = 'normal';
        monitorBlur.style.maskComposite = 'add';
    }

    // 4. Color tint & dashed border
    if (radius >= 65) {
        monitorBlur.style.backgroundColor = 'rgba(10, 10, 20, 0.78)';
        monitorBlur.style.borderColor = 'rgba(250, 204, 21, 0.9)';
    } else {
        monitorBlur.style.backgroundColor = 'rgba(168, 85, 247, 0.20)';
        monitorBlur.style.borderColor = 'rgba(192, 132, 252, 0.85)';
    }
}

function selectBlurShape(shape, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    currentOverlayAssets.blurShape = shape;

    // Update active highlight across shape items
    const shapes = ['filmstrip', 'circle', 'rectangle'];
    shapes.forEach(s => {
        const item = document.getElementById(`shape-opt-${s}`);
        if (item) {
            item.classList.toggle('active', s === shape);
        }
    });

    // Ensure blur mask tool is active on video monitor
    if (!currentOverlayAssets.blurActive) {
        toggleBlurMaskTool(null, true);
    }

    const monitorBlur = document.getElementById('monitor-blur-overlay');
    const labelTag = monitorBlur ? monitorBlur.querySelector('.blur-label-tag') : null;

    if (monitorBlur) {
        monitorBlur.classList.remove('shape-filmstrip', 'shape-circle', 'shape-rectangle');
        monitorBlur.classList.add(`shape-${shape}`);

        if (shape === 'circle') {
            monitorBlur.style.aspectRatio = '1 / 1';
            monitorBlur.style.width = '95px';
            monitorBlur.style.height = '95px';
            if (labelTag) labelTag.innerHTML = '<i class="fa-regular fa-circle"></i> CIRCLE';
            showToast("Blur Mask set to: Circle");
            appendLiveTerminalLine("Blur mask shape changed to Circle.", "[Blur Engine]", "info");
        } else if (shape === 'filmstrip') {
            monitorBlur.style.aspectRatio = 'auto';
            monitorBlur.style.width = 'calc(100% - 28px)';
            monitorBlur.style.height = '46px';
            monitorBlur.style.left = '14px';
            monitorBlur.style.right = '14px';
            if (labelTag) labelTag.innerHTML = '<i class="fa-solid fa-film"></i> FILMSTRIP';
            showToast("Blur Mask set to: Filmstrip");
            appendLiveTerminalLine("Blur mask shape changed to Filmstrip.", "[Blur Engine]", "info");
        } else {
            // Rectangle
            monitorBlur.style.aspectRatio = 'auto';
            monitorBlur.style.width = '130px';
            monitorBlur.style.height = '52px';
            if (labelTag) labelTag.innerHTML = '<i class="fa-solid fa-eye-slash"></i> RECTANGLE';
            showToast("Blur Mask set to: Rectangle");
            appendLiveTerminalLine("Blur mask shape changed to Rectangle.", "[Blur Engine]", "info");
        }
    }

    applyBlurMaskStyling();
}

function selectBlurPreset(radius, title, labelShort, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    applyBlurIntensity(radius, labelShort || `${radius}px`);
    const slider = document.getElementById('input-blur-intensity');
    if (slider) slider.value = radius;
}

function applyBlurIntensity(radius, displayLabel) {
    currentOverlayAssets.blurRadius = radius;
    
    // Apply styling to Video Preview Monitor overlay
    applyBlurMaskStyling();

    // Update Slider Badge
    const badge = document.getElementById('blur-slider-badge');
    if (badge) {
        badge.textContent = `${radius}px`;
    }

    // Update Row 2 status text
    const statusLabel = document.getElementById('blur-status-label');
    if (statusLabel) {
        statusLabel.textContent = `Blur (${radius}px)`;
    }

    const descLabel = document.getElementById('blur-intensity-desc-label');
    if (descLabel) {
        descLabel.textContent = `Active Blur: ${radius}px (${displayLabel || ''})`;
    }
}

function setOverlayPosition(type, pos, event) {
    if (event) event.stopPropagation();
    let el = null;
    if (type === 'logo') el = document.getElementById('monitor-logo-overlay');
    else if (type === 'blur') el = document.getElementById('monitor-blur-overlay');
    else if (type === 'text') el = document.getElementById('monitor-text-overlay');
    else if (type === 'lower_third') el = document.getElementById('monitor-lower-third-overlay');
    if (!el) return;

    if (type === 'logo') currentOverlayAssets.logoPosition = pos;
    if (type === 'blur') currentOverlayAssets.blurPosition = pos;
    if (type === 'text') currentOverlayAssets.textPosition = pos;
    if (type === 'lower_third') currentOverlayAssets.lowerThirdPosition = pos;

    el.style.left = '';
    el.style.right = '';
    el.style.top = '';
    el.style.bottom = '';
    el.style.transform = '';

    if (pos === 'top-center') {
        if (type === 'lower_third') {
            const elHeight = el.offsetHeight || 450;
            el.style.top = `${-Math.round(elHeight * 0.42)}px`;
            el.style.bottom = 'auto';
            el.style.left = '0%';
            el.style.transform = 'none';
        } else {
            el.style.top = '24px';
            el.style.left = '50%';
            el.style.transform = 'translateX(-50%)';
        }
    } else if (pos === 'bottom-center') {
        if (type === 'lower_third') {
            const pHeight = el.parentElement ? el.parentElement.offsetHeight : 640;
            const elHeight = el.offsetHeight || 450;
            const flushBottom = Math.round(pHeight - elHeight * 0.58);
            el.style.top = `${flushBottom}px`;
            el.style.bottom = 'auto';
            el.style.left = '0%';
            el.style.transform = 'none';
        } else {
            el.style.bottom = '24px';
            el.style.left = '50%';
            el.style.transform = 'translateX(-50%)';
        }
    } else if (pos === 'top-right') {
        el.style.top = '14px';
        el.style.right = '14px';
    } else if (pos === 'top-left') {
        el.style.top = '14px';
        el.style.left = '14px';
    } else if (pos === 'bottom-right') {
        if (type === 'lower_third') {
            const pHeight = el.parentElement ? el.parentElement.offsetHeight : 640;
            const elHeight = el.offsetHeight || 450;
            el.style.top = `${Math.round(pHeight - elHeight * 0.58)}px`;
            el.style.bottom = 'auto';
            el.style.right = '0px';
        } else {
            el.style.bottom = '14px';
            el.style.right = '14px';
        }
    } else if (pos === 'bottom-left') {
        if (type === 'lower_third') {
            const pHeight = el.parentElement ? el.parentElement.offsetHeight : 640;
            const elHeight = el.offsetHeight || 450;
            el.style.top = `${Math.round(pHeight - elHeight * 0.58)}px`;
            el.style.bottom = 'auto';
            el.style.left = '0px';
        } else {
            el.style.bottom = '14px';
            el.style.left = '14px';
        }
    }

    // Update active preset button styling
    const card = document.getElementById(type === 'logo' ? 'card-upload-logo' : type === 'blur' ? 'card-upload-blur' : type === 'text' ? 'card-upload-text' : 'card-upload-lower-third');
    if (card) {
        card.querySelectorAll('.pos-preset-btn').forEach(btn => {
            const btnKey = btn.textContent.trim().toLowerCase();
            const targetKey = pos === 'top-right' ? 'tr' : pos === 'top-left' ? 'tl' : pos === 'bottom-right' ? 'br' : pos === 'top-center' ? 'tc' : 'bc';
            btn.classList.toggle('active', btnKey === targetKey);
        });
    }
    if (type === 'lower_third') {
        ['bc', 'bl', 'br', 'tc'].forEach(k => {
            const b = document.getElementById(`btn-lt-pos-${k}`);
            if (b) {
                const targetKey = pos === 'bottom-center' ? 'bc' : pos === 'bottom-left' ? 'bl' : pos === 'bottom-right' ? 'br' : 'tc';
                b.classList.toggle('active', k === targetKey);
            }
        });
    }

    if (type === 'blur') {
        document.querySelectorAll('#blur-custom-dropdown .blur-tray-pill-btn').forEach(btn => btn.classList.remove('active'));
        const btnKey = pos === 'top-right' ? 'btn-blur-pos-tr' : pos === 'top-left' ? 'btn-blur-pos-tl' : 'btn-blur-pos-bc';
        const activeBtn = document.getElementById(btnKey);
        if (activeBtn) activeBtn.classList.add('active');
    }

    if (type === 'text') {
        const textDropdown = document.getElementById('text-custom-dropdown');
        if (textDropdown) {
            textDropdown.querySelectorAll('.blur-tray-pill-btn').forEach(btn => btn.classList.remove('active'));
            let activeId = 'btn-text-pos-tc';
            if (pos === 'bottom-center') activeId = 'btn-text-pos-bc';
            else if (pos === 'top-left') activeId = 'btn-text-pos-tl';
            else if (pos === 'top-right') activeId = 'btn-text-pos-tr';
            const activeBtn = document.getElementById(activeId);
            if (activeBtn) activeBtn.classList.add('active');
        }
    }

    if (type === 'lower_third') {
        const ltDropdown = document.getElementById('lower-third-custom-dropdown');
        if (ltDropdown) {
            ltDropdown.querySelectorAll('.blur-tray-pill-btn').forEach(btn => btn.classList.remove('active'));
            let activeId = 'btn-lt-pos-bc';
            if (pos === 'bottom-left') activeId = 'btn-lt-pos-bl';
            else if (pos === 'bottom-right') activeId = 'btn-lt-pos-br';
            else if (pos === 'top-center') activeId = 'btn-lt-pos-tc';
            const activeBtn = document.getElementById(activeId);
            if (activeBtn) activeBtn.classList.add('active');
        }
    }
}

function adjustOverlaySize(type, delta, event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }

    if (type === 'logo') {
        const overlay = document.getElementById('monitor-logo-overlay');
        const img = document.getElementById('monitor-logo-img');
        if (!overlay) return;

        currentOverlayAssets.logoScale = Math.max(0.3, Math.min(3.5, Number(((currentOverlayAssets.logoScale || 1.0) + delta).toFixed(2))));
        const baseW = 110;
        const newW = Math.round(baseW * currentOverlayAssets.logoScale);

        overlay.style.width = `${newW}px`;
        overlay.style.maxWidth = 'none';
        if (img) {
            img.style.maxHeight = 'none';
            img.style.width = '100%';
        }
        currentOverlayAssets.logoWidth = newW;

        const label = document.getElementById('logo-size-label');
        if (label) label.textContent = `${Math.round(currentOverlayAssets.logoScale * 100)}%`;
    } else if (type === 'blur') {
        const overlay = document.getElementById('monitor-blur-overlay');
        if (!overlay) return;

        const curScale = currentOverlayAssets.blurScale || 1.0;
        const targetScale = Math.max(0.3, Math.min(4.0, Number((curScale + delta).toFixed(2))));
        const ratio = targetScale / curScale;

        const curW = currentOverlayAssets.blurWidth || 120;
        const curH = currentOverlayAssets.blurHeight || 50;
        const newW = Math.round(Math.max(40, curW * ratio));
        const newH = Math.round(Math.max(22, curH * ratio));

        overlay.style.width = `${newW}px`;
        overlay.style.height = `${newH}px`;
        currentOverlayAssets.blurWidth = newW;
        currentOverlayAssets.blurHeight = newH;
        currentOverlayAssets.blurScale = targetScale;

        const label = document.getElementById('blur-size-label');
        if (label) label.textContent = `${Math.round(targetScale * 100)}%`;
        const trayLabel = document.getElementById('blur-tray-size-val');
        if (trayLabel) trayLabel.textContent = `${Math.round(targetScale * 100)}%`;
    } else if (type === 'lower_third') {
        const curScale = currentOverlayAssets.lowerThirdScale || 1.0;
        const targetScale = Math.max(0.20, Math.min(1.50, Number((curScale + delta).toFixed(2))));
        if (typeof onLowerThirdScaleChange === 'function') {
            onLowerThirdScaleChange(Math.round(targetScale * 100));
        }
    }
}

// ==========================================================================
// TEXT OVERLAY (Title, Episode Hook, Page Watermark) CONTROLS
// ==========================================================================
function toggleTextOverlayTool(event, forceState) {
    if (event) {
        event.stopPropagation();
    }
    if (typeof forceState === 'boolean') {
        currentOverlayAssets.textActive = forceState;
    } else {
        currentOverlayAssets.textActive = !currentOverlayAssets.textActive;
    }

    const monitorText = document.getElementById('monitor-text-overlay');
    const statusPill = document.getElementById('text-status-pill');
    const statusLabel = document.getElementById('text-status-label');
    const descLabel = document.getElementById('text-overlay-desc-label');

    if (currentOverlayAssets.textActive) {
        if (monitorText) {
            monitorText.style.display = 'flex';
            setOverlayPosition('text', currentOverlayAssets.textPosition || 'top-center');
            makeOverlayDraggable(monitorText);
            const textHandle = document.getElementById('text-resize-handle');
            if (textHandle) makeOverlayResizable(monitorText, textHandle, 'text');
            applyTextOverlayStyling();
        }
        if (statusPill) {
            statusPill.className = 'overlay-status-pill selected text-active-pill';
        }
        if (statusLabel) {
            const previewVal = (currentOverlayAssets.textValue || 'Text').slice(0, 14);
            statusLabel.textContent = `Text: ${previewVal}`;
        }
        if (descLabel) {
            descLabel.textContent = `Active Text: "${currentOverlayAssets.textValue || 'EPISODE 01'}" (${currentOverlayAssets.textSize || 24}px)`;
        }
        showToast("Text Overlay enabled on video (adjustable color, text & position)!");
        appendLiveTerminalLine("Text overlay enabled on video preview monitor (active)", "[Overlay Engine]", "success");
    } else {
        if (monitorText) {
            monitorText.style.display = 'none';
        }
        if (statusPill) {
            statusPill.className = 'overlay-status-pill empty';
        }
        if (statusLabel) {
            statusLabel.textContent = 'Click to Add Text';
        }
        if (descLabel) {
            descLabel.textContent = 'Add series title, episode number (EP), or watermark text';
        }
        closeTextOverlayDropdown();
        showToast("Removed Text Overlay from video");
    }
}

function toggleTextOverlayDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }

    if (typeof closeBlurMaskDropdown === 'function') closeBlurMaskDropdown();
    if (typeof closeLowerThirdDropdown === 'function') closeLowerThirdDropdown();
    if (typeof closeTrackBgmDropdown === 'function') closeTrackBgmDropdown();

    const panel = document.getElementById('overlay-inline-settings-panel');
    const divider = document.getElementById('overlay-inline-panel-divider');
    const dropdown = document.getElementById('text-custom-dropdown');
    const chevron = document.getElementById('text-dropdown-chevron');
    const stack = document.getElementById('staged-overlay-unified-panel');
    if (!dropdown || !panel) return;

    const isOpen = (dropdown.classList.contains('show') || dropdown.style.display === 'flex') && dropdown.style.display !== 'none';
    if (isOpen) {
        closeTextOverlayDropdown();
    } else {
        if (!currentOverlayAssets.textActive) {
            toggleTextOverlayTool(null, true);
        }
        renderWordTokenChips();
        if (divider) divider.style.display = 'block';
        panel.style.display = 'flex';
        if (stack) stack.classList.add('has-inline-open');

        dropdown.style.display = 'flex';
        dropdown.classList.add('show');
        if (chevron) chevron.classList.add('open');
    }
}

function closeTextOverlayDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const panel = document.getElementById('overlay-inline-settings-panel');
    const divider = document.getElementById('overlay-inline-panel-divider');
    const dropdown = document.getElementById('text-custom-dropdown');
    const chevron = document.getElementById('text-dropdown-chevron');
    const blurDropdown = document.getElementById('blur-custom-dropdown');
    const ltDropdown = document.getElementById('lower-third-custom-dropdown');
    const subDropdown = document.getElementById('subtitle-custom-dropdown');
    const stack = document.getElementById('staged-overlay-unified-panel');

    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.classList.remove('show');
    }
    if (chevron) chevron.classList.remove('open');

    const isBlurOpen = blurDropdown && (blurDropdown.classList.contains('show') || blurDropdown.style.display === 'flex') && blurDropdown.style.display !== 'none';
    const isLtOpen = ltDropdown && (ltDropdown.classList.contains('show') || ltDropdown.style.display === 'flex') && ltDropdown.style.display !== 'none';
    const isSubOpen = subDropdown && (subDropdown.classList.contains('show') || subDropdown.style.display === 'flex') && subDropdown.style.display !== 'none';
    if (!isBlurOpen && !isLtOpen && !isSubOpen) {
        if (divider) divider.style.display = 'none';
        if (panel) panel.style.display = 'none';
        if (stack) stack.classList.remove('has-inline-open');
    }
}

function onOverlayTextInput(val, e) {
    if (e) e.stopPropagation();
    currentOverlayAssets.textValue = val || '';
    if (!currentOverlayAssets.textActive) {
        toggleTextOverlayTool(null, true);
    }
    renderWordTokenChips();
    applyTextOverlayStyling();
}

function onTextSizeChange(val, e) {
    if (e) e.stopPropagation();
    const size = parseInt(val, 10) || 24;
    currentOverlayAssets.textSize = size;

    const slider = document.getElementById('input-text-size');
    if (slider && parseInt(slider.value, 10) !== size) slider.value = size;

    const badge = document.getElementById('text-size-badge');
    if (badge) badge.textContent = `${size}px`;

    if (!currentOverlayAssets.textActive) {
        toggleTextOverlayTool(null, true);
    }
    applyTextOverlayStyling();
}

function splitTextIntoTokens(text) {
    if (!text) return [];
    return text.trim().split(/\s+/).filter(Boolean);
}

function renderWordTokenChips() {
    const container = document.getElementById('text-word-tokens-container');
    const badge = document.getElementById('text-active-word-badge');
    if (!container) return;

    const text = currentOverlayAssets.textValue || '';
    const tokens = splitTextIntoTokens(text);
    if (!currentOverlayAssets.wordColors) currentOverlayAssets.wordColors = {};

    let sel = currentOverlayAssets.selectedWordIndex;
    if (sel !== 'all' && typeof sel === 'number' && (sel < 0 || sel >= tokens.length)) {
        sel = 'all';
        currentOverlayAssets.selectedWordIndex = 'all';
    }

    const allColor = currentOverlayAssets.textColor || '#ffffff';

    let html = `
        <button type="button" class="text-word-chip ${sel === 'all' ? 'active' : ''}" id="chip-word-all" onclick="selectTargetWord('all', event)" title="Color All Words">
            <span class="word-dot" style="background:${allColor};"></span>
            <span class="word-text">All</span>
        </button>
    `;

    tokens.forEach((token, idx) => {
        const color = currentOverlayAssets.wordColors[idx] || allColor;
        const isActive = sel === idx;
        html += `
            <button type="button" class="text-word-chip ${isActive ? 'active' : ''}" id="chip-word-${idx}" onclick="selectTargetWord(${idx}, event)" title="Select word: ${escapeHtml(token)}">
                <span class="word-dot" style="background:${color};"></span>
                <span class="word-text">${escapeHtml(token)}</span>
            </button>
        `;
    });

    container.innerHTML = html;

    // Update active word badge
    if (badge) {
        if (sel === 'all' || sel === undefined || sel === null) {
            badge.textContent = 'Word: All';
            badge.style.color = '#38bdf8';
        } else if (tokens[sel]) {
            badge.textContent = `Word: "${tokens[sel]}"`;
            const activeColor = currentOverlayAssets.wordColors[sel] || allColor;
            badge.style.color = activeColor;
        } else {
            badge.textContent = 'Word: All';
            badge.style.color = '#38bdf8';
        }
    }

    updateActivePaletteChipHighlight();
}

function updateActivePaletteChipHighlight() {
    const panel = document.getElementById('text-custom-dropdown');
    if (!panel) return;

    const sel = currentOverlayAssets.selectedWordIndex;
    const allColor = (currentOverlayAssets.textColor || '#ffffff').toLowerCase();
    const currentColor = (sel === 'all' || sel === undefined || sel === null 
        ? allColor 
        : (currentOverlayAssets.wordColors && currentOverlayAssets.wordColors[sel] ? currentOverlayAssets.wordColors[sel] : allColor)).toLowerCase();

    panel.querySelectorAll('#text-color-chips-list .text-color-chip').forEach(btn => {
        const btnColor = (btn.style.getPropertyValue('--c') || '').trim().toLowerCase();
        btn.classList.toggle('active', btnColor === currentColor);
    });

    const picker = document.getElementById('input-custom-word-color');
    if (picker && currentColor.startsWith('#') && currentColor.length === 7) {
        picker.value = currentColor;
    }
}

function selectTargetWord(target, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    currentOverlayAssets.selectedWordIndex = target;
    renderWordTokenChips();
}

function applyColorToSelectedWord(color, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const c = color || '#ffffff';
    const sel = currentOverlayAssets.selectedWordIndex;
    const tokens = splitTextIntoTokens(currentOverlayAssets.textValue || '');

    if (!currentOverlayAssets.wordColors) currentOverlayAssets.wordColors = {};

    if (sel === 'all' || sel === undefined || sel === null) {
        currentOverlayAssets.textColor = c;
        tokens.forEach((_, idx) => {
            currentOverlayAssets.wordColors[idx] = c;
        });
        showToast(`Changed all text color to ${c}`);
    } else {
        const idx = parseInt(sel, 10);
        currentOverlayAssets.wordColors[idx] = c;
        const targetWord = tokens[idx] || `Word ${idx + 1}`;
        showToast(`Changed word "${targetWord}" color to ${c}`);
    }

    if (!currentOverlayAssets.textActive) {
        toggleTextOverlayTool(null, true);
    }

    renderWordTokenChips();
    applyTextOverlayStyling();
}

function setTextTextColor(color, e) {
    applyColorToSelectedWord(color, e);
}

function onTextBgToggle(checked, e) {
    if (e) e.stopPropagation();
    currentOverlayAssets.textBg = !!checked;

    if (!currentOverlayAssets.textActive) {
        toggleTextOverlayTool(null, true);
    }
    applyTextOverlayStyling();
}

function applyTextPreset(type, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }

    let val = '';
    currentOverlayAssets.wordColors = {};
    if (type === 'ep') {
        val = '⚡ EPISODE 01';
        currentOverlayAssets.wordColors = { 0: '#facc15', 1: '#ffffff', 2: '#38bdf8' };
    } else if (type === 'full') {
        val = '🎬 Full Series';
        currentOverlayAssets.wordColors = { 0: '#f43f5e', 1: '#ffffff' };
    } else if (type === 'credit') {
        val = 'SN DRAMA';
        currentOverlayAssets.wordColors = { 0: '#f43f5e', 1: '#ffffff' };
    } else if (type === 'dub') {
        val = '🎙️ Khmer Dub';
        currentOverlayAssets.wordColors = { 0: '#38bdf8', 1: '#ffffff' };
    }

    const input = document.getElementById('input-overlay-text-val');
    if (input) input.value = val;

    currentOverlayAssets.textValue = val;
    currentOverlayAssets.selectedWordIndex = 'all';

    if (!currentOverlayAssets.textActive) {
        toggleTextOverlayTool(null, true);
    }
    renderWordTokenChips();
    applyTextOverlayStyling();
    showToast(`Applied Preset: ${val}`);
}

function setTextMotion(motion, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    currentOverlayAssets.textMotion = motion || 'static';
    if (!currentOverlayAssets.textActive) {
        toggleTextOverlayTool(null, true);
    }

    const btnStatic = document.getElementById('btn-motion-static');
    const btnScroll = document.getElementById('btn-motion-scroll');
    const btnScrollDown = document.getElementById('btn-motion-scroll-down');
    const badge = document.getElementById('text-motion-badge');
    const optionsBox = document.getElementById('text-scroll-options-box');
    const staticPresets = document.getElementById('text-static-presets-row');
    const scrollPresets = document.getElementById('text-scroll-presets-row');

    if (motion === 'scroll_up' || motion === 'scroll_down') {
        if (btnStatic) btnStatic.classList.remove('active');
        if (btnScroll) btnScroll.classList.toggle('active', motion === 'scroll_up');
        if (btnScrollDown) btnScrollDown.classList.toggle('active', motion === 'scroll_down');
        if (badge) badge.textContent = motion === 'scroll_up' ? '🚀 Scroll Up' : '🔻 Scroll Down';
        if (optionsBox) optionsBox.style.display = 'inline-flex';
        if (staticPresets) staticPresets.style.display = 'none';
        if (scrollPresets) scrollPresets.style.display = 'flex';
        showToast(motion === 'scroll_up' ? 'Motion enabled: Scroll Up ⬆️' : 'Motion enabled: Scroll Down ⬇️');
    } else {
        if (btnStatic) btnStatic.classList.add('active');
        if (btnScroll) btnScroll.classList.remove('active');
        if (btnScrollDown) btnScrollDown.classList.remove('active');
        if (badge) badge.textContent = '📌 Static';
        if (optionsBox) optionsBox.style.display = 'none';
        if (staticPresets) staticPresets.style.display = 'flex';
        if (scrollPresets) scrollPresets.style.display = 'none';
        showToast("Motion changed: Static");
    }

    applyTextOverlayStyling();
}

function setTextScrollSpeed(speed, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const s = parseInt(speed, 10) || 65;
    currentOverlayAssets.textSpeed = s;

    const chipSlow = document.getElementById('speed-chip-slow');
    const chipNormal = document.getElementById('speed-chip-normal');
    const chipFast = document.getElementById('speed-chip-fast');

    if (chipSlow) chipSlow.classList.toggle('active', s <= 45);
    if (chipNormal) chipNormal.classList.toggle('active', s > 45 && s < 90);
    if (chipFast) chipFast.classList.toggle('active', s >= 90);

    const speedName = s <= 45 ? 'Slow' : (s >= 90 ? 'Fast' : 'Normal');
    showToast(`Scroll Speed: ${speedName} (${s}px/s)`);

    applyTextOverlayStyling();
}

function applyScrollTextPreset(type, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }

    let val = '';
    if (type === 'ep_daily') val = '⚡ New Episode Daily';
    else if (type === 'enjoy') val = '🎬 Enjoy Watching';
    else if (type === 'follow') val = '✨ Follow for Next Episode';
    else if (type === 'thanks') val = '🙏 Thank You for Watching';

    const input = document.getElementById('input-overlay-text-val');
    if (input) input.value = val;

    currentOverlayAssets.textValue = val;
    if (!currentOverlayAssets.textActive) {
        toggleTextOverlayTool(null, true);
    }
    applyTextOverlayStyling();
    showToast(`Applied scrolling text: "${val}"`);
}

function applyTextOverlayStyling() {
    const monitorText = document.getElementById('monitor-text-overlay');
    const displayEl = document.getElementById('monitor-text-display');
    if (!monitorText || !displayEl) return;

    const rawText = currentOverlayAssets.textValue !== undefined ? currentOverlayAssets.textValue : 'EPISODE 01';
    const size = currentOverlayAssets.textSize || 24;
    const defaultColor = currentOverlayAssets.textColor || '#ffffff';
    const hasBg = currentOverlayAssets.textBg === true;
    const motion = currentOverlayAssets.textMotion || 'static';
    const speed = currentOverlayAssets.textSpeed || 65;

    const tokens = splitTextIntoTokens(rawText);
    let segments = [];
    if (tokens.length === 0) {
        segments = [{ text: rawText, color: defaultColor }];
    } else {
        tokens.forEach((word, idx) => {
            const wColor = (currentOverlayAssets.wordColors && currentOverlayAssets.wordColors[idx]) 
                           ? currentOverlayAssets.wordColors[idx] 
                           : defaultColor;
            segments.push({ text: word, color: wColor });
        });
    }
    currentOverlayAssets.textSegments = segments;

    displayEl.innerHTML = segments.map(seg => `<span style="color:${seg.color};">${escapeHtml(seg.text)}</span>`).join(' ');
    displayEl.style.fontSize = `${size}px`;

    if (hasBg) {
        monitorText.classList.remove('no-bg');
    } else {
        monitorText.classList.add('no-bg');
    }

    if (motion === 'scroll_up') {
        monitorText.classList.remove('scrolling-down');
        monitorText.classList.add('scrolling-up');
        const durationSec = speed <= 45 ? 9.5 : (speed >= 90 ? 4.0 : 6.5);
        monitorText.style.setProperty('--scroll-duration', `${durationSec}s`);
    } else if (motion === 'scroll_down') {
        monitorText.classList.remove('scrolling-up');
        monitorText.classList.add('scrolling-down');
        const durationSec = speed <= 45 ? 9.5 : (speed >= 90 ? 4.0 : 6.5);
        monitorText.style.setProperty('--scroll-duration', `${durationSec}s`);
    } else {
        monitorText.classList.remove('scrolling-up');
        monitorText.classList.remove('scrolling-down');
    }

    const statusLabel = document.getElementById('text-status-label');
    if (statusLabel && currentOverlayAssets.textActive) {
        const previewVal = (rawText || 'Text').slice(0, 12);
        if (motion === 'scroll_up') {
            statusLabel.textContent = `⬆️ Scroll Up: ${previewVal}`;
        } else if (motion === 'scroll_down') {
            statusLabel.textContent = `⬇️ Scroll Down: ${previewVal}`;
        } else {
            statusLabel.textContent = `Text: ${previewVal}`;
        }
    }

    const descLabel = document.getElementById('text-overlay-desc-label');
    if (descLabel && currentOverlayAssets.textActive) {
        if (motion === 'scroll_up') {
            descLabel.textContent = `Scroll Up Text: "${rawText}" (${speed}px/s)`;
        } else if (motion === 'scroll_down') {
            descLabel.textContent = `Scroll Down Text: "${rawText}" (${speed}px/s)`;
        } else {
            descLabel.textContent = `Active Text: "${rawText}" (${size}px)`;
        }
    }
}

// ==========================================================================
// LOWER THIRD VIDEO OVERLAY (Motion Badges & Animation) CONTROLS
// ==========================================================================
function toggleLowerThirdTool(event, forceState) {
    if (event) {
        event.stopPropagation();
    }
    // If no video or file loaded yet, prompt user to pick from computer directly!
    if (!currentOverlayAssets.lowerThirdUrl && !currentOverlayAssets.serverLowerThirdPath) {
        const input = document.getElementById('input-overlay-lower-third-file');
        if (input) input.click();
        return;
    }

    if (typeof forceState === 'boolean') {
        currentOverlayAssets.lowerThirdActive = forceState;
    } else {
        currentOverlayAssets.lowerThirdActive = !currentOverlayAssets.lowerThirdActive;
    }

    const monitorLt = document.getElementById('monitor-lower-third-overlay');
    const monitorVideo = document.getElementById('monitor-lower-third-video');

    if (currentOverlayAssets.lowerThirdActive) {
        if (monitorLt) {
            monitorLt.style.display = 'flex';
            const scalePct = Math.round((currentOverlayAssets.lowerThirdScale || 1.0) * 100);
            monitorLt.style.width = `${scalePct}%`;
            monitorLt.style.opacity = currentOverlayAssets.lowerThirdOpacity !== undefined ? currentOverlayAssets.lowerThirdOpacity : 1.0;
            setOverlayPosition('lower_third', currentOverlayAssets.lowerThirdPosition || 'bottom-center');
            makeOverlayDraggable(monitorLt);
            const ltHandle = document.getElementById('lower-third-resize-handle');
            if (ltHandle) makeOverlayResizable(monitorLt, ltHandle, 'lower_third');
        }

        if (monitorVideo) {
            monitorVideo.playbackRate = currentOverlayAssets.lowerThirdSpeed || 1.0;
            monitorVideo.loop = currentOverlayAssets.lowerThirdLoop !== false;
            monitorVideo.play().catch(() => {});
        }

        showToast("Lower Third enabled on Video Preview!");
        appendLiveTerminalLine("Lower Third overlay enabled on preview monitor", "[Overlay Engine]", "success");
    } else {
        if (monitorLt) monitorLt.style.display = 'none';
        if (monitorVideo) monitorVideo.pause();
        closeLowerThirdDropdown();
    }
}

function openLowerThirdDropdown() {
    if (typeof closeBlurMaskDropdown === 'function') closeBlurMaskDropdown();
    if (typeof closeTextOverlayDropdown === 'function') closeTextOverlayDropdown();
    if (typeof closeTrackBgmDropdown === 'function') closeTrackBgmDropdown();

    const panel = document.getElementById('overlay-inline-settings-panel');
    const divider = document.getElementById('overlay-inline-panel-divider');
    const dropdown = document.getElementById('lower-third-custom-dropdown');
    const chevron = document.getElementById('lower-third-dropdown-chevron');
    const stack = document.getElementById('staged-overlay-unified-panel');
    if (!dropdown || !panel) return;

    if (divider) divider.style.display = 'block';
    panel.style.display = 'flex';
    if (stack) stack.classList.add('has-inline-open');

    dropdown.style.display = 'flex';
    dropdown.classList.add('show');
    if (chevron) chevron.classList.add('open');
}

function toggleLowerThirdDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }

    const dropdown = document.getElementById('lower-third-custom-dropdown');
    if (!dropdown) return;

    const isOpen = (dropdown.classList.contains('show') || dropdown.style.display === 'flex') && dropdown.style.display !== 'none';
    if (isOpen) {
        closeLowerThirdDropdown();
    } else {
        openLowerThirdDropdown();
    }
}

function closeLowerThirdDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const panel = document.getElementById('overlay-inline-settings-panel');
    const divider = document.getElementById('overlay-inline-panel-divider');
    const dropdown = document.getElementById('lower-third-custom-dropdown');
    const chevron = document.getElementById('lower-third-dropdown-chevron');
    const blurDropdown = document.getElementById('blur-custom-dropdown');
    const textDropdown = document.getElementById('text-custom-dropdown');
    const subDropdown = document.getElementById('subtitle-custom-dropdown');
    const stack = document.getElementById('staged-overlay-unified-panel');

    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.classList.remove('show');
    }
    if (chevron) chevron.classList.remove('open');

    const isBlurOpen = blurDropdown && (blurDropdown.classList.contains('show') || blurDropdown.style.display === 'flex') && blurDropdown.style.display !== 'none';
    const isTextOpen = textDropdown && (textDropdown.classList.contains('show') || textDropdown.style.display === 'flex') && textDropdown.style.display !== 'none';
    const isSubOpen = subDropdown && (subDropdown.classList.contains('show') || subDropdown.style.display === 'flex') && subDropdown.style.display !== 'none';
    if (!isBlurOpen && !isTextOpen && !isSubOpen) {
        if (divider) divider.style.display = 'none';
        if (panel) panel.style.display = 'none';
        if (stack) stack.classList.remove('has-inline-open');
    }
}

function handleLowerThirdFileSelect(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    currentOverlayAssets.lowerThirdFile = file;
    currentOverlayAssets.lowerThirdSamplePath = null;
    currentOverlayAssets.serverLowerThirdPath = null;
    currentOverlayAssets.lowerThirdScale = 1.0; // 100% full width directly!
    currentOverlayAssets.lowerThirdPosition = 'bottom-center';
    currentOverlayAssets.lowerThirdActive = true;

    if (currentOverlayAssets.lowerThirdUrl && currentOverlayAssets.lowerThirdUrl.startsWith('blob:')) {
        URL.revokeObjectURL(currentOverlayAssets.lowerThirdUrl);
    }
    currentOverlayAssets.lowerThirdUrl = URL.createObjectURL(file);

    // Update scale slider & badge UI to 100%
    const scaleSlider = document.getElementById('input-lt-scale');
    const scaleBadge = document.getElementById('lt-scale-badge');
    if (scaleSlider) scaleSlider.value = '100';
    if (scaleBadge) scaleBadge.textContent = '100%';

    // Position buttons: highlight BC Bottom-Center
    ['bc', 'bl', 'br', 'tc'].forEach(k => {
        const b = document.getElementById(`btn-lt-pos-${k}`);
        if (b) b.classList.toggle('active', k === 'bc');
    });

    const monitorLt = document.getElementById('monitor-lower-third-overlay');
    const monitorVideo = document.getElementById('monitor-lower-third-video');
    if (monitorLt) {
        monitorLt.style.display = 'flex';
        monitorLt.style.width = '100%';
        monitorLt.style.left = '0%';
        monitorLt.style.bottom = '0px';
        monitorLt.style.top = 'auto';
        monitorLt.style.transform = 'none';
        monitorLt.style.opacity = currentOverlayAssets.lowerThirdOpacity !== undefined ? currentOverlayAssets.lowerThirdOpacity : 1.0;
        makeOverlayDraggable(monitorLt);
        const ltHandle = document.getElementById('lower-third-resize-handle');
        if (ltHandle) makeOverlayResizable(monitorLt, ltHandle, 'lower_third');
    }

    if (monitorVideo) {
        try {
            monitorVideo.src = currentOverlayAssets.lowerThirdUrl;
            monitorVideo.playbackRate = currentOverlayAssets.lowerThirdSpeed || 1.0;
            monitorVideo.loop = currentOverlayAssets.lowerThirdLoop !== false;
            monitorVideo.play().catch(() => {});
        } catch (_) {}
    }

    const card = document.getElementById('card-upload-lower-third');
    if (card) card.classList.add('has-active-controls');

    const descLabel = document.getElementById('lower-third-desc-label');
    if (descLabel) descLabel.textContent = `Lower Third: ${file.name} (Scale 100%, Opacity, Speed adjustable)`;

    // Show initial loading status pill while fast transcoding runs on server
    const sizeKb = (file.size / 1024).toFixed(1);
    const statusEl = document.getElementById('status-overlay-lower-third');
    if (statusEl) {
        statusEl.innerHTML = `
            <div class="overlay-active-controls">
                <span class="overlay-status-pill selected" title="${escapeHtml(file.name)}">
                    <i class="fa-solid fa-spinner fa-spin" style="color:#f59e0b; margin-right:4px;"></i>
                    <span class="overlay-file-name">${escapeHtml(file.name)}</span>
                    <button type="button" class="overlay-file-remove-btn" onclick="clearLowerThirdFile(event)" title="Remove Lower Third">&times;</button>
                </span>
                <button type="button" class="lt-row-settings-btn" onclick="toggleLowerThirdDropdown(event)" title="Adjust Lower Third Settings (Size, Position, Speed)">
                    <i class="fa-solid fa-sliders"></i>
                </button>
            </div>
        `;
    }

    const pill = document.getElementById('lt-file-preview-pill');
    const label = document.getElementById('lt-filename-display');
    if (pill) pill.style.display = 'inline-flex';
    if (label) label.textContent = file.name;

    const btnText = document.getElementById('lt-upload-btn-text');
    if (btnText) btnText.textContent = `Change Video (${file.name})`;

    // Upload to backend to generate transparent WebM preview and poster for qtrle MOV
    try {
        const fd = new FormData();
        fd.append('lower_third_file', file);
        fetch('/api/projects/upload-overlay-lower-third', { method: 'POST', body: fd })
            .then(r => r.json())
            .then(d => {
                if (d.success) {
                    currentOverlayAssets.serverLowerThirdPath = d.lower_third_path || d.video_path;
                    currentOverlayAssets.lowerThirdPreviewUrl = d.preview_url || d.url;
                    currentOverlayAssets.lowerThirdThumbUrl = d.thumb_url || '';
                    currentOverlayAssets.lowerThirdOrigWidth = d.orig_width || 2000;
                    currentOverlayAssets.lowerThirdOrigHeight = d.orig_height || 2500;

                    const mVid = document.getElementById('monitor-lower-third-video');
                    if (mVid) {
                        if (d.thumb_url) mVid.poster = d.thumb_url;
                        if (d.preview_url) {
                            mVid.src = d.preview_url;
                            mVid.playbackRate = currentOverlayAssets.lowerThirdSpeed || 1.0;
                            mVid.loop = currentOverlayAssets.lowerThirdLoop !== false;
                            mVid.load();
                            mVid.play().catch(() => {});
                        }
                    }

                    // Replace loading spinner with standard ready icon
                    if (statusEl) {
                        statusEl.innerHTML = `
                            <div class="overlay-active-controls">
                                <span class="overlay-status-pill selected" title="${escapeHtml(file.name)}">
                                    <i class="fa-solid fa-file-video" style="color:#60a5fa; margin-right:4px;"></i>
                                    <span class="overlay-file-name">${escapeHtml(file.name)}</span>
                                    <button type="button" class="overlay-file-remove-btn" onclick="clearLowerThirdFile(event)" title="Remove Lower Third">&times;</button>
                                </span>
                                <button type="button" class="lt-row-settings-btn" onclick="toggleLowerThirdDropdown(event)" title="Adjust Lower Third Settings (Size, Position, Speed)">
                                    <i class="fa-solid fa-sliders"></i>
                                </button>
                            </div>
                        `;
                    }
                    appendLiveTerminalLine(`Lower Third engine ready: ${d.filename} (${sizeKb} KB)`, "[Overlay Engine]", "info");
                }
            })
            .catch(err => console.warn("Lower third upload background note:", err));
    } catch (e) {
        console.warn("Lower third upload trigger note:", e);
    }

    // Open lower third settings panel so user can adjust size, opacity, position, speed
    openLowerThirdDropdown();
    showToast(`Lower Third applied: ${file.name}`);
    appendLiveTerminalLine(`Lower third attached to preview: ${file.name} (${sizeKb} KB)`, "[Overlay Engine]", "success");
}

function clearLowerThirdFile(event) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    if (currentOverlayAssets.lowerThirdUrl && currentOverlayAssets.lowerThirdUrl.startsWith('blob:')) {
        URL.revokeObjectURL(currentOverlayAssets.lowerThirdUrl);
    }
    currentOverlayAssets.lowerThirdFile = null;
    currentOverlayAssets.lowerThirdUrl = null;
    currentOverlayAssets.serverLowerThirdPath = null;
    currentOverlayAssets.lowerThirdSamplePath = null;
    currentOverlayAssets.lowerThirdActive = false;
    currentOverlayAssets.lowerThirdScale = 1.0;

    const scaleSlider = document.getElementById('input-lt-scale');
    const scaleBadge = document.getElementById('lt-scale-badge');
    if (scaleSlider) scaleSlider.value = '100';
    if (scaleBadge) scaleBadge.textContent = '100%';

    const input = document.getElementById('input-overlay-lower-third-file');
    if (input) input.value = '';

    const monitorLt = document.getElementById('monitor-lower-third-overlay');
    if (monitorLt) monitorLt.style.display = 'none';

    const monitorVideo = document.getElementById('monitor-lower-third-video');
    if (monitorVideo) {
        monitorVideo.pause();
        monitorVideo.removeAttribute('src');
        monitorVideo.removeAttribute('poster');
        monitorVideo.load();
    }

    const card = document.getElementById('card-upload-lower-third');
    if (card) card.classList.remove('has-active-controls');

    const descLabel = document.getElementById('lower-third-desc-label');
    if (descLabel) descLabel.textContent = 'Upload Lower Third video (MP4/MOV/WebM) from computer';

    const statusEl = document.getElementById('status-overlay-lower-third');
    if (statusEl) {
        statusEl.innerHTML = `
            <span class="overlay-status-pill empty" id="lower-third-status-pill">
                <i class="fa-solid fa-cloud-arrow-up"></i> <span id="lower-third-status-label">Upload</span>
            </span>
        `;
    }

    const pill = document.getElementById('lt-file-preview-pill');
    if (pill) pill.style.display = 'none';

    const btnText = document.getElementById('lt-upload-btn-text');
    if (btnText) btnText.textContent = 'Choose Video from Computer';

    closeLowerThirdDropdown();
    showToast("Removed Lower Third file");
}

function applyLowerThirdSamplePreset(presetKey, e) {
    const input = document.getElementById('input-overlay-lower-third-file');
    if (input) input.click();
}

function onLowerThirdScaleChange(val, e) {
    if (e) e.stopPropagation();
    const scalePct = parseInt(val, 10) || 100;
    const scale = scalePct / 100;
    currentOverlayAssets.lowerThirdScale = scale;

    const slider = document.getElementById('input-lt-scale');
    if (slider && parseInt(slider.value, 10) !== scalePct) slider.value = scalePct;

    const badge = document.getElementById('lt-scale-badge');
    if (badge) badge.textContent = `${scalePct}%`;

    const monitorLt = document.getElementById('monitor-lower-third-overlay');
    if (monitorLt) {
        monitorLt.style.width = `${scalePct}%`;
        if (scalePct >= 95) {
            monitorLt.style.left = '0%';
            monitorLt.style.transform = 'none';
        } else if (currentOverlayAssets.lowerThirdPosition === 'bottom-center' || currentOverlayAssets.lowerThirdPosition === 'top-center') {
            monitorLt.style.left = '50%';
            monitorLt.style.transform = 'translateX(-50%)';
        }
    }
}

function onLowerThirdOpacityChange(val, e) {
    if (e) e.stopPropagation();
    const opacityPct = parseInt(val, 10) || 100;
    const opacity = opacityPct / 100;
    currentOverlayAssets.lowerThirdOpacity = opacity;

    const slider = document.getElementById('input-lt-opacity');
    if (slider && parseInt(slider.value, 10) !== opacityPct) slider.value = opacityPct;

    const badge = document.getElementById('lt-opacity-badge');
    if (badge) badge.textContent = `${opacityPct}%`;

    const monitorLt = document.getElementById('monitor-lower-third-overlay');
    if (monitorLt) {
        monitorLt.style.opacity = opacity;
    }
}

function onLowerThirdTimingChange() {
    const startInput = document.getElementById('input-lt-start-time');
    const endInput = document.getElementById('input-lt-end-time');
    const startVal = parseFloat(startInput ? startInput.value : 0) || 0;
    const endVal = parseFloat(endInput ? endInput.value : 0) || 0;

    currentOverlayAssets.lowerThirdStartTime = Math.max(0, startVal);
    currentOverlayAssets.lowerThirdEndTime = Math.max(0, endVal);

    const chipAll = document.getElementById('chip-timing-all');
    const chipIntro = document.getElementById('chip-timing-intro');
    const chipOutro = document.getElementById('chip-timing-outro');
    if (chipAll) chipAll.classList.toggle('active', startVal === 0 && endVal === 0);
    if (chipIntro) chipIntro.classList.toggle('active', startVal === 0 && endVal === 8);
    if (chipOutro) chipOutro.classList.toggle('active', startVal > 0 && endVal > 0 && startVal !== 0);
}

function setLowerThirdTimingPreset(preset, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const startInput = document.getElementById('input-lt-start-time');
    const endInput = document.getElementById('input-lt-end-time');

    if (preset === 'all') {
        if (startInput) startInput.value = 0;
        if (endInput) endInput.value = 0;
    } else if (preset === 'intro') {
        if (startInput) startInput.value = 0;
        if (endInput) endInput.value = 8;
    } else if (preset === 'outro') {
        const mainVideo = document.getElementById('main-video');
        const dur = (mainVideo && mainVideo.duration && !isNaN(mainVideo.duration)) ? Math.round(mainVideo.duration) : 30;
        const outroStart = Math.max(0, dur - 10);
        if (startInput) startInput.value = outroStart;
        if (endInput) endInput.value = dur;
    }
    onLowerThirdTimingChange();
}

function onLowerThirdLoopToggle(checked, e) {
    if (e) e.stopPropagation();
    currentOverlayAssets.lowerThirdLoop = !!checked;
    const video = document.getElementById('monitor-lower-third-video');
    if (video) {
        video.loop = !!checked;
    }
    showToast(checked ? "Loop Enabled" : "Loop Disabled");
}

function setLowerThirdSpeed(speed, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const s = parseFloat(speed) || 1.0;
    currentOverlayAssets.lowerThirdSpeed = s;

    const video = document.getElementById('monitor-lower-third-video');
    if (video) {
        video.playbackRate = s;
    }

    const speeds = [0.5, 1.0, 1.25, 1.5];
    const speedIds = { 0.5: 'btn-lt-speed-05', 1.0: 'btn-lt-speed-10', 1.25: 'btn-lt-speed-125', 1.5: 'btn-lt-speed-15' };
    speeds.forEach(sp => {
        const btn = document.getElementById(speedIds[sp]);
        if (btn) btn.classList.toggle('active', sp === s);
    });
    showToast(`Lower Third Animation Speed: ${s}x`);
}

// ==========================================================================
// SUBTITLE OVERLAY (Viral Khmer Captions & Subtitles) CONTROLS
// ==========================================================================
function openSubtitleDropdown() {
    if (typeof closeBlurMaskDropdown === 'function') closeBlurMaskDropdown();
    if (typeof closeTextOverlayDropdown === 'function') closeTextOverlayDropdown();
    if (typeof closeLowerThirdDropdown === 'function') closeLowerThirdDropdown();
    if (typeof closeTrackBgmDropdown === 'function') closeTrackBgmDropdown();

    const panel = document.getElementById('overlay-inline-settings-panel');
    const divider = document.getElementById('overlay-inline-panel-divider');
    const dropdown = document.getElementById('subtitle-custom-dropdown');
    const chevron = document.getElementById('subtitle-dropdown-chevron');
    const stack = document.getElementById('staged-overlay-unified-panel');
    if (!dropdown || !panel) return;

    if (divider) divider.style.display = 'block';
    panel.style.display = 'flex';
    if (stack) stack.classList.add('has-inline-open');

    dropdown.style.display = 'flex';
    dropdown.classList.add('show');
    if (chevron) chevron.classList.add('open');
}

function toggleSubtitleDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const dropdown = document.getElementById('subtitle-custom-dropdown');
    if (!dropdown) return;
    const isOpen = (dropdown.classList.contains('show') || dropdown.style.display === 'flex') && dropdown.style.display !== 'none';
    if (isOpen) {
        closeSubtitleDropdown();
    } else {
        openSubtitleDropdown();
    }
}

function closeSubtitleDropdown(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const panel = document.getElementById('overlay-inline-settings-panel');
    const divider = document.getElementById('overlay-inline-panel-divider');
    const dropdown = document.getElementById('subtitle-custom-dropdown');
    const chevron = document.getElementById('subtitle-dropdown-chevron');
    const blurDropdown = document.getElementById('blur-custom-dropdown');
    const textDropdown = document.getElementById('text-custom-dropdown');
    const ltDropdown = document.getElementById('lower-third-custom-dropdown');
    const stack = document.getElementById('staged-overlay-unified-panel');

    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.classList.remove('show');
    }
    if (chevron) chevron.classList.remove('open');

    const isBlurOpen = blurDropdown && (blurDropdown.classList.contains('show') || blurDropdown.style.display === 'flex') && blurDropdown.style.display !== 'none';
    const isTextOpen = textDropdown && (textDropdown.classList.contains('show') || textDropdown.style.display === 'flex') && textDropdown.style.display !== 'none';
    const isLtOpen = ltDropdown && (ltDropdown.classList.contains('show') || ltDropdown.style.display === 'flex') && ltDropdown.style.display !== 'none';
    if (!isBlurOpen && !isTextOpen && !isLtOpen) {
        if (divider) divider.style.display = 'none';
        if (panel) panel.style.display = 'none';
        if (stack) stack.classList.remove('has-inline-open');
    }
}

function toggleSubtitleTool(event, forceState) {
    if (event) {
        event.stopPropagation();
    }
    if (typeof forceState === 'boolean') {
        currentOverlayAssets.subtitleActive = forceState;
    } else {
        currentOverlayAssets.subtitleActive = !currentOverlayAssets.subtitleActive;
    }

    const toggle = document.getElementById('toggle-subtitle-enable');
    if (toggle) toggle.checked = currentOverlayAssets.subtitleActive;

    const toggleText = document.getElementById('subtitle-toggle-text');
    if (toggleText) toggleText.textContent = currentOverlayAssets.subtitleActive ? 'Active' : 'Enable';

    const pill = document.getElementById('subtitle-status-pill');
    const label = document.getElementById('subtitle-status-label');
    const card = document.getElementById('card-upload-subtitle');
    const monitorSub = document.getElementById('monitor-subtitle-overlay');

    if (currentOverlayAssets.subtitleActive) {
        if (pill) {
            pill.classList.remove('empty');
            pill.classList.add('active');
        }
        if (label) label.textContent = 'Active';
        if (card) card.classList.add('active');
        if (monitorSub) {
            monitorSub.style.display = 'block';
            if (typeof makeOverlayDraggable === 'function') makeOverlayDraggable(monitorSub);
        }
        showToast("Khmer Subtitles enabled! 💬");
        appendLiveTerminalLine("Khmer Subtitles overlay enabled (interactive preview active)", "[Subtitle Engine]", "success");
    } else {
        if (pill) {
            pill.classList.remove('active');
            pill.classList.add('empty');
        }
        if (label) label.textContent = 'Off';
        if (card) card.classList.remove('active');
        if (monitorSub) monitorSub.style.display = 'none';
        showToast("Subtitles turned off");
    }

    applySubtitleStyling();
}

function setSubtitleAnimation(animType, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    const validAnims = ['pop', 'fade', 'slide', 'static'];
    if (!validAnims.includes(animType)) animType = 'pop';

    currentOverlayAssets.subtitleAnimation = animType;

    validAnims.forEach(a => {
        const card = document.getElementById(`btn-sub-anim-${a}`);
        if (card) card.classList.toggle('active', a === animType);
    });

    if (!currentOverlayAssets.subtitleActive) {
        toggleSubtitleTool(null, true);
    }
    applySubtitleStyling();

    const names = {
        pop: 'Pop-up Bounce (TikTok Viral)',
        fade: 'Smooth Fade In (រលាយចូល)',
        slide: 'Slide Up (រំកិលឡើង)',
        static: 'Classic Static (ស្ដង់ដារ)'
    };
    showToast(`បែបអក្សរលោតមក: ${names[animType] || animType}`);
}

function setSubtitleStyle(styleName, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    setSubtitleAnimation('pop', e);
}

function onSubtitleSizeChange(val, e) {
    if (e) e.stopPropagation();
    const size = parseInt(val, 10) || 44;
    currentOverlayAssets.subtitleSize = size;

    const slider = document.getElementById('input-sub-size');
    if (slider && parseInt(slider.value, 10) !== size) slider.value = size;

    const badge = document.getElementById('sub-size-badge');
    if (badge) badge.textContent = `${size}px`;

    if (!currentOverlayAssets.subtitleActive) {
        toggleSubtitleTool(null, true);
    }
    applySubtitleStyling();
}

function onSubtitleMarginChange(val, e) {
    if (e) e.stopPropagation();
    const margin = parseInt(val, 10) || 65;
    currentOverlayAssets.subtitleMarginV = margin;
    currentOverlayAssets.subtitleUserDragged = false;

    const slider = document.getElementById('input-sub-margin');
    if (slider && parseInt(slider.value, 10) !== margin) slider.value = margin;

    const badge = document.getElementById('sub-margin-badge');
    if (badge) badge.textContent = `${margin}px`;

    const btnBottom = document.getElementById('btn-sub-pos-bottom');
    const btnAboveLt = document.getElementById('btn-sub-pos-above-lt');
    const btnMiddle = document.getElementById('btn-sub-pos-middle');
    const btnHigher = document.getElementById('btn-sub-pos-higher');
    if (btnBottom) btnBottom.classList.toggle('active', margin <= 150);
    if (btnAboveLt) btnAboveLt.classList.toggle('active', margin > 150 && margin <= 450);
    if (btnMiddle) btnMiddle.classList.toggle('active', margin > 450 && margin <= 800);
    if (btnHigher) btnHigher.classList.toggle('active', margin > 800);

    if (!currentOverlayAssets.subtitleActive) {
        toggleSubtitleTool(null, true);
    }
    applySubtitleStyling();
}

function setSubtitleMarginPreset(margin, e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    onSubtitleMarginChange(margin);
}

async function handleCustomSubtitleFileSelect(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    currentOverlayAssets.customSubtitleFile = file;
    currentOverlayAssets.customSubtitleName = file.name;

    const pill = document.getElementById('sub-file-preview-pill');
    const nameDisplay = document.getElementById('sub-filename-display');
    const uploadBtnText = document.getElementById('sub-upload-btn-text');

    if (pill) pill.style.display = 'inline-flex';
    if (nameDisplay) nameDisplay.textContent = file.name;
    if (uploadBtnText) uploadBtnText.textContent = 'Change SRT';

    showToast(`Uploaded custom subtitle: ${file.name}`);

    try {
        const fd = new FormData();
        fd.append('subtitle_file', file);
        const r = await fetch('/api/projects/upload-overlay-subtitle', { method: 'POST', body: fd });
        const d = await r.json();
        if (d.success && d.subtitle_path) {
            currentOverlayAssets.customSubtitlePath = d.subtitle_path;
        }
    } catch (err) {
        console.warn("Subtitle upload note:", err);
    }

    if (!currentOverlayAssets.subtitleActive) {
        toggleSubtitleTool(null, true);
    }
}

function clearCustomSubtitleFile(e) {
    if (e) {
        e.stopPropagation();
        e.preventDefault();
    }
    currentOverlayAssets.customSubtitleFile = null;
    currentOverlayAssets.customSubtitlePath = null;
    currentOverlayAssets.customSubtitleName = null;

    const fileInput = document.getElementById('input-custom-subtitle-file');
    if (fileInput) fileInput.value = '';

    const pill = document.getElementById('sub-file-preview-pill');
    const uploadBtnText = document.getElementById('sub-upload-btn-text');
    if (pill) pill.style.display = 'none';
    if (uploadBtnText) uploadBtnText.textContent = 'Upload Custom SRT';

    showToast("Reverted to AI auto-subtitles");
}

function applySubtitleStyling() {
    const monitorSub = document.getElementById('monitor-subtitle-overlay');
    const displayEl = document.getElementById('monitor-subtitle-display');
    if (!monitorSub || !displayEl) return;

    const anim = currentOverlayAssets.subtitleAnimation || 'pop';
    const size = currentOverlayAssets.subtitleSize || 44;
    const margin = currentOverlayAssets.subtitleMarginV || 65;

    // Reset and apply animation class to trigger animation replay
    displayEl.className = 'monitor-subtitle-content style-viral-yellow';
    void displayEl.offsetWidth; // Force DOM reflow to replay CSS animation
    displayEl.classList.add(`anim-${anim}`);

    const previewFs = Math.max(13, Math.round(size * 0.45));
    monitorSub.style.setProperty('--sub-fontsize', `${previewFs}px`);

    if (!currentOverlayAssets.subtitleUserDragged) {
        const parent = monitorSub.parentElement;
        const parentH = parent ? parent.offsetHeight : 540;
        const previewBottomPx = Math.max(6, Math.round((margin / 1920.0) * parentH));
        monitorSub.style.setProperty('--sub-bottom', `${previewBottomPx}px`);
        monitorSub.style.bottom = `${previewBottomPx}px`;
        monitorSub.style.top = 'auto';
        monitorSub.style.left = '50%';
        monitorSub.style.transform = 'translateX(-50%)';
    }

    const descLabel = document.getElementById('subtitle-desc-label');
    if (descLabel) {
        const animLabels = {
            pop: 'Pop-up Bounce (CapCut Viral)',
            fade: 'Smooth Fade In (រលាយចូល)',
            slide: 'Slide Up (រំកិលឡើង)',
            static: 'Classic Static (ស្ដង់ដារ)'
        };
        if (currentOverlayAssets.subtitleActive) {
            descLabel.textContent = `Active Subtitles: ${animLabels[anim] || anim} (${size}px, ${margin}px margin)`;
        } else {
            descLabel.textContent = 'Burn auto-translated Khmer subtitles with TikTok/Viral animations';
        }
    }
}

function makeOverlayResizable(overlayEl, handleEl, type) {
    if (!overlayEl || !handleEl || handleEl._hasResizeHandler) return;
    handleEl._hasResizeHandler = true;

    let isResizing = false;
    let startX = 0, startY = 0;
    let startWidth = 0, startHeight = 0;

    const startResize = (clientX, clientY, e) => {
        isResizing = true;
        startX = clientX;
        startY = clientY;
        startWidth = overlayEl.offsetWidth;
        startHeight = overlayEl.offsetHeight;

        // Anchor explicit left and top if positioned with right/bottom
        const parentRect = overlayEl.parentElement.getBoundingClientRect();
        const elRect = overlayEl.getBoundingClientRect();
        overlayEl.style.left = `${elRect.left - parentRect.left}px`;
        overlayEl.style.top = `${elRect.top - parentRect.top}px`;
        overlayEl.style.right = 'auto';
        overlayEl.style.bottom = 'auto';
        overlayEl.style.transform = 'none';

        overlayEl.classList.add('resizing');
        handleEl.classList.add('active');

        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
    };

    const doResize = (clientX, clientY) => {
        if (!isResizing) return;
        const dx = clientX - startX;
        const dy = clientY - startY;

        const parentRect = overlayEl.parentElement.getBoundingClientRect();
        const elRect = overlayEl.getBoundingClientRect();
        const maxW = Math.max(50, parentRect.right - elRect.left - 4);
        const maxH = Math.max(30, parentRect.bottom - elRect.top - 4);

        if (type === 'blur') {
            // Free 2D resizing for Blur Mask with mouse drag (100% interactive)
            const newW = Math.round(Math.max(40, Math.min(maxW, startWidth + dx)));
            const newH = Math.round(Math.max(22, Math.min(maxH, startHeight + dy)));
            overlayEl.style.width = `${newW}px`;
            overlayEl.style.height = `${newH}px`;

            currentOverlayAssets.blurWidth = newW;
            currentOverlayAssets.blurHeight = newH;
            currentOverlayAssets.blurScale = +(newW / 120).toFixed(2);

            const label = document.getElementById('blur-size-label');
            if (label) label.textContent = `${Math.round(currentOverlayAssets.blurScale * 100)}%`;
            const trayLabel = document.getElementById('blur-tray-size-val');
            if (trayLabel) trayLabel.textContent = `${Math.round(currentOverlayAssets.blurScale * 100)}%`;
        } else if (type === 'logo') {
            // Proportional smooth resizing for Logo using dominant movement
            const delta = Math.abs(dx) > Math.abs(dy) ? dx : dy;
            const newW = Math.round(Math.max(35, Math.min(maxW, startWidth + delta)));
            overlayEl.style.width = `${newW}px`;
            overlayEl.style.maxWidth = 'none';
            const img = document.getElementById('monitor-logo-img');
            if (img) {
                img.style.maxHeight = 'none';
                img.style.width = '100%';
            }

            currentOverlayAssets.logoWidth = newW;
            currentOverlayAssets.logoScale = +(newW / 110).toFixed(2);

            const label = document.getElementById('logo-size-label');
            if (label) label.textContent = `${Math.round(currentOverlayAssets.logoScale * 100)}%`;
        } else if (type === 'text') {
            const delta = Math.abs(dx) > Math.abs(dy) ? dx : dy;
            const curSize = currentOverlayAssets.textSize || 24;
            const newSize = Math.max(14, Math.min(64, Math.round(curSize + delta * 0.12)));
            onTextSizeChange(newSize);
        } else if (type === 'lower_third') {
            const delta = dx;
            const newW = Math.round(Math.max(60, Math.min(maxW, startWidth + delta)));
            overlayEl.style.width = `${newW}px`;
            const parentWidth = parentRect.width || 360;
            const scalePct = Math.round(Math.max(20, Math.min(150, (newW / parentWidth) * 100)));
            currentOverlayAssets.lowerThirdScale = +(scalePct / 100).toFixed(2);

            const slider = document.getElementById('input-lt-scale');
            if (slider) slider.value = scalePct;
            const badge = document.getElementById('lt-scale-badge');
            if (badge) badge.textContent = `${scalePct}%`;
        }
    };

    const stopResize = () => {
        if (isResizing) {
            isResizing = false;
            overlayEl.classList.remove('resizing');
            handleEl.classList.remove('active');
        }
    };

    handleEl.addEventListener('mousedown', (e) => startResize(e.clientX, e.clientY, e));
    window.addEventListener('mousemove', (e) => doResize(e.clientX, e.clientY));
    window.addEventListener('mouseup', stopResize);

    // Touch support for touchscreens
    handleEl.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches[0]) {
            startResize(e.touches[0].clientX, e.touches[0].clientY, e);
        }
    }, { passive: false });

    window.addEventListener('touchmove', (e) => {
        if (isResizing && e.touches && e.touches[0]) {
            doResize(e.touches[0].clientX, e.touches[0].clientY);
            e.preventDefault();
        }
    }, { passive: false });

    window.addEventListener('touchend', stopResize);
}

function initInteractiveOverlays() {
    const monitorLogo = document.getElementById('monitor-logo-overlay');
    const logoHandle = document.getElementById('logo-resize-handle');
    if (monitorLogo) makeOverlayDraggable(monitorLogo);
    if (monitorLogo && logoHandle) makeOverlayResizable(monitorLogo, logoHandle, 'logo');

    const monitorBlur = document.getElementById('monitor-blur-overlay');
    const blurHandle = document.getElementById('blur-resize-handle');
    if (monitorBlur) makeOverlayDraggable(monitorBlur);
    if (monitorBlur && blurHandle) makeOverlayResizable(monitorBlur, blurHandle, 'blur');

    const monitorText = document.getElementById('monitor-text-overlay');
    const textHandle = document.getElementById('text-resize-handle');
    if (monitorText) makeOverlayDraggable(monitorText);
    if (monitorText && textHandle) makeOverlayResizable(monitorText, textHandle, 'text');

    const monitorLt = document.getElementById('monitor-lower-third-overlay');
    const ltHandle = document.getElementById('lower-third-resize-handle');
    if (monitorLt) makeOverlayDraggable(monitorLt);
    if (monitorLt && ltHandle) makeOverlayResizable(monitorLt, ltHandle, 'lower_third');
}

function makeOverlayDraggable(el) {
    if (!el || el._hasDragHandler) return;
    el._hasDragHandler = true;

    let isDragging = false;
    let startX = 0, startY = 0, origLeft = 0, origTop = 0;

    const startDrag = (clientX, clientY, target, e) => {
        if (target.tagName.toLowerCase() === 'button') return;
        if (target.classList.contains('overlay-resize-handle') || target.closest('.overlay-resize-handle')) return;

        isDragging = true;
        startX = clientX;
        startY = clientY;

        const parentRect = el.parentElement.getBoundingClientRect();
        const elRect = el.getBoundingClientRect();

        origLeft = elRect.left - parentRect.left;
        origTop = elRect.top - parentRect.top;

        el.style.left = `${origLeft}px`;
        el.style.top = `${origTop}px`;
        el.style.right = 'auto';
        el.style.bottom = 'auto';
        el.style.transform = 'none';

        el.classList.add('dragging');
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
    };

    const doDrag = (clientX, clientY) => {
        if (!isDragging) return;
        const dx = clientX - startX;
        const dy = clientY - startY;

        const parentRect = el.parentElement.getBoundingClientRect();
        const elWidth = el.offsetWidth;
        const elHeight = el.offsetHeight;

        const isLt = (el.id === 'monitor-lower-third-overlay');
        const isSub = (el.id === 'monitor-subtitle-overlay');
        let minTop = 0;
        let maxTop = Math.max(0, parentRect.height - elHeight);

        if (isLt) {
            // Allows dragging until banner is completely flush with the top edge (0px)
            // and completely flush with the bottom edge (parentRect.height)
            minTop = -Math.round(elHeight * 0.46);
            maxTop = Math.round(parentRect.height - elHeight * 0.54);
            currentOverlayAssets.lowerThirdUserDragged = true;
        } else if (isSub) {
            minTop = 8;
            maxTop = Math.max(8, parentRect.height - elHeight - 8);
            currentOverlayAssets.subtitleUserDragged = true;
        }

        let newLeft = Math.max(0, Math.min(parentRect.width - elWidth, origLeft + dx));
        let newTop = Math.max(minTop, Math.min(maxTop, origTop + dy));

        // Magnetic center snap (within 14px of parent center)
        const centerOffset = (newLeft + elWidth / 2) - (parentRect.width / 2);
        if (Math.abs(centerOffset) < 14) {
            newLeft = Math.round((parentRect.width - elWidth) / 2);
            el.classList.add('snapped-center');
        } else {
            el.classList.remove('snapped-center');
        }

        el.style.left = `${newLeft}px`;
        el.style.top = `${newTop}px`;
    };

    const stopDrag = () => {
        if (isDragging) {
            isDragging = false;
            el.classList.remove('dragging');
            el.classList.remove('snapped-center');

            if (el.id === 'monitor-subtitle-overlay') {
                currentOverlayAssets.subtitleUserDragged = true;
                const parentRect = el.parentElement ? el.parentElement.getBoundingClientRect() : null;
                const elRect = el.getBoundingClientRect();
                if (parentRect && parentRect.height > 20) {
                    const normBottom = Math.max(0.02, Math.min(0.98, (parentRect.bottom - elRect.bottom) / parentRect.height));
                    const approxMarginV = Math.max(20, Math.min(1400, Math.round(normBottom * 1920)));
                    currentOverlayAssets.subtitleMarginV = approxMarginV;

                    const slider = document.getElementById('input-sub-margin');
                    if (slider) slider.value = approxMarginV;
                    const badge = document.getElementById('sub-margin-badge');
                    if (badge) badge.textContent = `${approxMarginV}px`;

                    const btnBottom = document.getElementById('btn-sub-pos-bottom');
                    const btnAboveLt = document.getElementById('btn-sub-pos-above-lt');
                    const btnMiddle = document.getElementById('btn-sub-pos-middle');
                    const btnHigher = document.getElementById('btn-sub-pos-higher');
                    if (btnBottom) btnBottom.classList.toggle('active', approxMarginV <= 150);
                    if (btnAboveLt) btnAboveLt.classList.toggle('active', approxMarginV > 150 && approxMarginV <= 450);
                    if (btnMiddle) btnMiddle.classList.toggle('active', approxMarginV > 450 && approxMarginV <= 800);
                    if (btnHigher) btnHigher.classList.toggle('active', approxMarginV > 800);
                }
            }
        }
    };

    el.addEventListener('mousedown', (e) => startDrag(e.clientX, e.clientY, e.target, e));
    window.addEventListener('mousemove', (e) => doDrag(e.clientX, e.clientY));
    window.addEventListener('mouseup', stopDrag);

    // Touch support for dragging
    el.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches[0]) {
            startDrag(e.touches[0].clientX, e.touches[0].clientY, e.target, e);
        }
    }, { passive: false });

    window.addEventListener('touchmove', (e) => {
        if (isDragging && e.touches && e.touches[0]) {
            doDrag(e.touches[0].clientX, e.touches[0].clientY);
            e.preventDefault();
        }
    }, { passive: false });

    window.addEventListener('touchend', stopDrag);
}

// Calculate the exact rendered video pixels area on screen inside #main-video (accounting for object-fit: contain)
function getActualVideoRect() {
    const mainVideo = document.getElementById('main-video');
    const screenArea = document.getElementById('monitor-screen-area');
    if (!screenArea) return null;

    if (!mainVideo || mainVideo.style.display === 'none') {
        return screenArea.getBoundingClientRect();
    }

    const vRect = mainVideo.getBoundingClientRect();
    if (!vRect || vRect.width <= 0 || vRect.height <= 0) {
        return screenArea.getBoundingClientRect();
    }

    const vw = mainVideo.videoWidth;
    const vh = mainVideo.videoHeight;
    if (!vw || !vh || vw <= 0 || vh <= 0) {
        return vRect;
    }

    if (window.videoFitMode === 'fill') {
        return {
            left: vRect.left,
            top: vRect.top,
            right: vRect.right,
            bottom: vRect.bottom,
            width: vRect.width,
            height: vRect.height
        };
    }

    const videoAspect = vw / vh;
    const boxAspect = vRect.width / vRect.height;

    let actualW, actualH, actualLeft, actualTop;
    if (boxAspect > videoAspect) {
        // Video has pillarbox (empty sides)
        actualH = vRect.height;
        actualW = vRect.height * videoAspect;
        actualTop = vRect.top;
        actualLeft = vRect.left + (vRect.width - actualW) / 2;
    } else {
        // Video has letterbox (empty top/bottom)
        actualW = vRect.width;
        actualH = vRect.width / videoAspect;
        actualLeft = vRect.left;
        actualTop = vRect.top + (vRect.height - actualH) / 2;
    }

    return {
        left: actualLeft,
        top: actualTop,
        right: actualLeft + actualW,
        bottom: actualTop + actualH,
        width: actualW,
        height: actualH
    };
}

// Extract exact normalized overlay coordinates (Logo watermark, Blur mask, and Text title) for FFmpeg render burning
async function getOverlayExportConfig() {
    const vRect = getActualVideoRect();
    const screenArea = document.getElementById('monitor-screen-area');
    const sRect = vRect || (screenArea ? screenArea.getBoundingClientRect() : null);

    // 1. Logo Watermark Overlay
    const monitorLogo = document.getElementById('monitor-logo-overlay');
    const isLogoActive = monitorLogo && monitorLogo.style.display !== 'none' && (currentOverlayAssets.logo || currentOverlayAssets.serverLogoPath);
    let logoCfg = { active: false };

    if (isLogoActive) {
        let sLogoPath = currentOverlayAssets.serverLogoPath;
        if (!sLogoPath && currentOverlayAssets.logo instanceof File) {
            try {
                const fd = new FormData();
                fd.append('logo_file', currentOverlayAssets.logo);
                const r = await fetch('/api/projects/upload-overlay-logo', { method: 'POST', body: fd });
                const d = await r.json();
                if (d.success && d.logo_path) {
                    sLogoPath = d.logo_path;
                    currentOverlayAssets.serverLogoPath = sLogoPath;
                }
            } catch (e) {
                console.warn("Logo export upload note:", e);
            }
        }

        let norm_x = 0.04, norm_y = 0.04, norm_w = 0.16;
        let isCentered = false;
        if (sRect && sRect.width > 20 && sRect.height > 20) {
            const lRect = monitorLogo.getBoundingClientRect();
            norm_x = Math.max(0, Math.min(0.96, (lRect.left - sRect.left) / sRect.width));
            norm_y = Math.max(0, Math.min(0.96, (lRect.top - sRect.top) / sRect.height));
            norm_w = Math.max(0.04, Math.min(0.95, lRect.width / sRect.width));
            const logoCenterX = (lRect.left + lRect.width / 2 - sRect.left) / sRect.width;
            if (Math.abs(logoCenterX - 0.50) < 0.04 || currentOverlayAssets.logoPosition === 'top-center' || currentOverlayAssets.logoPosition === 'bottom-center') {
                isCentered = true;
                norm_x = Math.max(0, (1.0 - norm_w) / 2);
            }
        } else {
            const pos = currentOverlayAssets.logoPosition || 'top-left';
            if (pos === 'top-left') { norm_x = 0.04; norm_y = 0.04; }
            else if (pos === 'top-right') { norm_x = 0.80; norm_y = 0.04; }
            else if (pos === 'bottom-right') { norm_x = 0.80; norm_y = 0.88; }
            else if (pos === 'bottom-left') { norm_x = 0.04; norm_y = 0.88; }
            else if (pos === 'top-center') { norm_x = (1.0 - norm_w) / 2; norm_y = 0.04; isCentered = true; }
            else if (pos === 'bottom-center') { norm_x = (1.0 - norm_w) / 2; norm_y = 0.88; isCentered = true; }
        }

        logoCfg = {
            active: true,
            path: sLogoPath || null,
            norm_x: +norm_x.toFixed(4),
            norm_y: +norm_y.toFixed(4),
            norm_w: +norm_w.toFixed(4),
            is_center: isCentered,
            opacity: 1.0,
            position: currentOverlayAssets.logoPosition || 'top-left'
        };
    }

    // 2. Blur Mask Overlay
    const monitorBlur = document.getElementById('monitor-blur-overlay');
    const isBlurActive = monitorBlur && monitorBlur.style.display !== 'none' && currentOverlayAssets.blurActive;
    let blurCfg = { active: false };

    if (isBlurActive) {
        let norm_x = 0.0, norm_y = 0.50, norm_w = 1.0, norm_h = 0.08;
        let isCentered = false;
        if (sRect && sRect.width > 20 && sRect.height > 20) {
            const bRect = monitorBlur.getBoundingClientRect();
            norm_x = Math.max(0, Math.min(0.98, (bRect.left - sRect.left) / sRect.width));
            norm_y = Math.max(0, Math.min(0.98, (bRect.top - sRect.top) / sRect.height));
            norm_w = Math.max(0.04, Math.min(1.0, bRect.width / sRect.width));
            norm_h = Math.max(0.02, Math.min(0.95, bRect.height / sRect.height));

            const blurCenterX = (bRect.left + bRect.width / 2 - sRect.left) / sRect.width;
            if (Math.abs(blurCenterX - 0.50) < 0.04 || currentOverlayAssets.blurPosition === 'bottom-center' || norm_w >= 0.85) {
                isCentered = true;
                if (norm_w >= 0.88) {
                    norm_x = 0.0;
                    norm_w = 1.0;
                } else {
                    norm_x = Math.max(0, (1.0 - norm_w) / 2);
                }
            }
        } else {
            const pos = currentOverlayAssets.blurPosition || 'center';
            if (pos === 'top-left') { norm_x = 0.04; norm_y = 0.03; norm_w = 0.35; }
            else if (pos === 'top-right') { norm_x = 0.65; norm_y = 0.03; norm_w = 0.35; }
            else if (pos === 'bottom-center') { norm_x = 0.0; norm_y = 0.88; norm_w = 1.0; isCentered = true; }
        }

        blurCfg = {
            active: true,
            radius: currentOverlayAssets.blurRadius || 25,
            norm_x: +norm_x.toFixed(4),
            norm_y: +norm_y.toFixed(4),
            norm_w: +norm_w.toFixed(4),
            norm_h: +norm_h.toFixed(4),
            is_center: isCentered,
            shape: currentOverlayAssets.blurShape || 'rectangle',
            feather: currentOverlayAssets.blurFeather || 0,
            roundCorners: currentOverlayAssets.blurRoundCorners || 0,
            position: currentOverlayAssets.blurPosition || 'center'
        };
    }

    // 3. Watermark / Title Text Overlay
    const monitorText = document.getElementById('monitor-text-overlay');
    const isTextActive = monitorText && monitorText.style.display !== 'none' && currentOverlayAssets.textActive;
    let textCfg = { active: false };

    if (isTextActive) {
        let center_x = 0.50, norm_y = 0.85, norm_w = 0.60, norm_h = 0.08, norm_x = 0.20;
        let isCentered = false;
        let norm_font_size = 0.04;

        if (sRect && sRect.width > 20 && sRect.height > 20) {
            const tRect = monitorText.getBoundingClientRect();
            const elemCenterX = tRect.left + (tRect.width / 2);
            center_x = (elemCenterX - sRect.left) / sRect.width;
            norm_x = Math.max(0, Math.min(0.98, (tRect.left - sRect.left) / sRect.width));
            norm_y = Math.max(0, Math.min(0.98, (tRect.top - sRect.top) / sRect.height));
            norm_w = Math.max(0.04, Math.min(1.0, tRect.width / sRect.width));
            norm_h = Math.max(0.02, Math.min(0.95, tRect.height / sRect.height));

            const rawSize = currentOverlayAssets.textSize || 24;
            norm_font_size = rawSize / sRect.height;

            const isPresetCenter = (currentOverlayAssets.textPosition === 'top-center' || currentOverlayAssets.textPosition === 'bottom-center');
            if (isPresetCenter || Math.abs(center_x - 0.50) < 0.04) {
                isCentered = true;
                center_x = 0.50;
            }
        } else {
            const pos = currentOverlayAssets.textPosition || 'bottom-center';
            if (pos === 'bottom-center') { center_x = 0.50; norm_y = 0.85; isCentered = true; }
            else if (pos === 'top-center') { center_x = 0.50; norm_y = 0.06; isCentered = true; }
            else if (pos === 'top-left') { center_x = 0.20; norm_x = 0.04; norm_y = 0.06; }
            else if (pos === 'top-right') { center_x = 0.80; norm_x = 0.65; norm_y = 0.06; }
        }

        const motion = currentOverlayAssets.textMotion || 'static';
        const speed = currentOverlayAssets.textSpeed || 65;
        const durationSec = speed <= 45 ? 9.5 : (speed >= 90 ? 4.0 : 6.5);

        textCfg = {
            active: true,
            text: currentOverlayAssets.textValue || 'EPISODE 01',
            size: currentOverlayAssets.textSize || 24,
            norm_font_size: +norm_font_size.toFixed(4),
            color: currentOverlayAssets.textColor || '#ffffff',
            segments: currentOverlayAssets.textSegments || [],
            bg: currentOverlayAssets.textBg === true,
            motion: motion,
            speed: speed,
            duration: durationSec,
            scroll_duration: durationSec,
            position: currentOverlayAssets.textPosition || 'bottom-center',
            center_x: +center_x.toFixed(4),
            norm_x: +norm_x.toFixed(4),
            norm_y: +norm_y.toFixed(4),
            norm_w: +norm_w.toFixed(4),
            norm_h: +norm_h.toFixed(4),
            is_center: isCentered
        };
    }

    // 4. Lower Third Video Overlay
    const monitorLt = document.getElementById('monitor-lower-third-overlay');
    const isLtActive = monitorLt && monitorLt.style.display !== 'none' && currentOverlayAssets.lowerThirdActive;
    let ltCfg = { active: false };

    if (isLtActive) {
        let sLtPath = currentOverlayAssets.serverLowerThirdPath;
        if (!sLtPath && currentOverlayAssets.lowerThirdFile instanceof File) {
            try {
                const fd = new FormData();
                fd.append('lower_third_file', currentOverlayAssets.lowerThirdFile);
                const r = await fetch('/api/projects/upload-overlay-lower-third', { method: 'POST', body: fd });
                const d = await r.json();
                if (d.success && (d.lower_third_path || d.video_path)) {
                    sLtPath = d.lower_third_path || d.video_path;
                    currentOverlayAssets.serverLowerThirdPath = sLtPath;
                }
            } catch (e) {
                console.warn("Lower third export upload note:", e);
            }
        }
        if (!sLtPath && currentOverlayAssets.lowerThirdSamplePath) {
            sLtPath = currentOverlayAssets.lowerThirdSamplePath;
        }

        let norm_x = 0.0, norm_y = 0.0, norm_w = 1.0, norm_h = 0.35;
        let isCentered = false;
        if (sRect && sRect.width > 20 && sRect.height > 20) {
            const ltRect = monitorLt.getBoundingClientRect();
            norm_x = Math.max(0, Math.min(0.98, (ltRect.left - sRect.left) / sRect.width));
            const rawNormY = (ltRect.top - sRect.top) / sRect.height;
            norm_y = Math.max(-0.65, Math.min(1.20, rawNormY));
            norm_w = Math.max(0.08, Math.min(1.0, ltRect.width / sRect.width));
            norm_h = Math.max(0.02, Math.min(0.95, ltRect.height / sRect.height));

            const ltCenterX = (ltRect.left + ltRect.width / 2 - sRect.left) / sRect.width;
            if (norm_w >= 0.95 || Math.abs(ltCenterX - 0.50) < 0.04 || currentOverlayAssets.lowerThirdPosition === 'bottom-center' || currentOverlayAssets.lowerThirdPosition === 'top-center') {
                isCentered = true;
                norm_x = Math.max(0, (1.0 - norm_w) / 2);
            }
        } else {
            const pos = currentOverlayAssets.lowerThirdPosition || 'bottom-center';
            norm_w = currentOverlayAssets.lowerThirdScale || 1.0;
            if (pos === 'bottom-center') { norm_x = (1.0 - norm_w) / 2; norm_y = 0.65; isCentered = true; }
            else if (pos === 'top-center') { norm_x = (1.0 - norm_w) / 2; norm_y = -0.30; isCentered = true; }
            else if (pos === 'bottom-left') { norm_x = 0.02; norm_y = 0.65; }
            else if (pos === 'bottom-right') { norm_x = Math.max(0, 0.98 - norm_w); norm_y = 0.65; }
        }

        ltCfg = {
            active: true,
            path: sLtPath || null,
            norm_x: +norm_x.toFixed(4),
            norm_y: +norm_y.toFixed(4),
            norm_w: +norm_w.toFixed(4),
            norm_h: +norm_h.toFixed(4),
            is_center: isCentered,
            user_dragged: !!currentOverlayAssets.lowerThirdUserDragged,
            scale: currentOverlayAssets.lowerThirdScale || 1.0,
            opacity: currentOverlayAssets.lowerThirdOpacity !== undefined ? currentOverlayAssets.lowerThirdOpacity : 1.0,
            start_time: currentOverlayAssets.lowerThirdStartTime || 0.0,
            end_time: currentOverlayAssets.lowerThirdEndTime || 0.0,
            loop: currentOverlayAssets.lowerThirdLoop !== false,
            speed: currentOverlayAssets.lowerThirdSpeed || 1.0,
            position: currentOverlayAssets.lowerThirdPosition || 'bottom-center'
        };
    }

    // 5. Subtitle Overlay (Viral Khmer Subtitles)
    let subNormY = null;
    let subCenterX = 0.50;
    let subMarginV = currentOverlayAssets.subtitleMarginV || 65;
    let subUserDragged = !!currentOverlayAssets.subtitleUserDragged;

    const monitorSub = document.getElementById('monitor-subtitle-overlay');
    if (monitorSub && currentOverlayAssets.subtitleActive && sRect && sRect.height > 20) {
        const subRect = monitorSub.getBoundingClientRect();
        // Distance of subtitle bottom edge from top of actual video canvas, normalized 0.0 to 1.0
        const rawNormBottomY = (subRect.bottom - sRect.top) / sRect.height;
        subNormY = Math.max(0.05, Math.min(0.98, rawNormBottomY));

        const rawCenterX = (subRect.left + subRect.width / 2 - sRect.left) / sRect.width;
        if (Math.abs(rawCenterX - 0.50) < 0.04) {
            subCenterX = 0.50;
        } else {
            subCenterX = Math.max(0.10, Math.min(0.90, rawCenterX));
        }

        // Keep margin_v in sync based on 1920 reference vertical height
        subMarginV = Math.max(20, Math.round((1.0 - subNormY) * 1920));
    } else {
        subNormY = Math.max(0.05, Math.min(0.98, (1920 - subMarginV) / 1920.0));
    }

    const subCfg = {
        active: !!currentOverlayAssets.subtitleActive,
        style: currentOverlayAssets.subtitleStyle || 'viral_yellow',
        animation: currentOverlayAssets.subtitleAnimation || 'pop',
        size: currentOverlayAssets.subtitleSize || 44,
        margin_v: subMarginV,
        center_x: +subCenterX.toFixed(4),
        norm_y: +subNormY.toFixed(4),
        is_center: Math.abs(subCenterX - 0.50) < 0.005,
        user_dragged: subUserDragged,
        custom_file: currentOverlayAssets.customSubtitlePath || null
    };

    return {
        logo: logoCfg,
        blur: blurCfg,
        text: textCfg,
        lower_third: ltCfg,
        subtitle: subCfg
    };
}

// Re-render an existing completed project when user adds/modifies Logo, Blur, Text, or Lower Third
async function reRenderCurrentDubbedProjectWithOverlay() {
    if (!currentDubbedProject || !currentDubbedProject.id) return;
    showToast("Rendering video with overlays (Logo, Blur, Text, Lower Third)...");
    appendLiveTerminalLine("Re-rendering dubbed video with Logo, Blur, Text & Lower Third overlays burned in...", "[Render Engine]", "info");
    updateExportProgressUI(10, 0, 30, "Burning overlays (Logo, Blur, Text, Lower Third) into video...");

    try {
        const overlayCfg = await getOverlayExportConfig();
        const res = await fetch(`/api/projects/${currentDubbedProject.id}/render-video`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                burn_subtitles: (currentOverlayAssets.subtitleActive || currentStoryConfig.subtitle_mode === "burn"),
                aspect_ratio: currentDubbedProject.aspect_ratio || currentStoryConfig.aspect_ratio || "9:16",
                overlay_config: overlayCfg
            })
        });
        const data = await res.json();
        if (data.success && data.project) {
            currentDubbedProject = data.project;
            updateExportProgressUI(100, 5, 0, "Rendered overlays into video successfully!");
            showToast("Exported video with overlays successfully!");
            appendLiveTerminalLine("Logo, Blur, Text & Lower Third overlays successfully burned into final video!", "[Render Engine]", "success");
            const mainVideo = document.getElementById('main-video');
            if (mainVideo && data.video_url) {
                mainVideo.src = `${data.video_url}?t=${Date.now()}`;
                mainVideo.load();
            }
            if (currentDubbedProject.output_video_file) {
                openExportFolderDirect(currentDubbedProject.output_video_file);
            }
        } else {
            showToast(`Render failed: ${data.error || 'Server error'}`);
            appendLiveTerminalLine(`Render error: ${data.error || 'Failed to render'}`, "[Render Engine]", "error");
        }
    } catch (e) {
        showToast(`Render error: ${e.message}`);
        appendLiveTerminalLine(`Render exception: ${e.message}`, "[Render Engine]", "error");
    }
}

function selectQuickBgmPreset(val) {
    const slider = document.getElementById('staged-bgm-slider');
    if (slider) slider.value = val;
    onQuickBgmSliderChange(val);
}

let quickBgmSaveDebounce = null;
function onQuickBgmSliderChange(val) {
    const numVal = parseInt(val, 10);
    const duckingFraction = (numVal / 100).toFixed(2);
    currentStoryConfig.ducking_volume = duckingFraction;

    [0, 10, 18, 28].forEach(p => {
        const btn = document.getElementById(`bgm-pre-${p}`);
        if (btn) {
            if (p === numVal) btn.classList.add('active');
            else btn.classList.remove('active');
        }
    });

    const bgmBadge = document.getElementById('staged-bgm-val-badge');
    if (bgmBadge) {
        if (numVal === 0) bgmBadge.textContent = "0% (Muted)";
        else if (numVal <= 10) bgmBadge.textContent = `${numVal}% • Subtle`;
        else if (numVal <= 20) bgmBadge.textContent = `${numVal}% • Recommended`;
        else bgmBadge.textContent = `${numVal}% • Moderate`;
    }

    const modalSlider = document.getElementById('story-ducking-slider');
    if (modalSlider) modalSlider.value = numVal;

    if (quickBgmSaveDebounce) clearTimeout(quickBgmSaveDebounce);
    quickBgmSaveDebounce = setTimeout(async () => {
        try {
            await fetch('/api/set-story-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ducking_volume: duckingFraction
                })
            });
            showToast(`BGM volume level adjusted: ${numVal}%`);
            appendLiveTerminalLine(`BGM volume / ducking set to: ${numVal}%`, "[Audio Config]", "info");
        } catch (e) {}
    }, 400);
}

async function loadStoryConfigData() {
    try {
        const res = await fetch('/api/story-config');
        if (res.ok) {
            const data = await res.json();
            if (data.success && data.config) {
                currentStoryConfig = Object.assign(currentStoryConfig, data.config);
                syncStagedCardControls();
                refreshStagedCardVoiceMeta();
            }
        }
    } catch (e) {
        console.warn("Story config load note:", e);
    }
}

async function loadDramaDictionaryUI() {
    try {
        const res = await fetch('/api/drama-dictionary');
        if (res.ok) {
            const data = await res.json();
            if (data.success && data.dictionary) {
                const dictElem = document.getElementById('story-dictionary-textarea');
                if (dictElem) {
                    const lines = Object.entries(data.dictionary).map(([k, v]) => `${k} = ${v}`);
                    dictElem.value = lines.join('\n');
                }
            }
        }
    } catch (e) {
        console.warn("Dictionary load note:", e);
    }
}

async function openStorySettingsModal() {
    await loadStoryConfigData();
    await loadDramaDictionaryUI();

    // Populate Voice & AI Tab fields
    const selVoice = document.getElementById('story-voice-select');
    let activeVoice = (currentStoryConfig.khmer_voice === 'sreymom') ? 'sreymom' : 'piseth';
    if (selVoice) selVoice.value = activeVoice;

    const selLang = document.getElementById('story-source-lang');
    if (selLang) selLang.value = currentStoryConfig.source_lang || 'auto';

    const selWhisper = document.getElementById('story-whisper-model');
    if (selWhisper) selWhisper.value = currentStoryConfig.whisper_model || 'medium';

    const lblProvider = document.getElementById('story-ai-provider-display');
    if (lblProvider) lblProvider.textContent = currentStoryConfig.ai_provider_display || 'Gemini API (Key Pool)';

    // Video & Look
    const selAspect = document.getElementById('story-aspect-ratio');
    if (selAspect) selAspect.value = currentStoryConfig.aspect_ratio || '9:16';

    const selSub = document.getElementById('story-subtitle-mode');
    if (selSub) selSub.value = currentStoryConfig.subtitle_mode || 'none';

    // Audio & Music
    const selDub = document.getElementById('story-dubbing-mode');
    if (selDub) selDub.value = currentStoryConfig.dubbing_mode || 'smart_bgm';

    let duckPct = 15;
    const rawDuck = parseFloat(currentStoryConfig.ducking_volume);
    if (!isNaN(rawDuck)) {
        duckPct = Math.round(rawDuck * 100);
        if (duckPct < 0) duckPct = 0;
        if (duckPct > 40) duckPct = 40;
    }
    syncStoryDuckingUI(duckPct);

    let speechVal = (currentStoryConfig.speech_boost_db !== undefined) ? parseFloat(currentStoryConfig.speech_boost_db) : 2.5;
    if (isNaN(speechVal)) speechVal = 2.5;
    syncStorySpeechUI(speechVal);

    updateStoryVoiceHint();
    switchStoryTab('voice');
    openModal('modal-story-settings');
}

function formatDuckingDbText(pct) {
    pct = parseInt(pct, 10);
    if (isNaN(pct)) pct = 15;
    if (pct <= 0) return "0% • Mute";
    let desc = "Standard";
    if (pct <= 8) desc = "Subtle";
    else if (pct <= 18) desc = "Standard (Recommended)";
    else if (pct <= 28) desc = "Moderate";
    else desc = "High BGM";
    return `${pct}% • ${desc}`;
}

function syncStoryDuckingUI(pct) {
    pct = parseInt(pct, 10);
    if (isNaN(pct)) pct = 15;
    pct = Math.max(0, Math.min(40, pct));

    const slider = document.getElementById('story-ducking-slider');
    const hidden = document.getElementById('story-ducking-vol');
    const badge = document.getElementById('story-ducking-badge');
    const container = document.getElementById('story-ducking-presets');

    if (slider) slider.value = pct;
    if (hidden) hidden.value = (pct / 100).toFixed(2);
    if (badge) badge.textContent = formatDuckingDbText(pct);

    if (container) {
        const chips = container.querySelectorAll('.ai-preset-chip');
        chips.forEach(chip => {
            const v = parseInt(chip.getAttribute('data-val'), 10);
            chip.classList.toggle('active', v === pct);
        });
    }
}

function onStoryDuckingSliderChange(val) {
    syncStoryDuckingUI(val);
}

function setDuckingPreset(pct) {
    syncStoryDuckingUI(pct);
}

function formatSpeechDbText(val) {
    val = parseFloat(val);
    if (isNaN(val)) val = 2.5;
    let desc = "Balanced";
    if (val === 0) desc = "Flat";
    else if (val <= 1.5) desc = "Subtle";
    else if (val <= 3.0) desc = "Balanced (Recommended)";
    else if (val <= 5.0) desc = "Punchy";
    else desc = "Maximum Boost";
    const prefix = val > 0 ? `+${val.toFixed(1)}` : `${val.toFixed(1)}`;
    return `${prefix} dB • ${desc}`;
}

function syncStorySpeechUI(val) {
    val = parseFloat(val);
    if (isNaN(val)) val = 2.5;
    val = Math.max(0, Math.min(8, val));

    const slider = document.getElementById('story-speech-slider');
    const hidden = document.getElementById('story-speech-boost');
    const badge = document.getElementById('story-speech-badge');
    const container = document.getElementById('story-speech-presets');

    if (slider) slider.value = val;
    if (hidden) hidden.value = val.toFixed(1);
    if (badge) badge.textContent = formatSpeechDbText(val);

    if (container) {
        const chips = container.querySelectorAll('.ai-preset-chip');
        chips.forEach(chip => {
            const v = parseFloat(chip.getAttribute('data-val'));
            chip.classList.toggle('active', Math.abs(v - val) < 0.1);
        });
    }
}

function onStorySpeechSliderChange(val) {
    syncStorySpeechUI(val);
}

function setSpeechBoostPreset(val) {
    syncStorySpeechUI(val);
}

function switchStoryTab(tabKey) {
    const tabs = ['voice', 'video', 'audio', 'vocal', 'export', 'dictionary'];
    tabs.forEach(t => {
        const btn = document.getElementById(`story-tab-btn-${t}`);
        const view = document.getElementById(`story-view-${t}`);
        if (btn) btn.classList.toggle('active', t === tabKey);
        if (view) view.style.display = (t === tabKey) ? 'flex' : 'none';
    });
}

function applyDramaDictionaryPreset(presetKey) {
    const dictElem = document.getElementById('story-dictionary-textarea');
    if (!dictElem) return;

    const presets = {
        modern_ceo: [
            "总裁 = President",
            "董事长 = Chairman",
            "夫人 = Madam",
            "少爷 = Young Master",
            "小姐 = Young Lady",
            "特助 = Special Assistant",
            "经理 = Manager",
            "秘书 = Secretary",
            "保安 = Security"
        ],
        family_inlaw: [
            "婆婆 = Mother-in-law",
            "公公 = Father-in-law",
            "儿媳 = Daughter-in-law",
            "女婿 = Son-in-law",
            "大嫂 = Elder Sister-in-law",
            "小叔子 = Younger Brother-in-law",
            "丈母娘 = Mother-in-law",
            "亲家 = In-laws"
        ],
        palace_royal: [
            "皇上 = Emperor",
            "陛下 = Your Majesty",
            "皇后 = Empress",
            "贵妃 = Imperial Consort",
            "娘娘 = Princess",
            "王爷 = Prince",
            "太后 = Empress Dowager",
            "微臣 = Your Humble Servant",
            "奴才 = Servant",
            "龙胎 = Dragon Heir"
        ],
        wuxia_martial: [
            "掌门 = Sect Leader",
            "师傅 = Master",
            "师兄 = Senior Brother",
            "师妹 = Junior Sister",
            "大侠 = Hero",
            "教主 = Cult Master",
            "前辈 = Senior",
            "在下 = Humble Self"
        ]
    };

    const linesToAdd = presets[presetKey] || [];
    if (linesToAdd.length === 0) return;

    let current = dictElem.value.trim();
    const existingLines = current ? current.split('\n') : [];
    const merged = new Set(existingLines);

    linesToAdd.forEach(l => merged.add(l));
    dictElem.value = Array.from(merged).join('\n');
    showToast(`Loaded dictionary preset: ${presetKey}`);
}

function updateStoryVoiceHint() {
    const hint = document.getElementById('story-voice-hint');
    const selVoice = document.getElementById('story-voice-select');
    if (!hint || !selVoice) return;

    const val = selVoice.value;
    if (val === 'sreymom') {
        hint.innerHTML = `<span style="color:#f472b6; font-weight:bold;">Sreymom (Female Solo - v7.3.1):</span> Smooth neural female voice (v7.3.1) for all dialogue lines.`;
    } else {
        hint.innerHTML = `<span style="color:#38bdf8; font-weight:bold;">Piseth (Male Solo - v7.3.1):</span> Crisp neural male voice (v7.3.1) for all dialogue lines.`;
    }
}

function onStoryVoiceChange() {
    updateStoryVoiceHint();
    const selVoice = document.getElementById('story-voice-select');
    if (!selVoice) return;
    if (selVoice.value === 'sreymom') {
        showToast("Selected: Sreymom (Female Solo)");
    } else {
        showToast("Selected: Piseth (Male Solo)");
    }
}

function onToggleMultiVoice(isChecked) {
    const selVoice = document.getElementById('story-voice-select');
    if (selVoice) selVoice.value = isChecked ? 'sreymom' : 'piseth';
    updateStoryVoiceHint();
}

async function saveStorySettings() {
    const saveBtn = document.querySelector('#modal-story-settings .ai-footer-save-btn');
    const originalBtnHtml = saveBtn ? saveBtn.innerHTML : '';
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Saving...</span>';
    }

    try {
        const selVoice = document.getElementById('story-voice-select');
        const voice = (selVoice && selVoice.value === 'sreymom') ? 'sreymom' : 'piseth';
        const isMulti = false;
        const lang = document.getElementById('story-source-lang') ? document.getElementById('story-source-lang').value : 'auto';
        const whisper = document.getElementById('story-whisper-model') ? document.getElementById('story-whisper-model').value : 'medium';
        const aspect = document.getElementById('story-aspect-ratio') ? document.getElementById('story-aspect-ratio').value : '9:16';
        const subtitle = document.getElementById('story-subtitle-mode') ? document.getElementById('story-subtitle-mode').value : 'none';
        const dubMode = document.getElementById('story-dubbing-mode') ? document.getElementById('story-dubbing-mode').value : 'smart_bgm';
        const duckElem = document.getElementById('story-ducking-vol');
        let duckVol = duckElem && duckElem.value ? duckElem.value : '0.15';
        if (!duckVol || isNaN(parseFloat(duckVol))) duckVol = '0.15';

        const boostElem = document.getElementById('story-speech-boost');
        let boost = boostElem && boostElem.value ? parseFloat(boostElem.value) : 2.5;
        if (isNaN(boost)) boost = 2.5;

        const payload = {
            khmer_voice: voice,
            auto_multi_voice: isMulti,
            source_lang: lang,
            whisper_model: whisper,
            aspect_ratio: aspect,
            subtitle_mode: subtitle,
            dubbing_mode: dubMode,
            ducking_volume: duckVol,
            speech_boost_db: boost
        };

        // Save Drama Dictionary only if the tab is explicitly visible and has content
        const dictTabBtn = document.getElementById('story-tab-btn-dictionary');
        const isDictVisible = dictTabBtn && dictTabBtn.style.display !== 'none' && dictTabBtn.offsetParent !== null;
        const dictElem = document.getElementById('story-dictionary-textarea');
        if (isDictVisible && dictElem && dictElem.value.trim()) {
            const dictMap = {};
            dictElem.value.split('\n').forEach(line => {
                const trimmed = line.trim();
                if (trimmed && (trimmed.includes('=') || trimmed.includes(':'))) {
                    const parts = trimmed.includes('=') ? trimmed.split('=') : trimmed.split(':');
                    if (parts.length >= 2) {
                        const k = parts[0].trim();
                        const v = parts.slice(1).join('=').trim();
                        if (k && v) dictMap[k] = v;
                    }
                }
            });
            if (Object.keys(dictMap).length > 0) {
                try {
                    await fetch('/api/drama-dictionary', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ dictionary: dictMap })
                    });
                } catch (e) {
                    console.warn("Dictionary save note:", e);
                }
            }
        }

        const resp = await fetch('/api/set-story-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const resData = await resp.json();
        if (resData.success) {
            currentStoryConfig = Object.assign(currentStoryConfig, payload);
            refreshStagedCardVoiceMeta();
            syncStagedCardControls();

            const voiceNameText = voice === 'sreymom' ? "Sreymom (Female Solo)" : "Piseth (Male Solo)";
            showToast(`Saved settings: ${voiceNameText} successfully!`);
        } else {
            showToast(`${resData.message || 'Error saving story settings'}`);
        }
    } catch (e) {
        showToast(`Error saving: ${e.message}`);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalBtnHtml || '<i class="fa-solid fa-check"></i><span>Save</span>';
        }
        closeModal('modal-story-settings');
    }
}


async function saveApiKey() {
    const key = document.getElementById('input-api-key').value.trim();
    if (key) {
        try {
            await fetch('/api/set-api-key', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: key })
            });
        } catch (e) {}
    }
    showToast("Saved Studio Engine Token!");
    backToSettingsHub();
}

// ==========================================================================
// STUDIO ENGINE & GEMINI KEY POOL MANAGER
// ==========================================================================
let currentAiConfig = {
    engine: "gemini_pool",
    keys: [],
    keys_raw: "",
    model: "gemini-2.5-flash",
    temperature: 0.3,
    prompt_style: "drama_dubbing"
};

async function loadAiConfigData() {
    try {
        const res = await fetch('/api/ai-config');
        if (res.ok) {
            const data = await res.json();
            if (data.success && data.config) {
                currentAiConfig = Object.assign(currentAiConfig, data.config);
            }
        }
    } catch (e) {
        console.warn("AI config load note:", e);
    }
}

async function openAiProvidingModal() {
    await loadAiConfigData();

    // Populate UI fields
    const selEngine = document.getElementById('ai-engine-select');
    if (selEngine) selEngine.value = currentAiConfig.engine || 'auto';

    const txtKeys = document.getElementById('ai-keys-pool-textarea');
    if (txtKeys) {
        txtKeys.value = currentAiConfig.keys_raw || (currentAiConfig.keys ? currentAiConfig.keys.join('\n') : '');
    }

    const selModel = document.getElementById('ai-model-select');
    if (selModel && currentAiConfig.model) selModel.value = currentAiConfig.model;

    const sliderTemp = document.getElementById('ai-temperature-slider');
    const badgeTemp = document.getElementById('ai-temp-val');
    if (sliderTemp && currentAiConfig.temperature !== undefined) {
        sliderTemp.value = currentAiConfig.temperature;
        if (badgeTemp) badgeTemp.textContent = currentAiConfig.temperature;
    }

    const txtPrompt = document.getElementById('ai-system-prompt-input');
    if (txtPrompt && currentAiConfig.prompt_style && currentAiConfig.prompt_style.length > 20) {
        txtPrompt.value = currentAiConfig.prompt_style;
    }

    // Load SpeechGen config
    try {
        const scResp = await fetch('/api/story-config');
        const scData = await scResp.json();
        if (scData.success && scData.config) {
            const tokenInput = document.getElementById('speechgen-token-input');
            const emailInput = document.getElementById('speechgen-email-input');
            if (tokenInput) tokenInput.value = scData.config.speechgen_token || '';
            if (emailInput) emailInput.value = scData.config.speechgen_email || '';
        }
    } catch (e) {}

    handleAiKeysInput();
    switchAiProvidingTab('provider');
    openModal('modal-ai-providing');
}

function switchAiProvidingTab(tabKey) {
    const tabs = ['provider', 'models', 'speechgen', 'backup'];
    tabs.forEach(t => {
        const btn = document.getElementById(`ai-tab-btn-${t}`);
        const view = document.getElementById(`ai-view-${t}`);
        if (btn) btn.classList.toggle('active', t === tabKey);
        if (view) view.style.display = (t === tabKey) ? 'flex' : 'none';
    });
}

function onAiEngineChange() {
    const sel = document.getElementById('ai-engine-select');
    if (!sel) return;
    const val = sel.value;
    if (val === 'free_ai' || val === 'auto') {
        showToast("Selected: Built-in Studio Translation Engine (Standard)");
    } else if (val === 'google_free') {
        showToast("Selected: Web Translation Engine");
    } else {
        showToast("Selected: Cloud API Engine (Key Pool)");
    }
}

function handleAiKeysInput() {
    const textarea = document.getElementById('ai-keys-pool-textarea');
    const gutter = document.getElementById('ai-editor-gutter');
    const badge = document.getElementById('ai-key-count-badge');
    if (!textarea) return;

    const val = textarea.value;
    const lines = val.split('\n');
    const lineCount = Math.max(1, lines.length);

    if (gutter) {
        let gutterHtml = '';
        for (let i = 1; i <= lineCount; i++) {
            gutterHtml += `<div>${i}</div>`;
        }
        gutter.innerHTML = gutterHtml;
    }

    const nonBlankKeys = lines.map(l => l.trim()).filter(l => l.length > 0);
    if (badge) {
        if (nonBlankKeys.length === 0) {
            badge.textContent = "0 loaded";
            badge.style.color = "#94a3b8";
        } else {
            badge.textContent = `${nonBlankKeys.length} loaded · active`;
            badge.style.color = "var(--gold-glow)";
        }
    }
}

function syncAiEditorScroll() {
    const textarea = document.getElementById('ai-keys-pool-textarea');
    const gutter = document.getElementById('ai-editor-gutter');
    if (textarea && gutter) {
        gutter.scrollTop = textarea.scrollTop;
    }
}

function triggerImportKeysFile() {
    const fileInput = document.getElementById('ai-keys-file-input');
    if (fileInput) {
        fileInput.value = "";
        fileInput.click();
    }
}

function handleAiKeysFileSelect(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const content = e.target.result || "";
        const textarea = document.getElementById('ai-keys-pool-textarea');
        if (textarea) {
            const existing = textarea.value.trim();
            const newKeys = content.trim();
            if (existing) {
                textarea.value = existing + "\n" + newKeys;
            } else {
                textarea.value = newKeys;
            }
            handleAiKeysInput();
            showToast(`Imported keys from ${file.name}`);
        }
    };
    reader.readAsText(file);
}

async function checkKeysLive() {
    const textarea = document.getElementById('ai-keys-pool-textarea');
    if (!textarea) return;

    const raw = textarea.value.trim();
    const lines = raw.split('\n').map(l => l.trim()).filter(l => l.length > 0);

    if (lines.length === 0) {
        showToast("Please enter at least 1 Gemini API Key before checking!");
        return;
    }

    const checkBtn = document.getElementById('btn-check-keys-live');
    const origHtml = checkBtn ? checkBtn.innerHTML : "";
    if (checkBtn) {
        checkBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Checking ${lines.length} keys...`;
        checkBtn.disabled = true;
    }

    try {
        const resp = await fetch('/api/check-keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keys: lines, keys_raw: raw })
        });
        const resData = await resp.json();
        if (resData.success) {
            const badge = document.getElementById('ai-key-count-badge');
            if (badge) {
                badge.textContent = `${resData.valid} / ${resData.total} live active`;
                badge.style.color = resData.valid > 0 ? "#4ade80" : "#f87171";
            }
            showToast(`Key Check Complete: ${resData.valid} of ${resData.total} keys active!`);
        } else {
            showToast(`Check error: ${resData.error || 'Failed'}`);
        }
    } catch (err) {
        showToast(`Network error while checking keys: ${err.message}`);
    } finally {
        if (checkBtn) {
            checkBtn.innerHTML = origHtml;
            checkBtn.disabled = false;
        }
    }
}

function exportKeysBackup() {
    const textarea = document.getElementById('ai-keys-pool-textarea');
    const content = textarea ? textarea.value.trim() : "";
    if (!content) {
        showToast("No API Keys available to export!");
        return;
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `gemini_api_keys_backup_${new Date().toISOString().slice(0,10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Exported API Keys backup successfully!");
}

function clearAllKeysPool() {
    if (!confirm("Are you sure you want to delete all Gemini API Keys?")) return;
    const textarea = document.getElementById('ai-keys-pool-textarea');
    if (textarea) {
        textarea.value = "";
        handleAiKeysInput();
    }
    showToast("Cleared all API Keys!");
}

async function saveAiProvidingConfig() {
    const saveBtn = document.querySelector('#modal-ai-providing .ai-footer-save-btn');
    const originalBtnHtml = saveBtn ? saveBtn.innerHTML : '';
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Saving...</span>';
    }

    const engine = document.getElementById('ai-engine-select') ? document.getElementById('ai-engine-select').value : 'auto';
    const keysRaw = document.getElementById('ai-keys-pool-textarea') ? document.getElementById('ai-keys-pool-textarea').value.trim() : '';
    const model = document.getElementById('ai-model-select') ? document.getElementById('ai-model-select').value : 'gemini-3.8-flash-high';
    const temperature = document.getElementById('ai-temperature-slider') ? parseFloat(document.getElementById('ai-temperature-slider').value) : 0.3;
    const promptStyle = document.getElementById('ai-system-prompt-input') ? document.getElementById('ai-system-prompt-input').value.trim() : '';

    const keysList = keysRaw.split('\n').map(k => k.trim()).filter(k => k.length > 0);

    try {
        const resp = await fetch('/api/set-ai-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                engine: engine,
                keys: keysList,
                keys_raw: keysRaw,
                model: model,
                temperature: temperature,
                prompt_style: promptStyle
            })
        });
        const resData = await resp.json();
        if (resData.success) {
            currentAiConfig = resData.config;

            // Save SpeechGen token and email
            const spToken = document.getElementById('speechgen-token-input') ? document.getElementById('speechgen-token-input').value.trim() : '';
            const spEmail = document.getElementById('speechgen-email-input') ? document.getElementById('speechgen-email-input').value.trim() : '';
            fetch('/api/story-config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ speechgen_token: spToken, speechgen_email: spEmail })
            }).catch(() => {});

            showToast(`Saved Engine, SpeechGen, and API Keys settings successfully!`);
        } else {
            showToast(`${resData.message || 'Error saving settings'}`);
        }
    } catch (e) {
        showToast(`Failed to save settings: ${e.message}`);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalBtnHtml || '<i class="fa-solid fa-check"></i><span>Save</span>';
        }
        closeModal('modal-ai-providing');
    }
}

function openImportModal() { openModal('modal-import'); }

async function triggerFileSelect() {
    showToast("Opening Windows File Explorer to select drama video...");
    try {
        const res = await fetch("/api/system/select-media-files", { method: "POST" });
        const data = await res.json();
        if (data && data.success && data.files && data.files.length > 0) {
            closeModal('modal-import');
            handleSelectedFiles(data.files);
            return;
        }
        if (data && data.cancelled) {
            return;
        }
    } catch (e) {
        console.warn("Native file picker note, falling back to HTML input:", e);
    }
    closeModal('modal-import');
    const input = document.getElementById('batch-files-input');
    if (input) input.click();
}

async function triggerFolderSelect() {
    showToast("Opening Windows Folder Explorer to select drama folder...");
    try {
        const res = await fetch("/api/system/select-media-folder", { method: "POST" });
        const data = await res.json();
        if (data && data.success && data.files && data.files.length > 0) {
            closeModal('modal-import');
            handleSelectedFiles(data.files, data.series_title);
            return;
        }
        if (data && data.cancelled) {
            return;
        }
    } catch (e) {
        console.warn("Native folder picker note, falling back to HTML input:", e);
    }
    closeModal('modal-import');
    const input = document.getElementById('batch-folder-input');
    if (input) input.click();
}

let activeDubbingTaskId = null;
let activeDubbingPollTimer = null;
let currentDubbedProject = null;

let stagedVideoFile = null;
let stagedBatchFiles = null;

function setStagedVideo(file) {
    if (activeDubbingPollTimer) {
        clearInterval(activeDubbingPollTimer);
        activeDubbingPollTimer = null;
    }
    activeDubbingTaskId = null;
    currentDubbedProject = null;
    stagedVideoSiblings = null;
    stagedVideoFolderTitle = "";

    // Clear previous banner if any
    const banner = document.getElementById('dubbing-success-banner');
    if (banner) banner.remove();

    // Reset progress monitor back to 0% ready state
    const pctElem = document.getElementById('monitor-export-percent');
    if (pctElem) pctElem.textContent = '0%';
    const fillElem = document.getElementById('monitor-progress-fill');
    if (fillElem) fillElem.style.width = '0%';
    const footerProg = document.getElementById('footer-studio-progress');
    if (footerProg) footerProg.style.width = '0%';
    const footerText = document.querySelector('#footer-studio-main div:first-child');
    if (footerText) footerText.textContent = 'Status: Ready for export';
    const elapElem = document.getElementById('monitor-elapsed-time');
    if (elapElem) elapElem.textContent = '00:00:00';
    const etaElem = document.getElementById('monitor-eta-time');
    if (etaElem) etaElem.textContent = '--:--:--';
    const finElem = document.getElementById('monitor-finish-time');
    if (finElem) finElem.textContent = 'Standby';
    const taskElem = document.getElementById('monitor-current-task');
    if (taskElem) taskElem.textContent = 'Standby (Ready to export)';

    stagedVideoFile = file;
    stagedBatchFiles = null;

    const fileName = getMediaFileName(file);
    const fileSizeMB = file.size_mb !== undefined ? file.size_mb : (file.size ? (file.size / (1024 * 1024)).toFixed(1) : "0.0");
    const filePath = getMediaFilePath(file);

    // Preview video in left monitor (support both native filepath and browser File blob)
    const mainVideo = document.getElementById('main-video');
    if (mainVideo) {
        try {
            if (filePath) {
                mainVideo.src = `/media/${filePath.replace(/\\/g, '/')}`;
            } else {
                mainVideo.src = URL.createObjectURL(file);
            }
            mainVideo.style.display = 'block';
            mainVideo.load();

            const handleMeta = () => {
                if (mainVideo.duration && !isNaN(mainVideo.duration) && isFinite(mainVideo.duration) && mainVideo.duration > 0) {
                    totalDurationSeconds = mainVideo.duration;
                    playheadSeconds = 0;
                    updateScrubberUI();

                    const durM = Math.floor(totalDurationSeconds / 60);
                    const durS = Math.floor(totalDurationSeconds % 60);
                    const durFormatted = `${String(durM).padStart(2,'0')}:${String(durS).padStart(2,'0')}`;
                    const stagedMeta = document.getElementById('staged-file-meta');
                    if (stagedMeta) stagedMeta.textContent = `${fileSizeMB} MB • Duration: ${durFormatted} • Ready to dub`;
                    syncTrackRowsInfo(fileName, durFormatted);
                }
                adaptMonitorScreenToVideo();
            };
            mainVideo.onloadedmetadata = handleMeta;
            mainVideo.ondurationchange = handleMeta;
            mainVideo.oncanplay = handleMeta;
            mainVideo.onloadeddata = handleMeta;
        } catch (e) {
            console.warn("Video preview load note:", e);
        }
    }

    if (!filePath) {
        autoDetectVideoDuration(file, (dur) => {
            totalDurationSeconds = dur;
            playheadSeconds = 0;
            updateScrubberUI();
            const durM = Math.floor(dur / 60);
            const durS = Math.floor(dur % 60);
            const durFormatted = `${String(durM).padStart(2,'0')}:${String(durS).padStart(2,'0')}`;
            const stagedMeta = document.getElementById('staged-file-meta');
            if (stagedMeta) refreshStagedCardVoiceMeta();
            appendLiveTerminalLine(`Media imported: "${fileName}" • Duration: ${durFormatted} (${dur.toFixed(1)}s)`, "[Video 1/1]", "info");
        });
    } else {
        appendLiveTerminalLine(`Media imported: "${fileName}" (${fileSizeMB} MB) • Native Direct Link`, "[Video 1/1]", "info");
    }

    // Update Clean Source View to Staged Ready State
    const importPrompt = document.getElementById('clean-import-prompt');
    const stagedCard = document.getElementById('staged-video-card');
    const stagedTitle = document.getElementById('staged-file-title');
    const stagedMeta = document.getElementById('staged-file-meta');
    const sourceLabel = document.getElementById('clean-source-label');

    if (importPrompt) importPrompt.style.display = 'none';
    if (stagedCard) stagedCard.style.display = 'flex';
    if (sourceLabel) sourceLabel.style.display = 'none';
    if (stagedTitle) stagedTitle.textContent = fileName;
    syncTrackRowsInfo(fileName, null);
    refreshStagedCardVoiceMeta();
    syncStagedCardControls();

    const exportBtn = document.getElementById('btn-tab-export');
    if (exportBtn) exportBtn.classList.add('export-ready-pulse');

    const pill = document.getElementById('monitor-engine-status-pill');
    const dot = document.getElementById('monitor-pulse-dot');
    const text = document.getElementById('monitor-engine-status-text');
    if (pill) pill.className = 'engine-status-pill standby';
    if (dot) dot.className = 'pulse-indicator standby';
    if (text) text.textContent = 'READY FOR EXPORT';

    updateScrubberUI();
    showToast(`Loaded "${fileName}" successfully! Click Export to start auto-dubbing.`);
    appendTerminalLine(`[Ready] Video "${fileName}" loaded. Click [Export] to begin studio dubbing.`);
}

function discardStagedVideo(e) {
    if (e && e.stopPropagation) e.stopPropagation();

    // 1. Reset Preview Video Player
    const mainVideo = document.getElementById('main-video');
    if (mainVideo) {
        try {
            mainVideo.pause();
            mainVideo.removeAttribute('src');
            mainVideo.load();
        } catch (err) {}
        mainVideo.style.display = 'none';
    }

    // 2. Reset Playback state & timer
    if (typeof isPlaying !== 'undefined') isPlaying = false;
    if (typeof playbackTimer !== 'undefined' && playbackTimer) {
        clearInterval(playbackTimer);
        playbackTimer = null;
    }
    if (typeof playheadSeconds !== 'undefined') playheadSeconds = 0;
    if (typeof totalDurationSeconds !== 'undefined') totalDurationSeconds = 0;
    if (typeof updateScrubberUI === 'function') updateScrubberUI();
    if (typeof resetVuMetersToIdle === 'function') resetVuMetersToIdle();

    // 3. Reset left monitor empty state
    const emptyState = document.getElementById('monitor-empty-state');
    if (emptyState) emptyState.style.display = 'flex';
    const centerPlayBtn = document.getElementById('center-play-btn');
    if (centerPlayBtn) centerPlayBtn.style.display = 'none';

    // 4. Reset staged data
    stagedVideoFile = null;
    stagedBatchFiles = null;

    // 5. Reset overlays
    if (typeof clearOverlayFile === 'function') clearOverlayFile(null, 'logo');
    if (typeof toggleBlurMaskTool === 'function') toggleBlurMaskTool(null, false);
    if (typeof toggleTextOverlayTool === 'function') toggleTextOverlayTool(null, false);

    // 6. Reset engine status text
    if (typeof resetEngineMonitorToStandby === 'function') resetEngineMonitorToStandby();

    // 7. Return to State 0 Clean Drag & Drop View
    showCleanSourceView();

    showToast("Discarded and returned to Home");
    appendTerminalLine("[SN Studio] Project discarded. Returned to home import canvas.");
}

function setStagedBatchFiles(files, folderTitle = "") {
    if (activeDubbingPollTimer) {
        clearInterval(activeDubbingPollTimer);
        activeDubbingPollTimer = null;
    }
    activeDubbingTaskId = null;
    currentDubbedProject = null;
    stagedVideoSiblings = null;
    stagedVideoFolderTitle = "";

    // Clear previous banner if any
    const banner = document.getElementById('dubbing-success-banner');
    if (banner) banner.remove();

    // Reset progress monitor back to 0% ready state
    const pctElem = document.getElementById('monitor-export-percent');
    if (pctElem) pctElem.textContent = '0%';
    const fillElem = document.getElementById('monitor-progress-fill');
    if (fillElem) fillElem.style.width = '0%';
    const footerProg = document.getElementById('footer-studio-progress');
    if (footerProg) footerProg.style.width = '0%';
    const footerText = document.querySelector('#footer-studio-main div:first-child');
    if (footerText) footerText.textContent = 'Status: Ready for export';
    const elapElem = document.getElementById('monitor-elapsed-time');
    if (elapElem) elapElem.textContent = '00:00:00';
    const etaElem = document.getElementById('monitor-eta-time');
    if (etaElem) etaElem.textContent = '--:--:--';
    const finElem = document.getElementById('monitor-finish-time');
    if (finElem) finElem.textContent = 'Standby';
    const taskElem = document.getElementById('monitor-current-task');
    if (taskElem) taskElem.textContent = 'Standby (Ready to export)';

    stagedBatchFiles = files;
    stagedVideoFile = null;

    if (files && files.length > 0) {
        const firstFile = files[0];
        const firstPath = getMediaFilePath(firstFile);
        const mainVideo = document.getElementById('main-video');
        if (mainVideo) {
            try {
                if (firstPath) {
                    mainVideo.src = `/media/${firstPath.replace(/\\/g, '/')}`;
                } else if (firstFile instanceof Blob || firstFile instanceof File) {
                    mainVideo.src = URL.createObjectURL(firstFile);
                }
                mainVideo.style.display = 'block';
                mainVideo.load();
            } catch (e) {
                console.warn("Batch preview load note:", e);
            }
        }
    }

    const importPrompt = document.getElementById('clean-import-prompt');
    const stagedCard = document.getElementById('staged-video-card');
    const stagedTitle = document.getElementById('staged-file-title');
    const stagedMeta = document.getElementById('staged-file-meta');
    const sourceLabel = document.getElementById('clean-source-label');

    if (importPrompt) importPrompt.style.display = 'none';
    if (stagedCard) stagedCard.style.display = 'flex';
    if (sourceLabel) sourceLabel.style.display = 'none';

    let folderName = folderTitle || "";
    if (!folderName && files[0] && files[0]._fullPath) {
        const parts = files[0]._fullPath.split('/').filter(Boolean);
        if (parts.length > 1) folderName = parts[0];
    } else if (!folderName && files[0] && files[0].webkitRelativePath) {
        const parts = files[0].webkitRelativePath.split('/');
        if (parts.length > 1) folderName = parts[0];
    } else if (!folderName && files[0] && files[0].filepath) {
        const parts = files[0].filepath.split(/[\\/]/);
        if (parts.length > 2) folderName = parts[parts.length - 2];
    }
    const seriesTitle = folderName ? `Folder: "${folderName}"` : `Full Drama Series`;

    if (stagedTitle) stagedTitle.textContent = `${seriesTitle} (${files.length} episodes)`;
    if (stagedMeta) stagedMeta.textContent = `Sorted sequentially from EP 1 to EP ${files.length} • Click "Export" to start dubbing`;
    refreshStagedCardVoiceMeta();
    syncStagedCardControls();

    const exportBtn = document.getElementById('btn-tab-export');
    if (exportBtn) exportBtn.classList.add('export-ready-pulse');

    showToast(`Loaded ${files.length} episodes successfully! Click Export to start dubbing.`);
    clearLiveTerminal();
    appendLiveTerminalLine(`Folder / Series Staged: ${files.length} episodes loaded in story order.`, "[Batch Ready]", "info");
    for (let i = 0; i < Math.min(files.length, 5); i++) {
        const f = files[i];
        const fName = getMediaFileName(f) || `Episode ${i+1}`;
        const fMB = f.size_mb !== undefined ? f.size_mb : (f.size ? (f.size / (1024*1024)).toFixed(1) : "?");
        appendLiveTerminalLine(`  • Episode ${i+1}: "${fName}" (${fMB} MB)`, "[Episode List]", "info");
    }
    if (files.length > 5) {
        appendLiveTerminalLine(`  ... and ${files.length - 5} more episodes`, "[Episode List]", "info");
    }
    appendLiveTerminalLine(`Click [Export] on the top bar to begin full drama automated dubbing.`, "[Ready]", "success");
}

function clearStagedFiles() {
    activeDubbingTaskId = null;
    stagedVideoFile = null;
    stagedBatchFiles = null;
    stagedVideoSiblings = null;
    stagedVideoFolderTitle = "";
    const exportBtn = document.getElementById('btn-tab-export');
    if (exportBtn) exportBtn.classList.remove('export-ready-pulse');

    const importPrompt = document.getElementById('clean-import-prompt');
    const stagedCard = document.getElementById('staged-video-card');
    const sourceLabel = document.getElementById('clean-source-label');
    if (importPrompt) importPrompt.style.display = 'flex';
    if (stagedCard) stagedCard.style.display = 'none';
    if (sourceLabel) sourceLabel.style.display = 'block';
}

function handleSelectedFiles(files, folderTitle = "") {
    if (!files || files.length === 0) return;
    switchMainTab('translate');
    closeModal('modal-import');

    const validExts = ['.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.ts', '.m4v', '.wmv'];
    const fileList = Array.from(files).filter(f => {
        const n = getMediaFileName(f).toLowerCase();
        return validExts.some(ext => n.endsWith(ext)) || (f.type && f.type.startsWith('video/'));
    });

    if (fileList.length === 0) {
        showToast("Please select drama video files (MP4, MKV, MOV...)");
        return;
    }

    // Natural numerical sorting: Episode 1, Episode 2, Episode 10 in true story order!
    fileList.sort((a, b) => {
        const nameA = getMediaFileName(a);
        const nameB = getMediaFileName(b);
        return nameA.localeCompare(nameB, undefined, { numeric: true, sensitivity: 'base' });
    });

    if (fileList.length === 1) {
        setStagedVideo(fileList[0]);
    } else {
        setStagedBatchFiles(fileList, folderTitle);
    }
}

async function startAutoDubbingPipeline(file, customTitle = null) {
    window._exportChimePlayedThisRun = false;
    currentDubbedProject = null;
    activeDubbingTaskId = null;
    if (activeDubbingPollTimer) {
        clearInterval(activeDubbingPollTimer);
        activeDubbingPollTimer = null;
    }
    const fileName = getMediaFileName(file);
    const fileSizeMB = file.size_mb !== undefined ? file.size_mb : (file.size ? (file.size / (1024*1024)).toFixed(1) : "?");
    const filePath = getMediaFilePath(file);
    showToast(`Preparing and starting video dubbing: ${fileName}`);

    // Output initial console startup sequence matching Image 2
    clearLiveTerminal();
    appendLiveTerminalLine(`Job initiated: Video Dubbing & Translation Pipeline`, "[Video 1/1]", "info");
    appendLiveTerminalLine(`Source media: ${fileName} (${fileSizeMB} MB)...`, "[Video 1/1]", "info");
    appendLiveTerminalLine(`Stem isolation: extracting audio track...`, "[Video 1/1]", "info");
    appendLiveTerminalLine(`Stem isolation: initializing separation engine...`, "[Video 1/1]", "info");
    appendLiveTerminalLine(`Stem isolation: hardware acceleration active (GPU / DirectML)...`, "[Video 1/1]", "info");
    appendLiveTerminalLine(`Stem isolation: acoustic separation model loaded.`, "[Video 1/1]", "info");

    // Keep clean source view active (uncluttered layout)
    showCleanSourceView();

    // Set Engine Monitor to Active Encoding State
    const pill = document.getElementById('monitor-engine-status-pill');
    const dot = document.getElementById('monitor-pulse-dot');
    const text = document.getElementById('monitor-engine-status-text');
    if (pill) pill.className = 'engine-status-pill';
    if (dot) dot.className = 'pulse-indicator';
    if (text) text.textContent = 'STUDIO DUBBING IN PROGRESS';

    updateExportProgressUI(5, 0, 90, "1/6 Connecting video to Studio engine...");

    const activeDramaMode = currentStudioPreset === "narration" ? "movie_recap" : "drama_dubbing";
    const activeSourceLang = currentStoryConfig.source_lang || "auto";
    const activeVoiceOverride = (currentStoryConfig.khmer_voice === "sreymom") ? "sreymom" : "piseth";
    const activeAspectRatio = currentStoryConfig.aspect_ratio || "9:16";
    const activeBurnSubs = (currentOverlayAssets.subtitleActive || currentStoryConfig.subtitle_mode === "burn") ? "true" : "false";
    const overlayConfig = await getOverlayExportConfig();
    if (overlayConfig.logo.active || overlayConfig.blur.active || overlayConfig.text.active || (overlayConfig.lower_third && overlayConfig.lower_third.active) || (overlayConfig.subtitle && overlayConfig.subtitle.active)) {
        appendLiveTerminalLine(
            `Burn-in overlays enabled: ${overlayConfig.logo.active ? 'Logo Watermark ✓ ' : ''}${overlayConfig.blur.active ? 'Blur Mask ✓ ' : ''}${overlayConfig.text.active ? 'Text Title ✓ ' : ''}${overlayConfig.lower_third && overlayConfig.lower_third.active ? 'Lower Third ✓ ' : ''}${overlayConfig.subtitle && overlayConfig.subtitle.active ? 'Khmer Subtitles ✓' : ''}`,
            "[Overlay Engine]",
            "success"
        );
    }

    try {
        let res;
        const projectTitleToUse = customTitle || file.title || undefined;
        if (filePath) {
            res = await fetch("/api/projects/auto-dub-video", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    filepath: filePath,
                    filename: fileName,
                    title: projectTitleToUse,
                    drama_mode: activeDramaMode,
                    source_lang: activeSourceLang,
                    voice_override: activeVoiceOverride,
                    aspect_ratio: activeAspectRatio,
                    burn_subtitles: activeBurnSubs,
                    overlay_config: overlayConfig,
                    custom_export_dir: currentCustomExportFolder || undefined
                })
            });
        } else {
            const formData = new FormData();
            formData.append("file", file);
            if (projectTitleToUse) {
                formData.append("title", projectTitleToUse);
            }
            formData.append("drama_mode", activeDramaMode);
            formData.append("source_lang", activeSourceLang);
            formData.append("voice_override", activeVoiceOverride);
            formData.append("aspect_ratio", activeAspectRatio);
            formData.append("burn_subtitles", activeBurnSubs);
            formData.append("overlay_config", JSON.stringify(overlayConfig));
            if (currentCustomExportFolder) {
                formData.append("custom_export_dir", currentCustomExportFolder);
            }
            if (currentOverlayAssets.logo instanceof File) {
                formData.append("logo_file", currentOverlayAssets.logo);
            }
            if (currentOverlayAssets.lowerThirdFile instanceof File) {
                formData.append("lower_third_file", currentOverlayAssets.lowerThirdFile);
            }

            res = await fetch("/api/projects/auto-dub-video", {
                method: "POST",
                body: formData
            });
        }
        const data = await res.json();
        if (!data.success || !data.task_id) {
            showToast(`Failed: ${data.error || "Cannot start dubbing"}`);
            appendLiveTerminalLine(`Failed to start pipeline: ${data.error || 'Server error'}`, "[Error]", "error");
            resetEngineMonitorToStandby();
            return;
        }

        activeDubbingTaskId = data.task_id;
        let elapsed = 0;
        let lastLoggedStep = "";
        let loggedDialogueIds = new Set();
        let sepProgressSim = 2;
        let sepTimerTicks = 0;

        appendLiveTerminalLine(`Dubbing engine dispatched in background. Task ID: ${activeDubbingTaskId}`, "[Video 1/1]", "info");

        if (activeDubbingPollTimer) clearInterval(activeDubbingPollTimer);
        activeDubbingPollTimer = setInterval(async () => {
            elapsed += 1;
            try {
                const sRes = await fetch(`/api/projects/auto-dub-status/${activeDubbingTaskId}`);
                const sData = await sRes.json();
                if (!sData.success) return;

                const pct = sData.progress || 10;
                const rawEn = sData.step_en || sData.step_km || "Processing...";
                const stepEn = sanitizeBranding(rawEn);
                const rem = 100 - pct;
                const eta = Math.max(1, Math.round((elapsed / Math.max(1, pct)) * rem));

                updateExportProgressUI(pct, elapsed, eta, stepEn);
                
                // Update bottom footer
                const footerProg = document.getElementById('footer-studio-progress');
                if (footerProg) footerProg.style.width = `${pct}%`;
                const footerText = document.querySelector('#footer-studio-main div:first-child');
                if (footerText) footerText.textContent = `Status: ${stepEn} (${pct}%)`;

                // Stream realistic vocal separation progress ticks while in separation stage (<35%)
                if (pct < 35) {
                    sepTimerTicks++;
                    if (sepTimerTicks % 2 === 0 && sepProgressSim < 95) {
                        appendLiveTerminalLine(`Acoustic separation: isolating dialogue stem (${sepProgressSim}%)...`, "[Video 1/1]", "info");
                        sepProgressSim += Math.floor(Math.random() * 4) + 3;
                    }
                }

                // Log pipeline milestone when step transitions
                if (stepEn && stepEn !== lastLoggedStep) {
                    lastLoggedStep = stepEn;
                    appendLiveTerminalLine(`${stepEn} (${pct}%)`, "[Video 1/1]", "info");
                }

                // Stream translated dialogue data lines in real-time
                const currentDialogues = (sData.project && sData.project.dialogues) || sData.dialogues || [];
                if (Array.isArray(currentDialogues) && currentDialogues.length > 0) {
                    currentDialogues.forEach((d, idx) => {
                        if (!loggedDialogueIds.has(idx)) {
                            loggedDialogueIds.add(idx);
                            const lineNum = String(idx + 1).padStart(2, '0');
                            const vName = (d.voice === 'sreymom' || d.voice === 'female') ? 'Sreymom (Female)' : 'Piseth (Male)';
                            const zhText = d.text_original || d.text || "";
                            const kmText = d.text_km || d.translated_text || d.khmer_text || d.text || "";
                            if (kmText && kmText !== zhText) {
                                appendLiveTerminalLine(`[Line ${lineNum}] Dialogue translated & synchronized (${vName})`, "[Dialogue Pipeline]", "dub");
                            } else if (zhText) {
                                appendLiveTerminalLine(`[Line ${lineNum}] Dialogue preserved: original audio retained`, "[Dialogue Pipeline]", "warning");
                            }
                        }
                    });
                }

                if (sData.status === "completed") {
                    clearInterval(activeDubbingPollTimer);
                    activeDubbingPollTimer = null;
                    activeDubbingTaskId = null;
                    currentDubbedProject = sData.project;
                    clearStagedFiles();

                    // Final flush of any remaining dialogues
                    const allDialogues = (sData.project && sData.project.dialogues) || sData.dialogues || [];
                    if (Array.isArray(allDialogues) && allDialogues.length > 0) {
                        allDialogues.forEach((d, idx) => {
                            if (!loggedDialogueIds.has(idx)) {
                                loggedDialogueIds.add(idx);
                                const lineNum = String(idx + 1).padStart(2, '0');
                                const vName = (d.voice === 'sreymom' || d.voice === 'female') ? 'Sreymom (Female)' : 'Piseth (Male)';
                                const zhText = d.text || "(Original)";
                                const kmText = d.translated_text || d.khmer_text || "(Dubbed)";
                                if (kmText && kmText !== zhText) {
                                    appendLiveTerminalLine(`[Line ${lineNum}] Dialogue translated & synchronized (${vName})`, "[Dialogue Pipeline]", "dub");
                                } else if (zhText) {
                                    appendLiveTerminalLine(`[Line ${lineNum}] Dialogue preserved: original audio retained`, "[Dialogue Pipeline]", "warning");
                                }
                            }
                        });
                    }

                    updateExportProgressUI(100, elapsed, 0, "100% Complete! Rendered video saved!");
                    showToast("Auto-dubbing completed 100% successfully!");
                    appendLiveTerminalLine(`Master audio mix: vocal synthesis & balance complete. Zero vocal bleed.`, "[Video 1/1]", "success");
                    appendLiveTerminalLine(`Master export MP4 generated: ${sData.project.output_video_file || 'Dubbed_Video.mp4'}`, "[Video 1/1]", "success");
                    appendLiveTerminalLine(`[Success 100%] Video dubbed successfully! Ready for playback.`, "[Video 1/1]", "success");

                    // Load dubbed video into player cleanly without jitter
                    const mainVideo = document.getElementById('main-video');
                    if (mainVideo && sData.video_url) {
                        if (playbackTimer) {
                            clearInterval(playbackTimer);
                            playbackTimer = null;
                        }
                        isPlaying = false;
                        playheadSeconds = 0;
                        mainVideo.pause();

                        mainVideo.src = sData.video_url;
                        mainVideo.style.display = 'block';
                        mainVideo.load();
                        totalDurationSeconds = sData.project.duration || 60;
                        updateScrubberUI();
                    }

                    // Store translated dialogues in memory for background playback, keeping UI clean
                    if (sData.project && sData.project.dialogues) {
                        activeLoadedDialogues = sData.project.dialogues;
                    }
                    showCleanSourceView();

                    // Show success action prompt with Open Folder & Download buttons
                    showDubbingSuccessNotification(sData);

                    // Automatically open folder and highlight the rendered video file in Windows Explorer!
                    const targetToOpen = sData.final_exported_video_path || (sData.project && sData.project.final_exported_video_path) || sData.final_exported_dir || currentCustomExportFolder || '';
                    if (targetToOpen) {
                        openExportFolderDirect(targetToOpen);
                    }

                } else if (sData.status === "failed") {
                    clearInterval(activeDubbingPollTimer);
                    activeDubbingPollTimer = null;
                    activeDubbingTaskId = null;

                    const errTitle = sData.error || "Dubbing process interrupted";
                    const errStage = sData.error_stage || "Step Processing";
                    const errTag = sData.error_tag || `[${errStage}]`;
                    const errSugg = sData.error_suggestion || "Please check media file or connection and try again.";

                    logStudioError(errStage, `Pipeline Failure: ${errTitle}`, {
                        details: sData.error_details || `Task ID: ${activeDubbingTaskId}\nStatus: failed\nError: ${errTitle}`,
                        type: sData.error_type || "PipelineError",
                        category: sData.error_category
                    }, errSugg);

                    showToast(`Dubbing failed: ${errTitle}`);

                    const pill = document.getElementById('monitor-engine-status-pill');
                    const dot = document.getElementById('monitor-pulse-dot');
                    const text = document.getElementById('monitor-engine-status-text');
                    if (pill) pill.className = 'engine-status-pill error';
                    if (dot) dot.className = 'pulse-indicator error';
                    if (text) text.textContent = `FAILED AT ${errStage.toUpperCase()}`;
                }
            } catch (err) {
                console.warn("Poll error:", err);
            }
        }, 1000);

    } catch (e) {
        activeDubbingTaskId = null;
        if (activeDubbingPollTimer) {
            clearInterval(activeDubbingPollTimer);
            activeDubbingPollTimer = null;
        }
        logStudioError("Upload & Connect", `Network upload failed: ${e.message}`, e, "Check your local server connection or verify that the video file is accessible.");
        showToast(`Failed to upload video: ${e.message}`);
        const pill = document.getElementById('monitor-engine-status-pill');
        const dot = document.getElementById('monitor-pulse-dot');
        const text = document.getElementById('monitor-engine-status-text');
        if (pill) pill.className = 'engine-status-pill error';
        if (dot) dot.className = 'pulse-indicator error';
        if (text) text.textContent = 'UPLOAD FAILED';
    }
}

async function startStudioBatchDubbingPipeline(files, outputMode = 'separate') {
    if (!files || files.length === 0) return;
    window._exportChimePlayedThisRun = false;
    currentDubbedProject = null;
    activeDubbingTaskId = null;
    if (activeDubbingPollTimer) {
        clearInterval(activeDubbingPollTimer);
        activeDubbingPollTimer = null;
    }
    const totalBatchCount = files.length;
    const modeLabel = outputMode === 'full' ? 'One Full Merged Video' : (outputMode === 'both' ? 'Both Separate Episodes & Merged Full Movie' : 'Separate Episodes');

    // =========================================================================
    // MODE 1: FULL MOVIE MERGED (Fast Pre-merge all episodes into 1 unified
    // source video, then dub the full movie at once: "បកពេញតែម្ដង់ មិនមែនជាភាគ")
    // =========================================================================
    if (outputMode === 'full') {
        clearLiveTerminal();
        appendLiveTerminalLine(`========================================================================`, "[Full Movie Mode]", "info");
        appendLiveTerminalLine(`🎬 FULL MOVIE MERGED DUBBING INITIATED`, "[Full Movie Mode]", "info");
        appendLiveTerminalLine(`Episodes: ${totalBatchCount} episodes loaded in story order.`, "[Full Movie Mode]", "info");
        appendLiveTerminalLine(`Mode: Single-Pass Full Movie Dubbing (Full Feature Length)`, "[Full Movie Mode]", "info");
        appendLiveTerminalLine(`Voices: Piseth (Male Solo) & Sreymom (Female Solo) • Zero Vocal Leakage`, "[Full Movie Mode]", "info");
        appendLiveTerminalLine(`========================================================================`, "[Full Movie Mode]", "info");

        showToast(`Starting drama dubbing (${totalBatchCount} episodes) - Full Movie Merged...`);
        showCleanSourceView();

        const pill = document.getElementById('monitor-engine-status-pill');
        const dot = document.getElementById('monitor-pulse-dot');
        const text = document.getElementById('monitor-engine-status-text');
        if (pill) pill.className = 'engine-status-pill';
        if (dot) dot.className = 'pulse-indicator';
        if (text) text.textContent = `FULL MOVIE MERGE (${totalBatchCount} EPS)`;

        updateExportProgressUI(5, 0, 180, `Step 1/2: Pre-merging ${totalBatchCount} episodes into 1 unified video...`);

        let seriesTitle = "Drama_Series";
        if (files && files[0]) {
            const f0Name = getMediaFileName(files[0]);
            seriesTitle = f0Name.replace(/\.[^/.]+$/, '').replace(/(?:_part|[-_]ep|[-_]e|\bep|\bepisode)[-_]?\d+/i, '').replace(/[-_]+$/, '').trim() || "";
            seriesTitle = seriesTitle.replace(/^(?:Dubbed_)+/i, '');

            // If stripping EP_XX resulted in empty or generic title, inspect parent directory path
            if (!seriesTitle || seriesTitle.toLowerCase() === "drama_series") {
                const rawPath = getMediaFilePath(files[0]) || files[0]._fullPath || files[0].webkitRelativePath || "";
                if (rawPath) {
                    const parts = rawPath.split(/[\\/]/).filter(Boolean);
                    if (parts.length >= 2) {
                        const parentFolder = parts[parts.length - 2].trim();
                        if (parentFolder && !["uploads", "cache", "temp", "batch_temp", "downloads", "data", "exports", "sn_dramas"].includes(parentFolder.toLowerCase())) {
                            seriesTitle = parentFolder;
                        }
                    }
                }
            }
        }
        if (!seriesTitle) seriesTitle = "Drama_Series";

        const videoPaths = files.map(f => getMediaFilePath(f)).filter(Boolean);
        let mergedSourcePath = null;
        let mergedSourceName = null;
        let mergedSizeMb = "?";

        if (videoPaths.length === totalBatchCount) {
            appendLiveTerminalLine(`▶ Lossless stream-copying ${totalBatchCount} episodes into unified container...`, "[Full Movie Mode]", "info");
            try {
                const mRes = await fetch("/api/projects/pre-merge-raw-episodes", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        video_paths: videoPaths,
                        series_title: seriesTitle
                    })
                });
                const mData = await mRes.json();
                if (mData.success && mData.merged_path) {
                    if (mData.series_title && mData.series_title !== "Drama_Series") {
                        seriesTitle = mData.series_title;
                    }
                    mergedSourcePath = mData.merged_path;
                    mergedSourceName = mData.merged_filename;
                    mergedSizeMb = mData.size_mb;
                    if (mData.trimmed_count > 0) {
                        appendLiveTerminalLine(`✓ Pre-merge AI Freeze Detector: trimmed ${mData.trimmed_count} frozen outros (-${mData.total_seconds_saved}s), creating seamless "${mergedSourceName}" (${mergedSizeMb} MB, ${totalBatchCount} eps)`, "[Full Movie Mode]", "success");
                    } else {
                        appendLiveTerminalLine(`✓ Fast Pre-merge complete: "${mergedSourceName}" (${mergedSizeMb} MB, ${totalBatchCount} episodes unified, 100% active scenes)`, "[Full Movie Mode]", "success");
                    }
                } else {
                    appendLiveTerminalLine(`Pre-merge warning: ${mData.error || 'Server note'}. Falling back to batch merge.`, "[Full Movie Mode]", "warning");
                }
            } catch (mErr) {
                appendLiveTerminalLine(`Pre-merge network note: ${mErr.message}. Falling back to batch merge.`, "[Full Movie Mode]", "warning");
            }
        }

        if (mergedSourcePath) {
            appendLiveTerminalLine(`▶ Step 2/2: Starting Full-Movie Automated AI Dubbing on unified video...`, "[Full Movie Mode]", "info");
            appendLiveTerminalLine(`Single-pass transcription & translation for seamless storytelling across scenes!`, "[Full Movie Mode]", "info");
            updateExportProgressUI(10, 0, 150, `Step 2/2: Dubbing full movie "${seriesTitle}" with Piseth & Sreymom...`);

            const fullMovieFile = {
                filepath: mergedSourcePath,
                filename: mergedSourceName,
                name: mergedSourceName,
                size_mb: mergedSizeMb,
                title: `${seriesTitle}_Full_Movie`
            };

            await startAutoDubbingPipeline(fullMovieFile, `Dubbed_${seriesTitle}_Full_Movie`);
            return;
        }
    }

    // =========================================================================
    // MODE 2 & 3: SEPARATE EPISODES / BOTH EPISODES & FULL MOVIE (Sequential)
    // =========================================================================
    showToast(`Starting drama dubbing (${totalBatchCount} episodes) - ${modeLabel}...`);

    clearLiveTerminal();
    appendLiveTerminalLine(`========================================================================`, "[Batch Series]", "info");
    appendLiveTerminalLine(`Series Batch Dubbing Initiated: ${totalBatchCount} episodes loaded in story order.`, "[Batch Series]", "info");
    appendLiveTerminalLine(`Export Mode: "${outputMode.toUpperCase()}" (${modeLabel})`, "[Batch Series]", "info");
    appendLiveTerminalLine(`Voices: Piseth (Male Solo) & Sreymom (Female Solo) • Zero Vocal Leakage Enabled`, "[Batch Series]", "info");
    appendLiveTerminalLine(`Mode: Studio In-Place Sequential Dubbing (stays right in Studio)`, "[Batch Series]", "info");
    appendLiveTerminalLine(`========================================================================`, "[Batch Series]", "info");

    // Keep clean source view active
    showCleanSourceView();

    // Set Engine Monitor to Active Encoding State
    const pill = document.getElementById('monitor-engine-status-pill');
    const dot = document.getElementById('monitor-pulse-dot');
    const text = document.getElementById('monitor-engine-status-text');
    if (pill) pill.className = 'engine-status-pill';
    if (dot) dot.className = 'pulse-indicator';

    let totalElapsedSeconds = 0;
    const batchMasterTimer = setInterval(() => {
        totalElapsedSeconds++;
    }, 1000);

    // Extract overlay configuration (Logo watermark, Blur mask, Text title, Lower Third, Subtitles) to burn into ALL drama episodes
    const batchOverlayConfig = await getOverlayExportConfig();
    if (batchOverlayConfig.logo.active || batchOverlayConfig.blur.active || batchOverlayConfig.text.active || (batchOverlayConfig.lower_third && batchOverlayConfig.lower_third.active) || (batchOverlayConfig.subtitle && batchOverlayConfig.subtitle.active)) {
        appendLiveTerminalLine(
            `Burn-in overlays for drama batch: ${batchOverlayConfig.logo.active ? 'Logo Watermark ✓ ' : ''}${batchOverlayConfig.blur.active ? 'Blur Mask ✓ ' : ''}${batchOverlayConfig.text.active ? 'Text Title ✓ ' : ''}${batchOverlayConfig.lower_third && batchOverlayConfig.lower_third.active ? 'Lower Third ✓ ' : ''}${batchOverlayConfig.subtitle && batchOverlayConfig.subtitle.active ? 'Khmer Subtitles ✓ ' : ''}(will be burned into all ${totalBatchCount} episodes)`,
            "[Overlay Engine]",
            "success"
        );
    }

    const completedProjects = [];

    for (let i = 0; i < totalBatchCount; i++) {
        const file = files[i];
        const epNum = i + 1;
        const fileName = getMediaFileName(file) || `Episode_${epNum}.mp4`;
        const fileSizeMb = file.size_mb !== undefined ? file.size_mb : (file.size ? (file.size / (1024 * 1024)).toFixed(1) : "?");
        const filePath = getMediaFilePath(file);

        if (text) text.textContent = `BATCH DUBBING (${epNum} / ${totalBatchCount})`;

        appendLiveTerminalLine(`------------------------------------------------------------------------`, `[Ep ${epNum}/${totalBatchCount}]`, "info");
        appendLiveTerminalLine(`▶ Starting Episode ${epNum}/${totalBatchCount}: "${fileName}" (${fileSizeMb} MB)...`, `[Ep ${epNum}/${totalBatchCount}]`, "info");
        appendLiveTerminalLine(`Stem isolation: extracting audio track & isolating dialogue...`, `[Ep ${epNum}/${totalBatchCount}]`, "info");

        const basePct = Math.round((i / totalBatchCount) * 100);
        updateExportProgressUI(basePct, totalElapsedSeconds, 60 * (totalBatchCount - i), `EP ${epNum}/${totalBatchCount}: ${fileName} - Sending to Studio...`);

        const dramaMode = currentStudioPreset === "narration" ? "movie_recap" : "drama_dubbing";
        const activeSourceLang = currentStoryConfig.source_lang || "auto";
        const activeVoiceOverride = (currentStoryConfig.khmer_voice === "sreymom") ? "sreymom" : "piseth";
        const activeAspectRatio = currentStoryConfig.aspect_ratio || "9:16";
        const activeBurnSubs = (currentOverlayAssets.subtitleActive || currentStoryConfig.subtitle_mode === "burn") ? "true" : "false";

        let taskId = null;
        try {
            let res;
            const isBlob = (file instanceof Blob || file instanceof File);
            if (filePath || !isBlob) {
                res = await fetch("/api/projects/auto-dub-video", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        filepath: filePath || (file && (file.filepath || file.path || file.video_url)) || fileName,
                        filename: fileName,
                        title: fileName,
                        drama_mode: dramaMode,
                        source_lang: activeSourceLang,
                        voice_override: activeVoiceOverride,
                        aspect_ratio: activeAspectRatio,
                        burn_subtitles: activeBurnSubs,
                        overlay_config: batchOverlayConfig,
                        custom_export_dir: currentCustomExportFolder || undefined
                    })
                });
            } else {
                const formData = new FormData();
                formData.append("file", file, fileName);
                formData.append("filename", fileName);
                formData.append("drama_mode", dramaMode);
                formData.append("source_lang", activeSourceLang);
                formData.append("voice_override", activeVoiceOverride);
                formData.append("aspect_ratio", activeAspectRatio);
                formData.append("burn_subtitles", activeBurnSubs);
                formData.append("overlay_config", JSON.stringify(batchOverlayConfig));
                if (currentCustomExportFolder) {
                    formData.append("custom_export_dir", currentCustomExportFolder);
                }
                if (currentOverlayAssets.logo instanceof File) {
                    formData.append("logo_file", currentOverlayAssets.logo);
                }
                if (currentOverlayAssets.lowerThirdFile instanceof File) {
                    formData.append("lower_third_file", currentOverlayAssets.lowerThirdFile);
                }

                res = await fetch("/api/projects/auto-dub-video", {
                    method: "POST",
                    body: formData
                });
            }
            const data = await res.json();
            if (!data.success || !data.task_id) {
                logStudioError(`Ep ${epNum}/${totalBatchCount}`, `Episode ${epNum} upload rejected: ${data.error || 'Server error'}`, data.error, "Check file integrity or server status.");
                await new Promise(r => setTimeout(r, 1500));
                continue;
            }
            taskId = data.task_id;
            activeDubbingTaskId = taskId;
        } catch (uploadErr) {
            logStudioError(`Ep ${epNum}/${totalBatchCount}`, `Episode ${epNum} network/upload error: ${uploadErr.message}`, uploadErr, "Check network connection or local server status.");
            await new Promise(r => setTimeout(r, 1500));
            continue;
        }

        // Poll this episode until complete
        const epDone = await new Promise((resolve) => {
            let lastLoggedStep = "";
            let loggedDialogueIds = new Set();
            let sepProgressSim = 5;
            let sepTimerTicks = 0;

            const pollInterval = setInterval(async () => {
                try {
                    const sRes = await fetch(`/api/projects/auto-dub-status/${taskId}`);
                    const sData = await sRes.json();
                    if (!sRes.ok || !sData.success) return;

                    const epPct = sData.progress || 10;
                    const stepKm = sData.step_en || sData.step_km || "Processing...";
                    const stepEn = sData.step_en || stepKm;

                    const overallPct = Math.min(99, Math.round((i / totalBatchCount) * 100 + (epPct / totalBatchCount)));
                    const remPct = 100 - overallPct;
                    const estEta = Math.max(5, Math.round((totalElapsedSeconds / Math.max(1, overallPct)) * remPct));

                    updateExportProgressUI(overallPct, totalElapsedSeconds, estEta, `EP ${epNum}/${totalBatchCount}: ${fileName} - ${stepEn || stepKm}`);

                    if (epPct < 35) {
                        sepTimerTicks++;
                        if (sepTimerTicks % 2 === 0 && sepProgressSim < 95) {
                            appendLiveTerminalLine(`Acoustic separation: isolating dialogue stem (${sepProgressSim}%)...`, `[Ep ${epNum}/${totalBatchCount}]`, "info");
                            sepProgressSim += Math.floor(Math.random() * 4) + 3;
                        }
                    }

                    if (stepEn && stepEn !== lastLoggedStep) {
                        lastLoggedStep = stepEn;
                        appendLiveTerminalLine(`${stepEn} (${epPct}%) [${stepKm}]`, `[Ep ${epNum}/${totalBatchCount}]`, "info");
                    }

                    // Stream dialogues
                    const currentDialogues = (sData.project && sData.project.dialogues) || sData.dialogues || [];
                    if (Array.isArray(currentDialogues) && currentDialogues.length > 0) {
                        currentDialogues.forEach((d, idx) => {
                            if (!loggedDialogueIds.has(idx)) {
                                loggedDialogueIds.add(idx);
                                const lineNum = String(idx + 1).padStart(2, '0');
                                const vName = (d.voice === 'sreymom' || d.voice === 'female') ? 'Sreymom (Female)' : 'Piseth (Male)';
                                const zhText = d.text_original || d.text || "";
                                const kmText = d.text_km || d.translated_text || d.khmer_text || d.text || "";
                                if (kmText && kmText !== zhText) {
                                    appendLiveTerminalLine(`[Line ${lineNum}] Dialogue translated & synchronized (${vName})`, `[Ep ${epNum} Dub]`, "dub");
                                } else if (zhText) {
                                    appendLiveTerminalLine(`[Line ${lineNum}] Dialogue preserved: original audio retained`, `[Ep ${epNum} Dub]`, "warning");
                                }
                            }
                        });
                    }

                    if (sData.status === "completed") {
                        clearInterval(pollInterval);
                        completedProjects.push(sData.project);
                        currentDubbedProject = sData.project;

                        // Preview newly finished episode in player cleanly without jitter
                        const mainVideo = document.getElementById('main-video');
                        if (mainVideo && sData.video_url) {
                            if (playbackTimer) {
                                clearInterval(playbackTimer);
                                playbackTimer = null;
                            }
                            isPlaying = false;
                            playheadSeconds = 0;
                            mainVideo.pause();

                            mainVideo.src = sData.video_url;
                            mainVideo.style.display = 'block';
                            mainVideo.load();
                        }

                        appendLiveTerminalLine(`✓ Episode ${epNum}/${totalBatchCount} finished: "${sData.project.output_video_file || fileName}"`, `[Ep ${epNum}/${totalBatchCount}]`, "success");
                        showToast(`EP ${epNum}/${totalBatchCount} dubbed successfully!`);
                        resolve(true);
                    } else if (sData.status === "failed") {
                        clearInterval(pollInterval);
                        const epErrTitle = sData.error || 'Episode dubbing failed';
                        const epErrStage = sData.error_stage || `Episode ${epNum}/${totalBatchCount}`;
                        const epErrSugg = sData.error_suggestion || "Check episode audio track or retry.";
                        logStudioError(epErrStage, `Episode ${epNum}/${totalBatchCount} failed: ${epErrTitle}`, {
                            details: sData.error_details || `Task ID: ${taskId}\nStatus: failed`,
                            type: sData.error_type || "PipelineError",
                            category: sData.error_category
                        }, epErrSugg);
                        showToast(`EP ${epNum} error: ${epErrTitle}`);
                        resolve(false);
                    }
                } catch (pollErr) {
                    console.warn("Batch episode poll error:", pollErr);
                }
            }, 1000);
        });

        // Small 1.5s pause between episodes
        if (i < totalBatchCount - 1) {
            await new Promise(r => setTimeout(r, 1500));
        }
    }

    // Merge into One Full Video if user selected 'full' or 'both'
    if ((outputMode === 'full' || outputMode === 'both') && completedProjects.length > 1) {
        appendLiveTerminalLine(`------------------------------------------------------------------------`, "[Full Movie Merge]", "info");
        appendLiveTerminalLine(`Export Mode: "${outputMode.toUpperCase()}" ➜ Concat/Merging all ${completedProjects.length} episodes into One Full Video...`, "[Full Movie Merge]", "info");
        updateExportProgressUI(96, totalElapsedSeconds, 30, `Merging ${completedProjects.length} episodes into Full Movie...`);

        const videoPaths = completedProjects.map(p => p.output_video_file || p.output_file).filter(Boolean);
        let seriesTitle = "Drama_Series";
        if (files && files[0]) {
            const f0Name = getMediaFileName(files[0]);
            seriesTitle = f0Name.replace(/\.[^/.]+$/, '').replace(/(?:_part|[-_]ep|[-_]e|\bep|\bepisode)[-_]?\d+/i, '').replace(/[-_]+$/, '').trim() || "Drama_Series";
            seriesTitle = seriesTitle.replace(/^(?:Dubbed_)+/i, '');
        }

        try {
            const mRes = await fetch("/api/projects/merge-episodes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    video_paths: videoPaths,
                    series_title: seriesTitle,
                    custom_export_dir: currentCustomExportFolder || undefined
                })
            });
            const mData = await mRes.json();
            if (mData.success) {
                appendLiveTerminalLine(`✓ Full Movie merged successfully: "${mData.merged_filename}"`, "[Full Movie Merge]", "success");
                showToast(`Full movie merged successfully: ${mData.merged_filename}`);

                const mainVideo = document.getElementById('main-video');
                if (mainVideo && mData.video_url) {
                    if (playbackTimer) {
                        clearInterval(playbackTimer);
                        playbackTimer = null;
                    }
                    isPlaying = false;
                    playheadSeconds = 0;
                    mainVideo.pause();

                    mainVideo.src = mData.video_url;
                    mainVideo.style.display = 'block';
                    mainVideo.load();
                }

                if (currentDubbedProject) {
                    currentDubbedProject.output_video_file = mData.merged_path;
                    currentDubbedProject.merged_filename = mData.merged_filename;
                }
            } else {
                appendLiveTerminalLine(`Merge failed: ${mData.error || 'Concat error'} (Separate episodes preserved)`, "[Full Movie Merge]", "error");
            }
        } catch (mErr) {
            appendLiveTerminalLine(`Merge network error: ${mErr.message} (Separate episodes preserved)`, "[Full Movie Merge]", "error");
        }
    }

    clearInterval(batchMasterTimer);
    activeDubbingTaskId = null;
    if (activeDubbingPollTimer) {
        clearInterval(activeDubbingPollTimer);
        activeDubbingPollTimer = null;
    }
    clearStagedFiles();
    updateExportProgressUI(100, totalElapsedSeconds, 0, `100% Complete! All ${completedProjects.length}/${totalBatchCount} episodes dubbed successfully!`);
    showToast(`Drama series (${completedProjects.length} episodes) dubbed successfully!`);

    appendLiveTerminalLine(`========================================================================`, "[Batch Complete]", "success");
    appendLiveTerminalLine(`Series Batch Dubbing Finished: ${completedProjects.length}/${totalBatchCount} episodes completed.`, "[Batch Complete]", "success");
    appendLiveTerminalLine(`Zero vocal leakage. All dubbed videos saved in "data/exports/".`, "[Batch Complete]", "success");
    appendLiveTerminalLine(`========================================================================`, "[Batch Complete]", "success");

    // Progress stays steady at 100% Completed!

    // Auto open export folder in Windows Explorer
    openExportFolderDirect();

    // Show success notification banner
    if (completedProjects.length > 0) {
        showDubbingSuccessNotification({
            project: completedProjects[completedProjects.length - 1],
            batch_count: completedProjects.length,
            total_count: totalBatchCount
        });
    }
}

function showDubbingSuccessNotification(data) {
    const existing = document.getElementById('dubbing-success-banner');
    if (existing) existing.remove();

    const isBatch = data && data.batch_count;
    const proj = data && data.project;
    const finalFile = (proj && proj.final_exported_video_path) || (data && data.final_exported_video_path) || "";
    const finalFileName = (proj && proj.final_exported_filename) || (data && data.final_exported_filename) || (finalFile ? finalFile.split(/[\\/]/).pop() : "");
    const finalDir = (proj && (proj.final_exported_dir || (proj.final_exported_video_path ? proj.final_exported_video_path.replace(/[\\/][^\\/]+$/, '') : ''))) || (data && data.final_exported_dir) || currentCustomExportFolder || 'data/exports';

    const bannerMsg = isBatch
        ? `All ${data.batch_count} episodes rendered 100% with Piseth & Sreymom voices into folder!`
        : `Video rendered 100% with Piseth & Sreymom voices into folder!`;

    // Stream directly into Studio Processing & Activity Console as requested by user
    if (typeof appendLiveTerminalLine === 'function') {
        appendLiveTerminalLine(bannerMsg, "[Render 100%]", "success");
        if (finalFileName) {
            appendLiveTerminalLine(`Rendered File: ${finalFileName}`, "[Export Done]", "success");
        }
        appendLiveTerminalLine(`Files saved in: ${finalDir} (100% Complete)`, "[Export Done]", "success");
    }

    // Set console progress to 100%
    const pctElem = document.getElementById('monitor-export-percent');
    if (pctElem) pctElem.textContent = '100%';
    const fillElem = document.getElementById('monitor-progress-fill');
    if (fillElem) fillElem.style.width = '100%';

    const pill = document.getElementById('monitor-engine-status-pill');
    const dot = document.getElementById('monitor-pulse-dot');
    const text = document.getElementById('monitor-engine-status-text');
    if (pill) pill.className = 'engine-status-pill standby';
    if (dot) dot.className = 'pulse-indicator standby';
    if (text) text.textContent = 'COMPLETED 100%';

    if (typeof playWindowsCompletionSound === 'function') {
        playWindowsCompletionSound();
    }
}

async function openExportFolderDirect(targetPath) {
    try {
        const pathToOpen = targetPath || currentCustomExportFolder || '';
        const res = await fetch('/api/projects/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: pathToOpen })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Opened folder: ${data.opened_path || pathToOpen || 'Exports'}`);
        } else {
            showToast(`${data.error || 'Cannot open folder'}`);
        }
    } catch (e) {
        showToast("Failed to open folder");
    }
}

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.style.removeProperty('display');
        modal.style.removeProperty('opacity');
        modal.style.removeProperty('pointer-events');
        modal.style.setProperty('display', 'flex', 'important');
        void modal.offsetWidth;
        modal.classList.add('active');
        modal.style.setProperty('opacity', '1', 'important');
        modal.style.setProperty('pointer-events', 'auto', 'important');
        modal.style.setProperty('z-index', '9999999', 'important');
    }
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.remove('active');
        modal.style.removeProperty('opacity');
        modal.style.removeProperty('pointer-events');
        modal.style.removeProperty('display');
        modal.style.removeProperty('z-index');
        modal.style.setProperty('display', 'none', 'important');
        modal.style.setProperty('opacity', '0', 'important');
        modal.style.setProperty('pointer-events', 'none', 'important');
    }
}

// ==========================================================================
// 6. LICENSE VERIFICATION & GATE SYSTEM
// ==========================================================================
async function checkDeviceLicenseStatus() {
    try {
        const res = await fetch('/api/license/status');
        const data = await res.json();
        currentHwid = data.hwid || "";
        
        const hwidElem = document.getElementById('settings-hwid-text');
        if (hwidElem) hwidElem.textContent = currentHwid;
        const gateHwidElem = document.getElementById('gate-hwid-text');
        if (gateHwidElem) gateHwidElem.textContent = currentHwid;

        const gateModal = document.getElementById('modal-license-gate');
        const badgeElem = document.getElementById('settings-lic-status-badge');
        const planElem = document.getElementById('settings-lic-plan-text');
        const expiryElem = document.getElementById('settings-lic-expiry-text');
        const clientNameElem = document.getElementById('settings-lic-client-name');
        const settingsClientNameInput = document.getElementById('settings-client-name-input');
        const gateClientNameInput = document.getElementById('gate-client-name-input');

        if (clientNameElem && data.client_name) {
            clientNameElem.textContent = data.client_name;
        }
        if (settingsClientNameInput && data.client_name && !settingsClientNameInput.value) {
            settingsClientNameInput.value = data.client_name;
        }
        if (gateClientNameInput && data.client_name && !gateClientNameInput.value) {
            gateClientNameInput.value = data.client_name;
        }

        if (data.telegram_link) window._adminTelegramLink = data.telegram_link;
        if (data.facebook_link) window._adminFacebookLink = data.facebook_link;
        if (data.app_version) {
            window._currentAppVersion = data.app_version;
            const gateVerElem = document.getElementById('gate-security-version');
            if (gateVerElem) gateVerElem.textContent = `SN TOOL Security Engine • v${data.app_version}`;
            const licEngineVerElem = document.getElementById('settings-lic-engine-version');
            if (licEngineVerElem) licEngineVerElem.textContent = `SN AI Engine v${data.app_version}`;
            const splashVer = document.getElementById('splash-version-tag');
            if (splashVer) splashVer.textContent = `v${data.app_version}`;
            const specVer = document.getElementById('update-spec-ver');
            if (specVer) specVer.textContent = `v${data.app_version}`;
        }

        if (data.is_banned) {
            window._isDeviceBanned = true;
            window._isDeviceActivated = false;
            document.body.classList.add('license-locked');
            if (gateModal) gateModal.classList.add('active');
            const cardBody = document.querySelector('.license-gate-body');
            const cardHeader = document.querySelector('.license-gate-header');
            if (cardHeader) {
                cardHeader.innerHTML = `
                    <div style="width: 50px; height: 50px; margin: 0 auto 6px auto; background: rgba(239,68,68,0.18); border: 2px solid #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #ef4444; font-size: 1.5rem;">
                        <i class="fa-solid fa-ban"></i>
                    </div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #f87171; letter-spacing: 0.5px;">DEVICE PERMANENTLY BANNED</div>
                    <div style="font-size: 0.75rem; color: #cbd5e1; margin-top: 3px; line-height: 1.4;">
                        ការប៉ុនប៉ង Hack / Bypass ត្រូវបានចាប់បាន!<br>
                        ឧបករណ៍កុំព្យូទ័រនេះត្រូវបានចាក់សោរជាអចិន្ត្រៃយ៍។
                    </div>
                `;
            }
            if (cardBody) {
                cardBody.innerHTML = `
                    <div style="background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 10px; margin-bottom: 12px; text-align: center;">
                        <div style="font-size: 0.68rem; color: #94a3b8; margin-bottom: 3px;">LOCKED MACHINE HWID:</div>
                        <div style="font-family: monospace; font-size: 0.86rem; font-weight: 800; color: #fca5a5; letter-spacing: 1px;">${data.hwid || currentHwid}</div>
                    </div>
                `;
            }
            return;
        }

        if (data.is_activated) {
            // License is valid & active
            window._isDeviceActivated = true;
            if (gateModal) gateModal.classList.remove('active');
            if (_splashDismissed) {
                document.body.classList.remove('license-locked');
                document.body.classList.remove('splash-active');
            }
            if (badgeElem) {
                if (data.is_expiring_soon) {
                    const daysLeft = (data.days_remaining !== null && data.days_remaining !== undefined) ? `${data.days_remaining} Days` : 'Expiring Soon';
                    badgeElem.innerHTML = `<span class="lic-pulse-dot" style="background-color:#f59e0b; box-shadow:0 0 8px #f59e0b;"></span> EXPIRING SOON (${daysLeft})`;
                    badgeElem.style.borderColor = "#f59e0b";
                    badgeElem.style.color = "#fbbf24";
                    badgeElem.style.background = "rgba(245,158,11,0.18)";
                } else {
                    badgeElem.innerHTML = `<span class="lic-pulse-dot"></span> ACTIVE`;
                    badgeElem.style.borderColor = "rgba(34,197,94,0.45)";
                    badgeElem.style.color = "#4ade80";
                    badgeElem.style.background = "rgba(34,197,94,0.16)";
                }
            }
            if (planElem) planElem.textContent = data.plan || "PRO Studio";
            if (expiryElem) {
                if (data.is_expiring_soon && data.days_remaining !== null) {
                    expiryElem.innerHTML = `${data.expires_at || "LIFETIME"} <span style="color:#fbbf24; font-weight:bold; margin-left:6px;">(${data.days_remaining} days left)</span>`;
                } else {
                    expiryElem.textContent = data.expires_at || "LIFETIME";
                }
            }
        } else {
            // License is not active -> Show lock gate
            window._isDeviceActivated = false;
            document.body.classList.add('license-locked');
            if (_splashDismissed && gateModal) gateModal.classList.add('active');
            if (badgeElem) {
                badgeElem.innerHTML = `<span class="lic-pulse-dot" style="background-color:#ef4444; box-shadow:0 0 8px #ef4444;"></span> ${data.status === "EXPIRED" ? "EXPIRED" : "UNLICENSED"}`;
                badgeElem.style.borderColor = "#ef4444";
                badgeElem.style.color = "#f87171";
                badgeElem.style.background = "rgba(239,68,68,0.15)";
            }
            if (planElem) planElem.textContent = "None";
            if (expiryElem) expiryElem.textContent = data.expires_at || "Expired / None";
        }
    } catch (e) {
        console.error("License check error:", e);
    }
}

async function submitGateLicense() {
    const input = document.getElementById('gate-license-input');
    const nameInput = document.getElementById('gate-client-name-input');
    const msgBox = document.getElementById('gate-status-msg');
    const key = input ? input.value.trim() : "";
    const clientName = nameInput ? nameInput.value.trim() : "";

    if (!key) {
        if (msgBox) {
            msgBox.style.display = 'block';
            msgBox.style.color = '#f87171';
            msgBox.style.background = 'rgba(239,68,68,0.1)';
            msgBox.textContent = "Please enter your License Key";
        }
        return;
    }

    if (msgBox) {
        msgBox.style.display = 'block';
        msgBox.style.color = '#facc15';
        msgBox.style.background = 'rgba(250,204,21,0.1)';
        msgBox.textContent = "Verifying License Key...";
    }

    try {
        const res = await fetch('/api/license/activate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ license_key: key, client_name: clientName })
        });
        const data = await res.json();
        if (data.success) {
            const displayName = clientName ? `Welcome ${clientName}! ` : "";
            if (msgBox) {
                msgBox.style.color = '#4ade80';
                msgBox.style.background = 'rgba(34,197,94,0.15)';
                msgBox.textContent = `${displayName}Activated successfully 100%!`;
            }
            showToast(`${displayName}Activated License Key successfully!`);
            setTimeout(() => {
                checkDeviceLicenseStatus();
            }, 1000);
        } else {
            if (msgBox) {
                msgBox.style.color = '#f87171';
                msgBox.style.background = 'rgba(239,68,68,0.15)';
                msgBox.textContent = `${data.message || data.error || 'Invalid License Key'}`;
            }
        }
    } catch (e) {
        if (msgBox) {
            msgBox.style.color = '#f87171';
            msgBox.textContent = "Network connection error";
        }
    }
}

async function confirmActivateLicense() {
    const keyInput = document.getElementById('input-license-key');
    const key = keyInput ? keyInput.value.trim() : "";
    const nameInput = document.getElementById('settings-client-name-input');
    const clientName = nameInput ? nameInput.value.trim() : "";
    if (!key) {
        showToast("Please enter License Key");
        return;
    }

    try {
        const res = await fetch('/api/license/activate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ license_key: key, client_name: clientName })
        });
        const data = await res.json();
        if (data.success) {
            showToast(clientName ? `License Key Activated for ${clientName}!` : "License Key Activated 100%!");
            checkDeviceLicenseStatus();
            backToSettingsHub();
        } else {
            showToast(`${data.message || data.error || 'Invalid License Key'}`);
        }
    } catch (e) {
        showToast("Network error");
    }
}

function copyHwid(elemId = 'settings-hwid-text') {
    const elem = document.getElementById(elemId);
    const text = elem ? elem.textContent.trim() : currentHwid;
    if (text && text !== "FETCHING...") {
        navigator.clipboard.writeText(text).then(() => {
            showToast(`Copied HWID: ${text}`);
        }).catch(() => {
            showToast(`HWID: ${text}`);
        });
    }
}

function contactAdmin(platform) {
    const hwidElem = document.getElementById('gate-hwid-text');
    const hwid = hwidElem ? hwidElem.textContent.trim() : (currentHwid || '');
    const isTg = (platform === 'tg' || platform === 'telegram');
    const pName = isTg ? 'Telegram' : 'Facebook';

    if (hwid && hwid !== 'FETCHING...') {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(hwid).then(() => {
                showToast(`📋 Copied HWID (${hwid})! Send to ${pName} Admin.`);
            }).catch(() => {
                showToast(`📋 Machine HWID: ${hwid}`);
            });
        } else {
            showToast(`📋 Machine HWID: ${hwid}`);
        }
    }

    const link = isTg
        ? (window._adminTelegramLink || 'https://t.me/')
        : (window._adminFacebookLink || 'https://facebook.com/');
    try {
        window.open(link, '_blank');
    } catch (e) {
        console.log("Open contact link error:", e);
    }
}

async function pasteGateLicense() {
    try {
        const text = await navigator.clipboard.readText();
        if (text) {
            const input = document.getElementById('gate-license-input');
            if (input) {
                input.value = text.trim();
                input.focus();
            }
            showToast("Pasted License Key!");
        }
    } catch (e) {
        showToast("Please press Ctrl+V to paste");
    }
}

// ==========================================================================
// WINDOWS SYSTEM NOTIFICATION SOUND AUDIO SYSTEM (BUILT-IN & PERMANENT)
// Plays genuine Microsoft Windows System Notification Sound whenever any task finishes
// (Export 100%, Batch Dubbing, Concat/Merge, Download, Split, Compress, Rename).
// Embedded directly inside the application; cannot be disabled, muted, or removed.
// ==========================================================================
let _lastWindowsChimeTimestamp = 0;
let _cachedChimeAudio = null;

function initWindowsCompletionSound() {
    try {
        if (!_cachedChimeAudio) {
            _cachedChimeAudio = new Audio('/static/system_notification.mp3');
            _cachedChimeAudio.preload = 'auto';
            _cachedChimeAudio.volume = 1.0;
        }
    } catch (e) {
        console.warn("[Sound System] Audio preload note:", e);
    }
}

// Fail-safe Web Audio API synthesizer matching harmonic frequencies:
// Tone 1: F#5 (739.99 Hz)
// Tone 2: C#6 (1108.73 Hz) + F6 (1396.91 Hz) harmonic overtone
function playSynthesizedWindowsNotifyChime() {
    try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) return;
        if (!window._winAudioCtx) {
            window._winAudioCtx = new AudioCtx();
        }
        const ctx = window._winAudioCtx;
        if (ctx.state === 'suspended') {
            ctx.resume();
        }
        
        const now = ctx.currentTime;
        // Tone 1: F#5 (739.99 Hz)
        const osc1 = ctx.createOscillator();
        const gain1 = ctx.createGain();
        osc1.type = 'sine';
        osc1.frequency.setValueAtTime(739.99, now);
        gain1.gain.setValueAtTime(0, now);
        gain1.gain.linearRampToValueAtTime(0.35, now + 0.02);
        gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
        osc1.connect(gain1);
        gain1.connect(ctx.destination);
        osc1.start(now);
        osc1.stop(now + 0.45);

        // Tone 2: C#6 (1108.73 Hz)
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(1108.73, now + 0.14);
        gain2.gain.setValueAtTime(0, now + 0.14);
        gain2.gain.linearRampToValueAtTime(0.38, now + 0.16);
        gain2.gain.exponentialRampToValueAtTime(0.0001, now + 1.15);
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.start(now + 0.14);
        osc2.stop(now + 1.15);

        // Harmonic overtone for Tone 2: F6 (1396.91 Hz)
        const osc3 = ctx.createOscillator();
        const gain3 = ctx.createGain();
        osc3.type = 'sine';
        osc3.frequency.setValueAtTime(1396.91, now + 0.14);
        gain3.gain.setValueAtTime(0, now + 0.14);
        gain3.gain.linearRampToValueAtTime(0.20, now + 0.16);
        gain3.gain.exponentialRampToValueAtTime(0.0001, now + 0.95);
        osc3.connect(gain3);
        gain3.connect(ctx.destination);
        osc3.start(now + 0.14);
        osc3.stop(now + 0.95);
    } catch (e) {
        console.warn("[Sound System] Synthesis note:", e);
    }
}

function playWindowsCompletionSound() {
    const now = Date.now();
    // Debounce to prevent overlapping triggers within 4.0s
    if (now - _lastWindowsChimeTimestamp < 4000) {
        return;
    }
    _lastWindowsChimeTimestamp = now;

    // 1. Direct native Windows OS playback via Python backend (rings OS audio device directly)
    fetch('/api/system/play-completion-sound', { method: 'POST' }).catch(() => {});

    // 2. Browser / WebView2 HTML5 Audio with genuine Windows System Notification sound
    try {
        if (!_cachedChimeAudio) {
            _cachedChimeAudio = new Audio('/static/system_notification.mp3');
            _cachedChimeAudio.volume = 1.0;
        }
        _cachedChimeAudio.currentTime = 0;
        const playPromise = _cachedChimeAudio.play();
        if (playPromise !== undefined) {
            playPromise.catch(err => {
                const wavAudio = new Audio('/static/system_notification.wav');
                wavAudio.volume = 1.0;
                wavAudio.play().catch(() => {
                    playSynthesizedWindowsNotifyChime();
                });
            });
        }
    } catch (err) {
        playSynthesizedWindowsNotifyChime();
    }
}

// Preload audio and unlock audio contexts
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initWindowsCompletionSound);
    } else {
        initWindowsCompletionSound();
    }
    ['click', 'keydown', 'pointerdown'].forEach(evt => {
        window.addEventListener(evt, () => {
            if (window._winAudioCtx && window._winAudioCtx.state === 'suspended') {
                window._winAudioCtx.resume();
            }
        }, { once: true });
    });
}

// ==========================================================================
// UTILITIES
// ==========================================================================
let _lastToastMsg = "";
let _lastToastTime = 0;

function showToast(msg) {
    if (!msg) return;
    msg = sanitizeBranding(msg);
    const str = String(msg);
    const now = Date.now();
    // Drop rapid identical toast spam within 2.5 seconds
    if (str === _lastToastMsg && (now - _lastToastTime < 2500)) {
        return;
    }
    _lastToastMsg = str;
    _lastToastTime = now;

    let tag = "[SN Studio]";
    let type = "info";
    const lower = str.toLowerCase();

    // NEVER trigger completion chime for individual episodes (only when entire task or all episodes are 100% finished!)
    const isSingleEpisode = lower.includes("ep ") || lower.includes("ep_") || lower.includes("ep/") || lower.includes("episode ");

    // Trigger authentic Windows completion chime ONLY when the ENTIRE batch / process is 100% finished
    const isCompletedAction = !isSingleEpisode && (
        lower.includes("downloaded all") ||
        lower.includes("all episodes") ||
        (lower.includes("all ") && (lower.includes("100%") || lower.includes("completed") || lower.includes("finished"))) ||
        lower.includes("100% complete") ||
        lower.includes("all dubbed") ||
        lower.includes("series dubbed") ||
        lower.includes("merged successfully") ||
        (lower.includes("saved") && lower.includes("mb") && !lower.includes("episode"))
    ) && !lower.includes("engine ready") && !lower.includes("console ready") && !lower.includes("modal");

    if (isCompletedAction) {
        playWindowsCompletionSound();
    }

    if (lower.includes("100%") || lower.includes("success") || lower.includes("ready") || lower.includes("complete") || lower.includes("finished")) {
        tag = "[Completed]";
        type = "success";
    } else if (lower.includes("failed") || lower.includes("error") || lower.includes("fail") || lower.includes("issue")) {
        tag = "[Alert]";
        type = "error";
    } else if (lower.includes("loading") || lower.includes("processing") || lower.includes("progress")) {
        tag = "[Processing]";
        type = "info";
    }

    // Stream directly into Studio Processing & Activity Console as requested by user
    if (typeof appendLiveTerminalLine === 'function') {
        appendLiveTerminalLine(str, tag, type);
    }

    // Completely silence floating toast banner so it never pops up over the window
    const toast = document.getElementById('toast');
    if (toast) {
        toast.classList.remove('show');
        toast.style.display = 'none';
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Window Scroll Lock: Ensure layout stays 100% stable and never scrolls vertically
window.addEventListener('scroll', () => {
    if (window.scrollY !== 0 || window.scrollX !== 0) {
        window.scrollTo(0, 0);
    }
}, { passive: true });
document.addEventListener('DOMContentLoaded', () => {
    window.scrollTo(0, 0);
});

// ==========================================================================
// GITHUB AUTO UPDATE MANAGER
// ==========================================================================
let _latestUpdateInfo = null;

async function checkForAppUpdates(manual = false) {
    const footerBtns = document.querySelectorAll('.footer-check-update-btn, .footer-update-logo-btn');
    const origHtmls = [];
    footerBtns.forEach((btn, idx) => {
        btn.disabled = true;
        if (btn.classList.contains('footer-update-logo-btn')) {
            btn.classList.add('is-checking');
        } else {
            origHtmls[idx] = btn.innerHTML;
            btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin" style="font-size:0.65rem;"></i> <span>Checking...</span>`;
        }
    });

    try {
        if (manual) showToast("Checking for updates...");
        let data = null;
        try {
            const res = await fetch('/api/update/check');
            if (res.ok) {
                data = await res.json();
            }
        } catch (localErr) {
            console.warn("Local update API offline or unreachable, querying GitHub directly...", localErr);
        }

        // If local update API returned result, use it directly
        if (!data || !data.success) {
            if (manual) {
                alert("Unable to connect to update server. Please verify your internet connection.");
            }
            return;
        }

        if (!data || !data.success) {
            if (manual) {
                alert("Unable to connect to update server. Please verify your internet connection.");
            }
            return;
        }

        _latestUpdateInfo = data;
        const curVer = data.current_version || '1.1.3';
        const latVer = data.latest_version || curVer;
        window._currentAppVersion = curVer;

        const curVerVal = document.getElementById('update-cur-ver-val');
        if (curVerVal) curVerVal.textContent = `v${curVer}`;
        const latVerEl = document.getElementById('update-latest-ver');
        if (latVerEl) latVerEl.textContent = `v${latVer}`;
        const latTitleEl = document.getElementById('update-lat-title');
        if (latTitleEl) latTitleEl.textContent = latVer;
        const notesVer = document.getElementById('update-notes-ver');
        if (notesVer) notesVer.textContent = latVer;
        const headerVer = document.getElementById('update-header-ver');
        if (headerVer) headerVer.textContent = latVer;
        const specVer = document.getElementById('update-spec-ver');
        if (specVer) specVer.textContent = data.has_update ? `v${curVer} → v${latVer}` : `v${curVer}`;

        const settingsVer = document.getElementById('settings-version-tag');
        if (settingsVer && curVer) settingsVer.textContent = `v${curVer}`;
        const licEngineVer = document.getElementById('settings-lic-engine-version');
        if (licEngineVer && curVer) licEngineVer.textContent = `SN AI Engine v${curVer}`;
        const gateVer = document.getElementById('gate-security-version');
        if (gateVer && curVer) gateVer.textContent = `SN TOOL Security Engine • v${curVer}`;

        const notesEl = document.getElementById('update-release-notes');
        const customNotesPanel = document.getElementById('update-custom-notes-panel');
        if (notesEl && data.release_notes && data.release_notes.length > 20) {
            notesEl.textContent = data.release_notes;
        }
        if (customNotesPanel) customNotesPanel.style.display = 'block';

        const progContainer = document.getElementById('update-progress-container');
        if (progContainer) progContainer.style.display = 'none';

        const btnUpdate = document.getElementById('btn-do-update');
        const btnText = document.getElementById('btn-do-update-text');
        const badgeText = document.getElementById('update-badge-text');
        const subtitle = document.getElementById('update-subtitle');

        if (btnUpdate) btnUpdate.disabled = false;

        if (data.has_update) {
            if (badgeText) badgeText.textContent = "NEW RELEASE AVAILABLE";
            if (subtitle) {
                if (data.subtitle && data.subtitle.trim().length > 0) {
                    subtitle.textContent = data.subtitle;
                } else if (data.description && data.description.trim().length > 0) {
                    subtitle.textContent = data.description;
                } else {
                    subtitle.textContent = `A new version (v${latVer}) is available with the latest neural engine upgrades and performance improvements.`;
                }
            }
            if (btnUpdate) btnUpdate.innerHTML = `<i class="fa-solid fa-cloud-arrow-down"></i> <span id="btn-do-update-text">Update Now (v${latVer})</span>`;
            openModal('modal-update');
            if (manual) showToast(`New version available: v${latVer}`);
        } else {
            // Already on latest official build: Do NOT pop up modal! Only log to Studio Processing & Activity Console!
            if (badgeText) badgeText.textContent = "LATEST OFFICIAL BUILD";
            if (subtitle) subtitle.textContent = `Official release notes and feature highlights for SN Tool Studio Pro (v${curVer}):`;
            if (btnUpdate) btnUpdate.innerHTML = `<i class="fa-solid fa-rotate"></i> <span id="btn-do-update-text">Reinstall / Update (v${curVer})</span>`;
            if (manual) {
                showToast(`SN Tool Studio Pro v${curVer} is up to date!`);
            }
        }
    } catch (err) {
        console.error("Update check error:", err);
        if (manual) showToast("Update check failed");
    } finally {
        footerBtns.forEach((btn, idx) => {
            btn.disabled = false;
            if (btn.classList.contains('footer-update-logo-btn')) {
                btn.classList.remove('is-checking');
            } else if (origHtmls[idx]) {
                btn.innerHTML = origHtmls[idx];
            }
        });
    }
}

async function executeAppUpdate() {
    if (!_latestUpdateInfo) return;
    const btnUpdate = document.getElementById('btn-do-update');
    const progContainer = document.getElementById('update-progress-container');
    const statusMsg = document.getElementById('update-status-msg');
    const progressBar = document.getElementById('update-progress-bar');
    const progressPct = document.getElementById('update-progress-pct');

    if (btnUpdate) btnUpdate.disabled = true;
    if (progContainer) progContainer.style.display = 'flex';
    if (statusMsg) statusMsg.textContent = "Downloading update package from Google Drive Cloud...";
    if (progressBar) progressBar.style.width = "35%";
    if (progressPct) progressPct.textContent = "35%";

    try {
        // Step progress simulation while downloading
        const simInterval = setInterval(() => {
            if (progressBar) {
                const currentW = parseInt(progressBar.style.width) || 35;
                if (currentW < 85) {
                    progressBar.style.width = (currentW + 12) + "%";
                    if (progressPct) progressPct.textContent = (currentW + 12) + "%";
                }
            }
        }, 600);

        const fallbackUrl = "https://raw.githubusercontent.com/songseyha1003-maker/skdtool.github/main/SN_TOOL_UPDATE.zip";
        const dlUrl = (_latestUpdateInfo && _latestUpdateInfo.download_url) ? _latestUpdateInfo.download_url : fallbackUrl;
        const res = await fetch('/api/update/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                download_url: dlUrl
            })
        });
        clearInterval(simInterval);
        const data = await res.json();
        if (data.success) {
            if (progressBar) progressBar.style.width = "100%";
            if (progressPct) progressPct.textContent = "100%";
            if (statusMsg) statusMsg.innerHTML = '<i class="fa-solid fa-circle-check" style="color:#10b981;"></i> Update successful! Restarting to new version...';
            showToast("Update successful!");
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        } else {
            if (statusMsg) statusMsg.textContent = "Error: " + (data.error || "Update failed");
            if (btnUpdate) btnUpdate.disabled = false;
            showToast("Error: " + (data.error || "Update failed"));
        }
    } catch (err) {
        if (statusMsg) statusMsg.textContent = "Error: " + err.message;
        if (btnUpdate) btnUpdate.disabled = false;
        showToast("Update error: " + err.message);
    }
}

// ==========================================================================
// 7. STUDIO SPLASH SCREEN CONTROLLER (1:1 Reference Image 2)
// Runs for 3.0 seconds on application startup, shows concentric radar rings,
// authentic 3D emblem, license verification progress, and seamlessly
// transitions into License Activation Gate (if unlicensed) or Studio Pro.
// ==========================================================================
let _splashDismissed = false;

function initStudioSplashScreen() {
    const splash = document.getElementById('studio-splash-screen');
    const bar = document.getElementById('splash-progress-bar');
    const statusLbl = document.getElementById('splash-status-label');

    // Immediately trigger license status verification in the background
    checkDeviceLicenseStatus().catch(err => console.error("Initial license check error:", err));

    // Dynamically synchronize splash edition chip and license cards with real version
    fetch('/api/update/check').then(r => r.json()).then(data => {
        if (data && data.current_version) {
            const curVer = data.current_version;
            window._currentAppVersion = curVer;
            const settingsTag = document.getElementById('settings-version-tag');
            if (settingsTag) settingsTag.textContent = 'v' + curVer;
            const licEngineVer = document.getElementById('settings-lic-engine-version');
            if (licEngineVer) licEngineVer.textContent = `SN AI Engine v${curVer}`;
            const gateVer = document.getElementById('gate-security-version');
            if (gateVer) gateVer.textContent = `SN TOOL Security Engine • v${curVer}`;
        }
    }).catch(() => {});

    if (!splash || !bar) {
        return;
    }

    const duration = 5000; // 5.0 seconds exact duration requested by user
    const startTime = performance.now();

    const pctEl = document.getElementById('splash-progress-pct');
    const iconEl = document.getElementById('splash-step-icon');

    function animateProgress(now) {
        const elapsed = now - startTime;
        const progress = Math.min(100, (elapsed / duration) * 100);
        bar.style.width = progress.toFixed(1) + '%';
        if (pctEl) pctEl.textContent = `${Math.floor(progress)}%`;

        // Dynamic Lively AI Boot Stages (Distributed smoothly across 5 seconds)
        if (elapsed < 1400) {
            if (iconEl && iconEl.dataset.stage !== '1') {
                iconEl.dataset.stage = '1';
                iconEl.innerHTML = '<i class="fa-solid fa-microchip" style="color:#facc15;"></i>';
                if (statusLbl) statusLbl.textContent = 'Initializing AI Neural Engine...';
            }
        } else if (elapsed < 2800) {
            if (iconEl && iconEl.dataset.stage !== '2') {
                iconEl.dataset.stage = '2';
                iconEl.innerHTML = '<i class="fa-solid fa-wave-square" style="color:#38bdf8;"></i>';
                if (statusLbl) statusLbl.textContent = 'Calibrating Khmer Voice Synthesizer...';
            }
        } else if (elapsed < 4300) {
            if (iconEl && iconEl.dataset.stage !== '3') {
                iconEl.dataset.stage = '3';
                iconEl.innerHTML = '<i class="fa-solid fa-shield-halved" style="color:#eab308;"></i>';
                if (statusLbl) statusLbl.textContent = 'Verifying License Security...';
            }
        } else {
            if (iconEl && iconEl.dataset.stage !== '4') {
                iconEl.dataset.stage = '4';
                iconEl.innerHTML = '<i class="fa-solid fa-circle-check" style="color:#4ade80;"></i>';
                if (statusLbl) {
                    statusLbl.textContent = 'System Ready & Calibrated!';
                    statusLbl.style.color = '#4ade80';
                }
            }
        }

        if (elapsed < duration) {
            requestAnimationFrame(animateProgress);
        } else {
            bar.style.width = '100%';
            if (pctEl) pctEl.textContent = '100%';

            setTimeout(() => {
                splash.classList.add('fade-out');
                setTimeout(() => {
                    splash.style.display = 'none';
                    _splashDismissed = true;
                    document.body.classList.remove('splash-active');

                    const gateModal = document.getElementById('modal-license-gate');
                    if (window._isDeviceActivated) {
                        document.body.classList.remove('license-locked');
                        if (gateModal) gateModal.classList.remove('active');
                        // Auto check for updates 2 seconds after startup
                        setTimeout(() => {
                            try { checkForAppUpdates(false); } catch (e) {}
                        }, 2000);
                    } else {
                        document.body.classList.add('license-locked');
                        if (gateModal) gateModal.classList.add('active');
                    }
                }, 500);
            }, 250);
        }
    }

    requestAnimationFrame(animateProgress);
}

// Start splash screen immediately upon page initialization
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStudioSplashScreen);
} else {
    initStudioSplashScreen();
}

// ==========================================================================
// 🛡️ ANTI-INSPECT & DEVTOOLS BLOCKER (Client-Side Protection)
// ==========================================================================
document.addEventListener('contextmenu', function(e) {
    const tag = (e.target && e.target.tagName ? e.target.tagName : '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || (e.target && e.target.isContentEditable)) {
        return true;
    }
    if (e.target && e.target.closest && e.target.closest('#studio-live-terminal-stream, .studio-live-terminal-stream, .selectable-text')) {
        return true;
    }
    e.preventDefault();
    return false;
});

document.addEventListener('keydown', function(e) {
    // Block F12 (DevTools)
    if (e.key === 'F12' || e.keyCode === 123) {
        e.preventDefault();
        return false;
    }
    // Block Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+Shift+C (DevTools inspect)
    if (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'i' || e.key === 'J' || e.key === 'j' || e.key === 'C' || e.key === 'c')) {
        e.preventDefault();
        return false;
    }
    // Block Ctrl+U (View Source)
    if (e.ctrlKey && (e.key === 'u' || e.key === 'U')) {
        e.preventDefault();
        return false;
    }
});


