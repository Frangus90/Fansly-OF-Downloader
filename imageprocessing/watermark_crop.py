"""Watermark detection and auto-crop using OCR"""

import json
import re
from pathlib import Path
from typing import Optional

from PIL import Image

from .crop import crop_image

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


BLACKLIST_FILENAME = "watermark_blacklist.json"

# Common OCR character substitutions: maps a character to regex alternatives
_OCR_SUBSTITUTIONS = {
    "l": "[l1iI|]",
    "1": "[1l!iI]",
    "i": "[i1l!|]",
    "o": "[o0OQ]",
    "0": "[0oOQ]",
    "s": "[s5$]",
    "5": "[5s$]",
    "a": "[a@4]",
    "e": "[e3]",
    "g": "[g9q]",
    "t": "[t7+]",
    "b": "[b6]",
    "z": "[z2]",
    "y": "[yv]",
    "v": "[vy]",
    "n": "[nm]",
    "m": "[mn]",
    "u": "[uv]",
}


def _strip_to_alnum(text: str) -> str:
    """Remove all non-alphanumeric characters from text."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _build_ocr_pattern(stripped_word: str) -> re.Pattern:
    """Build a regex pattern that accounts for common OCR misreads."""
    parts = []
    for char in stripped_word:
        if char in _OCR_SUBSTITUTIONS:
            parts.append(_OCR_SUBSTITUTIONS[char])
        else:
            parts.append(re.escape(char))
    return re.compile("".join(parts))


class WatermarkDetector:
    """Detects watermark text in images using EasyOCR and crops it away."""

    def __init__(self):
        self._reader: Optional[object] = None

    def _get_reader(self) -> object:
        """Lazy-initialize EasyOCR reader. Tries GPU first, falls back to CPU."""
        if not EASYOCR_AVAILABLE:
            raise RuntimeError(
                "easyocr is not installed. Install it with: pip install easyocr"
            )
        if self._reader is None:
            try:
                import torch
                if torch.cuda.is_available():
                    self._reader = easyocr.Reader(["en"], gpu=True)
                    return self._reader
            except Exception:
                pass
            self._reader = easyocr.Reader(["en"], gpu=False)
        return self._reader

    def detect_text(
        self,
        image_path: str,
        text_threshold: float = 0.7,
        low_text: float = 0.4,
        mag_ratio: float = 1.0,
    ) -> list[dict]:
        """Run OCR on an image and return all detected text regions.

        Args:
            image_path: Path to the image file.
            text_threshold: Confidence threshold for text detection (0.0-1.0).
                Lower = more sensitive, detects faint text. Default 0.7.
            low_text: Text low-bound score for text region grouping (0.0-1.0).
                Lower = merges more aggressively. Default 0.4.
            mag_ratio: Image magnification ratio before detection.
                Higher = better for small text but slower. Default 1.0.

        Returns:
            List of dicts with keys: 'bbox', 'text', 'confidence'.
            bbox is (y_min, y_max, x_min, x_max) in pixel coordinates.
        """
        reader = self._get_reader()
        results = reader.readtext(
            image_path,
            text_threshold=text_threshold,
            low_text=low_text,
            mag_ratio=mag_ratio,
        )

        detections = []
        for bbox, text, confidence in results:
            # bbox is [[x1,y1], [x2,y1], [x2,y2], [x1,y2]] (quad corners)
            ys = [int(point[1]) for point in bbox]
            xs = [int(point[0]) for point in bbox]
            detections.append({
                "bbox": (min(ys), max(ys), min(xs), max(xs)),
                "text": text,
                "confidence": confidence,
            })

        return detections

    def find_blacklisted_regions(
        self,
        detections: list[dict],
        blacklist: list[str],
    ) -> list[dict]:
        """Filter detections to only those containing blacklisted words.

        Uses multi-level matching to handle common OCR artifacts:
        1. Direct substring match on raw text
        2. Stripped match (alphanumeric only) to ignore spaces/punctuation
        3. OCR substitution match to handle common misreads (l/1/i, o/0, etc.)

        Args:
            detections: Output from detect_text().
            blacklist: List of words to match (case-insensitive).

        Returns:
            Subset of detections that contain a blacklisted word.
        """
        if not blacklist:
            return []

        blacklist_lower = [word.lower() for word in blacklist]
        blacklist_stripped = [_strip_to_alnum(w) for w in blacklist_lower]
        blacklist_patterns = [_build_ocr_pattern(w) for w in blacklist_stripped]
        matches = []

        for detection in detections:
            text_lower = detection["text"].lower()
            text_stripped = _strip_to_alnum(text_lower)

            matched = False
            for i, word in enumerate(blacklist_lower):
                # Level 1: direct substring
                if word in text_lower:
                    matched = True
                    break
                # Level 2: stripped alphanumeric substring
                if blacklist_stripped[i] in text_stripped:
                    matched = True
                    break
                # Level 3: OCR substitution pattern
                if blacklist_patterns[i].search(text_stripped):
                    matched = True
                    break

            if matched:
                matches.append(detection)

        return matches

    def calculate_crop_box(
        self,
        image_width: int,
        image_height: int,
        matched_detections: list[dict],
        margin: int = 5,
    ) -> Optional[tuple[int, int, int, int]]:
        """Calculate the crop box that removes watermark bands.

        For each matched detection, determines whether it's near the top or
        bottom of the image and removes the full-width band from that edge.

        Args:
            image_width: Image width in pixels.
            image_height: Image height in pixels.
            matched_detections: Detections containing blacklisted text.
            margin: Extra pixels to crop beyond the text boundary.

        Returns:
            (x1, y1, x2, y2) crop box to keep, or None if no crop needed.
        """
        if not matched_detections:
            return None

        trim_top = 0  # no top crop until a detection moves this inward
        bottom_crop_line = image_height  # no bottom crop until a detection moves this inward
        midpoint = image_height / 2

        for detection in matched_detections:
            y_min, y_max, _, _ = detection["bbox"]
            center_y = (y_min + y_max) / 2

            if center_y >= midpoint:
                # Text is in bottom half - crop from text top to image bottom
                crop_line = max(0, y_min - margin)
                bottom_crop_line = min(bottom_crop_line, crop_line)
            else:
                # Text is in top half - crop from image top to text bottom
                crop_line = min(image_height, y_max + margin)
                trim_top = max(trim_top, crop_line)

        if trim_top >= bottom_crop_line:
            return None

        return (0, trim_top, image_width, bottom_crop_line)

    def crop_watermark(
        self,
        image_path: str,
        blacklist: list[str],
        margin: int = 5,
        text_threshold: float = 0.7,
        low_text: float = 0.4,
        mag_ratio: float = 1.0,
    ) -> tuple[Optional[Image.Image], list[dict], list[dict]]:
        """Detect and crop watermark text from an image.

        Args:
            image_path: Path to the image file.
            blacklist: List of words to match.
            margin: Extra pixels to crop beyond the text boundary.
            text_threshold: OCR text confidence threshold.
            low_text: OCR low text score threshold.
            mag_ratio: Image magnification ratio for OCR.

        Returns:
            Tuple of (cropped_image_or_None, all_detections, matched_detections).
            cropped_image is None if no watermark was found.
        """
        detections = self.detect_text(
            image_path,
            text_threshold=text_threshold,
            low_text=low_text,
            mag_ratio=mag_ratio,
        )
        matches = self.find_blacklisted_regions(detections, blacklist)

        if not matches:
            return None, detections, matches

        with Image.open(image_path) as img:
            crop_box = self.calculate_crop_box(
                img.width, img.height, matches, margin
            )
            if crop_box is None:
                return None, detections, matches

            cropped = crop_image(img.copy(), *crop_box)
            return cropped, detections, matches


def load_blacklist(directory: Optional[Path] = None) -> list[str]:
    """Load watermark blacklist from JSON file.

    Args:
        directory: Directory containing the blacklist file. Defaults to cwd.

    Returns:
        List of blacklisted words.
    """
    if directory is None:
        directory = Path.cwd()

    filepath = directory / BLACKLIST_FILENAME
    if not filepath.exists():
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(w) for w in data if w]
            return []
    except (json.JSONDecodeError, OSError):
        return []


def save_blacklist(words: list[str], directory: Optional[Path] = None) -> None:
    """Save watermark blacklist to JSON file.

    Args:
        words: List of words to save.
        directory: Directory to save to. Defaults to cwd.
    """
    if directory is None:
        directory = Path.cwd()

    filepath = directory / BLACKLIST_FILENAME
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2)
