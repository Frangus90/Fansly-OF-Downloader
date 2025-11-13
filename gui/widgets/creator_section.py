"""
Creator selection widget with checkbox-based multi-select
"""

import customtkinter as ctk


class CreatorSection(ctk.CTkFrame):
    """Creator username input section with checkbox-based selection"""

    def __init__(self, parent, config, app_state):
        super().__init__(parent)
        self.config = config
        self.app_state = app_state  # Reference to app state for persistence
        self.creators = []  # List of all creator usernames
        self.creator_widgets = {}  # Dict: username -> {checkbox, frame, var}

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
            button_frame, text="Select All", width=100, command=self.select_all
        )
        self.select_all_btn.pack(side="left", padx=5)

        self.deselect_all_btn = ctk.CTkButton(
            button_frame, text="Deselect All", width=100, command=self.deselect_all
        )
        self.deselect_all_btn.pack(side="left", padx=5)

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

        # Save immediately to gui_state.json
        self._sync_and_save()

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

        # Save immediately to gui_state.json
        self._sync_and_save()

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

    def on_selection_changed(self):
        """Called when any checkbox changes"""
        self.update_info_label()

        # Save immediately to gui_state.json
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

    def _sync_and_save(self):
        """Sync current widget state to AppState and save to JSON immediately"""
        # Update AppState with current widget state
        self.app_state.all_creators = self.creators.copy()
        self.app_state.selected_creators = set(self.get_selected_creators())

        # Save to JSON file immediately
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

        # Create rows
        for username in self.creators:
            checked = username in selected
            self.create_creator_row(username, checked=checked)

        self.update_info_label()

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
