"""OnlyFans Single Post Downloading

Download a single post from OnlyFans by post ID or URL.
"""

from typing import Optional
from pathlib import Path

from config.onlyfans_config import OnlyFansConfig
from download.downloadstate import DownloadState
from download_of.timeline import parse_post_media, download_media_item
from textio import print_info, print_warning, print_error
from utils.url_parser import is_valid_onlyfans_post_id, get_post_id_from_of_request


def download_single_post_of(config: OnlyFansConfig, state: DownloadState) -> None:
    """
    Download a single OnlyFans post by ID or URL.

    Args:
        config: OnlyFans configuration
        state: Download state for tracking progress
    """
    total_media = 0

    # GUI progress callback helper
    def send_progress(current: int, total: int, filename: str = '', status: str = 'running'):
        if config.gui_mode and config.progress_callback:
            config.progress_callback({
                'type': 'single',
                'current': current,
                'total': total,
                'current_file': filename,
                'status': status,
                'downloaded': total_media
            })

    print_info("You have launched in Single Post download mode (OnlyFans).")

    # Get post ID from config or interactive input
    if config.post_id is not None:
        print_info(f"Downloading post {config.post_id} as specified ...")
        post_id = config.post_id

    elif not config.interactive:
        raise RuntimeError(
            'Single Post downloading requires a post ID in non-interactive mode. '
            'Set config.post_id before calling this function.'
        )

    else:
        post_id = prompt_for_post_id()

    try:
        api = config.get_api()

        # Fetch post from API
        print_info(f"Fetching post {post_id} ...")
        post = api.get_post(post_id)

        if not post:
            print_error(f"Failed to fetch post {post_id} - empty response")
            send_progress(0, 0, '', 'error')
            return

        # Extract creator info from post
        creator_username = extract_creator_from_post(post)
        creator_id = post.get('author', {}).get('id') or post.get('fromUser', {}).get('id')

        if creator_username:
            state.creator_name = creator_username
            state.account_id = str(creator_id) if creator_id else None
            print_info(f"Post by: {creator_username}")
        else:
            # Try to use configured creator name as fallback
            if not state.creator_name:
                state.creator_name = "unknown_creator"
            print_warning(f"Could not determine creator from post, using: {state.creator_name}")

        # Set up download path: Downloads/{creator}-of/Timeline/
        # Uses Timeline folder so dupe check works with regular timeline downloads
        creator_folder = config.creator_folder_name(state.creator_name)
        timeline_folder = config.download_directory / creator_folder / "Timeline"
        timeline_folder.mkdir(parents=True, exist_ok=True)

        state.base_path = timeline_folder

        # Parse media from post
        media_items = parse_post_media(post, state)

        if not media_items:
            print_warning(f"No accessible media found in post {post_id}")
            send_progress(0, 0, '', 'complete')
            return

        print_info(f"Found {len(media_items)} media item(s)")

        # Download each media item
        downloaded = 0
        for idx, media in enumerate(media_items):
            # Check stop flag
            if config.stop_flag and config.stop_flag.is_set():
                print_warning("Download stopped by user")
                break

            media_type = media.get('type', 'unknown')

            # Skip audio
            if media_type == 'audio':
                continue

            # Apply media type filters
            if media_type in ('photo', 'gif') and not config.download_photos:
                continue
            if media_type == 'video' and not config.download_videos:
                continue

            # Send progress update
            send_progress(
                current=idx + 1,
                total=len(media_items),
                filename=media.get('filename', '')
            )

            if download_media_item(config, state, media):
                downloaded += 1
                total_media += 1

        print_info(f"\n Single post download complete!")
        print_info(f"  Downloaded: {downloaded} of {len(media_items)} items")

        # Send completion progress
        send_progress(
            current=len(media_items),
            total=len(media_items),
            filename='',
            status='complete'
        )

        # Update state counters
        state.pic_count = downloaded

    except Exception as e:
        print_error(f"Single post download failed: {e}")
        send_progress(0, 0, '', 'error')
        raise


def prompt_for_post_id() -> str:
    """
    Interactive prompt for post ID/URL input.

    Returns:
        Validated post ID
    """
    print_info(
        "Please enter the link or ID of the post you would like to download."
        f"\n{17*' '}The ID is in the URL: https://onlyfans.com/{'{post_id}'}/{'{username}'}"
    )
    print()

    while True:
        requested_post = input(f"\n{17*' '} Post Link or ID: ")
        post_id = get_post_id_from_of_request(requested_post)

        if is_valid_onlyfans_post_id(post_id):
            return post_id

        print_error(
            f"The input '{requested_post}' is not a valid OnlyFans post link or ID."
            f"\n{22*' '}Example URL: 'https://onlyfans.com/123456789/creatorname'"
            f"\n{22*' '}Or just the ID: '123456789'",
            17
        )


def extract_creator_from_post(post: dict) -> Optional[str]:
    """
    Extract creator username from post API response.

    OnlyFans post responses can have creator info in different locations
    depending on the endpoint.

    Args:
        post: Post data from API

    Returns:
        Creator username or None
    """
    # Try 'author' field (common in post responses)
    author = post.get('author')
    if author:
        username = author.get('username')
        if username:
            return username

    # Try 'fromUser' field
    from_user = post.get('fromUser')
    if from_user:
        username = from_user.get('username')
        if username:
            return username

    # Try 'user' field
    user = post.get('user')
    if user:
        username = user.get('username')
        if username:
            return username

    return None
