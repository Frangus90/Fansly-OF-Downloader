"""OnlyFans Timeline Scraping

Download timeline posts from OnlyFans creators.
Handles photos, videos, and GIFs.
"""

import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
from config.onlyfans_config import OnlyFansConfig
from download.downloadstate import DownloadState
from textio import print_info, print_warning, print_error


def download_timeline(config: OnlyFansConfig, state: DownloadState) -> None:
    """
    Download OnlyFans timeline posts

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
                'type': 'timeline',
                'current': current,
                'total': total,
                'current_file': filename,
                'status': status,
                'duplicates': 0,
                'downloaded': total_media
            })

    try:
        api = config.get_api()

        print_info(f"\nDownloading timeline for: {state.creator_name}")

        # Ensure we have creator ID
        if not state.account_id:
            print_error("Creator ID not set. Run get_creator_account_info first.")
            return

        # Set download path: Downloads/CreatorName-of/Timeline/
        creator_folder = config.creator_folder_name(state.creator_name)
        timeline_folder = config.download_directory / creator_folder / "Timeline"
        timeline_folder.mkdir(parents=True, exist_ok=True)

        state.base_path = timeline_folder

        # Check if creator has download history (folder exists and has files)
        has_history = timeline_folder.exists() and any(timeline_folder.iterdir())

        # Check if post limit should be applied
        # Only apply to new creators when NOT in incremental mode
        apply_post_limit = (
            config.max_posts_per_creator is not None
            and not config.incremental_mode
            and not has_history
        )

        if apply_post_limit:
            print_info(f"Post limit enabled: Will download up to {config.max_posts_per_creator} newest posts for this new creator")

        before_cursor = None
        total_posts = 0

        while True:
            try:
                # Fetch posts
                response = api.get_timeline(
                    user_id=state.account_id,
                    limit=100,
                    before_publish_time=before_cursor
                )

                posts = response.get('list', [])

                if not posts:
                    print_info("No more posts to fetch")
                    break

                print_info(f"Processing {len(posts)} posts...")

                # Process each post
                for post in posts:
                    # Check stop flag before processing each post
                    if config.stop_flag and config.stop_flag.is_set():
                        print_warning("Download stopped by user")
                        break

                    total_posts += 1
                    post_id = post.get('id')

                    if config.show_downloads:
                        print_info(f"Post {total_posts}: ID {post_id}")

                    # Parse media from post
                    media_items = parse_post_media(post, state)

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

                    # If stopped during media downloads, break from post loop too
                    if config.stop_flag and config.stop_flag.is_set():
                        break

                # Check if post limit reached
                if apply_post_limit and total_posts >= config.max_posts_per_creator:
                    print_info(f"Reached post limit ({config.max_posts_per_creator} posts). Stopping timeline download.")
                    print_info(f"Downloaded content from {total_posts} posts for this new creator.")
                    break

                # Check for more posts
                has_more = response.get('hasMore', False)

                if not has_more:
                    print_info("Reached end of timeline")
                    break

                # Update cursor for next page
                # Use last post's publish time
                if posts:
                    last_post = posts[-1]
                    before_cursor = last_post.get('postedAtPrecise') or last_post.get('createdAt')

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

        print_info(f"\n✓ Timeline download complete!")
        print_info(f"  Posts processed: {total_posts}")
        print_info(f"  Media downloaded: {total_media}")

        # Send completion progress
        send_progress(
            current=total_media,
            total=total_media,
            filename='',
            status='complete'
        )

        state.files_downloaded = total_media

    except Exception as e:
        print_error(f"Timeline download failed: {e}")
        raise


def parse_post_media(post: Dict, state: DownloadState) -> List[Dict]:
    """
    Parse media items from OnlyFans post

    Args:
        post: Post data from API
        state: Download state

    Returns:
        List of media item dicts with url, filename, type
    """
    media_items = []
    post_id = post.get('id', 'unknown')

    # OF posts have 'media' array
    media_array = post.get('media', [])

    for idx, media in enumerate(media_array):
        media_id = media.get('id', idx)
        media_type = media.get('type', 'unknown')  # 'photo', 'video', 'gif', 'audio'

        # Get media URL
        # Check different possible URL locations
        media_url = None

        if 'source' in media:
            source = media['source']
            media_url = source.get('source') or source.get('url')

        if not media_url and 'files' in media:
            # Try files array
            files = media['files']
            if isinstance(files, dict):
                # Get highest quality
                for quality in ['source', 'full', 'preview']:
                    if quality in files:
                        media_url = files[quality].get('url')
                        if media_url:
                            break

        if not media_url:
            print_warning(f"Could not find media URL for {media_id}")
            continue

        # Determine file extension
        extension = get_media_extension(media_type, media_url)

        # Create filename: PostID_MediaID.ext
        filename = f"{post_id}_{media_id}.{extension}"

        media_items.append({
            'id': media_id,
            'type': media_type,
            'url': media_url,
            'filename': filename,
            'post_id': post_id,
        })

    return media_items


def download_media_item(config: OnlyFansConfig, state: DownloadState,
                        media: Dict) -> bool:
    """
    Download single media item

    Args:
        config: OnlyFans configuration
        state: Download state
        media: Media item dict

    Returns:
        True if downloaded successfully, False if skipped
    """
    file_path = state.base_path / media['filename']

    # Skip if exists
    if file_path.exists():
        if config.show_skipped_downloads:
            print_info(f"  ⊘ Skipping (exists): {media['filename']}")
        return False

    try:
        if config.show_downloads:
            print_info(f"  ↓ Downloading: {media['filename']}")

        # Download file
        response = requests.get(media['url'], stream=True, timeout=60)
        response.raise_for_status()

        # Write to file
        stopped = False
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                # Check stop flag during download
                if config.stop_flag and config.stop_flag.is_set():
                    print_warning(f"  ⊘ Download stopped: {media['filename']}")
                    stopped = True
                    break  # Exit loop, let file close

                if chunk:
                    f.write(chunk)

        # Clean up partial file if stopped (file is now closed)
        if stopped:
            if file_path.exists():
                file_path.unlink()
            return False

        return True

    except Exception as e:
        print_error(f"  ✗ Failed to download {media['filename']}: {e}")
        # Remove partial file
        if file_path.exists():
            file_path.unlink()
        return False


def get_media_extension(media_type: str, url: str) -> str:
    """
    Determine file extension from media type and URL

    Args:
        media_type: Type from API ('photo', 'video', 'gif', 'audio')
        url: Media URL

    Returns:
        File extension without dot
    """
    # Type-based mapping
    type_map = {
        'photo': 'jpg',
        'video': 'mp4',
        'gif': 'gif',
        'audio': 'mp3',
    }

    # Try type first
    if media_type in type_map:
        return type_map[media_type]

    # Try to extract from URL
    if '.' in url:
        parts = url.split('.')
        # Get last part before query string
        ext = parts[-1].split('?')[0].lower()
        # Validate it looks like an extension
        if len(ext) <= 4 and ext.isalnum():
            return ext

    # Default fallback
    return 'bin'
