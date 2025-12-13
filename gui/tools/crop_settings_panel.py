"""Left panel with crop settings and controls"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from typing import Callable, List, Optional

from gui.tools import dialogs
from imageprocessing.presets import (
    get_preset_names,
    get_preset_aspect_ratio,
    get_preset_anchor,
    get_preset_data,
    add_preset,
    remove_preset,
    format_aspect_ratio,
)


class CropSettingsPanel(ctk.CTkFrame):
    """Settings panel for image crop controls"""

    def __init__(
        self,
        parent,
        on_upload_callback: Callable[[List[Path]], None],
        on_preset_change_callback: Callable[[str], None],
        on_settings_change_callback: Callable[[], None],
        on_aspect_ratio_apply_callback: Optional[Callable[[float], None]] = None
    ):
        super().__init__(parent)

        self.on_upload_callback = on_upload_callback
        self.on_preset_change_callback = on_preset_change_callback
        self.on_settings_change_callback = on_settings_change_callback
        self.on_aspect_ratio_apply_callback = on_aspect_ratio_apply_callback

        # Flag to prevent callbacks during initialization
        self._initialized = False

        # Build UI
        self._build_ui()

        # Now safe to call callbacks
        self._initialized = True

    def _build_ui(self):
        """Build the settings panel UI"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="Crop Settings",
            font=("Arial", 18, "bold"),
            anchor="w"
        )
        title.pack(padx=15, pady=(15, 10), anchor="w")

        # Upload section
        self._build_upload_section()

        # Preset section
        self._build_preset_section()

        # Aspect Ratio section
        self._build_aspect_ratio_section()

        # Format section
        self._build_format_section()

    def _build_upload_section(self):
        """Build upload button section"""
        section = ctk.CTkFrame(self)
        section.pack(fill="x", padx=10, pady=5)

        label = ctk.CTkLabel(
            section,
            text="Images",
            font=("Arial", 14, "bold"),
            anchor="w"
        )
        label.pack(padx=10, pady=(10, 5), anchor="w")

        upload_btn = ctk.CTkButton(
            section,
            text="Upload Images",
            command=self._browse_images,
            height=40,
            font=("Arial", 13),
        )
        upload_btn.pack(padx=10, pady=5, fill="x")

        self.upload_status = ctk.CTkLabel(
            section,
            text="No images loaded",
            font=("Arial", 10),
            text_color="gray60"
        )
        self.upload_status.pack(padx=10, pady=(0, 10))

    def _build_preset_section(self):
        """Build preset selection section with save/delete"""
        section = ctk.CTkFrame(self)
        section.pack(fill="x", padx=10, pady=5)

        label = ctk.CTkLabel(
            section,
            text="Presets",
            font=("Arial", 14, "bold"),
            anchor="w"
        )
        label.pack(padx=10, pady=(10, 5), anchor="w")

        # Dropdown row
        dropdown_frame = ctk.CTkFrame(section)
        dropdown_frame.pack(fill="x", padx=10, pady=(0, 5))

        # Get preset names (may be empty)
        preset_names = get_preset_names()
        if not preset_names:
            preset_names = ["(No presets)"]

        self.preset_var = ctk.StringVar(value=preset_names[0] if preset_names else "")
        self.preset_dropdown = ctk.CTkOptionMenu(
            dropdown_frame,
            variable=self.preset_var,
            values=preset_names,
            command=self._on_preset_selected,
            width=120
        )
        self.preset_dropdown.pack(side="left")

        # Apply preset button
        self.apply_preset_btn = ctk.CTkButton(
            dropdown_frame,
            text="Apply",
            command=self._on_apply_preset,
            width=50,
            height=28
        )
        self.apply_preset_btn.pack(side="left", padx=(5, 0))

        # Delete preset button
        self.delete_preset_btn = ctk.CTkButton(
            dropdown_frame,
            text="X",
            command=self._on_delete_preset,
            width=30,
            height=28,
            fg_color="#dc3545",
            hover_color="#c82333"
        )
        self.delete_preset_btn.pack(side="left", padx=(5, 0))

        # Save current as preset button
        save_preset_btn = ctk.CTkButton(
            section,
            text="+ Save Current as Preset",
            command=self._on_save_preset,
            height=30,
            font=("Arial", 11)
        )
        save_preset_btn.pack(padx=10, pady=(0, 10), fill="x")

        # Disable controls if no presets
        if not get_preset_names():
            self.preset_dropdown.configure(state="disabled")
            self.apply_preset_btn.configure(state="disabled")
            self.delete_preset_btn.configure(state="disabled")

    def _build_aspect_ratio_section(self):
        """Build aspect ratio controls section"""
        section = ctk.CTkFrame(self)
        section.pack(fill="x", padx=10, pady=5)

        label = ctk.CTkLabel(
            section,
            text="Aspect Ratio",
            font=("Arial", 14, "bold"),
            anchor="w"
        )
        label.pack(padx=10, pady=(10, 5), anchor="w")

        # Current aspect ratio display
        current_frame = ctk.CTkFrame(section)
        current_frame.pack(fill="x", padx=10, pady=(0, 5))

        current_label = ctk.CTkLabel(
            current_frame,
            text="Current:",
            width=60,
            anchor="w"
        )
        current_label.pack(side="left")

        self.current_aspect_label = ctk.CTkLabel(
            current_frame,
            text="--",
            font=("Arial", 11, "bold"),
            text_color="#3b8ed0"
        )
        self.current_aspect_label.pack(side="left", padx=5)

        # Aspect ratio lock checkbox
        self.lock_aspect_var = ctk.BooleanVar(value=False)
        self.lock_aspect_check = ctk.CTkCheckBox(
            section,
            text="Lock aspect ratio",
            variable=self.lock_aspect_var,
            command=self._on_settings_changed
        )
        self.lock_aspect_check.pack(padx=10, pady=(5, 5), anchor="w")

        # Aspect ratio input
        input_frame = ctk.CTkFrame(section)
        input_frame.pack(fill="x", padx=10, pady=(5, 5))

        self.aspect_ratio_var = ctk.StringVar(value="")
        self.aspect_ratio_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.aspect_ratio_var,
            placeholder_text="1.333 or 16:9",
            width=100
        )
        self.aspect_ratio_entry.pack(side="left", padx=(0, 5))

        self.apply_aspect_btn = ctk.CTkButton(
            input_frame,
            text="Apply to Selected",
            command=self._on_apply_aspect_ratio,
            width=110,
            height=28
        )
        self.apply_aspect_btn.pack(side="left")

        # Crop anchor/alignment dropdown
        anchor_frame = ctk.CTkFrame(section)
        anchor_frame.pack(fill="x", padx=10, pady=(5, 10))

        anchor_label = ctk.CTkLabel(
            anchor_frame,
            text="Align:",
            width=45,
            anchor="w"
        )
        anchor_label.pack(side="left")

        self.anchor_var = ctk.StringVar(value="Center")
        self.anchor_dropdown = ctk.CTkOptionMenu(
            anchor_frame,
            variable=self.anchor_var,
            values=["Center", "Top", "Bottom", "Left", "Right"],
            width=120
        )
        self.anchor_dropdown.pack(side="left", padx=5)


    def _build_format_section(self):
        """Build format and quality section"""
        section = ctk.CTkFrame(self)
        section.pack(fill="x", padx=10, pady=5)

        label = ctk.CTkLabel(
            section,
            text="Export Format",
            font=("Arial", 14, "bold"),
            anchor="w"
        )
        label.pack(padx=10, pady=(10, 5), anchor="w")

        # Format selector
        self.format_var = ctk.StringVar(value="JPEG")
        format_frame = ctk.CTkFrame(section)
        format_frame.pack(fill="x", padx=10, pady=5)

        jpeg_radio = ctk.CTkRadioButton(
            format_frame,
            text="JPEG",
            variable=self.format_var,
            value="JPEG",
            command=self._on_format_changed
        )
        jpeg_radio.pack(side="left", padx=5)

        png_radio = ctk.CTkRadioButton(
            format_frame,
            text="PNG",
            variable=self.format_var,
            value="PNG",
            command=self._on_format_changed
        )
        png_radio.pack(side="left", padx=5)

        webp_radio = ctk.CTkRadioButton(
            format_frame,
            text="WebP",
            variable=self.format_var,
            value="WEBP",
            command=self._on_format_changed
        )
        webp_radio.pack(side="left", padx=5)

        # Quality slider (for JPEG/WebP)
        quality_label = ctk.CTkLabel(
            section,
            text="Quality:",
            anchor="w"
        )
        quality_label.pack(padx=10, pady=(10, 0), anchor="w")

        self.quality_var = ctk.IntVar(value=100)
        self.quality_slider = ctk.CTkSlider(
            section,
            from_=1,
            to=100,
            number_of_steps=99,
            variable=self.quality_var,
            command=self._on_settings_changed
        )
        self.quality_slider.pack(padx=10, pady=2, fill="x")

        self.quality_value_label = ctk.CTkLabel(
            section,
            text="100%",
            font=("Arial", 10),
            text_color="gray60"
        )
        self.quality_value_label.pack(padx=10, pady=(0, 10))

        # Bind quality slider to update label
        self.quality_var.trace_add('write', self._update_quality_label)

        # File size compression section
        self._build_compression_section()

    def _build_compression_section(self):
        """Build file size compression controls"""
        self.compression_section = ctk.CTkFrame(self)
        self.compression_section.pack(fill="x", padx=10, pady=5)

        label = ctk.CTkLabel(
            self.compression_section,
            text="File Size Compression",
            font=("Arial", 14, "bold"),
            anchor="w"
        )
        label.pack(padx=10, pady=(10, 5), anchor="w")

        # Target size input frame
        self.target_size_frame = ctk.CTkFrame(self.compression_section)
        self.target_size_frame.pack(fill="x", padx=10, pady=5)

        # Label
        target_label = ctk.CTkLabel(
            self.target_size_frame,
            text="Target size:",
            anchor="w",
            width=80
        )
        target_label.pack(side="left", padx=(0, 5))

        # Dropdown with common sizes + custom option
        self.target_size_var = ctk.StringVar(value="5 MB")
        self.target_size_dropdown = ctk.CTkOptionMenu(
            self.target_size_frame,
            variable=self.target_size_var,
            values=["1 MB", "2 MB", "5 MB", "10 MB", "20 MB", "Custom..."],
            command=self._on_target_size_changed,
            width=110
        )
        self.target_size_dropdown.pack(side="left", padx=5)

        # Custom input (hidden by default)
        self.custom_size_var = ctk.StringVar(value="5.0")
        self.custom_size_entry = ctk.CTkEntry(
            self.target_size_frame,
            textvariable=self.custom_size_var,
            width=60,
            placeholder_text="5.0"
        )

        # Info label
        self.compression_info_label = ctk.CTkLabel(
            self.compression_section,
            text="Quality will be automatically adjusted to meet target size",
            font=("Arial", 9),
            text_color="gray60",
            wraplength=200
        )
        self.compression_info_label.pack(padx=10, pady=(0, 5))

        # Processing mode selection
        mode_label = ctk.CTkLabel(
            self.compression_section,
            text="Processing mode:",
            anchor="w"
        )
        mode_label.pack(padx=10, pady=(5, 0), anchor="w")

        self.processing_mode_var = ctk.StringVar(value="crop_and_compress")
        mode_container = ctk.CTkFrame(self.compression_section, fg_color="transparent")
        mode_container.pack(fill="x", padx=10, pady=5)

        # Radio buttons - each has callback to update compression UI
        crop_and_compress_radio = ctk.CTkRadioButton(
            mode_container,
            text="Crop + Compress",
            variable=self.processing_mode_var,
            value="crop_and_compress",
            command=self._on_processing_mode_changed
        )
        crop_and_compress_radio.pack(anchor="w", pady=2)

        compress_only_radio = ctk.CTkRadioButton(
            mode_container,
            text="Compress Only (no crop)",
            variable=self.processing_mode_var,
            value="compress_only",
            command=self._on_processing_mode_changed
        )
        compress_only_radio.pack(anchor="w", pady=2)

        crop_only_radio = ctk.CTkRadioButton(
            mode_container,
            text="Crop Only (no compression)",
            variable=self.processing_mode_var,
            value="crop_only",
            command=self._on_processing_mode_changed
        )
        crop_only_radio.pack(anchor="w", pady=2)

        # Initial state - compression controls enabled (default is crop_and_compress)
        self._update_compression_visibility()
        self._on_format_changed()  # Sync quality label with initial mode

    def _browse_images(self):
        """Open file browser to select multiple images"""
        # Get the toplevel window to use as parent for the dialog
        toplevel = self.winfo_toplevel()

        filepaths = filedialog.askopenfilenames(
            parent=toplevel,
            title="Select Images to Crop",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.webp *.gif *.bmp"),
                ("JPEG files", "*.jpg *.jpeg"),
                ("PNG files", "*.png"),
                ("WebP files", "*.webp"),
                ("All files", "*.*"),
            ]
        )

        # Bring crop window back to front after file dialog closes
        toplevel.lift()
        toplevel.focus_force()

        if filepaths:
            # Convert tuple to list of Path objects
            paths = [Path(fp) for fp in filepaths]

            # Notify parent window to load these images
            self.on_upload_callback(paths)

            # Update status label
            self.upload_status.configure(
                text=f"{len(paths)} image(s) loaded",
                text_color="#28a745"
            )

    def _on_preset_selected(self, preset_name: str):
        """Handle preset dropdown selection - fills in aspect ratio box and anchor"""
        if preset_name == "(No presets)":
            return

        # Get aspect ratio for this preset and fill in the input box
        ratio = get_preset_aspect_ratio(preset_name)
        if ratio:
            # Fill in the aspect ratio input box
            self.aspect_ratio_var.set(f"{ratio:.3f}")
        
        # Get anchor for this preset and set it
        anchor = get_preset_anchor(preset_name)
        if anchor:
            self.anchor_var.set(anchor)

    def _on_apply_preset(self):
        """Handle Apply preset button - applies selected preset"""
        preset_name = self.preset_var.get()
        if preset_name == "(No presets)":
            return

        # Get aspect ratio for this preset
        ratio = get_preset_aspect_ratio(preset_name)
        if ratio:
            # Fill in the aspect ratio input box
            self.aspect_ratio_var.set(f"{ratio:.3f}")

            # Notify parent to apply this preset
            self.on_preset_change_callback(preset_name)

    def _on_save_preset(self):
        """Save current aspect ratio and anchor as a new preset"""
        toplevel = self.winfo_toplevel()

        # Get current aspect ratio from label
        current_text = self.current_aspect_label.cget("text")
        if current_text == "--":
            dialogs.show_warning(toplevel, "No Crop", "Load an image and adjust the crop box first.")
            return

        # Parse the ratio from the label (format: "1.333" or "1.333 (4:3)")
        try:
            ratio_str = current_text.split(" ")[0]
            ratio = float(ratio_str)
        except (ValueError, IndexError):
            dialogs.show_error(toplevel, "Error", "Could not determine current aspect ratio.")
            return

        # Get current anchor/alignment
        anchor = self.anchor_var.get()

        # Use the enhanced preset save dialog with visual indicators
        name = dialogs.ask_preset_name(
            toplevel,
            ratio,
            anchor,
            format_aspect_ratio
        )

        if name:
            name = name.strip()
            if not name:
                return

            # Check for duplicate
            existing = get_preset_names()
            if name in existing:
                if not dialogs.ask_yes_no(toplevel, "Overwrite", f"Preset '{name}' already exists. Overwrite?"):
                    return

            # Save preset with both aspect ratio and anchor
            if add_preset(name, ratio, anchor):
                dialogs.show_info(toplevel, "Saved", f"Preset '{name}' saved successfully.")
                self._refresh_preset_dropdown()
                self.preset_var.set(name)
            else:
                dialogs.show_error(toplevel, "Error", "Failed to save preset.")

    def _on_delete_preset(self):
        """Delete the currently selected preset"""
        toplevel = self.winfo_toplevel()
        current = self.preset_var.get()
        if current == "(No presets)":
            return

        if dialogs.ask_yes_no(toplevel, "Delete Preset", f"Delete preset '{current}'?"):
            if remove_preset(current):
                self._refresh_preset_dropdown()
            else:
                dialogs.show_error(toplevel, "Error", "Failed to delete preset.")

    def _refresh_preset_dropdown(self):
        """Refresh the preset dropdown with current presets"""
        preset_names = get_preset_names()

        if preset_names:
            self.preset_dropdown.configure(values=preset_names, state="normal")
            self.apply_preset_btn.configure(state="normal")
            self.delete_preset_btn.configure(state="normal")
            self.preset_var.set(preset_names[0])
        else:
            self.preset_dropdown.configure(values=["(No presets)"], state="disabled")
            self.apply_preset_btn.configure(state="disabled")
            self.delete_preset_btn.configure(state="disabled")
            self.preset_var.set("(No presets)")

    def _on_format_changed(self):
        """Handle format selection change and manage compression state"""
        format_val = self.format_var.get()
        mode = self.processing_mode_var.get()
        compression_enabled = mode in ('crop_and_compress', 'compress_only')

        if format_val == "PNG":
            # PNG is lossless, disable quality slider
            self.quality_slider.configure(state="disabled")
            self.quality_value_label.configure(text="N/A (lossless)")
        else:
            # JPEG/WebP support compression
            if compression_enabled:
                # Compression mode - disable quality slider (auto-adjusted)
                self.quality_slider.configure(state="disabled")
                self.quality_value_label.configure(text="Auto (size-based)")
            else:
                # Crop only mode - enable quality slider
                self.quality_slider.configure(state="normal")
                self._update_quality_label()

        self._on_settings_changed()

    def _on_settings_changed(self, *args):
        """Handle any settings change"""
        # Don't call callback during initialization
        if self._initialized:
            self.on_settings_change_callback()

    def _update_quality_label(self, *args):
        """Update quality value label"""
        value = self.quality_var.get()
        self.quality_value_label.configure(text=f"{value}%")

    def _on_processing_mode_changed(self):
        """Handle processing mode radio button change"""
        self._update_compression_visibility()
        self._on_format_changed()  # Update quality slider state

    def _update_compression_visibility(self):
        """Show/hide compression controls based on processing mode"""
        mode = self.processing_mode_var.get()
        # Show compression controls for modes that include compression
        show_compression = mode in ('crop_and_compress', 'compress_only')

        if show_compression:
            self.target_size_frame.pack(fill="x", padx=10, pady=5)
            self.compression_info_label.pack(padx=10, pady=(0, 5))
            self.target_size_dropdown.configure(state="normal")
            # Show custom input if needed
            if self.target_size_var.get() == "Custom...":
                self.custom_size_entry.pack(side="left", padx=5)
        else:
            self.target_size_frame.pack_forget()
            self.compression_info_label.pack_forget()
            self.custom_size_entry.pack_forget()

    def _on_target_size_changed(self, value: str):
        """Handle target size dropdown change"""
        if value == "Custom...":
            # Show custom input
            self.custom_size_entry.pack(side="left", padx=5)
            self.custom_size_entry.focus_set()
        else:
            # Hide custom input
            self.custom_size_entry.pack_forget()

    def _on_apply_aspect_ratio(self):
        """Parse and apply aspect ratio input to selected images (or all if none selected)"""
        ratio_str = self.aspect_ratio_var.get().strip()

        if not ratio_str:
            return

        # Replace comma with period for European decimal format
        ratio_str = ratio_str.replace(',', '.')

        try:
            # Try to parse decimal format (1.333) or ratio format (16:9)
            if ':' in ratio_str:
                # Ratio format (16:9)
                parts = ratio_str.split(':')
                if len(parts) != 2:
                    raise ValueError("Invalid ratio format")
                ratio = float(parts[0]) / float(parts[1])
            else:
                # Decimal format (1.333 or 1,333)
                ratio = float(ratio_str)

            # Validate range
            if ratio <= 0.1 or ratio >= 10.0:
                raise ValueError("Aspect ratio must be between 0.1 and 10.0")

            # Notify parent to update ALL images with this aspect ratio
            if self.on_aspect_ratio_apply_callback:
                self.on_aspect_ratio_apply_callback(ratio)

        except (ValueError, ZeroDivisionError) as e:
            dialogs.show_error(
                self.winfo_toplevel(),
                "Invalid Aspect Ratio",
                f"Please enter a valid aspect ratio.\n\n"
                f"Examples: 1.333, 0.75, 16:9, 4:3\n\nError: {e}"
            )

    def update_current_aspect_ratio(self, ratio: float):
        """
        Update the current aspect ratio display.

        Args:
            ratio: Current aspect ratio of crop box
        """
        self.current_aspect_label.configure(text=format_aspect_ratio(ratio))

    def get_settings(self) -> dict:
        """
        Get current settings.

        Returns:
            Dictionary with all current settings
        """
        # Parse target size
        target_size_str = self.target_size_var.get()
        if target_size_str == "Custom...":
            try:
                target_mb = float(self.custom_size_var.get())
            except ValueError:
                target_mb = 5.0
        else:
            target_mb = float(target_size_str.replace(" MB", ""))

        # Derive compression from processing mode
        mode = self.processing_mode_var.get()
        enable_compression = mode in ('crop_and_compress', 'compress_only')

        return {
            'preset': self.preset_var.get(),
            'lock_aspect': self.lock_aspect_var.get(),
            'format': self.format_var.get(),
            'quality': self.quality_var.get(),
            'enable_compression': enable_compression,
            'target_size_mb': target_mb,
            'processing_mode': mode,
        }

    def get_current_aspect_ratio_input(self) -> Optional[float]:
        """Get the aspect ratio from the input field, or None if invalid"""
        ratio_str = self.aspect_ratio_var.get().strip()
        if not ratio_str:
            return None

        # Replace comma with period for European decimal format
        ratio_str = ratio_str.replace(',', '.')

        try:
            if ':' in ratio_str:
                parts = ratio_str.split(':')
                return float(parts[0]) / float(parts[1])
            else:
                return float(ratio_str)
        except (ValueError, ZeroDivisionError):
            return None

    def get_crop_anchor(self) -> str:
        """
        Get the selected crop anchor/alignment.

        Returns:
            One of: "Center", "Top", "Bottom", "Left", "Right"
        """
        return self.anchor_var.get()
