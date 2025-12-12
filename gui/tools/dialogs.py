"""Custom styled dialog boxes matching CustomTkinter theme"""

import customtkinter as ctk
from typing import Optional, Tuple


class CTkDialog(ctk.CTkToplevel):
    """Base class for custom dialogs"""

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        icon_type: str = "info",  # info, warning, error, question
        buttons: list = None,
    ):
        super().__init__(parent)

        self.result = None

        # Window setup
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Keep on top
        self.attributes('-topmost', True)

        # Build UI
        self._build_ui(message, icon_type, buttons or ["OK"])

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)

        # Handle close button
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Bind escape key
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _build_ui(self, message: str, icon_type: str, buttons: list):
        """Build dialog UI"""
        # Main frame with padding
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Icon and message row
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="x", pady=(0, 15))

        # Icon (using text emoji for simplicity)
        icon_map = {
            "info": ("i", "#3b8ed0"),
            "warning": ("!", "#f0ad4e"),
            "error": ("X", "#dc3545"),
            "question": ("?", "#5bc0de"),
        }
        icon_text, icon_color = icon_map.get(icon_type, ("i", "#3b8ed0"))

        icon_label = ctk.CTkLabel(
            content_frame,
            text=icon_text,
            font=("Arial", 24, "bold"),
            text_color=icon_color,
            width=40,
            height=40,
        )
        icon_label.pack(side="left", padx=(0, 15))

        # Message
        message_label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=("Arial", 12),
            justify="left",
            anchor="w",
            wraplength=350,
        )
        message_label.pack(side="left", fill="x", expand=True)

        # Buttons frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        # Create buttons (left-aligned, first button is primary)
        for i, btn_text in enumerate(buttons):
            is_primary = i == 0  # First button is primary
            btn = ctk.CTkButton(
                button_frame,
                text=btn_text,
                command=lambda t=btn_text: self._on_button_click(t),
                width=80,
                height=32,
                fg_color="#3b8ed0" if is_primary else "transparent",
                border_width=1 if not is_primary else 0,
                border_color="#3b8ed0" if not is_primary else None,
                text_color="white" if is_primary else "#3b8ed0",
            )
            btn.pack(side="left", padx=(0, 5))

            # Bind Enter to primary button
            if is_primary:
                self.bind("<Return>", lambda e, t=btn_text: self._on_button_click(t))

    def _center_on_parent(self, parent):
        """Center dialog on parent window"""
        self.update_idletasks()

        # Get parent geometry
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        # Get dialog size
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()

        # Calculate position
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2

        self.geometry(f"+{x}+{y}")

    def _on_button_click(self, button_text: str):
        """Handle button click"""
        self.result = button_text
        self.destroy()

    def _on_cancel(self):
        """Handle cancel/close"""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[str]:
        """Wait for dialog and return result"""
        self.wait_window()
        return self.result


def show_info(parent, title: str, message: str):
    """Show info dialog"""
    dialog = CTkDialog(parent, title, message, icon_type="info", buttons=["OK"])
    dialog.get_result()


def show_warning(parent, title: str, message: str):
    """Show warning dialog"""
    dialog = CTkDialog(parent, title, message, icon_type="warning", buttons=["OK"])
    dialog.get_result()


def show_error(parent, title: str, message: str):
    """Show error dialog"""
    dialog = CTkDialog(parent, title, message, icon_type="error", buttons=["OK"])
    dialog.get_result()


def ask_yes_no(parent, title: str, message: str) -> bool:
    """Show yes/no dialog, returns True for Yes, False for No"""
    dialog = CTkDialog(parent, title, message, icon_type="question", buttons=["Yes", "No"])
    result = dialog.get_result()
    return result == "Yes"


def ask_ok_cancel(parent, title: str, message: str) -> bool:
    """Show OK/Cancel dialog, returns True for OK, False for Cancel"""
    dialog = CTkDialog(parent, title, message, icon_type="question", buttons=["OK", "Cancel"])
    result = dialog.get_result()
    return result == "OK"


