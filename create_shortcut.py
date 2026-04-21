"""Run this once to create a desktop shortcut that launches the Overwatch Limiter UI."""

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


def create_shortcut():
    app_dir = Path(__file__).parent.resolve()
    app_path = app_dir / "app.py"
    icon_path = app_dir / "icon.ico"
    desktop = Path.home() / "Desktop"
    shortcut_path = desktop / "Overwatch Limiter.lnk"

    print("Saving icon...")
    _save_icon(icon_path)

    pythonw = Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        pythonw = Path(sys.executable)

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
    result = subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Shortcut created: {shortcut_path}")
    else:
        print(f"Failed: {result.stderr.strip()}")


if __name__ == "__main__":
    create_shortcut()
