#!/usr/bin/env python3
"""
Fansly Downloader NG - GUI Version
Graphical interface for downloading Fansly content
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Add ocr_libs to path if it exists (EasyOCR installed post-build)
_ocr_libs = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "ocr_libs")
if os.path.isdir(_ocr_libs) and _ocr_libs not in sys.path:
    sys.path.insert(0, _ocr_libs)

# If frozen and easyocr still not importable, check system Python's site-packages
if getattr(sys, "frozen", False):
    try:
        import easyocr as _test_easyocr  # noqa: F401
    except ImportError:
        try:
            import shutil
            import subprocess
            _python = shutil.which("python3") or shutil.which("python")
            if _python:
                _result = subprocess.run(
                    [_python, "-c", "import easyocr; print(easyocr.__path__[0])"],
                    capture_output=True, text=True, timeout=10,
                )
                if _result.returncode == 0:
                    _easyocr_path = _result.stdout.strip()
                    _site_packages = os.path.dirname(_easyocr_path)
                    if _site_packages not in sys.path:
                        sys.path.insert(0, _site_packages)
        except Exception:
            pass

from gui.app import create_app

# BUILD VERIFICATION - Updated each time we rebuild
# This helps confirm we're running the latest build
BUILD_TIMESTAMP = "v1.8.0_2026-02-20_1903"


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
