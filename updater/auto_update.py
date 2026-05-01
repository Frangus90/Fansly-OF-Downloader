"""Auto-Update Core Logic

Handles checking for updates, downloading new versions, and applying updates.
"""

import os
import platform
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import dateutil.parser
import requests

try:
    from packaging.version import parse as parse_version
except ImportError:
    try:
        from pkg_resources import parse_version
    except ImportError:
        def parse_version(version_string):
            return tuple(map(int, version_string.split('.')))

from utils.web import get_release_info_from_github


APP_NAME = "FanslyOFDownloaderNG"
PROTECTED_UPDATE_FILES = (
    "config.ini",
    "onlyfans_config.ini",
    "gui_state.json",
    "onlyfans_gui_state.json",
    "log_window_settings.json",
)


@dataclass
class UpdateInfo:
    """Information about an available update"""
    version: str
    download_url: str
    release_name: str
    published_date: str
    download_count: int
    release_notes: Optional[str] = None


def select_update_asset(
    assets: list[dict],
    current_platform: str,
    version: str,
) -> Optional[dict]:
    """Select the release asset suitable for the current app/platform."""
    if current_platform == "Windows":
        preferred_name = f"{APP_NAME}-Windows-x64-v{version}.zip".lower()
        legacy_name = f"{APP_NAME}.zip".lower()

        for asset in assets:
            if asset.get("name", "").lower() == preferred_name:
                return asset

        for asset in assets:
            name = asset.get("name", "").lower()
            if (
                name.endswith(".zip")
                and APP_NAME.lower() in name
                and "windows" in name
                and "source" not in name
            ):
                return asset

        for asset in assets:
            if asset.get("name", "").lower() == legacy_name:
                return asset

    for asset in assets:
        name = asset.get("name", "")
        if current_platform in name and "source" not in name.lower():
            return asset

    return None


def check_for_update(
    current_version: str,
    skipped_version: Optional[str] = None,
    force: bool = False
) -> Optional[UpdateInfo]:
    """
    Check GitHub for available updates.

    Args:
        current_version: The current program version
        skipped_version: Version the user chose to skip (won't notify)
        force: If True, ignore skipped_version and always check

    Returns:
        UpdateInfo if an update is available, None otherwise
    """
    release_info = get_release_info_from_github(current_version)

    if release_info is None:
        return None

    # Don't ship drafts or pre-releases
    if release_info.get("draft") or release_info.get("prerelease"):
        return None

    # Parse version from tag (format: v1.2.3)
    tag_name = release_info.get("tag_name", "")
    if not tag_name.startswith("v"):
        return None

    new_version = tag_name[1:]  # Remove 'v' prefix

    # Check if this version should be skipped
    if not force and skipped_version and new_version == skipped_version:
        return None

    # Compare versions - only update if newer
    try:
        if parse_version(current_version) >= parse_version(new_version):
            return None
    except Exception:
        return None

    # Find appropriate asset for current platform
    current_platform = 'macOS' if platform.system() == 'Darwin' else platform.system()

    asset = select_update_asset(release_info.get('assets', []), current_platform, new_version)
    if asset is None:
        return None

    download_url = asset.get('browser_download_url')
    release_name = asset.get('name')
    download_count = asset.get('download_count', 0)
    published_date = None

    created_at = asset.get('created_at')
    if created_at:
        try:
            d = dateutil.parser.isoparse(created_at).replace(tzinfo=None)
            published_date = d.strftime('%d %b %Y')
        except Exception:
            published_date = created_at

    if not download_url:
        return None

    # Parse release notes
    release_notes = None
    body = release_info.get("body", "")
    if body:
        release_notes = body

    return UpdateInfo(
        version=new_version,
        download_url=download_url,
        release_name=release_name or f"v{new_version}",
        published_date=published_date or "Unknown",
        download_count=download_count,
        release_notes=release_notes
    )


