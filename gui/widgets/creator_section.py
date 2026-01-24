"""
Creator selection widget with checkbox-based multi-select
"""

import customtkinter as ctk
import threading
from tkinter import messagebox


class CreatorSection(ctk.CTkFrame):
    """Creator username input section with checkbox-based selection"""

    def __init__(self, parent, config, app_state, import_callback=None):
        super().__init__(parent)
        self.config = config
        self.app_state = app_state  # Reference to app state for persistence
        self.creators = []  # List of all creator usernames
        self.creator_widgets = {}  # Dict: username -> {checkbox, frame, var}
        self.import_callback = import_callback  # Callback for subscription import

        # Title
        title = ctk.CTkLabel(
            self, text="Creators", font=("Arial", 16, "bold"), anchor="w"
        )
        title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        # Username input row
        username_label = ctk.CTkLabel(self, text="Username:", anchor="w")
        username_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.username_entry = ctk.CTkEntry(
            self, width=200, placeholder_text="creator_username"
        )
        self.username_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.username_entry.bind("<Return>", lambda e: self.add_creator())

        self.add_button = ctk.CTkButton(
            self, text="Add", width=80, command=self.add_creator
        )
        self.add_button.grid(row=1, column=2, padx=10, pady=5)

        # Selection control buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=5, sticky="ew")

        self.select_all_btn = ctk.CTkButton(
            button_frame, text="Select All", width=85, command=self.select_all
        )
        self.select_all_btn.pack(side="left", padx=3)

        self.deselect_all_btn = ctk.CTkButton(
            button_frame, text="Deselect All", width=85, command=self.deselect_all
        )
        self.deselect_all_btn.pack(side="left", padx=3)

        # Remove Selected button
        self.remove_selected_btn = ctk.CTkButton(
            button_frame,
            text="Remove Selected",
            width=110,
            command=self.remove_selected,
            fg_color="#d32f2f",
            hover_color="#9a0007"
        )
        self.remove_selected_btn.pack(side="left", padx=3)

        # Import subscriptions button (if callback provided)
        if import_callback:
            self.import_subs_btn = ctk.CTkButton(
                button_frame,
                text="Import Subs",
                width=95,
                command=self._on_import_subscriptions,
                fg_color="#1f6aa5",
                hover_color="#144870"
            )
            self.import_subs_btn.pack(side="left", padx=3)

        # Scrollable frame for creator checkboxes
        self.scroll_frame = ctk.CTkScrollableFrame(self, height=400)
        self.scroll_frame.grid(
            row=3, column=0, columnspan=3, padx=10, pady=5, sticky="nsew"
        )

        # Info label
        self.info_label = ctk.CTkLabel(
            self, text="Add creator usernames to download", text_color="gray", anchor="w"
        )
        self.info_label.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        # Configure grid weights
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Make scroll frame expandable
        
        # Debouncing for save operations
        self._save_timer_id = None
        
        # Batched widget creation state
        self._widget_creation_queue = None
        self._selected_set = None

        # Load from config
        self.load_from_config()

    def add_creator(self):
        """Add a creator to the list"""
        username = self.username_entry.get().strip()

        if not username:
            self.info_label.configure(text="⚠ Enter a username first", text_color="red")
            return

        # Check for duplicates
        if username in self.creators:
            self.info_label.configure(
                text=f"⚠ @{username} is already in the list", text_color="orange"
            )
            return

        # Add to list
        self.creators.append(username)
        self.create_creator_row(username, checked=True)  # AUTO-CHECKED

        # Clear entry
        self.username_entry.delete(0, "end")

        # Update info
        self.update_info_label()

        # Save immediately for explicit add action
        self._sync_and_save(immediate=True)

    def create_creator_row(self, username, checked=False):
        """Create a single row with checkbox, label, and remove button"""
        row_frame = ctk.CTkFrame(self.scroll_frame)
        row_frame.pack(fill="x", padx=5, pady=2)

        # Checkbox
        checkbox_var = ctk.BooleanVar(value=checked)
        checkbox = ctk.CTkCheckBox(
            row_frame,
            text=f"@{username}",
            variable=checkbox_var,
            command=self.on_selection_changed,
        )
        checkbox.pack(side="left", fill="x", expand=True, padx=5)

        # Remove button (small X)
        remove_btn = ctk.CTkButton(
            row_frame,
            text="✕",
            width=30,
            height=24,
            fg_color="red",
            hover_color="darkred",
            command=lambda: self.remove_creator_by_name(username),
        )
        remove_btn.pack(side="right", padx=5)

        # Store widgets
        self.creator_widgets[username] = {
            "frame": row_frame,
            "checkbox": checkbox,
            "var": checkbox_var,
        }

    def remove_creator_by_name(self, username):
        """Remove a specific creator by username"""
        if username not in self.creators:
            return

        # Remove from list
        self.creators.remove(username)

        # Destroy widgets
        if username in self.creator_widgets:
            self.creator_widgets[username]["frame"].destroy()
            del self.creator_widgets[username]

        # Update info
        self.update_info_label()

        # Save immediately for explicit remove action
        self._sync_and_save(immediate=True)

    def select_all(self):
        """Select all creators"""
        for username, widgets in self.creator_widgets.items():
            widgets["var"].set(True)
        self.on_selection_changed()

    def deselect_all(self):
        """Deselect all creators"""
        for username, widgets in self.creator_widgets.items():
            widgets["var"].set(False)
        self.on_selection_changed()

    def remove_selected(self):
        """Remove all selected creators from the list"""
        selected = self.get_selected_creators()

        if not selected:
            self.info_label.configure(text="⚠ No creators selected to remove", text_color="orange")
            return

        # Confirm removal
        from tkinter import messagebox
        count = len(selected)
        if not messagebox.askyesno(
            "Confirm Removal",
            f"Remove {count} selected creator{'s' if count != 1 else ''}?\n\nThis cannot be undone."
        ):
            return

        # Remove each selected creator
        for username in selected:
            self.remove_creator_by_name(username)

        self.info_label.configure(
            text=f"✓ Removed {count} creator{'s' if count != 1 else ''}",
            text_color="green"
        )

        # Save changes (already saved by remove_creator_by_name, but ensure final state is saved)
        self._sync_and_save(immediate=True)

    def on_selection_changed(self):
        """Called when any checkbox changes"""
        self.update_info_label()

        # Save to gui_state.json (debounced)
        self._sync_and_save()

    def update_info_label(self):
        """Update the info label with current selection status"""
        selected_count = len(self.get_selected_creators())
        total_count = len(self.creators)

        if total_count == 0:
            self.info_label.configure(
                text="Add creator usernames to download", text_color="gray"
            )
        else:
            self.info_label.configure(
                text=f"{selected_count}/{total_count} creator{'s' if total_count != 1 else ''} selected",
                text_color="gray",
            )

    def get_selected_creators(self):
        """Get list of currently selected creators"""
        selected = []
        for username, widgets in self.creator_widgets.items():
            if widgets["var"].get():
                selected.append(username)
        return selected

    def _sync_and_save(self, immediate=False):
        """Sync current widget state to AppState and save to JSON
        
        Args:
            immediate: If True, save immediately. If False, debounce (default).
        """
        if immediate:
            # Cancel any pending save
            if self._save_timer_id is not None:
                self.after_cancel(self._save_timer_id)
                self._save_timer_id = None
            
            # Save immediately
            self._do_save()
        else:
            # Debounce: cancel previous timer and schedule new one
            if self._save_timer_id is not None:
                self.after_cancel(self._save_timer_id)
            
            # Schedule save after 500ms delay
            self._save_timer_id = self.after(500, self._do_save)
    
    def _do_save(self):
        """Actually perform the save operation"""
        self._save_timer_id = None
        # Update AppState with current widget state
        self.app_state.all_creators = self.creators.copy()
        self.app_state.selected_creators = set(self.get_selected_creators())

        # Save to JSON file
        self.app_state.save_gui_state()

    def load_from_config(self):
        """Load values from AppState (GUI-only storage)"""
        # Load from AppState - this is loaded from gui_state.json
        if self.app_state.all_creators:
            self.creators = self.app_state.all_creators.copy()
            selected = self.app_state.selected_creators
        else:
            # Fallback: try to import from config.ini ONE TIME (for migration)
            if hasattr(self.config, "user_names") and self.config.user_names:
                self.creators = list(self.config.user_names)
                selected = set(self.creators)  # Default: all selected
                # Save to new format immediately
                self.app_state.all_creators = self.creators.copy()
                self.app_state.selected_creators = selected
                self.app_state.save_gui_state()
                print("Migrated creators from config.ini to gui_state.json")
            else:
                return  # No creators to load

        # Batch creation for large lists to avoid blocking UI
        if len(self.creators) > 20:
            self._batch_create_widgets(self.creators, selected)
        else:
            # Small list - create immediately
            for username in self.creators:
                checked = username in selected
                self.create_creator_row(username, checked=checked)
            self.update_info_label()

    def _batch_create_widgets(self, creators, selected):
        """Create widgets in batches to avoid blocking UI"""
        self._widget_creation_queue = list(creators)
        self._selected_set = selected
        self._create_next_batch()

    def _create_next_batch(self, batch_size=10):
        """Create next batch of widgets"""
        for _ in range(batch_size):
            if not self._widget_creation_queue:
                self.update_info_label()
                self._widget_creation_queue = None
                self._selected_set = None
                return
            username = self._widget_creation_queue.pop(0)
            checked = username in self._selected_set
            self.create_creator_row(username, checked=checked)
        
        # Schedule next batch
        if self._widget_creation_queue:
            self.after(10, lambda: self._create_next_batch(batch_size))
        else:
            self.update_info_label()
            self._widget_creation_queue = None
            self._selected_set = None

    def save_to_config(self, config):
        """Save values to AppState and GUI state file"""
        # Save to AppState (session memory)
        self.app_state.all_creators = self.creators.copy()
        self.app_state.selected_creators = set(self.get_selected_creators())

        # Save to GUI state file (persistent storage)
        self.app_state.save_gui_state()

        # DO NOT save to config.user_names - we don't use it for storage anymore
        # config.user_names will be set in handlers.py only for download purposes

    def validate(self):
        """Validate that at least one creator is selected"""
        selected = self.get_selected_creators()

        if not selected:
            self.info_label.configure(
                text="⚠ Select at least one creator to download", text_color="red"
            )
            return False

        count = len(selected)
        self.info_label.configure(
            text=f"Ready to download from {count} creator{'s' if count != 1 else ''}",
            text_color="green",
        )
        return True

    def _on_import_subscriptions(self):
        """Import subscriptions via callback"""
        if not self.import_callback:
            return

        # Disable button during import
        self.import_subs_btn.configure(state="disabled", text="Importing...")
        self.info_label.configure(text="Fetching subscriptions...", text_color="blue")

        # Run in background thread to avoid blocking GUI
        def import_thread():
            try:
                result = self.import_callback()
                # Update GUI on main thread
                self.after(0, lambda: self._on_import_complete(result))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._on_import_error(error_msg))

        threading.Thread(target=import_thread, daemon=True).start()

    def _on_import_complete(self, result: dict):
        """Handle import completion"""
        self.import_subs_btn.configure(state="normal", text="Import Subscriptions")

        added_count = result.get('added', 0)
        skipped_count = result.get('skipped', 0)
        total = added_count + skipped_count

        # Refresh the creator list display
        if added_count > 0:
            # Reload from app state
            self.load_from_config()

        message = f"Import complete!\n\nTotal subscriptions: {total}\nNew creators added: {added_count}\nAlready in list: {skipped_count}"
        self.info_label.configure(text=f"✓ Imported {added_count} new creator{'s' if added_count != 1 else ''}", text_color="green")
        messagebox.showinfo("Subscriptions Imported", message)

    def _on_import_error(self, error_msg: str):
        """Handle import error"""
        self.import_subs_btn.configure(state="normal", text="Import Subscriptions")
        self.info_label.configure(text="✗ Import failed", text_color="red")
        messagebox.showerror("Import Failed", f"Failed to import subscriptions:\n\n{error_msg}")
