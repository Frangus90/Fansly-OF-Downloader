"""
CustomTkinter application initialization
"""

import customtkinter as ctk
from pathlib import Path


def initialize_app():
    """Initialize CustomTkinter settings"""
    # Set dark theme only
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def create_app():
    """Create and return the main CTk app instance"""
    initialize_app()

    # Create main window
    # (wizard check will happen after event loop starts)
    from gui.window import MainWindow

    return MainWindow()


def should_run_wizard(config_path):
    """
    Determine if setup wizard should run

    Returns True if:
    - config.ini doesn't exist
    - config.ini is empty
    - config.ini is missing required sections
    - config.ini has invalid/placeholder values
    """
    from configparser import ConfigParser

    # Check 1: File doesn't exist
    if not config_path.exists():
        print("Config file not found - running setup wizard")
        return True

    # Check 2: File is empty or too small
    try:
        file_size = config_path.stat().st_size
        if file_size == 0:
            print("Config file is empty - running setup wizard")
            return True
        if file_size < 100:  # Valid config should be at least 100 bytes
            print("Config file is too small - running setup wizard")
            return True
    except Exception as ex:
        print(f"Error checking config file size: {ex} - running setup wizard")
        return True

    # Check 3: File is valid INI format with required sections/fields
    try:
        parser = ConfigParser()
        parser.read(config_path, encoding="utf-8")

        # Check for required sections
        required_sections = ["TargetedCreator", "MyAccount", "Options", "Cache", "Logic"]
        for section in required_sections:
            if not parser.has_section(section):
                print(f"Config missing section [{section}] - running setup wizard")
                return True

        # Check for critical MyAccount fields (using PascalCase to match config.py)
        if not parser.has_option("MyAccount", "Authorization_Token"):
            print("Config missing Authorization_Token - running setup wizard")
            return True

        if not parser.has_option("MyAccount", "User_Agent"):
            print("Config missing User_Agent - running setup wizard")
            return True

        if not parser.has_option("MyAccount", "Check_Key"):
            print("Config missing Check_Key - running setup wizard")
            return True

        # Check if values are valid (not placeholders)
        token = parser.get("MyAccount", "Authorization_Token", fallback="")
        user_agent = parser.get("MyAccount", "User_Agent", fallback="")
        check_key = parser.get("MyAccount", "Check_Key", fallback="")

        # Validate token
        if not token or "ReplaceMe" in token or len(token) < 50:
            print("Config has invalid/placeholder token - running setup wizard")
            return True

        # Validate user agent
        if not user_agent or "ReplaceMe" in user_agent or len(user_agent) < 40:
            print("Config has invalid/placeholder user_agent - running setup wizard")
            return True

        # Validate check_key
        if not check_key or "ReplaceMe" in check_key or len(check_key) < 10:
            print("Config has invalid/placeholder check_key - running setup wizard")
            return True

        # Config appears valid
        print("Config file is valid - skipping setup wizard")
        return False

    except Exception as ex:
        print(f"Config validation error: {ex} - running setup wizard")
        return True
