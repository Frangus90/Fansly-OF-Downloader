"""Utility functions for image processing"""

from pathlib import Path
from typing import Tuple
from PIL import Image

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}


def validate_image_file(filepath: Path) -> bool:
    """
    Validate if file is a supported image.

    Args:
        filepath: Path to image file

    Returns:
        True if valid image file, False otherwise
    """
    if not filepath.exists():
        return False

    if not filepath.is_file():
        return False

    if filepath.suffix.lower() not in SUPPORTED_FORMATS:
        return False

    # Try to open with PIL to verify it's actually an image
    try:
        with Image.open(filepath) as img:
            img.verify()
        return True
    except Exception:
        return False


def is_supported_format(filepath: Path) -> bool:
    """
    Check if file extension is supported.

    Args:
        filepath: Path to check

    Returns:
        True if extension is supported
    """
    return filepath.suffix.lower() in SUPPORTED_FORMATS


def get_aspect_ratio(width: int, height: int) -> float:
    """
    Calculate aspect ratio.

    Args:
        width: Image width
        height: Image height

    Returns:
        Aspect ratio (width/height)
    """
    if height == 0:
        return 1.0
    return width / height


def calculate_constrained_size(
    current_w: int,
    current_h: int,
    target_w: int,
    target_h: int,
    lock_aspect: bool = True
) -> Tuple[int, int]:
    """
    Calculate final size maintaining aspect ratio if locked.

    Args:
        current_w: Current width
        current_h: Current height
        target_w: Target width
        target_h: Target height
        lock_aspect: Whether to maintain aspect ratio

    Returns:
        Tuple of (final_width, final_height)
    """
    if not lock_aspect:
        return (target_w, target_h)

    # Maintain aspect ratio based on current dimensions
    current_ratio = get_aspect_ratio(current_w, current_h)

    # Determine which dimension is the constraint
    if target_w / current_ratio <= target_h:
        # Width is the constraint
        final_w = target_w
        final_h = int(target_w / current_ratio)
    else:
        # Height is the constraint
        final_h = target_h
        final_w = int(target_h * current_ratio)

    return (final_w, final_h)


def get_image_info(filepath: Path) -> dict:
    """
    Get image information.

    Args:
        filepath: Path to image file

    Returns:
        Dictionary with image info (width, height, format, mode, size_bytes)
    """
    try:
        with Image.open(filepath) as img:
            return {
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'mode': img.mode,
                'size_bytes': filepath.stat().st_size,
            }
    except Exception as e:
        return {
            'error': str(e)
        }
