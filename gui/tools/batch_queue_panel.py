"""Right panel with batch processing queue"""

import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional
from PIL import Image


class BatchQueuePanel(ctk.CTkFrame):
    """Panel showing batch processing queue"""

    def __init__(
        self,
        parent,
        on_select_callback: Callable[[int], None],
        on_remove_callback: Callable[[int], None],
        on_process_callback: Callable[[], None],
        output_dir: Path
    ):
        super().__init__(parent)

        self.on_select_callback = on_select_callback
        self.on_remove_callback = on_remove_callback
        self.on_process_callback = on_process_callback
        self.output_dir = output_dir

        self.queue_items = []  # List of (Path, thumbnail_image)
        self.selected_index = -1

        # Build UI
        self._build_ui()

    def _build_ui(self):
        """Build the queue panel UI"""
        # Title
        title = ctk.CTkLabel(
            self,
            text="Batch Queue",
            font=("Arial", 18, "bold"),
            anchor="w"
        )
        title.pack(padx=15, pady=(15, 10), anchor="w")

        # Queue list (scrollable)
        self.queue_frame = ctk.CTkScrollableFrame(self, height=400)
        self.queue_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Empty state label
        self.empty_label = ctk.CTkLabel(
            self.queue_frame,
            text="No images in queue\n\nUpload images to begin",
            font=("Arial", 12),
            text_color="gray60"
        )
        self.empty_label.pack(pady=40)

        # Controls section
        controls_frame = ctk.CTkFrame(self)
        controls_frame.pack(fill="x", padx=10, pady=10)

        # Clear all button
        self.clear_btn = ctk.CTkButton(
            controls_frame,
            text="Clear All",
            command=self._on_clear_all,
            height=30,
            fg_color="#dc3545",
            state="disabled"
        )
        self.clear_btn.pack(fill="x", pady=(5, 2))

        # Progress section
        progress_label = ctk.CTkLabel(
            controls_frame,
            text="Processing Progress",
            font=("Arial", 12, "bold"),
            anchor="w"
        )
        progress_label.pack(padx=5, pady=(10, 2), anchor="w")

        self.progress_bar = ctk.CTkProgressBar(controls_frame)
        self.progress_bar.pack(fill="x", padx=5, pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            controls_frame,
            text="0/0",
            font=("Arial", 10),
            text_color="gray60"
        )
        self.progress_label.pack(padx=5, pady=(0, 10))

        # Output directory section
        output_label = ctk.CTkLabel(
            controls_frame,
            text="Output Directory",
            font=("Arial", 12, "bold"),
            anchor="w"
        )
        output_label.pack(padx=5, pady=(5, 2), anchor="w")

        self.output_path_label = ctk.CTkLabel(
            controls_frame,
            text=str(self.output_dir),
            font=("Arial", 9),
            text_color="gray60",
            anchor="w"
        )
        self.output_path_label.pack(padx=5, pady=2, anchor="w")

        browse_output_btn = ctk.CTkButton(
            controls_frame,
            text="Change Output Dir...",
            command=self._browse_output_dir,
            height=25,
            font=("Arial", 10)
        )
        browse_output_btn.pack(fill="x", padx=5, pady=5)

        # Process button
        self.process_btn = ctk.CTkButton(
            controls_frame,
            text="⚡ Process All",
            command=self._on_process,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="#28a745",
            state="disabled"
        )
        self.process_btn.pack(fill="x", pady=(10, 5))

    def add_images(self, filepaths: List[Path]):
        """
        Add images to queue.

        Args:
            filepaths: List of image file paths
        """
        # Hide empty label
        self.empty_label.pack_forget()

        for filepath in filepaths:
            try:
                # Create thumbnail using CTkImage for HighDPI support
                img = Image.open(filepath)
                img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                # CTkImage handles HighDPI scaling automatically
                thumbnail = ctk.CTkImage(light_image=img, dark_image=img, size=(64, 64))

                # Create queue item frame
                item_frame = ctk.CTkFrame(self.queue_frame)
                item_frame.pack(fill="x", pady=2)

                # Thumbnail
                thumb_label = ctk.CTkLabel(item_frame, image=thumbnail, text="")
                thumb_label.image = thumbnail  # Keep reference
                thumb_label.pil_image = img  # Keep PIL image reference for CTkImage
                thumb_label.pack(side="left", padx=5, pady=5)

                # Filename
                name_label = ctk.CTkLabel(
                    item_frame,
                    text=filepath.name,
                    anchor="w",
                    font=("Arial", 10)
                )
                name_label.pack(side="left", fill="x", expand=True, padx=5)

                # Remove button
                index = len(self.queue_items)
                remove_btn = ctk.CTkButton(
                    item_frame,
                    text="×",
                    width=30,
                    height=30,
                    command=lambda idx=index: self._on_remove_item(idx),
                    fg_color="#dc3545"
                )
                remove_btn.pack(side="right", padx=5)

                # Make item clickable to select
                item_frame.bind("<Button-1>", lambda e, idx=index: self._on_select_item(idx))
                thumb_label.bind("<Button-1>", lambda e, idx=index: self._on_select_item(idx))
                name_label.bind("<Button-1>", lambda e, idx=index: self._on_select_item(idx))

                # Store item with PIL image reference
                self.queue_items.append({
                    'filepath': filepath,
                    'frame': item_frame,
                    'thumbnail': thumbnail,
                    'pil_image': img  # Keep PIL image alive for CTkImage
                })

            except Exception as e:
                print(f"Error loading {filepath}: {e}")
                continue

        # Enable controls
        if self.queue_items:
            self.clear_btn.configure(state="normal")
            self.process_btn.configure(state="normal")

        # Update progress
        self._update_progress_label()

    def _on_select_item(self, index: int):
        """Handle queue item selection"""
        # Deselect previous
        if 0 <= self.selected_index < len(self.queue_items):
            self.queue_items[self.selected_index]['frame'].configure(fg_color=["gray90", "gray13"])

        # Select new
        if 0 <= index < len(self.queue_items):
            self.selected_index = index
            self.queue_items[index]['frame'].configure(fg_color=["#3b8ed0", "#1f538d"])

            # Notify parent
            self.on_select_callback(index)

    def _on_remove_item(self, index: int):
        """Handle removing item from queue"""
        if 0 <= index < len(self.queue_items):
            # Remove from UI
            self.queue_items[index]['frame'].destroy()

            # Remove from list
            self.queue_items.pop(index)

            # Notify parent
            self.on_remove_callback(index)

            # Update indices for remaining items
            self._refresh_item_indices()

            # Show empty label if queue is empty
            if not self.queue_items:
                self.empty_label.pack(pady=40)
                self.clear_btn.configure(state="disabled")
                self.process_btn.configure(state="disabled")
                self.selected_index = -1

            # Update progress
            self._update_progress_label()

    def _on_clear_all(self):
        """Clear all items from queue"""
        for item in self.queue_items:
            item['frame'].destroy()

        self.queue_items.clear()
        self.selected_index = -1

        # Show empty label
        self.empty_label.pack(pady=40)

        # Disable controls
        self.clear_btn.configure(state="disabled")
        self.process_btn.configure(state="disabled")

        # Reset progress
        self.progress_bar.set(0)
        self._update_progress_label()

    def _on_process(self):
        """Handle process button click"""
        self.on_process_callback()

    def _browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir
        )

        if directory:
            self.output_dir = Path(directory)
            self.output_path_label.configure(text=str(self.output_dir))

    def _refresh_item_indices(self):
        """Refresh item indices after removal"""
        # This is needed because we use indices in lambda callbacks
        # We need to rebuild the callbacks with new indices
        for idx, item in enumerate(self.queue_items):
            # Find remove button and update its command
            for widget in item['frame'].winfo_children():
                if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "×":
                    widget.configure(command=lambda i=idx: self._on_remove_item(i))

            # Update click bindings
            item['frame'].bind("<Button-1>", lambda e, i=idx: self._on_select_item(i))

    def update_progress(self, current: int, total: int, message: str = ""):
        """
        Update progress bar and label.

        Args:
            current: Current progress
            total: Total items
            message: Optional status message
        """
        if total > 0:
            progress = current / total
            self.progress_bar.set(progress)
            self.progress_label.configure(text=f"{current}/{total}")

            if message:
                self.progress_label.configure(text=f"{current}/{total} - {message}")

    def _update_progress_label(self):
        """Update progress label with queue size"""
        total = len(self.queue_items)
        self.progress_label.configure(text=f"0/{total}")

    def get_output_dir(self) -> Path:
        """Get current output directory"""
        return self.output_dir

    def get_queue_size(self) -> int:
        """Get number of items in queue"""
        return len(self.queue_items)

    def get_filepath_at_index(self, index: int) -> Optional[Path]:
        """Get filepath at specific index"""
        if 0 <= index < len(self.queue_items):
            return self.queue_items[index]['filepath']
        return None

    def set_processing_state(self, processing: bool):
        """
        Enable/disable controls during processing.

        Args:
            processing: True if processing, False otherwise
        """
        state = "disabled" if processing else "normal"
        self.process_btn.configure(state=state)
        self.clear_btn.configure(state=state)
