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
from gui.tools.compare_slider_canvas import CompareSliderCanvas
from gui.tools.batch_queue_panel import BatchQueuePanel
from gui.tools import dialogs

from imageprocessing import ImageProcessor, ImageTask
from imageprocessing.presets import (
    get_preset_aspect_ratio,
    get_preset_anchor,
    get_preset_data,
    get_last_output_dir,
)

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
            # Try to load last used output directory
            last_dir = get_last_output_dir()
            if last_dir:
                self.output_dir = last_dir
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

        # Compression preview state
        self._compression_preview_timer = None
        self._compression_preview_cancel_event = threading.Event()

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

    def destroy(self):
        """Override destroy to clean up background operations"""
        # Cancel any pending compression preview timer
        if self._compression_preview_timer is not None:
            try:
                self.after_cancel(self._compression_preview_timer)
            except Exception:
                pass
            self._compression_preview_timer = None

        # Signal any running preview threads to stop
        if hasattr(self, '_compression_preview_cancel_event'):
            self._compression_preview_cancel_event.set()

        # Call parent destroy
        super().destroy()

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

        # Center panel: Tabbed preview area
        self.preview_tabview = ctk.CTkTabview(main_frame)
        self.preview_tabview.grid(row=0, column=1, sticky="nsew", padx=5)

        # Add tabs
        self.preview_tabview.add("Crop Preview")
        self.preview_tabview.add("Compress Preview")

        # Crop canvas in first tab
        self.crop_canvas = CropCanvas(self.preview_tabview.tab("Crop Preview"))
        self.crop_canvas.pack(fill="both", expand=True)

        # Compare canvas in second tab
        self.compare_canvas = CompareSliderCanvas(
            self.preview_tabview.tab("Compress Preview"),
            on_request_comparison=self._on_request_comparison
        )
        self.compare_canvas.pack(fill="both", expand=True)

        # Tab change handler
        self.preview_tabview.configure(command=self._on_tab_changed)

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

    def _calculate_crop_dimensions(self, img_w: int, img_h: int, ratio: float) -> tuple[int, int]:
        """Calculate largest crop box with given aspect ratio that fits image.

        Args:
            img_w: Image width in pixels
            img_h: Image height in pixels
            ratio: Desired aspect ratio (width / height)

        Returns:
            (crop_w, crop_h) tuple with crop box dimensions
        """
        if ratio > img_w / img_h:
            # Image is taller than target ratio - crop height
            return img_w, int(img_w / ratio)
        else:
            # Image is wider than target ratio - crop width
            return int(img_h * ratio), img_h

    def _calculate_anchor_position(
        self,
        img_w: int,
        img_h: int,
        crop_w: int,
        crop_h: int,
        anchor: str
    ) -> tuple[int, int]:
        """Calculate crop box position based on anchor point.

        Args:
            img_w: Image width in pixels
            img_h: Image height in pixels
            crop_w: Crop box width
            crop_h: Crop box height
            anchor: Anchor position ("Center", "Top", "Bottom", "Left", "Right")

        Returns:
            (x1, y1) tuple with top-left corner coordinates
        """
        anchor_positions = {
            "Center": ((img_w - crop_w) // 2, (img_h - crop_h) // 2),
            "Top": ((img_w - crop_w) // 2, 0),
            "Bottom": ((img_w - crop_w) // 2, img_h - crop_h),
            "Left": (0, (img_h - crop_h) // 2),
            "Right": (img_w - crop_w, (img_h - crop_h) // 2),
        }
        return anchor_positions.get(anchor, anchor_positions["Center"])

    def _on_crop_changed(self, aspect_ratio: float):
        """Handle crop box changes - update aspect ratio display"""
        self.settings_panel.update_current_aspect_ratio(aspect_ratio)
        # Schedule compression preview update
        self._schedule_compression_preview()

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

            # Get settings from panel to check lock state
            settings = self.settings_panel.get_settings()

            # Restore saved crop if exists
            if saved_settings:
                if saved_settings.get('crop_rect'):
                    self.crop_canvas.set_crop_from_coordinates(saved_settings['crop_rect'])
                # Only restore aspect ratio if lock checkbox is currently checked
                if settings['lock_aspect'] and saved_settings.get('aspect_ratio'):
                    self.crop_canvas.set_aspect_ratio(saved_settings['aspect_ratio'])
                elif not settings['lock_aspect']:
                    self.crop_canvas.set_aspect_ratio(None)
            else:
                # No saved settings - use current panel settings
                if settings['lock_aspect']:
                    # If lock is enabled, try to get ratio from current aspect
                    ratio = self.settings_panel.get_current_aspect_ratio_input()
                    if ratio:
                        self.crop_canvas.set_aspect_ratio(ratio)
                else:
                    self.crop_canvas.set_aspect_ratio(None)

            # Update counter
            self.crop_canvas.update_image_counter(index, len(self.loaded_images))

            # Schedule compression preview update
            self._schedule_compression_preview()

            # Also update comparison if on Compress Preview tab
            if self.preview_tabview.get() == "Compress Preview":
                self._generate_compression_comparison()

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
        # Get preset data (aspect ratio and anchor)
        preset_data = get_preset_data(preset_name)
        if not preset_data:
            return
        
        ratio = preset_data.get('aspect_ratio')
        anchor = preset_data.get('anchor', 'Center')
        
        if ratio:
            # Update anchor dropdown to match preset
            self.settings_panel.anchor_var.set(anchor)
            
            # Check if lock is enabled before applying aspect ratio
            settings = self.settings_panel.get_settings()
            if settings['lock_aspect']:
                # Lock is enabled - apply aspect ratio lock
                self.crop_canvas.set_aspect_ratio(ratio)
            else:
                # Lock is disabled - don't set aspect ratio lock
                self.crop_canvas.set_aspect_ratio(None)
            
            # Apply preset to current image with the saved anchor
            # This calculates and sets the crop box with the correct aspect ratio and alignment
            if self.current_image_index >= 0 and self.loaded_images:
                self._apply_aspect_ratio_to_current_image(ratio, anchor)

    def _on_settings_changed(self):
        """Handle settings change"""
        settings = self.settings_panel.get_settings()

        # Update aspect ratio lock
        if settings['lock_aspect']:
            # Lock is ON - get ratio from input field and apply it
            ratio = self.settings_panel.get_current_aspect_ratio_input()
            if ratio:
                self.crop_canvas.set_aspect_ratio(ratio)
        else:
            # Lock is OFF - clear aspect ratio
            self.crop_canvas.set_aspect_ratio(None)

        # Schedule compression preview update
        self._schedule_compression_preview()

    def _apply_aspect_ratio_to_current_image(self, ratio: float, anchor: str):
        """Apply aspect ratio and anchor to the current image only"""
        if self.current_image_index < 0 or not self.loaded_images:
            return
        
        filepath = self.loaded_images[self.current_image_index]
        
        try:
            with Image.open(filepath) as img:
                img_w, img_h = img.size

            # Calculate crop dimensions and position
            crop_w, crop_h = self._calculate_crop_dimensions(img_w, img_h, ratio)
            x1, y1 = self._calculate_anchor_position(img_w, img_h, crop_w, crop_h, anchor)
            x2 = x1 + crop_w
            y2 = y1 + crop_h

            # Store settings for this image
            self.image_crop_settings[self.current_image_index] = {
                'crop_rect': (x1, y1, x2, y2),
                'aspect_ratio': ratio
            }
            
            # Update canvas to show the new crop
            self.crop_canvas.set_crop_from_coordinates((x1, y1, x2, y2))
            
        except Exception as e:
            print(f"Error applying aspect ratio to current image: {e}")

    def _on_aspect_ratio_applied(self, ratio: float):
        """Handle aspect ratio input - apply to selected images (or all if none selected)"""
        if not self.loaded_images:
            dialogs.show_info(self, "No Images", "Load images first before applying aspect ratio.")
            return

        # Save current crop settings first
        self._save_current_crop_settings()

        # Get anchor/alignment setting
        anchor = self.settings_panel.get_crop_anchor()

        # Get selected indices from queue panel - if none selected, apply to all
        selected_indices = self.queue_panel.get_selected_indices()
        if not selected_indices:
            # No selection - apply to all images
            indices_to_apply = list(range(len(self.loaded_images)))
        else:
            indices_to_apply = selected_indices

        # Apply to selected images (or all if none selected)
        for idx in indices_to_apply:
            if idx >= len(self.loaded_images):
                continue
            filepath = self.loaded_images[idx]
            # Calculate crop box with target aspect ratio for each image
            try:
                with Image.open(filepath) as img:
                    img_w, img_h = img.size

                # Calculate crop dimensions and position
                crop_w, crop_h = self._calculate_crop_dimensions(img_w, img_h, ratio)
                x1, y1 = self._calculate_anchor_position(img_w, img_h, crop_w, crop_h, anchor)
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

        # Only set aspect ratio lock if checkbox is currently checked
        # Don't force the checkbox state - respect user's choice
        settings = self.settings_panel.get_settings()
        if settings['lock_aspect']:
            # Lock is enabled - apply aspect ratio lock
            self.crop_canvas.set_aspect_ratio(ratio)
        else:
            # Lock is disabled - don't lock aspect ratio
            self.crop_canvas.set_aspect_ratio(None)

        # Reload current image to show the new crop
        if self.current_image_index >= 0:
            self._load_image_in_canvas(self.current_image_index)

        # Show confirmation
        anchor_text = f"aligned to {anchor.lower()}" if anchor != "Center" else "centered"
        applied_count = len(indices_to_apply)
        if selected_indices:
            title = "Applied to Selected"
            message = f"Aspect ratio {ratio:.3f} applied to {applied_count} selected image(s).\n\n"
        else:
            title = "Applied to All"
            message = f"Aspect ratio {ratio:.3f} applied to all {applied_count} image(s).\n\n"
        dialogs.show_info(
            self,
            title,
            message + f"Each image has a crop box {anchor_text}."
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

                # Determine operations based on processing mode
                mode = settings.get('processing_mode', 'crop_and_compress')

                if mode == 'crop_only':
                    crop_coords = saved.get('crop_rect')
                    enable_compression = False
                    target_size_mb = None
                elif mode == 'compress_only':
                    # Compress only - no crop, always compress
                    crop_coords = None
                    enable_compression = True
                    target_size_mb = settings.get('target_size_mb', 5.0)
                else:  # crop_and_compress
                    # Both operations - crop and always compress
                    crop_coords = saved.get('crop_rect')
                    enable_compression = True
                    target_size_mb = settings.get('target_size_mb', 5.0)

                task = ImageTask(
                    filepath=filepath,
                    crop_rect=crop_coords,
                    target_size=None,  # No resizing, just crop
                    format=settings['format'],
                    quality=settings['quality'],
                    target_file_size_mb=target_size_mb,
                    enable_size_compression=enable_compression,
                    # Advanced compression options
                    min_compression_quality=settings.get('min_quality', 75),
                    progressive_jpeg=settings.get('progressive', False),
                    chroma_subsampling=settings.get('chroma_subsampling', 2),
                    use_mozjpeg=settings.get('use_mozjpeg', False),
                    ssim_threshold=settings.get('ssim_threshold'),
                )
                self.processor.add_to_queue(task)

            # Process batch with overwrite/skip options
            output_dir = self.queue_panel.get_output_dir()
            result = self.processor.process_batch(
                output_dir,
                progress_callback=self._on_progress_update,
                overwrite=self._process_overwrite,
                skip_existing=self._process_skip_existing
            )

            # Notify completion on main thread
            self.after(0, self._on_batch_complete, result)

        except Exception as e:
            # Reset state IMMEDIATELY, then show error on main thread
            self.is_processing = False
            self.after(0, lambda: dialogs.show_error(self, "Processing Error", f"Error processing batch:\n{str(e)}"))
            self.after(0, self._reset_processing_state)

    def _on_progress_update(self, current: int, total: int, filename: str):
        """Handle progress update from processor"""
        # Truncate long filenames to prevent layout shifts
        if len(filename) > 20:
            filename = filename[:17] + "..."
        # Update UI on main thread
        self.after(0, self.queue_panel.update_progress, current, total, filename)

    def _on_batch_complete(self, result: dict):
        """Handle batch processing completion"""
        self.is_processing = False
        self.queue_panel.set_processing_state(False)

        # Extract results from dict
        output_files = result.get('success', [])
        failed_files = result.get('failed', [])
        skipped = result.get('skipped', 0)

        if output_files:
            # Show success dialog with details
            message = f"Successfully processed {len(output_files)} image(s)!"

            if failed_files:
                message += f"\n{len(failed_files)} file(s) failed."

            if skipped > 0:
                message += f"\n{skipped} file(s) skipped (already exist)."

            message += f"\n\nSaved to:\n{output_files[0].parent}"

            open_folder = dialogs.ask_yes_no(
                self,
                "Batch Processing Complete",
                message + "\n\nOpen output folder?"
            )

            if open_folder:
                self._open_folder(output_files[0].parent)

        elif failed_files:
            # All files failed
            error_details = "\n".join([f"• {path.name}: {err}" for path, err in failed_files[:5]])
            if len(failed_files) > 5:
                error_details += f"\n... and {len(failed_files) - 5} more"

            dialogs.show_error(
                self,
                "Processing Failed",
                f"All {len(failed_files)} file(s) failed to process:\n\n{error_details}"
            )
        else:
            dialogs.show_warning(
                self,
                "Processing Complete",
                "No images were processed.\n\nAll files may have been skipped."
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

    # Compression Preview Methods
    def _schedule_compression_preview(self):
        """Schedule compression preview with 300ms debounce"""
        # Cancel any pending preview
        if self._compression_preview_timer is not None:
            self.after_cancel(self._compression_preview_timer)

        # Schedule new preview after 300ms
        self._compression_preview_timer = self.after(300, self._start_compression_preview)

    def _start_compression_preview(self):
        """Start compression preview in background thread"""
        self._compression_preview_timer = None

        # Cancel any existing preview computation
        if hasattr(self, '_compression_preview_cancel_event'):
            self._compression_preview_cancel_event.set()

        # Create new cancel event
        cancel_event = threading.Event()
        self._compression_preview_cancel_event = cancel_event

        # Show computing state
        self.settings_panel.update_estimated_file_size(None, is_computing=True)

        # Start background computation
        thread = threading.Thread(
            target=self._compute_compression_preview,
            args=(cancel_event,),
            daemon=True
        )
        thread.start()

    def _compute_compression_preview(self, cancel_event):
        """Compute estimated file size in background thread

        Args:
            cancel_event: Threading event to signal cancellation
        """
        try:
            # Check if we have an image
            if self.current_image_index < 0 or not self.loaded_images:
                self.after(0, self.settings_panel.update_estimated_file_size, None, False)
                return

            if cancel_event.is_set():
                return

            # Get current image and settings
            filepath = self.loaded_images[self.current_image_index]
            settings = self.settings_panel.get_settings()
            crop_coords = self.crop_canvas.get_crop_coordinates()

            if cancel_event.is_set():
                return

            # Load and process image
            from imageprocessing.crop import crop_image
            from imageprocessing.compression import (
                QuickStrategy, AdvancedStrategy, get_encoder, CompressionEngine
            )
            from imageprocessing.compression.result import EncoderOptions

            img = Image.open(filepath)
            source_file_size = filepath.stat().st_size

            # Check if cropping will be applied
            is_cropping = crop_coords and crop_coords != (0, 0, img.width, img.height)

            # Apply crop if exists
            if is_cropping:
                img = crop_image(img, *crop_coords)

            if cancel_event.is_set():
                img.close()
                return

            # Use new compression system
            mode = settings.get('mode', 'advanced')
            target_mb = settings.get('target_mb')
            format_val = settings.get('format', 'JPEG')

            # Check if compression will be skipped (source under target, not cropping)
            if mode == 'quick' and target_mb is not None:
                target_bytes = int(target_mb * 1024 * 1024)

                # If source is under target and not cropping, file will be copied as-is
                if source_file_size <= target_bytes and not is_cropping:
                    img.close()
                    if cancel_event.is_set():
                        return
                    # Show original file size (will be copied as-is)
                    self.after(0, self.settings_panel.update_estimated_file_size, source_file_size, False)
                    return

                # Quick mode - use strategy
                strategy = QuickStrategy(
                    target_mb=target_mb,
                    auto_format=format_val == 'AUTO',
                    preferred_format=format_val,
                    min_quality=settings.get('min_quality', 60),
                    calculate_ssim=False,
                )
                result = strategy.compress(img)
                size_bytes = result.final_size_bytes

                # If compression made it larger than source AND source was under target
                # show source size (will be copied as-is)
                if size_bytes > source_file_size and source_file_size <= target_bytes and not is_cropping:
                    size_bytes = source_file_size
            else:
                # Advanced mode - encode at quality
                quality = settings.get('quality', 85)
                # Handle AUTO format for advanced mode
                if format_val == 'AUTO':
                    format_val = 'JPEG'
                encoder = get_encoder(format_val)
                if encoder:
                    options = EncoderOptions(
                        quality=quality,
                        chroma_subsampling=settings.get('chroma_subsampling', 2),
                        progressive=settings.get('progressive', False),
                        use_mozjpeg=settings.get('use_mozjpeg', False),
                    )
                    encoded = encoder.encode(img, options)
                    size_bytes = len(encoded)
                else:
                    size_bytes = None

            img.close()

            if cancel_event.is_set():
                return

            # Update UI on main thread
            self.after(0, self.settings_panel.update_estimated_file_size, size_bytes, False)

        except Exception as e:
            # On error, reset to "--"
            if not cancel_event.is_set():
                self.after(0, self.settings_panel.update_estimated_file_size, None, False)

    # Comparison Tab Methods
    def _on_tab_changed(self):
        """Handle tab change - generate comparison when switching to Compress Preview"""
        current_tab = self.preview_tabview.get()
        if current_tab == "Compress Preview":
            self._generate_compression_comparison()

    def _on_request_comparison(self):
        """Handle refresh button click from compare canvas"""
        self._generate_compression_comparison()

    def _generate_compression_comparison(self):
        """Generate compression comparison in background thread"""
        if self.current_image_index < 0 or not self.loaded_images:
            self.compare_canvas.clear()
            return

        # Start background thread
        thread = threading.Thread(
            target=self._generate_comparison_thread,
            daemon=True
        )
        thread.start()

    def _generate_comparison_thread(self):
        """Background worker: encode both versions and calculate SSIM"""
        try:
            from imageprocessing.crop import crop_image
            from imageprocessing.compression import (
                QuickStrategy, get_encoder, calculate_ssim_inmemory, SSIM_AVAILABLE
            )
            from imageprocessing.compression.result import EncoderOptions
            from io import BytesIO

            # Get current image
            filepath = self.loaded_images[self.current_image_index]
            settings = self.settings_panel.get_settings()
            crop_coords = self.crop_canvas.get_crop_coordinates()

            # Load image
            img = Image.open(filepath)

            # Apply crop if exists
            if crop_coords and crop_coords != (0, 0, img.width, img.height):
                img = crop_image(img, *crop_coords)

            original_img = img.copy()

            # Get settings
            mode = settings.get('mode', 'advanced')
            target_mb = settings.get('target_mb')
            format_val = settings.get('format', 'JPEG')
            quality = settings.get('quality', 85)

            # Determine actual format for encoding
            if format_val == 'AUTO':
                actual_format = 'JPEG'  # Default for original comparison
            else:
                actual_format = format_val

            # Check if format is lossless
            is_lossless = actual_format == 'PNG'

            # Encode original at quality 100
            encoder = get_encoder(actual_format)
            if not encoder:
                raise ValueError(f"No encoder for format: {actual_format}")

            original_options = EncoderOptions(quality=100)
            original_bytes = encoder.encode(img, original_options)
            original_size = len(original_bytes)

            # Encode compressed with current settings
            if mode == 'quick' and target_mb is not None:
                # Quick mode - use strategy to compress
                strategy = QuickStrategy(
                    target_mb=target_mb,
                    auto_format=format_val == 'AUTO',
                    preferred_format=format_val,
                    min_quality=settings.get('min_quality', 60),
                    calculate_ssim=False,
                )
                result = strategy.compress(img)
                compressed_bytes = result.encoded_bytes
                compressed_size = result.final_size_bytes
                actual_format = result.format_used
            else:
                # Advanced mode - encode at quality
                options = EncoderOptions(
                    quality=quality,
                    chroma_subsampling=settings.get('chroma_subsampling', 2),
                    progressive=settings.get('progressive', False),
                    use_mozjpeg=settings.get('use_mozjpeg', False),
                )
                compressed_bytes = encoder.encode(img, options)
                compressed_size = len(compressed_bytes)

            img.close()

            # Load compressed image for display and SSIM
            compressed_img = Image.open(BytesIO(compressed_bytes))

            # Calculate SSIM if available
            ssim_score = None
            if SSIM_AVAILABLE:
                try:
                    ssim_score = calculate_ssim_inmemory(original_img, compressed_img)
                except Exception:
                    pass

            # Update UI on main thread
            self.after(0, self._update_comparison_display,
                       original_img, compressed_img,
                       original_size, compressed_size, ssim_score, is_lossless)

        except Exception as e:
            print(f"Error generating comparison: {e}")
            self.after(0, self.compare_canvas.clear)

    def _update_comparison_display(self, original_img, compressed_img,
                                    original_size, compressed_size, ssim_score,
                                    is_lossless=False):
        """Update comparison canvas on main thread"""
        self.compare_canvas.set_images(
            original_img, compressed_img,
            original_size, compressed_size, ssim_score, is_lossless
        )
