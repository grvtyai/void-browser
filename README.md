<div align="center">

# 🕳️ Void Browser

**A minimal, hackable browser built with Python & PySide6.**  
Crafted for learning, privacy, and a seamless local wiki experience.

![Python](https://img.shields.io/badge/Python-3.10+-8a2be2?style=flat-square&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-Qt6-5a3a7a?style=flat-square&logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Linux-0a0a14?style=flat-square&logo=linux&logoColor=white)

</div>

---

## 🌌 What is Void?

Void is a personal browser project — dark, minimal, and built from scratch in Python. It started as a wrapper for a private offline TiddlyWiki (**Blackhole**) and grew into a fully custom browsing experience with its own UI, tab management, settings system, and start page.

No Electron. No Chrome extensions. Just Python, Qt, and full control.

---

## ✨ Features

### 🗂️ Tab Management
- **Vertical sidebar** with tabs listed top to bottom
- **Auto-collapsing sidebar** — shows only favicons on idle, expands smoothly on hover
- Favicons automatically loaded from each website
- Active tab highlighted with a subtle background
- Close individual tabs with the ✕ button

### 🏠 Start Page
- Live **clock & date** with a glowing purple aesthetic
- **Search bar** — type a URL or search directly via your chosen engine
- **Most visited sites** grid — add, remove, and click your favorite links
- Local file support — link directly to your TiddlyWiki or any local HTML file

### ⚙️ Settings (persistent)
All settings are saved to `settings.json` and applied instantly via a Python–JavaScript bridge (`QWebChannel`):

| Setting | Description |
|---|---|
| 🔍 Search engine | Google, DuckDuckGo, Brave, Bing |
| 🏠 Homepage | Void start page or custom URL |
| 📐 Sidebar width | Adjustable via slider (160–380px) |
| 🔒 Tracker blocker | Blocks Google Analytics, DoubleClick & more |
| 🚫 Do Not Track | Sends DNT header to websites |
| 📂 Auto-collapse sidebar | Favicon-only mode with smooth animation |

### 🔒 Privacy
- Built-in **tracker blocker** (Google Analytics, DoubleClick, Facebook, etc.)
- **Persistent cookies & cache** — stays logged in across sessions
- Do Not Track header support

### 🖥️ UI & UX
- Fully **frameless window** with custom titlebar
- Drag to move, resize from all edges and corners
- Minimize, maximize, close buttons
- **URL bar** with status bar showing hovered link destinations
- All links open in a **new tab** by default
- Dark space theme — blacks, deep purples, glowing lavender accents

---

## 📁 Project Structure

```
void-browser/
├── void.py              # Main browser application
├── settings.json        # Persistent user settings (auto-generated)
├── startpage/
│   └── index.html       # Custom start page with settings modal
└── assets/
    └── void_logo.jpg    # Window icon

blackhole/               # Your TiddlyWiki (separate folder)
└── index.html
```

---

## 🚀 Getting Started

### Requirements

```bash
pip install PySide6
```

### Run

```bash
cd void-browser
python void.py
```

### Linking your TiddlyWiki

Point Void to your local TiddlyWiki by navigating to it in the URL bar:

```
file:///absolute/path/to/blackhole/index.html
```

Or add it as a favorite on the start page using a relative path like `../blackhole/index.html` — Void resolves it automatically.

---

## 🎨 Design Philosophy

Void is built around the aesthetic of its namesake — a black hole.  
Deep blacks, rich purples, and glowing lavender highlights pulled directly from space photography.  
Everything is intentional: no bloat, no ads, no telemetry.

> *"What falls in, stays."*

---

## 🔧 Hackability

Void is designed to be modified. Every component is self-contained:

- **`SimpleTrackerBlocker`** — extend the blocked domain list
- **`BrowserBridge`** — add new Python↔JS settings via `@Slot`
- **`TabEntry`** — customize how tabs look and behave
- **`startpage/index.html`** — pure HTML/CSS/JS, edit freely

---

## 🛣️ Roadmap

- [ ] Tab groups with collapsible sections in the sidebar
- [ ] Keyboard shortcuts (Ctrl+T, Ctrl+W, Ctrl+L)
- [ ] Bookmark manager
- [ ] History viewer
- [ ] Custom themes via settings
- [ ] TiddlyWiki save improvements

---

## 📄 License

MIT — download it, break it, make it yours.
