Void Browser

This is a minimal, personal browser project I built to learn Python and HTML basics. The main idea is to develop the browser itself and use it as a hub for a private TiddlyWiki.

You can check out TiddlyWiki's Getting Started guide if you want to see how to create and manage your own wiki.

The browser is fully downloadable – feel free to grab it, tweak it, and adjust it to your own needs. 
Think of it as a personal playground for Python, WebEngine, and offline wiki experimentation.

Current Features:

Tabbed browsing – open multiple tabs, close them, navigate back/forward.

Custom tracker blocker – blocks common trackers like Google Analytics, DoubleClick, Facebook, etc.

Persistent cookies and disk cache – keeps your session info (like logged-in accounts) across restarts.

Frameless, dark-themed UI – simple, clean, and easy on the eyes.

Custom title bar with window controls – minimize, maximize, close, and basic navigation buttons.

URL bar navigation – type a URL and press enter to visit.

Download support – save files through the browser.

Start page integration – opens your local TiddlyWiki as the default homepage.

Tip: once you have your TiddlyWiki index.html, you can point the browser to it by editing this line in void.py:

startpage_path = Path(__file__).parent.parent / "void-hub" / "index.html"

Adjust the path however your folder structure is set up – the example above matches my setup, not yours.

Planned Features:

Enhanced privacy options – fine-grained control over JavaScript, third-party cookies, and requests.

Improved auto-save for TiddlyWiki – making edits seamless without manually replacing files.

Optional extensions / customization – let users add more functionality for their personal needs.

Better tab management – like pinning, reordering, or restoring sessions.

Smoother drag-and-drop UI tweaks – improve the window and toolbar handling.



This project is very much a personal and experimental tool, but anyone curious about Python GUI development or offline wikis can explore, hack, and expand it.

-grvty
