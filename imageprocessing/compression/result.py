"""Compression result dataclass with rich feedback."""

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class CompressionResult:
    """Result of a compression operation with detailed feedback.

    Attributes:
        success: True if target size was achieved
        encoded_bytes: The compressed image data
        final_size_bytes: Actual size of compressed data
        quality_used: Quality level used for compression
        format_used: Format name (JPEG, WEBP, AVIF)
        dimensions: Image dimensions (width, height)
        ssim_score: Structural similarity score (0-1) if calculated
        encoding_time_ms: Time taken to encode in milliseconds
        iterations: Number of binary search iterations

        # Fallback info (populated when success=False)
        suggested_dimensions: Dimensions that would achieve target
        suggested_format: Alternative format that could achieve target
        suggested_format_size: Estimated size with suggested format
        message: Human-readable status message
    """
    success: bool
    encoded_bytes: bytes
    final_size_bytes: int
    quality_used: int
    format_used: str
    dimensions: Tuple[int, int]

    # Optional quality metrics
    ssim_score: Optional[float] = None
    encoding_time_ms: int = 0
    iterations: int = 0

    # Fallback suggestions (when success=False)
    suggested_dimensions: Optional[Tuple[int, int]] = None
    suggested_format: Optional[str] = None
    suggested_format_size: Optional[int] = None

    # Human-readable message
    message: str = ""

    @property
    def final_size_mb(self) -> float:
        """Get final size in megabytes."""
        return self.final_size_bytes / (1024 * 1024)

    @property
    def suggested_format_size_mb(self) -> Optional[float]:
        """Get suggested format size in megabytes."""
        if self.suggested_format_size is None:
            return None
        return self.suggested_format_size / (1024 * 1024)

    def has_fallback_options(self) -> bool:
        """Check if any fallback options are available."""
        return (
            self.suggested_dimensions is not None or
            self.suggested_format is not None
        )


@dataclass
class EncoderOptions:
    """Options for format-specific encoding.

    Attributes:
        quality: Compression quality (1-100)
        chroma_subsampling: JPEG chroma mode (0=4:4:4, 1=4:2:2, 2=4:2:0)
        progressive: Enable progressive encoding
        use_mozjpeg: Apply MozJPEG lossless optimization
        effort: Encoder effort level (format-specific)
    """
    quality: int = 85
    chroma_subsampling: int = 2
    progressive: bool = False
    use_mozjpeg: bool = True
    effort: int = 4  # AVIF/WebP effort (0-10, higher = slower/better)

    def __post_init__(self):
        """Validate options."""
        if not 1 <= self.quality <= 100:
            raise ValueError(f"quality must be 1-100, got {self.quality}")
        if self.chroma_subsampling not in (0, 1, 2):
            raise ValueError(f"chroma_subsampling must be 0, 1, or 2")
        if not 0 <= self.effort <= 10:
            raise ValueError(f"effort must be 0-10, got {self.effort}")
