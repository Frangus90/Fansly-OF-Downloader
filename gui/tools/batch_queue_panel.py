"""Right panel with batch processing queue"""

import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from typing import Callable, List, Optional
from PIL import Image

from imageprocessing.presets import save_last_output_dir


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
        # Title row with selection info
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=15, pady=(15, 5))

        title = ctk.CTkLabel(
            title_frame,
            text="Batch Queue",
            font=("Arial", 18, "bold"),
            anchor="w"
        )
        title.pack(side="left")

        # Selection count label
        self.selection_label = ctk.CTkLabel(
            title_frame,
            text="0/0 selected",
            font=("Arial", 11),
            text_color="gray60"
        )
        self.selection_label.pack(side="right")

        # Selection buttons row
        selection_btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        selection_btn_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.select_all_btn = ctk.CTkButton(
            selection_btn_frame,
            text="Select All",
            command=self.select_all,
            width=80,
            height=25,
            font=("Arial", 10),
            state="disabled"
        )
        self.select_all_btn.pack(side="left", padx=(0, 5))

        self.deselect_all_btn = ctk.CTkButton(
            selection_btn_frame,
            text="Deselect",
            command=self.deselect_all,
            width=70,
            height=25,
            font=("Arial", 10),
            state="disabled"
        )
        self.deselect_all_btn.pack(side="left", padx=(0, 5))

        self.delete_selected_btn = ctk.CTkButton(
            selection_btn_frame,
            text="Delete Selected",
            command=self.delete_selected,
            width=100,
            height=25,
            font=("Arial", 10),
            fg_color="#dc3545",
            state="disabled"
        )
        self.delete_selected_btn.pack(side="left")

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

                # Checkbox for selection
                index = len(self.queue_items)
                selected_var = ctk.BooleanVar(value=False)
                checkbox = ctk.CTkCheckBox(
                    item_frame,
                    text="",
                    variable=selected_var,
                    command=self._on_selection_changed,
                    width=20
                )
                checkbox.pack(side="left", padx=(5, 0))

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

                # Store item with PIL image reference and selection state
                self.queue_items.append({
                    'filepath': filepath,
                    'frame': item_frame,
                    'thumbnail': thumbnail,
                    'pil_image': img,  # Keep PIL image alive for CTkImage
                    'selected_var': selected_var,
                    'checkbox': checkbox
                })

            except Exception as e:
                print(f"Error loading {filepath}: {e}")
                continue

        # Enable controls
        if self.queue_items:
            self.clear_btn.configure(state="normal")
            self.process_btn.configure(state="normal")
            self.select_all_btn.configure(state="normal")

        # Update progress and selection
        self._update_progress_label()
        self._update_selection_label()

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
                self.select_all_btn.configure(state="disabled")
                self.deselect_all_btn.configure(state="disabled")
                self.delete_selected_btn.configure(state="disabled")
                self.selected_index = -1

            # Update progress and selection
            self._update_progress_label()
            self._update_selection_label()
            self._update_selection_buttons()

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
        self.select_all_btn.configure(state="disabled")
        self.deselect_all_btn.configure(state="disabled")
        self.delete_selected_btn.configure(state="disabled")

        # Reset progress and selection
        self.progress_bar.set(0)
        self._update_progress_label()
        self._update_selection_label()

    def _on_process(self):
        """Handle process button click"""
        self.on_process_callback()

    def _browse_output_dir(self):
        """Browse for output directory"""
        # Get toplevel window to use as parent
        toplevel = self.winfo_toplevel()

        directory = filedialog.askdirectory(
            parent=toplevel,
            title="Select Output Directory",
            initialdir=self.output_dir
        )

        # Restore focus to crop window
        toplevel.lift()
        toplevel.focus_force()

        if directory:
            self.output_dir = Path(directory)
            self.output_path_label.configure(text=str(self.output_dir))
            # Save as last used output directory
            save_last_output_dir(self.output_dir)

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

        # Update selection UI after index refresh
        self._update_selection_label()
        self._update_selection_buttons()

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
        self.select_all_btn.configure(state=state)
        self.deselect_all_btn.configure(state=state if self._get_selected_count() > 0 else "disabled")
        self.delete_selected_btn.configure(state=state if self._get_selected_count() > 0 else "disabled")

    def select_all(self):
        """Select all items in the queue"""
        for item in self.queue_items:
            item['selected_var'].set(True)
        self._on_selection_changed()

    def deselect_all(self):
        """Deselect all items in the queue"""
        for item in self.queue_items:
            item['selected_var'].set(False)
        self._on_selection_changed()

    def get_selected_indices(self) -> List[int]:
        """Get indices of all selected items"""
        return [i for i, item in enumerate(self.queue_items) if item['selected_var'].get()]

    def _get_selected_count(self) -> int:
        """Get count of selected items"""
        return sum(1 for item in self.queue_items if item['selected_var'].get())

    def _on_selection_changed(self):
        """Handle selection state change - update UI"""
        self._update_selection_label()
        self._update_selection_buttons()

    def _update_selection_label(self):
        """Update the selection count label"""
        selected = self._get_selected_count()
        total = len(self.queue_items)
        self.selection_label.configure(text=f"{selected}/{total} selected")

    def _update_selection_buttons(self):
        """Enable/disable selection buttons based on current state"""
        selected_count = self._get_selected_count()
        total = len(self.queue_items)

        # Select All: enabled if there are items and not all selected
        if total > 0 and selected_count < total:
            self.select_all_btn.configure(state="normal")
        else:
            self.select_all_btn.configure(state="disabled")

        # Deselect: enabled if any items selected
        if selected_count > 0:
            self.deselect_all_btn.configure(state="normal")
            self.delete_selected_btn.configure(state="normal")
        else:
            self.deselect_all_btn.configure(state="disabled")
            self.delete_selected_btn.configure(state="disabled")

    def delete_selected(self):
        """Delete all selected items from the queue"""
        from tkinter import messagebox

        selected_indices = self.get_selected_indices()
        if not selected_indices:
            return

        # Confirm deletion
        count = len(selected_indices)
        if not messagebox.askyesno(
            "Delete Selected",
            f"Delete {count} selected image{'s' if count > 1 else ''}?",
            parent=self.winfo_toplevel()
        ):
            return

        # Remove items in reverse order to maintain correct indices
        for idx in sorted(selected_indices, reverse=True):
            # Remove from UI
            self.queue_items[idx]['frame'].destroy()
            # Remove from list
            self.queue_items.pop(idx)
            # Notify parent
            self.on_remove_callback(idx)

        # Refresh indices for remaining items
        self._refresh_item_indices()

        # Show empty label if queue is empty
        if not self.queue_items:
            self.empty_label.pack(pady=40)
            self.clear_btn.configure(state="disabled")
            self.process_btn.configure(state="disabled")
            self.select_all_btn.configure(state="disabled")
            self.selected_index = -1

        # Update progress and selection
        self._update_progress_label()
        self._update_selection_label()
        self._update_selection_buttons()
