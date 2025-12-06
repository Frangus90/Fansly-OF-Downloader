#!/usr/bin/env python3

"""OnlyFans Downloader

Separate main script for OnlyFans scraping.
Parallel to fansly_downloader_ng.py but for OnlyFans.
"""

__version__ = '1.0.0'
__date__ = '2025-01-13'
__maintainer__ = 'prof79'
__copyright__ = f'Copyright (C) 2024-2025 by {__maintainer__}'

import traceback

from config.onlyfans_config import (
    OnlyFansConfig,
    load_onlyfans_config,
    validate_onlyfans_config
)
from download_of import download_timeline, get_creator_account_info
from download.downloadstate import DownloadState
from errors import (
    EXIT_SUCCESS,
    EXIT_ABORT,
    API_ERROR,
    CONFIG_ERROR,
    DOWNLOAD_ERROR,
    SOME_USERS_FAILED,
    UNEXPECTED_ERROR,
    ApiError,
    DownloadError,
    ConfigError,
)
from textio import (
    input_enter_close,
    input_enter_continue,
    print_error,
    print_info,
    print_warning,
    set_window_title,
)
from utils.timer import Timer


def print_logo() -> None:
    """Prints the OnlyFans Downloader logo."""
    print(
        """
  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
  ┃                                                                 ┃
  ┃   ╔═══╗╔═╗ ╔╗╔╗     ╔═══╗                                     ┃
  ┃   ║╔═╗║║║╚╗║║║║     ║╔══╝                                     ┃
  ┃   ║║ ║║║╔╗╚╝║║║     ║╚══╗╔══╗╔═╗╔═╗╔══╗                      ┃
  ┃   ║║ ║║║║╚╗║║║║ ╔╗  ║╔══╝║╔╗║║╔╗╝║║║══╣                      ┃
  ┃   ║╚═╝║║║ ║║║║╚═╝║  ║║   ║╔╗║║║║ ║╚╣══║                      ┃
  ┃   ╚═══╝╚╝ ╚═╝╚═══╝  ╚╝   ╚╝╚╝╚╝╚═╩═╩══╝                      ┃
  ┃                                                                 ┃
  ┃             Downloader & Scraper                                ┃
  ┃                                                                 ┃
  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
        """
    )
    print(f"{(70 - len(__version__) - 1)//2*' '}v{__version__}\n")


def main(config: OnlyFansConfig) -> int:
    """
    Main OnlyFans downloader logic

    Args:
        config: OnlyFans configuration

    Returns:
        Exit code
    """
    exit_code = EXIT_SUCCESS

    timer = Timer('Total')
    timer.start()

    # Update window title
    set_window_title(f"OnlyFans Downloader v{config.program_version}")

    # Print logo
    try:
        print_logo()
    except UnicodeEncodeError:
        # Fallback for Windows consoles that don't support UTF-8
        print(f"\nOnlyFans Downloader v{config.program_version}\n")

    # Load configuration
    try:
        load_onlyfans_config(config)
    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        return CONFIG_ERROR

    # Validate configuration
    if not validate_onlyfans_config(config):
        return CONFIG_ERROR

    print()
    print_info(f"Session: {config.sess[:20]}..." if config.sess else "Session: Not set")
    print_info(f"Auth ID: {config.auth_id}")
    print_info(f"User Agent: {config.user_agent[:50]}..." if config.user_agent else "User Agent: Not set")

    # Test authentication
    try:
        print()
        print_info("Testing OnlyFans authentication...")
        api = config.get_api()
        if api.test_auth():
            print_info("✓ Authentication successful!")
        else:
            print_error("✗ Authentication failed")
            return CONFIG_ERROR
    except Exception as e:
        print_error(f"✗ Authentication failed: {e}")
        return CONFIG_ERROR

    # Process each creator
    for creator_name in sorted(config.user_names):
        print()
        print_info("=" * 70)
        print_info(f"Processing creator: {creator_name}")
        print_info("=" * 70)

        with Timer(creator_name):
            try:
                state = DownloadState(creator_name=creator_name)

                # Get creator account info
                get_creator_account_info(config, state)

                print()
                print_info(f"Download mode: {config.download_mode}")
                print()

                # Download based on mode
                if config.download_mode == "Timeline":
                    download_timeline(config, state)
                elif config.download_mode == "Normal":
                    # Normal mode: Timeline (+ Messages/Collections in future)
                    download_timeline(config, state)
                else:
                    print_warning(f"Download mode '{config.download_mode}' not yet supported")
                    print_info("Currently supported: Timeline, Normal")

                # Show stats
                print()
                print_info(f"✓ Completed: {creator_name}")
                print_info(f"  Files downloaded: {state.files_downloaded}")

            except ApiError as e:
                print_error(f"API error processing {creator_name}: {e}")
                if config.interactive:
                    input_enter_continue(True)
                exit_code = SOME_USERS_FAILED

            except DownloadError as e:
                print_error(f"Download error processing {creator_name}: {e}")
                if config.interactive:
                    input_enter_continue(True)
                exit_code = SOME_USERS_FAILED

            except ConfigError as e:
                print_error(f"Configuration error processing {creator_name}: {e}")
                if config.interactive:
                    input_enter_continue(True)
                exit_code = SOME_USERS_FAILED

            except Exception as e:
                print_error(f"Unexpected error processing {creator_name} (type: {type(e).__name__}): {e}\n{traceback.format_exc()}")
                if config.interactive:
                    input_enter_continue(True)
                exit_code = SOME_USERS_FAILED

    timer.stop()

    # Show timing
    print()
    print_info("=" * 70)
    print_info(f"Total time: {timer.elapsed_str()}")
    print_info("=" * 70)

    return exit_code


if __name__ == '__main__':
    config = OnlyFansConfig(program_version=__version__)
    exit_code = EXIT_SUCCESS

    try:
        exit_code = main(config)

    except KeyboardInterrupt:
        print()
        print_warning('Program aborted.')
        exit_code = EXIT_ABORT

    except ApiError as e:
        print()
        print_error(str(e))
        exit_code = API_ERROR

    except ConfigError as e:
        print()
        print_error(str(e))
        exit_code = CONFIG_ERROR

    except DownloadError as e:
        print()
        print_error(str(e))
        exit_code = DOWNLOAD_ERROR

    except Exception as e:
        print()
        print_error(f'An unexpected error occurred: {e}\n{traceback.format_exc()}')
        exit_code = UNEXPECTED_ERROR

    input_enter_close(config.prompt_on_exit)
    exit(exit_code)
