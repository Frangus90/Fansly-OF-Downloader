"""OnlyFans Configuration

Separate configuration system for OnlyFans scraping.
Completely independent from Fansly configuration.
"""

from configparser import ConfigParser
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Callable, Any
import threading

if TYPE_CHECKING:
    from api.onlyfans_api import OnlyFansApi


@dataclass
class OnlyFansConfig:
    """OnlyFans configuration - completely independent from Fansly"""

    # Program version
    program_version: str

    # Configuration file
    config_path: Path = Path("onlyfans_config.ini")

    # OnlyFans credentials
    sess: Optional[str] = None
    auth_id: Optional[str] = None
    auth_uid: Optional[str] = None  # Only if 2FA enabled
    user_agent: Optional[str] = None
    x_bc: Optional[str] = None

    # Download settings
    user_names: Optional[set[str]] = None
    download_directory: Optional[Path] = None
    download_mode: str = "Timeline"
    show_downloads: bool = True
    show_skipped_downloads: bool = True
    open_folder_when_finished: bool = True
    incremental_mode: bool = False
    interactive: bool = True
    prompt_on_exit: bool = True

    # Rate limiting
    rate_limit_delay: int = 2
    max_retries: int = 3

    # Post limit for new creators (None = unlimited)
    # Only applies when creator has no download history and not in incremental mode
    max_posts_per_creator: Optional[int] = None

    # Media type filters (which types to download)
    download_photos: bool = True
    download_videos: bool = True

    # Cache
    last_run_timestamp: Optional[str] = None

    # GUI support
    gui_mode: bool = False
    progress_callback: Optional[Callable] = None
    log_callback: Optional[Callable] = None
    stop_flag: Optional[threading.Event] = None

    # Config parser
    _parser: ConfigParser = field(default_factory=lambda: ConfigParser(interpolation=None))
    _api: Optional['OnlyFansApi'] = None

    def get_api(self) -> 'OnlyFansApi':
        """Get OnlyFans API instance"""
        if self._api is None:
            from api.onlyfans_api import OnlyFansApi

            if not self.has_credentials():
                raise RuntimeError("OnlyFans credentials not configured")

            self._api = OnlyFansApi(
                sess=self.sess,
                auth_id=self.auth_id,
                auth_uid=self.auth_uid,
                user_agent=self.user_agent,
                x_bc=self.x_bc
            )

        return self._api

    def has_credentials(self) -> bool:
        """Check if OF credentials are configured"""
        return all([
            self.sess,
            self.auth_id,
            self.user_agent,
            self.x_bc
        ])

    def creator_folder_name(self, creator_name: str) -> str:
        """Get folder name for OF creator: CreatorName-of"""
        return f"{creator_name}-of"

    def user_names_str(self) -> Optional[str]:
        """Returns comma-separated creator names"""
        if self.user_names:
            return ', '.join(sorted(self.user_names))
        return None

    def _save_config(self) -> None:
        """Save configuration to file"""
        save_onlyfans_config(self)


def load_onlyfans_config(config: OnlyFansConfig) -> None:
    """Load OnlyFans config from onlyfans_config.ini"""

    if not config.config_path.exists():
        create_default_onlyfans_config(config)
        return

    config._parser.read(config.config_path, encoding='utf-8')

    # Load credentials
    if config._parser.has_section('MyAccount'):
        config.sess = config._parser.get('MyAccount', 'sess', fallback=None)
        config.auth_id = config._parser.get('MyAccount', 'auth_id', fallback=None)
        config.auth_uid = config._parser.get('MyAccount', 'auth_uid', fallback=None)
        config.user_agent = config._parser.get('MyAccount', 'user_agent', fallback=None)
        config.x_bc = config._parser.get('MyAccount', 'x_bc', fallback=None)

    # Load targeted creators
    if config._parser.has_section('TargetedCreators'):
        usernames_str = config._parser.get('TargetedCreators', 'usernames', fallback='')
        if usernames_str.strip():
            config.user_names = set(name.strip() for name in usernames_str.split(',') if name.strip())

    # Load options
    if config._parser.has_section('Options'):
        download_dir_str = config._parser.get('Options', 'download_directory', fallback=None)
        if download_dir_str:
            config.download_directory = Path(download_dir_str)

        config.download_mode = config._parser.get('Options', 'download_mode', fallback='Timeline')
        config.show_downloads = config._parser.getboolean('Options', 'show_downloads', fallback=True)
        config.show_skipped_downloads = config._parser.getboolean('Options', 'show_skipped_downloads', fallback=True)
        config.open_folder_when_finished = config._parser.getboolean('Options', 'open_folder_when_finished', fallback=True)
        config.incremental_mode = config._parser.getboolean('Options', 'incremental_mode', fallback=False)
        config.interactive = config._parser.getboolean('Options', 'interactive', fallback=True)
        config.prompt_on_exit = config._parser.getboolean('Options', 'prompt_on_exit', fallback=True)

        # Optional int - post limit
        max_posts_str = config._parser.get('Options', 'max_posts_per_creator', fallback=None)
        if max_posts_str and max_posts_str.strip():
            try:
                config.max_posts_per_creator = int(max_posts_str)
            except ValueError:
                config.max_posts_per_creator = None
        else:
            config.max_posts_per_creator = None

        # Media type filters
        config.download_photos = config._parser.getboolean('Options', 'download_photos', fallback=True)
        config.download_videos = config._parser.getboolean('Options', 'download_videos', fallback=True)

    # Load cache
    if config._parser.has_section('Cache'):
        config.last_run_timestamp = config._parser.get('Cache', 'last_run_timestamp', fallback=None)

    # Load logic settings
    if config._parser.has_section('Logic'):
        config.rate_limit_delay = config._parser.getint('Logic', 'rate_limit_delay', fallback=2)
        config.max_retries = config._parser.getint('Logic', 'max_retries', fallback=3)


