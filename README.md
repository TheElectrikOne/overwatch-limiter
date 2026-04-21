# Overwatch Limiter

A local Windows desktop app that tracks your daily Overwatch playtime, sends warnings as you approach your limit, and force-closes the game when time's up.

![Dark UI with today's usage, settings, and 7-day history chart]

## Features

- Dark, modern UI built with customtkinter
- Live progress bar and 7-day play history chart
- Desktop notifications at configurable warning thresholds
- Force-closes Overwatch when the daily limit is hit
- Minimises to the system tray — stays running without a window in the way
- Settings saved instantly — no config file editing required

## Requirements

- Python 3.10+
- Windows 10 or 11
- Overwatch 2 via Battle.net

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Launch the app

```bash
python app.py
```

The monitor starts automatically when the app opens. The window can be closed safely — it minimises to the system tray (look for the orange **OW** icon near the clock). Right-click the tray icon for **Show** / **Quit**.

### 3. Create a desktop shortcut (one-time)

```bash
python create_shortcut.py
```

This places an **Overwatch Limiter** shortcut on your Desktop with a custom icon. Double-click it to launch the app without opening a terminal.

> **Auto-start on login (optional):** Press `Win + R`, type `shell:startup`, and copy the desktop shortcut into that folder. The limiter will then launch silently every time you log in.

## Using the UI

| Element | Description |
|---|---|
| **TODAY** display | Shows minutes played vs. your daily limit and a colour-coded progress bar |
| **Daily limit** field | How many minutes you're allowed per day |
| **Warn at** field | Comma-separated list of remaining-minute thresholds that trigger a desktop notification (e.g. `15, 10, 5`) |
| **Save Settings** | Saves and immediately applies the new values |
| **Stop / Start Monitor** | Pauses or resumes process monitoring |
| **Reset Today's Playtime** | Zeroes out today's tracked time |
| **LAST 7 DAYS** chart | Bar chart of recent play — bars turn red when the daily limit was exceeded |

## How it works

The app polls running processes every 5 seconds (configurable in `config.json`). When `Overwatch.exe` is detected a session timer starts. Play time accumulates in `%USERPROFILE%\.overwatch_limiter\data.json` and resets at midnight each day. When remaining time hits a warning threshold you receive a desktop notification; when it reaches zero Overwatch is killed and the session is saved.

## Data & privacy

All data is stored locally at `%USERPROFILE%\.overwatch_limiter\data.json`. Nothing is sent anywhere.

## CLI usage (optional)

The original command-line interface is still available:

```bash
# Run monitor in terminal
python limiter.py

# View stats
python limiter.py --status

# Reset today
python limiter.py --reset
```
