"""
Separate console log window
"""

import customtkinter as ctk
from datetime import datetime
from gui.log_settings import (
    load_log_window_settings,
    save_log_window_settings,
    get_default_settings
)


class LogWindow(ctk.CTkToplevel):
    """Separate window for console log display"""

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        # Window properties
        self.title("Console Log")
        self.minsize(600, 300)

        # Load settings
        self.settings = load_log_window_settings()
        if not self.settings:
            self.settings = get_default_settings(parent)

        # Apply saved size and position
        width = self.settings.get("window_width", 800)
        height = self.settings.get("window_height", 400)
        x = self.settings.get("window_x", 100)
        y = self.settings.get("window_y", 100)

        # Validate position is on screen
        if x < 0 or y < 0 or x > 3000 or y > 3000:
            # Position seems invalid (e.g., disconnected monitor)
            defaults = get_default_settings(parent)
            x = defaults["window_x"]
            y = defaults["window_y"]

        self.geometry(f"{width}x{height}+{x}+{y}")

        # Apply always on top preference
        always_on_top = self.settings.get("always_on_top", False)
        if always_on_top:
            self.attributes('-topmost', True)

        # Build UI
        self._build_ui(always_on_top)

        # Handle close button (hide instead of destroy)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Save position/size when window is moved or resized
        self.bind("<Configure>", self._on_configure)

        # Start hidden by default
        is_visible = self.settings.get("is_visible", False)
        if not is_visible:
            self.withdraw()

    def _build_ui(self, always_on_top_initial: bool):
        """Build log window UI"""
        # Title bar with controls
        title_frame = ctk.CTkFrame(self)
        title_frame.pack(fill="x", padx=10, pady=(10, 0))

        title = ctk.CTkLabel(
            title_frame,
            text="Console Log",
            font=("Arial", 16, "bold"),
            anchor="w"
        )
        title.pack(side="left")

        # Always on top checkbox
        self.always_on_top_var = ctk.BooleanVar(value=always_on_top_initial)
        always_on_top_check = ctk.CTkCheckBox(
            title_frame,
            text="Always on Top",
            variable=self.always_on_top_var,
            command=self._on_always_on_top_toggle
        )
        always_on_top_check.pack(side="right", padx=(0, 10))

        # Clear button
        clear_btn = ctk.CTkButton(
            title_frame,
            text="Clear",
            command=self.clear_log,
            width=80
        )
        clear_btn.pack(side="right")

        # Text widget with scrollbar
        self.log_text = ctk.CTkTextbox(
            self,
            wrap="word",
            font=("Consolas", 10)
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Configure text tags for colors
        self.log_text._textbox.tag_config("info", foreground="#5DADE2")
        self.log_text._textbox.tag_config("warning", foreground="#F39C12")
        self.log_text._textbox.tag_config("error", foreground="#E74C3C")
        self.log_text._textbox.tag_config("success", foreground="#2ECC71")

    def add_log(self, message, level="info"):
        """
        Add a log message with color coding.
        Same interface as LogSection for compatibility.
        """
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

    def _on_always_on_top_toggle(self):
        """Handle always on top checkbox toggle"""
        is_on_top = self.always_on_top_var.get()
        self.attributes('-topmost', is_on_top)
        self.settings["always_on_top"] = is_on_top
        save_log_window_settings(self.settings)

    def _on_configure(self, event):
        """Handle window move/resize events"""
        # Only save if event is for the window itself, not child widgets
        if event.widget == self:
            # Debounce - only save after window stops moving/resizing
            # Cancel any pending save
            if hasattr(self, '_configure_save_id'):
                self.after_cancel(self._configure_save_id)

            # Schedule save for 500ms from now
            self._configure_save_id = self.after(500, self._save_window_state)

    def _save_window_state(self):
        """Save current window position, size, and visibility"""
        # Get current geometry
        self.update_idletasks()

        self.settings["window_width"] = self.winfo_width()
        self.settings["window_height"] = self.winfo_height()
        self.settings["window_x"] = self.winfo_x()
        self.settings["window_y"] = self.winfo_y()
        self.settings["is_visible"] = self.winfo_viewable()

        save_log_window_settings(self.settings)

    def _on_close(self):
        """Handle close button - hide instead of destroy"""
        self.withdraw()
        self._save_window_state()
