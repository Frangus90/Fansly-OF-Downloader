"""Self-Update Utility Functions"""


import dateutil.parser
import os
import platform
import re
# import requests
# import subprocess
# import sys

# import errors

from pathlib import Path

# Use the public API instead of internal _vendor API
# This avoids deprecation warnings and import errors
try:
    from packaging.version import parse as parse_version
except ImportError:
    # Fallback to pkg_resources if packaging is not installed
    try:
        from pkg_resources import parse_version
    except ImportError:
        # Last resort: use a simple string comparison
        def parse_version(version_string):
            """Simple fallback version parser."""
            return tuple(map(int, version_string.split('.')))

# from shutil import unpack_archive

from config import FanslyConfig
from textio import clear_terminal, print_error, print_info, print_update, print_warning
from utils.web import get_release_info_from_github


def delete_deprecated_files() -> None:
    """Deletes deprecated files after an update."""
    old_files = [
        "old_updater",
        "updater",
        "Automatic Configurator",
        "Fansly Scraper",
        "deprecated_version",
        "old_config"
    ]

    directory = Path.cwd()

    for root, _, files in os.walk(directory):
        for file in files:

            file_object = Path(file)

            if file_object.suffix.lower() != '.py' and file_object.stem in old_files:

                file_path = Path(root) / file

                if file_path.exists():
                    file_path.unlink()


def display_release_notes(program_version: str, release_notes: str) -> None:
    """Displays the release notes of a Fansly Downloader NG version.
    
    :param str program_version: The Fansly Downloader NG version.
    :param str release_notes: The corresponding release notes.
    """
    print_update(f"Successfully updated to version {program_version}!\n\n► Release Notes:\n{release_notes}")
    print()
    input('Press <ENTER> to start Fansly Downloader NG ...')

    clear_terminal()


def parse_release_notes(release_info: dict) -> str | None:
    """Parse the release notes from the release info dictionary
    obtained from GitHub.

    :param dict release_info: Program release information from GitHub.

    :return: The release notes or None if there was empty content or
        a parsing error.
    :rtype: str | None
    """
    release_body = release_info.get("body")

    if not release_body:
        return None

    body_match = re.search(
        r"```(.*)```",
        release_body,
        re.DOTALL | re.MULTILINE
    )

    if not body_match:
        return None

    release_notes = body_match[1]

    if not release_notes:
        return None

    return release_notes


def perform_update(program_version: str, release_info: dict) -> bool:
    """Performs a self-update of Fansly Downloader.

    :param str program_version: The current program version.
    :param dict releas_info: Release information from GitHub.

    :return: True if successful or False otherwise.
    :rtype: bool
    """
    print_warning(f"A new version of Fansly Downloader NG has been found on GitHub - update recommended.")
    
    if not release_info:
        return False

    keys = ['release_version', 'created_at', 'download_count']

    for key in keys:
        if not key in release_info.keys():
            return False

    print_info(
        f"Latest Build:"
        f"\n{16*' '} Version: {release_info['release_version']}"
        f"\n{16*' '} Published: {release_info['created_at']}"
        f"\n{16*' '} Download count: {release_info['download_count']}"
        f"\n\n{16*' '} Your version {program_version} is outdated.")

    print_warning(
        f"To update Fansly Downloader NG, please download the latest version from the GitHub repository.")

    return False


def post_update_steps(program_version: str, release_info: dict | None) -> None:
    """Performs necessary steps after  a self-update.
    
    :param str program_version: The program version updated to.
    :param dict release_info: The version's release info from GitHub.
    """
    if release_info is not None:
        release_notes = parse_release_notes(release_info)

        if release_notes is not None:
            display_release_notes(program_version, release_notes)


def check_for_update(config: FanslyConfig) -> bool:
    """Checks for an updated program version.

    :param FanslyConfig config: The program configuration including the
        current version number.

    :return: False if anything went wrong (network errors, ...)
        or True otherwise.
    :rtype: bool
    """
    release_info = get_release_info_from_github(config.program_version)

    if release_info is None:
        return False
    
    else:
        # we don't want to ship drafts or pre-releases
        if release_info["draft"] or release_info["prerelease"]:
            return False

        # remove the string "v" from the version tag
        tag_parts = release_info["tag_name"].split('v')
        if len(tag_parts) < 2:
            print_warning(f"Invalid version tag format: {release_info['tag_name']}")
            return False
        new_version = tag_parts[1]
        
        # we do only want current platform compatible updates
        new_release = None
        current_platform = 'macOS' if platform.system() == 'Darwin' else platform.system()

        for new_release in release_info['assets']:
            if current_platform in new_release['name']:
                d = dateutil.parser.isoparse(new_release['created_at']).replace(tzinfo=None)

                parsed_date = f"{d.strftime('%d')} {d.strftime('%B')[:3]} {d.strftime('%Y')}"

                new_release = {
                    'release_name': new_release['name'],
                    'release_version': new_version,
                    'created_at': parsed_date,
                    'download_count': new_release['download_count'],
                    'download_url': new_release['browser_download_url']
                }

        if new_release is None:
            return False
    
        empty_values = [
            value is None for key, value in new_release.items()
            if key != 'download_count'
        ]

        if any(empty_values):
            return False

        # just return if our current version is still sufficient
        if parse_version(config.program_version) >= parse_version(new_version):
            return True

        else:
            return perform_update(config.program_version, new_release)
