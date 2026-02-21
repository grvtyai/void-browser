import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
os.environ["QT_OPENGL"] = "software"
import sys
import json
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QRect, QSize, Slot, QObject, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QIcon, QCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QLineEdit, QFileDialog,
    QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QStatusBar, QSizePolicy, QStyle, QStackedWidget, QScrollArea, QSplitter,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
    QWebEngineDownloadRequest, QWebEngineUrlRequestInterceptor,
    QWebEngineScript,
)
from PySide6.QtWebChannel import QWebChannel

EDGE_MARGIN = 8
SIDEBAR_COLLAPSED_WIDTH = 48
SETTINGS_FILE = Path(__file__).parent / "settings.json"

DEFAULT_SETTINGS = {
    "sidebar_width": 220,
    "engine": "https://google.com/search?q=",
    "homepage": "void",
    "homepage_url": "",
    "tracker": True,
    "dnt": False,
    "auto_collapse": True,
}

def load_settings():
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
    except Exception:
        pass
    return DEFAULT_SETTINGS.copy()

def save_settings(data):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# ---- Tracker Blocker ----
class SimpleTrackerBlocker(QWebEngineUrlRequestInterceptor):
    BLOCKED_DOMAINS = [
        "doubleclick.net", "google-analytics.com",
        "googletagmanager.com", "facebook.net", "adsystem.com"
    ]
    def __init__(self):
        super().__init__()
        self.enabled = True

    def interceptRequest(self, info):
        if not self.enabled:
            return
        url = info.requestUrl().toString()
        for domain in self.BLOCKED_DOMAINS:
            if domain in url:
                info.block(True)
                return

# ---- QWebChannel Bridge ----
class BrowserBridge(QObject):
    sidebarWidthChanged = Signal(int)

    def __init__(self, browser):
        super().__init__()
        self.browser = browser

    @Slot(int)
    def setSidebarWidth(self, width):
        width = max(160, min(400, width))
        self.browser.settings_data["sidebar_width"] = width
        save_settings(self.browser.settings_data)
        self.browser.apply_sidebar_width(width)

    @Slot(str)
    def setEngine(self, engine):
        self.browser.settings_data["engine"] = engine
        save_settings(self.browser.settings_data)

    @Slot(bool)
    def setTracker(self, enabled):
        self.browser.settings_data["tracker"] = enabled
        self.browser.tracker.enabled = enabled
        save_settings(self.browser.settings_data)

    @Slot(bool)
    def setDnt(self, enabled):
        self.browser.settings_data["dnt"] = enabled
        save_settings(self.browser.settings_data)

    @Slot(str, str)
    def setHomepage(self, mode, url):
        self.browser.settings_data["homepage"] = mode
        self.browser.settings_data["homepage_url"] = url
        save_settings(self.browser.settings_data)

    @Slot(bool)
    def setAutoCollapse(self, enabled):
        self.browser.settings_data["auto_collapse"] = enabled
        save_settings(self.browser.settings_data)
        self.browser.apply_auto_collapse(enabled)

    @Slot(str, result=str)
    def resolveLocalPath(self, relative_path):
        """Löst einen relativen Pfad von void.py aus auf einen absoluten file:// URL."""
        base = Path(__file__).parent
        resolved = (base / relative_path).resolve()
        return resolved.as_uri()  # gibt file:///absoluter/pfad zurück

    @Slot(result=str)
    def getSettings(self):
        return json.dumps(self.browser.settings_data)

# ---- Custom Page ----
class BrowserPage(QWebEnginePage):
    def __init__(self, profile, browser, parent=None):
        super().__init__(profile, parent)
        self.browser = browser
        self.linkHovered.connect(self._on_link_hovered)

    def _on_link_hovered(self, url):
        if url:
            self.browser.statusbar.showMessage(url)
        else:
            self.browser.statusbar.clearMessage()

    def createWindow(self, win_type):
        tab = self.browser.add_tab()
        return tab.page()

# ---- Browser Tab ----
class BrowserTab(QWebEngineView):
    def __init__(self, profile, browser, parent=None):
        super().__init__(parent)
        page = BrowserPage(profile, browser, self)
        self.setPage(page)
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)
        try:
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        except AttributeError:
            pass

