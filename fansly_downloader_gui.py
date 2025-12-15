#!/usr/bin/env python3
"""
Fansly Downloader NG - GUI Version
Graphical interface for downloading Fansly content
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from gui.app import create_app

# BUILD VERIFICATION - Updated each time we rebuild
# This helps confirm we're running the latest build
BUILD_TIMESTAMP = "v1.3.0_2025-12-15_1821"


def main():
    """Launch the GUI application"""
    try:
        # === CRITICAL: Setup stdout/stderr redirection FIRST ===
        # In windowed mode (--windowed), sys.stdout and sys.stderr are None
        # This causes crashes when libraries try to print/log
        from gui.stream_redirector import setup_stream_redirection
        setup_stream_redirection()

        # === DIAGNOSTIC STARTUP LOGGING ===
        from pathlib import Path
        from gui.logger import log, log_separator

        log_separator()
        log("FANSLY DOWNLOADER NG - STARTUP DIAGNOSTICS")
        log_separator()
        log("stdout/stderr redirection: ACTIVE")
        log(f"Build Version: {BUILD_TIMESTAMP}")
        log(f"Working Directory: {Path.cwd()}")
        log(f"Script Directory: {Path(__file__).parent.absolute()}")
        log(f"Executable: {sys.executable}")

        # Check if running from PyInstaller bundle
        if getattr(sys, 'frozen', False):
            log(f"Running as: FROZEN EXECUTABLE (PyInstaller)")
            log(f"Bundle Dir: {sys._MEIPASS}")
        else:
            log(f"Running as: PYTHON SCRIPT")

        # Check config file location
        config_path = Path.cwd() / "config.ini"
        log(f"")
        log(f"Config file path: {config_path}")
        log(f"Config exists: {config_path.exists()}")

        if config_path.exists():
            log(f"Config size: {config_path.stat().st_size} bytes")
            log(f"Config modified: {config_path.stat().st_mtime}")

        # List files in current directory
        log(f"")
        log(f"Files in working directory:")
        try:
            items = sorted(Path.cwd().iterdir())[:10]  # Show first 10
            for item in items:
                log(f"  - {item.name}")
        except Exception as e:
            log(f"  Error listing files: {e}")

        log_separator()
        # === END DIAGNOSTICS ===

        app = create_app()
        app.run()
    except Exception as ex:
        from gui.logger import log, close_logger
        log(f"FATAL ERROR: {ex}")
        import traceback
        log(traceback.format_exc())

        # Show error to user
        try:
            import tkinter.messagebox as mb
            mb.showerror(
                "Application Error",
                f"An error occurred. Please check fansly_downloader.log for details.\n\n{ex}"
            )
        except Exception:
            pass

        sys.exit(1)
    finally:
        from gui.logger import close_logger
        close_logger()


if __name__ == "__main__":
    # Required for Windows multiprocessing support
    from multiprocessing import freeze_support
    freeze_support()
    main()
