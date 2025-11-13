"""
Event handlers for GUI actions
"""

import tkinter.messagebox as messagebox
from gui.download_manager import DownloadManager


class EventHandlers:
    """Handles all GUI events and callbacks"""

    def __init__(self, state, window):
        self.state = state
        self.window = window
        self.sections = None
        self.download_manager = DownloadManager(
            progress_callback=self.on_progress, log_callback=self.on_log
        )

    def set_sections(self, sections):
        """Set UI sections after layout is built"""
        self.sections = sections

    def on_start_download(self):
        """Handle start button click"""
        if not self.sections:
            return

        # Validate
        if not self.sections["auth"].validate():
            self.sections["log"].add_log("Authentication required!", "error")
            return

        if not self.sections["creator"].validate():
            self.sections["log"].add_log("Creator username required!", "error")
            return

        # Save config from UI
        self.sections["auth"].save_to_config(self.state.config)
        self.sections["creator"].save_to_config(self.state.config)  # Saves to gui_state.json
        self.sections["settings"].save_to_config(self.state.config)

        # Get selected creators
        selected_creators = self.sections["creator"].get_selected_creators()
        if not selected_creators:
            self.sections["log"].add_log("No creators selected!", "error")
            return

        # Set config.user_names to ONLY the creator we're downloading
        # This is what the download system expects
        first_creator = selected_creators[0]
        self.state.config.user_names = {first_creator}
        self.state.config.current_download_creator = first_creator

        # If multiple selected, log info
        if len(selected_creators) > 1:
            self.sections["log"].add_log(
                f"Multiple creators selected. Downloading {first_creator} first. "
                f"({len(selected_creators)-1} others queued)",
                "info",
            )

        # Update UI
        self.sections["buttons"]["start"].configure(state="disabled")
        self.sections["buttons"]["stop"].configure(state="normal")
        self.sections["status"].configure(text="Status: Downloading...")

        # Start download
        self.download_manager.start(self.state.config)
        self.sections["log"].add_log("Download started", "info")

    def on_stop_download(self):
        """Handle stop button click"""
        if not self.sections:
            return

        self.download_manager.stop()
        self.sections["log"].add_log("Stopping download...", "warning")
        self.sections["buttons"]["start"].configure(state="normal")
        self.sections["buttons"]["stop"].configure(state="disabled")
        self.sections["status"].configure(text="Status: Stopped")

    def on_progress(self, update):
        """Handle progress update from download thread"""
        if not self.sections:
            return

        # Schedule UI update on main thread
        self.window.after(0, self._update_progress_ui, update)

    def _update_progress_ui(self, update):
        """Update progress UI (runs on main thread)"""
        if not self.sections:
            return

        self.sections["progress"].update_progress(update)

        if update.status == "complete":
            self.sections["buttons"]["start"].configure(state="normal")
            self.sections["buttons"]["stop"].configure(state="disabled")
            self.sections["status"].configure(text="Status: Complete")
            self.sections["log"].add_log("Download completed!", "info")

        elif update.status == "error":
            self.sections["buttons"]["start"].configure(state="normal")
            self.sections["buttons"]["stop"].configure(state="disabled")
            self.sections["status"].configure(
                text=f"Status: Error - {update.message[:50]}"
            )

    def on_log(self, message, level):
        """Handle log message from download thread"""
        if not self.sections:
            return

        # Schedule UI update on main thread
        self.window.after(0, self.sections["log"].add_log, message, level)

    def on_close(self):
        """Handle window close request"""
        if self.download_manager.is_running:
            if messagebox.askyesno(
                "Confirm Exit", "Download in progress. Stop and exit?"
            ):
                self.download_manager.stop()
                self.window.destroy()
        else:
            self.window.destroy()
