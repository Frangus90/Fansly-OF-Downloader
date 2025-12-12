"""
Build script to create standalone .exe for Fansly & OnlyFans Downloader NG GUI
Usage: python build_exe.py
"""

import PyInstaller.__main__
import os
import shutil


def build_exe():
    """Build the executable using PyInstaller"""

    print("Starting build process...")

    # Clean previous builds
    if os.path.exists("build"):
        print("Cleaning old build directory...")
        shutil.rmtree("build")
    if os.path.exists("dist"):
        print("Cleaning old dist directory...")
        shutil.rmtree("dist")

    # PyInstaller configuration
    print("Running PyInstaller...")
    PyInstaller.__main__.run(
        [
            "fansly_downloader_gui.py",  # Entry point
            "--name=FanslyOFDownloaderNG",  # Exe name (updated for both platforms)
            "--onefile",  # Single exe file
            "--windowed",  # No console window
            "--icon=resources/fansly_ng.ico",  # Application icon (file icon)
            # Config files
            "--add-data=config.sample.ini;.",  # Fansly sample config
            "--add-data=onlyfans_config.ini;.",  # OF config template
            # Icon file (for runtime taskbar icon)
            "--add-data=resources/fansly_ng.ico;resources",  # Include icon in bundle
            # Base packages
            "--hidden-import=customtkinter",  # Ensure CTk included
            "--hidden-import=PIL",  # Ensure Pillow included
            "--hidden-import=plyvel",  # Ensure LevelDB included
            "--hidden-import=requests",  # Ensure requests included
            "--hidden-import=loguru",  # Ensure loguru included
            "--hidden-import=rich",  # Ensure rich included
            "--hidden-import=m3u8",  # Ensure m3u8 included
            "--hidden-import=ImageHash",  # Ensure ImageHash included
            # OnlyFans modules (NEW)
            "--hidden-import=api.onlyfans_api",
            "--hidden-import=api.onlyfans_auth",
            "--hidden-import=config.onlyfans_config",
            "--hidden-import=download_of",
            "--hidden-import=download_of.timeline",
            "--hidden-import=download_of.account",
            "--hidden-import=gui.tabs.onlyfans_tab",
            "--hidden-import=gui.widgets.onlyfans_auth",
            "--hidden-import=gui.widgets.credential_help",
            "--clean",  # Clean cache
            "--noconfirm",  # Overwrite without asking
        ]
    )

    print("\n" + "=" * 60)
    print("✓ Build complete!")
    print(f"✓ Executable: dist\\FanslyOFDownloaderNG.exe")

    if os.path.exists("dist\\FanslyOFDownloaderNG.exe"):
        size_mb = os.path.getsize("dist\\FanslyOFDownloaderNG.exe") // 1024 // 1024
        print(f"✓ Size: ~{size_mb} MB")
        print("\nYou can now run: dist\\FanslyOFDownloaderNG.exe")
        print("✓ Supports both Fansly and OnlyFans!")
    else:
        print("⚠ Warning: Executable not found!")

    print("=" * 60)


if __name__ == "__main__":
    try:
        build_exe()
    except Exception as ex:
        print(f"\n✗ Build failed: {ex}")
        import traceback

        traceback.print_exc()
        input("\nPress Enter to exit...")
