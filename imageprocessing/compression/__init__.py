"""Image compression package with format-specific encoders and strategies."""

from .result import CompressionResult
from .engine import CompressionEngine
from .encoders import (
    AVIF_AVAILABLE,
    MOZJPEG_AVAILABLE,
    SSIM_AVAILABLE,
    get_encoder,
    get_available_formats,
    calculate_ssim_inmemory,
)
from .strategy import QuickStrategy, AdvancedStrategy
from .format_advisor import FormatAdvisor

__all__ = [
    'CompressionResult',
    'CompressionEngine',
    'QuickStrategy',
    'AdvancedStrategy',
    'FormatAdvisor',
    'AVIF_AVAILABLE',
    'MOZJPEG_AVAILABLE',
    'SSIM_AVAILABLE',
    'get_encoder',
    'get_available_formats',
    'calculate_ssim_inmemory',
]
