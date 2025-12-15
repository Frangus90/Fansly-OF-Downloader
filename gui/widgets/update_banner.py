"""
Update notification banner widget
"""

import customtkinter as ctk
from typing import Callable, Optional

from updater.auto_update import UpdateInfo


class UpdateBanner(ctk.CTkFrame):
    """Non-blocking update notification banner at top of window"""

    def __init__(
        self,
        parent,
        update_info: UpdateInfo,
        on_update: Callable[[], None],
        on_skip: Callable[[str], None],
        on_dismiss: Callable[[], None]
    ):
        """
        Create update notification banner.

        Args:
            parent: Parent widget
            update_info: Information about the available update
            on_update: Called when user clicks "Update Now"
            on_skip: Called with version string when user clicks "Skip This Version"
            on_dismiss: Called when user clicks "Remind Later" or close button
        """
        super().__init__(parent, fg_color="#1a5fb4")  # Blue background

        self.update_info = update_info
        self.on_update = on_update
        self.on_skip = on_skip
        self.on_dismiss = on_dismiss

        self._build_ui()

    def _build_ui(self):
        """Build the banner UI"""
        # Main container with padding
        self.grid_columnconfigure(1, weight=1)

        # Icon/indicator (left)
        icon_label = ctk.CTkLabel(
            self,
            text="⬆",
            font=("Arial", 18, "bold"),
            text_color="white"
        )
        icon_label.grid(row=0, column=0, padx=(15, 10), pady=10)

        # Message (center, expandable)
        message = f"Version {self.update_info.version} is available!"
        message_label = ctk.CTkLabel(
            self,
            text=message,
            font=("Arial", 13, "bold"),
            text_color="white",
            anchor="w"
        )
        message_label.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        # Button container (right)
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=0, column=2, padx=10, pady=5)

        # Update Now button
        update_btn = ctk.CTkButton(
            button_frame,
            text="Update Now",
            command=self.on_update,
            width=100,
            height=28,
            fg_color="#28a745",
            hover_color="#218838",
            font=("Arial", 12, "bold")
        )
        update_btn.pack(side="left", padx=3)

        # Skip This Version button
        skip_btn = ctk.CTkButton(
            button_frame,
            text="Skip",
            command=lambda: self.on_skip(self.update_info.version),
            width=60,
            height=28,
            fg_color="#6c757d",
            hover_color="#5a6268",
            font=("Arial", 11)
        )
        skip_btn.pack(side="left", padx=3)

        # Remind Later / Close button
        close_btn = ctk.CTkButton(
            button_frame,
            text="✕",
            command=self.on_dismiss,
            width=28,
            height=28,
            fg_color="transparent",
            hover_color="#2e7bcf",
            text_color="white",
            font=("Arial", 14)
        )
        close_btn.pack(side="left", padx=3)


class DownloadProgressBanner(ctk.CTkFrame):
    """Download progress banner showing update download status"""

    def __init__(
        self,
        parent,
        on_cancel: Callable[[], None]
    ):
        """
        Create download progress banner.

        Args:
            parent: Parent widget
            on_cancel: Called when user clicks cancel
        """
        super().__init__(parent, fg_color="#1a5fb4")  # Blue background

        self.on_cancel = on_cancel
        self._build_ui()

    def _build_ui(self):
        """Build the progress banner UI"""
        self.grid_columnconfigure(1, weight=1)

        # Icon (left)
        icon_label = ctk.CTkLabel(
            self,
            text="⬇",
            font=("Arial", 18, "bold"),
            text_color="white"
        )
        icon_label.grid(row=0, column=0, padx=(15, 10), pady=10)

        # Progress container (center)
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        # Status label
        self.status_label = ctk.CTkLabel(
            progress_frame,
            text="Downloading update...",
            font=("Arial", 12, "bold"),
            text_color="white",
            anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            width=300,
            height=12,
            progress_color="#28a745"
        )
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(5, 0))

        # Percentage label
        self.percent_label = ctk.CTkLabel(
            progress_frame,
            text="0%",
            font=("Arial", 11),
            text_color="white",
            anchor="e"
        )
        self.percent_label.grid(row=1, column=1, padx=(10, 0))

        # Cancel button (right)
        cancel_btn = ctk.CTkButton(
            self,
            text="Cancel",
            command=self.on_cancel,
            width=80,
            height=28,
            fg_color="#dc3545",
            hover_color="#c82333",
            font=("Arial", 11)
        )
        cancel_btn.grid(row=0, column=2, padx=15, pady=10)

    def update_progress(self, downloaded: int, total: int):
        """Update the progress display"""
        if total > 0:
            progress = downloaded / total
            percent = int(progress * 100)

            self.progress_bar.set(progress)
            self.percent_label.configure(text=f"{percent}%")

            # Show size
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self.status_label.configure(
                text=f"Downloading update... ({downloaded_mb:.1f} / {total_mb:.1f} MB)"
            )

    def set_complete(self):
        """Show download complete state"""
        self.progress_bar.set(1.0)
        self.percent_label.configure(text="100%")
        self.status_label.configure(text="Download complete!")

    def set_error(self, message: str = "Download failed"):
        """Show error state"""
        self.status_label.configure(text=message)
        self.progress_bar.configure(progress_color="#dc3545")
