"""
OnlyFans-specific settings widget
Simplified compared to Fansly - only shows what's actually implemented
"""

import customtkinter as ctk
import platform
import subprocess
from tkinter import filedialog
from pathlib import Path

from gui.widgets.single_post_input import SinglePostInput


class OnlyFansSettingsSection(ctk.CTkFrame):
    """OnlyFans download settings - simplified for current capabilities"""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config

        # Title
        title = ctk.CTkLabel(
            self, text="Download Settings", font=("Arial", 16, "bold"), anchor="w"
        )
        title.grid(row=0, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="w")

        # Download Mode Selection
        mode_label = ctk.CTkLabel(self, text="Download Mode:", anchor="w")
        mode_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        mode_frame = ctk.CTkFrame(self)
        mode_frame.grid(row=1, column=1, columnspan=3, padx=10, pady=5, sticky="w")

        self.mode_var = ctk.StringVar(value="Timeline")

        self.normal_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Normal",
            variable=self.mode_var,
            value="Normal",
            command=self._on_mode_change
        )
        self.normal_radio.pack(side="left", padx=10)

        self.timeline_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Timeline",
            variable=self.mode_var,
            value="Timeline",
            command=self._on_mode_change
        )
        self.timeline_radio.pack(side="left", padx=10)

        self.messages_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Messages",
            variable=self.mode_var,
            value="Messages",
            command=self._on_mode_change
        )
        self.messages_radio.pack(side="left", padx=10)

        self.single_radio = ctk.CTkRadioButton(
            mode_frame,
            text="Single Post",
            variable=self.mode_var,
            value="Single",
            command=self._on_mode_change
        )
        self.single_radio.pack(side="left", padx=10)

        # Single Post Input (shown only when Single mode selected)
        self.single_post_frame = ctk.CTkFrame(self)
        self.single_post_input = SinglePostInput(
            self.single_post_frame,
            platform="onlyfans"
        )
        self.single_post_input.pack(fill="x", padx=5, pady=5)
        # Initially hidden
        self.single_post_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky="ew")
        self.single_post_frame.grid_remove()

        # Media Types
        media_label = ctk.CTkLabel(self, text="Media Types:", anchor="w")
        media_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        media_frame = ctk.CTkFrame(self)
        media_frame.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="w")

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
        dir_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.dir_entry = ctk.CTkEntry(self, width=300)
        self.dir_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        browse_btn = ctk.CTkButton(
            self, text="Browse...", command=self.browse_directory, width=100
        )
        browse_btn.grid(row=4, column=2, padx=(10, 5), pady=5)

        open_folder_btn = ctk.CTkButton(
            self, text="Open Folder", command=self._open_download_folder, width=100
        )
        open_folder_btn.grid(row=4, column=3, padx=(0, 10), pady=5)

        # Options
        options_label = ctk.CTkLabel(self, text="Options:", anchor="w")
        options_label.grid(row=5, column=0, padx=10, pady=5, sticky="nw")

        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=5, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        # Incremental mode toggle
        self.incremental_var = ctk.BooleanVar(value=False)
        self.incremental_check = ctk.CTkCheckBox(
            options_frame,
            text="Incremental mode (skip downloaded)",
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

        # Rate Limiting Section
        rate_limit_label = ctk.CTkLabel(self, text="Rate Limiting:", anchor="w")
        rate_limit_label.grid(row=6, column=0, padx=10, pady=5, sticky="nw")

        rate_limit_frame = ctk.CTkFrame(self)
        rate_limit_frame.grid(row=6, column=1, columnspan=2, padx=10, pady=5, sticky="ew")

        rate_limit_desc_label = ctk.CTkLabel(
            rate_limit_frame,
            text="Delay between requests:",
            font=("Arial", 11)
        )
        rate_limit_desc_label.pack(side="left", padx=5)

        self.rate_limit_slider = ctk.CTkSlider(
            rate_limit_frame,
            from_=0,
            to=10,
            number_of_steps=20,  # 0.5 second increments
            command=self._on_rate_limit_change
        )
        self.rate_limit_slider.pack(side="left", padx=10, fill="x", expand=True)

        self.rate_limit_value_label = ctk.CTkLabel(
            rate_limit_frame,
            text="2.0s",
            width=50
        )
        self.rate_limit_value_label.pack(side="left", padx=5)

        # Auto-update setting (row 7)
        auto_update_label = ctk.CTkLabel(self, text="Updates:", anchor="w")
        auto_update_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")

        auto_update_frame = ctk.CTkFrame(self)
        auto_update_frame.grid(row=7, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        self.auto_update_var = ctk.BooleanVar(value=True)
        self.auto_update_check = ctk.CTkCheckBox(
            auto_update_frame,
            text="Check for updates on startup",
            variable=self.auto_update_var,
        )
        self.auto_update_check.pack(anchor="w", pady=2)

        # Configure grid weights
        self.grid_columnconfigure(1, weight=1)

        # Load from config
        self.load_from_config()

    def _on_mode_change(self):
        """Handle download mode change"""
        mode = self.mode_var.get()
        if mode == "Single":
            self.single_post_frame.grid()
            self.single_post_input.focus()
        else:
            self.single_post_frame.grid_remove()

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
        """Open the current download directory in file explorer"""
        path = self.dir_entry.get().strip()
        if not path:
            return

        folder = Path(path)
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        if folder.exists():
            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", str(folder)], check=False)
            elif system == "Darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)

    def _on_rate_limit_change(self, value):
        """Update rate limit value label"""
        self.rate_limit_value_label.configure(text=f"{value:.1f}s")

    def load_from_config(self):
        """Load values from config"""
        # Download mode
        if hasattr(self.config, 'download_mode') and self.config.download_mode:
            self.mode_var.set(self.config.download_mode)
            self._on_mode_change()

        # Directory
        if self.config.download_directory:
            self.dir_entry.insert(0, str(self.config.download_directory))

        # Incremental mode
        if hasattr(self.config, 'incremental_mode'):
            self.incremental_var.set(self.config.incremental_mode)

        # Media types
        if hasattr(self.config, 'download_photos'):
            self.photos_var.set(self.config.download_photos)
        if hasattr(self.config, 'download_videos'):
            self.videos_var.set(self.config.download_videos)

        # Rate limit
        if hasattr(self.config, 'rate_limit_delay'):
            self.rate_limit_slider.set(self.config.rate_limit_delay)
            self._on_rate_limit_change(self.config.rate_limit_delay)

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

        # Auto-update
        if hasattr(self.config, 'auto_check_updates'):
            self.auto_update_var.set(self.config.auto_check_updates)

    def save_to_config(self, config):
        """Save values to config"""
        from utils.url_parser import get_post_id_from_of_request

        # Set download mode based on selection
        mode = self.mode_var.get()
        config.download_mode = mode

        # If Single mode, get the post ID
        if mode == "Single":
            post_input = self.single_post_input.get_post_input()
            if post_input:
                config.post_id = get_post_id_from_of_request(post_input)
            else:
                config.post_id = None
        else:
            config.post_id = None

        # Directory
        dir_path = self.dir_entry.get().strip()
        if dir_path:
            config.download_directory = Path(dir_path)

        # Incremental mode
        config.incremental_mode = self.incremental_var.get()

        # Media types
        config.download_photos = self.photos_var.get()
        config.download_videos = self.videos_var.get()

        # Rate limit
        config.rate_limit_delay = int(self.rate_limit_slider.get())

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

        # Auto-update
        config.auto_check_updates = self.auto_update_var.get()

    def validate(self):
        """Validate settings"""
        return True
