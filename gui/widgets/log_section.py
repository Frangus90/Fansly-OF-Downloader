"""
Console log display widget
"""

import customtkinter as ctk
from datetime import datetime


class LogSection(ctk.CTkFrame):
    """Console log display section"""
    
    MAX_LOG_LINES = 1000

    def __init__(self, parent):
        super().__init__(parent)

        # Title bar with clear button
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=10, pady=(10, 0))

        title = ctk.CTkLabel(
            title_frame, text="Console Log", font=("Arial", 16, "bold"), anchor="w"
        )
        title.pack(side="left")

        clear_btn = ctk.CTkButton(
            title_frame, text="Clear", command=self.clear_log, width=80
        )
        clear_btn.pack(side="right")

        # Text widget with scrollbar
        self.log_text = ctk.CTkTextbox(
            self, height=200, wrap="word", font=("Consolas", 10)
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Configure text tags for colors
        self.log_text._textbox.tag_config("info", foreground="#5DADE2")
        self.log_text._textbox.tag_config("warning", foreground="#F39C12")
        self.log_text._textbox.tag_config("error", foreground="#E74C3C")
        self.log_text._textbox.tag_config("success", foreground="#2ECC71")

    def _is_scrolled_to_bottom(self):
        """Check if user has scrolled to bottom of log"""
        try:
            # Get current view position
            top_index = self.log_text._textbox.index("@0,0")
            bottom_index = self.log_text._textbox.index("@0,{}".format(self.log_text._textbox.winfo_height()))
            end_index = self.log_text._textbox.index("end-1c")
            
            # Check if bottom of view is near end of text
            top_line = int(top_index.split(".")[0])
            bottom_line = int(bottom_index.split(".")[0])
            end_line = int(end_index.split(".")[0])
            
            # Consider "at bottom" if within 3 lines of end
            return (end_line - bottom_line) <= 3
        except Exception:
            # If check fails, assume at bottom (safer default)
            return True

    def add_log(self, message, level="info"):
        """Add a log message with color coding"""
        # Check if user is at bottom before adding
        is_at_bottom = self._is_scrolled_to_bottom()
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        # Map level to tag
        tag = level.lower()
        if tag not in ["info", "warning", "error", "success"]:
            tag = "info"

        # Insert with color
        self.log_text.insert("end", formatted_message, tag)

        # Remove old lines if over limit
        try:
            line_count = int(self.log_text._textbox.index("end-1c").split(".")[0])
            if line_count > self.MAX_LOG_LINES:
                lines_to_remove = line_count - self.MAX_LOG_LINES
                self.log_text._textbox.delete("1.0", f"{lines_to_remove}.0")
        except Exception:
            # If line counting fails, skip cleanup
            pass

        # Only auto-scroll if user was at bottom
        if is_at_bottom:
            self.log_text.see("end")

    def clear_log(self):
        """Clear all log messages"""
        self.log_text.delete("1.0", "end")
        self.add_log("Log cleared", "info")
