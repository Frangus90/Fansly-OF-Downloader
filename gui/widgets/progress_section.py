"""
Progress display widget
"""

import customtkinter as ctk


class ProgressSection(ctk.CTkFrame):
    """Download progress display section"""

    def __init__(self, parent):
        super().__init__(parent)

        # Title
        title = ctk.CTkLabel(
            self, text="Progress", font=("Arial", 16, "bold"), anchor="w"
        )
        title.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        # Current file label
        self.current_file_label = ctk.CTkLabel(
            self, text="Ready to start", anchor="w", text_color="gray"
        )
        self.current_file_label.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        # Stats frame
        stats_frame = ctk.CTkFrame(self)
        stats_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.downloaded_label = ctk.CTkLabel(stats_frame, text="Downloaded: 0", anchor="w")
        self.downloaded_label.pack(side="left", padx=10, pady=5)

        self.duplicates_label = ctk.CTkLabel(stats_frame, text="Duplicates: 0", anchor="w")
        self.duplicates_label.pack(side="left", padx=10, pady=5)

        self.speed_label = ctk.CTkLabel(stats_frame, text="Speed: 0 MB/s", anchor="w")
        self.speed_label.pack(side="left", padx=10, pady=5)

        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)

    def update_progress(self, update):
        """Update progress display with ProgressUpdate data"""
        # Update progress bar
        if update.total > 0:
            progress = min(update.current / update.total, 1.0)
            self.progress_bar.set(progress)
            percent = int(progress * 100)

            # Update current file with percentage
            if update.current_file:
                self.current_file_label.configure(
                    text=f"[{percent}%] {update.current_file}",
                    text_color="white"
                )
            else:
                self.current_file_label.configure(
                    text=f"Progress: {percent}%",
                    text_color="white"
                )
        else:
            # No total, show indeterminate progress
            if update.current_file:
                self.current_file_label.configure(
                    text=f"Processing: {update.current_file}",
                    text_color="white"
                )

        # Update stats
        self.downloaded_label.configure(text=f"Downloaded: {update.downloaded}")
        self.duplicates_label.configure(text=f"Duplicates: {update.duplicates}")

        if update.speed > 0:
            self.speed_label.configure(text=f"Speed: {update.speed:.2f} MB/s")

        # Handle completion
        if update.status == "complete":
            self.progress_bar.set(1.0)
            self.current_file_label.configure(
                text="Download complete!", text_color="green"
            )

        # Handle error
        elif update.status == "error":
            self.current_file_label.configure(
                text=f"Error: {update.message[:50]}", text_color="red"
            )

    def reset(self):
        """Reset progress display"""
        self.progress_bar.set(0)
        self.current_file_label.configure(
            text="Ready to start", text_color="gray"
        )
        self.downloaded_label.configure(text="Downloaded: 0")
        self.duplicates_label.configure(text="Duplicates: 0")
        self.speed_label.configure(text="Speed: 0 MB/s")
