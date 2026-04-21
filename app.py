import threading
from datetime import date, timedelta
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
import pystray

from limiter_core import (
    LimiterThread,
    load_config,
    save_config,
    load_data,
    save_data,
    today_key,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLOR_GREEN = "#2ecc71"
COLOR_GREEN_HOVER = "#27ae60"
COLOR_RED = "#e74c3c"
COLOR_RED_HOVER = "#c0392b"
COLOR_ORANGE = "#f39c12"
COLOR_BLUE = "#3498db"


def _make_tray_image():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([2, 2, 62, 62], fill=(245, 166, 35, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 18), "OW", fill=(255, 255, 255, 255), font=font)
    return img


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Overwatch Limiter")
        self.geometry("480x640")
        self.resizable(False, False)

        self._monitor: LimiterThread | None = None
        self._tray: pystray.Icon | None = None
        self._tray_thread: threading.Thread | None = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)
        self._start_tray()
        self.after(200, self._refresh_display)
        self.after(300, self._start_monitor)
        self.after(5000, self._auto_refresh)

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        # ── Header ──────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 6))
        ctk.CTkLabel(
            header, text="Overwatch Limiter", font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")
        self._status_label = ctk.CTkLabel(
            header, text="● INACTIVE", text_color="gray", font=ctk.CTkFont(size=12)
        )
        self._status_label.pack(side="right", pady=(4, 0))

        # ── Today card ──────────────────────────────────────────────────────────
        today_card = ctk.CTkFrame(self)
        today_card.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            today_card, text="TODAY", font=ctk.CTkFont(size=10), text_color="gray"
        ).pack(pady=(12, 0))
        self._usage_label = ctk.CTkLabel(
            today_card, text="0 / 120 min", font=ctk.CTkFont(size=38, weight="bold")
        )
        self._usage_label.pack()
        self._remaining_label = ctk.CTkLabel(
            today_card, text="120 min remaining", font=ctk.CTkFont(size=12), text_color="gray"
        )
        self._remaining_label.pack()
        self._progress = ctk.CTkProgressBar(today_card, width=400)
        self._progress.pack(pady=(6, 14), padx=20)
        self._progress.set(0)

        # ── Settings card ────────────────────────────────────────────────────────
        cfg = load_config()
        settings_card = ctk.CTkFrame(self)
        settings_card.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            settings_card, text="SETTINGS", font=ctk.CTkFont(size=10), text_color="gray"
        ).pack(anchor="w", padx=16, pady=(12, 6))

        def _setting_row(parent, label, var, width=90):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=3)
            ctk.CTkLabel(row, text=label, anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkEntry(row, textvariable=var, width=width).pack(side="right")

        self._limit_var = ctk.StringVar(value=str(cfg["daily_limit_minutes"]))
        self._warn_var = ctk.StringVar(
            value=", ".join(str(w) for w in cfg.get("warn_at_minutes_remaining", [15, 10, 5]))
        )

        _setting_row(settings_card, "Daily limit (minutes)", self._limit_var)
        _setting_row(
            settings_card,
            "Warn at remaining minutes  (comma-separated)",
            self._warn_var,
            width=120,
        )

        self._save_btn = ctk.CTkButton(
            settings_card, text="Save Settings", command=self._save_settings
        )
        self._save_btn.pack(pady=(8, 12), padx=16, fill="x")

        # ── Monitor toggle & reset ───────────────────────────────────────────────
        self._toggle_btn = ctk.CTkButton(
            self,
            text="Stop Monitor",
            height=44,
            fg_color=COLOR_RED,
            hover_color=COLOR_RED_HOVER,
            command=self._toggle_monitor,
        )
        self._toggle_btn.pack(fill="x", padx=20, pady=(6, 3))

        ctk.CTkButton(
            self,
            text="Reset Today's Playtime",
            height=32,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._reset_today,
        ).pack(fill="x", padx=20, pady=(0, 6))

        # ── 7-day history ────────────────────────────────────────────────────────
        hist_card = ctk.CTkFrame(self)
        hist_card.pack(fill="x", padx=20, pady=6)
        ctk.CTkLabel(
            hist_card, text="LAST 7 DAYS", font=ctk.CTkFont(size=10), text_color="gray"
        ).pack(anchor="w", padx=16, pady=(12, 4))
        self._canvas = ctk.CTkCanvas(
            hist_card, height=110, bg="#2b2b2b", highlightthickness=0
        )
        self._canvas.pack(fill="x", padx=16, pady=(0, 14))
        self._canvas.bind("<Configure>", lambda _e: self._draw_history())

    # ------------------------------------------------------------------ tray

    def _start_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._show_window, default=True),
            pystray.MenuItem("Quit", self._quit_app),
        )
        self._tray = pystray.Icon("ow_limiter", _make_tray_image(), "Overwatch Limiter", menu)
        self._tray_thread = threading.Thread(target=self._tray.run, daemon=True)
        self._tray_thread.start()

    def _hide_to_tray(self):
        self.withdraw()

    def _show_window(self, _icon=None, _item=None):
        self.after(0, self.deiconify)
        self.after(0, self.lift)
        self.after(0, self.focus_force)

    def _quit_app(self, _icon=None, _item=None):
        if self._monitor:
            self._monitor.stop()
        if self._tray:
            self._tray.stop()
        self.after(0, self.destroy)

    # ------------------------------------------------------------------ monitor

    def _start_monitor(self):
        self._monitor = LimiterThread(
            on_status_update=self._on_status_update,
            on_warning=self._on_warning,
            on_limit_reached=self._on_limit_reached,
        )
        self._monitor.start()
        self._toggle_btn.configure(
            text="Stop Monitor", fg_color=COLOR_RED, hover_color=COLOR_RED_HOVER
        )

    def _stop_monitor(self):
        if self._monitor:
            self._monitor.stop()
            self._monitor = None
        self._toggle_btn.configure(
            text="Start Monitor", fg_color=COLOR_GREEN, hover_color=COLOR_GREEN_HOVER
        )
        self._status_label.configure(text="● INACTIVE", text_color="gray")

    def _toggle_monitor(self):
        if self._monitor and self._monitor.is_alive():
            self._stop_monitor()
        else:
            self._start_monitor()

    # ------------------------------------------------------------------ callbacks

    def _on_status_update(self, ow_running, played_today_sec, remaining_sec):
        self.after(0, lambda: self._apply_status(ow_running, played_today_sec, remaining_sec))

    def _apply_status(self, ow_running, played_today_sec, remaining_sec):
        cfg = load_config()
        limit_sec = cfg["daily_limit_minutes"] * 60
        played_min = played_today_sec / 60
        remaining_min = remaining_sec / 60

        self._usage_label.configure(
            text=f"{played_min:.0f} / {cfg['daily_limit_minutes']} min"
        )
        self._remaining_label.configure(text=f"{remaining_min:.0f} min remaining")

        ratio = min(1.0, played_today_sec / limit_sec) if limit_sec else 0
        self._progress.set(ratio)
        if ratio >= 1.0:
            self._progress.configure(progress_color=COLOR_RED)
        elif ratio >= 0.75:
            self._progress.configure(progress_color=COLOR_ORANGE)
        else:
            self._progress.configure(progress_color=COLOR_BLUE)

        if ow_running:
            self._status_label.configure(text="● PLAYING", text_color=COLOR_GREEN)
        else:
            self._status_label.configure(text="● MONITORING", text_color=COLOR_BLUE)

        self._draw_history()

    def _on_warning(self, minutes_remaining):
        try:
            from plyer import notification
            notification.notify(
                title="Overwatch Limiter",
                message=f"Only {minutes_remaining} minutes left today!",
                app_name="Overwatch Limiter",
                timeout=10,
            )
        except Exception:
            pass

    def _on_limit_reached(self):
        try:
            from plyer import notification
            notification.notify(
                title="Overwatch Limiter",
                message="Time's up! Daily limit reached. Closing Overwatch.",
                app_name="Overwatch Limiter",
                timeout=10,
            )
        except Exception:
            pass
        self.after(0, self._refresh_display)

    # ------------------------------------------------------------------ actions

    def _save_settings(self):
        try:
            limit = int(self._limit_var.get().strip())
            warns = [
                int(x.strip())
                for x in self._warn_var.get().split(",")
                if x.strip().isdigit()
            ]
            cfg = load_config()
            cfg["daily_limit_minutes"] = limit
            cfg["warn_at_minutes_remaining"] = sorted(warns, reverse=True)
            save_config(cfg)
            self._save_btn.configure(text="Saved ✓")
            self.after(1500, lambda: self._save_btn.configure(text="Save Settings"))
            if self._monitor and self._monitor.is_alive():
                self._stop_monitor()
                self._start_monitor()
            self._refresh_display()
        except (ValueError, KeyError):
            self._save_btn.configure(text="Invalid input")
            self.after(1500, lambda: self._save_btn.configure(text="Save Settings"))

    def _reset_today(self):
        data = load_data()
        data[today_key()] = 0
        save_data(data)
        self._refresh_display()

    # ------------------------------------------------------------------ display

    def _refresh_display(self):
        cfg = load_config()
        data = load_data()
        played_sec = data.get(today_key(), 0)
        limit_sec = cfg["daily_limit_minutes"] * 60
        remaining_sec = max(0.0, limit_sec - played_sec)
        self._apply_status(ow_running=False, played_today_sec=played_sec, remaining_sec=remaining_sec)
        self._limit_var.set(str(cfg["daily_limit_minutes"]))
        self._warn_var.set(
            ", ".join(str(w) for w in cfg.get("warn_at_minutes_remaining", [15, 10, 5]))
        )

    def _draw_history(self):
        canvas = self._canvas
        canvas.delete("all")
        canvas.update_idletasks()
        w = canvas.winfo_width() or 400
        h = canvas.winfo_height() or 110

        cfg = load_config()
        data = load_data()
        limit_min = cfg["daily_limit_minutes"]
        max_min = limit_min * 1.25 or 1

        days = [str(date.today() - timedelta(days=i)) for i in range(6, -1, -1)]
        bar_w = w / 7

        for i, day in enumerate(days):
            mins = data.get(day, 0) / 60
            bar_h = min((mins / max_min) * (h - 28), h - 28)
            x0 = i * bar_w + 4
            x1 = (i + 1) * bar_w - 4
            y1 = h - 18
            y0 = y1 - bar_h

            color = COLOR_RED if mins >= limit_min else COLOR_BLUE
            if bar_h > 0:
                canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

            label = "Today" if day == str(date.today()) else day[5:]
            canvas.create_text(
                (x0 + x1) / 2, h - 8, text=label, fill="#888", font=("Segoe UI", 7)
            )
            if mins > 0:
                canvas.create_text(
                    (x0 + x1) / 2,
                    max(y0 - 7, 6),
                    text=f"{int(mins)}m",
                    fill="white",
                    font=("Segoe UI", 7),
                )

    def _auto_refresh(self):
        if not (self._monitor and self._monitor.is_alive()):
            self._refresh_display()
        self.after(10_000, self._auto_refresh)


if __name__ == "__main__":
    app = App()
    app.mainloop()