# ---- Tab Entry Widget ----
class TabEntry(QWidget):
    def __init__(self, label, on_click, on_close, parent=None):
        super().__init__(parent)
        self.on_click = on_click
        self.setFixedHeight(36)
        self.setCursor(Qt.PointingHandCursor)
        self._active = False
        self.setObjectName("tabEntry")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 0, 6, 0)
        self._layout.setSpacing(8)

        # Favicon box – feste 28x28 Box mit Border
        self.favicon_box = QWidget()
        self.favicon_box.setFixedSize(28, 28)
        self.favicon_box.setStyleSheet("""
            background-color: #12101e;
            border: 1px solid #2a1f3d;
            border-radius: 6px;
        """)
        fav_layout = QHBoxLayout(self.favicon_box)
        fav_layout.setContentsMargins(4, 4, 4, 4)

        self.favicon = QLabel()
        self.favicon.setFixedSize(16, 16)
        self.favicon.setScaledContents(True)
        self._set_default_icon()
        fav_layout.addWidget(self.favicon)

        self._layout.addWidget(self.favicon_box)

        self.label = QLabel(label)
        self._layout.addWidget(self.label)
        self._layout.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.clicked.connect(on_close)
        self._layout.addWidget(self.close_btn)

        self._update_style()

    def _set_default_icon(self):
        # Unauffälliges Welt-Icon als Fallback
        pixmap = QApplication.style().standardIcon(QStyle.SP_DriveNetIcon).pixmap(16, 16)
        self.favicon.setPixmap(pixmap)

    def set_favicon(self, icon: QIcon):
        if icon and not icon.isNull():
            self.favicon.setPixmap(icon.pixmap(QSize(16, 16)))
        else:
            self._set_default_icon()

    def set_active(self, active):
        self._active = active
        self._update_style()

    def set_label(self, text):
        self.label.setText(text[:28])

    def _update_style(self):
        if self._active:
            self.setStyleSheet("""
                background-color: #2a1f3d;
                color: #e8d0f8;
            """)
        else:
            self.setStyleSheet("""
                background-color: #0a0a14;
                color: #6a5080;
            """)

    def set_collapsed(self, collapsed):
        if collapsed:
            self.label.hide()
            self.close_btn.hide()
            # Gleichmäßiger Abstand links und rechts um die favicon_box
            self._layout.setContentsMargins(10, 0, 10, 0)
            self._layout.setSpacing(0)
        else:
            self._layout.setContentsMargins(8, 0, 6, 0)
            self._layout.setSpacing(8)
            self.label.show()
            self.close_btn.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_click()

