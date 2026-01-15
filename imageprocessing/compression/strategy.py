"""Compression strategies for Quick and Advanced modes.

Quick mode: User sets target MB, system auto-optimizes format and quality.
Advanced mode: User controls all settings manually.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List

from PIL import Image

from .result import CompressionResult, EncoderOptions
from .engine import CompressionEngine
from .encoders import get_encoder, get_available_formats, AVIF_AVAILABLE


@dataclass
class StrategyConfig:
    """Configuration for compression strategy.

    Attributes:
        target_mb: Target file size in megabytes (None = no target)
        format: Output format (JPEG, WEBP, AVIF, or AUTO)
        quality: Manual quality setting (1-100)
        min_quality: Quality floor for size-based compression
        chroma_subsampling: JPEG chroma mode (0=4:4:4, 1=4:2:2, 2=4:2:0)
        progressive: Enable progressive encoding
        use_mozjpeg: Apply MozJPEG optimization
        calculate_ssim: Calculate quality score
    """
    target_mb: Optional[float] = None
    format: str = "JPEG"
    quality: int = 85
    min_quality: int = 60
    chroma_subsampling: int = 2
    progressive: bool = False
    use_mozjpeg: bool = True
    calculate_ssim: bool = False

    @property
    def target_bytes(self) -> Optional[int]:
        """Convert target_mb to bytes."""
        if self.target_mb is None:
            return None
        return int(self.target_mb * 1024 * 1024)


class CompressionStrategy(ABC):
    """Abstract base class for compression strategies."""

    @abstractmethod
    def compress(self, image: Image.Image) -> CompressionResult:
        """Compress image according to strategy.

        Args:
            image: PIL Image to compress

        Returns:
            CompressionResult with outcome and metadata
        """
        pass

    @abstractmethod
    def get_config(self) -> StrategyConfig:
        """Get current strategy configuration."""
        pass


class QuickStrategy(CompressionStrategy):
    """Quick mode: target size with automatic format selection.

    Tries formats in order of quality preservation (least aggressive first):
    1. JPEG (preserves most quality, universal support)
    2. WebP (good compression, wide support)
    3. AVIF (best compression, if available)

    This order ensures maximum quality when source is already under target.
    Only uses more aggressive formats when needed to hit target.
    """

    # Format priority (quality preservation first, compression last)
    FORMAT_PRIORITY = ['JPEG', 'WEBP', 'AVIF']

    def __init__(
        self,
        target_mb: float,
        auto_format: bool = True,
        preferred_format: str = "AUTO",
        min_quality: int = 60,
        calculate_ssim: bool = False,
    ):
        """Initialize Quick strategy.

        Args:
            target_mb: Target file size in megabytes
            auto_format: If True, try multiple formats to hit target
            preferred_format: Preferred format (AUTO = try all)
            min_quality: Minimum acceptable quality
            calculate_ssim: Whether to calculate SSIM score
        """
        self.target_mb = target_mb
        self.auto_format = auto_format and preferred_format == "AUTO"
        self.preferred_format = preferred_format
        self.min_quality = min_quality
        self.calculate_ssim = calculate_ssim

    def compress(self, image: Image.Image) -> CompressionResult:
        """Compress with automatic optimization."""
        target_bytes = int(self.target_mb * 1024 * 1024)

        # Determine formats to try
        if self.auto_format:
            formats_to_try = [
                f for f in self.FORMAT_PRIORITY
                if f in get_available_formats()
            ]
        else:
            formats_to_try = [self.preferred_format]

        best_result: Optional[CompressionResult] = None

        for format_name in formats_to_try:
            encoder = get_encoder(format_name)
            if encoder is None:
                continue

            engine = CompressionEngine(encoder)
            options = EncoderOptions(
                quality=100,  # Start at max, engine will search down
                chroma_subsampling=2,  # Smallest for Quick mode
                progressive=False,
                use_mozjpeg=True,
            )

            result = engine.compress_to_target(
                image,
                target_bytes,
                min_quality=self.min_quality,
                options=options,
                calculate_ssim=self.calculate_ssim,
            )

            if result.success:
                return result

            # Track best failure for fallback info
            if best_result is None or result.final_size_bytes < best_result.final_size_bytes:
                best_result = result

        # None succeeded - return best attempt with suggestions
        if best_result is not None:
            # Add format suggestion if we haven't tried all formats
            if not self.auto_format:
                best_result = self._add_format_suggestion(
                    image, target_bytes, best_result
                )
            return best_result

        # Fallback: return basic JPEG result
        encoder = get_encoder('JPEG')
        engine = CompressionEngine(encoder)
        return engine.compress_to_target(
            image, target_bytes, min_quality=self.min_quality
        )

    # More aggressive formats for suggestions when current format fails
    AGGRESSIVE_FORMATS = ['WEBP', 'AVIF']

    def _add_format_suggestion(
        self,
        image: Image.Image,
        target_bytes: int,
        result: CompressionResult
    ) -> CompressionResult:
        """Check if alternative format could achieve target."""
        for format_name in self.AGGRESSIVE_FORMATS:
            if format_name == result.format_used:
                continue
            if format_name not in get_available_formats():
                continue

            encoder = get_encoder(format_name)
            engine = CompressionEngine(encoder)
            options = EncoderOptions(quality=self.min_quality)

            test_result = engine.compress_at_quality(image, options)

            if test_result.final_size_bytes <= target_bytes:
                result.suggested_format = format_name
                result.suggested_format_size = test_result.final_size_bytes
                break

        return result

    def get_config(self) -> StrategyConfig:
        """Get current configuration."""
        return StrategyConfig(
            target_mb=self.target_mb,
            format="AUTO" if self.auto_format else self.preferred_format,
            quality=100,
            min_quality=self.min_quality,
            calculate_ssim=self.calculate_ssim,
        )


class AdvancedStrategy(CompressionStrategy):
    """Advanced mode: full manual control over all settings.

    User specifies exact format, quality, and optional size target.
    """

    def __init__(
        self,
        format: str,
        quality: int = 85,
        target_mb: Optional[float] = None,
        min_quality: int = 60,
        chroma_subsampling: int = 2,
        progressive: bool = False,
        use_mozjpeg: bool = True,
        calculate_ssim: bool = False,
    ):
        """Initialize Advanced strategy.

        Args:
            format: Output format (JPEG, WEBP, AVIF)
            quality: Compression quality (1-100)
            target_mb: Optional target size (None = use quality directly)
            min_quality: Quality floor when targeting size
            chroma_subsampling: JPEG chroma mode
            progressive: Enable progressive encoding
            use_mozjpeg: Apply MozJPEG optimization
            calculate_ssim: Calculate quality score
        """
        self.format = format.upper()
        self.quality = quality
        self.target_mb = target_mb
        self.min_quality = min_quality
        self.chroma_subsampling = chroma_subsampling
        self.progressive = progressive
        self.use_mozjpeg = use_mozjpeg
        self.calculate_ssim = calculate_ssim

    def compress(self, image: Image.Image) -> CompressionResult:
        """Compress with user-specified settings."""
        encoder = get_encoder(self.format)
        if encoder is None:
            raise ValueError(f"Unsupported format: {self.format}")

        engine = CompressionEngine(encoder)
        options = EncoderOptions(
            quality=self.quality,
            chroma_subsampling=self.chroma_subsampling,
            progressive=self.progressive,
            use_mozjpeg=self.use_mozjpeg,
        )

        if self.target_mb is not None:
            # Size-based compression
            target_bytes = int(self.target_mb * 1024 * 1024)
            result = engine.compress_to_target(
                image,
                target_bytes,
                min_quality=self.min_quality,
                max_quality=self.quality,
                options=options,
                calculate_ssim=self.calculate_ssim,
            )

            # Add format suggestion if target not met
            if not result.success:
                result = self._add_format_suggestion(image, target_bytes, result)

            return result
        else:
            # Quality-based compression
            return engine.compress_at_quality(
                image, options, calculate_ssim=self.calculate_ssim
            )

    def _add_format_suggestion(
        self,
        image: Image.Image,
        target_bytes: int,
        result: CompressionResult
    ) -> CompressionResult:
        """Check if alternative format could achieve target."""
        for format_name in ['AVIF', 'WEBP', 'JPEG']:
            if format_name == self.format:
                continue
            if format_name not in get_available_formats():
                continue

            encoder = get_encoder(format_name)
            engine = CompressionEngine(encoder)
            options = EncoderOptions(quality=self.min_quality)

            test_result = engine.compress_at_quality(image, options)

            if test_result.final_size_bytes <= target_bytes:
                result.suggested_format = format_name
                result.suggested_format_size = test_result.final_size_bytes
                break

        return result

    def get_config(self) -> StrategyConfig:
        """Get current configuration."""
        return StrategyConfig(
            target_mb=self.target_mb,
            format=self.format,
            quality=self.quality,
            min_quality=self.min_quality,
            chroma_subsampling=self.chroma_subsampling,
            progressive=self.progressive,
            use_mozjpeg=self.use_mozjpeg,
            calculate_ssim=self.calculate_ssim,
        )


def create_strategy(
    mode: str,
    target_mb: Optional[float] = None,
    format: str = "JPEG",
    quality: int = 85,
    **kwargs
) -> CompressionStrategy:
    """Factory function to create compression strategy.

    Args:
        mode: "quick" or "advanced"
        target_mb: Target size in MB (required for quick mode)
        format: Output format
        quality: Quality level
        **kwargs: Additional strategy-specific options

    Returns:
        Configured CompressionStrategy
    """
    if mode.lower() == "quick":
        if target_mb is None:
            raise ValueError("Quick mode requires target_mb")
        return QuickStrategy(
            target_mb=target_mb,
            auto_format=format.upper() == "AUTO",
            preferred_format=format,
            **kwargs
        )
    elif mode.lower() == "advanced":
        return AdvancedStrategy(
            format=format,
            quality=quality,
            target_mb=target_mb,
            **kwargs
        )
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'quick' or 'advanced'")
