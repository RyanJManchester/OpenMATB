# --- top of file (unchanged imports) ---
from .abstractplugin import AbstractPlugin
import random, time, csv, os
from pyglet.window import key

from core import validation

# If you renamed your class already to `Pvt`, keep that. If not, rename it here:
class Pvt(AbstractPlugin):
    alias = "pvt"
    version = "0.3"
        # Tell Scenario which parameters exist and how to validate them
    validation_dict = {
        "duration_s":         validation.is_natural_integer,   # e.g., 180
        "iti_min_ms":         validation.is_natural_integer,   # e.g., 2000
        "iti_max_ms":         validation.is_natural_integer,   # e.g., 10000
        "lapse_threshold_ms": validation.is_natural_integer,   # e.g., 500
        "response_key":       validation.is_keyboard_key,      # e.g., SPACE
        "outfile":            validation.is_string,            # e.g., pvt_trials.csv
        "show_countup":       validation.is_boolean,           # true/false
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Parameters (scenario-overridable)
        self.duration_s = 180
        self.iti_min_ms = 2000
        self.iti_max_ms = 10000
        self.response_key = "SPACE"
        self.lapse_threshold_ms = 500
        self.outfile = ""
        self.show_countup = True

        # State
        self._state = "idle"
        self._trial_deadline = None
        self._trial_idx = 0
        self._stim_on_ms = None
        self._session_start_s = None
        self._iti_ms = None

        # UI: defer creating label until window exists
        self._msg = None
        self._anchor_window = None

        # Optional CSV
        self._csv_fp = None
        self._csv_writer = None

     

    # --------- new helpers ----------
    def _ensure_ui(self):
        """Create label once a window is available."""
        if self._msg is not None:
            return
        # Prefer the plugin's window if AbstractPlugin sets it later
        win = getattr(self, "window", None)
        if win is None:
            # Fallback: use the first pyglet window if available
            import pyglet
            win = pyglet.app.windows[0] if pyglet.app.windows else None

        if win:
            cx, cy = win.width // 2, win.height // 2
            self._anchor_window = win
        else:
            # conservative fallback if drawn before window attach (shouldn't happen in OpenMATB)
            cx, cy = 320, 240

        self._msg = text.Label(
            "",
            font_name="Arial",
            font_size=28,
            x=cx,
            y=cy,
            anchor_x="center",
            anchor_y="center",
        )

    # Keep your set_parameter() as you had it; omitted here for brevity
    def set_parameter(self, name, value):
        name = str(name)
        if name in ("duration_s", "iti_min_ms", "iti_max_ms", "lapse_threshold_ms"):
            setattr(self, name, int(value))
        elif name == "response_key":
            self.response_key = str(value).upper()
        elif name == "outfile":
            self.outfile = str(value)
        elif name == "show_countup":
            self.show_countup = str(value).lower() in ("1", "true", "yes", "y")

    def start(self):
        self._trial_idx = 0
        self._session_start_s = time.time()
        self._state = "waiting"
        self._schedule_next_trial()
        self._open_csv_if_requested()
        self._ensure_ui()  # <-- safe now; window should be ready
        self.log("pvt_session_start", {"t0": self._session_start_s})

    def stop(self):
        if self._state != "idle":
            self.log("pvt_session_end", {"elapsed_s": round(time.time() - self._session_start_s, 3)})
        self._state = "idle"
        self._close_csv_if_open()

    def update(self, dt):
        if self._state == "waiting" and time.time() >= self._trial_deadline:
            self._stim_on_ms = self._now_ms()
            self._state = "stim"
        if self._session_start_s and (time.time() - self._session_start_s) >= self.duration_s:
            self.stop()

    def draw(self):
        self._ensure_ui()
        if not self._msg:
            return  # nothing to draw yet

        if self._state == "stim":
            self._msg.text = "NOW!"
        elif self._state == "waiting":
            self._msg.text = "···" if self.show_countup else ""
        else:
            self._msg.text = ""

        self._msg.draw()

    def on_resize(self, width, height):
        # recentre label if window is resized
        if self._msg:
            self._msg.x = width // 2
            self._msg.y = height // 2

    def on_key_press(self, symbol, modifiers):
        if self._state != "stim":
            return
        from pyglet.window import key as pyg_key
        if pyg_key.symbol_string(symbol).upper() != self.response_key:
            return

        rt_ms = self._now_ms() - self._stim_on_ms
        self._trial_idx += 1
        lapse = int(rt_ms >= self.lapse_threshold_ms)
        row = {
            "trial": self._trial_idx,
            "rt_ms": rt_ms,
            "lapse": lapse,
            "stim_on_ms": self._stim_on_ms,
            "timestamp_s": round(time.time(), 3),
        }
        self.log("pvt_trial", row)
        if self._csv_writer:
            self._csv_writer.writerow(row)
            self._csv_fp.flush()
        self._schedule_next_trial()
        self._state = "waiting"

    # ----- unchanged helpers -----
    def _schedule_next_trial(self):
        self._iti_ms = random.randint(self.iti_min_ms, self.iti_max_ms)
        self._trial_deadline = time.time() + (self._iti_ms / 1000.0)

    def _now_ms(self):
        return int(time.time() * 1000)

    def _open_csv_if_requested(self):
        if not self.outfile:
            return
        session_dir = getattr(self, "session_directory", None) or ""
        path = os.path.join(session_dir, self.outfile) if session_dir else self.outfile
        if os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
        self._csv_fp = open(path, "w", newline="", encoding="utf-8")
        self._csv_writer = csv.DictWriter(
            self._csv_fp, fieldnames=["trial", "rt_ms", "lapse", "stim_on_ms", "timestamp_s"]
        )
        self._csv_writer.writeheader()

    def _close_csv_if_open(self):
        if self._csv_fp:
            try:
                self._csv_fp.close()
            finally:
                self._csv_fp = None
                self._csv_writer = None
