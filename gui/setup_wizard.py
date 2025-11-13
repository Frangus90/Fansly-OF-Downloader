"""
First-time setup wizard for creating config.ini
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
from configparser import ConfigParser
import threading
from gui.logger import log


class SetupWizard(ctk.CTkToplevel):
    """First-time setup wizard modal dialog"""

    def __init__(self, parent):
        super().__init__(parent)

        # Modal settings
        self.title("Fansly Downloader NG - First Time Setup")
        self.geometry("600x500")
        self.resizable(False, False)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Result
        self.success = False

        # Current page
        self.current_page = 0

        # Data storage
        self.data = {
            "token": "",
            "user_agent": "",
            "download_dir": str(Path.cwd() / "Downloads"),
            "download_mode": "Normal",
            "download_previews": True,
            "open_folder": True,
            "separate_timeline": True,
        }

        # Build UI
        self.build_ui()

        # Show first page
        self.show_page(0)

    def build_ui(self):
        """Build all pages"""
        # Container frame
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        # Pages list
        self.pages = [
            self.build_welcome_page(),
            self.build_token_page(),
            self.build_user_agent_page(),
            self.build_settings_page(),
            self.build_progress_page(),
            self.build_complete_page(),
        ]

        # Hide all pages initially
        for page in self.pages:
            page.pack_forget()

    def build_welcome_page(self):
        """Page 0: Welcome"""
        page = ctk.CTkFrame(self.container)

        # Title
        title = ctk.CTkLabel(
            page, text="Welcome to Fansly Downloader NG!", font=("Arial", 20, "bold")
        )
        title.pack(pady=(40, 10))

        # Instructions
        instructions = ctk.CTkLabel(
            page,
            text="This setup wizard will help you configure\nthe application.\n\n"
            "You will need:\n"
            "• Authorization Token from your browser\n"
            "• User Agent from your browser\n"
            "• Download folder location",
            font=("Arial", 14),
            justify="left",
        )
        instructions.pack(pady=40)

        # Buttons
        btn_frame = ctk.CTkFrame(page)
        btn_frame.pack(side="bottom", fill="x", pady=10)

        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.on_cancel)
        cancel_btn.pack(side="right", padx=5)

        next_btn = ctk.CTkButton(btn_frame, text="Next", command=self.next_page)
        next_btn.pack(side="right", padx=5)

        return page

    def build_token_page(self):
        """Page 1: Authorization Token"""
        page = ctk.CTkFrame(self.container)

        # Title
        title = ctk.CTkLabel(
            page, text="Authentication - Step 1/2", font=("Arial", 18, "bold")
        )
        title.pack(pady=(10, 20))

        # Token label
        token_label = ctk.CTkLabel(page, text="Authorization Token:")
        token_label.pack(anchor="w", padx=20)

        # Token entry frame
        token_frame = ctk.CTkFrame(page)
        token_frame.pack(fill="x", padx=20, pady=5)

        self.token_entry = ctk.CTkEntry(token_frame, width=450, show="*")
        self.token_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.show_token_btn = ctk.CTkButton(
            token_frame, text="Show", width=80, command=self.toggle_token_visibility
        )
        self.show_token_btn.pack(side="right")

        # Instructions
        instructions = ctk.CTkTextbox(page, height=150, width=500)
        instructions.pack(padx=20, pady=10)
        instructions.insert(
            "1.0",
            "How to get your token:\n\n"
            "1. Open Fansly.com in your browser and log in\n"
            "2. Press F12 to open DevTools\n"
            "3. Go to Application/Storage > Cookies\n"
            "4. Find 'session_active_session' cookie\n"
            "5. Copy the entire cookie value and paste it here\n"
            "   (The wizard will automatically extract the token)",
        )
        instructions.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(page)
        btn_frame.pack(side="bottom", fill="x", pady=10)

        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.on_cancel)
        cancel_btn.pack(side="right", padx=5)

        next_btn = ctk.CTkButton(btn_frame, text="Next", command=self.save_and_next)
        next_btn.pack(side="right", padx=5)

        back_btn = ctk.CTkButton(btn_frame, text="Back", command=self.prev_page)
        back_btn.pack(side="right", padx=5)

        return page

    def build_user_agent_page(self):
        """Page 2: User Agent"""
        page = ctk.CTkFrame(self.container)

        # Title
        title = ctk.CTkLabel(
            page, text="Authentication - Step 2/2", font=("Arial", 18, "bold")
        )
        title.pack(pady=(10, 20))

        # User Agent label
        ua_label = ctk.CTkLabel(page, text="User Agent:")
        ua_label.pack(anchor="w", padx=20)

        # User Agent entry
        self.ua_entry = ctk.CTkEntry(page, width=500)
        self.ua_entry.pack(fill="x", padx=20, pady=5)

        # Default button
        default_btn = ctk.CTkButton(
            page, text="Use Default Mozilla UA", command=self.use_default_ua
        )
        default_btn.pack(pady=10)

        # Instructions
        instructions = ctk.CTkTextbox(page, height=120, width=500)
        instructions.pack(padx=20, pady=10)
        instructions.insert(
            "1.0",
            "How to get your User Agent:\n\n"
            "1. In DevTools (F12), go to Network tab\n"
            "2. Refresh the page\n"
            "3. Click any request\n"
            "4. Find 'User-Agent' in Request Headers\n"
            "5. Copy the entire value",
        )
        instructions.configure(state="disabled")

        # Buttons
        btn_frame = ctk.CTkFrame(page)
        btn_frame.pack(side="bottom", fill="x", pady=10)

        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.on_cancel)
        cancel_btn.pack(side="right", padx=5)

        next_btn = ctk.CTkButton(btn_frame, text="Next", command=self.save_and_next)
        next_btn.pack(side="right", padx=5)

        back_btn = ctk.CTkButton(btn_frame, text="Back", command=self.prev_page)
        back_btn.pack(side="right", padx=5)

        return page

    def build_settings_page(self):
        """Page 3: Download Settings"""
        page = ctk.CTkFrame(self.container)

        # Title
        title = ctk.CTkLabel(
            page, text="Download Settings", font=("Arial", 18, "bold")
        )
        title.pack(pady=(10, 20))

        # Download directory
        dir_label = ctk.CTkLabel(page, text="Download Directory:")
        dir_label.pack(anchor="w", padx=20)

        dir_frame = ctk.CTkFrame(page)
        dir_frame.pack(fill="x", padx=20, pady=5)

        self.dir_entry = ctk.CTkEntry(dir_frame, width=380)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.dir_entry.insert(0, self.data["download_dir"])

        browse_btn = ctk.CTkButton(
            dir_frame, text="Browse...", width=100, command=self.browse_directory
        )
        browse_btn.pack(side="right")

        # Download mode
        mode_label = ctk.CTkLabel(page, text="Download Mode:")
        mode_label.pack(anchor="w", padx=20, pady=(15, 5))

        self.mode_var = ctk.StringVar(value="Normal")

        normal_radio = ctk.CTkRadioButton(
            page,
            text="Normal (Messages + Timeline)",
            variable=self.mode_var,
            value="Normal",
        )
        normal_radio.pack(anchor="w", padx=40)

        timeline_radio = ctk.CTkRadioButton(
            page, text="Timeline Only", variable=self.mode_var, value="Timeline"
        )
        timeline_radio.pack(anchor="w", padx=40)

        messages_radio = ctk.CTkRadioButton(
            page, text="Messages Only", variable=self.mode_var, value="Messages"
        )
        messages_radio.pack(anchor="w", padx=40)

        # Options
        options_label = ctk.CTkLabel(page, text="Options:")
        options_label.pack(anchor="w", padx=20, pady=(15, 5))

        self.preview_var = ctk.BooleanVar(value=True)
        preview_check = ctk.CTkCheckBox(
            page, text="Download media previews", variable=self.preview_var
        )
        preview_check.pack(anchor="w", padx=40, pady=2)

        self.open_folder_var = ctk.BooleanVar(value=True)
        open_folder_check = ctk.CTkCheckBox(
            page, text="Open folder when finished", variable=self.open_folder_var
        )
        open_folder_check.pack(anchor="w", padx=40, pady=2)

        self.separate_timeline_var = ctk.BooleanVar(value=True)
        separate_check = ctk.CTkCheckBox(
            page, text="Separate timeline folder", variable=self.separate_timeline_var
        )
        separate_check.pack(anchor="w", padx=40, pady=2)

        # Buttons
        btn_frame = ctk.CTkFrame(page)
        btn_frame.pack(side="bottom", fill="x", pady=10)

        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.on_cancel)
        cancel_btn.pack(side="right", padx=5)

        finish_btn = ctk.CTkButton(
            btn_frame, text="Finish", command=self.create_config, fg_color="green"
        )
        finish_btn.pack(side="right", padx=5)

        back_btn = ctk.CTkButton(btn_frame, text="Back", command=self.prev_page)
        back_btn.pack(side="right", padx=5)

        return page

    def build_progress_page(self):
        """Page 4: Creating configuration"""
        page = ctk.CTkFrame(self.container)

        # Title
        title = ctk.CTkLabel(page, text="Setting Up...", font=("Arial", 18, "bold"))
        title.pack(pady=(50, 30))

        # Status label
        self.status_label = ctk.CTkLabel(
            page, text="⏳ Fetching check_key from Fansly...", font=("Arial", 14)
        )
        self.status_label.pack(pady=10)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(page, width=400)
        self.progress_bar.pack(pady=20)
        self.progress_bar.set(0)

        # Info
        info = ctk.CTkLabel(page, text="Please wait...")
        info.pack(pady=10)

        return page

    def build_complete_page(self):
        """Page 5: Complete"""
        page = ctk.CTkFrame(self.container)

        # Success icon/text
        success = ctk.CTkLabel(
            page,
            text="✓ Configuration file created!",
            font=("Arial", 24, "bold"),
            text_color="green",
        )
        success.pack(pady=(80, 30))

        # Info
        info = ctk.CTkLabel(
            page,
            text="Your settings have been saved to config.ini\n\n"
            "You can now start using Fansly Downloader NG",
            font=("Arial", 14),
        )
        info.pack(pady=20)

        # Launch button
        launch_btn = ctk.CTkButton(
            page,
            text="Launch GUI",
            command=self.on_complete,
            height=50,
            font=("Arial", 16, "bold"),
            fg_color="green",
        )
        launch_btn.pack(pady=40)

        return page

    # Helper methods

    def show_page(self, page_num):
        """Show specific page"""
        # Hide current page
        self.pages[self.current_page].pack_forget()

        # Show new page
        self.current_page = page_num
        self.pages[page_num].pack(fill="both", expand=True)

    def next_page(self):
        """Go to next page"""
        if self.current_page < len(self.pages) - 1:
            self.show_page(self.current_page + 1)

    def prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def save_and_next(self):
        """Save current page data and go to next"""
        # Validate and save based on current page
        if self.current_page == 1:  # Token page
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

            if not token or len(token) < 50:
                # Show error
                messagebox.showwarning(
                    "Invalid Token",
                    "Please enter a valid authorization token (at least 50 characters)",
                )
                return
            self.data["token"] = token

        elif self.current_page == 2:  # User Agent page
            ua = self.ua_entry.get().strip()
            if not ua or len(ua) < 40:
                # Show error
                messagebox.showwarning(
                    "Invalid User Agent",
                    "Please enter a valid user agent (at least 40 characters)",
                )
                return
            self.data["user_agent"] = ua

        self.next_page()

    def toggle_token_visibility(self):
        """Toggle token show/hide"""
        if self.token_entry.cget("show") == "*":
            self.token_entry.configure(show="")
            self.show_token_btn.configure(text="Hide")
        else:
            self.token_entry.configure(show="*")
            self.show_token_btn.configure(text="Show")

    def use_default_ua(self):
        """Fill in default Mozilla User Agent"""
        default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.ua_entry.delete(0, "end")
        self.ua_entry.insert(0, default_ua)

    def browse_directory(self):
        """Browse for download directory"""
        directory = filedialog.askdirectory(title="Select Download Directory")
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)

    def create_config(self):
        """Create config.ini file"""
        # Save settings from page 3
        self.data["download_dir"] = self.dir_entry.get().strip()
        self.data["download_mode"] = self.mode_var.get()
        self.data["download_previews"] = self.preview_var.get()
        self.data["open_folder"] = self.open_folder_var.get()
        self.data["separate_timeline"] = self.separate_timeline_var.get()

        # Show progress page
        self.show_page(4)

        # Start background thread for config creation
        thread = threading.Thread(target=self._create_config_thread, daemon=True)
        thread.start()

    def _create_config_thread(self):
        """Background thread to create config"""
        try:
            # Update status
            self.after(0, self.update_status, "Fetching check_key from Fansly...", 0.2)

            # Fetch check_key
            check_key = None
            fetch_success = False
            try:
                from utils.web import guess_check_key

                check_key = guess_check_key(
                    main_js_pattern=r'\ssrc\s*=\s*"(main\..*?\.js)"',
                    check_key_pattern=r'this\.checkKey_\s*=\s*["' + "']([^\"']+)[\"']",
                    user_agent=self.data["user_agent"],
                )

                if check_key and isinstance(check_key, str) and len(check_key.strip()) > 0:
                    fetch_success = True
                    log(f"Successfully fetched check_key from Fansly: {check_key}")
                else:
                    log("Failed to fetch check_key from Fansly (returned None or empty)")

            except Exception as ex:
                log(f"Failed to fetch check_key (exception): {ex}")
                import traceback
                log(traceback.format_exc())

            # Ensure check_key is never None or empty - use default as fallback
            if not fetch_success:
                check_key = "qybZy9-fyszis-bybxyf"
                log(f"Using default fallback check_key: {check_key}")
                log("  (This is normal if Fansly website is unreachable or has changed structure)")

            self.after(0, self.update_status, "Creating configuration file...", 0.6)

            # Create config.ini
            config = ConfigParser()

            # TargetedCreator section
            config.add_section("TargetedCreator")
            config.set("TargetedCreator", "username", "")  # Empty initially

            # MyAccount section
            config.add_section("MyAccount")
            # IMPORTANT: Use PascalCase field names to match config loader (config.py:175-180)
            config.set("MyAccount", "Authorization_Token", self.data["token"])
            config.set("MyAccount", "User_Agent", self.data["user_agent"])
            config.set("MyAccount", "Check_Key", check_key)

            # Options section
            config.add_section("Options")
            config.set("Options", "download_directory", self.data["download_dir"])
            config.set("Options", "download_mode", self.data["download_mode"])
            config.set("Options", "metadata_handling", "Advanced")
            config.set("Options", "show_downloads", "True")
            config.set("Options", "show_skipped_downloads", "True")
            config.set(
                "Options",
                "download_media_previews",
                str(self.data["download_previews"]),
            )
            config.set(
                "Options", "open_folder_when_finished", str(self.data["open_folder"])
            )
            config.set("Options", "separate_messages", "True")
            config.set("Options", "separate_previews", "False")
            config.set(
                "Options", "separate_timeline", str(self.data["separate_timeline"])
            )
            config.set("Options", "use_duplicate_threshold", "False")
            config.set("Options", "use_folder_suffix", "True")
            config.set("Options", "interactive", "True")
            config.set("Options", "prompt_on_exit", "True")
            config.set("Options", "timeline_retries", "3")
            config.set("Options", "timeline_delay_seconds", "45")

            # Cache section
            config.add_section("Cache")

            # Logic section
            config.add_section("Logic")
            config.set(
                "Logic", "check_key_pattern", r'this\.checkKey_\s*=\s*["' + "']([^\"']+)[\"']"
            )
            config.set("Logic", "main_js_pattern", r'\ssrc\s*=\s*"(main\..*?\.js)"')

            self.after(0, self.update_status, "Saving configuration...", 0.9)

            # Write config file
            config_path = Path.cwd() / "config.ini"
            log(f"Writing config to: {config_path}")
            log(f"Current working directory: {Path.cwd()}")

            with open(config_path, "w", encoding="utf-8") as f:
                config.write(f)
                f.flush()  # Ensure buffer is written

            # Verify file was written
            import os
            if config_path.exists():
                file_size = os.path.getsize(config_path)
                log(f"Config file written successfully ({file_size} bytes)")

                # Double-check all critical fields were written correctly (using PascalCase)
                verify_parser = ConfigParser()
                verify_parser.read(config_path, encoding="utf-8")
                written_token = verify_parser.get("MyAccount", "Authorization_Token", fallback="NOT_FOUND")
                written_ua = verify_parser.get("MyAccount", "User_Agent", fallback="NOT_FOUND")
                written_check_key = verify_parser.get("MyAccount", "Check_Key", fallback="NOT_FOUND")
                log(f"Verified Authorization_Token in file: {'SET (' + str(len(written_token)) + ' chars)' if written_token != 'NOT_FOUND' else 'NOT_FOUND'}")
                log(f"Verified User_Agent in file: {'SET (' + str(len(written_ua)) + ' chars)' if written_ua != 'NOT_FOUND' else 'NOT_FOUND'}")
                log(f"Verified Check_Key in file: {written_check_key}")
            else:
                log(f"ERROR: Config file not found after write: {config_path}")

            self.after(0, self.update_status, "Complete!", 1.0)

            # Wait a bit then show complete page
            import time
            time.sleep(0.5)

            self.after(0, self.show_complete)

        except Exception as ex:
            self.after(0, self.show_error, str(ex))

    def update_status(self, text, progress):
        """Update status label and progress bar"""
        self.status_label.configure(text=text)
        self.progress_bar.set(progress)

    def show_complete(self):
        """Show completion page"""
        self.show_page(5)

    def show_error(self, error):
        """Show error message"""
        messagebox.showerror(
            "Setup Error", f"Failed to create configuration:\n\n{error}"
        )
        # Go back to settings page
        self.show_page(3)

    def on_complete(self):
        """Handle completion"""
        self.success = True
        self.destroy()

    def on_cancel(self):
        """Handle cancellation"""
        self.success = False
        self.destroy()
