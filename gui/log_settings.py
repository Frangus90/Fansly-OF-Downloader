"""
Settings persistence for log window
"""

import json
from pathlib import Path
from typing import Dict, Any


# Settings file location
SETTINGS_FILE = Path.cwd() / "log_window_settings.json"


def load_log_window_settings() -> Dict[str, Any]:
    """
    Load log window settings from JSON file.

    Returns:
        Dictionary with settings (window position, size, preferences)
    """
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_log_window_settings(settings: Dict[str, Any]) -> bool:
    """
    Save log window settings to JSON file.

    Args:
        settings: Dictionary with settings to save

    Returns:
        True if saved successfully
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2)
        return True
    except IOError:
        return False


def get_default_settings(parent) -> Dict[str, Any]:
    """
    Get default settings with window centered on parent.

    Args:
        parent: Parent window to center on

    Returns:
        Dictionary with default settings
    """
    # Default window size
    default_width = 800
    default_height = 400

    # Calculate centered position on parent
    parent.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()

    # Center on parent
    x = parent_x + (parent_width - default_width) // 2
    y = parent_y + (parent_height - default_height) // 2

    # Ensure window is on screen (minimum 0,0)
    x = max(0, x)
    y = max(0, y)

    return {
        "window_x": x,
        "window_y": y,
        "window_width": default_width,
        "window_height": default_height,
        "always_on_top": False,
        "is_visible": False
    }
