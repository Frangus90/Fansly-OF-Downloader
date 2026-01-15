"""Two-mode compression panel for Quick and Advanced modes.

Provides a clean, simplified interface for image compression with:
- Quick mode: Target size with automatic optimization
- Advanced mode: Full manual control over all settings
"""

import customtkinter as ctk
from typing import Optional, Callable, Dict, Any

from imageprocessing.compression import (
    get_available_formats,
    get_encoder,
    AVIF_AVAILABLE,
    MOZJPEG_AVAILABLE,
    SSIM_AVAILABLE,
)
from imageprocessing.compression.encoders import CHROMA_LABELS


class CompressionPanel(ctk.CTkFrame):
    """Two-mode compression settings panel.

    Provides Quick mode (target size) and Advanced mode (manual control).
    """

    # Target size presets in MB
    SIZE_PRESETS = [2, 5, 10, 20]

    def __init__(
        self,
        parent,
        on_settings_changed: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """Initialize compression panel.

        Args:
            parent: Parent widget
            on_settings_changed: Callback when any setting changes
            **kwargs: Additional frame options
        """
        super().__init__(parent, **kwargs)

        self.on_settings_changed = on_settings_changed

        # Mode state
        self.mode_var = ctk.StringVar(value="quick")

        # Quick mode variables
        self.quick_target_var = ctk.StringVar(value="5")
        self.quick_format_var = ctk.StringVar(value="AUTO")
        self.quick_custom_size_var = ctk.StringVar(value="5.0")

        # Advanced mode variables
        self.adv_format_var = ctk.StringVar(value="JPEG")
        self.adv_quality_var = ctk.IntVar(value=85)
        self.adv_enable_target_var = ctk.BooleanVar(value=False)
        self.adv_target_var = ctk.StringVar(value="5.0")
        self.adv_min_quality_var = ctk.IntVar(value=60)
        self.adv_chroma_var = ctk.IntVar(value=2)
        self.adv_progressive_var = ctk.BooleanVar(value=False)
        self.adv_mozjpeg_var = ctk.BooleanVar(value=True)
        self.adv_ssim_enabled_var = ctk.BooleanVar(value=False)
        self.adv_ssim_threshold_var = ctk.StringVar(value="0.95")

        self._build_ui()

    def _build_ui(self):
        """Build the panel UI."""
        # Mode selector
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            mode_frame, text="Compression Mode", font=("Arial", 12, "bold")
        ).pack(anchor="w")

        mode_buttons = ctk.CTkFrame(mode_frame, fg_color="transparent")
        mode_buttons.pack(fill="x", pady=(5, 0))

        self.quick_btn = ctk.CTkButton(
            mode_buttons,
            text="Quick",
            command=lambda: self._set_mode("quick"),
            width=80,
            height=28,
        )
        self.quick_btn.pack(side="left", padx=(0, 5))

        self.adv_btn = ctk.CTkButton(
            mode_buttons,
            text="Advanced",
            command=lambda: self._set_mode("advanced"),
            width=80,
            height=28,
            fg_color="transparent",
            border_width=1,
            border_color="#3b8ed0",
            text_color="#3b8ed0",
        )
        self.adv_btn.pack(side="left")

        # Content frames (switch between these)
        self.quick_frame = self._build_quick_mode()
        self.adv_frame = self._build_advanced_mode()

        # Show quick mode by default
        self.quick_frame.pack(fill="x", expand=True)

    def _build_quick_mode(self) -> ctk.CTkFrame:
        """Build Quick mode UI."""
        frame = ctk.CTkFrame(self, fg_color="transparent")

        # Target size section
        size_label = ctk.CTkLabel(
            frame, text="Target Size", font=("Arial", 11, "bold")
        )
        size_label.pack(anchor="w", pady=(10, 5))

        # Preset buttons
        presets_frame = ctk.CTkFrame(frame, fg_color="transparent")
        presets_frame.pack(fill="x", pady=(0, 5))

        for size in self.SIZE_PRESETS:
            btn = ctk.CTkButton(
                presets_frame,
                text=f"{size} MB",
                command=lambda s=size: self._set_quick_target(str(s)),
                width=55,
                height=28,
                fg_color="transparent" if self.quick_target_var.get() != str(size) else None,
                border_width=1,
                border_color="#3b8ed0",
            )
            btn.pack(side="left", padx=(0, 5))

        # Custom size
        custom_frame = ctk.CTkFrame(frame, fg_color="transparent")
        custom_frame.pack(fill="x", pady=(5, 0))

        ctk.CTkLabel(custom_frame, text="Custom:").pack(side="left")

        self.custom_entry = ctk.CTkEntry(
            custom_frame,
            textvariable=self.quick_custom_size_var,
            width=60,
            height=28,
        )
        self.custom_entry.pack(side="left", padx=(5, 0))
        self.custom_entry.bind("<Return>", lambda e: self._apply_custom_size())
        self.custom_entry.bind("<FocusOut>", lambda e: self._apply_custom_size())

        ctk.CTkLabel(custom_frame, text="MB").pack(side="left", padx=(5, 0))

        # Format selection
        format_label = ctk.CTkLabel(
            frame, text="Format", font=("Arial", 11, "bold")
        )
        format_label.pack(anchor="w", pady=(15, 5))

        format_options = ["AUTO"] + get_available_formats()
        self.quick_format_menu = ctk.CTkOptionMenu(
            frame,
            values=format_options,
            variable=self.quick_format_var,
            command=self._on_setting_changed,
            width=150,
        )
        self.quick_format_menu.pack(anchor="w")

        format_hint = ctk.CTkLabel(
            frame,
            text="AUTO tries JPEG > WebP > AVIF (quality first)",
            font=("Arial", 10),
            text_color="gray",
        )
        format_hint.pack(anchor="w", pady=(2, 0))

        return frame

    def _build_advanced_mode(self) -> ctk.CTkFrame:
        """Build Advanced mode UI."""
        frame = ctk.CTkFrame(self, fg_color="transparent")

        # Format selection
        format_label = ctk.CTkLabel(
            frame, text="Format", font=("Arial", 11, "bold")
        )
        format_label.pack(anchor="w", pady=(10, 5))

        self.adv_format_menu = ctk.CTkOptionMenu(
            frame,
            values=get_available_formats(),
            variable=self.adv_format_var,
            command=self._on_format_changed,
            width=150,
        )
        self.adv_format_menu.pack(anchor="w")

        # Quality slider
        quality_label = ctk.CTkLabel(
            frame, text="Quality", font=("Arial", 11, "bold")
        )
        quality_label.pack(anchor="w", pady=(15, 5))

        quality_frame = ctk.CTkFrame(frame, fg_color="transparent")
        quality_frame.pack(fill="x")

        self.quality_slider = ctk.CTkSlider(
            quality_frame,
            from_=1,
            to=100,
            variable=self.adv_quality_var,
            command=self._on_quality_changed,
            width=180,
        )
        self.quality_slider.pack(side="left")

        self.quality_value_label = ctk.CTkLabel(
            quality_frame,
            textvariable=self.adv_quality_var,
            width=30,
        )
        self.quality_value_label.pack(side="left", padx=(10, 0))

        # Target size (optional)
        target_frame = ctk.CTkFrame(frame, fg_color="transparent")
        target_frame.pack(fill="x", pady=(15, 0))

        self.target_checkbox = ctk.CTkCheckBox(
            target_frame,
            text="Target file size:",
            variable=self.adv_enable_target_var,
            command=self._on_target_toggle,
        )
        self.target_checkbox.pack(side="left")

        self.target_entry = ctk.CTkEntry(
            target_frame,
            textvariable=self.adv_target_var,
            width=60,
            height=28,
            state="disabled",
        )
        self.target_entry.pack(side="left", padx=(10, 0))

        ctk.CTkLabel(target_frame, text="MB").pack(side="left", padx=(5, 0))

        # Quality floor (when target enabled)
        self.floor_frame = ctk.CTkFrame(frame, fg_color="transparent")

        ctk.CTkLabel(self.floor_frame, text="Quality floor:").pack(side="left")

        self.floor_slider = ctk.CTkSlider(
            self.floor_frame,
            from_=30,
            to=90,
            variable=self.adv_min_quality_var,
            command=self._on_setting_changed,
            width=120,
        )
        self.floor_slider.pack(side="left", padx=(10, 0))

        self.floor_value_label = ctk.CTkLabel(
            self.floor_frame,
            textvariable=self.adv_min_quality_var,
            width=30,
        )
        self.floor_value_label.pack(side="left")

        # JPEG Options (collapsible)
        self.jpeg_options_frame = self._build_jpeg_options(frame)

        # Quality validation (collapsible)
        self.validation_frame = self._build_validation_options(frame)

        return frame

    def _build_jpeg_options(self, parent) -> ctk.CTkFrame:
        """Build JPEG-specific options section."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")

        # Header with toggle
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(15, 0))

        self.jpeg_toggle_var = ctk.BooleanVar(value=False)
        toggle_btn = ctk.CTkButton(
            header,
            text="JPEG Options",
            command=self._toggle_jpeg_options,
            width=120,
            height=24,
            fg_color="transparent",
            text_color="#3b8ed0",
            anchor="w",
        )
        toggle_btn.pack(side="left")

        # Options content (hidden by default)
        self.jpeg_content = ctk.CTkFrame(frame, fg_color="transparent")

        # Chroma subsampling
        chroma_frame = ctk.CTkFrame(self.jpeg_content, fg_color="transparent")
        chroma_frame.pack(fill="x", pady=(5, 0))

        ctk.CTkLabel(chroma_frame, text="Color:").pack(side="left")

        chroma_options = [CHROMA_LABELS[i] for i in [0, 1, 2]]
        self.chroma_menu = ctk.CTkOptionMenu(
            chroma_frame,
            values=chroma_options,
            command=self._on_chroma_changed,
            width=150,
        )
        self.chroma_menu.set(CHROMA_LABELS[2])  # Default: Smallest
        self.chroma_menu.pack(side="left", padx=(10, 0))

        # Progressive
        self.progressive_check = ctk.CTkCheckBox(
            self.jpeg_content,
            text="Progressive loading",
            variable=self.adv_progressive_var,
            command=self._on_setting_changed,
        )
        self.progressive_check.pack(anchor="w", pady=(5, 0))

        # MozJPEG
        mozjpeg_text = "MozJPEG optimization"
        if not MOZJPEG_AVAILABLE:
            mozjpeg_text += " (not installed)"

        self.mozjpeg_check = ctk.CTkCheckBox(
            self.jpeg_content,
            text=mozjpeg_text,
            variable=self.adv_mozjpeg_var,
            command=self._on_setting_changed,
            state="normal" if MOZJPEG_AVAILABLE else "disabled",
        )
        self.mozjpeg_check.pack(anchor="w", pady=(5, 0))

        return frame

    def _build_validation_options(self, parent) -> ctk.CTkFrame:
        """Build quality validation options section."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")

        # Header with toggle
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(10, 0))

        toggle_btn = ctk.CTkButton(
            header,
            text="Quality Check",
            command=self._toggle_validation_options,
            width=120,
            height=24,
            fg_color="transparent",
            text_color="#3b8ed0",
            anchor="w",
        )
        toggle_btn.pack(side="left")

        # Options content (hidden by default)
        self.validation_content = ctk.CTkFrame(frame, fg_color="transparent")

        ssim_text = "SSIM validation"
        if not SSIM_AVAILABLE:
            ssim_text += " (requires scikit-image)"

        ssim_frame = ctk.CTkFrame(self.validation_content, fg_color="transparent")
        ssim_frame.pack(fill="x", pady=(5, 0))

        self.ssim_check = ctk.CTkCheckBox(
            ssim_frame,
            text=ssim_text,
            variable=self.adv_ssim_enabled_var,
            command=self._on_ssim_toggle,
            state="normal" if SSIM_AVAILABLE else "disabled",
        )
        self.ssim_check.pack(side="left")

        ctk.CTkLabel(ssim_frame, text="Threshold:").pack(side="left", padx=(15, 0))

        self.ssim_entry = ctk.CTkEntry(
            ssim_frame,
            textvariable=self.adv_ssim_threshold_var,
            width=50,
            height=24,
            state="disabled",
        )
        self.ssim_entry.pack(side="left", padx=(5, 0))

        return frame

    def _set_mode(self, mode: str):
        """Switch between Quick and Advanced modes."""
        self.mode_var.set(mode)

        # Default button color in customtkinter
        default_color = "#3b8ed0"

        if mode == "quick":
            self.quick_btn.configure(
                fg_color=default_color,
                border_width=0,
                text_color="white",
            )
            self.adv_btn.configure(
                fg_color="transparent",
                border_width=1,
                text_color=default_color,
            )
            self.adv_frame.pack_forget()
            self.quick_frame.pack(fill="x", expand=True)
        else:
            self.adv_btn.configure(
                fg_color=default_color,
                border_width=0,
                text_color="white",
            )
            self.quick_btn.configure(
                fg_color="transparent",
                border_width=1,
                text_color=default_color,
            )
            self.quick_frame.pack_forget()
            self.adv_frame.pack(fill="x", expand=True)

        self._notify_changed()

    def _set_quick_target(self, size: str):
        """Set quick mode target size."""
        self.quick_target_var.set(size)
        self.quick_custom_size_var.set(size + ".0")
        self._notify_changed()

    def _apply_custom_size(self):
        """Apply custom size from entry."""
        try:
            size = float(self.quick_custom_size_var.get())
            if 0.1 <= size <= 100:
                self.quick_target_var.set("custom")
                self._notify_changed()
        except ValueError:
            pass

    def _on_format_changed(self, value: str):
        """Handle format change in advanced mode."""
        # Show/hide JPEG options based on format
        if value == "JPEG":
            self.jpeg_options_frame.pack(fill="x", after=self.adv_format_menu)
        else:
            self.jpeg_options_frame.pack_forget()

        self._notify_changed()

    def _on_quality_changed(self, value: float):
        """Handle quality slider change."""
        self._notify_changed()

    def _on_target_toggle(self):
        """Handle target size checkbox toggle."""
        enabled = self.adv_enable_target_var.get()
        state = "normal" if enabled else "disabled"

        self.target_entry.configure(state=state)

        if enabled:
            self.floor_frame.pack(fill="x", pady=(5, 0))
            self.quality_slider.configure(state="disabled")
        else:
            self.floor_frame.pack_forget()
            self.quality_slider.configure(state="normal")

        self._notify_changed()

    def _on_chroma_changed(self, value: str):
        """Handle chroma subsampling change."""
        # Map label back to value
        for val, label in CHROMA_LABELS.items():
            if label == value:
                self.adv_chroma_var.set(val)
                break
        self._notify_changed()

    def _on_ssim_toggle(self):
        """Handle SSIM checkbox toggle."""
        enabled = self.adv_ssim_enabled_var.get()
        self.ssim_entry.configure(state="normal" if enabled else "disabled")
        self._notify_changed()

    def _toggle_jpeg_options(self):
        """Toggle JPEG options visibility."""
        if self.jpeg_content.winfo_manager():
            self.jpeg_content.pack_forget()
        else:
            self.jpeg_content.pack(fill="x")

    def _toggle_validation_options(self):
        """Toggle validation options visibility."""
        if self.validation_content.winfo_manager():
            self.validation_content.pack_forget()
        else:
            self.validation_content.pack(fill="x")

    def _on_setting_changed(self, *args):
        """Generic setting change handler."""
        self._notify_changed()

    def _notify_changed(self):
        """Notify that settings have changed."""
        if self.on_settings_changed:
            self.on_settings_changed()

    def get_settings(self) -> Dict[str, Any]:
        """Get current compression settings.

        Returns:
            Dict with all compression settings
        """
        mode = self.mode_var.get()

        if mode == "quick":
            # Get target size
            if self.quick_target_var.get() == "custom":
                try:
                    target_mb = float(self.quick_custom_size_var.get())
                except ValueError:
                    target_mb = 5.0
            else:
                target_mb = float(self.quick_target_var.get())

            return {
                'mode': 'quick',
                'target_mb': target_mb,
                'format': self.quick_format_var.get(),
                'min_quality': 60,
            }
        else:
            settings = {
                'mode': 'advanced',
                'format': self.adv_format_var.get(),
                'quality': self.adv_quality_var.get(),
                'target_mb': None,
                'min_quality': self.adv_min_quality_var.get(),
                'chroma_subsampling': self.adv_chroma_var.get(),
                'progressive': self.adv_progressive_var.get(),
                'use_mozjpeg': self.adv_mozjpeg_var.get() and MOZJPEG_AVAILABLE,
                'calculate_ssim': self.adv_ssim_enabled_var.get() and SSIM_AVAILABLE,
                'ssim_threshold': None,
            }

            if self.adv_enable_target_var.get():
                try:
                    settings['target_mb'] = float(self.adv_target_var.get())
                except ValueError:
                    settings['target_mb'] = 5.0

            if settings['calculate_ssim']:
                try:
                    settings['ssim_threshold'] = float(self.adv_ssim_threshold_var.get())
                except ValueError:
                    settings['ssim_threshold'] = 0.95

            return settings

    def set_settings(self, settings: Dict[str, Any]):
        """Apply settings to the panel.

        Args:
            settings: Dict with compression settings
        """
        mode = settings.get('mode', 'quick')
        self._set_mode(mode)

        if mode == 'quick':
            target = settings.get('target_mb', 5.0)
            self.quick_custom_size_var.set(str(target))
            if target in self.SIZE_PRESETS:
                self.quick_target_var.set(str(int(target)))
            else:
                self.quick_target_var.set("custom")

            self.quick_format_var.set(settings.get('format', 'AUTO'))

        else:
            self.adv_format_var.set(settings.get('format', 'JPEG'))
            self.adv_quality_var.set(settings.get('quality', 85))

            target_mb = settings.get('target_mb')
            if target_mb is not None:
                self.adv_enable_target_var.set(True)
                self.adv_target_var.set(str(target_mb))
            else:
                self.adv_enable_target_var.set(False)

            self.adv_min_quality_var.set(settings.get('min_quality', 60))
            self.adv_chroma_var.set(settings.get('chroma_subsampling', 2))
            self.adv_progressive_var.set(settings.get('progressive', False))
            self.adv_mozjpeg_var.set(settings.get('use_mozjpeg', True))
            self.adv_ssim_enabled_var.set(settings.get('calculate_ssim', False))

            threshold = settings.get('ssim_threshold')
            if threshold is not None:
                self.adv_ssim_threshold_var.set(str(threshold))

            # Update UI state
            self._on_target_toggle()
            self._on_format_changed(self.adv_format_var.get())

    def is_compression_enabled(self) -> bool:
        """Check if compression is enabled.

        Returns:
            True if compression will be applied
        """
        if self.mode_var.get() == "quick":
            return True
        return self.adv_enable_target_var.get()

    def get_target_mb(self) -> Optional[float]:
        """Get target size in MB.

        Returns:
            Target size or None if not targeting size
        """
        settings = self.get_settings()
        return settings.get('target_mb')
