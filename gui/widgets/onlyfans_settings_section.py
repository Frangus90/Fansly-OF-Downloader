"""
OnlyFans-specific settings widget
Simplified compared to Fansly - only shows what's actually implemented
"""

import customtkinter as ctk
import platform
import subprocess
from tkinter import filedialog
from pathlib import Path


class OnlyFansSettingsSection(ctk.CTkFrame):
    """OnlyFans download settings - simplified for current capabilities"""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config

        # Title
        title = ctk.CTkLabel(
            self, text="Download Settings", font=("Arial", 16, "bold"), anchor="w"
        )
        title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        # Info label about Timeline mode
        info_label = ctk.CTkLabel(
            self,
            text="Mode: Timeline (Posts from creator's wall)",
            font=("Arial", 10, "italic"),
            text_color="gray",
            anchor="w"
        )
        info_label.grid(row=1, column=0, columnspan=3, padx=10, pady=(0, 10), sticky="w")

        # Download Directory
        dir_label = ctk.CTkLabel(self, text="Download Directory:", anchor="w")
        dir_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.dir_entry = ctk.CTkEntry(self, width=300)
        self.dir_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        browse_btn = ctk.CTkButton(
            self, text="Browse...", command=self.browse_directory, width=100
        )
        browse_btn.grid(row=2, column=2, padx=(10, 5), pady=5)

        open_folder_btn = ctk.CTkButton(
            self, text="Open Folder", command=self._open_download_folder, width=100
        )
        open_folder_btn.grid(row=2, column=3, padx=(0, 10), pady=5)

        # Options
        options_label = ctk.CTkLabel(self, text="Options:", anchor="w")
        options_label.grid(row=3, column=0, padx=10, pady=5, sticky="nw")

        options_frame = ctk.CTkFrame(self)
        options_frame.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="w")

        # Incremental mode toggle
        self.incremental_var = ctk.BooleanVar(value=False)
        self.incremental_check = ctk.CTkCheckBox(
            options_frame,
            text="Incremental mode (skip already downloaded files)",
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

    def load_from_config(self):
        """Load values from config"""
        # Directory
        if self.config.download_directory:
            self.dir_entry.insert(0, str(self.config.download_directory))

        # Incremental mode
        if hasattr(self.config, 'incremental_mode'):
            self.incremental_var.set(self.config.incremental_mode)

    def save_to_config(self, config):
        """Save values to config"""
        from config.modes import DownloadMode

        # Always set Timeline mode (only mode supported)
        config.download_mode = DownloadMode.TIMELINE

        # Directory
        dir_path = self.dir_entry.get().strip()
        if dir_path:
            config.download_directory = Path(dir_path)

        # Incremental mode
        config.incremental_mode = self.incremental_var.get()

    def validate(self):
        """Validate settings"""
        return True
