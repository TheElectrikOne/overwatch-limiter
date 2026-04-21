import psutil
import time
import json
import threading
from datetime import date
from pathlib import Path

PROCESS_NAMES = {"Overwatch.exe", "Overwatch Beta.exe", "Overwatch_retail_shipping.exe"}
CONFIG_FILE = Path(__file__).parent / "config.json"
DATA_FILE = Path.home() / ".overwatch_limiter" / "data.json"


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}


def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def today_key():
    return str(date.today())


def find_overwatch():
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] in PROCESS_NAMES:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def kill_overwatch():
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] in PROCESS_NAMES:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass


class LimiterThread(threading.Thread):
    """Background thread that monitors Overwatch and enforces the daily time limit."""

    def __init__(self, on_status_update=None, on_warning=None, on_limit_reached=None):
        super().__init__(daemon=True)
        self.on_status_update = on_status_update
        self.on_warning = on_warning
        self.on_limit_reached = on_limit_reached
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        config = load_config()
        daily_limit_sec = config["daily_limit_minutes"] * 60
        warn_thresholds = sorted(
            [w * 60 for w in config.get("warn_at_minutes_remaining", [15, 10, 5])],
            reverse=True,
        )
        interval = config.get("check_interval_seconds", 5)

        warned = set()
        session_start = None

        while not self._stop_event.is_set():
            data = load_data()
            played_so_far = data.get(today_key(), 0)
            proc = find_overwatch()

            if proc and session_start is None:
                session_start = time.time()
                if played_so_far >= daily_limit_sec:
                    if self.on_limit_reached:
                        self.on_limit_reached()
                    kill_overwatch()
                    session_start = None

            elif proc and session_start is not None:
                elapsed = time.time() - session_start
                total_played = played_so_far + elapsed
                remaining_sec = daily_limit_sec - total_played

                if self.on_status_update:
                    self.on_status_update(
                        ow_running=True,
                        played_today_sec=total_played,
                        remaining_sec=max(0.0, remaining_sec),
                    )

                for threshold in warn_thresholds:
                    if remaining_sec <= threshold and threshold not in warned:
                        warned.add(threshold)
                        if self.on_warning:
                            self.on_warning(int(remaining_sec / 60))

                if remaining_sec <= 0:
                    data[today_key()] = played_so_far + elapsed
                    save_data(data)
                    if self.on_limit_reached:
                        self.on_limit_reached()
                    kill_overwatch()
                    session_start = None
                    warned.clear()

            elif not proc and session_start is not None:
                elapsed = time.time() - session_start
                data[today_key()] = played_so_far + elapsed
                save_data(data)
                total = data[today_key()]
                session_start = None
                warned.clear()
                if self.on_status_update:
                    self.on_status_update(
                        ow_running=False,
                        played_today_sec=total,
                        remaining_sec=max(0.0, daily_limit_sec - total),
                    )
            else:
                if self.on_status_update:
                    self.on_status_update(
                        ow_running=False,
                        played_today_sec=played_so_far,
                        remaining_sec=max(0.0, daily_limit_sec - played_so_far),
                    )

            self._stop_event.wait(interval)
