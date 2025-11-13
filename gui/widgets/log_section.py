"""
Console log display widget
"""

import customtkinter as ctk
from datetime import datetime


class LogSection(ctk.CTkFrame):
    """Console log display section"""

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

    def add_log(self, message, level="info"):
        """Add a log message with color coding"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        # Map level to tag
        tag = level.lower()
        if tag not in ["info", "warning", "error", "success"]:
            tag = "info"

        # Insert with color
        self.log_text.insert("end", formatted_message, tag)

        # Auto-scroll to bottom
        self.log_text.see("end")

    def clear_log(self):
        """Clear all log messages"""
        self.log_text.delete("1.0", "end")
        self.add_log("Log cleared", "info")
