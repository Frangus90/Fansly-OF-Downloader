"""
Main application window
"""

import customtkinter as ctk
from pathlib import Path
from gui.layout import build_layout
from gui.handlers import EventHandlers
from gui.state import AppState
from gui.logger import log


class MainWindow(ctk.CTk):
    """Main GUI window for Fansly Downloader NG"""

    def __init__(self):
        super().__init__()

        # Window properties
        self.title("Fansly & OnlyFans Downloader NG v0.9.9")
        self.geometry("900x1000")
        self.minsize(1000, 700)

        # Initialize tkdnd for drag-and-drop support in child windows
        self._init_tkdnd()

        # Check for setup wizard BEFORE initializing app state
        # This ensures wizard runs before config is loaded
        self._wizard_checked = False
        self.after(100, self._check_for_wizard_then_init)

    def _check_for_wizard_then_init(self):
        """Check for wizard first, then initialize the rest of the app"""
        from gui.app import should_run_wizard
        from gui.setup_wizard import SetupWizard

        config_path = Path.cwd() / "config.ini"

        wizard_was_completed = False
        if should_run_wizard(config_path):
            log("Showing setup wizard...")

            # Show wizard
            wizard = SetupWizard(self)
            self.wait_window(wizard)

            # Check if wizard completed successfully
            if not wizard.success:
                # User cancelled - exit application
                log("Setup cancelled by user")
                self.destroy()
                import sys
                sys.exit(0)

            log("Setup wizard completed successfully")
            wizard_was_completed = True

            # Add a small delay to ensure file is fully written to disk
            # This is especially important for EXE builds
            import time
            time.sleep(0.3)

            # Verify config file exists after wizard
            if not config_path.exists():
                log(f"ERROR: Config file not found after wizard completion: {config_path}")
                log(f"  Checked at: {config_path.absolute()}")
                log(f"  Current working directory: {Path.cwd()}")
                log(f"  Files in current dir:")
                try:
                    for f in sorted(Path.cwd().iterdir())[:15]:
                        log(f"    - {f.name}")
                except Exception as e:
                    log(f"    Error listing files: {e}")
            else:
                import os
                file_size = os.path.getsize(config_path)
                log(f"Config file exists after wizard: {config_path} ({file_size} bytes)")
                log(f"  Absolute path: {config_path.absolute()}")

        # Now initialize the rest of the app
        self._initialize_app(wizard_was_completed=wizard_was_completed)

    def _initialize_app(self, wizard_was_completed=False):
        """Initialize application state and UI after wizard check"""
        if wizard_was_completed:
            log("Initializing app after wizard completion...")

        # Application state
        self.app_state = AppState()

        if wizard_was_completed:
            log(f"Config loaded - token: {'SET' if self.app_state.config.token else 'NOT SET'}")
            log(f"Config loaded - user_agent: {'SET' if self.app_state.config.user_agent else 'NOT SET'}")
            log(f"Config loaded - check_key: {self.app_state.config.check_key if self.app_state.config.check_key else 'NOT SET'}")

        # Event handlers
        self.handlers = EventHandlers(self.app_state, self)

        # Create tabbed interface
        self.tab_view = ctk.CTkTabview(self, width=880)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # Add tabs
        self.tab_view.add("Fansly")
        self.tab_view.add("OnlyFans")

        # Build Fansly UI in first tab
        self.sections = build_layout(
            self.tab_view.tab("Fansly"),
            self.app_state,
            self.handlers,
            toggle_log_callback=self.toggle_log_window
        )

        # Build OnlyFans UI in second tab
        from gui.tabs.onlyfans_tab import build_onlyfans_layout
        from gui.state import OnlyFansAppState

        self.of_app_state = OnlyFansAppState()
        from gui.handlers import OnlyFansEventHandlers
        self.of_handlers = OnlyFansEventHandlers(self.of_app_state, self)
        self.of_sections = build_onlyfans_layout(
            self.tab_view.tab("OnlyFans"),
            self.of_app_state,
            self.of_handlers,
            toggle_log_callback=self.toggle_log_window
        )
        self.of_handlers.set_sections(self.of_sections)

        # Connect handlers to UI
        self.handlers.set_sections(self.sections)

        # Create shared log window for both tabs
        from gui.widgets.log_window import LogWindow
        self.log_window = LogWindow(self)
        self.sections["log"] = self.log_window     # Fansly tab
        self.of_sections["log"] = self.log_window  # OnlyFans tab (shared)

        # Window events
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Add keyboard shortcut for log window toggle (Ctrl+L)
        self.bind("<Control-l>", lambda e: self.toggle_log_window())

        if wizard_was_completed:
            log("App initialization complete after wizard")

    def on_close(self):
        """Handle window close event"""
        # Save log window state
        if hasattr(self, 'log_window'):
            self.log_window._save_window_state()

        # Save GUI state before closing
        self.app_state.save_gui_state()
        # Handle download stop if needed
        self.handlers.on_close()

    def toggle_log_window(self):
        """Toggle log window visibility"""
        if self.log_window.winfo_viewable():
            self.log_window.withdraw()
            # Update both tab buttons
            self.sections["status"]["log_button"].configure(text="Show Log")
            self.of_sections["status"]["log_button"].configure(text="Show Log")
        else:
            self.log_window.deiconify()
            self.log_window.lift()

            # Clear unread badge counts for both handlers
            self.handlers.unread_warnings = 0
            self.handlers.unread_errors = 0
            self.handlers._update_log_button_badge()

            self.of_handlers.unread_warnings = 0
            self.of_handlers.unread_errors = 0
            self.of_handlers._update_log_button_badge()

            # Update both tab buttons
            self.sections["status"]["log_button"].configure(text="Hide Log")
            self.of_sections["status"]["log_button"].configure(text="Hide Log")

    def open_log_file(self):
        """Open log file in default text editor"""
        import os
        import platform

        log_path = Path.cwd() / "fansly_downloader.log"

        if not log_path.exists():
            log("Attempted to open log file but it doesn't exist yet")
            return

        log(f"Opening log file: {log_path}")

        try:
            # Open with default text editor
            if platform.system() == 'Windows':
                os.startfile(log_path)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{log_path}"')
            else:  # Linux
                os.system(f'xdg-open "{log_path}"')
        except Exception as e:
            log(f"Error opening log file: {e}")

    def _init_tkdnd(self):
        """Initialize tkdnd for drag-and-drop support"""
        try:
            # Import DnDWrapper which adds DnD methods to tkinter.BaseWidget
            from tkinterdnd2.TkinterDnD import _require, DnDWrapper
            # The import above adds drop_target_register, dnd_bind etc. to all widgets

            # Load tkdnd into the Tcl interpreter
            _require(self)
            # Now all widgets (including CTk widgets) have DnD methods available
        except ImportError:
            # tkinterdnd2 not installed
            pass
        except Exception:
            # tkdnd loading failed
            pass

    def run(self):
        """Start the GUI main loop"""
        self.mainloop()
