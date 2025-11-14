"""Fansly Download Functionality"""


import random

from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Column
from time import sleep

from .downloadstate import DownloadState
from .m3u8 import download_m3u8
from .types import DownloadType

from config import FanslyConfig
from errors import ApiError, DownloadError, DuplicateCountError, M3U8Error, MediaError
from fileio.dedupe import dedupe_media_file
from media import MediaItem
from pathio import set_create_directory_for_download
from textio import print_info, print_warning, print_error
from utils.common import batch_list


def download_media_infos(
            config: FanslyConfig,
            media_ids: list[str]
        ) -> list[dict]:

    media_infos: list[dict] = []

    for ids in batch_list(media_ids, config.BATCH_SIZE):
        media_ids_str = ','.join(ids)

        # Retry logic for rate limiting and server errors
        max_retries = 3
        attempts = 0
        success = False

        while attempts < max_retries and not success:
            media_info_response = config.get_api() \
                .get_account_media(media_ids_str)

            # Check for rate limiting FIRST (HTTP 429)
            if media_info_response.status_code == 429:
                attempts += 1
                if attempts < max_retries:
                    # Try to get Retry-After header, otherwise use configured delay
                    retry_after = int(media_info_response.headers.get('Retry-After', config.timeline_delay_seconds))
                    print_warning(
                        f"Rate limited (HTTP 429) on media info fetch! "
                        f"Waiting {retry_after}s before retry attempt {attempts}/{max_retries}..."
                    )
                    sleep(retry_after)
                    continue  # Retry same batch
                else:
                    print_error(f"Rate limit exceeded maximum retries ({max_retries}) for media info batch.")
                    raise DownloadError(
                        f"Could not retrieve media info for {media_ids_str} due to rate limiting "
                        f"after {max_retries} attempts"
                    )

            # Check for server errors (500-599)
            elif 500 <= media_info_response.status_code < 600:
                attempts += 1
                if attempts < max_retries:
                    backoff_delay = config.timeline_delay_seconds * (2 ** attempts)
                    backoff_delay = min(backoff_delay, 300)  # Cap at 5 minutes
                    print_warning(
                        f"Server error {media_info_response.status_code} on media info fetch. "
                        f"Retrying in {backoff_delay}s (attempt {attempts}/{max_retries})..."
                    )
                    sleep(backoff_delay)
                    continue  # Retry same batch
                else:
                    print_error(f"Server error exceeded maximum retries ({max_retries}) for media info batch.")
                    raise DownloadError(
                        f"Could not retrieve media info for {media_ids_str} due to server error "
                        f"{media_info_response.status_code} after {max_retries} attempts"
                    )

            # Success case
            elif media_info_response.status_code == 200:
                media_info = media_info_response.json()

                if not media_info['success']:
                    raise ApiError(
                        f"Could not retrieve media info for {media_ids_str} due to an "
                        f"API error - unsuccessful "
                        f"| content: \n{media_info}"
                    )

                for info in media_info['response']:
                    media_infos.append(info)

                success = True  # Exit retry loop

            # Other client errors (4xx)
            else:
                raise DownloadError(
                    f"Could not retrieve media info for {media_ids_str} due to an "
                    f"error --> status_code: {media_info_response.status_code} "
                    f"| content: \n{media_info_response.content.decode('utf-8')}"
                )

        # Delay between API calls to avoid rate limiting
        sleep(1.0)

    return media_infos