def check_for_update_async(
    current_version: str,
    skipped_version: Optional[str],
    callback: Callable[[Optional[UpdateInfo]], None],
    force: bool = False
) -> threading.Thread:
    """
    Check for updates in a background thread.

    Args:
        current_version: The current program version
        skipped_version: Version the user chose to skip
        callback: Function to call with result (runs on background thread!)
        force: If True, ignore skipped_version

    Returns:
        The background thread (already started)
    """
    def worker():
        try:
            result = check_for_update(current_version, skipped_version, force)
            callback(result)
        except Exception:
            callback(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def download_update(
    download_url: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Optional[Path]:
    """
    Download update file to temp directory.

    Args:
        download_url: URL to download from
        progress_callback: Called with (downloaded_bytes, total_bytes)

    Returns:
        Path to downloaded file, or None on failure
    """
    try:
        # Start download with streaming
        response = requests.get(download_url, stream=True, timeout=60)
        response.raise_for_status()

        # Get total size
        total_size = int(response.headers.get('content-length', 0))

        # Create temp file
        temp_dir = Path(tempfile.gettempdir())
        filename = download_url.split('/')[-1]
        temp_path = temp_dir / f"update_{filename}"

        # Download with progress
        downloaded = 0
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)

        return temp_path

    except Exception:
        return None


def download_update_async(
    download_url: str,
    progress_callback: Optional[Callable[[int, int], None]],
    complete_callback: Callable[[Optional[Path]], None]
) -> threading.Thread:
    """
    Download update in background thread.

    Args:
        download_url: URL to download from
        progress_callback: Called with (downloaded_bytes, total_bytes)
        complete_callback: Called with download path (or None on failure)

    Returns:
        The background thread (already started)
    """
    def worker():
        try:
            result = download_update(download_url, progress_callback)
            complete_callback(result)
        except Exception:
            complete_callback(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread


def create_windows_update_script(current_exe: Path, downloaded_path: Path) -> Path:
    """
    Create a batch script that will:
    1. Wait for current process to exit
    2. Extract zip / replace exe with new version
    3. Restart the application

    Args:
        current_exe: Path to the current executable
        downloaded_path: Path to the downloaded update file (.zip or .exe)

    Returns:
        Path to the created batch script
    """
    script_path = Path(tempfile.gettempdir()) / "fansly_update.bat"
    pid = os.getpid()
    app_dir = current_exe.parent
    protected_files = " ".join(f'"{filename}"' for filename in PROTECTED_UPDATE_FILES)

    if downloaded_path.suffix.lower() == ".zip":
        # Zip update: extract over the app directory
        script = f'''@echo off
title Fansly Downloader NG - Updating...
echo Waiting for application to close...

:wait_loop
tasklist /fi "pid eq {pid}" 2>nul | find "{pid}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo Applying update...
timeout /t 1 /nobreak >nul

REM Extract zip to temp location
set TEMP_EXTRACT=%TEMP%\\fansly_update_extract
if exist "%TEMP_EXTRACT%" rmdir /s /q "%TEMP_EXTRACT%"
mkdir "%TEMP_EXTRACT%"

REM Preserve user config and GUI state files before copying bundled files
set PRESERVE_DIR=%TEMP%\\fansly_update_preserve
if exist "%PRESERVE_DIR%" rmdir /s /q "%PRESERVE_DIR%"
mkdir "%PRESERVE_DIR%"
for %%F in ({protected_files}) do (
    if exist "{app_dir}\\%%~F" copy /y "{app_dir}\\%%~F" "%PRESERVE_DIR%\\%%~F" >nul
)

powershell -Command "Expand-Archive -Path '{downloaded_path}' -DestinationPath '%TEMP_EXTRACT%' -Force"

REM Find the inner folder (zip contains AppName/...)
for /d %%D in ("%TEMP_EXTRACT%\\*") do set INNER_DIR=%%D

REM Copy extracted files over the app directory
xcopy /s /y /q "%INNER_DIR%\\*" "{app_dir}\\"

REM Restore user config and GUI state files after bundled files are copied
for %%F in ({protected_files}) do (
    if exist "%PRESERVE_DIR%\\%%~F" copy /y "%PRESERVE_DIR%\\%%~F" "{app_dir}\\%%~F" >nul
)

REM Clean up
rmdir /s /q "%TEMP_EXTRACT%"
if exist "%PRESERVE_DIR%" rmdir /s /q "%PRESERVE_DIR%"
del /f /q "{downloaded_path}"

echo Update complete! Starting application...
timeout /t 1 /nobreak >nul

REM Restart application
start "" "{current_exe}"

REM Delete this script
del /f /q "%~f0"
'''
    else:
        # Single exe update (legacy fallback)
        script = f'''@echo off
title Fansly Downloader NG - Updating...
echo Waiting for application to close...

:wait_loop
tasklist /fi "pid eq {pid}" 2>nul | find "{pid}" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo Applying update...
timeout /t 1 /nobreak >nul

REM Backup old version
if exist "{current_exe}.bak" del /f /q "{current_exe}.bak"
move /y "{current_exe}" "{current_exe}.bak"

REM Copy new version
copy /y "{downloaded_path}" "{current_exe}"

REM Clean up
del /f /q "{downloaded_path}"

echo Update complete! Starting application...
timeout /t 1 /nobreak >nul

REM Restart application
start "" "{current_exe}"

REM Delete this script
del /f /q "%~f0"
'''

    with open(script_path, 'w') as f:
        f.write(script)

    return script_path


def apply_update(downloaded_path: Path) -> bool:
    """
    Apply a downloaded update by launching the update script.

    This will:
    1. Create the update batch script
    2. Launch it in a new process
    3. The calling code should then exit the application

    Args:
        downloaded_path: Path to the downloaded update file

    Returns:
        True if update script was launched, False on error
    """
    try:
        # Get current executable path
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            current_exe = Path(sys.executable)
        else:
            # Running as script - can't self-update
            return False

        # Only support Windows for now
        if platform.system() != 'Windows':
            return False

        # Create update script
        script_path = create_windows_update_script(current_exe, downloaded_path)

        # Launch script in new process (hidden window)
        subprocess.Popen(
            ['cmd', '/c', str(script_path)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
            close_fds=True
        )

        return True

    except Exception:
        return False


def is_running_as_exe() -> bool:
    """Check if running as a compiled executable (vs Python script)"""
    return getattr(sys, 'frozen', False)
