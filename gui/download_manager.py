"""
Download manager for background thread execution
"""

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class ProgressUpdate:
    """Data structure for progress updates"""

    type: str  # 'timeline', 'messages', 'media', 'complete', 'error'
    current: int = 0
    total: int = 0
    current_file: str = ""
    status: str = "running"  # 'running', 'stopped', 'complete', 'error'
    speed: float = 0.0  # MB/s
    duplicates: int = 0
    downloaded: int = 0
    message: str = ""


class DownloadManager:
    """Simple download manager - start/stop only"""

    def __init__(
        self,
        progress_callback: Callable[[ProgressUpdate], None],
        log_callback: Callable[[str, str], None],
    ):
        """
        Initialize download manager

        Args:
            progress_callback: Function to call with progress updates
            log_callback: Function to call with log messages (message, level)
        """
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        self.is_running = False
        
        # Progress throttling
        self._last_progress_time = 0.0
        self._pending_progress: Optional[ProgressUpdate] = None
        self._progress_throttle_ms = 100  # Max 10 updates/sec

    def start(self, config):
        """Start download in background thread"""
        if self.is_running:
            self.log_callback("Download already running", "warning")
            return

        self.stop_flag.clear()
        self.is_running = True

        self.thread = threading.Thread(
            target=self._download_worker, args=(config,), daemon=True
        )
        self.thread.start()

    def stop(self):
        """Stop the download"""
        if not self.is_running:
            return

        self.stop_flag.set()
        self.is_running = False
        self.log_callback("Download stop requested", "info")

    def _download_worker(self, config):
        """Worker thread that runs the download"""
        try:
            # Import the download runner in the worker thread
            # This avoids circular imports because download_runner
            # is never imported at module level
            from gui.download_runner import run_download

            # Run the download with callbacks
            run_download(
                config,
                self.stop_flag,
                self._handle_progress,
                self._handle_log
            )

            # Send completion update
            if not self.stop_flag.is_set():
                self._send_progress(
                    ProgressUpdate(
                        type="complete",
                        status="complete",
                        message="Download completed successfully!",
                    )
                )
                self.log_callback("Download complete!", "info")

        except Exception as ex:
            # Import error types here to avoid circular imports
            from errors import ApiError, DownloadError, ConfigError, MediaError
            
            error_type = type(ex).__name__
            error_msg = f"Download error ({error_type}): {ex}"
            self.log_callback(error_msg, "error")
            
            # Provide more specific error messages based on exception type
            if isinstance(ex, (ApiError, DownloadError, MediaError, ConfigError)):
                detailed_msg = f"{error_type}: {ex}"
            else:
                import traceback
                detailed_msg = f"Unexpected {error_type}: {ex}\n{traceback.format_exc()}"
            
            self._send_progress(
                ProgressUpdate(type="error", status="error", message=detailed_msg)
            )

        finally:
            # Flush any pending progress before finishing
            self._flush_pending_progress()
            self.is_running = False

    def _handle_progress(self, data: dict):
        """Convert dict to ProgressUpdate and send to callback"""
        update = ProgressUpdate(
            type=data.get("type", "unknown"),
            current=data.get("current", 0),
            total=data.get("total", 0),
            current_file=data.get("current_file", ""),
            status=data.get("status", "running"),
            speed=data.get("speed", 0.0),
            duplicates=data.get("duplicates", 0),
            downloaded=data.get("downloaded", 0),
            message=data.get("message", ""),
        )
        self._send_progress(update)

    def _handle_log(self, message: str, level: str):
        """Forward log message to GUI"""
        self.log_callback(message, level)

    def _send_progress(self, update: ProgressUpdate):
        """Send progress update to callback with throttling"""
        # Always store latest update
        self._pending_progress = update
        
        # Throttle: only send if enough time has passed or if it's a completion/error
        current_time = time.time() * 1000
        is_important = update.status in ("complete", "error", "stopped")
        
        if is_important or (current_time - self._last_progress_time >= self._progress_throttle_ms):
            self._last_progress_time = current_time
            try:
                self.progress_callback(self._pending_progress)
                self._pending_progress = None
            except Exception as ex:
                # Log error using log callback if available, otherwise fallback to print
                try:
                    self.log_callback(f"Progress callback error: {ex}", "error")
                except Exception:
                    # Fallback if log callback also fails
                    print(f"Progress callback error: {ex}")
    
    def _flush_pending_progress(self):
        """Flush any pending progress update (called on completion/error)"""
        if self._pending_progress is not None:
            try:
                self.progress_callback(self._pending_progress)
                self._pending_progress = None
            except Exception:
                pass


