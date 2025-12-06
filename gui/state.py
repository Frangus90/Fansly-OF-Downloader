"""
Application state management
"""

import json
import traceback
from pathlib import Path
from config import FanslyConfig, load_config
from config.onlyfans_config import OnlyFansConfig, load_onlyfans_config
from gui.logger import log


class AppState:
    """Centralized application state for GUI"""

    def __init__(self):
        self.config = FanslyConfig(program_version="0.9.9")
        self.is_downloading = False
        self.current_creator = None

        # GUI-specific creator management (preserves full list during downloads)
        self.all_creators = []  # Master list of all creators
        self.selected_creators = set()  # Currently selected creators

        # GUI state file path (separate from config.ini)
        self.gui_state_file = Path.cwd() / "gui_state.json"

        # Load config from file
        self.load_config_file()

        # Load GUI state (creators) from separate file
        self.load_gui_state()

    def load_config_file(self):
        """Load configuration from config.ini"""
        try:
            log("AppState: Loading config from file...")
            log(f"AppState: Current working directory: {Path.cwd()}")

            config_path = Path.cwd() / "config.ini"
            log(f"AppState: Looking for config at: {config_path}")
            log(f"AppState: Absolute path: {config_path.absolute()}")
            log(f"AppState: Config file exists: {config_path.exists()}")

            if config_path.exists():
                log(f"AppState: Config file size: {config_path.stat().st_size} bytes")
                # Show first few lines of config for verification
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()[:5]
                    log(f"AppState: First lines of config.ini:")
                    for line in lines:
                        log(f"  {line.rstrip()}")
                except Exception as e:
                    log(f"AppState: Could not read config file: {e}")

            # Use the existing load_config function from config module
            log("AppState: Calling load_config() from config module...")
            log("  (This will use textio/loguru which requires stdout/stderr)")

            load_config(self.config)

            log("AppState: load_config() completed without exceptions")

            # Log what was loaded
            log(f"AppState: Config values after load:")
            log(f"  - token: {'SET (' + str(len(self.config.token)) + ' chars)' if self.config.token else 'NOT SET'}")
            log(f"  - user_agent: {'SET (' + str(len(self.config.user_agent)) + ' chars)' if self.config.user_agent else 'NOT SET'}")
            log(f"  - check_key: {self.config.check_key if self.config.check_key else 'NOT SET'}")

        except Exception as ex:
            log(f"AppState: Exception during config loading!")
            log(f"  Exception type: {type(ex).__name__}")
            log(f"  Exception message: {ex}")
            log(f"  Full traceback:")
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    log(f"    {line}")
            # Config will use defaults if load fails

    def save_config_file(self):
        """Save configuration to config.ini"""
        try:
            # Save using the config's internal method
            if hasattr(self.config, '_save_config'):
                self.config._save_config()

        except Exception as ex:
            print(f"Config save error: {ex}")

    def reset(self):
        """Reset download state"""
        self.is_downloading = False
        self.current_creator = None

    def load_gui_state(self):
        """Load GUI-specific state from gui_state.json"""
        try:
            if self.gui_state_file.exists():
                with open(self.gui_state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.all_creators = state.get("creators", [])
                    self.selected_creators = set(state.get("selected", []))
                    print(f"Loaded {len(self.all_creators)} creators from GUI state")
        except Exception as ex:
            print(f"GUI state load error: {ex}")
            # Default to empty if load fails
            self.all_creators = []
            self.selected_creators = set()

    def save_gui_state(self):
        """Save GUI-specific state to gui_state.json"""
        try:
            state = {
                "creators": self.all_creators,
                "selected": list(self.selected_creators)
            }
            with open(self.gui_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            print(f"Saved {len(self.all_creators)} creators to GUI state")
        except Exception as ex:
            print(f"GUI state save error: {ex}")


class OnlyFansAppState:
    """Application state for OnlyFans tab"""

    def __init__(self):
        self.config = OnlyFansConfig(program_version="1.0.0")
        self.is_downloading = False
        self.current_creator = None

        # GUI-specific creator management
        self.all_creators = []
        self.selected_creators = set()

        # GUI state file (separate from Fansly)
        self.gui_state_file = Path.cwd() / "onlyfans_gui_state.json"

        # Load config
        self.load_config_file()

        # Load GUI state
        self.load_gui_state()

    def load_config_file(self):
        """Load OnlyFans configuration"""
        try:
            log("OnlyFansAppState: Loading OF config...")
            load_onlyfans_config(self.config)
            log(f"OnlyFansAppState: Config loaded - sess: {'SET' if self.config.sess else 'NOT SET'}")

        except Exception as ex:
            log(f"OnlyFansAppState: Config load error: {ex}")

    def save_config_file(self):
        """Save OnlyFans configuration"""
        try:
            if hasattr(self.config, '_save_config'):
                self.config._save_config()
        except Exception as ex:
            print(f"OF config save error: {ex}")

    def reset(self):
        """Reset download state"""
        self.is_downloading = False
        self.current_creator = None

    def load_gui_state(self):
        """Load OF GUI state from json"""
        try:
            if self.gui_state_file.exists():
                with open(self.gui_state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.all_creators = state.get("creators", [])
                    self.selected_creators = set(state.get("selected", []))
        except Exception as ex:
            print(f"OF GUI state load error: {ex}")
            self.all_creators = []
            self.selected_creators = set()

    def save_gui_state(self):
        """Save OF GUI state to json"""
        try:
            state = {
                "creators": self.all_creators,
                "selected": list(self.selected_creators)
            }
            with open(self.gui_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as ex:
            print(f"OF GUI state save error: {ex}")
