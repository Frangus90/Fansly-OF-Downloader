"""
Download settings widget
"""

import customtkinter as ctk
import platform
import subprocess
from tkinter import filedialog
from pathlib import Path


class SettingsSection(ctk.CTkFrame):
    """Download settings configuration section"""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config

        # Title
        title = ctk.CTkLabel(
            self, text="Download Settings", font=("Arial", 16, "bold"), anchor="w"
        )
        title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        # Download Mode
        mode_label = ctk.CTkLabel(self, text="Download Mode:", anchor="w")
        mode_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        mode_frame = ctk.CTkFrame(self)
        mode_frame.grid(row=1, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        self.mode_var = ctk.StringVar(value="normal")

        self.normal_radio = ctk.CTkRadioButton(
            mode_frame, text="Normal", variable=self.mode_var, value="normal"
        )
        self.normal_radio.pack(side="left", padx=5)

        self.timeline_radio = ctk.CTkRadioButton(
            mode_frame, text="Timeline", variable=self.mode_var, value="timeline"
        )
        self.timeline_radio.pack(side="left", padx=5)

        self.messages_radio = ctk.CTkRadioButton(
            mode_frame, text="Messages", variable=self.mode_var, value="messages"
        )
        self.messages_radio.pack(side="left", padx=5)

        # Media Types
        media_label = ctk.CTkLabel(self, text="Media Types:", anchor="w")
        media_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        media_frame = ctk.CTkFrame(self)
        media_frame.grid(row=2, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        self.photos_var = ctk.BooleanVar(value=True)
        self.photos_check = ctk.CTkCheckBox(
            media_frame, text="Photos", variable=self.photos_var
        )
        self.photos_check.pack(side="left", padx=5)

        self.videos_var = ctk.BooleanVar(value=True)
        self.videos_check = ctk.CTkCheckBox(
            media_frame, text="Videos", variable=self.videos_var
        )
        self.videos_check.pack(side="left", padx=5)

        # Download Directory
        dir_label = ctk.CTkLabel(self, text="Download Directory:", anchor="w")
        dir_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.dir_entry = ctk.CTkEntry(self, width=300)
        self.dir_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        browse_btn = ctk.CTkButton(
            self, text="Browse...", command=self.browse_directory, width=100
        )
        browse_btn.grid(row=3, column=2, padx=(10, 5), pady=5)

        open_folder_btn = ctk.CTkButton(
            self, text="Open Folder", command=self._open_download_folder, width=100
        )
        open_folder_btn.grid(row=3, column=3, padx=(0, 10), pady=5)

        # Options
        options_label = ctk.CTkLabel(self, text="Options:", anchor="w")
        options_label.grid(row=4, column=0, padx=10, pady=5, sticky="nw")

        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=4, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        self.preview_var = ctk.BooleanVar(value=False)
        self.preview_check = ctk.CTkCheckBox(
            options_frame, text="Download previews", variable=self.preview_var
        )
        self.preview_check.pack(anchor="w", pady=2)

        self.separate_preview_var = ctk.BooleanVar(value=True)
        self.separate_preview_check = ctk.CTkCheckBox(
            options_frame,
            text="Separate previews folder",
            variable=self.separate_preview_var,
        )
        self.separate_preview_check.pack(anchor="w", pady=2)

        # Incremental mode toggle
        self.incremental_var = ctk.BooleanVar(value=False)
        self.incremental_check = ctk.CTkCheckBox(
            options_frame,
            text="Incremental mode (new content only)",
            variable=self.incremental_var,
        )
        self.incremental_check.pack(anchor="w", pady=2)

        # Post limit for new creators
        post_limit_frame = ctk.CTkFrame(options_frame)
        post_limit_frame.pack(anchor="w", pady=2, fill="x")

        self.post_limit_var = ctk.BooleanVar(value=False)
        self.post_limit_check = ctk.CTkCheckBox(
            post_limit_frame,
            text="Limit posts for new creators:",
            variable=self.post_limit_var,
            command=self._on_post_limit_toggle,
        )
        self.post_limit_check.pack(side="left", padx=(0, 5))

        self.post_limit_entry = ctk.CTkEntry(
            post_limit_frame,
            width=80,
            placeholder_text="e.g. 100"
        )
        self.post_limit_entry.pack(side="left", padx=5)
        self.post_limit_entry.configure(state="disabled")

        post_limit_info = ctk.CTkLabel(
            post_limit_frame,
            text="(N newest posts for new creators)",
            font=("Arial", 9),
            text_color="gray"
        )
        post_limit_info.pack(side="left", padx=5)

        # Configure grid weights
        self.grid_columnconfigure(1, weight=1)

        # Load from config
        self.load_from_config()

    def _on_post_limit_toggle(self):
        """Toggle post limit entry field"""
        if self.post_limit_var.get():
            self.post_limit_entry.configure(state="normal")
        else:
            self.post_limit_entry.configure(state="disabled")

    def browse_directory(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory(title="Select Download Directory")
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)

    def _open_download_folder(self):
        """Open the current download directory in file explorer."""
        path = self.dir_entry.get().strip()
        if not path:
            return

        folder = Path(path)
        if not folder.exists():
            # Try to create it or just open parent
            folder.mkdir(parents=True, exist_ok=True)

        if folder.exists():
            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", str(folder)], check=False)
            elif system == "Darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)

    def load_from_config(self):
        """Load values from config"""
        # Download mode
        if hasattr(self.config, 'download_mode'):
            mode_str = str(self.config.download_mode).lower()
            if 'timeline' in mode_str:
                self.mode_var.set("timeline")
            elif 'message' in mode_str:
                self.mode_var.set("messages")
            else:
                self.mode_var.set("normal")

        # Directory
        if self.config.download_directory:
            self.dir_entry.insert(0, str(self.config.download_directory))

        # Options
        if hasattr(self.config, 'download_media_previews'):
            self.preview_var.set(self.config.download_media_previews)

        if hasattr(self.config, 'separate_previews'):
            self.separate_preview_var.set(self.config.separate_previews)

        if hasattr(self.config, 'incremental_mode'):
            self.incremental_var.set(self.config.incremental_mode)

        # Media types
        if hasattr(self.config, 'download_photos'):
            self.photos_var.set(self.config.download_photos)
        if hasattr(self.config, 'download_videos'):
            self.videos_var.set(self.config.download_videos)

        # Post limit
        if hasattr(self.config, 'max_posts_per_creator'):
            if self.config.max_posts_per_creator is not None:
                self.post_limit_var.set(True)
                self.post_limit_entry.configure(state="normal")
                self.post_limit_entry.delete(0, "end")
                self.post_limit_entry.insert(0, str(self.config.max_posts_per_creator))
            else:
                self.post_limit_var.set(False)
                self.post_limit_entry.configure(state="disabled")

    def save_to_config(self, config):
        """Save values to config"""
        # Download mode
        mode = self.mode_var.get()
        if mode == "timeline":
            from config.modes import DownloadMode
            config.download_mode = DownloadMode.TIMELINE
        elif mode == "messages":
            from config.modes import DownloadMode
            config.download_mode = DownloadMode.MESSAGES
        else:
            from config.modes import DownloadMode
            config.download_mode = DownloadMode.NORMAL

        # Directory
        dir_path = self.dir_entry.get().strip()
        if dir_path:
            config.download_directory = Path(dir_path)

        # Options
        config.download_media_previews = self.preview_var.get()
        config.separate_previews = self.separate_preview_var.get()
        config.incremental_mode = self.incremental_var.get()

        # Media types
        config.download_photos = self.photos_var.get()
        config.download_videos = self.videos_var.get()

        # Post limit
        if self.post_limit_var.get():
            try:
                limit_value = int(self.post_limit_entry.get().strip())
                if limit_value > 0:
                    config.max_posts_per_creator = limit_value
                else:
                    config.max_posts_per_creator = None
            except (ValueError, AttributeError):
                config.max_posts_per_creator = None
        else:
            config.max_posts_per_creator = None

    def validate(self):
        """Validate settings"""
        # All settings have defaults, so always valid
        return True
