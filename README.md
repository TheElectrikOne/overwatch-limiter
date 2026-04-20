# Overwatch Limiter

A lightweight local tool that monitors your Overwatch playtime, sends desktop warnings, and force-closes the game when your daily limit is hit.

## Requirements

- Python 3.8+
- Windows (uses Windows process names)

## Setup

1. **Clone or download** this repo to any folder.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your limit** by editing `config.json`:
   ```json
   {
     "daily_limit_minutes": 120,
     "warn_at_minutes_remaining": [15, 10, 5],
     "check_interval_seconds": 5
   }
   ```
   - `daily_limit_minutes` — how many minutes you're allowed per day (default: 120)
   - `warn_at_minutes_remaining` — desktop notifications will fire at these remaining-time milestones
   - `check_interval_seconds` — how often the script checks if Overwatch is running (default: 5)

## Usage

### Run the limiter
```bash
python limiter.py
```
Keep this running in a terminal (or set it up to start on login — see below). It will:
- Detect when Overwatch opens and start tracking your session
- Send desktop notifications as you approach your limit
- Force-close Overwatch when the limit is reached
- Save your playtime data locally at `~/.overwatch_limiter/data.json`

### Check your stats
```bash
python limiter.py --status
```
Shows today's usage, remaining time, and a bar chart of the last 7 days.

### Reset today's playtime
```bash
python limiter.py --reset
```
Resets today's tracked time back to 0 (if you want a fresh start mid-day).

## Auto-start on login (optional)

To have the limiter run automatically every time you log into Windows:

1. Press `Win + R`, type `shell:startup`, press Enter.
2. Create a shortcut in that folder pointing to:
   ```
   pythonw "C:\path\to\overwatch-limiter\limiter.py"
   ```
   Using `pythonw` instead of `python` runs it silently in the background with no terminal window.

## How it works

The script polls running processes every few seconds looking for `Overwatch.exe`. When found, it starts a session timer. Playtime is accumulated daily and stored in a local JSON file. When your remaining time hits a warning threshold you get a desktop notification; when it hits zero, Overwatch is killed and the session is saved.

Playtime resets automatically at midnight each day.

## Notes

- The limiter must be running to enforce limits — it doesn't retroactively block play.
- Data is stored at `%USERPROFILE%\.overwatch_limiter\data.json` and never leaves your machine.
- Tested on Windows 10/11 with Overwatch 2 via Battle.net.
