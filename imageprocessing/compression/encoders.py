"""Format-specific image encoders with optional dependency support.

Provides encoders for JPEG, WebP, and AVIF with graceful degradation
when optional dependencies (MozJPEG, pillow-avif-plugin, scikit-image)
are not installed.
"""

from abc import ABC, abstractmethod
from io import BytesIO
from typing import Optional, Dict, Tuple, List, Protocol
import time

import numpy as np
from PIL import Image

from .result import EncoderOptions


# Optional dependency checks
SSIM_AVAILABLE = False
try:
    from skimage.metrics import structural_similarity
    SSIM_AVAILABLE = True
except ImportError:
    pass

MOZJPEG_AVAILABLE = False
try:
    import mozjpeg_lossless_optimization
    MOZJPEG_AVAILABLE = True
except ImportError:
    pass

AVIF_AVAILABLE = False
try:
    import pillow_avif  # noqa: F401
    AVIF_AVAILABLE = True
except ImportError:
    pass


# Human-readable labels for chroma subsampling
CHROMA_LABELS = {
    0: "Best Color Quality",
    1: "Balanced",
    2: "Smallest File Size",
}


class BaseEncoder(ABC):
    """Abstract base class for format-specific encoders."""

    format_name: str
    supports_quality: bool = True
    supports_transparency: bool = False
    file_extension: str

    @abstractmethod
    def encode(
        self,
        image: Image.Image,
        options: EncoderOptions
    ) -> bytes:
        """Encode image to bytes.

        Args:
            image: PIL Image to encode
            options: Encoding options

        Returns:
            Encoded image bytes
        """
        pass

    def get_quality_range(self) -> Tuple[int, int]:
        """Get valid quality range for this format.

        Returns:
            Tuple of (min_quality, max_quality)
        """
        return (1, 100)

    def prepare_image(self, image: Image.Image) -> Image.Image:
        """Prepare image for encoding (mode conversion, etc).

        Args:
            image: Source image

        Returns:
            Image ready for encoding
        """
        return image


class JpegEncoder(BaseEncoder):
    """JPEG encoder with MozJPEG optimization support."""

    format_name = "JPEG"
    supports_quality = True
    supports_transparency = False
    file_extension = ".jpg"

    def encode(self, image: Image.Image, options: EncoderOptions) -> bytes:
        """Encode image as JPEG."""
        # Prepare image (convert to RGB if needed)
        image = self.prepare_image(image)

        # Encode to buffer
        buffer = BytesIO()
        image.save(
            buffer,
            format='JPEG',
            quality=options.quality,
            optimize=True,
            progressive=options.progressive,
            subsampling=options.chroma_subsampling,
        )
        encoded_bytes = buffer.getvalue()

        # Apply MozJPEG lossless optimization if available and requested
        if options.use_mozjpeg and MOZJPEG_AVAILABLE:
            try:
                encoded_bytes = mozjpeg_lossless_optimization.optimize(encoded_bytes)
            except Exception:
                pass  # Fall back to unoptimized

        return encoded_bytes

    def prepare_image(self, image: Image.Image) -> Image.Image:
        """Convert to RGB for JPEG."""
        if image.mode == 'RGBA':
            # Composite on white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            return background
        elif image.mode == 'P':
            # Convert palette mode
            return image.convert('RGB')
        elif image.mode != 'RGB':
            return image.convert('RGB')
        return image


class WebpEncoder(BaseEncoder):
    """WebP encoder with lossy and lossless support."""

    format_name = "WEBP"
    supports_quality = True
    supports_transparency = True
    file_extension = ".webp"

    def encode(self, image: Image.Image, options: EncoderOptions) -> bytes:
        """Encode image as WebP."""
        image = self.prepare_image(image)

        buffer = BytesIO()
        image.save(
            buffer,
            format='WEBP',
            quality=options.quality,
            method=min(options.effort, 6),  # WebP method 0-6
        )
        return buffer.getvalue()

    def prepare_image(self, image: Image.Image) -> Image.Image:
        """Prepare image for WebP encoding."""
        if image.mode == 'P':
            # Check if palette has transparency
            if 'transparency' in image.info:
                return image.convert('RGBA')
            return image.convert('RGB')
        elif image.mode not in ('RGB', 'RGBA'):
            return image.convert('RGB')
        return image


