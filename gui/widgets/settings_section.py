"""
Download settings widget
"""

import customtkinter as ctk
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

        # Download Directory
        dir_label = ctk.CTkLabel(self, text="Download Directory:", anchor="w")
        dir_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.dir_entry = ctk.CTkEntry(self, width=300)
        self.dir_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        browse_btn = ctk.CTkButton(
            self, text="Browse...", command=self.browse_directory, width=100
        )
        browse_btn.grid(row=2, column=2, padx=10, pady=5)

        # Options
        options_label = ctk.CTkLabel(self, text="Options:", anchor="w")
        options_label.grid(row=3, column=0, padx=10, pady=5, sticky="nw")

        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="w")

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

        self.open_folder_var = ctk.BooleanVar(value=True)
        self.open_folder_check = ctk.CTkCheckBox(
            options_frame, text="Open folder when done", variable=self.open_folder_var
        )
        self.open_folder_check.pack(anchor="w", pady=2)

        # Incremental mode toggle
        self.incremental_var = ctk.BooleanVar(value=False)
        self.incremental_check = ctk.CTkCheckBox(
            options_frame,
            text="Incremental mode (download only new content since last run)",
            variable=self.incremental_var,
        )
        self.incremental_check.pack(anchor="w", pady=2)

        # Configure grid weights
        self.grid_columnconfigure(1, weight=1)

        # Load from config
        self.load_from_config()

    def browse_directory(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory(title="Select Download Directory")
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)

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

        if hasattr(self.config, 'open_folder_when_finished'):
            self.open_folder_var.set(self.config.open_folder_when_finished)

        if hasattr(self.config, 'incremental_mode'):
            self.incremental_var.set(self.config.incremental_mode)

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
        config.open_folder_when_finished = self.open_folder_var.get()
        config.incremental_mode = self.incremental_var.get()

    def validate(self):
        """Validate settings"""
        # All settings have defaults, so always valid
        return True
