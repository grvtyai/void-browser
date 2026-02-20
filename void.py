import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
os.environ["QT_OPENGL"] = "software"
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QToolBar,
    QLineEdit,
    QTabWidget,
    QFileDialog,
    QPushButton,
    QWidget,
    QHBoxLayout,
    QLabel,
    QStyle,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineSettings,
    QWebEngineDownloadRequest,
    QWebEngineUrlRequestInterceptor
)

# ---- Tracker Blocker ----
class SimpleTrackerBlocker(QWebEngineUrlRequestInterceptor):
    BLOCKED_DOMAINS = [
        "doubleclick.net",
        "google-analytics.com",
        "googletagmanager.com",
        "facebook.net",
        "adsystem.com"
    ]

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        for domain in self.BLOCKED_DOMAINS:
            if domain in url:
                info.block(True)
                return

# ---- Browser Tab ----
class BrowserTab(QWebEngineView):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setPage(QWebEnginePage(profile, self))
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, False)

# ---- Main Browser ----
class Browser(QMainWindow):
    def __init__(self, title="Void"):
        super().__init__()

        self.setWindowTitle(title)
        self.resize(1200, 800)

        # Start Page
        startpage_path = Path(__file__).parent.parent / "void-hub" / "index.html"
        self.home_url = QUrl.fromLocalFile(str(startpage_path))


        # Frameless Window
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")

        # Profile
        self.profile = QWebEngineProfile("default", self)
        self.profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        self.profile.setUrlRequestInterceptor(SimpleTrackerBlocker())
        self.profile.downloadRequested.connect(self.handle_download)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_urlbar)
        self.setCentralWidget(self.tabs)

        # ===== CUSTOM TITLEBAR =====
        self.toolbar_widget = QWidget()
        self.toolbar_widget.setStyleSheet("background-color: #1e1e1e;")
        layout = QHBoxLayout(self.toolbar_widget)
        layout.setContentsMargins(8, 0, 8, 0)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        title_label.setStyleSheet("color: white;")
        layout.addWidget(title_label)

        layout.addStretch()

        # Navigation buttons
        def icon(pixmap):
            return self.style().standardIcon(pixmap)

        def nav_button(pixmap, action):
            btn = QPushButton()
            btn.setIcon(icon(pixmap))
            btn.setFixedSize(28, 28)
            btn.setStyleSheet("background: none; border: none;")
            btn.clicked.connect(action)
            return btn

        layout.addWidget(nav_button(QStyle.SP_ArrowBack, lambda: self.current_tab().back()))
        layout.addWidget(nav_button(QStyle.SP_ArrowForward, lambda: self.current_tab().forward()))
        layout.addWidget(nav_button(QStyle.SP_BrowserReload, lambda: self.current_tab().reload()))
        layout.addWidget(nav_button(QStyle.SP_FileDialogNewFolder, self.add_tab))

        # URL bar
        self.urlbar = QLineEdit()
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        self.urlbar.setStyleSheet("""
            background-color: #2b2b2b;
            color: white;
            border: 1px solid #555;
            padding: 4px;
        """)
        layout.addWidget(self.urlbar)

        # ===== WINDOW BUTTONS =====
        def window_button(text, callback, hover=None):
            btn = QPushButton(text)
            btn.setFixedSize(30, 24)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1e1e1e;
                    color: white;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {hover if hover else "#333"};
                }}
            """)
            btn.clicked.connect(callback)
            return btn

        layout.addWidget(window_button("—", self.showMinimized))
        layout.addWidget(window_button("▢", self.toggle_maximize))
        layout.addWidget(window_button("✕", self.close, "#b00020"))

        # Toolbar wrapper
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.addWidget(self.toolbar_widget)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Drag window
        self.toolbar_widget.mousePressEvent = self.mousePressEvent
        self.toolbar_widget.mouseMoveEvent = self.mouseMoveEvent
        self._drag_pos = None

        # First tab
        self.add_tab(self.home_url, "Start")


    # ---- Window drag ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()

    # ---- Window controls ----
    def toggle_maximize(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    # ---- Tabs ----
    def current_tab(self):
        return self.tabs.currentWidget()

    def add_tab(self, url=None, label="New Tab"):
        url = url or QUrl(self.home_url)
        tab = BrowserTab(self.profile)
        tab.setUrl(url)
        index = self.tabs.addTab(tab, label)
        self.tabs.setCurrentIndex(index)
        tab.urlChanged.connect(lambda q, t=tab: self.update_tab_title(t, q))
        tab.titleChanged.connect(lambda title, t=tab: self.set_tab_text(t, title))

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)

    def update_tab_title(self, tab, qurl):
        if tab == self.current_tab():
            self.urlbar.setText(qurl.toString())

    def set_tab_text(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index >= 0:
            self.tabs.setTabText(index, title[:20])

    def update_urlbar(self, index):
        tab = self.tabs.widget(index)
        if tab:
            self.urlbar.setText(tab.url().toString())

    def navigate_to_url(self):
        url = self.urlbar.text().strip()
        if not url.startswith("http"):
            url = "https://" + url
        self.current_tab().setUrl(QUrl(url))

    @Slot(QWebEngineDownloadRequest)
    def handle_download(self, download):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", download.suggestedFileName())
        if path:
            download.setDownloadFileName(path)
            download.accept()

    def closeEvent(self, event):
        while self.tabs.count():
            tab = self.tabs.widget(0)
            self.tabs.removeTab(0)
            tab.deleteLater()
        super().closeEvent(event)

# ---- Entry Point ----
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QTabBar::tab { background: #3c3c3c; color: white; padding: 6px; }
        QTabBar::tab:selected { background: #2b2b2b; }
    """)
    browser = Browser("Void Browser")
    browser.show()
    sys.exit(app.exec())
