"""Format advisor for suggesting optimal image formats.

Analyzes image characteristics and compression targets to recommend
the best format for the job.
"""

from dataclasses import dataclass
from typing import Optional, List

from PIL import Image

from .encoders import get_encoder, get_available_formats, AVIF_AVAILABLE
from .result import EncoderOptions


@dataclass
class FormatSuggestion:
    """Suggestion for an alternative format.

    Attributes:
        format_name: Suggested format (AVIF, WEBP, JPEG)
        estimated_size: Estimated file size in bytes
        estimated_quality: Quality level for the estimate
        reason: Human-readable explanation
        can_achieve_target: Whether this format can hit the target
    """
    format_name: str
    estimated_size: int
    estimated_quality: int
    reason: str
    can_achieve_target: bool

    @property
    def estimated_size_mb(self) -> float:
        """Get estimated size in megabytes."""
        return self.estimated_size / (1024 * 1024)


class FormatAdvisor:
    """Analyzes images and suggests optimal formats.

    Considers:
    - Image characteristics (size, transparency, content type)
    - Target file size requirements
    - Available encoders
    - Format compression efficiency
    """

    # Typical compression ratios relative to JPEG at same quality
    # Based on empirical testing with photographic content
    COMPRESSION_RATIOS = {
        'AVIF': 0.5,   # AVIF typically 50% smaller than JPEG
        'WEBP': 0.75,  # WebP typically 25% smaller than JPEG
        'JPEG': 1.0,   # Baseline
        'PNG': 3.0,    # PNG much larger for photos (lossless)
    }

    # Format descriptions for UI
    FORMAT_DESCRIPTIONS = {
        'AVIF': "Best compression, modern browsers",
        'WEBP': "Good compression, wide support",
        'JPEG': "Universal compatibility",
        'PNG': "Lossless, large files",
    }

    def __init__(self, min_quality: int = 60):
        """Initialize advisor.

        Args:
            min_quality: Minimum quality to consider for estimates
        """
        self.min_quality = min_quality

    def suggest_format(
        self,
        image: Image.Image,
        target_bytes: int,
        current_format: str,
        current_min_size: Optional[int] = None,
    ) -> Optional[FormatSuggestion]:
        """Suggest better format if current can't achieve target.

        Args:
            image: Source image
            target_bytes: Target file size in bytes
            current_format: Currently selected format
            current_min_size: Size at min quality with current format

        Returns:
            FormatSuggestion if a better option exists, None otherwise
        """
        if current_min_size is not None and current_min_size <= target_bytes:
            return None  # Current format can achieve target

        suggestions = self.get_all_suggestions(image, target_bytes)

        # Filter out current format and find best alternative
        alternatives = [s for s in suggestions if s.format_name != current_format]

        # Return best option that can achieve target, or best overall
        achievable = [s for s in alternatives if s.can_achieve_target]
        if achievable:
            return min(achievable, key=lambda s: s.estimated_size)

        # No format can achieve target - return smallest
        if alternatives:
            return min(alternatives, key=lambda s: s.estimated_size)

        return None

    def get_all_suggestions(
        self,
        image: Image.Image,
        target_bytes: int,
    ) -> List[FormatSuggestion]:
        """Get suggestions for all available formats.

        Args:
            image: Source image
            target_bytes: Target file size in bytes

        Returns:
            List of FormatSuggestion for each available format
        """
        suggestions = []
        has_transparency = self._has_transparency(image)

        for format_name in get_available_formats():
            encoder = get_encoder(format_name)
            if encoder is None:
                continue

            # Skip non-transparency formats for transparent images
            if has_transparency and not encoder.supports_transparency:
                continue

            # Estimate size at minimum quality
            estimated_size = self._estimate_size(image, format_name)
            can_achieve = estimated_size <= target_bytes

            suggestion = FormatSuggestion(
                format_name=format_name,
                estimated_size=estimated_size,
                estimated_quality=self.min_quality,
                reason=self.FORMAT_DESCRIPTIONS.get(format_name, ""),
                can_achieve_target=can_achieve,
            )
            suggestions.append(suggestion)

        # Sort by estimated size (smallest first)
        suggestions.sort(key=lambda s: s.estimated_size)
        return suggestions

    def _estimate_size(self, image: Image.Image, format_name: str) -> int:
        """Estimate file size for format at minimum quality.

        Uses actual encoding for accuracy.

        Args:
            image: Source image
            format_name: Format to estimate

        Returns:
            Estimated size in bytes
        """
        encoder = get_encoder(format_name)
        if encoder is None:
            return float('inf')

        options = EncoderOptions(
            quality=self.min_quality,
            chroma_subsampling=2,  # Maximum compression
            use_mozjpeg=True,
        )

        try:
            encoded = encoder.encode(image, options)
            return len(encoded)
        except Exception:
            return float('inf')

    def _has_transparency(self, image: Image.Image) -> bool:
        """Check if image has transparency.

        Args:
            image: PIL Image

        Returns:
            True if image has alpha channel or transparency info
        """
        if image.mode in ('RGBA', 'LA', 'PA'):
            return True
        if image.mode == 'P' and 'transparency' in image.info:
            return True
        return False

    def get_format_comparison(
        self,
        image: Image.Image,
        quality: int = 85,
    ) -> List[dict]:
        """Compare all formats at same quality level.

        Useful for showing users a comparison table.

        Args:
            image: Source image
            quality: Quality level to compare at

        Returns:
            List of dicts with format info and sizes
        """
        comparisons = []
        has_transparency = self._has_transparency(image)

        for format_name in get_available_formats():
            encoder = get_encoder(format_name)
            if encoder is None:
                continue

            # Skip non-transparency formats for transparent images
            if has_transparency and not encoder.supports_transparency:
                continue

            options = EncoderOptions(
                quality=quality,
                chroma_subsampling=2,
                use_mozjpeg=True,
            )

            try:
                encoded = encoder.encode(image, options)
                size = len(encoded)
            except Exception:
                continue

            comparisons.append({
                'format': format_name,
                'size_bytes': size,
                'size_mb': size / (1024 * 1024),
                'description': self.FORMAT_DESCRIPTIONS.get(format_name, ""),
                'supports_transparency': encoder.supports_transparency,
            })

        # Sort by size
        comparisons.sort(key=lambda c: c['size_bytes'])
        return comparisons

    def recommend_format_for_use_case(
        self,
        use_case: str,
        has_transparency: bool = False,
    ) -> str:
        """Recommend format based on use case.

        Args:
            use_case: One of "web", "social", "archive", "universal"
            has_transparency: Whether image needs transparency

        Returns:
            Recommended format name
        """
        if has_transparency:
            # Transparency support required
            if AVIF_AVAILABLE:
                return 'AVIF'
            return 'WEBP'

        recommendations = {
            'web': 'AVIF' if AVIF_AVAILABLE else 'WEBP',
            'social': 'JPEG',  # Most compatible
            'archive': 'PNG',  # Lossless
            'universal': 'JPEG',  # Maximum compatibility
            'smallest': 'AVIF' if AVIF_AVAILABLE else 'WEBP',
        }

        return recommendations.get(use_case, 'JPEG')