def download_media(config: FanslyConfig, state: DownloadState, accessible_media: list[MediaItem]):
    """Downloads all media items to their respective target folders."""
    if state.download_type == DownloadType.NOTSET:
        raise RuntimeError('Internal error during media download - download type not set on state.')

    # loop through the accessible_media and download the media files
    for index, media_item in enumerate(accessible_media):
        # Check if stop requested (GUI)
        if config.stop_flag and config.stop_flag.is_set():
            print_info("Media download stopped by user")
            return

        # Send progress update for current file (GUI)
        if config.gui_mode and config.progress_callback:
            config.progress_callback({
                'type': 'media',
                'current': index + 1,
                'total': len(accessible_media),
                'current_file': media_item.get_file_name() if media_item else '',
                'status': 'running',
                'duplicates': state.duplicate_count,
                'downloaded': state.pic_count + state.vid_count
            })
        # Verify that the duplicate count has not drastically spiked and
        # and if it did verify that the spiked amount is significantly
        # high to cancel scraping
        if config.use_duplicate_threshold \
                and state.duplicate_count > config.DUPLICATE_THRESHOLD \
                and config.DUPLICATE_THRESHOLD >= 50:
            raise DuplicateCountError(state.duplicate_count)

        # general filename construction & if content is a preview; add that into its filename
        filename = media_item.get_file_name()

        # "None" safeguards
        if media_item.mimetype is None:
            raise MediaError('MIME type for media item not defined. Aborting.')

        if media_item.download_url is None:
            raise MediaError('Download URL for media item not defined. Aborting.')

        # deduplication - part 1: decide if this media is even worth further processing; by media id
        if any([media_item.media_id in state.recent_photo_media_ids, media_item.media_id in state.recent_video_media_ids]):
            if config.show_downloads and config.show_skipped_downloads:
                print_info(f"Deduplication [Media ID]: {media_item.mimetype.split('/')[-2]} '{filename}' → skipped")
            state.duplicate_count += 1
            continue

        else:
            if 'image' in media_item.mimetype:
                state.recent_photo_media_ids.add(media_item.media_id)

            elif 'video' in media_item.mimetype:
                state.recent_video_media_ids.add(media_item.media_id)

            elif 'audio' in media_item.mimetype:
                state.recent_audio_media_ids.add(media_item.media_id)

        base_directory = set_create_directory_for_download(config, state)

        # for collections downloads we just put everything into the same folder
        if state.download_type == DownloadType.COLLECTIONS:
            file_save_path = base_directory / filename
            # compatibility for final "Download finished...!" print
            file_save_dir = file_save_path

        # for every other type of download; we do want to determine the sub-directory to save the media file based on the mimetype
        else:
            if 'image' in media_item.mimetype:
                file_save_dir = base_directory / "Pictures"

            elif 'video' in media_item.mimetype:
                file_save_dir = base_directory / "Videos"

            elif 'audio' in media_item.mimetype:
                file_save_dir = base_directory / "Audio"

            else:
                # if the mimetype is neither image nor video, skip the download
                print_warning(f"Unknown mimetype; skipping download for mimetype: '{media_item.mimetype}' | media_id: {media_item.media_id}")
                continue
            
            # decides to separate previews or not
            if media_item.is_preview and config.separate_previews:
                file_save_path = file_save_dir / 'Previews' / filename
                file_save_dir = file_save_dir / 'Previews'

            else:
                file_save_path = file_save_dir / filename

            if not file_save_dir.exists():
                file_save_dir.mkdir(parents=True)
        
        # if show_downloads is True / downloads should be shown
        if config.show_downloads:
            print_info(f"Downloading {media_item.mimetype.split('/')[-2]} '{filename}'")

        try:
            if media_item.file_extension == 'm3u8':
                # handle the download of a m3u8 file with retry logic
                m3u8_retry_count = 0
                m3u8_success = False

                while m3u8_retry_count < 3 and not m3u8_success:
                    try:
                        file_save_path = download_m3u8(
                            config,
                            m3u8_url=media_item.download_url,
                            save_path=file_save_path
                        )
                        m3u8_success = True
                    except M3U8Error as ex:
                        m3u8_retry_count += 1
                        if m3u8_retry_count < 3:
                            print_warning(f'M3U8 download failed (attempt {m3u8_retry_count}/3): {ex}. Retrying in 2s...')
                            sleep(2)
                        else:
                            # Re-raise to be caught by outer exception handler
                            raise

            else:
                # handle the download of a normal media file
                with config.get_api().get_with_ngsw(
                            url=media_item.download_url,
                            stream=True,
                            add_fansly_headers=False,
                        ) as response:

                    if response.status_code == 200:
                        text_column = TextColumn(f"", table_column=Column(ratio=1))
                        bar_column = BarColumn(bar_width=60, table_column=Column(ratio=5))

                        file_size = int(response.headers.get('content-length', 0))

                        # if file size is above 20 MB display loading bar
                        disable_loading_bar = False if file_size >= 20_000_000 else True

                        progress = Progress(
                            text_column,
                            bar_column,
                            expand=True,
                            transient=True,
                            disable=disable_loading_bar
                        )

                        task_id = progress.add_task('', total=file_size)

                        progress.start()

                        CHUNK_SIZE = 1_048_576

                        with open(file_save_path, 'wb') as output_file:
                            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                                if chunk:
                                    output_file.write(chunk)
                                    progress.advance(task_id, len(chunk))

                        progress.refresh()
                        progress.stop()

                    else:
                        raise DownloadError(
                            f"Download failed on filename {filename} due to an "
                            f"error --> status_code: {response.status_code} "
                            f"| content: \n{response.content.decode('utf-8')} [13]"
                        )

            is_dupe = dedupe_media_file(config, state, media_item.mimetype, file_save_path)

            # Delay between downloads to avoid rate limiting
            sleep(0.5)

            # Is it a duplicate?
            if is_dupe:
                continue

            # We only count them if the file was actually kept
            state.pic_count += 1 if 'image' in media_item.mimetype else 0
            state.vid_count += 1 if 'video' in media_item.mimetype else 0

        except M3U8Error as ex:
            print_warning(f'Skipping invalid item: {ex}')

        # Delay between API calls to avoid rate limiting
        sleep(1.0)
