# plugins/link.py
from .abstractplugin import AbstractPlugin
import webbrowser, os, time
from pyglet.window import key

validation_dict = {}  # no parameters

class Link(AbstractPlugin):
    alias = "link"
    version = "0.3"

    _URL = "https://www.psytoolkit.org/c/3.6.4/edit?e=pvtb_touch"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._opened_at = None
        self._paused = False

        # >>> ONE OF THESE NAMES USUALLY WORKS WITH THE SCHEDULER <<<
        # Keep all three so whichever your fork checks will be True until ENTER.
        self.running = False
        self.active = False

    def set_parameter(self, name, value):
        pass  # no scenario params

    def start(self):
        self._open_url_firefox_or_default(self._URL)
        self._opened_at = time.time()
        self._paused = True
        # advertise liveness
        self.running = True
        self.active = True
        self.log("link_opened", {"url": self._URL})

    def stop(self):
        self._paused = False
        self.running = False
        self.active = False
        elapsed = (time.time() - self._opened_at) if self._opened_at else 0
        self.log("link_end", {"elapsed_s": round(elapsed, 3)})

    # --- If your AbstractPlugin exposes these hooks, they help too ---
    # They’re harmless if unused by your fork.
    def is_active(self):
        return self._paused or self.running or self.active

    def is_finished(self):
        return not self.is_active()

    def update(self, dt):
        # nothing to do; we just hold until ENTER
        pass

    def on_key_press(self, symbol, modifiers):
        if not self._paused:
            return
        if key.symbol_string(symbol).upper() == "ENTER":
            self._paused = False
            self.running = False
            self.active = False
            after_s = round(time.time() - (self._opened_at or time.time()), 3)
            self.log("link_resume", {"after_s": after_s})

    def draw(self):
        # optional prompt
        pass

    def _open_url_firefox_or_default(self, url: str):
        ff_paths = [
            r"C:\Program Files\Mozilla Firefox\firefox.exe",
            r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
        ]
        exe = next((p for p in ff_paths if os.path.exists(p)), None)
        if exe:
            webbrowser.register("firefox", None, webbrowser.BackgroundBrowser(exe))
            webbrowser.get("firefox").open(url, new=2)
        else:
            webbrowser.open(url, new=2)
