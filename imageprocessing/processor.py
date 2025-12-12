"""Batch image processing and queue management"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List, Callable
from PIL import Image

from .crop import crop_image, resize_image, add_padding, save_image


@dataclass
class ImageTask:
    """Represents a single image processing task"""
    filepath: Path
    crop_rect: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)
    target_size: Optional[Tuple[int, int]] = None  # (width, height)
    format: str = 'JPEG'
    quality: int = 95
    padding: int = 0
    target_file_size_mb: Optional[float] = None  # Target file size in MB
    enable_size_compression: bool = False  # Enable file size compression

    def __post_init__(self):
        """Validate task parameters"""
        if not isinstance(self.filepath, Path):
            self.filepath = Path(self.filepath)

        if not self.filepath.exists():
            raise ValueError(f"Image file not found: {self.filepath}")

        if self.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError(f"Unsupported format: {self.format}")

        if not 1 <= self.quality <= 100:
            raise ValueError(f"Quality must be 1-100, got {self.quality}")

        if self.padding < 0:
            raise ValueError(f"Padding must be >= 0, got {self.padding}")


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

                # Load image
                image = Image.open(task.filepath)

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

                # Save with optional file size compression
                compression_target = task.target_file_size_mb if task.enable_size_compression else None
                save_image(image, output_path, task.format, task.quality, compression_target)
                output_files.append(output_path)

                # Update progress
                if progress_callback:
                    progress_callback(idx + 1, total, task.filepath.name)

            except Exception as e:
                # Log error but continue processing other images
                error_msg = f"ERROR: {task.filepath.name} - {str(e)}"
                if progress_callback:
                    progress_callback(idx + 1, total, error_msg)
                continue

        return output_files

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
            # Load image
            image = Image.open(task.filepath)

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

            # Save with optional file size compression
            compression_target = task.target_file_size_mb if task.enable_size_compression else None
            save_image(image, output_path, task.format, task.quality, compression_target)
            return True

        except Exception:
            return False
