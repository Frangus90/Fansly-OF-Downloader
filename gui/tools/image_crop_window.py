"""Main window for bulk image crop tool"""

import customtkinter as ctk
from pathlib import Path
from typing import List, Optional
import threading
import platform
import subprocess
import re

from PIL import Image

from gui.tools.crop_settings_panel import CropSettingsPanel
from gui.tools.crop_canvas import CropCanvas
from gui.tools.batch_queue_panel import BatchQueuePanel
from gui.tools import dialogs

from imageprocessing import ImageProcessor, ImageTask
from imageprocessing.presets import get_preset_aspect_ratio

# Try to import tkinterdnd2 for drag-and-drop support
try:
    from tkinterdnd2 import DND_FILES
    TKDND_AVAILABLE = True
except ImportError:
    TKDND_AVAILABLE = False


class ImageCropWindow(ctk.CTkToplevel):
    """Main window for the image crop tool"""

    def __init__(self, parent, default_output_dir: Optional[Path] = None):
        super().__init__(parent)

        self.title("Bulk Image Crop Tool")
        self.geometry("1200x800")
        self.minsize(900, 600)

        # Set default output directory
        if default_output_dir:
            self.output_dir = default_output_dir
        else:
            self.output_dir = Path.cwd() / "Downloads" / "processed"

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # State
        self.loaded_images: List[Path] = []
        self.current_image_index = -1
        self.processor = ImageProcessor()
        self.is_processing = False
        self.image_crop_settings = {}  # Maps index -> {'crop_rect': (x1,y1,x2,y2), 'aspect_ratio': float}

        # Build UI
        self._build_ui()

        # Bind keyboard shortcuts
        self.bind("<Left>", lambda e: self._navigate_prev())
        self.bind("<Right>", lambda e: self._navigate_next())

        # Setup drag and drop
        self._setup_drag_drop()

        # Bring window to front after it's fully created
        self.after(100, self._bring_to_front)

    def _bring_to_front(self):
        """Bring window to front and keep it on top while open"""
        self.lift()
        self.attributes('-topmost', True)
        self.focus_force()
        # Keep topmost - no use case for downloader window to be on top while cropping

    def _setup_drag_drop(self):
        """Setup drag and drop support for adding images"""
        if not TKDND_AVAILABLE:
            return

        try:
            # Try to load tkdnd package (may already be loaded by main window)
            try:
                self.tk.eval('package require tkdnd')
            except Exception:
                pass  # Already loaded or not available

            # Create a Python callback for drops
            def drop_callback(data):
                self._process_dropped_files(data)
                return 'copy'

            # Register the callback with Tcl
            handler_name = f'drop_handler_{id(self)}'
            self.tk.createcommand(handler_name, drop_callback)

            # Register this window as a drop target and bind the handler
            widget_path = str(self)
            self.tk.eval(f'tkdnd::drop_target register {widget_path} DND_Files')
            self.tk.eval(f'bind {widget_path} <<Drop:DND_Files>> {{ {handler_name} %D }}')

            # Also try to register child widgets after they're created
            self.after(500, self._register_child_drop_targets)
        except Exception:
            # tkdnd not available on this system
            pass

    def _register_child_drop_targets(self):
        """Register child widgets as drop targets for better coverage"""
        try:
            # Create a Python callback for drops (same for all widgets)
            def drop_callback(data):
                self._process_dropped_files(data)
                return 'copy'

            handler_name = f'drop_handler_child_{id(self)}'
            self.tk.createcommand(handler_name, drop_callback)

            # Register the canvas area specifically
            if hasattr(self, 'crop_canvas'):
                canvas_path = str(self.crop_canvas)
                self.tk.eval(f'tkdnd::drop_target register {canvas_path} DND_Files')
                self.tk.eval(f'bind {canvas_path} <<Drop:DND_Files>> {{ {handler_name} %D }}')

            # Register the queue panel
            if hasattr(self, 'queue_panel'):
                queue_path = str(self.queue_panel)
                self.tk.eval(f'tkdnd::drop_target register {queue_path} DND_Files')
                self.tk.eval(f'bind {queue_path} <<Drop:DND_Files>> {{ {handler_name} %D }}')
        except Exception:
            pass

    def _process_dropped_files(self, file_data):
        """Handle files dropped onto the window"""
        if not file_data or not isinstance(file_data, str):
            return

        # Handle different formats:
        # Windows: {C:/path/to/file.jpg} {C:/path/to/file2.png}
        # Linux/Mac: /path/to/file.jpg /path/to/file2.png
        # Files with spaces are wrapped in braces on Windows

        files = []

        # Try to extract brace-enclosed paths first (Windows with spaces)
        brace_pattern = r'\{([^}]+)\}'
        brace_matches = re.findall(brace_pattern, file_data)

        if brace_matches:
            files = brace_matches
        else:
            # Split by spaces for simple paths
            files = file_data.split()

        # Filter for valid image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
        image_files = []

        for f in files:
            # Clean up the path (remove any trailing/leading whitespace or quotes)
            f = f.strip().strip('"').strip("'")
            if not f:
                continue

            path = Path(f)
            if path.suffix.lower() in image_extensions and path.exists():
                image_files.append(path)

        if image_files:
            self._on_images_uploaded(image_files)

    def _build_ui(self):
        """Build the 3-column layout"""
        # Main container
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Configure grid (30% - 50% - 20% split) with minimum sizes to prevent layout shifts
        main_frame.grid_columnconfigure(0, weight=3, minsize=250)  # Left: settings
        main_frame.grid_columnconfigure(1, weight=5, minsize=400)  # Center: canvas
        main_frame.grid_columnconfigure(2, weight=2, minsize=200)  # Right: queue
        main_frame.grid_rowconfigure(0, weight=1)

        # Left panel: Settings
        self.settings_panel = CropSettingsPanel(
            main_frame,
            on_upload_callback=self._on_images_uploaded,
            on_preset_change_callback=self._on_preset_changed,
            on_settings_change_callback=self._on_settings_changed,
            on_aspect_ratio_apply_callback=self._on_aspect_ratio_applied
        )
        self.settings_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # Center panel: Canvas
        self.crop_canvas = CropCanvas(main_frame)
        self.crop_canvas.grid(row=0, column=1, sticky="nsew", padx=5)

        # Set up callbacks
        self.crop_canvas.set_nav_callback(self._on_navigate)
        self.crop_canvas.set_crop_change_callback(self._on_crop_changed)

        # Right panel: Batch queue
        self.queue_panel = BatchQueuePanel(
            main_frame,
            on_select_callback=self._on_queue_item_selected,
            on_remove_callback=self._on_queue_item_removed,
            on_process_callback=self._on_process_batch,
            output_dir=self.output_dir
        )
        self.queue_panel.grid(row=0, column=2, sticky="nsew", padx=(5, 0))

    def _on_crop_changed(self, aspect_ratio: float):
        """Handle crop box changes - update aspect ratio display"""
        self.settings_panel.update_current_aspect_ratio(aspect_ratio)

    def _on_images_uploaded(self, filepaths: List[Path]):
        """Handle images being uploaded"""
        # Store filepaths
        self.loaded_images = filepaths

        # Clear previous crop settings
        self.image_crop_settings.clear()

        # Add to queue panel
        self.queue_panel.add_images(filepaths)

        # Load first image in canvas
        if filepaths:
            self.current_image_index = 0
            self._load_image_in_canvas(0)

        # Bring crop window back to front after file dialog closes
        self.lift()
        self.focus_force()

    def _load_image_in_canvas(self, index: int):
        """Load image at index into canvas"""
        if 0 <= index < len(self.loaded_images):
            filepath = self.loaded_images[index]
            self.current_image_index = index

            # Check if we have saved settings for this image
            saved_settings = self.image_crop_settings.get(index)

            # Load image (no preset dimensions - just load the image)
            self.crop_canvas.load_image(filepath)

            # Restore saved crop if exists
            if saved_settings:
                if saved_settings.get('crop_rect'):
                    self.crop_canvas.set_crop_from_coordinates(saved_settings['crop_rect'])
                if saved_settings.get('aspect_ratio'):
                    self.crop_canvas.set_aspect_ratio(saved_settings['aspect_ratio'])
            else:
                # Get settings from panel
                settings = self.settings_panel.get_settings()
                if settings['lock_aspect']:
                    # If lock is enabled, try to get ratio from current aspect
                    ratio = self.settings_panel.get_current_aspect_ratio_input()
                    if ratio:
                        self.crop_canvas.set_aspect_ratio(ratio)
                else:
                    self.crop_canvas.set_aspect_ratio(None)

            # Update counter
            self.crop_canvas.update_image_counter(index, len(self.loaded_images))

    def _on_queue_item_selected(self, index: int):
        """Handle queue item selection"""
        # Save current before switching
        self._save_current_crop_settings()
        self._load_image_in_canvas(index)

    def _on_queue_item_removed(self, index: int):
        """Handle queue item removal"""
        if 0 <= index < len(self.loaded_images):
            self.loaded_images.pop(index)

            # Remove crop settings for this image and shift others
            new_settings = {}
            for idx, settings in self.image_crop_settings.items():
                if idx < index:
                    new_settings[idx] = settings
                elif idx > index:
                    new_settings[idx - 1] = settings
            self.image_crop_settings = new_settings

            # Load next image or previous
            if self.loaded_images:
                new_index = min(index, len(self.loaded_images) - 1)
                self._load_image_in_canvas(new_index)
            else:
                self.current_image_index = -1

    def _on_preset_changed(self, preset_name: str):
        """Handle preset selection change"""
        # Get aspect ratio for this preset
        ratio = get_preset_aspect_ratio(preset_name)
        if ratio:
            # Apply this ratio to current image
            self.crop_canvas.set_aspect_ratio(ratio)
            self.crop_canvas.update_crop_for_target_size(int(ratio * 1000), 1000)

    def _on_settings_changed(self):
        """Handle settings change"""
        settings = self.settings_panel.get_settings()

        # Update aspect ratio lock
        if not settings['lock_aspect']:
            self.crop_canvas.set_aspect_ratio(None)

    def _on_aspect_ratio_applied(self, ratio: float):
        """Handle aspect ratio input - apply to ALL images in queue"""
        if not self.loaded_images:
            dialogs.show_info(self, "No Images", "Load images first before applying aspect ratio.")
            return

        # Save current crop settings first
        self._save_current_crop_settings()

        # Get anchor/alignment setting
        anchor = self.settings_panel.get_crop_anchor()

        # Apply to ALL images
        for idx, filepath in enumerate(self.loaded_images):
            # Calculate crop box with target aspect ratio for each image
            try:
                with Image.open(filepath) as img:
                    img_w, img_h = img.size

                # Calculate largest crop box with this aspect ratio that fits
                if ratio > img_w / img_h:
                    # Image is taller than target ratio - crop height
                    crop_w = img_w
                    crop_h = int(img_w / ratio)
                else:
                    # Image is wider than target ratio - crop width
                    crop_h = img_h
                    crop_w = int(img_h * ratio)

                # Position crop box based on anchor
                if anchor == "Center":
                    x1 = (img_w - crop_w) // 2
                    y1 = (img_h - crop_h) // 2
                elif anchor == "Top":
                    x1 = (img_w - crop_w) // 2
                    y1 = 0
                elif anchor == "Bottom":
                    x1 = (img_w - crop_w) // 2
                    y1 = img_h - crop_h
                elif anchor == "Left":
                    x1 = 0
                    y1 = (img_h - crop_h) // 2
                elif anchor == "Right":
                    x1 = img_w - crop_w
                    y1 = (img_h - crop_h) // 2
                else:
                    # Default to center
                    x1 = (img_w - crop_w) // 2
                    y1 = (img_h - crop_h) // 2

                x2 = x1 + crop_w
                y2 = y1 + crop_h

                # Store settings for this image
                self.image_crop_settings[idx] = {
                    'crop_rect': (x1, y1, x2, y2),
                    'aspect_ratio': ratio
                }

            except Exception as e:
                print(f"Error calculating crop for {filepath}: {e}")
                continue

        # Set aspect ratio lock on canvas
        self.crop_canvas.set_aspect_ratio(ratio)

        # Reload current image to show the new crop
        if self.current_image_index >= 0:
            self._load_image_in_canvas(self.current_image_index)

        # Show confirmation
        anchor_text = f"aligned to {anchor.lower()}" if anchor != "Center" else "centered"
        dialogs.show_info(
            self,
            "Applied to All",
            f"Aspect ratio {ratio:.3f} applied to {len(self.loaded_images)} image(s).\n\n"
            f"Each image has a crop box {anchor_text}."
        )

    def _on_navigate(self, direction: str):
        """Handle prev/next navigation"""
        if direction == 'prev':
            self._navigate_prev()
        elif direction == 'next':
            self._navigate_next()

    def _navigate_prev(self):
        """Navigate to previous image"""
        if self.current_image_index > 0:
            # Save current crop before switching
            self._save_current_crop_settings()

            # Go to previous
            self._load_image_in_canvas(self.current_image_index - 1)

    def _navigate_next(self):
        """Navigate to next image"""
        if self.current_image_index < len(self.loaded_images) - 1:
            # Save current crop before switching
            self._save_current_crop_settings()

            # Go to next
            self._load_image_in_canvas(self.current_image_index + 1)

    def _save_current_crop_settings(self):
        """Save current image's crop settings"""
        if self.current_image_index >= 0:
            crop_coords = self.crop_canvas.get_crop_coordinates()
            aspect = self.crop_canvas.locked_aspect_ratio

            self.image_crop_settings[self.current_image_index] = {
                'crop_rect': crop_coords,
                'aspect_ratio': aspect
            }

    def _on_process_batch(self):
        """Handle batch processing"""
        if not self.loaded_images:
            dialogs.show_warning(self, "No Images", "No images in queue to process.")
            return

        if self.is_processing:
            dialogs.show_warning(self, "Processing", "Already processing images.")
            return

        # Get output settings
        output_dir = self.queue_panel.get_output_dir()
        settings = self.settings_panel.get_settings()
        output_format = settings['format']

        # Check for existing files
        existing_files = self.processor.check_existing_files(
            self.loaded_images,
            output_dir,
            output_format
        )

        # Determine overwrite mode
        overwrite = False
        skip_existing = False

        if existing_files:
            # Show dialog to ask user what to do
            count = len(existing_files)
            choice = dialogs.ask_overwrite_skip(
                self,
                "Files Already Exist",
                f"{count} file(s) already exist in the output folder.\n\n"
                f"What would you like to do?"
            )

            if choice is None:
                # User cancelled
                return
            elif choice == "overwrite":
                overwrite = True
            elif choice == "skip":
                skip_existing = True
        else:
            # No conflicts, confirm with user
            result = dialogs.ask_yes_no(
                self,
                "Process Batch",
                f"Process {len(self.loaded_images)} image(s) with current settings?\n\n"
                f"Output: {output_dir}"
            )

            if not result:
                return

        # Store the processing options for the thread
        self._process_overwrite = overwrite
        self._process_skip_existing = skip_existing

        # Start processing in background thread
        self.is_processing = True
        self.queue_panel.set_processing_state(True)

        thread = threading.Thread(target=self._process_batch_thread, daemon=True)
        thread.start()

    def _process_batch_thread(self):
        """Background thread for batch processing"""
        try:
            # Get settings
            settings = self.settings_panel.get_settings()

            # Save current crop settings before processing
            self._save_current_crop_settings()

            # Build processor queue with per-image settings
            self.processor.clear_queue()

            for idx, filepath in enumerate(self.loaded_images):
                # Get saved settings for this image
                saved = self.image_crop_settings.get(idx, {})
                crop_coords = saved.get('crop_rect')

                task = ImageTask(
                    filepath=filepath,
                    crop_rect=crop_coords,
                    target_size=None,  # No resizing, just crop
                    format=settings['format'],
                    quality=settings['quality'],
                    padding=settings['padding']
                )
                self.processor.add_to_queue(task)

            # Process batch with overwrite/skip options
            output_dir = self.queue_panel.get_output_dir()
            output_files = self.processor.process_batch(
                output_dir,
                progress_callback=self._on_progress_update,
                overwrite=self._process_overwrite,
                skip_existing=self._process_skip_existing
            )

            # Notify completion on main thread
            self.after(0, self._on_batch_complete, output_files)

        except Exception as e:
            # Show error on main thread
            self.after(0, lambda: dialogs.show_error(self, "Processing Error", f"Error processing batch:\n{str(e)}"))
            self.after(0, self._reset_processing_state)

    def _on_progress_update(self, current: int, total: int, filename: str):
        """Handle progress update from processor"""
        # Truncate long filenames to prevent layout shifts
        if len(filename) > 20:
            filename = filename[:17] + "..."
        # Update UI on main thread
        self.after(0, self.queue_panel.update_progress, current, total, filename)

    def _on_batch_complete(self, output_files: List[Path]):
        """Handle batch processing completion"""
        self.is_processing = False
        self.queue_panel.set_processing_state(False)

        if output_files:
            # Show success dialog
            message = f"Successfully processed {len(output_files)} image(s)!\n\n"
            message += f"Saved to:\n{output_files[0].parent}"

            result = dialogs.ask_yes_no(
                self,
                "Batch Processing Complete",
                message + "\n\nOpen output folder?"
            )

            if result:
                self._open_folder(output_files[0].parent)
        else:
            dialogs.show_warning(
                self,
                "Processing Complete",
                "No images were successfully processed.\n\nCheck the log for errors."
            )

    def _reset_processing_state(self):
        """Reset processing state after error"""
        self.is_processing = False
        self.queue_panel.set_processing_state(False)

    def _open_folder(self, folder: Path):
        """Open folder in file explorer"""
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.run(["explorer", str(folder)], check=False)
            elif system == "Darwin":
                subprocess.run(["open", str(folder)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as e:
            print(f"Error opening folder: {e}")
