"""OnlyFans Messages Scraping

Download messages from OnlyFans creators.
Handles photos, videos, and GIFs from direct messages.
"""

import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
from config.onlyfans_config import OnlyFansConfig
from download.downloadstate import DownloadState
from download.state_manager import DownloadStateManager
from textio import print_info, print_warning, print_error
from .timeline import download_media_item, get_media_extension


def download_messages(config: OnlyFansConfig, state: DownloadState) -> None:
    """
    Download OnlyFans messages

    Args:
        config: OnlyFans configuration
        state: Download state for this creator
    """
    # Track totals for progress reporting
    total_media = 0

    # GUI progress callback helper
    def send_progress(current, total, filename='', status='running'):
        if config.gui_mode and config.progress_callback:
            config.progress_callback({
                'type': 'messages',
                'current': current,
                'total': total,
                'current_file': filename,
                'status': status,
                'duplicates': 0,
                'downloaded': total_media
            })

    try:
        api = config.get_api()

        print_info(f"\nDownloading messages for: {state.creator_name}")

        # Ensure we have creator ID
        if not state.account_id:
            print_error("Creator ID not set. Run get_creator_account_info first.")
            return

        # Set download path: Downloads/CreatorName-of/Messages/
        creator_folder = config.creator_folder_name(state.creator_name)
        messages_folder = config.download_directory / creator_folder / "Messages"
        messages_folder.mkdir(parents=True, exist_ok=True)

        state.base_path = messages_folder

        # Initialize state manager for incremental downloads
        state_file = Path(config.download_directory) / "download_history.json"
        state_manager = DownloadStateManager(state_file)

        # Check for incremental mode
        last_message_id = None
        if config.incremental_mode:
            saved_cursor = state_manager.get_last_cursor(state.creator_name, "messages")
            if saved_cursor:
                last_message_id = saved_cursor
                last_update = state_manager.get_last_update_time(state.creator_name, "messages")
                if last_update:
                    from datetime import datetime
                    last_update_str = datetime.fromtimestamp(last_update).strftime('%Y-%m-%d %H:%M:%S')
                    print_info(f"Incremental mode: Checking for messages newer than {last_update_str}")
                else:
                    print_info(f"Incremental mode: Checking for new messages")
            else:
                print_info(f"Incremental mode enabled but no previous messages download found. Performing full download.")

        # Use creator's user ID as chat ID (confirmed from HAR analysis)
        chat_id = state.account_id

        # Track for state update
        session_new_items = 0
        most_recent_message_id = None
        total_messages = 0

        while True:
            try:
                # Fetch messages
                response = api.get_chat_messages(
                    chat_id=chat_id,
                    limit=25,
                    message_id=last_message_id
                )

                messages = response.get('list', [])

                if not messages:
                    print_info("No more messages to fetch")
                    break

                print_info(f"Processing {len(messages)} messages...")

                # Process each message
                for message in messages:
                    # Check stop flag before processing each message
                    if config.stop_flag and config.stop_flag.is_set():
                        print_warning("Download stopped by user")
                        break

                    total_messages += 1
                    message_id = message.get('id')

                    # Track most recent message ID for incremental mode
                    if most_recent_message_id is None:
                        most_recent_message_id = message_id

                    if config.show_downloads:
                        print_info(f"Message {total_messages}: ID {message_id}")

                    # Parse media from message
                    media_items = parse_message_media(message, state)

                    # Download each media item
                    for media in media_items:
                        # Check stop flag before each download
                        if config.stop_flag and config.stop_flag.is_set():
                            print_warning("Download stopped by user")
                            break

                        media_type = media.get('type', 'unknown')

                        # Skip audio entirely (user preference)
                        if media_type == 'audio':
                            continue

                        # Skip media types user doesn't want
                        if media_type in ('photo', 'gif') and not config.download_photos:
                            continue
                        if media_type == 'video' and not config.download_videos:
                            continue

                        # Send progress update before download
                        send_progress(
                            current=total_media + 1,
                            total=total_media + len(media_items),
                            filename=media.get('filename', '')
                        )

                        if download_media_item(config, state, media):
                            total_media += 1
                            session_new_items += 1

                    # If stopped during media downloads, break from message loop too
                    if config.stop_flag and config.stop_flag.is_set():
                        break

                # Check for more messages
                has_more = response.get('hasMore', False)

                if not has_more:
                    print_info("Reached end of messages")
                    break

                # Update cursor for next page (use last message's ID)
                if messages:
                    last_message_id = messages[-1].get('id')

                # Rate limiting
                if config.rate_limit_delay > 0:
                    time.sleep(config.rate_limit_delay)

                # Check for stop flag (GUI support)
                if config.stop_flag and config.stop_flag.is_set():
                    print_warning("Download stopped by user")
                    break

            except requests.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limited
                    print_warning("Rate limited. Waiting 60 seconds...")
                    time.sleep(60)
                    continue
                else:
                    raise

        print_info(f"\n✓ Messages download complete!")
        print_info(f"  Messages processed: {total_messages}")
        print_info(f"  Media downloaded: {total_media}")

        # Send completion progress
        send_progress(
            current=total_media,
            total=total_media,
            filename='',
            status='complete'
        )

        # Update state manager with last message ID for incremental mode
        if most_recent_message_id and session_new_items > 0:
            state_manager.update_cursor(
                creator_username=state.creator_name,
                creator_id=state.account_id,
                download_type="messages",
                cursor=most_recent_message_id,
                new_items=session_new_items
            )

        state.pic_count = total_media

    except Exception as e:
        print_error(f"Messages download failed: {e}")
        raise


def parse_message_media(message: Dict, state: DownloadState) -> List[Dict]:
    """
    Parse media items from OnlyFans message

    Args:
        message: Message data from API
        state: Download state

    Returns:
        List of media item dicts with url, filename, type
    """
    media_items = []
    message_id = message.get('id', 'unknown')

    # Messages have 'media' array
    media_array = message.get('media', [])

    for idx, media in enumerate(media_array):
        media_id = media.get('id', idx)
        media_type = media.get('type', 'unknown')  # 'photo', 'video', 'gif', 'audio'

        # Get media URL - check multiple possible locations
        # Videos often use 'source' field, photos use 'files.full.url'
        url = None

        # First check 'source' field (common for videos)
        if 'source' in media:
            source = media['source']
            url = source.get('source') or source.get('url')

        # If no source, check 'files' field (common for photos)
        if not url and 'files' in media:
            if 'full' in media['files']:
                url = media['files']['full'].get('url')
            else:
                # Fallback: try other quality levels
                files = media['files']
                if isinstance(files, dict):
                    for quality in ['source', 'full', 'preview']:
                        if quality in files:
                            file_obj = files[quality]
                            if isinstance(file_obj, dict):
                                url = file_obj.get('url')
                            if url:
                                break

        if not url:
            # This could be paywall-locked content or media with no accessible URL
            print_warning(f"Could not find media URL for message {message_id}, media {media_id} (type: {media_type}) - may be paywall-locked")
            continue

        # Determine file extension
        extension = get_media_extension(media_type, url)

        # Create filename: msg_MessageID_MediaID.ext
        filename = f"msg_{message_id}_{media_id}.{extension}"

        media_items.append({
            'id': media_id,
            'type': media_type,
            'url': url,
            'filename': filename,
            'message_id': message_id,
        })

    return media_items
