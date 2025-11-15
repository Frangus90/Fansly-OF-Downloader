"""State manager for incremental downloads."""

from pathlib import Path
import json
from typing import Optional
from datetime import datetime


class DownloadStateManager:
    """Manages persistent state for incremental downloads."""

    def __init__(self, state_file: Path):
        """Initialize state manager.

        Args:
            state_file: Path to download_history.json
        """
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load state from JSON file, or create new if doesn't exist."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                # Corrupted or unreadable file - start fresh
                print(f"Warning: Could not load download history ({e}). Starting fresh.")
                return {"creators": {}, "version": "1.0"}
        return {"creators": {}, "version": "1.0"}

    def _save_state(self):
        """Persist state to disk."""
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save download history ({e})")

    def get_last_cursor(self, creator_username: str, download_type: str) -> Optional[str]:
        """Get last cursor for a creator's download type.

        Args:
            creator_username: Creator's username
            download_type: 'timeline' or 'messages'

        Returns:
            Last cursor string, or None if not found
        """
        creator_data = self.state["creators"].get(creator_username)
        if not creator_data:
            return None

        cursor_key = f"last_{download_type}_cursor"
        return creator_data.get(cursor_key)

    def update_cursor(
        self,
        creator_username: str,
        creator_id: str,
        download_type: str,
        cursor: str,
        new_items: int
    ):
        """Update cursor after successful download.

        Args:
            creator_username: Creator's username
            creator_id: Creator's ID
            download_type: 'timeline' or 'messages'
            cursor: New cursor position
            new_items: Number of new items downloaded
        """
        if creator_username not in self.state["creators"]:
            self.state["creators"][creator_username] = {
                "creator_id": creator_id,
                "total_downloads": 0,
                "download_history": []
            }

        creator = self.state["creators"][creator_username]
        cursor_key = f"last_{download_type}_cursor"
        update_key = f"last_{download_type}_update"

        creator[cursor_key] = cursor
        creator[update_key] = int(datetime.now().timestamp())
        creator["total_downloads"] = creator.get("total_downloads", 0) + new_items
        creator["last_new_items"] = new_items

        # Add to history
        creator["download_history"].append({
            "timestamp": int(datetime.now().timestamp()),
            "type": download_type,
            "new_items": new_items
        })

        # Keep only last 50 history entries
        creator["download_history"] = creator["download_history"][-50:]

        self._save_state()

    def get_last_update_time(self, creator_username: str, download_type: str) -> Optional[int]:
        """Get timestamp of last update.

        Args:
            creator_username: Creator's username
            download_type: 'timeline' or 'messages'

        Returns:
            Unix timestamp, or None if not found
        """
        creator_data = self.state["creators"].get(creator_username)
        if not creator_data:
            return None

        update_key = f"last_{download_type}_update"
        return creator_data.get(update_key)

    def clear_cursor(self, creator_username: str, download_type: str):
        """Clear cursor to force full download.

        Args:
            creator_username: Creator's username
            download_type: 'timeline' or 'messages'
        """
        if creator_username in self.state["creators"]:
            cursor_key = f"last_{download_type}_cursor"
            self.state["creators"][creator_username].pop(cursor_key, None)
            self._save_state()
