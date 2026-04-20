import psutil
import time
import json
import argparse
from datetime import date
from pathlib import Path

PROCESS_NAMES = {"Overwatch.exe", "Overwatch Beta.exe", "Overwatch_retail_shipping.exe"}
CONFIG_FILE = Path(__file__).parent / "config.json"
DATA_FILE = Path.home() / ".overwatch_limiter" / "data.json"


def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE) as f:
            return json.load(f)
    return {}


def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def notify(title, message):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, app_name="Overwatch Limiter", timeout=10)
    except Exception:
        print(f"[{title}] {message}")


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


def today_key():
    return str(date.today())


def show_status():
    data = load_data()
    config = load_config()
    limit = config["daily_limit_minutes"]
    today = today_key()
    played_today = data.get(today, 0) / 60

    print(f"\n=== Overwatch Limiter Status ===")
    print(f"Daily limit : {limit} minutes")
    print(f"Played today: {played_today:.1f} minutes")
    print(f"Remaining   : {max(0, limit - played_today):.1f} minutes")

    print(f"\n--- Last 7 days ---")
    from datetime import timedelta
    for i in range(6, -1, -1):
        day = str(date.today() - timedelta(days=i))
        mins = data.get(day, 0) / 60
        bar = "#" * int(mins / 5)
        label = "today" if i == 0 else day
        print(f"  {label}: {mins:.0f} min  {bar}")
    print()


def reset_today():
    data = load_data()
    data[today_key()] = 0
    save_data(data)
    print("Today's playtime reset to 0.")


def run_limiter():
    config = load_config()
    daily_limit_sec = config["daily_limit_minutes"] * 60
    warn_thresholds = sorted(
        [w * 60 for w in config.get("warn_at_minutes_remaining", [15, 10, 5])],
        reverse=True,
    )
    interval = config.get("check_interval_seconds", 5)

    print(f"Overwatch Limiter active — daily limit: {config['daily_limit_minutes']} min")
    print("Press Ctrl+C to stop.\n")

    warned = set()
    session_start = None

    while True:
        try:
            data = load_data()
            played_so_far = data.get(today_key(), 0)
            proc = find_overwatch()

            if proc and session_start is None:
                session_start = time.time()
                remaining = (daily_limit_sec - played_so_far) / 60
                print(f"Overwatch running — {remaining:.1f} min remaining today.")
                if played_so_far >= daily_limit_sec:
                    notify("Overwatch Limiter", "Daily limit already reached! Closing Overwatch.")
                    kill_overwatch()
                    session_start = None

            elif proc and session_start is not None:
                elapsed = time.time() - session_start
                total_played = played_so_far + elapsed
                remaining_sec = daily_limit_sec - total_played

                for threshold in warn_thresholds:
                    if remaining_sec <= threshold and threshold not in warned:
                        warned.add(threshold)
                        notify(
                            "Overwatch Limiter",
                            f"Only {int(remaining_sec / 60)} minutes left for today!",
                        )

                if remaining_sec <= 0:
                    data[today_key()] = played_so_far + elapsed
                    save_data(data)
                    notify("Overwatch Limiter", "Time's up! Daily limit reached. Closing Overwatch.")
                    print("Limit reached — closing Overwatch.")
                    kill_overwatch()
                    session_start = None
                    warned.clear()

            elif not proc and session_start is not None:
                elapsed = time.time() - session_start
                data[today_key()] = played_so_far + elapsed
                save_data(data)
                total_today = data[today_key()] / 60
                print(f"Overwatch closed — session: {elapsed/60:.1f} min, total today: {total_today:.1f} min")
                session_start = None
                warned.clear()

            time.sleep(interval)

        except KeyboardInterrupt:
            if session_start is not None:
                elapsed = time.time() - session_start
                data = load_data()
                data[today_key()] = data.get(today_key(), 0) + elapsed
                save_data(data)
                print(f"\nStopped. Saved {elapsed/60:.1f} min to today's total.")
            else:
                print("\nStopped.")
            break


def main():
    parser = argparse.ArgumentParser(description="Overwatch playtime limiter")
    parser.add_argument("--status", action="store_true", help="Show play stats")
    parser.add_argument("--reset", action="store_true", help="Reset today's playtime to 0")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.reset:
        reset_today()
    else:
        run_limiter()


if __name__ == "__main__":
    main()