class OnlyFansDownloadManager:
    """Download manager for OnlyFans"""

    def __init__(
        self,
        progress_callback: Callable[[ProgressUpdate], None],
        log_callback: Callable[[str, str], None],
    ):
        """Initialize OF download manager"""
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()
        self.is_running = False
        
        # Progress throttling
        self._last_progress_time = 0.0
        self._pending_progress: Optional[ProgressUpdate] = None
        self._progress_throttle_ms = 100  # Max 10 updates/sec

    def start(self, config):
        """Start OF download in background thread"""
        if self.is_running:
            self.log_callback("OF download already running", "warning")
            return

        self.stop_flag.clear()
        self.is_running = True

        self.thread = threading.Thread(
            target=self._download_worker, args=(config,), daemon=True
        )
        self.thread.start()

    def stop(self):
        """Stop OF download"""
        if not self.is_running:
            return

        self.stop_flag.set()
        self.is_running = False
        self.log_callback("OF download stop requested", "info")

    def _download_worker(self, config):
        """Worker thread for OF downloads"""
        try:
            # Import the OF download runner
            from gui.download_runner import run_onlyfans_download

            # Run download
            run_onlyfans_download(
                config,
                self.stop_flag,
                self._handle_progress,
                self._handle_log
            )

            # Send completion
            if not self.stop_flag.is_set():
                self._send_progress(
                    ProgressUpdate(
                        type="complete",
                        status="complete",
                        message="OF download completed!",
                    )
                )
                self.log_callback("OF download complete!", "info")

        except Exception as ex:
            error_msg = f"OF download error: {ex}"
            self.log_callback(error_msg, "error")
            self._send_progress(
                ProgressUpdate(type="error", status="error", message=str(ex))
            )

        finally:
            # Flush any pending progress before finishing
            self._flush_pending_progress()
            self.is_running = False

    def _handle_progress(self, data: dict):
        """Convert dict to ProgressUpdate"""
        update = ProgressUpdate(
            type=data.get("type", "unknown"),
            current=data.get("current", 0),
            total=data.get("total", 0),
            current_file=data.get("current_file", ""),
            status=data.get("status", "running"),
            speed=data.get("speed", 0.0),
            duplicates=data.get("duplicates", 0),
            downloaded=data.get("downloaded", 0),
            message=data.get("message", ""),
        )
        self._send_progress(update)

    def _handle_log(self, message: str, level: str):
        """Forward log message to GUI"""
        self.log_callback(message, level)

    def _send_progress(self, update: ProgressUpdate):
        """Send progress update to callback with throttling"""
        # Always store latest update
        self._pending_progress = update
        
        # Throttle: only send if enough time has passed or if it's a completion/error
        current_time = time.time() * 1000
        is_important = update.status in ("complete", "error", "stopped")
        
        if is_important or (current_time - self._last_progress_time >= self._progress_throttle_ms):
            self._last_progress_time = current_time
            try:
                self.progress_callback(self._pending_progress)
                self._pending_progress = None
            except Exception as ex:
                try:
                    self.log_callback(f"OF Progress callback error: {ex}", "error")
                except Exception:
                    print(f"Progress callback error: {ex}")
    
    def _flush_pending_progress(self):
        """Flush any pending progress update (called on completion/error)"""
        if self._pending_progress is not None:
            try:
                self.progress_callback(self._pending_progress)
                self._pending_progress = None
            except Exception:
                pass