class AvifEncoder(BaseEncoder):
    """AVIF encoder using pillow-avif-plugin."""

    format_name = "AVIF"
    supports_quality = True
    supports_transparency = True
    file_extension = ".avif"

    def encode(self, image: Image.Image, options: EncoderOptions) -> bytes:
        """Encode image as AVIF."""
        if not AVIF_AVAILABLE:
            raise RuntimeError("AVIF encoding requires pillow-avif-plugin")

        image = self.prepare_image(image)

        buffer = BytesIO()
        # AVIF quality is inverted (0=best, 63=worst in some implementations)
        # pillow-avif-plugin uses 0-100 like other formats
        image.save(
            buffer,
            format='AVIF',
            quality=options.quality,
            speed=10 - options.effort,  # Convert effort to speed (0=slowest/best)
        )
        return buffer.getvalue()

    def prepare_image(self, image: Image.Image) -> Image.Image:
        """Prepare image for AVIF encoding."""
        if image.mode == 'P':
            if 'transparency' in image.info:
                return image.convert('RGBA')
            return image.convert('RGB')
        elif image.mode not in ('RGB', 'RGBA'):
            return image.convert('RGB')
        return image


class PngEncoder(BaseEncoder):
    """PNG encoder (lossless, no quality setting)."""

    format_name = "PNG"
    supports_quality = False
    supports_transparency = True
    file_extension = ".png"

    def encode(self, image: Image.Image, options: EncoderOptions) -> bytes:
        """Encode image as PNG."""
        buffer = BytesIO()
        image.save(buffer, format='PNG', optimize=True)
        return buffer.getvalue()

    def get_quality_range(self) -> Tuple[int, int]:
        """PNG doesn't use quality."""
        return (100, 100)


# Encoder registry
_ENCODERS: Dict[str, BaseEncoder] = {
    'JPEG': JpegEncoder(),
    'WEBP': WebpEncoder(),
    'PNG': PngEncoder(),
}

# Register AVIF if available
if AVIF_AVAILABLE:
    _ENCODERS['AVIF'] = AvifEncoder()


def get_encoder(format_name: str) -> Optional[BaseEncoder]:
    """Get encoder for format.

    Args:
        format_name: Format name (JPEG, WEBP, AVIF, PNG)

    Returns:
        Encoder instance or None if format not supported
    """
    return _ENCODERS.get(format_name.upper())


def get_available_formats() -> List[str]:
    """Get list of available format names.

    Returns:
        List of format names that can be used
    """
    return list(_ENCODERS.keys())


def calculate_ssim_inmemory(
    original: Image.Image,
    compressed: Image.Image
) -> Optional[float]:
    """Calculate SSIM between two images in memory.

    No disk I/O - works directly with PIL Images.

    Args:
        original: Original PIL Image
        compressed: Compressed PIL Image

    Returns:
        SSIM score (0.0 to 1.0) or None if scikit-image unavailable
    """
    if not SSIM_AVAILABLE:
        return None

    # Ensure same size
    if original.size != compressed.size:
        compressed = compressed.resize(original.size, Image.Resampling.LANCZOS)

    # Convert to same mode
    if original.mode != compressed.mode:
        # Prefer RGB for comparison
        original = original.convert('RGB')
        compressed = compressed.convert('RGB')
    elif original.mode not in ('RGB', 'L'):
        original = original.convert('RGB')
        compressed = compressed.convert('RGB')

    # Convert to numpy arrays
    orig_array = np.array(original)
    comp_array = np.array(compressed)

    # Handle grayscale vs color
    if len(orig_array.shape) == 2:
        return structural_similarity(orig_array, comp_array, data_range=255)
    else:
        return structural_similarity(
            orig_array,
            comp_array,
            data_range=255,
            channel_axis=-1
        )


def get_encoder_capabilities() -> dict:
    """Get available encoder features.

    Returns:
        Dict with boolean flags for each feature
    """
    return {
        'ssim_validation': SSIM_AVAILABLE,
        'mozjpeg_optimization': MOZJPEG_AVAILABLE,
        'avif_encoding': AVIF_AVAILABLE,
        'formats': get_available_formats(),
    }
