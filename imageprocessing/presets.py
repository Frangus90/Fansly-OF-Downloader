"""Custom aspect ratio presets for image cropping"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union

# Presets file location (in current working directory where exe runs)
PRESETS_FILE = Path.cwd() / "crop_presets.json"
SETTINGS_FILE = Path.cwd() / "crop_settings.json"

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


def load_settings() -> Dict[str, str]:
    """
    Load crop tool settings from JSON file.

    Returns:
        Dictionary with settings (e.g., last_output_dir)
    """
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_settings(settings: Dict[str, str]) -> bool:
    """
    Save crop tool settings to JSON file.

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


def get_last_output_dir() -> Optional[Path]:
    """
    Get the last used output directory.

    Returns:
        Path to last output directory, or None if not set
    """
    settings = load_settings()
    dir_str = settings.get('last_output_dir')
    if dir_str:
        path = Path(dir_str)
        if path.exists() and path.is_dir():
            return path
    return None


def save_last_output_dir(output_dir: Path) -> bool:
    """
    Save the last used output directory.

    Args:
        output_dir: Path to output directory

    Returns:
        True if saved successfully
    """
    settings = load_settings()
    settings['last_output_dir'] = str(output_dir)
    return save_settings(settings)


def get_compression_settings() -> Dict[str, Union[bool, float, str]]:
    """
    Get file size compression settings.

    Returns:
        Dictionary with compression settings:
        - enable_file_size_compression: bool
        - target_file_size_mb: float
        - processing_mode: str
    """
    settings = load_settings()
    return {
        'enable_file_size_compression': settings.get('enable_file_size_compression', False),
        'target_file_size_mb': settings.get('target_file_size_mb', 5.0),
        'processing_mode': settings.get('processing_mode', 'crop_and_compress')
    }


def save_compression_settings(enable: bool, target_mb: float, mode: str) -> bool:
    """
    Save file size compression settings.

    Args:
        enable: Enable file size compression
        target_mb: Target file size in MB
        mode: Processing mode (crop_only, compress_only, crop_and_compress)

    Returns:
        True if saved successfully
    """
    settings = load_settings()
    settings['enable_file_size_compression'] = enable
    settings['target_file_size_mb'] = target_mb
    settings['processing_mode'] = mode
    return save_settings(settings)
