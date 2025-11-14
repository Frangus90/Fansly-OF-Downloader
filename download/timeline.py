"""Timeline Downloads"""


import random
import traceback

from requests import Response
from time import sleep

from .common import get_unique_media_ids, process_download_accessible_media
from .downloadstate import DownloadState
from .media import download_media_infos
from .types import DownloadType

from config import FanslyConfig
from errors import ApiError
from textio import input_enter_continue, print_debug, print_error, print_info, print_warning


def calculate_backoff_delay(attempt: int, base_delay: int) -> float:
    """Calculate exponential backoff delay with jitter.

    Formula: base_delay * (2^attempt) + random jitter
    Caps at 300 seconds (5 minutes) to prevent excessive waits.

    :param attempt: Current retry attempt number (0-indexed)
    :param base_delay: Base delay in seconds
    :return: Calculated delay in seconds with jitter
    """
    delay = base_delay * (2 ** attempt)
    jitter = random.uniform(0, delay * 0.1)  # Add 10% jitter
    return min(delay + jitter, 300)  # Cap at 5 minutes


def download_timeline(config: FanslyConfig, state: DownloadState) -> None:

    print_info(f"Executing Timeline functionality. Anticipate remarkable outcomes!")
    print()

    # This is important for directory creation later on.
    state.download_type = DownloadType.TIMELINE

    # GUI progress callback helper
    def send_progress(current, total, filename=''):
        if config.gui_mode and config.progress_callback:
            config.progress_callback({
                'type': 'timeline',
                'current': current,
                'total': total,
                'current_file': filename,
                'status': 'running',
                'duplicates': state.duplicate_count,
                'downloaded': state.pic_count + state.vid_count
            })

    # this has to be up here so it doesn't get looped
    timeline_cursor = 0
    attempts = 0
    max_consecutive_empty = 3  # Allow 3 empty responses before assuming end of content
    consecutive_empty_count = 0

    # Careful - "retry" means (1 + retries) runs
    while True and attempts <= config.timeline_retries:
        # Check if stop requested (GUI)
        if config.stop_flag and config.stop_flag.is_set():
            print_info("Timeline download stopped by user")
            return

        starting_duplicates = state.duplicate_count

        if timeline_cursor == 0:
            print_info(f"Inspecting most recent Timeline cursor ... [CID: {state.creator_id}]")

        else:
            print_info(f"Inspecting Timeline cursor: {timeline_cursor} [CID: {state.creator_id}]")

        timeline_response = Response()

        try:
            if state.creator_id is None or timeline_cursor is None:
                raise RuntimeError('Creator name or timeline cursor should not be None')

            timeline_response = config.get_api() \
                .get_timeline(state.creator_id, str(timeline_cursor))

            # Check for rate limiting FIRST (HTTP 429)
            if timeline_response.status_code == 429:
                if attempts < config.timeline_retries:
                    # Try to get Retry-After header, otherwise use configured delay
                    retry_after = int(timeline_response.headers.get('Retry-After', config.timeline_delay_seconds))
                    print_warning(f"Rate limited (HTTP 429)! Waiting {retry_after}s before retry attempt {attempts + 1}/{config.timeline_retries}...")
                    sleep(retry_after)
                    attempts += 1
                    continue  # Retry same cursor
                else:
                    print_warning(f"Rate limit exceeded maximum retries ({config.timeline_retries}) at cursor {timeline_cursor}. Stopping timeline download.")
                    print_info("This may be temporary. Try running again later to continue from where you left off.")
                    break

            # Check for server errors (500-599)
            elif 500 <= timeline_response.status_code < 600:
                if attempts < config.timeline_retries:
                    backoff_delay = calculate_backoff_delay(attempts, config.timeline_delay_seconds)
                    print_warning(
                        f"Server error {timeline_response.status_code}. "
                        f"Retrying in {backoff_delay:.1f}s (attempt {attempts + 1}/{config.timeline_retries})..."
                    )
                    sleep(backoff_delay)
                    attempts += 1
                    continue  # Retry same cursor
                else:
                    print_error(f"Server error {timeline_response.status_code} persisted after {attempts} attempts. Stopping.")
                    break

            # Now check for other HTTP errors
            timeline_response.raise_for_status()

            if timeline_response.status_code == 200:

                timeline = timeline_response.json()['response']

                if config.debug:
                    print_debug(f'Timeline object: {timeline}')

                all_media_ids = get_unique_media_ids(timeline)

                if len(all_media_ids) == 0:
                    # Empty response - could be end of content or temporary issue
                    consecutive_empty_count += 1

                    if consecutive_empty_count >= max_consecutive_empty:
                        print_info(
                            f"Received {consecutive_empty_count} consecutive empty responses. "
                            "Likely reached end of timeline content."
                        )
                        break

                    # Still retry in case it's a temporary API issue
                    if attempts < config.timeline_retries:
                        backoff_delay = calculate_backoff_delay(attempts, config.timeline_delay_seconds)
                        print_info(
                            f"Empty response ({consecutive_empty_count}/{max_consecutive_empty}). "
                            f"Slowing down for {backoff_delay:.1f}s to avoid rate limits..."
                        )
                        sleep(backoff_delay)
                        attempts += 1
                        continue
                    else:
                        print_info("Empty response and no retries left. Stopping timeline download.")
                        break

                else:
                    # Successful fetch with content - reset counters
                    consecutive_empty_count = 0
                    attempts = 0

                media_infos = download_media_infos(config, all_media_ids)

                # Send progress update
                send_progress(
                    state.pic_count + state.vid_count,
                    state.total_timeline_pictures + state.total_timeline_videos,
                    f"Processing timeline batch"
                )

                if not process_download_accessible_media(config, state, media_infos):
                    # Break on deduplication error - already downloaded
                    break

                # Print info on skipped downloads if `show_skipped_downloads` is enabled
                skipped_downloads = state.duplicate_count - starting_duplicates
                if skipped_downloads > 1 and config.show_downloads and not config.show_skipped_downloads:
                    print_info(
                        f"Skipped {skipped_downloads} already downloaded media item{'' if skipped_downloads == 1 else 's'}."
                    )

                print()

                # get next timeline_cursor
                try:
                    # Slow down to avoid the Fansly rate-limit which was introduced in late August 2023
                    # Reduced to 1-2s since we now have proper 429 rate limit detection
                    sleep(random.uniform(1, 2))

                    # Check if posts exist and have content
                    if 'posts' not in timeline or len(timeline['posts']) == 0:
                        print_warning("No posts in timeline response. Likely reached end of timeline content.")
                        break

                    # Get the last post's ID as the next cursor
                    next_cursor = timeline['posts'][-1]['id']

                    # Validate cursor
                    if next_cursor is None or next_cursor == timeline_cursor:
                        print_warning("Next cursor is None or unchanged. Reached end of timeline content.")
                        break

                    timeline_cursor = next_cursor

                except IndexError:
                    # Empty posts array - end is reached
                    print_info("No more posts available. Timeline download complete.")
                    break

                except (KeyError, TypeError) as e:
                    # Malformed response structure
                    print_warning(f"Could not parse next cursor from timeline response: {e}. Likely reached end of timeline.")
                    break

                except Exception:
                    message = \
                        'Please copy & paste this on GitHub > Issues & provide a short explanation (34):'\
                        f'\n{traceback.format_exc()}\n'

                    raise ApiError(message)

        except KeyError:
            print_error("Couldn't find any scrapable media at all!\
                \n This most likely happend because you're not following the creator, your authorisation token is wrong\
                \n or the creator is not providing unlocked content.",
                35
            )
            input_enter_continue(config.interactive)

        except Exception:
            print_error(f"Unexpected error during Timeline download: \n{traceback.format_exc()}", 36)
            input_enter_continue(config.interactive)
