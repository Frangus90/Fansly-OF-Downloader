"""Image processing package for bulk cropping and resizing"""

from .crop import crop_image, resize_image, add_padding, save_image
from .processor import ImageProcessor, ImageTask
from .presets import (
    load_presets,
    save_presets,
    add_preset,
    remove_preset,
    get_preset_names,
    get_preset_aspect_ratio,
    format_aspect_ratio,
)
from .watermark_crop import WatermarkDetector, load_blacklist, save_blacklist

__all__ = [
    'crop_image',
    'resize_image',
    'add_padding',
    'save_image',
    'ImageProcessor',
    'ImageTask',
    'load_presets',
    'save_presets',
    'add_preset',
    'remove_preset',
    'get_preset_names',
    'get_preset_aspect_ratio',
    'format_aspect_ratio',
    'WatermarkDetector',
    'load_blacklist',
    'save_blacklist',
]
