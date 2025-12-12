"""Core image cropping and manipulation functions"""

from PIL import Image, ImageOps
from pathlib import Path
from typing import Tuple, Optional
from io import BytesIO
import math


# File size compression constants
MIN_COMPRESSION_QUALITY = 75
MAX_COMPRESSION_ITERATIONS = 15
DIMENSION_SAFETY_MARGIN = 0.9
MIN_TARGET_SIZE_MB = 0.1
MAX_TARGET_SIZE_MB = 100.0


def crop_image(image: Image.Image, x1: int, y1: int, x2: int, y2: int) -> Image.Image:
    """
    Crop image to specified rectangle.

    Args:
        image: PIL Image object
        x1: Left coordinate
        y1: Top coordinate
        x2: Right coordinate
        y2: Bottom coordinate

    Returns:
        Cropped PIL Image
    """
    # Ensure coordinates are within image bounds
    x1 = max(0, min(x1, image.width))
    y1 = max(0, min(y1, image.height))
    x2 = max(0, min(x2, image.width))
    y2 = max(0, min(y2, image.height))

    # Ensure x2 > x1 and y2 > y1
    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Invalid crop coordinates: ({x1}, {y1}, {x2}, {y2})")

    return image.crop((x1, y1, x2, y2))


def resize_image(
    image: Image.Image,
    width: int,
    height: int,
    maintain_aspect: bool = True
) -> Image.Image:
    """
    Resize image to specified dimensions.

    Args:
        image: PIL Image object
        width: Target width
        height: Target height
        maintain_aspect: If True, maintain aspect ratio (may not match exact dimensions)

    Returns:
        Resized PIL Image
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid dimensions: {width}x{height}")

    if maintain_aspect:
        # Calculate size maintaining aspect ratio, fitting within target dimensions
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        return image
    else:
        # Resize to exact dimensions (may distort)
        return image.resize((width, height), Image.Resampling.LANCZOS)


def add_padding(
    image: Image.Image,
    padding_px: int,
    color: str = 'white'
) -> Image.Image:
    """
    Add padding/border around image.

    Args:
        image: PIL Image object
        padding_px: Padding size in pixels
        color: Border color (name or hex)

    Returns:
        Padded PIL Image
    """
    if padding_px <= 0:
        return image

    return ImageOps.expand(image, border=padding_px, fill=color)


def trim_whitespace(image: Image.Image, tolerance: int = 10) -> Image.Image:
    """
    Automatically trim whitespace from edges.

    Args:
        image: PIL Image object
        tolerance: Color tolerance for what counts as "whitespace" (0-255)

    Returns:
        Trimmed PIL Image
    """
    # Convert to RGB if needed
    if image.mode not in ('RGB', 'L'):
        image = image.convert('RGB')

    # Get bounding box of non-white pixels
    bg = Image.new(image.mode, image.size, 'white')
    diff = ImageOps.difference(image, bg)
    bbox = diff.getbbox()

    if bbox:
        return image.crop(bbox)
    return image


def calculate_dimension_for_target_size(
    current_dimensions: Tuple[int, int],
    current_size_bytes: int,
    target_size_bytes: int
) -> Tuple[int, int]:
    """
    Estimate dimensions needed to achieve target file size.

    File size scales roughly with pixel count at same quality.
    Use conservative estimate (90% of calculated) to ensure success.

    Args:
        current_dimensions: (width, height)
        current_size_bytes: Current file size in bytes
        target_size_bytes: Target file size in bytes

    Returns:
        Suggested (width, height) maintaining aspect ratio
    """
    if current_size_bytes <= target_size_bytes:
        return current_dimensions

    # File size scales with pixel count
    # Scale factor = sqrt(target / current) because dimensions are 2D
    scale_factor = math.sqrt(target_size_bytes / current_size_bytes)

    # Apply safety margin
    scale_factor *= DIMENSION_SAFETY_MARGIN

    # Calculate new dimensions
    width, height = current_dimensions
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)

    # Ensure dimensions are at least 1
    new_width = max(1, new_width)
    new_height = max(1, new_height)

    return (new_width, new_height)


def compress_to_target_size(
    image: Image.Image,
    filepath: Path,
    format: str,
    target_size_mb: float,
    min_quality: int = MIN_COMPRESSION_QUALITY,
    max_iterations: int = MAX_COMPRESSION_ITERATIONS,
    source_filepath: Optional[Path] = None
) -> dict:
    """
    Compress image to target file size using binary search.

    Args:
        image: PIL Image object to compress
        filepath: Output file path
        format: Output format (JPEG or WEBP only)
        target_size_mb: Target file size in megabytes
        min_quality: Minimum quality to try (1-100)
        max_iterations: Maximum compression attempts
        source_filepath: Original file path (for size check optimization)

    Returns:
        dict with keys:
            - 'success': bool - Whether target was achieved
            - 'final_size_mb': float - Actual file size achieved
            - 'quality_used': int - Quality value used
            - 'message': str - Status message
            - 'suggested_dimensions': Optional[Tuple[int, int]] - If target not met
    """
    import os

    format = format.upper()

    if format not in ('JPEG', 'WEBP'):
        return {
            'success': False,
            'final_size_mb': 0,
            'quality_used': 0,
            'message': f'Compression only supported for JPEG and WEBP, not {format}',
            'suggested_dimensions': None
        }

    # Clamp target size to valid range
    target_size_mb = max(MIN_TARGET_SIZE_MB, min(MAX_TARGET_SIZE_MB, target_size_mb))
    target_size_bytes = int(target_size_mb * 1024 * 1024)

    # Prepare image for format (convert mode if needed)
    if format == 'JPEG':
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, 'white')
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

    # Early check: Is image already under target size?
    # Use source file size if available (instant), otherwise encode at q=100
    current_size_bytes = None

    if source_filepath and source_filepath.exists():
        # Check if source format matches output format (otherwise sizes won't match)
        source_ext = source_filepath.suffix.lower()
        format_matches = (
            (format == 'JPEG' and source_ext in ('.jpg', '.jpeg')) or
            (format == 'WEBP' and source_ext == '.webp')
        )
        if format_matches:
            current_size_bytes = os.path.getsize(source_filepath)

    if current_size_bytes is None:
        # Encode at quality=100 to check size
        buffer = BytesIO()
        if format == 'JPEG':
            image.save(buffer, format=format, quality=100, optimize=True)
        else:
            image.save(buffer, format=format, quality=100)
        current_size_bytes = buffer.tell()

    # If already under target, save at max quality and return early
    if current_size_bytes <= target_size_bytes:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if format == 'JPEG':
            image.save(filepath, format=format, quality=100, optimize=True)
        else:
            image.save(filepath, format=format, quality=100)

        final_size_bytes = filepath.stat().st_size
        final_size_mb = final_size_bytes / (1024 * 1024)

        return {
            'success': True,
            'final_size_mb': final_size_mb,
            'quality_used': 100,
            'message': f'Already under target ({final_size_mb:.2f} MB), saved at quality 100',
            'suggested_dimensions': None
        }

    # Binary search for optimal quality
    low_quality = min_quality
    high_quality = 100
    best_quality = None
    best_size = 0
    best_diff = float('inf')

    for iteration in range(max_iterations):
        current_quality = (low_quality + high_quality) // 2

        # Test compression to BytesIO
        buffer = BytesIO()
        if format == 'JPEG':
            image.save(buffer, format=format, quality=current_quality, optimize=True)
        else:  # WEBP
            image.save(buffer, format=format, quality=current_quality)

        current_size = buffer.tell()
        diff_from_target = abs(target_size_bytes - current_size)

        # Update best result if this is under/at target AND closer to target
        if current_size <= target_size_bytes:
            if best_quality is None or diff_from_target < best_diff:
                best_quality = current_quality
                best_size = current_size
                best_diff = diff_from_target

            # Try higher quality to get even closer
            low_quality = current_quality + 1
        else:
            # Over target, try lower quality
            high_quality = current_quality - 1

        # Stop if quality range collapsed
        if low_quality > high_quality:
            break

    # If no valid quality was found, use minimum quality
    if best_quality is None:
        best_quality = min_quality
        buffer = BytesIO()
        if format == 'JPEG':
            image.save(buffer, format=format, quality=best_quality, optimize=True)
        else:
            image.save(buffer, format=format, quality=best_quality)
        best_size = buffer.tell()

    # After binary search, try a few higher quality values to see if we can get closer
    # without going over (fine-tuning)
    for test_quality in range(best_quality + 1, min(best_quality + 4, 101)):
        buffer = BytesIO()
        if format == 'JPEG':
            image.save(buffer, format=format, quality=test_quality, optimize=True)
        else:
            image.save(buffer, format=format, quality=test_quality)

        test_size = buffer.tell()
        test_diff = abs(target_size_bytes - test_size)

        # If this quality is still under/at target and closer, use it
        if test_size <= target_size_bytes and test_diff < best_diff:
            best_quality = test_quality
            best_size = test_size
            best_diff = test_diff

    # Save final result
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if format == 'JPEG':
        image.save(filepath, format=format, quality=best_quality, optimize=True)
    else:  # WEBP
        image.save(filepath, format=format, quality=best_quality)

    # Get actual file size
    final_size_bytes = filepath.stat().st_size
    final_size_mb = final_size_bytes / (1024 * 1024)

    # Check if target was met
    success = final_size_bytes <= target_size_bytes

    result = {
        'success': success,
        'final_size_mb': final_size_mb,
        'quality_used': best_quality,
        'suggested_dimensions': None
    }

    if success:
        result['message'] = f'Compressed to {final_size_mb:.2f} MB at quality {best_quality}'
    else:
        # Calculate suggested dimensions
        suggested_dims = calculate_dimension_for_target_size(
            image.size,
            final_size_bytes,
            target_size_bytes
        )
        result['suggested_dimensions'] = suggested_dims
        result['message'] = f'Could not reach target. Achieved {final_size_mb:.2f} MB at minimum quality {best_quality}'

    return result


def save_image(
    image: Image.Image,
    filepath: Path,
    format: str = 'JPEG',
    quality: int = 100,
    target_size_mb: Optional[float] = None,
    source_filepath: Optional[Path] = None
) -> Optional[dict]:
    """
    Save image to file with specified format and quality.

    Args:
        image: PIL Image object
        filepath: Output file path
        format: Output format (JPEG, PNG, WEBP)
        quality: Quality for JPEG (1-100), ignored for PNG
        target_size_mb: Optional target file size in MB (JPEG/WEBP only)
        source_filepath: Original file path (for compression size check optimization)

    Returns:
        Optional[dict]: Compression result if target_size_mb is provided, None otherwise

    Raises:
        ValueError: If format is unsupported
        IOError: If save fails
    """
    format = format.upper()

    if format not in ('JPEG', 'PNG', 'WEBP'):
        raise ValueError(f"Unsupported format: {format}")

    # If target size is specified and format supports compression
    if target_size_mb is not None and format in ('JPEG', 'WEBP'):
        return compress_to_target_size(
            image, filepath, format, target_size_mb,
            source_filepath=source_filepath
        )

    # Ensure parent directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Convert image mode if needed for format
    if format == 'JPEG':
        # JPEG doesn't support transparency
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', image.size, 'white')
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        image.save(filepath, format=format, quality=quality, optimize=True)

    elif format == 'PNG':
        # PNG supports transparency, keep as-is
        image.save(filepath, format=format, optimize=True)

    elif format == 'WEBP':
        # WebP supports transparency
        image.save(filepath, format=format, quality=quality)

    return None


def get_crop_preview_dimensions(
    image_width: int,
    image_height: int,
    canvas_width: int,
    canvas_height: int
) -> Tuple[int, int, float]:
    """
    Calculate dimensions for displaying image in canvas.

    Args:
        image_width: Original image width
        image_height: Original image height
        canvas_width: Canvas width
        canvas_height: Canvas height

    Returns:
        Tuple of (display_width, display_height, scale_factor)
    """
    # Calculate scale to fit in canvas
    width_scale = canvas_width / image_width
    height_scale = canvas_height / image_height
    scale = min(width_scale, height_scale)

    display_width = int(image_width * scale)
    display_height = int(image_height * scale)

    return (display_width, display_height, scale)
