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
BUILD_TIMESTAMP = "v1.7.2_2026-02-18_1543"


def main():
    """Launch the GUI application"""
    try:
        # === CRITICAL: Setup stdout/stderr redirection FIRST ===
        # In windowed mode (--windowed), sys.stdout and sys.stderr are None
        # This causes crashes when libraries try to print/log
        from gui.stream_redirector import setup_stream_redirection
        setup_stream_redirection()

        # Minimal startup logging
        from gui.logger import log
        log(f"Starting Fansly Downloader NG {BUILD_TIMESTAMP}")

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
        except Exception as dialog_error:
            # If we can't show the dialog, at least log to stderr
            import sys
            print(f"CRITICAL: Could not display error dialog: {dialog_error}", file=sys.stderr)
            print(f"Original error: {ex}", file=sys.stderr)

        sys.exit(1)
    finally:
        from gui.logger import close_logger
        close_logger()


if __name__ == "__main__":
    # Required for Windows multiprocessing support
    from multiprocessing import freeze_support
    freeze_support()
    main()
