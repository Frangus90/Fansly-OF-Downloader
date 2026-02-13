"""Class to Represent Media Items"""


from dataclasses import dataclass
from typing import Any

from utils.datetime import get_adjusted_datetime


@dataclass
class MediaItem(object):
    """Represents a media item published on Fansly
    eg. a picture or video.
    """
    default_normal_id: int = 0
    default_normal_created_at: int = 0
    default_normal_locations: str | None = None
    default_normal_mimetype: str | None = None
    default_normal_height: int = 0

    media_id: int = 0
    metadata: dict[str, Any] | None = None
    mimetype: str | None = None
    created_at: int = 0
    download_url: str | None = None
    file_extension: str | None = None

    highest_variants_resolution: int = 0
    highest_variants_resolution_height: int = 0
    highest_variants_resolution_url: str | None = None

    is_preview: bool = False


    def created_at_str(self) -> str:
        return get_adjusted_datetime(self.created_at)


    def get_download_url_file_extension(self) -> str | None:
        if not self.download_url:
            return None

        try:
            from urllib.parse import urlparse
            from pathlib import Path

            # Parse URL and extract path
            parsed = urlparse(self.download_url)
            path = Path(parsed.path)

            # Get extension without the leading dot
            ext = path.suffix.lstrip('.')
            return ext if ext else None
        except Exception:
            # Fallback to original method if parsing fails
            try:
                parts = self.download_url.split('/')
                if parts:
                    filename = parts[-1].split('?')[0]
                    ext_parts = filename.split('.')
                    if len(ext_parts) > 1:
                        return ext_parts[-1]
            except Exception:
                pass
            return None


    def get_file_name(self) -> str:
        """General filename construction & if content is a preview;
        add that into it's filename.
        """
        id = 'id'

        if self.is_preview:
            id = 'preview_id'

        # Ensure file_extension is not None
        if self.file_extension is None:
            # Try to get extension from download URL if available
            if self.download_url:
                ext = self.get_download_url_file_extension()
                if ext:
                    self.file_extension = ext
                else:
                    # Default to 'bin' if we can't determine extension
                    self.file_extension = 'bin'
            else:
                # No download URL and no extension - use default
                self.file_extension = 'bin'

        return f"{self.created_at_str()}_{id}_{self.media_id}.{self.file_extension}"
