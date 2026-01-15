"""Compression engine with improved binary search algorithm."""

import math
import time
from io import BytesIO
from typing import Optional, Dict, Tuple

from PIL import Image

from .result import CompressionResult, EncoderOptions
from .encoders import (
    BaseEncoder,
    get_encoder,
    calculate_ssim_inmemory,
)


# Constants
EARLY_EXIT_TOLERANCE = 0.05  # Exit if within 5% of target
MAX_ITERATIONS = 12  # Maximum binary search iterations
DIMENSION_SAFETY_MARGIN = 0.9  # Conservative margin for dimension calculations


class CompressionEngine:
    """Core compression engine with caching and efficient binary search.

    Features:
    - Cached encoding (avoids re-encoding same quality)
    - Early exit when close to target
    - In-memory SSIM calculation
    - Dimension suggestion for unreachable targets
    """

    def __init__(self, encoder: BaseEncoder):
        """Initialize engine with specific encoder.

        Args:
            encoder: Format-specific encoder to use
        """
        self.encoder = encoder
        self._cache: Dict[int, Tuple[bytes, int]] = {}

    def clear_cache(self):
        """Clear the encoding cache."""
        self._cache.clear()

    def compress_to_target(
        self,
        image: Image.Image,
        target_bytes: int,
        min_quality: int = 60,
        max_quality: int = 100,
        options: Optional[EncoderOptions] = None,
        calculate_ssim: bool = False,
    ) -> CompressionResult:
        """Compress image to target size using adaptive binary search.

        Args:
            image: PIL Image to compress
            target_bytes: Target file size in bytes
            min_quality: Minimum acceptable quality
            max_quality: Maximum quality to try
            options: Base encoding options (quality will be overridden)
            calculate_ssim: Whether to calculate SSIM score

        Returns:
            CompressionResult with compression outcome and fallback info
        """
        start_time = time.time()
        self.clear_cache()

        if options is None:
            options = EncoderOptions()

        dimensions = image.size

        # First, check if image is already under target at max quality
        max_options = EncoderOptions(
            quality=max_quality,
            chroma_subsampling=options.chroma_subsampling,
            progressive=options.progressive,
            use_mozjpeg=options.use_mozjpeg,
            effort=options.effort,
        )
        max_bytes, max_size = self._encode_cached(image, max_quality, max_options)

        if max_size <= target_bytes:
            # Already under target at max quality
            ssim = None
            if calculate_ssim:
                compressed_img = Image.open(BytesIO(max_bytes))
                ssim = calculate_ssim_inmemory(image, compressed_img)

            return CompressionResult(
                success=True,
                encoded_bytes=max_bytes,
                final_size_bytes=max_size,
                quality_used=max_quality,
                format_used=self.encoder.format_name,
                dimensions=dimensions,
                ssim_score=ssim,
                encoding_time_ms=int((time.time() - start_time) * 1000),
                iterations=1,
                message=f"Compressed to {max_size / (1024*1024):.2f} MB at quality {max_quality}",
            )

        # Binary search for optimal quality
        best_quality, best_bytes, best_size, iterations = self._binary_search(
            image, target_bytes, min_quality, max_quality, options
        )

        success = best_size <= target_bytes

        # Calculate SSIM if requested
        ssim = None
        if calculate_ssim:
            compressed_img = Image.open(BytesIO(best_bytes))
            ssim = calculate_ssim_inmemory(image, compressed_img)

        # Calculate suggestions if target not met
        suggested_dims = None
        if not success:
            suggested_dims = self._calculate_suggested_dimensions(
                image, target_bytes, best_size
            )

        encoding_time = int((time.time() - start_time) * 1000)

        return CompressionResult(
            success=success,
            encoded_bytes=best_bytes,
            final_size_bytes=best_size,
            quality_used=best_quality,
            format_used=self.encoder.format_name,
            dimensions=dimensions,
            ssim_score=ssim,
            encoding_time_ms=encoding_time,
            iterations=iterations,
            suggested_dimensions=suggested_dims,
            message=self._build_message(success, best_size, target_bytes, best_quality),
        )

    def compress_at_quality(
        self,
        image: Image.Image,
        options: EncoderOptions,
        calculate_ssim: bool = False,
    ) -> CompressionResult:
        """Compress at specific quality without size targeting.

        Args:
            image: PIL Image to compress
            options: Encoding options including quality
            calculate_ssim: Whether to calculate SSIM score

        Returns:
            CompressionResult with compression outcome
        """
        start_time = time.time()

        encoded_bytes = self.encoder.encode(image, options)
        size = len(encoded_bytes)

        ssim = None
        if calculate_ssim:
            compressed_img = Image.open(BytesIO(encoded_bytes))
            ssim = calculate_ssim_inmemory(image, compressed_img)

        return CompressionResult(
            success=True,
            encoded_bytes=encoded_bytes,
            final_size_bytes=size,
            quality_used=options.quality,
            format_used=self.encoder.format_name,
            dimensions=image.size,
            ssim_score=ssim,
            encoding_time_ms=int((time.time() - start_time) * 1000),
            iterations=1,
            message=f"Encoded at quality {options.quality}: {size / (1024*1024):.2f} MB",
        )

    def estimate_size_at_quality(
        self,
        image: Image.Image,
        quality: int,
        options: Optional[EncoderOptions] = None
    ) -> int:
        """Estimate file size at given quality.

        Uses cache if available.

        Args:
            image: PIL Image
            quality: Quality level
            options: Encoding options

        Returns:
            Estimated size in bytes
        """
        if options is None:
            options = EncoderOptions(quality=quality)
        else:
            options = EncoderOptions(
                quality=quality,
                chroma_subsampling=options.chroma_subsampling,
                progressive=options.progressive,
                use_mozjpeg=options.use_mozjpeg,
                effort=options.effort,
            )

        _, size = self._encode_cached(image, quality, options)
        return size

    def _encode_cached(
        self,
        image: Image.Image,
        quality: int,
        options: EncoderOptions
    ) -> Tuple[bytes, int]:
        """Encode with caching to avoid redundant encoding.

        Args:
            image: PIL Image
            quality: Quality level
            options: Encoding options

        Returns:
            Tuple of (encoded_bytes, size_in_bytes)
        """
        if quality in self._cache:
            return self._cache[quality]

        # Update options with quality
        encode_options = EncoderOptions(
            quality=quality,
            chroma_subsampling=options.chroma_subsampling,
            progressive=options.progressive,
            use_mozjpeg=options.use_mozjpeg,
            effort=options.effort,
        )

        encoded = self.encoder.encode(image, encode_options)
        size = len(encoded)
        self._cache[quality] = (encoded, size)
        return encoded, size

    def _binary_search(
        self,
        image: Image.Image,
        target_bytes: int,
        min_quality: int,
        max_quality: int,
        options: EncoderOptions,
    ) -> Tuple[int, bytes, int, int]:
        """Adaptive binary search for optimal quality.

        Features:
        - Early exit when within tolerance
        - Caches all encoded results
        - Returns best result found

        Args:
            image: PIL Image
            target_bytes: Target size in bytes
            min_quality: Minimum quality bound
            max_quality: Maximum quality bound
            options: Base encoding options

        Returns:
            Tuple of (quality, bytes, size, iterations)
        """
        low = min_quality
        high = max_quality

        best_quality = min_quality
        best_bytes = b''
        best_size = float('inf')

        iterations = 0

        while low <= high and iterations < MAX_ITERATIONS:
            iterations += 1
            mid = (low + high) // 2

            encoded, size = self._encode_cached(image, mid, options)

            if size <= target_bytes:
                # Under target - this is valid, try higher quality
                best_quality = mid
                best_bytes = encoded
                best_size = size

                # Check early exit (within tolerance)
                if size >= target_bytes * (1 - EARLY_EXIT_TOLERANCE):
                    break

                low = mid + 1
            else:
                # Over target - try lower quality
                high = mid - 1

        # If we never found a valid result, use minimum quality
        if best_size > target_bytes:
            best_bytes, best_size = self._encode_cached(image, min_quality, options)
            best_quality = min_quality

        # Fine-tune: check quality levels just above best
        if best_size < target_bytes:
            for test_q in range(best_quality + 1, min(best_quality + 4, max_quality + 1)):
                test_bytes, test_size = self._encode_cached(image, test_q, options)
                iterations += 1
                if test_size <= target_bytes:
                    best_quality = test_q
                    best_bytes = test_bytes
                    best_size = test_size
                else:
                    break

        return best_quality, best_bytes, best_size, iterations

    def _calculate_suggested_dimensions(
        self,
        image: Image.Image,
        target_bytes: int,
        current_size: int,
    ) -> Tuple[int, int]:
        """Calculate dimensions needed to achieve target size.

        Uses conservative estimate with safety margin.

        Args:
            image: Original image
            target_bytes: Target size in bytes
            current_size: Current compressed size at min quality

        Returns:
            Suggested (width, height) tuple
        """
        width, height = image.size

        # Calculate scale factor needed
        # Size scales approximately with pixel count
        scale = math.sqrt(target_bytes / current_size) * DIMENSION_SAFETY_MARGIN

        new_width = max(100, int(width * scale))
        new_height = max(100, int(height * scale))

        # Round to multiples of 8 (JPEG block size)
        new_width = (new_width // 8) * 8
        new_height = (new_height // 8) * 8

        return (new_width, new_height)

    def _build_message(
        self,
        success: bool,
        final_size: int,
        target_bytes: int,
        quality: int
    ) -> str:
        """Build human-readable result message."""
        size_mb = final_size / (1024 * 1024)
        target_mb = target_bytes / (1024 * 1024)

        if success:
            return f"Compressed to {size_mb:.2f} MB at quality {quality}"
        else:
            return (
                f"Could not reach target {target_mb:.2f} MB. "
                f"Best: {size_mb:.2f} MB at minimum quality {quality}"
            )
