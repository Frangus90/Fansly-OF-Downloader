"""Console Output"""


import os
import platform
import subprocess
import sys
import threading

from loguru import logger
from pathlib import Path
from time import sleep


LOG_FILE_NAME: str = 'fansly_downloader_ng.log'

# GUI config reference for log routing
_gui_config = None

# Thread lock for dynamic level registration
_level_lock = threading.Lock()
_registered_levels: set[str] = set()

# --- One-time loguru setup (module load) ---

# Remove loguru's default stderr handler
logger.remove()

# Minimum level across all custom levels is 1 (Info), so set handler level to 1
# to ensure all custom levels are captured.
logger.add(
    sys.stdout,
    format="<level>{level}</level> | <white>{time:HH:mm}</white> <level>|</level><light-white>| {message}</light-white>",
    level=1,
)
logger.add(
    Path.cwd() / LOG_FILE_NAME,
    encoding='utf-8',
    format="[{level} ] [{time:YYYY-MM-DD} | {time:HH:mm}]: {message}",
    level=1,
    rotation='1MB',
    retention=5,
)

# Register all known custom levels once
_CUSTOM_LEVELS = [
    (' Info', 1, '<light-blue>'),
    (' ERROR', 2, '<red>'),
    (' WARNING', 3, '<yellow>'),
    (' lnfo', 4, '<light-red>'),
    (' Config', 5, '<light-magenta>'),
    (' Updater', 6, '<light-green>'),
    (' DEBUG', 7, '<light-red>'),
]

for _name, _no, _color in _CUSTOM_LEVELS:
    try:
        logger.level(_name, no=_no, color=_color)
        _registered_levels.add(_name)
    except TypeError:
        pass


def _ensure_level(log_type: str, level: int, color: str) -> None:
    """Register a dynamic log level if not already registered (thread-safe)."""
    if log_type not in _registered_levels:
        with _level_lock:
            if log_type not in _registered_levels:
                try:
                    logger.level(log_type, no=level, color=color)
                except TypeError:
                    pass
                _registered_levels.add(log_type)


def set_gui_config(config):
    """Set the config object to enable GUI log routing.

    When set, all log messages will also be sent to the GUI's
    log_callback if gui_mode is True.
    """
    global _gui_config
    _gui_config = config


def output(level: int, log_type: str, color: str, message: str) -> None:
    _ensure_level(log_type, level, color)
    logger.log(log_type, message)

    # Route to GUI callback if available
    if _gui_config and _gui_config.gui_mode and _gui_config.log_callback:
        log_type_upper = log_type.strip().upper()
        if 'ERROR' in log_type_upper:
            gui_level = 'error'
        elif 'WARNING' in log_type_upper:
            gui_level = 'warning'
        else:
            gui_level = 'info'

        try:
            _gui_config.log_callback(message, gui_level)
        except Exception as ex:
            print(f"GUI log callback error: {ex}", file=sys.stderr)


def print_config(message: str) -> None:
    output(5, ' Config', '<light-magenta>', message)


def print_debug(message: str) -> None:
    output(7,' DEBUG', '<light-red>', message)


def print_error(message: str, number: int=-1) -> None:
    if number >= 0:
        output(2, f' [{number}]ERROR', '<red>', message)
    else:
        output(2, ' ERROR', '<red>', message)


def print_info(message: str) -> None:
    output(1, ' Info', '<light-blue>', message)


def print_info_highlight(message: str) -> None:
    output(4, ' lnfo', '<light-red>', message)


def print_update(message: str) -> None:
    output(6,' Updater', '<light-green>', message)


def print_warning(message: str) -> None:
    output(3, ' WARNING', '<yellow>', message)


def input_enter_close(interactive: bool) -> None:
    """Asks user for <ENTER> to close and exits the program.
    In non-interactive mode sleeps instead, then exits.
    """
    if interactive:
        input('\nPress <ENTER> to close ...')

    else:
        print('\nExiting in 3 seconds ...')
        sleep(3)

    sys.exit()


def input_enter_continue(interactive: bool) -> None:
    """Asks user for <ENTER> to continue.
    In non-interactive mode sleeps instead.
    """
    if interactive:
        input('\nPress <ENTER> to attempt to continue ...')
    else:
        print('\nContinuing in 3 seconds ...')
        sleep(3)


def clear_terminal() -> None:
    system = platform.system()

    if system == 'Windows':
        os.system('cls')

    else:
        os.system('clear')


def set_window_title(title) -> None:
    current_platform = platform.system()

    if current_platform == 'Windows':
        subprocess.call('title {}'.format(title), shell=True)

    elif current_platform == 'Linux' or current_platform == 'Darwin':
        subprocess.call(['printf', r'\33]0;{}\a'.format(title)])
