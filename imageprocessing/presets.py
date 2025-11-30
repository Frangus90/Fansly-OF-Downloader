"""Custom aspect ratio presets for image cropping"""

import json
from pathlib import Path
from typing import Dict, List, Optional

# Presets file location (next to the main script)
PRESETS_FILE = Path(__file__).parent.parent / "crop_presets.json"


def load_presets() -> Dict[str, float]:
    """
    Load custom presets from JSON file.

    Returns:
        Dictionary mapping preset name to aspect ratio
    """
    if PRESETS_FILE.exists():
        try:
            with open(PRESETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_presets(presets: Dict[str, float]) -> bool:
    """
    Save presets to JSON file.

    Args:
        presets: Dictionary mapping preset name to aspect ratio

    Returns:
        True if saved successfully
    """
    try:
        with open(PRESETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2)
        return True
    except IOError:
        return False


def add_preset(name: str, aspect_ratio: float) -> bool:
    """
    Add a new preset.

    Args:
        name: Preset name
        aspect_ratio: Aspect ratio (width/height)

    Returns:
        True if added successfully
    """
    presets = load_presets()
    presets[name] = aspect_ratio
    return save_presets(presets)


def remove_preset(name: str) -> bool:
    """
    Remove a preset.

    Args:
        name: Preset name to remove

    Returns:
        True if removed successfully
    """
    presets = load_presets()
    if name in presets:
        del presets[name]
        return save_presets(presets)
    return False


def get_preset_names() -> List[str]:
    """
    Get list of all preset names.

    Returns:
        List of preset names
    """
    presets = load_presets()
    return list(presets.keys())


def get_preset_aspect_ratio(name: str) -> Optional[float]:
    """
    Get aspect ratio for a preset.

    Args:
        name: Preset name

    Returns:
        Aspect ratio or None if not found
    """
    presets = load_presets()
    return presets.get(name)


def format_aspect_ratio(ratio: float) -> str:
    """
    Format aspect ratio for display.

    Args:
        ratio: Aspect ratio value

    Returns:
        Formatted string like "1.333" or "1.333 (4:3)" if it matches common ratios
    """
    # Common aspect ratios
    common_ratios = {
        1.0: "1:1",
        16/9: "16:9",
        9/16: "9:16",
        4/3: "4:3",
        3/4: "3:4",
        3/2: "3:2",
        2/3: "2:3",
        21/9: "21:9",
        1.91: "1.91:1",  # Instagram landscape
        0.8: "4:5",  # Instagram portrait
    }

    # Check for close match to common ratios
    for common_val, common_name in common_ratios.items():
        if abs(ratio - common_val) < 0.01:
            return f"{ratio:.3f} ({common_name})"

    return f"{ratio:.3f}"
