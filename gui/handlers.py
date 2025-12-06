"""
Event handlers for GUI actions
"""

import tkinter.messagebox as messagebox
from gui.download_manager import DownloadManager, OnlyFansDownloadManager


class EventHandlers:
    """Handles all GUI events and callbacks"""

    def __init__(self, state, window):
        self.state = state
        self.window = window
        self.sections = None
        self.download_manager = DownloadManager(
            progress_callback=self.on_progress, log_callback=self.on_log
        )

    def set_sections(self, sections):
        """Set UI sections after layout is built"""
        self.sections = sections

    def on_start_download(self):
        """Handle start button click"""
        if not self.sections:
            return

        # Validate
        if not self.sections["auth"].validate():
            self.sections["log"].add_log("Authentication required!", "error")
            return

        if not self.sections["creator"].validate():
            self.sections["log"].add_log("Creator username required!", "error")
            return

        # Save config from UI
        self.sections["auth"].save_to_config(self.state.config)
        self.sections["creator"].save_to_config(self.state.config)  # Saves to gui_state.json
        self.sections["settings"].save_to_config(self.state.config)

        # Get selected creators
        selected_creators = self.sections["creator"].get_selected_creators()
        if not selected_creators:
            self.sections["log"].add_log("No creators selected!", "error")
            return

        # Set config.user_names to ONLY the creator we're downloading
        # This is what the download system expects
        first_creator = selected_creators[0]
        self.state.config.user_names = {first_creator}
        self.state.config.current_download_creator = first_creator

        # If multiple selected, log info
        if len(selected_creators) > 1:
            self.sections["log"].add_log(
                f"Multiple creators selected. Downloading {first_creator} first. "
                f"({len(selected_creators)-1} other{'s' if len(selected_creators) > 2 else ''} selected - start new download after this completes)",
                "info",
            )

        # Update UI
        self.sections["buttons"]["start"].configure(state="disabled")
        self.sections["buttons"]["stop"].configure(state="normal")
        self.sections["status"].configure(text="Status: Downloading...")

        # Start download
        self.download_manager.start(self.state.config)
        self.sections["log"].add_log("Download started", "info")

    def on_stop_download(self):
        """Handle stop button click"""
        if not self.sections:
            return

        self.download_manager.stop()
        self.sections["log"].add_log("Stopping download...", "warning")
        self.sections["buttons"]["start"].configure(state="normal")
        self.sections["buttons"]["stop"].configure(state="disabled")
        self.sections["status"].configure(text="Status: Stopped")

    def on_progress(self, update):
        """Handle progress update from download thread"""
        if not self.sections:
            return

        # Schedule UI update on main thread
        self.window.after(0, self._update_progress_ui, update)

    def _update_progress_ui(self, update):
        """Update progress UI (runs on main thread)"""
        if not self.sections:
            return

        self.sections["progress"].update_progress(update)

        if update.status == "complete":
            self.sections["buttons"]["start"].configure(state="normal")
            self.sections["buttons"]["stop"].configure(state="disabled")
            self.sections["status"].configure(text="Status: Complete")
            self.sections["log"].add_log("Download completed!", "info")

        elif update.status == "error":
            self.sections["buttons"]["start"].configure(state="normal")
            self.sections["buttons"]["stop"].configure(state="disabled")
            self.sections["status"].configure(
                text=f"Status: Error - {update.message[:50]}"
            )

    def on_log(self, message, level):
        """Handle log message from download thread"""
        if not self.sections:
            return

        # Schedule UI update on main thread
        self.window.after(0, self.sections["log"].add_log, message, level)

    def on_close(self):
        """Handle window close request"""
        if self.download_manager.is_running:
            if messagebox.askyesno(
                "Confirm Exit", "Download in progress. Stop and exit?"
            ):
                self.download_manager.stop()
                self.window.destroy()
        else:
            self.window.destroy()

    def on_open_crop_tool(self):
        """Handle opening the image crop tool window (CustomTkinter version)"""
        from gui.tools.image_crop_window import ImageCropWindow
        from pathlib import Path

        # Get default output directory from download settings
        if self.state.config.download_directory:
            default_output = Path(self.state.config.download_directory) / "processed"
        else:
            default_output = Path.cwd() / "Downloads" / "processed"

        # Open crop tool window
        crop_window = ImageCropWindow(self.window, default_output_dir=default_output)
        crop_window.focus()

    def import_subscriptions(self) -> dict:
        """
        Import all Fansly subscriptions.

        Returns:
            dict: {'added': int, 'skipped': int}
        """
        # Get API instance
        api = self.state.config.get_api()

        # Step 1: Get all subscriptions
        response = api.get_subscriptions()

        # Check HTTP status first
        if response.status_code != 200:
            # Try to get error details
            try:
                error_detail = response.json()
                error_msg = error_detail.get('error', {}).get('message', response.text[:100])
            except (ValueError, KeyError, json.JSONDecodeError):
                error_msg = response.text[:100] if response.text else 'No error details'
            raise RuntimeError(f"Failed to fetch subscriptions from Fansly (HTTP {response.status_code}): {error_msg}")

        # get_json_response_contents already validates and extracts the 'response' field
        json_data = api.get_json_response_contents(response)

        if not json_data:
            raise RuntimeError("Failed to fetch subscriptions from Fansly (empty response)")

        # json_data is already the 'response' object, not the full JSON
        all_subscriptions = json_data.get('subscriptions', [])

        # Filter for active subscriptions only (status 3 = active, status 5 = inactive)
        subscriptions = [sub for sub in all_subscriptions if sub.get('status') == 3]

        if not subscriptions:
            return {'added': 0, 'skipped': 0}

        # Step 2: Extract account IDs from active subscriptions
        account_ids = [sub['accountId'] for sub in subscriptions]

        # Step 3: Batch lookup accounts to get usernames
        accounts_response = api.get_accounts_by_ids(account_ids)
        # get_json_response_contents already validates and extracts the 'response' field
        accounts_data = api.get_json_response_contents(accounts_response)

        if not accounts_data:
            raise RuntimeError("Failed to lookup account information")

        # accounts_data is already the 'response' array
        accounts = accounts_data if isinstance(accounts_data, list) else []

        # Step 4: Extract usernames
        usernames = [acc['username'] for acc in accounts if 'username' in acc]

        # Step 5: Add to creator list (avoiding duplicates)
        added = 0
        skipped = 0

        existing_creators = set(self.state.all_creators)

        for username in usernames:
            if username not in existing_creators:
                self.state.all_creators.append(username)
                self.state.selected_creators.add(username)  # Auto-select new imports
                added += 1
            else:
                skipped += 1

        # Step 6: Save GUI state
        self.state.save_gui_state()

        return {'added': added, 'skipped': skipped}


