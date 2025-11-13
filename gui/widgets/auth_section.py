"""
Authentication section widget
"""

import customtkinter as ctk
import threading
from gui.logger import log


class AuthSection(ctk.CTkFrame):
    """Authentication configuration section"""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config

        # Title
        title = ctk.CTkLabel(
            self, text="Authentication", font=("Arial", 16, "bold"), anchor="w"
        )
        title.grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        # Authorization Token
        token_label = ctk.CTkLabel(self, text="Authorization Token:", anchor="w")
        token_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.token_entry = ctk.CTkEntry(self, width=400, show="*")
        self.token_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        self.show_token_btn = ctk.CTkButton(
            self, text="Show", command=self.toggle_token_visibility, width=60
        )
        self.show_token_btn.grid(row=1, column=2, padx=10, pady=5)

        # User Agent
        user_agent_label = ctk.CTkLabel(self, text="User Agent:", anchor="w")
        user_agent_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.user_agent_entry = ctk.CTkEntry(self, width=400)
        self.user_agent_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # Button frame for Connect and Reconfigure buttons
        button_frame = ctk.CTkFrame(self)
        button_frame.grid(row=3, column=1, padx=10, pady=10, sticky="e")

        self.connect_btn = ctk.CTkButton(
            button_frame,
            text="Connect",
            command=self.test_connection,
            width=100,
            fg_color="#0d6efd",
            hover_color="#0b5ed7",
        )
        self.connect_btn.pack(side="left", padx=5)

        self.reconfigure_btn = ctk.CTkButton(
            button_frame,
            text="Reconfigure...",
            command=self.run_setup_wizard,
            width=120,
            fg_color="#6c757d",
            hover_color="#5c636a",
        )
        self.reconfigure_btn.pack(side="left", padx=5)

        # Status indicator
        self.status_label = ctk.CTkLabel(
            self, text="● Not Connected", text_color="gray", anchor="w"
        )
        self.status_label.grid(row=4, column=0, columnspan=3, padx=10, pady=5, sticky="w")

        # Configure grid weights
        self.grid_columnconfigure(1, weight=1)

        # Load from config
        self.load_from_config()

    def toggle_token_visibility(self):
        """Toggle token visibility"""
        if self.token_entry.cget("show") == "*":
            self.token_entry.configure(show="")
            self.show_token_btn.configure(text="Hide")
        else:
            self.token_entry.configure(show="*")
            self.show_token_btn.configure(text="Show")

    def test_connection(self):
        """Test the API connection with provided credentials"""
        # Get current values
        token = self.token_entry.get().strip()
        user_agent = self.user_agent_entry.get().strip()

        # Try to parse token as JSON (in case user copied the entire cookie value)
        if token.startswith('{') and token.endswith('}'):
            try:
                import json
                token_data = json.loads(token)
                if 'token' in token_data:
                    token = token_data['token']
                    # Update the entry with the extracted token
                    self.token_entry.delete(0, 'end')
                    self.token_entry.insert(0, token)
            except json.JSONDecodeError:
                pass  # Not valid JSON, use as-is

        # Validate fields
        if not token:
            self.status_label.configure(
                text="● Error: Authorization token required", text_color="red"
            )
            return

        if not user_agent:
            self.status_label.configure(
                text="● Error: User agent required", text_color="red"
            )
            return

        # Check token length (basic validation)
        if len(token) < 50:
            self.status_label.configure(
                text="● Error: Token appears invalid (too short)", text_color="red"
            )
            return

        # Update status to connecting
        self.status_label.configure(text="● Connecting...", text_color="orange")
        self.connect_btn.configure(state="disabled", text="Testing...")

        # Force GUI update
        self.update()

        # Test connection in thread to avoid blocking UI
        thread = threading.Thread(
            target=self._test_connection_thread, args=(token, user_agent)
        )
        thread.daemon = True
        thread.start()

    def _test_connection_thread(self, token, user_agent):
        """Background thread for testing connection"""
        try:
            # Temporarily update config
            self.config.token = token
            self.config.user_agent = user_agent

            # Check if check_key exists
            if not self.config.check_key:
                self.after(
                    0,
                    self._connection_failed,
                    "check_key missing in config.ini - please ensure config.ini is set up",
                )
                return

            # Try to initialize API
            api = self.config.get_api()

            # If we got here, connection successful
            self.after(0, self._connection_success)

        except RuntimeError as e:
            self.after(0, self._connection_failed, str(e))
        except Exception as e:
            self.after(0, self._connection_failed, f"Unexpected error: {str(e)}")

    def _connection_success(self):
        """Update UI on successful connection"""
        self.status_label.configure(
            text="● Connected successfully!", text_color="green"
        )
        self.connect_btn.configure(state="normal", text="Reconnect")

    def _connection_failed(self, error_msg):
        """Update UI on failed connection"""
        # Truncate long error messages
        if len(error_msg) > 60:
            error_msg = error_msg[:57] + "..."

        self.status_label.configure(
            text=f"● Connection failed: {error_msg}", text_color="red"
        )
        self.connect_btn.configure(state="normal", text="Retry")

    def load_from_config(self):
        """Load values from config"""
        log("AuthSection: Loading config values...")

        has_token = hasattr(self.config, "token") and self.config.token
        has_user_agent = hasattr(self.config, "user_agent") and self.config.user_agent

        log(f"AuthSection: has_token={has_token}, has_user_agent={has_user_agent}")

        if has_token:
            token_len = len(self.config.token) if self.config.token else 0
            log(f"AuthSection: Inserting token (length: {token_len})")
            self.token_entry.insert(0, self.config.token)
        else:
            log("AuthSection: No token to load")

        if has_user_agent:
            ua_len = len(self.config.user_agent) if self.config.user_agent else 0
            log(f"AuthSection: Inserting user_agent (length: {ua_len})")
            self.user_agent_entry.insert(0, self.config.user_agent)
        else:
            log("AuthSection: No user_agent to load")

        # Check if API is already initialized (from config load)
        if hasattr(self.config, "_api") and self.config._api is not None:
            log("AuthSection: API already initialized, showing Connected status")
            self.status_label.configure(text="● Connected", text_color="green")
            self.connect_btn.configure(text="Reconnect")
        # Auto-connect if both credentials exist but API not initialized
        elif has_token and has_user_agent:
            log("AuthSection: Scheduling auto-connect test")
            # Auto-connect after a short delay to let UI finish loading
            self.after(500, self.test_connection)
        else:
            log("AuthSection: Skipping auto-connect (missing credentials)")

    def save_to_config(self, config):
        """Save values to config"""
        token = self.token_entry.get().strip()

        # Try to parse as JSON (in case user copied the entire cookie value)
        if token.startswith('{') and token.endswith('}'):
            try:
                import json
                token_data = json.loads(token)
                if 'token' in token_data:
                    token = token_data['token']
            except json.JSONDecodeError:
                pass  # Not valid JSON, use as-is

        config.token = token
        user_agent = self.user_agent_entry.get().strip()
        if user_agent:
            config.user_agent = user_agent

    def validate(self):
        """Validate that required fields are filled"""
        token = self.token_entry.get().strip()
        user_agent = self.user_agent_entry.get().strip()

        if not token or not user_agent:
            self.status_label.configure(
                text="● Error: Fill all fields and connect", text_color="red"
            )
            return False

        # Check if connected (check if API is initialized)
        if not hasattr(self.config, "_api") or self.config._api is None:
            self.status_label.configure(
                text="● Warning: Please test connection first", text_color="orange"
            )
            # Still return True to allow download attempt (user may want to try anyway)

        return True

    def run_setup_wizard(self):
        """Launch the setup wizard to reconfigure the application"""
        from tkinter import messagebox

        # Show confirmation dialog
        result = messagebox.askyesno(
            "Reconfigure Application",
            "This will launch the setup wizard to reconfigure your authentication and settings.\n\n"
            "Your current configuration will be overwritten.\n\nContinue?",
            icon="warning",
        )

        if not result:
            return

        # Import setup wizard
        from gui.setup_wizard import SetupWizard

        # Get main window (traverse up to root)
        root = self.winfo_toplevel()

        # Show wizard
        wizard = SetupWizard(root)
        root.wait_window(wizard)

        # Check if wizard completed successfully
        if wizard.success:
            # Reload configuration
            from config import load_config

            try:
                load_config(self.config)
                self.load_from_config()
                self.status_label.configure(
                    text="● Configuration updated - please test connection",
                    text_color="orange",
                )
            except Exception as ex:
                self.status_label.configure(
                    text=f"● Error reloading config: {str(ex)}", text_color="red"
                )
        else:
            # User cancelled
            self.status_label.configure(text="● Reconfiguration cancelled", text_color="gray")
