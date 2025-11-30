"""Core image cropping and manipulation functions"""

from PIL import Image, ImageOps
from pathlib import Path
from typing import Tuple


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


def save_image(
    image: Image.Image,
    filepath: Path,
    format: str = 'JPEG',
    quality: int = 100
) -> None:
    """
    Save image to file with specified format and quality.

    Args:
        image: PIL Image object
        filepath: Output file path
        format: Output format (JPEG, PNG, WEBP)
        quality: Quality for JPEG (1-100), ignored for PNG

    Raises:
        ValueError: If format is unsupported
        IOError: If save fails
    """
    format = format.upper()

    if format not in ('JPEG', 'PNG', 'WEBP'):
        raise ValueError(f"Unsupported format: {format}")

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
