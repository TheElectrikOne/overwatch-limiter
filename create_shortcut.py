"""Run this once to create a desktop shortcut and register the app to run at Windows startup."""

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _save_icon(dest: Path):
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 252, 252], fill=(245, 166, 35, 255))
    try:
        font = ImageFont.truetype("arialbd.ttf", 96)
    except Exception:
        font = ImageFont.load_default()
    draw.text((40, 72), "OW", fill=(255, 255, 255, 255), font=font)
    img.save(dest, format="ICO", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])


def _make_shortcut(pythonw: Path, app_path: Path, app_dir: Path, icon_path: Path, shortcut_path: Path):
    ps = f"""
$ws = New-Object -ComObject WScript.Shell
$s  = $ws.CreateShortcut('{shortcut_path}')
$s.TargetPath      = '{pythonw}'
$s.Arguments       = '"{app_path}"'
$s.WorkingDirectory= '{app_dir}'
$s.IconLocation    = '{icon_path}'
$s.Description     = 'Overwatch Limiter'
$s.Save()
"""
    return subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True)


def create_shortcut():
    app_dir = Path(__file__).parent.resolve()
    app_path = app_dir / "app.py"
    icon_path = app_dir / "icon.ico"
    shortcut_path = app_dir / "Overwatch Limiter.lnk"

    print("Saving icon...")
    _save_icon(icon_path)

    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)

    # Desktop shortcut — use PowerShell to get the real desktop path (handles OneDrive redirection)
    desktop_result = subprocess.run(
        ["powershell", "-Command", "[Environment]::GetFolderPath('Desktop')"],
        capture_output=True, text=True
    )
    desktop_dir = Path(desktop_result.stdout.strip())
    shortcut_path = desktop_dir / "Overwatch Limiter.lnk"
    result = _make_shortcut(pythonw, app_path, app_dir, icon_path, shortcut_path)
    if result.returncode == 0:
        print(f"Desktop shortcut created: {shortcut_path}")
    else:
        print(f"Desktop shortcut failed: {result.stderr.strip()}")

    # Startup folder shortcut (runs automatically at Windows login)
    startup_dir = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    startup_shortcut = startup_dir / "Overwatch Limiter.lnk"
    result = _make_shortcut(pythonw, app_path, app_dir, icon_path, startup_shortcut)
    if result.returncode == 0:
        print(f"Startup entry created: {startup_shortcut}")
    else:
        print(f"Startup entry failed: {result.stderr.strip()}")


if __name__ == "__main__":
    create_shortcut()
