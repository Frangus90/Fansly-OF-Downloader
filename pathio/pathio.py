"""Work Directory Manipulation"""


import os
import sys
import time

from pathlib import Path
from tkinter import Tk, filedialog

from config import FanslyConfig
from download.downloadstate import DownloadState
from download.types import DownloadType
from textio import print_info, print_error


# if the users custom provided filepath is invalid; a tkinter dialog will open during runtime, asking to adjust download path
def ask_correct_dir() -> Path:
    root = Tk()
    root.withdraw()

    while True:
        directory_name = filedialog.askdirectory()

        # Handle case when user cancels dialog (returns None or empty string)
        if not directory_name:
            print_error(f"You did not choose a folder. Please try again!", 5)
            continue

        if Path(directory_name).is_dir():
            print_info(f"Folder path chosen: {directory_name}")
            return Path(directory_name)

        print_error(f"You did not choose a valid folder. Please try again!", 5)


def set_create_directory_for_download(config: FanslyConfig, state: DownloadState) -> Path:
    """Sets and creates the appropriate download directory according to
    download type for storing media from a distinct creator.

    :param FanslyConfig config: The current download session's
        configuration object. download_directory will be taken as base path.

    :param DownloadState state: The current download session's state.
        This function will modify base_path (based on creator) and
        save_path (full path based on download type) accordingly.

    :return Path: The (created) path current media downloads.
    """
    if config.download_directory is None:
        message = 'Internal error during directory creation - download directory not set.'
        raise RuntimeError(message)

    if state.creator_name is None:
        message = 'Internal error during directory creation - creator name not set.'
        raise RuntimeError(message)

    else:
        import os
        import platform

        suffix = ''

        if config.use_folder_suffix:
            suffix = '_fansly'

        # Sanitize creator name for filesystem safety
        creator_name = state.creator_name
        
        # Windows reserved names and characters
        if platform.system() == 'Windows':
            # Windows reserved names (case-insensitive)
            reserved_names = {'CON', 'PRN', 'AUX', 'NUL',
                            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
                            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
            
            # Check if creator name matches reserved name
            if creator_name.upper() in reserved_names:
                creator_name = f"_{creator_name}"
            
            # Remove invalid characters for Windows
            invalid_chars = '<>:"|?*'
            for char in invalid_chars:
                creator_name = creator_name.replace(char, '_')
        
        # Limit path length to prevent filesystem issues
        # Windows MAX_PATH is 260, but we need room for subdirectories and filenames
        max_name_length = 200
        if len(creator_name) > max_name_length:
            creator_name = creator_name[:max_name_length]
        
        # Remove leading/trailing dots and spaces (Windows doesn't allow these)
        creator_name = creator_name.strip('. ')
        if not creator_name:  # If name becomes empty after sanitization
            creator_name = "unknown_creator"

        user_base_path = config.download_directory / f'{creator_name}{suffix}'

        user_base_path.mkdir(parents=True, exist_ok=True)

        # Default directory if download types don't match in check below
        download_directory = user_base_path

        if state.download_type == DownloadType.COLLECTIONS:
            download_directory = config.download_directory / 'Collections'

        elif state.download_type == DownloadType.MESSAGES and config.separate_messages:
            download_directory = user_base_path / 'Messages'

        elif state.download_type == DownloadType.TIMELINE and config.separate_timeline:
            download_directory = user_base_path / 'Timeline'

        elif state.download_type == DownloadType.SINGLE and config.separate_timeline:
            download_directory = user_base_path / 'Timeline'

        # Save state
        state.base_path = user_base_path
        state.download_path = download_directory

        # Create the directory
        download_directory.mkdir(parents=True, exist_ok=True)

        return download_directory


def delete_temporary_pyinstaller_files():
    """Delete old files from the PyInstaller temporary folder.
    
    Files older than an hour will be deleted.
    """
    try:
        base_path = sys._MEIPASS

    except Exception as e:
        # Not running as PyInstaller bundle, skip cleanup
        return

    temp_dir = os.path.abspath(os.path.join(base_path, '..'))
    current_time = time.time()

    for folder in os.listdir(temp_dir):
        try:
            item = os.path.join(temp_dir, folder)

            if folder.startswith('_MEI') \
                and os.path.isdir(item) \
                    and (current_time - os.path.getctime(item)) > 3600:

                for root, dirs, files in os.walk(item, topdown=False):

                    for file in files:
                        os.remove(os.path.join(root, file))

                    for dir in dirs:
                        os.rmdir(os.path.join(root, dir))

                os.rmdir(item)

        except Exception as e:
            # Log but don't fail on individual file/folder deletion errors
            # This is cleanup code, so we silently continue
            pass
