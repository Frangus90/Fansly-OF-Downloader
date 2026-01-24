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
        
        # Track last update state to avoid unnecessary widget updates
        self._last_update = {}

    def update_progress(self, update):
        """Update progress display with ProgressUpdate data"""
        # Calculate progress percentage
        progress_value = None
        if update.total > 0:
            progress_value = min(update.current / update.total, 1.0)
        
        # Update progress bar only if changed
        if progress_value is not None:
            last_progress = self._last_update.get('progress')
            if last_progress != progress_value:
                self.progress_bar.set(progress_value)
                self._last_update['progress'] = progress_value
        
        # Update current file label only if changed
        if update.total > 0:
            percent = int(progress_value * 100)
            new_text = f"[{percent}%] {update.current_file}" if update.current_file else f"Progress: {percent}%"
            new_color = "white"
        else:
            new_text = f"Processing: {update.current_file}" if update.current_file else "Processing..."
            new_color = "white"
        
        # Handle status changes
        if update.status == "complete":
            new_text = "Download complete!"
            new_color = "green"
            if self._last_update.get('progress') != 1.0:
                self.progress_bar.set(1.0)
                self._last_update['progress'] = 1.0
        elif update.status == "error":
            new_text = f"Error: {update.message[:50]}"
            new_color = "red"
        
        # Only update label if text or color changed
        last_text = self._last_update.get('current_file_text')
        last_color = self._last_update.get('current_file_color')
        if last_text != new_text or last_color != new_color:
            self.current_file_label.configure(text=new_text, text_color=new_color)
            self._last_update['current_file_text'] = new_text
            self._last_update['current_file_color'] = new_color

        # Update stats only if changed
        if update.downloaded != self._last_update.get('downloaded'):
            self.downloaded_label.configure(text=f"Downloaded: {update.downloaded}")
            self._last_update['downloaded'] = update.downloaded
        
        if update.duplicates != self._last_update.get('duplicates'):
            self.duplicates_label.configure(text=f"Duplicates: {update.duplicates}")
            self._last_update['duplicates'] = update.duplicates

        # Update speed only if changed (round to avoid micro-updates)
        speed_rounded = round(update.speed, 2) if update.speed > 0 else 0
        if speed_rounded != self._last_update.get('speed'):
            if speed_rounded > 0:
                self.speed_label.configure(text=f"Speed: {speed_rounded:.2f} MB/s")
            else:
                self.speed_label.configure(text="Speed: 0 MB/s")
            self._last_update['speed'] = speed_rounded

    def reset(self):
        """Reset progress display"""
        self.progress_bar.set(0)
        self.current_file_label.configure(
            text="Ready to start", text_color="gray"
        )
        self.downloaded_label.configure(text="Downloaded: 0")
        self.duplicates_label.configure(text="Duplicates: 0")
        self.speed_label.configure(text="Speed: 0 MB/s")
        # Reset last update tracking
        self._last_update = {}
