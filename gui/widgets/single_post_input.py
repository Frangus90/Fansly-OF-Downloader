"""Single Post Input Widget

Reusable widget for entering a single post URL or ID.
Works for both Fansly and OnlyFans platforms.
"""

import customtkinter as ctk
from typing import Optional, Callable


class SinglePostInput(ctk.CTkFrame):
    """Input widget for single post URL or ID"""

    def __init__(
        self,
        parent,
        platform: str = "fansly",
        on_download: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize single post input widget.

        Args:
            parent: Parent widget
            platform: "fansly" or "onlyfans" - affects help text
            on_download: Callback when download button clicked, receives post input
        """
        super().__init__(parent)
        self.platform = platform.lower()
        self.on_download_callback = on_download

        # Configure grid
        self.grid_columnconfigure(1, weight=1)

        # Post URL/ID Entry
        entry_label = ctk.CTkLabel(self, text="Post URL or ID:", anchor="w")
        entry_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.post_entry = ctk.CTkEntry(
            self,
            width=300,
            placeholder_text="Paste URL or enter post ID"
        )
        self.post_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        # Bind Enter key to trigger download
        self.post_entry.bind("<Return>", self._on_enter_pressed)

        # Help text based on platform
        if self.platform == "onlyfans":
            help_text = "Example: https://onlyfans.com/123456789/creatorname"
        else:
            help_text = "Example: https://fansly.com/post/1283998432982"

        help_label = ctk.CTkLabel(
            self,
            text=help_text,
            font=("Arial", 9),
            text_color="gray"
        )
        help_label.grid(row=1, column=1, padx=10, pady=(0, 5), sticky="w")

    def _on_enter_pressed(self, event):
        """Handle Enter key press"""
        if self.on_download_callback:
            post_input = self.get_post_input()
            if post_input:
                self.on_download_callback(post_input)

    def get_post_input(self) -> str:
        """Get the current post URL/ID input"""
        return self.post_entry.get().strip()

    def set_post_input(self, value: str):
        """Set the post URL/ID input"""
        self.post_entry.delete(0, "end")
        self.post_entry.insert(0, value)

    def clear(self):
        """Clear the input field"""
        self.post_entry.delete(0, "end")

    def set_enabled(self, enabled: bool):
        """Enable/disable the widget"""
        state = "normal" if enabled else "disabled"
        self.post_entry.configure(state=state)

    def focus(self):
        """Set focus to the input field"""
        self.post_entry.focus_set()
