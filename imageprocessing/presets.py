"""Custom aspect ratio presets for image cropping"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

# Presets file location (next to the main script)
PRESETS_FILE = Path(__file__).parent.parent / "crop_presets.json"

# Preset data structure: can be float (legacy) or dict with 'aspect_ratio' and 'anchor'
PresetData = Union[float, Dict[str, Union[float, str]]]


def load_presets() -> Dict[str, PresetData]:
    """
    Load custom presets from JSON file.
    Supports both legacy format (float) and new format (dict with aspect_ratio and anchor).

    Returns:
        Dictionary mapping preset name to preset data (float or dict)
    """
    if PRESETS_FILE.exists():
        try:
            with open(PRESETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_presets(presets: Dict[str, PresetData]) -> bool:
    """
    Save presets to JSON file.

    Args:
        presets: Dictionary mapping preset name to preset data

    Returns:
        True if saved successfully
    """
    try:
        with open(PRESETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2)
        return True
    except IOError:
        return False


def add_preset(name: str, aspect_ratio: float, anchor: Optional[str] = None) -> bool:
    """
    Add a new preset.

    Args:
        name: Preset name
        aspect_ratio: Aspect ratio (width/height)
        anchor: Optional alignment/anchor (Center, Top, Bottom, Left, Right)

    Returns:
        True if added successfully
    """
    presets = load_presets()
    
    # Save as new format if anchor is provided, otherwise save as legacy format for compatibility
    if anchor:
        presets[name] = {
            'aspect_ratio': aspect_ratio,
            'anchor': anchor
        }
    else:
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
    Supports both legacy format (float) and new format (dict).

    Args:
        name: Preset name

    Returns:
        Aspect ratio or None if not found
    """
    presets = load_presets()
    preset_data = presets.get(name)
    
    if preset_data is None:
        return None
    
    # Handle legacy format (float)
    if isinstance(preset_data, (int, float)):
        return float(preset_data)
    
    # Handle new format (dict)
    if isinstance(preset_data, dict):
        return preset_data.get('aspect_ratio')
    
    return None


def get_preset_anchor(name: str) -> Optional[str]:
    """
    Get anchor/alignment for a preset.

    Args:
        name: Preset name

    Returns:
        Anchor string (Center, Top, Bottom, Left, Right) or None if not found/legacy format
    """
    presets = load_presets()
    preset_data = presets.get(name)
    
    if preset_data is None:
        return None
    
    # Handle new format (dict)
    if isinstance(preset_data, dict):
        return preset_data.get('anchor', 'Center')  # Default to Center if missing
    
    # Legacy format doesn't have anchor
    return None


def get_preset_data(name: str) -> Optional[Dict[str, Union[float, str]]]:
    """
    Get full preset data (aspect ratio and anchor).

    Args:
        name: Preset name

    Returns:
        Dictionary with 'aspect_ratio' and 'anchor' keys, or None if not found
    """
    presets = load_presets()
    preset_data = presets.get(name)
    
    if preset_data is None:
        return None
    
    # Handle legacy format (float) - convert to new format
    if isinstance(preset_data, (int, float)):
        return {
            'aspect_ratio': float(preset_data),
            'anchor': 'Center'  # Default anchor for legacy presets
        }
    
    # Handle new format (dict)
    if isinstance(preset_data, dict):
        return {
            'aspect_ratio': preset_data.get('aspect_ratio'),
            'anchor': preset_data.get('anchor', 'Center')
        }
    
    return None


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
