"""
Redirect stdout/stderr for windowed GUI applications

In windowed mode (PyInstaller --windowed), sys.stdout and sys.stderr are None.
This causes crashes when libraries like textio/loguru try to write output.

This module provides fake streams that redirect all output to our log file.
"""

import sys
from gui.logger import get_logger


class LoggerStream:
    """A stream object that writes to our logger instead of console"""

    def __init__(self):
        self.logger = None

    def write(self, message):
        """Write message to logger"""
        if message and message.strip():
            # Lazy-load logger to avoid circular import
            if self.logger is None:
                self.logger = get_logger()
            self.logger.log(message.rstrip())

    def flush(self):
        """Flush - no-op for our logger (already line-buffered)"""
        pass

    def isatty(self):
        """Return False - not a TTY"""
        return False


def setup_stream_redirection():
    """
    Setup stdout/stderr redirection for windowed GUI apps.

    MUST be called BEFORE any imports that might use print() or logging.
    """
    if sys.stdout is None:
        sys.stdout = LoggerStream()

    if sys.stderr is None:
        sys.stderr = LoggerStream()
