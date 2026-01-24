"""
Download runner - isolated from GUI imports to avoid circular dependencies
This module is imported ONLY in the worker thread
"""


def run_download(config, stop_flag, progress_callback, log_callback):
    """
    Run the download process

    This function is called in a worker thread and imports download
    modules locally to avoid circular imports with the GUI.
    """
    # Import all download modules here, in the worker thread
    from download.account import get_creator_account_info
    from download.timeline import download_timeline
    from download.messages import download_messages
    from download.single import download_single_post
    from download.collections import download_collections
    from download.core import DownloadState
    from fileio.dedupe import dedupe_init
    from config.modes import DownloadMode

    # Inject callbacks into config
    config.gui_mode = True
    config.progress_callback = progress_callback
    config.log_callback = log_callback
    config.stop_flag = stop_flag

    # Enable GUI log routing for textio messages
    from textio import set_gui_config
    set_gui_config(config)

    # Create download state for the creator
    # Use current_download_creator if set (GUI mode), otherwise first from user_names
    if config.current_download_creator:
        creator_name = config.current_download_creator
    elif config.user_names:
        creator_name = list(config.user_names)[0]
    else:
        raise RuntimeError("No creator username specified")

    state = DownloadState(creator_name=creator_name)

    # Initialize deduplication
    if config.download_mode != DownloadMode.SINGLE:
        dedupe_init(config, state)

    # Get creator account info
    get_creator_account_info(config, state)

    # Download based on mode
    if config.download_mode == DownloadMode.SINGLE:
        download_single_post(config, state)
    elif config.download_mode == DownloadMode.COLLECTION:
        download_collections(config, state)
    elif config.download_mode == DownloadMode.MESSAGES:
        download_messages(config, state)
    elif config.download_mode == DownloadMode.TIMELINE:
        download_timeline(config, state)
    else:  # DownloadMode.NORMAL
        download_messages(config, state)
        download_timeline(config, state)

    return True


def run_onlyfans_download(config, stop_flag, progress_callback, log_callback):
    """
    Run OnlyFans download process

    This function is called in a worker thread for OF downloads.
    """
    # Import OF download modules
    from download_of import download_timeline, get_creator_account_info, download_single_post_of, download_messages
    from download.downloadstate import DownloadState
    from textio import print_info

    # Inject callbacks into config
    config.gui_mode = True
    config.progress_callback = progress_callback
    config.log_callback = log_callback
    config.stop_flag = stop_flag

    # Enable GUI log routing
    from textio import set_gui_config
    set_gui_config(config)

    # Debug: Show download mode
    print_info(f"Download mode: {config.download_mode}")

    # Handle Single Post mode (no creator loop needed)
    if config.download_mode == "Single":
        print_info("Starting single post download...")
        state = DownloadState()
        download_single_post_of(config, state)
        return True

    # Process each creator for Timeline mode
    for creator_name in config.user_names:
        if stop_flag.is_set():
            break

        state = DownloadState(creator_name=creator_name)

        # Get creator info
        get_creator_account_info(config, state)

        # Download based on mode
        if config.download_mode in ("Timeline", "Normal"):
            print_info("Starting timeline download...")
            download_timeline(config, state)
        if config.download_mode in ("Messages", "Normal"):
            print_info("Starting messages download...")
            download_messages(config, state)

    return True
