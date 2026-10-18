"""Bundled Tenshi branding, compatible with source and PyInstaller --onefile."""
from pathlib import Path
import sys


def asset_path(name: str) -> Path:
    """Find assets both from source and the one-file PyInstaller extraction dir."""
    if name not in ("tenshi_logo.png", "tenshi_icon.png", "tenshi.ico"):
        raise ValueError("Unbekanntes Tenshi-Asset")
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        root = Path(sys._MEIPASS)
    else:
        root = Path(__file__).resolve().parent.parent
    return root / "recoverydesk" / "assets" / name