class OnlyFansEventHandlers:
    """Handles OnlyFans GUI events"""

    def __init__(self, state, window):
        self.state = state
        self.window = window
        self.sections = None
        self.download_manager = OnlyFansDownloadManager(
            progress_callback=self.on_progress,
            log_callback=self.on_log
        )

    def set_sections(self, sections):
        """Set UI sections after layout is built"""
        self.sections = sections

    def on_start_download(self):
        """Handle OF start button click"""
        if not self.sections:
            return

        # Validate
        if not self.state.config.has_credentials():
            self.sections["log"].add_log("OnlyFans authentication required!", "error")
            return

        # Get selected creators
        selected_creators = self.sections["creator"].get_selected_creators()
        if not selected_creators:
            self.sections["log"].add_log("No OF creators selected!", "error")
            return

        # Save config
        self.sections["auth"].save_to_config()
        self.sections["settings"].save_to_config(self.state.config)
        self.sections["creator"].save_to_config(self.state.config)

        # Set creators
        self.state.config.user_names = set(selected_creators)

        # Update UI
        self.sections["buttons"]["start"].configure(state="disabled")
        self.sections["buttons"]["stop"].configure(state="normal")
        self.sections["status"]["label"].configure(text="OnlyFans: Downloading...")

        # Start download
        self.download_manager.start(self.state.config)
        self.sections["log"].add_log("OF download started", "info")

    def on_stop_download(self):
        """Handle OF stop button click"""
        if not self.sections:
            return

        self.download_manager.stop()
        self.sections["log"].add_log("Stopping OF download...", "warning")
        self.sections["buttons"]["start"].configure(state="normal")
        self.sections["buttons"]["stop"].configure(state="disabled")
        self.sections["status"]["label"].configure(text="OnlyFans: Stopped")

    def on_progress(self, update):
        """Handle progress update"""
        if not self.sections:
            return
        self.window.after(0, self._update_progress_ui, update)

    def _update_progress_ui(self, update):
        """Update progress UI"""
        if not self.sections:
            return

        self.sections["progress"].update_progress(update)

        if update.status == "complete":
            self.sections["buttons"]["start"].configure(state="normal")
            self.sections["buttons"]["stop"].configure(state="disabled")
            self.sections["status"]["label"].configure(text="OnlyFans: Complete")
            self.sections["log"].add_log("OF download completed!", "info")

        elif update.status == "error":
            self.sections["buttons"]["start"].configure(state="normal")
            self.sections["buttons"]["stop"].configure(state="disabled")
            self.sections["status"]["label"].configure(text=f"OnlyFans: Error")

    def on_log(self, message, level):
        """Handle log message"""
        if not self.sections:
            return
        self.window.after(0, self.sections["log"].add_log, message, level)

    def on_open_crop_tool(self):
        """Handle opening the image crop tool window (CustomTkinter version)"""
        from gui.tools.image_crop_window import ImageCropWindow
        from pathlib import Path

        # Get default output directory from download settings
        if self.state.config.download_directory:
            default_output = Path(self.state.config.download_directory) / "processed"
        else:
            default_output = Path.cwd() / "Downloads" / "processed"

        # Open crop tool window
        crop_window = ImageCropWindow(self.window, default_output_dir=default_output)
        crop_window.focus()

    def on_close(self):
        """Handle window close"""
        if self.download_manager.is_running:
            if messagebox.askyesno("Confirm Exit", "OF download in progress. Stop and exit?"):
                self.download_manager.stop()
        self.window.destroy()

    def import_subscriptions(self) -> dict:
        """
        Import all OnlyFans subscriptions.

        Returns:
            dict: {'added': int, 'skipped': int}
        """
        # Get API instance
        api = self.state.config.get_api()

        all_creators = []
        offset = 0
        limit = 100

        # Paginate through all subscriptions
        while True:
            response = api.get_subscriptions(limit=limit, offset=offset)

            if not response:
                break

            # Handle both list and dict responses
            if isinstance(response, list):
                # Response is a list directly
                subscription_list = response
                has_more = len(subscription_list) >= limit
            elif isinstance(response, dict):
                # Response is a dict with 'list' key
                subscription_list = response.get('list', [])
                has_more = response.get('hasMore', False) or len(subscription_list) >= limit
            else:
                raise RuntimeError(f"Unexpected response type: {type(response)}")

            if not subscription_list:
                break

            # Extract usernames from response - only active subscriptions
            for sub in subscription_list:
                if not isinstance(sub, dict):
                    continue

                # Check if subscription is active
                # OnlyFans uses 'subscribedBy' field to indicate active subscription
                is_active = sub.get('subscribedBy', False)

                # Also check for 'subscribed' field as fallback
                if not is_active and 'subscribed' in sub:
                    is_active = sub.get('subscribed', False)

                # Only add if active and has username
                if is_active and 'username' in sub:
                    all_creators.append(sub['username'])

            # Check if more pages exist
            if not has_more:
                break

            offset += limit

        # Add to creator list (avoiding duplicates)
        added = 0
        skipped = 0

        existing_creators = set(self.state.all_creators)

        for username in all_creators:
            if username not in existing_creators:
                self.state.all_creators.append(username)
                self.state.selected_creators.add(username)  # Auto-select new imports
                added += 1
            else:
                skipped += 1

        # Save GUI state
        self.state.save_gui_state()

        return {'added': added, 'skipped': skipped}