class CTkInputDialog(ctk.CTkToplevel):
    """Custom input dialog matching app theme"""

    def __init__(self, parent, title: str, prompt: str, initial_value: str = ""):
        super().__init__(parent)

        self.result = None

        # Window setup
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.attributes('-topmost', True)

        # Build UI
        self._build_ui(prompt, initial_value)

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)

        # Handle close
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _build_ui(self, prompt: str, initial_value: str):
        """Build input dialog UI"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Prompt label with better formatting support
        prompt_label = ctk.CTkLabel(
            main_frame,
            text=prompt,
            font=("Arial", 12),
            justify="left",
            anchor="nw",
            wraplength=350,
        )
        prompt_label.pack(fill="x", pady=(0, 10), anchor="w")

        # Input entry
        self.entry_var = ctk.StringVar(value=initial_value)
        self.entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.entry_var,
            width=300,
            height=35,
        )
        self.entry.pack(fill="x", pady=(0, 15))
        self.entry.focus_set()
        self.entry.select_range(0, 'end')

        # Bind Enter to OK
        self.entry.bind("<Return>", lambda e: self._on_ok())

        # Buttons frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        ok_btn = ctk.CTkButton(
            button_frame,
            text="OK",
            command=self._on_ok,
            width=80,
            height=32,
        )
        ok_btn.pack(side="right", padx=(5, 0))

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=80,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color="#3b8ed0",
            text_color="#3b8ed0",
        )
        cancel_btn.pack(side="right")

    def _center_on_parent(self, parent):
        """Center dialog on parent window"""
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")

    def _on_ok(self):
        """Handle OK button"""
        self.result = self.entry_var.get()
        self.destroy()

    def _on_cancel(self):
        """Handle cancel"""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[str]:
        """Wait for dialog and return result"""
        self.wait_window()
        return self.result


def ask_string(parent, title: str, prompt: str, initial_value: str = "") -> Optional[str]:
    """Show input dialog, returns string or None if cancelled"""
    dialog = CTkInputDialog(parent, title, prompt, initial_value)
    return dialog.get_result()


class CTkPresetSaveDialog(ctk.CTkToplevel):
    """Custom dialog for saving presets with visual indicators"""

    def __init__(self, parent, aspect_ratio: float, anchor: str, format_aspect_ratio_func):
        super().__init__(parent)

        self.result = None

        # Window setup
        self.title("Save Preset")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.attributes('-topmost', True)

        # Build UI
        self._build_ui(aspect_ratio, anchor, format_aspect_ratio_func)

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)

        # Handle close
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _build_ui(self, aspect_ratio: float, anchor: str, format_aspect_ratio_func):
        """Build preset save dialog UI"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Enter a name for this preset:",
            font=("Arial", 13, "bold"),
            anchor="w"
        )
        title_label.pack(fill="x", pady=(0, 15), anchor="w")

        # Info box showing what will be saved
        info_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a", corner_radius=8)
        info_frame.pack(fill="x", pady=(0, 15))

        info_title = ctk.CTkLabel(
            info_frame,
            text="Will be saved with:",
            font=("Arial", 11, "bold"),
            text_color="#3b8ed0",
            anchor="w"
        )
        info_title.pack(fill="x", padx=15, pady=(12, 8), anchor="w")

        # Aspect ratio indicator
        ratio_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        ratio_frame.pack(fill="x", padx=15, pady=(0, 5))

        ratio_label = ctk.CTkLabel(
            ratio_frame,
            text="Aspect Ratio:",
            font=("Arial", 11),
            width=100,
            anchor="w"
        )
        ratio_label.pack(side="left")

        ratio_value = ctk.CTkLabel(
            ratio_frame,
            text=format_aspect_ratio_func(aspect_ratio),
            font=("Arial", 11, "bold"),
            text_color="#28a745",
            anchor="w"
        )
        ratio_value.pack(side="left", padx=(10, 0))

        # Alignment indicator
        anchor_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        anchor_frame.pack(fill="x", padx=15, pady=(0, 12))

        anchor_label = ctk.CTkLabel(
            anchor_frame,
            text="Alignment:",
            font=("Arial", 11),
            width=100,
            anchor="w"
        )
        anchor_label.pack(side="left")

        anchor_value = ctk.CTkLabel(
            anchor_frame,
            text=anchor,
            font=("Arial", 11, "bold"),
            text_color="#28a745",
            anchor="w"
        )
        anchor_value.pack(side="left", padx=(10, 0))

        # Input entry
        self.entry_var = ctk.StringVar(value="")
        self.entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.entry_var,
            width=350,
            height=35,
            placeholder_text="Preset name..."
        )
        self.entry.pack(fill="x", pady=(0, 15))
        self.entry.focus_set()

        # Bind Enter to OK
        self.entry.bind("<Return>", lambda e: self._on_ok())

        # Buttons frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        ok_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._on_ok,
            width=80,
            height=32,
        )
        ok_btn.pack(side="right", padx=(5, 0))

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
            width=80,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color="#3b8ed0",
            text_color="#3b8ed0",
        )
        cancel_btn.pack(side="right")

    def _center_on_parent(self, parent):
        """Center dialog on parent window"""
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")

    def _on_ok(self):
        """Handle OK button"""
        self.result = self.entry_var.get()
        self.destroy()

    def _on_cancel(self):
        """Handle cancel"""
        self.result = None
        self.destroy()

    def get_result(self) -> Optional[str]:
        """Wait for dialog and return result"""
        self.wait_window()
        return self.result


