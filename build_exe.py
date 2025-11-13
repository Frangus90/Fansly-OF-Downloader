"""
Build script to create standalone .exe for Fansly Downloader NG GUI
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
            "--name=FanslyDownloaderNG",  # Exe name
            "--onefile",  # Single exe file
            "--windowed",  # No console window
            "--icon=NONE",  # TODO: Add icon later
            "--add-data=config.sample.ini;.",  # Include sample config
            "--hidden-import=customtkinter",  # Ensure CTk included
            "--hidden-import=PIL",  # Ensure Pillow included
            "--hidden-import=plyvel",  # Ensure LevelDB included
            "--hidden-import=requests",  # Ensure requests included
            "--hidden-import=loguru",  # Ensure loguru included
            "--hidden-import=rich",  # Ensure rich included
            "--hidden-import=m3u8",  # Ensure m3u8 included
            "--hidden-import=ImageHash",  # Ensure ImageHash included
            "--clean",  # Clean cache
            "--noconfirm",  # Overwrite without asking
        ]
    )

    print("\n" + "=" * 60)
    print("✓ Build complete!")
    print(f"✓ Executable: dist\\FanslyDownloaderNG.exe")

    if os.path.exists("dist\\FanslyDownloaderNG.exe"):
        size_mb = os.path.getsize("dist\\FanslyDownloaderNG.exe") // 1024 // 1024
        print(f"✓ Size: ~{size_mb} MB")
        print("\nYou can now run: dist\\FanslyDownloaderNG.exe")
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
