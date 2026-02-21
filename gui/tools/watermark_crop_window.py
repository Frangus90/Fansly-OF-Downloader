"""GUI window for watermark auto-crop tool"""

import customtkinter as ctk
import logging
import shutil
import tkinter as tk
from io import BytesIO
from pathlib import Path
from typing import List, Optional
from tkinter import filedialog
import threading
import platform
import subprocess
import re

from PIL import Image, ImageDraw

from imageprocessing.watermark_crop import (
    WatermarkDetector,
    load_blacklist,
    save_blacklist,
)
from imageprocessing.ocr_env import is_ocr_installed, install_ocr_env, detect_cuda
from imageprocessing.crop import crop_image, save_image
from imageprocessing.presets import get_last_output_dir, save_last_output_dir
from gui.tools import dialogs

try:
    from tkinterdnd2 import DND_FILES
    TKDND_AVAILABLE = True
except ImportError:
    TKDND_AVAILABLE = False


_FORMAT_MAP = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".bmp": "BMP",
    ".tiff": "TIFF",
    ".tif": "TIFF",
}


def _extension_to_format(ext: str) -> str:
    """Map a file extension (e.g. '.png') to a Pillow format string."""
    return _FORMAT_MAP.get(ext.lower(), "JPEG")


class WatermarkCropWindow(ctk.CTkToplevel):
    """Window for automatic watermark detection and cropping"""

    def __init__(self, parent, default_output_dir: Optional[Path] = None):
        super().__init__(parent)

        self.title("Watermark Auto-Crop")
        self.geometry("1100x750")
        self.minsize(850, 550)

        # Output directory
        if default_output_dir:
            self.output_dir = default_output_dir
        else:
            last_dir = get_last_output_dir()
            self.output_dir = last_dir if last_dir else Path.cwd() / "Downloads" / "processed"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.loaded_images: List[Path] = []
        self.current_image_index = -1
        self.is_processing = False
        self.detector = WatermarkDetector()

        # Thread-safe OCR cache
        self._ocr_cache: dict[int, tuple[list, list]] = {}
        self._cache_lock = threading.Lock()

        self._build_ui()
        self._setup_drag_drop()
        self.after(100, self._bring_to_front)

    def _bring_to_front(self):
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()

    def destroy(self):
        super().destroy()

    # -- Drag and drop (reuse pattern from image_crop_window) --

    def _setup_drag_drop(self):
        if not TKDND_AVAILABLE:
            return
        try:
            try:
                self.tk.eval("package require tkdnd")
            except Exception:
                pass

            def drop_callback(data):
                self._process_dropped_files(data)
                return "copy"

            handler_name = f"wm_drop_handler_{id(self)}"
            self.tk.createcommand(handler_name, drop_callback)
            widget_path = str(self)
            self.tk.eval(f"tkdnd::drop_target register {widget_path} DND_Files")
            self.tk.eval(
                f'bind {widget_path} <<Drop:DND_Files>> {{ {handler_name} %D }}'
            )
        except Exception:
            pass

    def _process_dropped_files(self, file_data):
        if not file_data or not isinstance(file_data, str):
            return

        files = []
        brace_matches = re.findall(r"\{([^}]+)\}", file_data)
        if brace_matches:
            files = brace_matches
        else:
            files = file_data.split()

        image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
        image_files = []
        for f in files:
            f = f.strip().strip('"').strip("'")
            if not f:
                continue
            path = Path(f)
            if path.suffix.lower() in image_extensions and path.exists():
                image_files.append(path)

        if image_files:
            self._on_images_loaded(image_files)

    # -- UI Layout --

    def _build_ui(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 3-column: settings | preview | queue
        main_frame.grid_columnconfigure(0, weight=2, minsize=220)
        main_frame.grid_columnconfigure(1, weight=5, minsize=400)
        main_frame.grid_columnconfigure(2, weight=2, minsize=200)
        main_frame.grid_rowconfigure(0, weight=1)

        self._build_settings_panel(main_frame)
        self._build_preview_panel(main_frame)
        self._build_queue_panel(main_frame)

    def _build_settings_panel(self, parent):
        panel = ctk.CTkFrame(parent)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Title
        title = ctk.CTkLabel(
            panel, text="Watermark Auto-Crop", font=("Arial", 16, "bold"), anchor="w"
        )
        title.pack(padx=15, pady=(15, 5), anchor="w")

        # EasyOCR status
        if is_ocr_installed():
            status_text = "EasyOCR: Ready"
            status_color = "#28a745"
        else:
            status_text = "EasyOCR: Not Installed"
            status_color = "#dc3545"
        self.ocr_status_label = ctk.CTkLabel(
            panel,
            text=status_text,
            font=("Arial", 10),
            text_color=status_color,
            anchor="w",
        )
        self.ocr_status_label.pack(padx=15, pady=(0, 5), anchor="w")

        if not is_ocr_installed():
            install_btn = ctk.CTkButton(
                panel,
                text="Install EasyOCR",
                command=self._on_install_easyocr,
                height=28,
                font=("Arial", 10),
                fg_color="#ffc107",
                text_color="#000000",
                hover_color="#e0a800",
            )
            install_btn.pack(fill="x", padx=15, pady=(0, 10))
        else:
            ctk.CTkLabel(panel, text="", height=5).pack()

        # Upload button
        self.upload_btn = ctk.CTkButton(
            panel,
            text="Upload Images...",
            command=self._on_upload,
            height=35,
            font=("Arial", 12),
        )
        self.upload_btn.pack(fill="x", padx=15, pady=(0, 10))

        # Blacklist section
        bl_label = ctk.CTkLabel(
            panel, text="Word Blacklist", font=("Arial", 13, "bold"), anchor="w"
        )
        bl_label.pack(padx=15, pady=(10, 2), anchor="w")

        bl_hint = ctk.CTkLabel(
            panel,
            text="One word per line. Images with matching text\nwill have the watermark band cropped.",
            font=("Arial", 10),
            text_color="gray60",
            anchor="w",
            justify="left",
        )
        bl_hint.pack(padx=15, pady=(0, 5), anchor="w")

        self.blacklist_textbox = ctk.CTkTextbox(panel, height=150, font=("Arial", 12))
        self.blacklist_textbox.pack(fill="x", padx=15, pady=(0, 5))

        # Load saved blacklist
        saved_words = load_blacklist()
        if saved_words:
            self.blacklist_textbox.insert("1.0", "\n".join(saved_words))

        # Save blacklist button
        save_bl_btn = ctk.CTkButton(
            panel,
            text="Save Blacklist",
            command=self._on_save_blacklist,
            height=28,
            font=("Arial", 10),
            fg_color="transparent",
            border_width=1,
            border_color="#3b8ed0",
            text_color="#3b8ed0",
        )
        save_bl_btn.pack(fill="x", padx=15, pady=(0, 10))

        # Crop all detected text checkbox
        self.crop_all_var = ctk.BooleanVar(value=False)
        self.crop_all_checkbox = ctk.CTkCheckBox(
            panel,
            text="Crop all detected text",
            variable=self.crop_all_var,
            font=("Arial", 11),
            command=self._on_update_preview,
        )
        self.crop_all_checkbox.pack(padx=15, pady=(0, 5), anchor="w")

        crop_all_hint = ctk.CTkLabel(
            panel,
            text="Bypass blacklist - treat all text as watermark",
            font=("Arial", 9),
            text_color="gray60",
            anchor="w",
        )
        crop_all_hint.pack(padx=15, pady=(0, 10), anchor="w")

        # OCR sensitivity
        sens_label = ctk.CTkLabel(
            panel, text="OCR Sensitivity", font=("Arial", 13, "bold"), anchor="w"
        )
        sens_label.pack(padx=15, pady=(5, 2), anchor="w")

        sens_frame = ctk.CTkFrame(panel, fg_color="transparent")
        sens_frame.pack(fill="x", padx=15, pady=(0, 5))

        self.sensitivity_var = ctk.StringVar(value="Normal")
        self.sensitivity_menu = ctk.CTkOptionMenu(
            sens_frame,
            values=["Low", "Normal", "High", "Max"],
            variable=self.sensitivity_var,
            width=120,
            height=28,
        )
        self.sensitivity_menu.pack(side="left")

        sens_hint = ctk.CTkLabel(
            panel,
            text="Higher = detects faint text but slower",
            font=("Arial", 9),
            text_color="gray60",
            anchor="w",
        )
        sens_hint.pack(padx=15, pady=(0, 10), anchor="w")

        # Margin setting
        margin_frame = ctk.CTkFrame(panel, fg_color="transparent")
        margin_frame.pack(fill="x", padx=15, pady=(5, 5))

        margin_label = ctk.CTkLabel(
            margin_frame, text="Crop Margin (px):", font=("Arial", 11), anchor="w"
        )
        margin_label.pack(side="left")

        self.margin_var = ctk.StringVar(value="5")
        margin_entry = ctk.CTkEntry(
            margin_frame, textvariable=self.margin_var, width=60, height=28
        )
        margin_entry.pack(side="right")

        # Update preview button
        self.update_preview_btn = ctk.CTkButton(
            panel,
            text="Update Preview",
            command=self._on_update_preview,
            height=28,
            font=("Arial", 10),
            fg_color="transparent",
            border_width=1,
            border_color="#5bc0de",
            text_color="#5bc0de",
            state="disabled",
        )
        self.update_preview_btn.pack(fill="x", padx=15, pady=(5, 5))

        # Scan current button
        self.scan_btn = ctk.CTkButton(
            panel,
            text="Scan Current Image",
            command=self._on_scan_current,
            height=35,
            font=("Arial", 12),
            fg_color="#5bc0de",
            state="disabled",
        )
        self.scan_btn.pack(fill="x", padx=15, pady=(15, 5))

        # Scan all button
        self.scan_all_btn = ctk.CTkButton(
            panel,
            text="Scan All Images",
            command=self._on_scan_all,
            height=35,
            font=("Arial", 12),
            fg_color="#17a2b8",
            state="disabled",
        )
        self.scan_all_btn.pack(fill="x", padx=15, pady=(5, 5))

        # Detection results
        self.detection_label = ctk.CTkLabel(
            panel,
            text="No scan results yet",
            font=("Arial", 10),
            text_color="gray60",
            anchor="w",
            justify="left",
            wraplength=200,
        )
        self.detection_label.pack(padx=15, pady=(5, 10), anchor="w")

    def _build_preview_panel(self, parent):
        preview_frame = ctk.CTkFrame(parent)
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=5)

        # Navigation bar
        nav_frame = ctk.CTkFrame(preview_frame, fg_color="transparent")
        nav_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.prev_btn = ctk.CTkButton(
            nav_frame, text="< Prev", width=70, command=self._navigate_prev, state="disabled"
        )
        self.prev_btn.pack(side="left")

        self.counter_label = ctk.CTkLabel(
            nav_frame, text="0 / 0", font=("Arial", 12)
        )
        self.counter_label.pack(side="left", expand=True)

        self.next_btn = ctk.CTkButton(
            nav_frame, text="Next >", width=70, command=self._navigate_next, state="disabled"
        )
        self.next_btn.pack(side="right")

        # Canvas for image preview
        self.preview_canvas = ctk.CTkCanvas(
            preview_frame, bg="#1a1a1a", highlightthickness=0
        )
        self.preview_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Status bar
        self.preview_status = ctk.CTkLabel(
            preview_frame,
            text="Upload images to begin",
            font=("Arial", 10),
            text_color="gray60",
        )
        self.preview_status.pack(padx=10, pady=(0, 10))

        # Bind resize
        self.preview_canvas.bind("<Configure>", self._on_canvas_resize)

        # Keyboard shortcuts
        self.bind("<Left>", lambda e: self._navigate_prev())
        self.bind("<Right>", lambda e: self._navigate_next())

    def _build_queue_panel(self, parent):
        panel = ctk.CTkFrame(parent)
        panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0))

        # Title
        title = ctk.CTkLabel(
            panel, text="Batch Queue", font=("Arial", 16, "bold"), anchor="w"
        )
        title.pack(padx=10, pady=(15, 5), anchor="w")

        # Scrollable queue list
        self.queue_frame = ctk.CTkScrollableFrame(panel, height=300)
        self.queue_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.empty_label = ctk.CTkLabel(
            self.queue_frame,
            text="No images loaded",
            font=("Arial", 11),
            text_color="gray60",
        )
        self.empty_label.pack(pady=30)

        # Queue items list (for reference cleanup)
        self.queue_widgets: list[dict] = []

        # Controls
        controls = ctk.CTkFrame(panel)
        controls.pack(fill="x", padx=10, pady=10)

        # Progress
        self.progress_bar = ctk.CTkProgressBar(controls)
        self.progress_bar.pack(fill="x", padx=5, pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            controls, text="0/0", font=("Arial", 10), text_color="gray60"
        )
        self.progress_label.pack(padx=5, pady=(0, 5))

        # Output dir
        output_label = ctk.CTkLabel(
            controls, text="Output Directory", font=("Arial", 11, "bold"), anchor="w"
        )
        output_label.pack(padx=5, pady=(5, 2), anchor="w")

        self.output_path_label = ctk.CTkLabel(
            controls,
            text=str(self.output_dir),
            font=("Arial", 9),
            text_color="gray60",
            anchor="w",
        )
        self.output_path_label.pack(padx=5, pady=2, anchor="w")

        browse_btn = ctk.CTkButton(
            controls,
            text="Change Output Dir...",
            command=self._browse_output_dir,
            height=25,
            font=("Arial", 10),
        )
        browse_btn.pack(fill="x", padx=5, pady=5)

        # Process all button
        self.process_btn = ctk.CTkButton(
            controls,
            text="Process All",
            command=self._on_process_all,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="#28a745",
            state="disabled",
        )
        self.process_btn.pack(fill="x", pady=(10, 5))

    # -- Image loading --

    def _on_upload(self):
        if self.is_processing:
            return

        filepaths = filedialog.askopenfilenames(
            parent=self,
            title="Select Images",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.webp *.gif *.bmp"),
                ("All files", "*.*"),
            ],
        )
        self.lift()
        self.focus_force()

        if filepaths:
            self._on_images_loaded([Path(p) for p in filepaths])

    def _on_images_loaded(self, filepaths: List[Path]):
        if self.is_processing:
            return

        self.loaded_images = filepaths
        with self._cache_lock:
            self._ocr_cache.clear()

        # Rebuild queue list
        self._rebuild_queue()

        if filepaths:
            self.current_image_index = 0
            self._display_image(0)
            self.scan_btn.configure(state="normal")
            self.scan_all_btn.configure(state="normal")
            self.update_preview_btn.configure(state="normal")
            self.process_btn.configure(state="normal")

        self._update_nav_state()

    def _rebuild_queue(self):
        # Clear old widgets
        for item in self.queue_widgets:
            item["frame"].destroy()
        self.queue_widgets.clear()

        if not self.loaded_images:
            self.empty_label.pack(pady=30)
            return

        self.empty_label.pack_forget()

        for idx, filepath in enumerate(self.loaded_images):
            frame = ctk.CTkFrame(self.queue_frame)
            frame.pack(fill="x", pady=2)

            name_label = ctk.CTkLabel(
                frame,
                text=filepath.name if len(filepath.name) <= 25 else filepath.name[:22] + "...",
                anchor="w",
                font=("Arial", 10),
            )
            name_label.pack(side="left", fill="x", expand=True, padx=10, pady=5)

            # Status indicator
            status_label = ctk.CTkLabel(
                frame, text="--", font=("Arial", 10), text_color="gray60", width=50
            )
            status_label.pack(side="right", padx=10)

            frame.bind("<Button-1>", lambda e, i=idx: self._on_queue_click(i))
            name_label.bind("<Button-1>", lambda e, i=idx: self._on_queue_click(i))

            self.queue_widgets.append(
                {"frame": frame, "status_label": status_label}
            )

        self.progress_label.configure(text=f"0/{len(self.loaded_images)}")

    def _on_queue_click(self, index: int):
        if 0 <= index < len(self.loaded_images):
            self.current_image_index = index
            self._display_image(index)
            self._update_nav_state()

    # -- Navigation --

    def _navigate_prev(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self._display_image(self.current_image_index)
            self._update_nav_state()

    def _navigate_next(self):
        if self.current_image_index < len(self.loaded_images) - 1:
            self.current_image_index += 1
            self._display_image(self.current_image_index)
            self._update_nav_state()

    def _update_nav_state(self):
        total = len(self.loaded_images)
        current = self.current_image_index + 1 if total > 0 else 0
        self.counter_label.configure(text=f"{current} / {total}")
        self.prev_btn.configure(
            state="normal" if self.current_image_index > 0 else "disabled"
        )
        self.next_btn.configure(
            state="normal"
            if self.current_image_index < total - 1
            else "disabled"
        )

    # -- Image display --

    def _display_image(self, index: int):
        """Display image at index with any cached detection overlays."""
        if index < 0 or index >= len(self.loaded_images):
            return

        filepath = self.loaded_images[index]
        try:
            img = Image.open(filepath)
        except Exception as e:
            self.preview_status.configure(text=f"Error: {e}")
            return

        # Draw detection overlays if cached
        with self._cache_lock:
            cached = self._ocr_cache.get(index)

        if cached is not None:
            all_detections, cached_matches = cached
            # When "crop all" is on, treat every detection as a match for preview
            matches = list(all_detections) if self.crop_all_var.get() else cached_matches
            img = self._draw_detections(img, all_detections, matches)

        self._render_on_canvas(img)

        # Update status
        if cached is not None:
            if matches:
                texts = ", ".join(d["text"] for d in matches)
                self.preview_status.configure(text=f"Watermark found: {texts}")
            else:
                self.preview_status.configure(text="No watermark detected")
        else:
            self.preview_status.configure(text=f"{filepath.name}")

        # Highlight queue item
        for i, item in enumerate(self.queue_widgets):
            if i == index:
                item["frame"].configure(fg_color=["#3b8ed0", "#1f538d"])
            else:
                item["frame"].configure(fg_color=["gray90", "gray13"])

    def _draw_detections(
        self, img: Image.Image, all_detections: list, matches: list
    ) -> Image.Image:
        """Draw bounding boxes and crop line on image."""
        img = img.copy().convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        match_ids = {id(d) for d in matches}
        margin = self._get_margin()

        for detection in all_detections:
            y_min, y_max, x_min, x_max = detection["bbox"]
            is_match = id(detection) in match_ids

            if is_match:
                # Red box around matched text
                draw.rectangle(
                    [x_min, y_min, x_max, y_max], outline=(255, 0, 0, 200), width=3
                )
            else:
                # Gray box for non-matching text
                draw.rectangle(
                    [x_min, y_min, x_max, y_max], outline=(150, 150, 150, 120), width=1
                )

        # Draw the actual crop region using calculate_crop_box
        if matches:
            crop_box = self.detector.calculate_crop_box(
                img.width, img.height, matches, margin
            )
            if crop_box:
                _, keep_top, _, keep_bottom = crop_box
                # Shade cropped-away regions in red
                if keep_top > 0:
                    draw.rectangle(
                        [0, 0, img.width, keep_top],
                        fill=(255, 0, 0, 60),
                    )
                    # Crop line
                    draw.line(
                        [(0, keep_top), (img.width, keep_top)],
                        fill=(255, 0, 0, 220), width=3,
                    )
                if keep_bottom < img.height:
                    draw.rectangle(
                        [0, keep_bottom, img.width, img.height],
                        fill=(255, 0, 0, 60),
                    )
                    # Crop line
                    draw.line(
                        [(0, keep_bottom), (img.width, keep_bottom)],
                        fill=(255, 0, 0, 220), width=3,
                    )

        result = Image.alpha_composite(img, overlay)
        return result.convert("RGB")

    def _render_on_canvas(self, img: Image.Image):
        """Render PIL image onto the canvas, scaled to fit."""
        canvas_w = self.preview_canvas.winfo_width()
        canvas_h = self.preview_canvas.winfo_height()

        if canvas_w < 10 or canvas_h < 10:
            return

        # Scale to fit
        scale = min(canvas_w / img.width, canvas_h / img.height)
        display_w = int(img.width * scale)
        display_h = int(img.height * scale)

        display_img = img.resize((display_w, display_h), Image.Resampling.LANCZOS)

        # Convert to PhotoImage
        self._photo = tk.PhotoImage(data=self._pil_to_ppm(display_img))
        self.preview_canvas.delete("all")

        x = (canvas_w - display_w) // 2
        y = (canvas_h - display_h) // 2
        self.preview_canvas.create_image(x, y, anchor="nw", image=self._photo)

    @staticmethod
    def _pil_to_ppm(img: Image.Image) -> bytes:
        """Convert PIL image to PPM bytes for tk.PhotoImage."""
        buf = BytesIO()
        img.convert("RGB").save(buf, format="PPM")
        return buf.getvalue()

    def _on_canvas_resize(self, event):
        """Re-render current image on canvas resize."""
        if self.current_image_index >= 0:
            self._display_image(self.current_image_index)

    # -- OCR scanning --

    _SENSITIVITY_PRESETS = {
        "Low":    {"text_threshold": 0.9,  "low_text": 0.5, "mag_ratio": 1.0},
        "Normal": {"text_threshold": 0.7,  "low_text": 0.4, "mag_ratio": 1.0},
        "High":   {"text_threshold": 0.4,  "low_text": 0.3, "mag_ratio": 1.5},
        "Max":    {"text_threshold": 0.2,  "low_text": 0.2, "mag_ratio": 2.0},
    }

    def _get_ocr_params(self) -> dict:
        """Get OCR parameters based on the selected sensitivity preset."""
        preset = self.sensitivity_var.get()
        return self._SENSITIVITY_PRESETS.get(preset, self._SENSITIVITY_PRESETS["Normal"])

    def _get_blacklist(self) -> list[str]:
        text = self.blacklist_textbox.get("1.0", "end").strip()
        if not text:
            return []
        return [line.strip() for line in text.split("\n") if line.strip()]

    def _get_margin(self) -> int:
        try:
            return max(0, int(self.margin_var.get()))
        except ValueError:
            return 5

    def _on_save_blacklist(self):
        words = self._get_blacklist()
        save_blacklist(words)
        dialogs.show_info(self, "Saved", f"Blacklist saved ({len(words)} words).")

    def _on_update_preview(self):
        """Re-render the current image preview with the current margin setting."""
        if self.current_image_index >= 0:
            self._display_image(self.current_image_index)

    def _on_scan_current(self):
        """Scan the current image for watermarks in a background thread."""
        if self.current_image_index < 0 or self.is_processing:
            return

        crop_all = self.crop_all_var.get()
        blacklist = self._get_blacklist()
        if not blacklist and not crop_all:
            dialogs.show_warning(
                self, "No Blacklist",
                "Add at least one word to the blacklist,\n"
                "or enable 'Crop all detected text'."
            )
            return

        if not is_ocr_installed():
            dialogs.show_error(
                self,
                "EasyOCR Not Installed",
                "Use the Install EasyOCR button to set up OCR.",
            )
            return

        self.scan_btn.configure(state="disabled", text="Scanning...")
        self.detection_label.configure(text="Running OCR...")

        index = self.current_image_index
        filepath = self.loaded_images[index]
        ocr_params = self._get_ocr_params()

        thread = threading.Thread(
            target=self._scan_thread,
            args=(index, filepath, blacklist, crop_all, ocr_params),
            daemon=True,
        )
        thread.start()

    def _scan_thread(self, index: int, filepath: Path, blacklist: list[str],
                     crop_all: bool, ocr_params: dict):
        try:
            all_detections = self.detector.detect_text(str(filepath), **ocr_params)
            if crop_all:
                matches = list(all_detections)
            else:
                matches = self.detector.find_blacklisted_regions(all_detections, blacklist)

            with self._cache_lock:
                self._ocr_cache[index] = (all_detections, matches)

            def update_ui():
                self.scan_btn.configure(state="normal", text="Scan Current Image")

                if index < len(self.queue_widgets):
                    if matches:
                        self.queue_widgets[index]["status_label"].configure(
                            text="Found", text_color="#dc3545"
                        )
                    else:
                        self.queue_widgets[index]["status_label"].configure(
                            text="Clean", text_color="#28a745"
                        )

                # Update detection label
                if all_detections:
                    lines = [f"Detected {len(all_detections)} text region(s):"]
                    for d in all_detections:
                        lines.append(f'  "{d["text"]}"')
                    if matches:
                        lines.append(f"\nMatched {len(matches)}:")
                        for m in matches:
                            lines.append(f'  "{m["text"]}"')
                    else:
                        lines.append("\nNo blacklist matches")
                    self.detection_label.configure(text="\n".join(lines))
                else:
                    self.detection_label.configure(text="No text detected in image")

                # Redraw with overlays
                if self.current_image_index == index:
                    self._display_image(index)

            self.after(0, update_ui)

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            logging.getLogger("ocr_env").error(f"Scan error:\n{error_detail}")

            def show_error():
                self.scan_btn.configure(state="normal", text="Scan Current Image")
                self.detection_label.configure(text=f"Error: {e}")

            self.after(0, show_error)

    # -- Batch scanning --

    def _on_scan_all(self):
        """Scan all loaded images for watermarks in a background thread."""
        if not self.loaded_images or self.is_processing:
            return

        crop_all = self.crop_all_var.get()
        blacklist = self._get_blacklist()
        if not blacklist and not crop_all:
            dialogs.show_warning(
                self, "No Blacklist",
                "Add at least one word to the blacklist,\n"
                "or enable 'Crop all detected text'."
            )
            return

        if not is_ocr_installed():
            dialogs.show_error(
                self,
                "EasyOCR Not Installed",
                "Use the Install EasyOCR button to set up OCR.",
            )
            return

        self.is_processing = True
        self.scan_btn.configure(state="disabled")
        self.scan_all_btn.configure(state="disabled", text="Scanning...")
        self.upload_btn.configure(state="disabled")
        self.process_btn.configure(state="disabled")

        ocr_params = self._get_ocr_params()
        thread = threading.Thread(
            target=self._scan_all_thread,
            args=(blacklist, crop_all, ocr_params),
            daemon=True,
        )
        thread.start()

    def _scan_all_thread(self, blacklist: list[str], crop_all: bool, ocr_params: dict):
        total = len(self.loaded_images)
        match_count = 0

        for idx, filepath in enumerate(self.loaded_images):
            try:
                self.after(
                    0,
                    self._update_scan_all_progress,
                    idx + 1,
                    total,
                    filepath.name,
                )

                all_detections = self.detector.detect_text(str(filepath), **ocr_params)
                if crop_all:
                    matches = list(all_detections)
                else:
                    matches = self.detector.find_blacklisted_regions(
                        all_detections, blacklist
                    )

                with self._cache_lock:
                    self._ocr_cache[idx] = (all_detections, matches)

                if matches:
                    match_count += 1

                def update_queue_status(i=idx, m=matches):
                    if i < len(self.queue_widgets):
                        if m:
                            self.queue_widgets[i]["status_label"].configure(
                                text="Found", text_color="#dc3545"
                            )
                        else:
                            self.queue_widgets[i]["status_label"].configure(
                                text="Clean", text_color="#28a745"
                            )

                self.after(0, update_queue_status)

            except Exception as e:
                import traceback
                logging.getLogger("ocr_env").error(
                    f"Batch scan error on {filepath}:\n{traceback.format_exc()}"
                )
                def mark_error(i=idx):
                    if i < len(self.queue_widgets):
                        self.queue_widgets[i]["status_label"].configure(
                            text="Error", text_color="#ffc107"
                        )
                self.after(0, mark_error)

        def on_complete(found=match_count):
            self._reset_processing_state()
            self.detection_label.configure(
                text=f"Batch scan complete\n"
                     f"Scanned {total} image(s)\n"
                     f"Watermarks found: {found}"
            )
            if self.current_image_index >= 0:
                self._display_image(self.current_image_index)

        self.after(0, on_complete)

    def _update_scan_all_progress(self, current: int, total: int, filename: str):
        display_name = filename if len(filename) <= 20 else filename[:17] + "..."
        self.scan_all_btn.configure(text=f"Scanning {current}/{total}...")
        self.detection_label.configure(text=f"Scanning {current}/{total}\n{display_name}")

    # -- Batch processing --

    def _on_process_all(self):
        if not self.loaded_images or self.is_processing:
            return

        # Lock UI immediately before any blocking dialog
        self.is_processing = True
        self.process_btn.configure(state="disabled", text="Processing...")
        self.scan_btn.configure(state="disabled")
        self.scan_all_btn.configure(state="disabled")
        self.upload_btn.configure(state="disabled")

        crop_all = self.crop_all_var.get()
        blacklist = self._get_blacklist()
        if not blacklist and not crop_all:
            self._reset_processing_state()
            dialogs.show_warning(
                self, "No Blacklist",
                "Add at least one word to the blacklist,\n"
                "or enable 'Crop all detected text'."
            )
            return

        if not is_ocr_installed():
            self._reset_processing_state()
            dialogs.show_error(
                self,
                "EasyOCR Not Installed",
                "Use the Install EasyOCR button to set up OCR.",
            )
            return

        result = dialogs.ask_yes_no(
            self,
            "Process All Images",
            f"Scan and crop {len(self.loaded_images)} image(s)?\n\n"
            f"{'Mode: Crop ALL detected text' if crop_all else 'Mode: Blacklist matching'}\n"
            f"Images without watermarks will be copied as-is.\n\n"
            f"Output: {self.output_dir}",
        )
        if not result:
            self._reset_processing_state()
            return

        margin = self._get_margin()
        ocr_params = self._get_ocr_params()

        thread = threading.Thread(
            target=self._process_all_thread,
            args=(blacklist, margin, crop_all, ocr_params),
            daemon=True,
        )
        thread.start()

    def _reset_processing_state(self):
        """Reset UI state after processing ends or is cancelled."""
        self.is_processing = False
        self.process_btn.configure(state="normal", text="Process All")
        self.scan_btn.configure(state="normal", text="Scan Current Image")
        self.scan_all_btn.configure(state="normal", text="Scan All Images")
        self.upload_btn.configure(state="normal")

    def _process_all_thread(self, blacklist: list[str], margin: int,
                            crop_all: bool, ocr_params: dict):
        total = len(self.loaded_images)
        processed = 0
        cropped_count = 0
        skipped_count = 0
        failed: list[tuple[Path, str]] = []

        for idx, filepath in enumerate(self.loaded_images):
            try:
                # Update progress on main thread
                self.after(
                    0,
                    self._update_progress,
                    idx + 1,
                    total,
                    filepath.name,
                )

                # Use cached results if available
                with self._cache_lock:
                    cached = self._ocr_cache.get(idx)

                if cached is not None:
                    all_detections, matches = cached
                else:
                    all_detections = self.detector.detect_text(
                        str(filepath), **ocr_params
                    )
                    if crop_all:
                        matches = list(all_detections)
                    else:
                        matches = self.detector.find_blacklisted_regions(
                            all_detections, blacklist
                        )
                    with self._cache_lock:
                        self._ocr_cache[idx] = (all_detections, matches)

                # Update queue status
                def update_status(i=idx, m=matches):
                    if i < len(self.queue_widgets):
                        if m:
                            self.queue_widgets[i]["status_label"].configure(
                                text="Found", text_color="#dc3545"
                            )
                        else:
                            self.queue_widgets[i]["status_label"].configure(
                                text="Clean", text_color="#28a745"
                            )

                self.after(0, update_status)

                output_path = self.output_dir / filepath.name

                if matches:
                    # Crop the watermark
                    with Image.open(filepath) as img:
                        crop_box = self.detector.calculate_crop_box(
                            img.width, img.height, matches, margin
                        )
                        if crop_box:
                            cropped = crop_image(img.copy(), *crop_box)
                            self.output_dir.mkdir(parents=True, exist_ok=True)
                            fmt = _extension_to_format(filepath.suffix)
                            save_image(cropped, output_path, format=fmt)
                            cropped_count += 1
                        else:
                            shutil.copy2(filepath, output_path)
                            skipped_count += 1
                else:
                    shutil.copy2(filepath, output_path)
                    skipped_count += 1

                processed += 1

            except Exception as e:
                failed.append((filepath, str(e)))

        # Done
        self.after(0, self._on_process_complete, processed, cropped_count, skipped_count, failed)

    def _update_progress(self, current: int, total: int, filename: str):
        if total > 0:
            self.progress_bar.set(current / total)
            display_name = filename if len(filename) <= 20 else filename[:17] + "..."
            self.progress_label.configure(text=f"{current}/{total} - {display_name}")

    def _on_process_complete(
        self,
        processed: int,
        cropped: int,
        skipped: int,
        failed: list[tuple[Path, str]],
    ):
        message = f"Processed {processed} image(s).\n\n"
        message += f"Cropped: {cropped}\n"
        message += f"Copied as-is: {skipped}\n"
        if failed:
            message += f"Failed: {len(failed)}\n"

        message += f"\nSaved to:\n{self.output_dir}"

        open_folder = dialogs.ask_yes_no(
            self, "Processing Complete", message + "\n\nOpen output folder?"
        )

        # Reset state after dialog dismissed
        self._reset_processing_state()

        if open_folder:
            self._open_folder(self.output_dir)

    # -- EasyOCR install --

    def _on_install_easyocr(self):
        """Install EasyOCR via embedded Python environment."""
        import sys as _sys

        if not getattr(_sys, "frozen", False):
            result = dialogs.ask_yes_no(
                self,
                "Install EasyOCR",
                "This will run:\n  pip install easyocr\n\n"
                "This downloads ~1-2 GB of ML dependencies.\n"
                "Continue?",
            )
            if not result:
                return

            self.ocr_status_label.configure(
                text="Installing EasyOCR...", text_color="#ffc107"
            )
            self.update()

            thread = threading.Thread(
                target=self._install_easyocr_source, daemon=True,
            )
            thread.start()
            return

        cuda_ver = detect_cuda()
        if cuda_ver:
            gpu_msg = (
                f"NVIDIA GPU detected (CUDA {cuda_ver}).\n"
                f"PyTorch will be installed with GPU acceleration.\n\n"
                f"Total download: ~3 GB\n"
            )
        else:
            gpu_msg = (
                "No NVIDIA GPU detected.\n"
                "PyTorch will be installed in CPU-only mode.\n\n"
                "Total download: ~1.5 GB\n"
            )

        result = dialogs.ask_yes_no(
            self,
            "Install EasyOCR",
            f"This will download a Python runtime and EasyOCR.\n\n"
            f"{gpu_msg}"
            f"Continue?",
        )
        if not result:
            return

        self.ocr_status_label.configure(
            text="Starting install...", text_color="#ffc107"
        )
        self.update()

        thread = threading.Thread(
            target=self._install_easyocr_embedded, daemon=True,
        )
        thread.start()

    def _install_progress(self, message: str, progress: float):
        """Thread-safe progress callback for install_ocr_env."""
        self._last_install_status = message
        is_done = progress == 1.0
        def update():
            color = "#28a745" if is_done else "#ffc107"
            self.ocr_status_label.configure(text=message, text_color=color)
        self.after(0, update)

    def _install_easyocr_embedded(self):
        """Install via embedded Python (frozen exe)."""
        self._last_install_status = "EasyOCR: Ready"
        try:
            install_ocr_env(callback=self._install_progress)

            final_status = self._last_install_status
            def on_success():
                self.ocr_status_label.configure(
                    text=final_status, text_color="#28a745",
                )
                dialogs.show_info(
                    self, "Installed",
                    "EasyOCR installed successfully.\n"
                    "You can start scanning immediately.",
                )
            self.after(0, on_success)
        except Exception as e:
            def on_error():
                self.ocr_status_label.configure(
                    text="EasyOCR: Install failed", text_color="#dc3545"
                )
                dialogs.show_error(self, "Install Error", str(e)[:500])
            self.after(0, on_error)

    def _install_easyocr_source(self):
        """Install via pip into current environment (running from source)."""
        import sys as _sys
        try:
            result = subprocess.run(
                [_sys.executable, "-m", "pip", "install", "easyocr"],
                capture_output=True, text=True, timeout=900,
            )
            if result.returncode == 0:
                def on_success():
                    self.ocr_status_label.configure(
                        text="EasyOCR: Ready", text_color="#28a745",
                    )
                    dialogs.show_info(
                        self, "Installed",
                        "EasyOCR installed successfully.",
                    )
                self.after(0, on_success)
            else:
                def on_fail():
                    self.ocr_status_label.configure(
                        text="EasyOCR: Install failed", text_color="#dc3545"
                    )
                    dialogs.show_error(
                        self, "Install Failed",
                        f"pip returned error:\n{result.stderr[:500]}",
                    )
                self.after(0, on_fail)
        except Exception as e:
            def on_error():
                self.ocr_status_label.configure(
                    text="EasyOCR: Install failed", text_color="#dc3545"
                )
                dialogs.show_error(self, "Install Error", str(e))
            self.after(0, on_error)

    # -- Utilities --

    def _browse_output_dir(self):
        directory = filedialog.askdirectory(
            parent=self, title="Select Output Directory", initialdir=self.output_dir
        )
        self.lift()
        self.focus_force()

        if directory:
            self.output_dir = Path(directory)
            self.output_path_label.configure(text=str(self.output_dir))
            save_last_output_dir(self.output_dir)

    def _open_folder(self, folder: Path):
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", str(folder)], check=False)
            elif system == "Darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as e:
            self.preview_status.configure(text=f"Could not open folder: {e}")