def ask_preset_name(parent, aspect_ratio: float, anchor: str, format_aspect_ratio_func) -> Optional[str]:
    """Show preset save dialog with visual indicators, returns preset name or None if cancelled"""
    dialog = CTkPresetSaveDialog(parent, aspect_ratio, anchor, format_aspect_ratio_func)
    return dialog.get_result()


def ask_overwrite_skip(parent, title: str, message: str) -> Optional[str]:
    """
    Show overwrite/skip dialog for file conflicts.

    Returns:
        "overwrite" - User chose to overwrite existing files
        "skip" - User chose to skip existing files
        None - User cancelled
    """
    dialog = CTkDialog(
        parent,
        title,
        message,
        icon_type="warning",
        buttons=["Overwrite", "Skip Existing", "Cancel"]
    )
    result = dialog.get_result()

    if result == "Overwrite":
        return "overwrite"
    elif result == "Skip Existing":
        return "skip"
    else:
        return None


class CTkCompressionWarningDialog(ctk.CTkToplevel):
    """Dialog for file size compression warnings"""

    def __init__(
        self,
        parent,
        filename: str,
        current_size_mb: float,
        target_size_mb: float,
        current_dimensions: Tuple[int, int],
        suggested_dimensions: Tuple[int, int]
    ):
        super().__init__(parent)

        self.result = None

        # Window setup
        self.title("Target Size Not Achievable")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.attributes('-topmost', True)

        # Build UI
        self._build_ui(
            filename,
            current_size_mb,
            target_size_mb,
            current_dimensions,
            suggested_dimensions
        )

        # Center on parent
        self.update_idletasks()
        self._center_on_parent(parent)

        # Handle close
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _build_ui(
        self,
        filename: str,
        current_size_mb: float,
        target_size_mb: float,
        current_dimensions: Tuple[int, int],
        suggested_dimensions: Tuple[int, int]
    ):
        """Build warning dialog UI"""
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Warning icon and title
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))

        icon_label = ctk.CTkLabel(
            title_frame,
            text="!",
            font=("Arial", 24, "bold"),
            text_color="#f0ad4e",
            width=40,
            height=40
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_label = ctk.CTkLabel(
            title_frame,
            text="Cannot compress to target size",
            font=("Arial", 14, "bold")
        )
        title_label.pack(side="left")

        # Filename
        filename_label = ctk.CTkLabel(
            main_frame,
            text=f"File: {filename}",
            font=("Arial", 11),
            anchor="w"
        )
        filename_label.pack(fill="x", pady=(0, 15), anchor="w")

        # Info box
        info_frame = ctk.CTkFrame(main_frame, fg_color="#1a1a1a", corner_radius=8)
        info_frame.pack(fill="x", pady=(0, 15))

        # Target size
        self._add_info_row(
            info_frame,
            "Target size:",
            f"{target_size_mb:.2f} MB"
        )

        # Achieved size
        self._add_info_row(
            info_frame,
            "Achieved (min quality):",
            f"{current_size_mb:.2f} MB",
            color="#dc3545"
        )

        # Current dimensions
        self._add_info_row(
            info_frame,
            "Current dimensions:",
            f"{current_dimensions[0]} × {current_dimensions[1]}"
        )

        # Suggested dimensions
        self._add_info_row(
            info_frame,
            "Suggested dimensions:",
            f"{suggested_dimensions[0]} × {suggested_dimensions[1]}",
            color="#28a745"
        )

        # Message
        message_label = ctk.CTkLabel(
            main_frame,
            text="The image cannot be compressed to the target size\n"
                 "even at minimum quality. You can:\n\n"
                 "• Keep current size (exceeds target)\n"
                 "• Reduce dimensions to suggested size\n"
                 "• Cancel this image",
            font=("Arial", 11),
            justify="left",
            anchor="w"
        )
        message_label.pack(fill="x", pady=(0, 15), anchor="w")

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x")

        keep_btn = ctk.CTkButton(
            button_frame,
            text="Keep Current Size",
            command=lambda: self._on_choice("keep"),
            width=140,
            height=32,
            fg_color="#f0ad4e"
        )
        keep_btn.pack(side="left", padx=(0, 5))

        resize_btn = ctk.CTkButton(
            button_frame,
            text="Reduce Dimensions",
            command=lambda: self._on_choice("resize"),
            width=140,
            height=32,
            fg_color="#28a745"
        )
        resize_btn.pack(side="left", padx=(0, 5))

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Skip This Image",
            command=self._on_cancel,
            width=120,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color="#3b8ed0",
            text_color="#3b8ed0"
        )
        cancel_btn.pack(side="left")

    def _add_info_row(
        self,
        parent,
        label: str,
        value: str,
        color: str = "#3b8ed0"
    ):
        """Add info row to info box"""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=5)

        label_widget = ctk.CTkLabel(row, text=label, width=150, anchor="w")
        label_widget.pack(side="left")

        value_widget = ctk.CTkLabel(
            row,
            text=value,
            font=("Arial", 11, "bold"),
            text_color=color,
            anchor="w"
        )
        value_widget.pack(side="left", padx=(10, 0))

    def _center_on_parent(self, parent):
        """Center dialog on parent window"""
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = parent_x + (parent_w - dialog_w) // 2
        y = parent_y + (parent_h - dialog_h) // 2
        self.geometry(f"+{x}+{y}")

    def _on_choice(self, choice: str):
        """Handle choice"""
        self.result = choice
        self.destroy()

    def _on_cancel(self):
        """Handle cancel"""
        self.result = "cancel"
        self.destroy()

    def get_result(self) -> Optional[str]:
        """Wait and return result"""
        self.wait_window()
        return self.result


def ask_compression_action(
    parent,
    filename: str,
    current_size_mb: float,
    target_size_mb: float,
    current_dimensions: Tuple[int, int],
    suggested_dimensions: Tuple[int, int]
) -> Optional[str]:
    """
    Show compression warning dialog.

    Returns:
        "keep" - Keep current size
        "resize" - Apply dimension reduction
        "cancel" - Skip this image
        None - Dialog closed
    """
    dialog = CTkCompressionWarningDialog(
        parent,
        filename,
        current_size_mb,
        target_size_mb,
        current_dimensions,
        suggested_dimensions
    )
    return dialog.get_result()
