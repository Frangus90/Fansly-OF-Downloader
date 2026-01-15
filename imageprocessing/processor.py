"""Batch image processing and queue management"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple, List, Callable, Dict, Any
from PIL import Image

from .crop import crop_image, resize_image, add_padding
from .compression import (
    CompressionEngine,
    CompressionResult,
    QuickStrategy,
    AdvancedStrategy,
    get_encoder,
    get_available_formats,
)
from .compression.result import EncoderOptions


@dataclass
class ImageTask:
    """Represents a single image processing task.

    Supports both the new compression system and legacy options for
    backward compatibility.
    """
    filepath: Path
    crop_rect: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
    target_size: Optional[Tuple[int, int]] = None  # (width, height)
    format: str = 'JPEG'
    quality: int = 95
    padding: int = 0

    # New compression mode
    compression_mode: str = 'advanced'  # 'quick' or 'advanced'
    target_file_size_mb: Optional[float] = None  # Target file size in MB

    # Advanced compression options
    min_compression_quality: int = 60  # Minimum quality floor for compression
    progressive_jpeg: bool = False  # Enable progressive JPEG encoding
    chroma_subsampling: int = 2  # 0=4:4:4, 1=4:2:2, 2=4:2:0
    use_mozjpeg: bool = True  # Apply MozJPEG lossless optimization
    calculate_ssim: bool = False  # Calculate SSIM score

    # Legacy compatibility
    enable_size_compression: bool = False  # Deprecated: use target_file_size_mb
    ssim_threshold: Optional[float] = None  # Deprecated: use calculate_ssim

    def __post_init__(self):
        """Validate task parameters."""
        if not isinstance(self.filepath, Path):
            self.filepath = Path(self.filepath)

        if not self.filepath.exists():
            raise ValueError(f"Image file not found: {self.filepath}")

        # Support AVIF if available
        available = get_available_formats()
        if self.format not in available:
            raise ValueError(f"Unsupported format: {self.format}. Available: {available}")

        if not 1 <= self.quality <= 100:
            raise ValueError(f"Quality must be 1-100, got {self.quality}")

        if self.padding < 0:
            raise ValueError(f"Padding must be >= 0, got {self.padding}")

        if not 1 <= self.min_compression_quality <= 100:
            raise ValueError(f"min_compression_quality must be 1-100, got {self.min_compression_quality}")

        if self.chroma_subsampling not in (0, 1, 2):
            raise ValueError(f"chroma_subsampling must be 0, 1, or 2, got {self.chroma_subsampling}")

        # Handle legacy enable_size_compression flag
        if self.enable_size_compression and self.target_file_size_mb is None:
            self.target_file_size_mb = 5.0  # Default target

    def get_compression_strategy(self):
        """Get the appropriate compression strategy for this task.

        Returns:
            CompressionStrategy instance or None if no compression
        """
        if self.target_file_size_mb is None:
            return None

        if self.compression_mode == 'quick':
            return QuickStrategy(
                target_mb=self.target_file_size_mb,
                auto_format=self.format == 'AUTO',
                preferred_format=self.format,
                min_quality=self.min_compression_quality,
                calculate_ssim=self.calculate_ssim,
            )
        else:
            return AdvancedStrategy(
                format=self.format,
                quality=self.quality,
                target_mb=self.target_file_size_mb,
                min_quality=self.min_compression_quality,
                chroma_subsampling=self.chroma_subsampling,
                progressive=self.progressive_jpeg,
                use_mozjpeg=self.use_mozjpeg,
                calculate_ssim=self.calculate_ssim,
            )


class ImageProcessor:
    """Handles batch processing of images"""

    def __init__(self):
        """Initialize processor with empty queue"""
        self.queue: List[ImageTask] = []

    def add_to_queue(self, task: ImageTask) -> None:
        """
        Add task to processing queue.

        Args:
            task: ImageTask to add
        """
        self.queue.append(task)

    def remove_from_queue(self, index: int) -> None:
        """
        Remove task from queue by index.

        Args:
            index: Index of task to remove
        """
        if 0 <= index < len(self.queue):
            self.queue.pop(index)

    def clear_queue(self) -> None:
        """Clear all tasks from queue"""
        self.queue.clear()

    def get_queue_size(self) -> int:
        """Get number of tasks in queue"""
        return len(self.queue)

    def _get_output_extension(self, format: str) -> str:
        """Get file extension for format"""
        ext_map = {
            'JPEG': '.jpg',
            'PNG': '.png',
            'WEBP': '.webp',
            'AVIF': '.avif',
        }
        return ext_map.get(format, '.jpg')

    def get_expected_output_path(
        self,
        original_path: Path,
        output_dir: Path,
        format: str
    ) -> Path:
        """
        Get the expected output path for a file (without collision handling).
        Preserves original filename exactly.

        Args:
            original_path: Original image file path
            output_dir: Output directory
            format: Output format (JPEG, PNG, WEBP) - not used, kept for compatibility

        Returns:
            Path object for expected output file
        """
        # Preserve exact original filename
        return output_dir / original_path.name

    def check_existing_files(
        self,
        filepaths: List[Path],
        output_dir: Path,
        format: str
    ) -> List[Path]:
        """
        Check which output files already exist.

        Args:
            filepaths: List of input file paths
            output_dir: Output directory
            format: Output format

        Returns:
            List of paths that already exist in output directory
        """
        existing = []
        output_dir = Path(output_dir)

        if not output_dir.exists():
            return existing

        for filepath in filepaths:
            expected_path = self.get_expected_output_path(filepath, output_dir, format)
            if expected_path.exists():
                existing.append(expected_path)

        return existing

    def _generate_output_path(
        self,
        original_path: Path,
        output_dir: Path,
        format: str,
        overwrite: bool = False
    ) -> Path:
        """
        Generate output path preserving original filename exactly.

        Args:
            original_path: Original image file path
            output_dir: Output directory
            format: Output format (JPEG, PNG, WEBP) - not used, kept for compatibility
            overwrite: If True, return path even if file exists

        Returns:
            Path object for output file
        """
        # Preserve exact original filename
        output_path = output_dir / original_path.name

        # If overwrite mode, return directly
        if overwrite:
            return output_path

        # Handle collisions by adding numeric suffix
        stem = original_path.stem
        extension = original_path.suffix
        counter = 1
        while output_path.exists():
            output_path = output_dir / f"{stem}_{counter}{extension}"
            counter += 1

        return output_path

    def process_batch(
        self,
        output_dir: Path,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        overwrite: bool = False,
        skip_existing: bool = False
    ) -> List[Path]:
        """
        Process all images in queue.

        Args:
            output_dir: Directory to save processed images
            progress_callback: Optional callback function(current, total, filename)
                               Called after each image is processed
            overwrite: If True, overwrite existing files
            skip_existing: If True, skip files that already exist

        Returns:
            List of output file paths (successfully processed images)

        Raises:
            ValueError: If output_dir is invalid
        """
        if not output_dir:
            raise ValueError("Output directory must be specified")

        # Create output directory if it doesn't exist
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_files = []
        failed_files = []
        total = len(self.queue)
        skipped = 0

        for idx, task in enumerate(self.queue):
            try:
                # Check if output file already exists
                expected_path = self.get_expected_output_path(
                    task.filepath, output_dir, task.format
                )

                if expected_path.exists() and skip_existing:
                    # Skip this file
                    skipped += 1
                    if progress_callback:
                        progress_callback(idx + 1, total, f"Skipped: {task.filepath.name}")
                    continue

                # Load image using context manager to ensure file handle is closed
                with Image.open(task.filepath) as image:
                    # Need to load image data before exiting context
                    image.load()

                    # Apply crop if specified
                    if task.crop_rect:
                        x1, y1, x2, y2 = task.crop_rect
                        image = crop_image(image, x1, y1, x2, y2)

                    # Apply resize if specified
                    if task.target_size:
                        width, height = task.target_size
                        image = resize_image(image, width, height, maintain_aspect=False)

                    # Apply padding if specified
                    if task.padding > 0:
                        image = add_padding(image, task.padding)

                    # Generate output path (with overwrite option)
                    output_path = self._generate_output_path(
                        task.filepath,
                        output_dir,
                        task.format,
                        overwrite=overwrite
                    )

                    # Use new compression system
                    was_cropped = task.crop_rect is not None
                    result = self._compress_and_save(image, task, output_path, was_cropped)
                    if result:
                        output_files.append(output_path)

                # Update progress
                if progress_callback:
                    progress_callback(idx + 1, total, task.filepath.name)

            except Exception as e:
                # Track failed files and continue processing others
                error_msg = f"ERROR: {task.filepath.name} - {str(e)}"
                failed_files.append((task.filepath, str(e)))
                if progress_callback:
                    progress_callback(idx + 1, total, error_msg)
                continue

        # Return dict with results so caller knows about failures
        return {
            'success': output_files,
            'failed': failed_files,
            'skipped': skipped
        }

    def process_single(
        self,
        task: ImageTask,
        output_path: Path
    ) -> bool:
        """
        Process a single image task.

        Args:
            task: ImageTask to process
            output_path: Full output path for saved image

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load image using context manager to ensure file handle is closed
            with Image.open(task.filepath) as image:
                # Need to load image data before exiting context
                image.load()

                # Apply crop if specified
                if task.crop_rect:
                    x1, y1, x2, y2 = task.crop_rect
                    image = crop_image(image, x1, y1, x2, y2)

                # Apply resize if specified
                if task.target_size:
                    width, height = task.target_size
                    image = resize_image(image, width, height, maintain_aspect=False)

                # Apply padding if specified
                if task.padding > 0:
                    image = add_padding(image, task.padding)

                # Use new compression system
                was_cropped = task.crop_rect is not None
                return self._compress_and_save(image, task, output_path, was_cropped)

        except Exception:
            return False

    def _compress_and_save(
        self,
        image: Image.Image,
        task: ImageTask,
        output_path: Path,
        was_cropped: bool = False
    ) -> bool:
        """Compress and save image using the new compression system.

        Args:
            image: PIL Image to save
            task: ImageTask with compression settings
            output_path: Path to save to
            was_cropped: Whether the image was cropped (affects skip logic)

        Returns:
            True if successful, False otherwise
        """
        try:
            strategy = task.get_compression_strategy()
            source_file_size = task.filepath.stat().st_size

            # Check if we should skip compression (source already under target)
            if strategy is not None and task.target_file_size_mb is not None:
                target_bytes = int(task.target_file_size_mb * 1024 * 1024)

                # If source is under target and not cropped, copy original file
                if source_file_size <= target_bytes and not was_cropped:
                    import shutil
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(task.filepath, output_path)
                    return True

            if strategy is not None:
                # Use compression strategy
                result = strategy.compress(image)

                # Safety check: if compression made file larger than source
                # and source was under target, use original
                if task.target_file_size_mb is not None:
                    target_bytes = int(task.target_file_size_mb * 1024 * 1024)
                    if (result.final_size_bytes > source_file_size and
                            source_file_size <= target_bytes and
                            not was_cropped):
                        import shutil
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(task.filepath, output_path)
                        return True

                # Write encoded bytes to file
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(result.encoded_bytes)
                return True
            else:
                # No compression target - save at specified quality
                encoder = get_encoder(task.format)
                if encoder is None:
                    return False

                options = EncoderOptions(
                    quality=task.quality,
                    chroma_subsampling=task.chroma_subsampling,
                    progressive=task.progressive_jpeg,
                    use_mozjpeg=task.use_mozjpeg,
                )
                encoded_bytes = encoder.encode(image, options)

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(encoded_bytes)
                return True

        except Exception:
            return False

    def compress_preview(
        self,
        image: Image.Image,
        task: ImageTask,
    ) -> Optional[CompressionResult]:
        """Generate compression preview without saving.

        Args:
            image: PIL Image to compress
            task: ImageTask with compression settings

        Returns:
            CompressionResult with preview data or None on error
        """
        try:
            strategy = task.get_compression_strategy()

            if strategy is not None:
                return strategy.compress(image)
            else:
                # No compression target - just encode at quality
                encoder = get_encoder(task.format)
                if encoder is None:
                    return None

                engine = CompressionEngine(encoder)
                options = EncoderOptions(
                    quality=task.quality,
                    chroma_subsampling=task.chroma_subsampling,
                    progressive=task.progressive_jpeg,
                    use_mozjpeg=task.use_mozjpeg,
                )
                return engine.compress_at_quality(
                    image, options, calculate_ssim=task.calculate_ssim
                )

        except Exception:
            return None
