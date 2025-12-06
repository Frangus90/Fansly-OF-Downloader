"""Interactive canvas for image cropping with draggable rectangle"""

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
from pathlib import Path
from typing import Optional, Tuple, Callable


# Cursor mapping for resize handles, move, and create operations
CURSOR_MAP = {
    'nw': 'top_left_corner',     # Northwest corner: ↖↘
    'ne': 'top_right_corner',    # Northeast corner: ↗↙
    'sw': 'bottom_left_corner',  # Southwest corner: ↙↗
    'se': 'bottom_right_corner', # Southeast corner: ↘↖
    'n': 'sb_v_double_arrow',    # North edge: ↕
    's': 'sb_v_double_arrow',    # South edge: ↕
    'e': 'sb_h_double_arrow',    # East edge: ↔
    'w': 'sb_h_double_arrow',    # West edge: ↔
    'move': 'fleur',             # Move entire box: ✥
    'create': 'cross',           # Create new box: ✚
}


class CropCanvas(ctk.CTkFrame):
    """Canvas widget with interactive crop rectangle"""

    def __init__(self, parent):
        super().__init__(parent)

        self.canvas_width = 600  # Initial size, will be updated dynamically
        self.canvas_height = 600

        # Image data
        self.original_image: Optional[Image.Image] = None
        self.display_image: Optional[ImageTk.PhotoImage] = None
        self.image_scale = 1.0  # Scale factor from original to display

        # Crop rectangle coordinates (in display coordinates)
        self.crop_x1 = 0
        self.crop_y1 = 0
        self.crop_x2 = 0
        self.crop_y2 = 0

        # Drag state
        self.drag_mode = None  # None, 'move', 'nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Canvas elements
        self.canvas_image_id = None
        self.crop_rect_id = None
        self.handle_ids = {}  # Dict of handle positions to canvas IDs

        # Aspect ratio lock
        self.locked_aspect_ratio: Optional[float] = None

        # Navigation callback
        self.on_nav_callback: Optional[Callable[[str], None]] = None

        # Crop change callback (reports current aspect ratio)
        self.on_crop_change_callback: Optional[Callable[[float], None]] = None

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build canvas UI"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="Image Preview",
            font=("Arial", 18, "bold"),
            anchor="w"
        )
        title.pack(padx=15, pady=(15, 5), anchor="w")

        # Canvas (responsive)
        self.canvas = tk.Canvas(
            self,
            bg='#2b2b2b',
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)

        # Bind events
        self.canvas.bind("<Button-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Motion>", self._on_mouse_motion)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Navigation controls
        nav_frame = ctk.CTkFrame(self)
        nav_frame.pack(fill="x", padx=10, pady=(5, 10))

        self.prev_btn = ctk.CTkButton(
            nav_frame,
            text="< Previous",
            command=lambda: self._on_nav_click('prev'),
            width=100,
            height=30
        )
        self.prev_btn.pack(side="left", padx=5)

        self.image_counter_label = ctk.CTkLabel(
            nav_frame,
            text="No images",
            font=("Arial", 11)
        )
        self.image_counter_label.pack(side="left", expand=True)

        self.next_btn = ctk.CTkButton(
            nav_frame,
            text="Next >",
            command=lambda: self._on_nav_click('next'),
            width=100,
            height=30
        )
        self.next_btn.pack(side="right", padx=5)

        # Initially disabled
        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")

        # Crop info label
        self.info_label = ctk.CTkLabel(
            self,
            text="No image loaded",
            font=("Arial", 10),
            text_color="gray60"
        )
        self.info_label.pack(padx=15, pady=(0, 10))

    def load_image(self, filepath: Path, target_width: Optional[int] = None, target_height: Optional[int] = None):
        """
        Load image and initialize crop rectangle.

        Args:
            filepath: Path to image file
            target_width: Optional target width for crop
            target_height: Optional target height for crop
        """
        try:
            # Load original image
            self.original_image = Image.open(filepath)

            # Get dynamic canvas size
            self.canvas_width = self.canvas.winfo_width()
            self.canvas_height = self.canvas.winfo_height()

            # Ensure minimum size
            if self.canvas_width < 100:
                self.canvas_width = 600
            if self.canvas_height < 100:
                self.canvas_height = 600

            # Calculate display size (fit in canvas)
            orig_w, orig_h = self.original_image.size
            width_scale = self.canvas_width / orig_w
            height_scale = self.canvas_height / orig_h
            self.image_scale = min(width_scale, height_scale, 1.0)  # Don't upscale

            display_w = int(orig_w * self.image_scale)
            display_h = int(orig_h * self.image_scale)

            # Create display image
            display_img = self.original_image.resize(
                (display_w, display_h),
                Image.Resampling.LANCZOS
            )
            self.display_image = ImageTk.PhotoImage(display_img)

            # Clear canvas
            self.canvas.delete("all")

            # Display image centered
            x_offset = (self.canvas_width - display_w) // 2
            y_offset = (self.canvas_height - display_h) // 2

            self.canvas_image_id = self.canvas.create_image(
                x_offset,
                y_offset,
                anchor="nw",
                image=self.display_image
            )

            # Initialize crop rectangle (80% of image, centered)
            if target_width and target_height:
                # Use target dimensions
                crop_w = int(target_width * self.image_scale)
                crop_h = int(target_height * self.image_scale)

                # Center the crop
                self.crop_x1 = x_offset + (display_w - crop_w) // 2
                self.crop_y1 = y_offset + (display_h - crop_h) // 2
                self.crop_x2 = self.crop_x1 + crop_w
                self.crop_y2 = self.crop_y1 + crop_h
            else:
                # Default 80% crop
                margin = 0.1
                self.crop_x1 = int(x_offset + display_w * margin)
                self.crop_y1 = int(y_offset + display_h * margin)
                self.crop_x2 = int(x_offset + display_w * (1 - margin))
                self.crop_y2 = int(y_offset + display_h * (1 - margin))

            # Draw crop rectangle
            self._draw_crop_rectangle()

            # Update info
            self._update_info_label()

        except Exception as e:
            self.info_label.configure(text=f"Error loading image: {e}")

    def _draw_crop_rectangle(self):
        """Draw crop rectangle and handles"""
        # Delete existing rectangle and handles
        if self.crop_rect_id:
            self.canvas.delete(self.crop_rect_id)
        for handle_id in self.handle_ids.values():
            self.canvas.delete(handle_id)
        self.handle_ids.clear()

        # Draw semi-transparent overlay (outside crop area)
        # This is complex in Tkinter, so we'll just draw the crop rectangle
        self.crop_rect_id = self.canvas.create_rectangle(
            self.crop_x1,
            self.crop_y1,
            self.crop_x2,
            self.crop_y2,
            outline="#ffffff",
            width=2,
            dash=(5, 5)
        )

        # Draw resize handles (visual size)
        handle_size = 10  # Increased from 8 for better visibility
        handles = {
            'nw': (self.crop_x1, self.crop_y1),
            'ne': (self.crop_x2, self.crop_y1),
            'sw': (self.crop_x1, self.crop_y2),
            'se': (self.crop_x2, self.crop_y2),
            'n': ((self.crop_x1 + self.crop_x2) // 2, self.crop_y1),
            's': ((self.crop_x1 + self.crop_x2) // 2, self.crop_y2),
            'w': (self.crop_x1, (self.crop_y1 + self.crop_y2) // 2),
            'e': (self.crop_x2, (self.crop_y1 + self.crop_y2) // 2),
        }

        for pos, (x, y) in handles.items():
            handle_id = self.canvas.create_rectangle(
                x - handle_size // 2,
                y - handle_size // 2,
                x + handle_size // 2,
                y + handle_size // 2,
                fill="#2116be",
                outline="white",
                width=1
            )
            self.handle_ids[pos] = handle_id

    def _on_mouse_down(self, event):
        """Handle mouse button press"""
        x, y = event.x, event.y

        # Check if clicking on a handle (larger hit area for easier clicking)
        hit_detection_size = 15  # Larger than visual size for better UX
        for pos, (hx, hy) in self._get_handle_positions().items():
            if abs(x - hx) <= hit_detection_size and abs(y - hy) <= hit_detection_size:
                self.drag_mode = pos
                self.drag_start_x = x
                self.drag_start_y = y
                return

        # Check if clicking inside crop rectangle
        if (self.crop_x1 <= x <= self.crop_x2 and
            self.crop_y1 <= y <= self.crop_y2):
            self.drag_mode = 'move'
            self.drag_start_x = x
            self.drag_start_y = y
        else:
            # Clicking outside - start creating new crop box
            self.drag_mode = 'create'
            self.drag_start_x = x
            self.drag_start_y = y
            # Initialize crop box at click point
            self.crop_x1 = x
            self.crop_y1 = y
            self.crop_x2 = x
            self.crop_y2 = y

        # Set cursor for drag operation
        if self.drag_mode:
            cursor = CURSOR_MAP.get(self.drag_mode, 'arrow')
            self.canvas.configure(cursor=cursor)

    def _on_mouse_move(self, event):
        """Handle mouse movement while dragging"""
        if not self.drag_mode:
            return

        x, y = event.x, event.y
        dx = x - self.drag_start_x
        dy = y - self.drag_start_y

        if self.drag_mode == 'move':
            # Move entire rectangle
            self.crop_x1 += dx
            self.crop_y1 += dy
            self.crop_x2 += dx
            self.crop_y2 += dy

        elif self.drag_mode == 'create':
            # Creating new crop box - expand from start point to current position
            # Use min/max to handle dragging in any direction from anchor point
            self.crop_x1 = min(self.drag_start_x, x)
            self.crop_y1 = min(self.drag_start_y, y)
            self.crop_x2 = max(self.drag_start_x, x)
            self.crop_y2 = max(self.drag_start_y, y)

        elif self.drag_mode in ('nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'):
            # Resize rectangle
            if 'n' in self.drag_mode:
                self.crop_y1 += dy
            if 's' in self.drag_mode:
                self.crop_y2 += dy
            if 'w' in self.drag_mode:
                self.crop_x1 += dx
            if 'e' in self.drag_mode:
                self.crop_x2 += dx

            # Apply aspect ratio lock if enabled
            if self.locked_aspect_ratio:
                self._apply_aspect_ratio_constraint()

        # Update drag start position (except for create mode where anchor stays fixed)
        if self.drag_mode != 'create':
            self.drag_start_x = x
            self.drag_start_y = y

        # Constrain crop to image bounds
        self._constrain_crop_to_bounds()

        # Redraw
        self._draw_crop_rectangle()
        self._update_info_label()

    def _on_mouse_up(self, event):
        """Handle mouse button release"""
        self.drag_mode = None
        # Update cursor based on current mouse position
        self._on_mouse_motion(event)

    def _on_mouse_motion(self, event):
        """Handle mouse motion to update cursor based on hover position"""
        # Don't change cursor while actively dragging
        if self.drag_mode:
            return

        x, y = event.x, event.y
        hit_detection_size = 15  # Same as click detection

        # Check if hovering over a resize handle
        for pos, (hx, hy) in self._get_handle_positions().items():
            if abs(x - hx) <= hit_detection_size and abs(y - hy) <= hit_detection_size:
                cursor = CURSOR_MAP.get(pos, 'arrow')
                self.canvas.configure(cursor=cursor)
                return

        # Check if hovering inside crop rectangle (move cursor)
        if (self.crop_x1 <= x <= self.crop_x2 and
            self.crop_y1 <= y <= self.crop_y2):
            self.canvas.configure(cursor=CURSOR_MAP['move'])
            return

        # Crosshair cursor when outside crop area (indicates can create new box)
        self.canvas.configure(cursor='crosshair')

    def _get_handle_positions(self) -> dict:
        """Get current handle positions"""
        return {
            'nw': (self.crop_x1, self.crop_y1),
            'ne': (self.crop_x2, self.crop_y1),
            'sw': (self.crop_x1, self.crop_y2),
            'se': (self.crop_x2, self.crop_y2),
            'n': ((self.crop_x1 + self.crop_x2) // 2, self.crop_y1),
            's': ((self.crop_x1 + self.crop_x2) // 2, self.crop_y2),
            'w': (self.crop_x1, (self.crop_y1 + self.crop_y2) // 2),
            'e': (self.crop_x2, (self.crop_y1 + self.crop_y2) // 2),
        }

    def _apply_aspect_ratio_constraint(self):
        """Apply aspect ratio lock to current crop rectangle"""
        if not self.locked_aspect_ratio:
            return

        # Calculate current dimensions
        width = self.crop_x2 - self.crop_x1
        height = self.crop_y2 - self.crop_y1

        # Adjust height to match aspect ratio
        target_height = width / self.locked_aspect_ratio

        # Adjust based on which corner/edge is being dragged
        if 'n' in self.drag_mode:
            self.crop_y1 = self.crop_y2 - int(target_height)
        elif 's' in self.drag_mode:
            self.crop_y2 = self.crop_y1 + int(target_height)

    def _update_info_label(self):
        """Update info label with crop dimensions"""
        if not self.original_image:
            self.info_label.configure(text="No image loaded")
            return

        # Calculate crop dimensions in original image coordinates
        orig_x1 = int((self.crop_x1 - self._get_image_offset_x()) / self.image_scale)
        orig_y1 = int((self.crop_y1 - self._get_image_offset_y()) / self.image_scale)
        orig_x2 = int((self.crop_x2 - self._get_image_offset_x()) / self.image_scale)
        orig_y2 = int((self.crop_y2 - self._get_image_offset_y()) / self.image_scale)

        crop_w = orig_x2 - orig_x1
        crop_h = orig_y2 - orig_y1

        orig_w, orig_h = self.original_image.size

        self.info_label.configure(
            text=f"Original: {orig_w}×{orig_h} | Crop: {crop_w}×{crop_h}"
        )

        # Notify callback of current aspect ratio
        if crop_h > 0 and self.on_crop_change_callback:
            aspect_ratio = crop_w / crop_h
            self.on_crop_change_callback(aspect_ratio)

    def _get_image_offset_x(self) -> int:
        """Get X offset of displayed image"""
        if not self.display_image:
            return 0
        display_w = self.display_image.width()
        return (self.canvas_width - display_w) // 2

    def _get_image_offset_y(self) -> int:
        """Get Y offset of displayed image"""
        if not self.display_image:
            return 0
        display_h = self.display_image.height()
        return (self.canvas_height - display_h) // 2

    def get_crop_coordinates(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get crop coordinates in original image space.

        Returns:
            Tuple of (x1, y1, x2, y2) in original image coordinates,
            or None if no image loaded
        """
        if not self.original_image:
            return None

        # Convert display coordinates to original coordinates
        offset_x = self._get_image_offset_x()
        offset_y = self._get_image_offset_y()

        orig_x1 = int((self.crop_x1 - offset_x) / self.image_scale)
        orig_y1 = int((self.crop_y1 - offset_y) / self.image_scale)
        orig_x2 = int((self.crop_x2 - offset_x) / self.image_scale)
        orig_y2 = int((self.crop_y2 - offset_y) / self.image_scale)

        # Clamp to image bounds
        orig_w, orig_h = self.original_image.size
        orig_x1 = max(0, min(orig_x1, orig_w))
        orig_y1 = max(0, min(orig_y1, orig_h))
        orig_x2 = max(0, min(orig_x2, orig_w))
        orig_y2 = max(0, min(orig_y2, orig_h))

        return (orig_x1, orig_y1, orig_x2, orig_y2)

    def set_aspect_ratio(self, ratio: Optional[float]):
        """
        Set aspect ratio lock.

        Args:
            ratio: Aspect ratio (width/height), or None to disable
        """
        self.locked_aspect_ratio = ratio

    def update_crop_for_target_size(self, width: int, height: int):
        """
        Update crop rectangle to match target dimensions (maintaining aspect ratio).
        Note: This does NOT set the aspect ratio lock - use set_aspect_ratio() for that.

        Args:
            width: Target width
            height: Target height
        """
        if not self.original_image:
            return

        # Calculate aspect ratio (but don't set the lock - preserve current lock state)
        aspect = width / height if height > 0 else 1.0
        # Don't modify self.locked_aspect_ratio here - only update_crop_for_target_size should change it

        # Get current crop center
        center_x = (self.crop_x1 + self.crop_x2) // 2
        center_y = (self.crop_y1 + self.crop_y2) // 2

        # Calculate new crop size in display coordinates
        # Use the smaller dimension to ensure it fits
        orig_w, orig_h = self.original_image.size
        display_w = int(orig_w * self.image_scale)
        display_h = int(orig_h * self.image_scale)

        # Calculate crop size
        if aspect > 1:
            # Wider than tall
            crop_w = min(display_w, int(display_h * aspect))
            crop_h = int(crop_w / aspect)
        else:
            # Taller than wide
            crop_h = min(display_h, int(display_w / aspect))
            crop_w = int(crop_h * aspect)

        # Update crop coordinates centered on current center
        self.crop_x1 = center_x - crop_w // 2
        self.crop_y1 = center_y - crop_h // 2
        self.crop_x2 = self.crop_x1 + crop_w
        self.crop_y2 = self.crop_y1 + crop_h

        # Redraw
        self._draw_crop_rectangle()
        self._update_info_label()

    def _constrain_crop_to_bounds(self):
        """Constrain crop rectangle to stay within image bounds"""
        if not self.display_image:
            return

        # Get image boundaries
        offset_x = self._get_image_offset_x()
        offset_y = self._get_image_offset_y()
        max_x = offset_x + self.display_image.width()
        max_y = offset_y + self.display_image.height()

        # Get crop dimensions
        crop_w = self.crop_x2 - self.crop_x1
        crop_h = self.crop_y2 - self.crop_y1

        # Minimum crop size (20px)
        min_size = 20
        crop_w = max(crop_w, min_size)
        crop_h = max(crop_h, min_size)

        # Constrain x1, y1 to image bounds
        self.crop_x1 = max(offset_x, min(self.crop_x1, max_x - crop_w))
        self.crop_y1 = max(offset_y, min(self.crop_y1, max_y - crop_h))

        # Recalculate x2, y2 based on constrained x1, y1
        self.crop_x2 = self.crop_x1 + crop_w
        self.crop_y2 = self.crop_y1 + crop_h

        # Final bounds check
        self.crop_x2 = min(self.crop_x2, max_x)
        self.crop_y2 = min(self.crop_y2, max_y)

    def _on_canvas_resize(self, event):
        """Handle canvas resize event"""
        # Get new canvas size
        new_width = event.width
        new_height = event.height

        # Update stored dimensions
        self.canvas_width = new_width
        self.canvas_height = new_height

        # Reload current image if one is loaded
        if self.original_image and self.canvas_width > 100 and self.canvas_height > 100:
            self._redraw_for_new_size()

    def _redraw_for_new_size(self):
        """Redraw image and crop when canvas is resized"""
        if not self.original_image:
            return

        # Store crop in normalized coordinates (0.0-1.0)
        orig_coords = self.get_crop_coordinates()
        if not orig_coords:
            return

        orig_w, orig_h = self.original_image.size
        norm_x1 = orig_coords[0] / orig_w
        norm_y1 = orig_coords[1] / orig_h
        norm_x2 = orig_coords[2] / orig_w
        norm_y2 = orig_coords[3] / orig_h

        # Recalculate display size
        width_scale = self.canvas_width / orig_w
        height_scale = self.canvas_height / orig_h
        self.image_scale = min(width_scale, height_scale, 1.0)

        display_w = int(orig_w * self.image_scale)
        display_h = int(orig_h * self.image_scale)

        # Create new display image
        display_img = self.original_image.resize(
            (display_w, display_h),
            Image.Resampling.LANCZOS
        )
        self.display_image = ImageTk.PhotoImage(display_img)

        # Clear and redraw
        self.canvas.delete("all")

        x_offset = (self.canvas_width - display_w) // 2
        y_offset = (self.canvas_height - display_h) // 2

        self.canvas_image_id = self.canvas.create_image(
            x_offset,
            y_offset,
            anchor="nw",
            image=self.display_image
        )

        # Restore crop using normalized coordinates
        self.crop_x1 = int(norm_x1 * orig_w * self.image_scale) + x_offset
        self.crop_y1 = int(norm_y1 * orig_h * self.image_scale) + y_offset
        self.crop_x2 = int(norm_x2 * orig_w * self.image_scale) + x_offset
        self.crop_y2 = int(norm_y2 * orig_h * self.image_scale) + y_offset

        self._draw_crop_rectangle()
        self._update_info_label()

    def set_nav_callback(self, callback: Callable[[str], None]):
        """Set callback for navigation button clicks"""
        self.on_nav_callback = callback

    def set_crop_change_callback(self, callback: Callable[[float], None]):
        """Set callback for crop box changes (receives aspect ratio)"""
        self.on_crop_change_callback = callback

    def _on_nav_click(self, direction: str):
        """Handle navigation button click"""
        if self.on_nav_callback:
            self.on_nav_callback(direction)

    def update_image_counter(self, current: int, total: int):
        """Update image counter display"""
        if total > 0:
            self.image_counter_label.configure(text=f"Image {current + 1} of {total}")
            self.prev_btn.configure(state="normal" if current > 0 else "disabled")
            self.next_btn.configure(state="normal" if current < total - 1 else "disabled")
        else:
            self.image_counter_label.configure(text="No images")
            self.prev_btn.configure(state="disabled")
            self.next_btn.configure(state="disabled")

    def set_crop_from_coordinates(self, orig_coords: Tuple[int, int, int, int]):
        """
        Set crop rectangle from original image coordinates.

        Args:
            orig_coords: (x1, y1, x2, y2) in original image space
        """
        if not self.original_image:
            return

        orig_x1, orig_y1, orig_x2, orig_y2 = orig_coords

        # Convert to display coordinates
        offset_x = self._get_image_offset_x()
        offset_y = self._get_image_offset_y()

        self.crop_x1 = int(orig_x1 * self.image_scale) + offset_x
        self.crop_y1 = int(orig_y1 * self.image_scale) + offset_y
        self.crop_x2 = int(orig_x2 * self.image_scale) + offset_x
        self.crop_y2 = int(orig_y2 * self.image_scale) + offset_y

        # Redraw
        self._draw_crop_rectangle()
        self._update_info_label()
