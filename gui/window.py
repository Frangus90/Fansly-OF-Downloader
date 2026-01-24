"""
Main application window
"""

import customtkinter as ctk
import tkinter.messagebox as messagebox
from pathlib import Path
from typing import Optional

from gui.layout import build_layout
from gui.handlers import EventHandlers
from gui.state import AppState
from gui.logger import log
from updater.auto_update import (
    UpdateInfo,
    check_for_update_async,
    download_update_async,
    apply_update,
    is_running_as_exe
)


class MainWindow(ctk.CTk):
    """Main GUI window for Fansly Downloader NG"""

    def __init__(self):
        super().__init__()

        # Window properties
        self.title("Fansly & OnlyFans Downloader NG v0.9.9")
        self.geometry("900x1000")
        self.minsize(1000, 700)

        # Set window icon (taskbar and title bar)
        self._set_window_icon()

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

        # Update banner (will be shown when update available)
        self.update_banner = None
        self.current_update_info: Optional[UpdateInfo] = None

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
            toggle_log_callback=self.toggle_log_window,
            check_update_callback=self._on_check_update_clicked
        )

        # Connect handlers to UI
        self.handlers.set_sections(self.sections)

        # OnlyFans tab will be built lazily on first access
        self.of_app_state = None
        self.of_handlers = None
        self.of_sections = None

        # Log window will be created lazily on first show
        self.log_window = None

        # Window events
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Add keyboard shortcut for log window toggle (Ctrl+L)
        self.bind("<Control-l>", lambda e: self.toggle_log_window())

        # Add tab change handler for lazy loading OnlyFans tab
        self.tab_view.configure(command=self._on_tab_changed)

        if wizard_was_completed:
            log("App initialization complete after wizard")

        # Schedule auto-update check (5 second delay for app to settle)
        if self.app_state.config.auto_check_updates:
            self.after(5000, self._check_for_updates_on_startup)

    def _on_tab_changed(self):
        """Handle tab switching - lazy load OnlyFans tab on first access"""
        current = self.tab_view.get()
        if current == "OnlyFans" and self.of_sections is None:
            # First time switching to OnlyFans - build it now
            self._build_onlyfans_tab()

    def _build_onlyfans_tab(self):
        """Build OnlyFans tab UI (called on first access)"""
        from gui.tabs.onlyfans_tab import build_onlyfans_layout
        from gui.state import OnlyFansAppState

        self.of_app_state = OnlyFansAppState()
        from gui.handlers import OnlyFansEventHandlers
        self.of_handlers = OnlyFansEventHandlers(self.of_app_state, self)
        self.of_sections = build_onlyfans_layout(
            self.tab_view.tab("OnlyFans"),
            self.of_app_state,
            self.of_handlers,
            toggle_log_callback=self.toggle_log_window,
            check_update_callback=self._on_check_update_clicked
        )
        self.of_handlers.set_sections(self.of_sections)
        
        # Connect log window if it already exists
        if self.log_window is not None:
            self.of_sections["log"] = self.log_window

    def on_close(self):
        """Handle window close event"""
        # Check if downloads are running and get user confirmation
        can_close = True
        if self.handlers.download_manager.is_running:
            can_close = self.handlers.on_close()
            if not can_close:
                return  # User cancelled
        
        if self.of_handlers is not None and self.of_handlers.download_manager.is_running:
            can_close = self.of_handlers.on_close()
            if not can_close:
                return  # User cancelled
        
        # Save log window state
        if self.log_window is not None:
            self.log_window._save_window_state()

        # Save GUI state before closing
        self.app_state.save_gui_state()
        if self.of_app_state is not None:
            self.of_app_state.save_gui_state()
        
        # Destroy window
        self.destroy()

    def toggle_log_window(self):
        """Toggle log window visibility"""
        # Create log window on first show
        if self.log_window is None:
            from gui.widgets.log_window import LogWindow
            self.log_window = LogWindow(self)
            self.sections["log"] = self.log_window
            # OnlyFans tab might not be built yet, handle that in _build_onlyfans_tab
        
        if self.log_window.winfo_viewable():
            self.log_window.withdraw()
            # Update both tab buttons (if they exist)
            if "status" in self.sections and "log_button" in self.sections["status"]:
                self.sections["status"]["log_button"].configure(text="Show Log")
            if hasattr(self, 'of_sections') and "status" in self.of_sections and "log_button" in self.of_sections["status"]:
                self.of_sections["status"]["log_button"].configure(text="Show Log")
        else:
            self.log_window.deiconify()
            self.log_window.lift()

            # Clear unread badge counts for both handlers
            self.handlers.unread_warnings = 0
            self.handlers.unread_errors = 0
            self.handlers._update_log_button_badge()

            if hasattr(self, 'of_handlers'):
                self.of_handlers.unread_warnings = 0
                self.of_handlers.unread_errors = 0
                self.of_handlers._update_log_button_badge()

            # Update both tab buttons (if they exist)
            if "status" in self.sections and "log_button" in self.sections["status"]:
                self.sections["status"]["log_button"].configure(text="Hide Log")
            if hasattr(self, 'of_sections') and "status" in self.of_sections and "log_button" in self.of_sections["status"]:
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

    def _set_window_icon(self):
        """Set window icon for taskbar and title bar"""
        import sys

        icon_path = Path("resources") / "fansly_ng.ico"

        # Check if running as frozen executable (PyInstaller)
        if getattr(sys, 'frozen', False):
            # Running in a bundle - icon should be in same dir as exe
            icon_path = Path(sys._MEIPASS) / "resources" / "fansly_ng.ico"

        # Set icon if file exists
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception as e:
                log(f"Warning: Could not set window icon: {e}")
        else:
            log(f"Warning: Icon file not found at {icon_path}")

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

    # ========== Auto-Update Methods ==========

    def _check_for_updates_on_startup(self):
        """Check for updates on startup (runs in background)"""
        log("Checking for updates...")

        check_for_update_async(
            current_version=self.app_state.config.program_version,
            skipped_version=self.app_state.config.skipped_update_version,
            callback=self._on_startup_update_check_result,
            force=False
        )

    def _on_check_update_clicked(self):
        """Handle manual check for update button click"""
        log("Manual update check initiated...")

        # Disable buttons while checking
        if self.sections and "status" in self.sections:
            btn = self.sections["status"].get("update_button")
            if btn:
                btn.configure(state="disabled", text="Checking...")

        if self.of_sections and "status" in self.of_sections:
            btn = self.of_sections["status"].get("update_button")
            if btn:
                btn.configure(state="disabled", text="Checking...")

        # Force check (ignore skipped version)
        check_for_update_async(
            current_version=self.app_state.config.program_version,
            skipped_version=None,  # Ignore skipped for manual check
            callback=self._on_manual_update_check_result,
            force=True
        )

    def _on_startup_update_check_result(self, update_info: Optional[UpdateInfo]):
        """Handle result of startup update check (called from background thread)"""
        # Schedule on main thread
        self.after(0, lambda: self._handle_update_check_result(update_info, is_manual=False))

    def _on_manual_update_check_result(self, update_info: Optional[UpdateInfo]):
        """Handle result of manual update check (called from background thread)"""
        # Schedule on main thread
        self.after(0, lambda: self._handle_update_check_result(update_info, is_manual=True))

    def _handle_update_check_result(self, update_info: Optional[UpdateInfo], is_manual: bool):
        """Process update check result on main thread"""
        # Re-enable buttons
        self._reset_update_buttons()

        if update_info:
            log(f"Update available: v{update_info.version}")
            self.current_update_info = update_info
            self._show_update_banner(update_info)
        else:
            if is_manual:
                log("Already running the latest version")
                if self.log_window is not None:
                    self.log_window.add_log("You are running the latest version!", "info")

    def _reset_update_buttons(self):
        """Reset update buttons to default state"""
        if self.sections and "status" in self.sections:
            btn = self.sections["status"].get("update_button")
            if btn:
                btn.configure(state="normal", text="Check for Update")

        if self.of_sections and "status" in self.of_sections:
            btn = self.of_sections["status"].get("update_button")
            if btn:
                btn.configure(state="normal", text="Check for Update")

    def _show_update_banner(self, update_info: UpdateInfo):
        """Show the update notification banner"""
        # Hide existing banner if any
        self._hide_update_banner()

        from gui.widgets.update_banner import UpdateBanner

        self.update_banner = UpdateBanner(
            self,
            update_info=update_info,
            on_update=self._start_update,
            on_skip=self._skip_version,
            on_dismiss=self._hide_update_banner
        )

        # Pack at top of window (before tab view)
        self.update_banner.pack(fill="x", padx=10, pady=(10, 0), before=self.tab_view)

    def _hide_update_banner(self):
        """Hide and destroy the update banner"""
        if self.update_banner:
            self.update_banner.destroy()
            self.update_banner = None

    def _skip_version(self, version: str):
        """Skip this version and don't notify again"""
        log(f"Skipping version {version}")

        # Save to config
        self.app_state.config.skipped_update_version = version
        self.app_state.config._save_config()

        # Hide banner
        self._hide_update_banner()

        if self.log_window is not None:
            self.log_window.add_log(f"Version {version} will be skipped", "info")

    def _start_update(self):
        """Start downloading and applying the update"""
        if not self.current_update_info:
            return

        # Check if running as exe
        if not is_running_as_exe():
            messagebox.showinfo(
                "Update Not Available",
                "Auto-update is only available when running as an executable.\n\n"
                "Please download the latest version manually from GitHub."
            )
            return

        log(f"Starting download of v{self.current_update_info.version}...")

        # Replace banner with progress banner
        self._hide_update_banner()

        from gui.widgets.update_banner import DownloadProgressBanner

        self.update_banner = DownloadProgressBanner(
            self,
            on_cancel=self._cancel_update
        )
        self.update_banner.pack(fill="x", padx=10, pady=(10, 0), before=self.tab_view)

        # Start download in background
        download_update_async(
            download_url=self.current_update_info.download_url,
            progress_callback=self._on_download_progress,
            complete_callback=self._on_download_complete
        )

    def _on_download_progress(self, downloaded: int, total: int):
        """Handle download progress (called from background thread)"""
        self.after(0, lambda: self._update_download_progress(downloaded, total))

    def _update_download_progress(self, downloaded: int, total: int):
        """Update download progress on main thread"""
        if self.update_banner and hasattr(self.update_banner, 'update_progress'):
            self.update_banner.update_progress(downloaded, total)

    def _on_download_complete(self, downloaded_path: Optional[Path]):
        """Handle download completion (called from background thread)"""
        self.after(0, lambda: self._handle_download_complete(downloaded_path))

    def _handle_download_complete(self, downloaded_path: Optional[Path]):
        """Process download completion on main thread"""
        if downloaded_path:
            log(f"Download complete: {downloaded_path}")

            if self.update_banner and hasattr(self.update_banner, 'set_complete'):
                self.update_banner.set_complete()

            # Ask user to restart
            self.after(500, lambda: self._show_restart_dialog(downloaded_path))
        else:
            log("Download failed")

            if self.update_banner and hasattr(self.update_banner, 'set_error'):
                self.update_banner.set_error("Download failed")

            if self.log_window is not None:
                self.log_window.add_log("Update download failed. Please try again or download manually.", "error")

    def _show_restart_dialog(self, downloaded_path: Path):
        """Show restart confirmation dialog"""
        result = messagebox.askyesno(
            "Update Downloaded",
            f"Version {self.current_update_info.version} has been downloaded.\n\n"
            "Would you like to restart now to apply the update?\n\n"
            "(The application will close and reopen automatically)"
        )

        if result:
            self._apply_update_and_restart(downloaded_path)
        else:
            self._hide_update_banner()
            if self.log_window is not None:
                self.log_window.add_log("Update will be applied next time you start the application", "info")

    def _apply_update_and_restart(self, downloaded_path: Path):
        """Apply update and restart the application"""
        log("Applying update and restarting...")

        success = apply_update(downloaded_path)

        if success:
            # Exit application - update script will restart it
            if self.log_window is not None:
                self.log_window.add_log("Restarting to apply update...", "info")
            self.after(500, self._force_close)
        else:
            messagebox.showerror(
                "Update Failed",
                "Failed to apply the update.\n\n"
                "Please download the latest version manually from GitHub."
            )
            self._hide_update_banner()

    def _cancel_update(self):
        """Cancel the update download"""
        log("Update cancelled by user")
        self._hide_update_banner()

    def _force_close(self):
        """Force close the application without prompts"""
        # Save state
        if hasattr(self, 'log_window'):
            self.log_window._save_window_state()
        self.app_state.save_gui_state()

        # Destroy window
        self.destroy()

        # Exit process
        import sys
        sys.exit(0)
