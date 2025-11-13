"""
Centralized logging for Fansly Downloader NG
Writes to fansly_downloader.log (overwrites on each run)
"""

import sys
from pathlib import Path
from datetime import datetime


class FileLogger:
    """Simple file logger that overwrites log on each run"""

    def __init__(self, log_file="fansly_downloader.log"):
        self.log_path = Path.cwd() / log_file

        # Overwrite log file (mode 'w')
        try:
            self.log_file = open(self.log_path, 'w', encoding='utf-8', buffering=1)
            self._write_header()
        except Exception as e:
            # Fallback: if can't write to cwd, try temp directory
            import tempfile
            self.log_path = Path(tempfile.gettempdir()) / log_file
            self.log_file = open(self.log_path, 'w', encoding='utf-8', buffering=1)
            self._write_header()

    def _write_header(self):
        """Write log file header"""
        self.log_file.write("=" * 70 + "\n")
        self.log_file.write(f"FANSLY DOWNLOADER NG - LOG FILE\n")
        self.log_file.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self.log_file.write(f"Log file: {self.log_path}\n")
        self.log_file.write("=" * 70 + "\n\n")
        self.log_file.flush()

    def log(self, message):
        """Write message to log file"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_file.write(f"[{timestamp}] {message}\n")
        self.log_file.flush()

    def close(self):
        """Close log file"""
        try:
            self.log_file.close()
        except:
            pass


# Global logger instance
_logger = None


def get_logger():
    """Get or create the global logger instance"""
    global _logger
    if _logger is None:
        _logger = FileLogger()
    return _logger


def log(message):
    """Convenience function to log a message"""
    get_logger().log(str(message))


def log_separator():
    """Log a visual separator"""
    log("=" * 70)


def close_logger():
    """Close the logger"""
    global _logger
    if _logger:
        _logger.close()
        _logger = None