def save_onlyfans_config(config: OnlyFansConfig) -> None:
    """Save OnlyFans config to onlyfans_config.ini"""

    # Update parser with current values
    if not config._parser.has_section('TargetedCreators'):
        config._parser.add_section('TargetedCreators')

    if config.user_names:
        config._parser.set('TargetedCreators', 'usernames', ', '.join(sorted(config.user_names)))
    else:
        config._parser.set('TargetedCreators', 'usernames', '')

    # Save credentials
    if not config._parser.has_section('MyAccount'):
        config._parser.add_section('MyAccount')

    config._parser.set('MyAccount', 'sess', config.sess or '')
    config._parser.set('MyAccount', 'auth_id', config.auth_id or '')
    config._parser.set('MyAccount', 'auth_uid', config.auth_uid or '')
    config._parser.set('MyAccount', 'user_agent', config.user_agent or '')
    config._parser.set('MyAccount', 'x_bc', config.x_bc or '')

    # Save options
    if not config._parser.has_section('Options'):
        config._parser.add_section('Options')

    if config.download_directory:
        config._parser.set('Options', 'download_directory', str(config.download_directory))

    config._parser.set('Options', 'download_mode', config.download_mode)
    config._parser.set('Options', 'show_downloads', str(config.show_downloads))
    config._parser.set('Options', 'show_skipped_downloads', str(config.show_skipped_downloads))
    config._parser.set('Options', 'open_folder_when_finished', str(config.open_folder_when_finished))
    config._parser.set('Options', 'incremental_mode', str(config.incremental_mode))
    config._parser.set('Options', 'interactive', str(config.interactive))
    config._parser.set('Options', 'prompt_on_exit', str(config.prompt_on_exit))

    # Post limit (optional int)
    if config.max_posts_per_creator is not None:
        config._parser.set('Options', 'max_posts_per_creator', str(config.max_posts_per_creator))
    else:
        config._parser.set('Options', 'max_posts_per_creator', '')

    # Media type filters
    config._parser.set('Options', 'download_photos', str(config.download_photos))
    config._parser.set('Options', 'download_videos', str(config.download_videos))

    # Save cache
    if not config._parser.has_section('Cache'):
        config._parser.add_section('Cache')

    config._parser.set('Cache', 'last_run_timestamp', config.last_run_timestamp or '')

    # Save logic
    if not config._parser.has_section('Logic'):
        config._parser.add_section('Logic')

    config._parser.set('Logic', 'rate_limit_delay', str(config.rate_limit_delay))
    config._parser.set('Logic', 'max_retries', str(config.max_retries))

    # Write to file
    with open(config.config_path, 'w', encoding='utf-8') as f:
        config._parser.write(f)


def create_default_onlyfans_config(config: OnlyFansConfig) -> None:
    """Create default OnlyFans config file"""

    # Set defaults
    if config.download_directory is None:
        config.download_directory = Path.cwd() / "Downloads"

    config.download_mode = "Timeline"
    config.show_downloads = True
    config.show_skipped_downloads = True
    config.open_folder_when_finished = True
    config.incremental_mode = False
    config.interactive = True
    config.prompt_on_exit = True
    config.rate_limit_delay = 2
    config.max_retries = 3

    # Save to file
    save_onlyfans_config(config)


def validate_onlyfans_config(config: OnlyFansConfig) -> bool:
    """Validate OnlyFans configuration"""

    errors = []

    # Check credentials
    if not config.sess:
        errors.append("Session cookie (sess) is required")

    if not config.auth_id:
        errors.append("Auth ID is required")

    if not config.user_agent:
        errors.append("User Agent is required")

    if not config.x_bc:
        errors.append("X-BC token is required")

    # Check download directory
    if not config.download_directory:
        errors.append("Download directory is required")
    elif not config.download_directory.exists():
        try:
            config.download_directory.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create download directory: {e}")

    # Check creators
    if not config.user_names or len(config.user_names) == 0:
        errors.append("At least one creator username is required")

    if errors:
        from textio import print_error
        print_error("OnlyFans configuration validation failed:")
        for error in errors:
            print_error(f"  - {error}")
        return False

    return True