# ---- Main Browser ----
class Browser(QMainWindow):
    def __init__(self, title="Void"):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(1400, 860)
        self.setMinimumSize(600, 400)

        self.settings_data = load_settings()

        icon_path = Path(__file__).parent / "assets" / "void_logo.jpg"
        self.setWindowIcon(QIcon(str(icon_path)))

        self.startpage_path = Path(__file__).parent / "startpage" / "index.html"
        self.home_url = QUrl.fromLocalFile(str(self.startpage_path))

        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #080810; color: #c8a8e8;")

        self._resizing = False
        self._resize_edge = None
        self._resize_start_pos = None
        self._resize_start_geom = None
        self.setMouseTracking(True)

        self._tabs = []
        self._entries = []
        self._current = -1

        # Tracker
        self.tracker = SimpleTrackerBlocker()
        self.tracker.enabled = self.settings_data.get("tracker", True)

        # Profile
        self.profile = QWebEngineProfile("void", self)
        self.profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.profile.setUrlRequestInterceptor(self.tracker)
        self.profile.downloadRequested.connect(self.handle_download)

        # WebChannel
        self.channel = QWebChannel()
        self.bridge = BrowserBridge(self)
        self.channel.registerObject("bridge", self.bridge)
        self._inject_webchannel_js()

        # ===== LAYOUT: Sidebar floating über Stack =====
        self._container = QWidget()
        self._container.setStyleSheet("background: #080810;")
        container_layout = QHBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Sidebar
        sidebar_width = self.settings_data.get("sidebar_width", 220)
        self._sidebar = QWidget(self._container)
        self._sidebar.setFixedWidth(sidebar_width)
        self._sidebar.setStyleSheet("""
            background-color: #0a0a14;
            border-right: 1px solid #2a1f3d;
        """)
        self._sidebar.raise_()
        sidebar_layout = QVBoxLayout(self._sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        self._new_tab_btn = QPushButton("＋  Neuer Tab")
        new_tab_btn = self._new_tab_btn
        new_tab_btn.setFixedHeight(36)
        new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a0a14; color: #5a3a7a; border: none;
                border-bottom: 1px solid #1a1020; font-size: 12px;
                text-align: left; padding-left: 14px;
            }
            QPushButton:hover { background-color: #12101e; color: #c8a8e8; }
        """)
        new_tab_btn.clicked.connect(lambda: self.add_tab())
        sidebar_layout.addWidget(new_tab_btn)

        self._tab_list_widget = QWidget()
        self._tab_list_layout = QVBoxLayout(self._tab_list_widget)
        self._tab_list_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_list_layout.setSpacing(1)
        self._tab_list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self._tab_list_widget)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: #0a0a14; }")
        sidebar_layout.addWidget(scroll)

        self._stack = QStackedWidget()
        container_layout.addWidget(self._sidebar)
        container_layout.addWidget(self._stack)

        # ===== TOOLBAR =====
        self.toolbar_widget = QWidget()
        self.toolbar_widget.setStyleSheet("background-color: #0d0d1a;")
        tlayout = QHBoxLayout(self.toolbar_widget)
        tlayout.setContentsMargins(8, 4, 8, 4)
        tlayout.setSpacing(4)

        def std_icon(p): return self.style().standardIcon(p)
        def nav_button(p, action, tip=""):
            btn = QPushButton()
            btn.setIcon(std_icon(p))
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.setStyleSheet("QPushButton{background:none;border:none;border-radius:4px;color:#c8a8e8;}QPushButton:hover{background:#2a1f3d;}")
            btn.clicked.connect(action)
            return btn

        tlayout.addWidget(nav_button(QStyle.SP_ArrowBack,     lambda: self.current_tab().back(),    "Zurück"))
        tlayout.addWidget(nav_button(QStyle.SP_ArrowForward,  lambda: self.current_tab().forward(), "Vorwärts"))
        tlayout.addWidget(nav_button(QStyle.SP_BrowserReload, lambda: self.current_tab().reload(),  "Neu laden"))

        self.urlbar = QLineEdit()
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        self.urlbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.urlbar.setStyleSheet("""
            QLineEdit { background:#12101e; color:#e8d0f8; border:1px solid #2a1f3d;
                        border-radius:4px; padding:4px 10px; font-size:13px; }
            QLineEdit:focus { border:1px solid #7a4aaa; }
        """)
        tlayout.addWidget(self.urlbar)

        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 9))
        title_label.setStyleSheet("color:#3d2a5a; padding:0 6px;")
        tlayout.addWidget(title_label)

        def win_btn(text, cb, hover=None):
            btn = QPushButton(text)
            btn.setFixedSize(30, 24)
            btn.setStyleSheet(f"QPushButton{{background:#0d0d1a;color:#c8a8e8;border:none;font-size:13px;}}QPushButton:hover{{background:{hover or '#2a1f3d'};color:#e8d0f8;}}")
            btn.clicked.connect(cb)
            return btn

        tlayout.addWidget(win_btn("—", self.showMinimized))
        tlayout.addWidget(win_btn("▢", self.toggle_maximize))
        tlayout.addWidget(win_btn("✕", self.close, "#b00020"))

        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.addWidget(self.toolbar_widget)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        self.toolbar_widget.mousePressEvent = self._titlebar_mouse_press
        self.toolbar_widget.mouseMoveEvent  = self._titlebar_mouse_move
        self._drag_pos = None

        # Statusbar
        self.statusbar = QStatusBar()
        self.statusbar.setStyleSheet("QStatusBar{background:#0a0a14;color:#6a5080;font-size:11px;border-top:1px solid #2a1f3d;}")
        self.statusbar.setSizeGripEnabled(False)
        self.setStatusBar(self.statusbar)

        self.setCentralWidget(self._container)

        # Apply auto-collapse setting
        self._auto_collapse = False
        self._sidebar_expanded = True
        if self.settings_data.get("auto_collapse", True):
            self.apply_auto_collapse(True)

        self.add_tab(self.home_url, "Start")

    # ---- WebChannel injection ----
    def _inject_webchannel_js(self):
        """Inject qwebchannel.js into every page via profile script."""
        qwc_path = Path(__file__).parent / "startpage" / "qwebchannel.js"
        # Qt ships qwebchannel.js – copy it out if not present
        if not qwc_path.exists():
            from PySide6.QtWebEngineCore import QWebEngineScript
            # Use the built-in resource
            src = ":/qtwebchannel/qwebchannel.js"
            # We'll inject via page instead (see _setup_page_channel)
        # We set the channel per-page in _setup_page_channel

    def _setup_page_channel(self, page):
        """Attach QWebChannel to a specific page."""
        page.setWebChannel(self.channel)

    # ---- Apply settings ----
    def apply_sidebar_width(self, width):
        if not self._auto_collapse or self._sidebar_expanded:
            self._sidebar.setFixedWidth(width)

    def apply_auto_collapse(self, enabled):
        self._auto_collapse = enabled
        if enabled:
            self._sidebar.enterEvent  = self._sidebar_enter
            self._sidebar.leaveEvent  = self._sidebar_leave
            self._collapse_sidebar()
        else:
            # Remove event hooks and expand
            self._sidebar.enterEvent = lambda e: None
            self._sidebar.leaveEvent = lambda e: None
            self._expand_sidebar()

    def _animate_sidebar(self, target_width):
        self._anim = QPropertyAnimation(self._sidebar, b"minimumWidth")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.setStartValue(self._sidebar.width())
        self._anim.setEndValue(target_width)
        # Also animate maximumWidth so setFixedWidth doesn't block
        self._anim2 = QPropertyAnimation(self._sidebar, b"maximumWidth")
        self._anim2.setDuration(220)
        self._anim2.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim2.setStartValue(self._sidebar.width())
        self._anim2.setEndValue(target_width)
        self._anim.start()
        self._anim2.start()

    def _collapse_sidebar(self):
        self._sidebar_expanded = False
        for entry in self._entries:
            entry.set_collapsed(True)
        self._new_tab_btn.setText("＋")
        self._new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a0a14; color: #5a3a7a; border: none;
                border-bottom: 1px solid #1a1020; font-size: 16px;
                text-align: center; padding: 0;
            }
            QPushButton:hover { background-color: #12101e; color: #c8a8e8; }
        """)
        self._animate_sidebar(SIDEBAR_COLLAPSED_WIDTH)

    def _expand_sidebar(self):
        self._sidebar_expanded = True
        w = self.settings_data.get("sidebar_width", 220)
        self._animate_sidebar(w)
        # Delay showing labels until animation is mostly done
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, self._show_expanded_content)

    def _show_expanded_content(self):
        for entry in self._entries:
            entry.set_collapsed(False)
        self._new_tab_btn.setText("＋  Neuer Tab")
        self._new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a0a14; color: #5a3a7a; border: none;
                border-bottom: 1px solid #1a1020; font-size: 12px;
                text-align: left; padding-left: 14px;
            }
            QPushButton:hover { background-color: #12101e; color: #c8a8e8; }
        """)

    def _sidebar_enter(self, event):
        self._expand_sidebar()

    def _sidebar_leave(self, event):
        self._collapse_sidebar()

    # ---- Tab Management ----
    def add_tab(self, url=None, label="Neuer Tab"):
        url = url or QUrl(self.home_url)
        tab = BrowserTab(self.profile, self)
        self._setup_page_channel(tab.page())
        tab.setUrl(url)

        idx = len(self._tabs)
        self._tabs.append(tab)
        self._stack.addWidget(tab)

        entry = TabEntry(
            label,
            on_click=lambda i=idx: self.switch_tab(i),
            on_close=lambda i=idx: self.close_tab(i),
        )
        self._entries.append(entry)
        insert_pos = self._tab_list_layout.count() - 1
        self._tab_list_layout.insertWidget(insert_pos, entry)

        tab.iconChanged.connect(lambda icon, i=idx: self._on_icon_changed(i, icon))
        tab.titleChanged.connect(lambda t, i=idx: self._on_title_changed(i, t))
        tab.urlChanged.connect(lambda q, i=idx: self._on_url_changed(i, q))

        self.switch_tab(idx)
        return tab

    def switch_tab(self, index):
        if index < 0 or index >= len(self._tabs): return
        if 0 <= self._current < len(self._entries):
            self._entries[self._current].set_active(False)
        self._current = index
        self._entries[index].set_active(True)
        self._stack.setCurrentWidget(self._tabs[index])
        self.urlbar.setText(self._tabs[index].url().toString())

    def close_tab(self, index):
        if len(self._tabs) <= 1: return
        tab   = self._tabs.pop(index)
        entry = self._entries.pop(index)
        self._stack.removeWidget(tab)
        tab.setPage(QWebEnginePage())
        tab.deleteLater()
        entry.setParent(None)
        entry.deleteLater()
        self._rewire_entries()
        self._current = -1
        self.switch_tab(min(index, len(self._tabs) - 1))

    def _rewire_entries(self):
        for i, entry in enumerate(self._entries):
            entry.on_click = lambda idx=i: self.switch_tab(idx)
            close_btn = entry.findChildren(QPushButton)[0]
            try: close_btn.clicked.disconnect()
            except RuntimeError: pass
            close_btn.clicked.connect(lambda _, idx=i: self.close_tab(idx))

    def current_tab(self):
        if 0 <= self._current < len(self._tabs):
            return self._tabs[self._current]
        return None

    def _on_icon_changed(self, index, icon):
        if index < len(self._entries):
            self._entries[index].set_favicon(icon)

    def _on_title_changed(self, index, title):
        if index < len(self._entries):
            self._entries[index].set_label(title or "Neuer Tab")

    def _on_url_changed(self, index, qurl):
        if index == self._current:
            self.urlbar.setText(qurl.toString())

    def navigate_to_url(self):
        url = self.urlbar.text().strip()
        if not url:
            return
        if url.startswith("file://"):
            qurl = QUrl(url)
        elif url.startswith("/") or url.startswith("../") or url.startswith("./"):
            # Relativer lokaler Pfad → absolut auflösen
            resolved = (Path(__file__).parent / url).resolve()
            qurl = QUrl.fromLocalFile(str(resolved))
        elif not url.startswith("http"):
            qurl = QUrl("https://" + url)
        else:
            qurl = QUrl(url)
        tab = self.current_tab()
        if tab:
            tab.setUrl(qurl)

    # ---- Resize ----
    def _get_resize_edge(self, pos):
        x, y, w, h, m = pos.x(), pos.y(), self.width(), self.height(), EDGE_MARGIN
        on_l, on_r = x <= m, x >= w - m
        on_t, on_b = y <= m, y >= h - m
        if on_t and on_l: return "top-left"
        if on_t and on_r: return "top-right"
        if on_b and on_l: return "bottom-left"
        if on_b and on_r: return "bottom-right"
        if on_l: return "left"
        if on_r: return "right"
        if on_t: return "top"
        if on_b: return "bottom"
        return None

    def _edge_to_cursor(self, edge):
        return {"left":Qt.SizeHorCursor,"right":Qt.SizeHorCursor,
                "top":Qt.SizeVerCursor,"bottom":Qt.SizeVerCursor,
                "top-left":Qt.SizeFDiagCursor,"bottom-right":Qt.SizeFDiagCursor,
                "top-right":Qt.SizeBDiagCursor,"bottom-left":Qt.SizeBDiagCursor,
                }.get(edge, Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self._get_resize_edge(event.position().toPoint())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_start_geom = self.geometry()
                event.accept(); return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            self._do_resize(event.globalPosition().toPoint())
            event.accept(); return
        edge = self._get_resize_edge(event.position().toPoint())
        self.setCursor(QCursor(self._edge_to_cursor(edge) if edge else Qt.ArrowCursor))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._resize_edge = None
            self.setCursor(QCursor(Qt.ArrowCursor))
            event.accept(); return
        super().mouseReleaseEvent(event)

    def _do_resize(self, gp):
        d = gp - self._resize_start_pos
        g = QRect(self._resize_start_geom)
        e, mw, mh = self._resize_edge, self.minimumWidth(), self.minimumHeight()
        if "right"  in e: g.setRight(max(g.left()+mw, g.right()+d.x()))
        if "bottom" in e: g.setBottom(max(g.top()+mh, g.bottom()+d.y()))
        if "left"   in e: g.setLeft(min(g.right()-mw, g.left()+d.x()))
        if "top"    in e: g.setTop(min(g.bottom()-mh, g.top()+d.y()))
        self.setGeometry(g)

    def _titlebar_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def _titlebar_mouse_move(self, event):
        if self._drag_pos and not self._resizing:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()

    def toggle_maximize(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    @Slot(QWebEngineDownloadRequest)
    def handle_download(self, download):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", download.suggestedFileName())
        if path:
            download.setDownloadFileName(path)
            download.accept()

    def closeEvent(self, event):
        for tab in self._tabs:
            tab.setPage(QWebEnginePage())
            tab.deleteLater()
        self._tabs.clear()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QScrollBar:vertical { background:#0a0a14; width:6px; }
        QScrollBar::handle:vertical { background:#3d2a5a; border-radius:3px; }
        QScrollBar::handle:vertical:hover { background:#7a4aaa; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0px; }
        QTabBar::tab { background:#0d0d1a; color:#6a5080; padding:6px; }
        QTabBar::tab:selected { background:#12101e; color:#c8a8e8; }
    """)
    browser = Browser("Void Browser")
    browser.show()
    sys.exit(app.exec())
