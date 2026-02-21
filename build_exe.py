"""
Build script to create standalone .exe for Fansly & OnlyFans Downloader NG GUI
Usage:
    python build_exe.py          # Build only
    python build_exe.py --release # Build and create GitHub release
"""

import PyInstaller.__main__
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


# Files containing version strings to update
VERSION_FILES = [
    ("fansly_downloader_ng.py", r"^__version__\s*=\s*['\"](.+?)['\"]", "__version__ = '{version}'"),
    ("onlyfans_downloader.py", r"^__version__\s*=\s*['\"](.+?)['\"]", "__version__ = '{version}'"),
]


def get_current_version() -> str:
    """Read current version from main file"""
    with open("fansly_downloader_ng.py", "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"^__version__\s*=\s*['\"](.+?)['\"]", content, re.MULTILINE)
    if match:
        return match.group(1)

    raise ValueError("Could not find __version__ in fansly_downloader_ng.py")


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse version string into (major, minor, patch)"""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version}. Expected X.Y.Z")

    return int(parts[0]), int(parts[1]), int(parts[2])


def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type (major, minor, patch)"""
    major, minor, patch = parse_version(current)

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")


def update_version_in_files(new_version: str):
    """Update version string in all relevant files"""
    for filename, pattern, replacement in VERSION_FILES:
        if not os.path.exists(filename):
            print(f"  Warning: {filename} not found, skipping")
            continue

        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        new_content = re.sub(
            pattern,
            replacement.format(version=new_version),
            content,
            flags=re.MULTILINE
        )

        with open(filename, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"  Updated {filename}")

    # Update BUILD_TIMESTAMP in GUI
    gui_file = "fansly_downloader_gui.py"
    if os.path.exists(gui_file):
        with open(gui_file, "r", encoding="utf-8") as f:
            content = f.read()

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        new_content = re.sub(
            r'BUILD_TIMESTAMP\s*=\s*"[^"]*"',
            f'BUILD_TIMESTAMP = "v{new_version}_{timestamp}"',
            content
        )

        with open(gui_file, "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"  Updated {gui_file} BUILD_TIMESTAMP")


def prompt_version_bump() -> tuple[str, str]:
    """Interactive prompt for version bump"""
    current = get_current_version()
    print(f"\nCurrent version: {current}")
    print("\nVersion bump options:")
    print(f"  [1] Patch  ({current} -> {bump_version(current, 'patch')})")
    print(f"  [2] Minor  ({current} -> {bump_version(current, 'minor')})")
    print(f"  [3] Major  ({current} -> {bump_version(current, 'major')})")
    print(f"  [4] Custom (enter manually)")
    print(f"  [5] Keep current ({current})")

    while True:
        choice = input("\nSelect option [1-5]: ").strip()

        if choice == "1":
            return current, bump_version(current, "patch")
        elif choice == "2":
            return current, bump_version(current, "minor")
        elif choice == "3":
            return current, bump_version(current, "major")
        elif choice == "4":
            custom = input("Enter new version (X.Y.Z): ").strip()
            try:
                parse_version(custom)  # Validate format
                return current, custom
            except ValueError as e:
                print(f"  Error: {e}")
                continue
        elif choice == "5":
            return current, current
        else:
            print("  Invalid option, try again")


def prompt_changelog() -> str:
    """Prompt for changelog message"""
    print("\nEnter changelog for this release (short description):")
    print("(Press Enter twice to finish)")

    lines = []
    empty_count = 0

    while empty_count < 1:
        line = input()
        if line == "":
            empty_count += 1
        else:
            empty_count = 0
            lines.append(line)

    return "\n".join(lines).strip()


def run_command(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return result"""
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if check and result.returncode != 0:
        print(f"  Error: {result.stderr}")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")

    return result


def check_gh_cli() -> bool:
    """Check if GitHub CLI is installed and authenticated"""
    try:
        result = run_command(["gh", "auth", "status"], check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_previous_tag() -> str:
    """Get the previous git tag for changelog comparison"""
    result = run_command(["git", "describe", "--tags", "--abbrev=0", "HEAD^"], check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    return "initial"


def create_github_release(version: str, changelog: str, asset_path: str):
    """Create a GitHub release with the built asset (zip or exe)"""
    tag = f"v{version}"

    print(f"\nCreating GitHub release {tag}...")

    # Check if tag already exists
    result = run_command(["git", "tag", "-l", tag], check=False)
    if tag in result.stdout:
        print(f"  Warning: Tag {tag} already exists")
        overwrite = input("  Overwrite? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("  Aborting release")
            return
        # Delete existing tag locally and remotely
        run_command(["git", "tag", "-d", tag], check=False)
        run_command(["git", "push", "origin", f":refs/tags/{tag}"], check=False)

    # Stage and commit version changes
    print("\nCommitting version bump...")
    run_command(["git", "add", "-A"])

    commit_msg = f"Release {tag}\n\n{changelog}"
    run_command(["git", "commit", "-m", commit_msg], check=False)  # May fail if no changes

    # Create tag
    print(f"\nCreating tag {tag}...")
    run_command(["git", "tag", "-a", tag, "-m", f"Release {tag}"])

    # Push changes and tag
    print("\nPushing to remote...")
    run_command(["git", "push"])
    run_command(["git", "push", "origin", tag])

    # Create GitHub release with executable
    print("\nCreating GitHub release...")
    prev_tag = get_previous_tag()
    release_notes = f"## What's Changed\n\n{changelog}\n\n---\n\n**Full Changelog**: https://github.com/Frangus90/fansly-downloader-ng/compare/{prev_tag}...{tag}"

    cmd = [
        "gh", "release", "create", tag,
        asset_path,
        "--title", f"Fansly & OnlyFans Downloader NG {tag}",
        "--notes", release_notes
    ]

    run_command(cmd)
    print(f"\n✓ Release {tag} created successfully!")
    print(f"  https://github.com/Frangus90/fansly-downloader-ng/releases/tag/{tag}")


def build_exe() -> str | None:
    """Build the executable using PyInstaller (onedir mode)"""
    print("\n" + "=" * 60)
    print("Building executable...")
    print("=" * 60)

    # Clean previous builds
    if os.path.exists("build"):
        print("Cleaning old build directory...")
        shutil.rmtree("build")
    if os.path.exists("dist"):
        print("Cleaning old dist directory...")
        shutil.rmtree("dist")

    app_name = "FanslyOFDownloaderNG"

    # PyInstaller configuration
    print("Running PyInstaller...")
    PyInstaller.__main__.run(
        [
            "fansly_downloader_gui.py",  # Entry point
            f"--name={app_name}",
            "--onedir",  # Directory bundle (allows post-install of packages)
            "--windowed",  # No console window
            "--icon=resources/fansly_ng.ico",
            # Config files
            "--add-data=config.sample.ini;.",
            "--add-data=onlyfans_config.ini;.",
            # Icon file (for runtime taskbar icon)
            "--add-data=resources/fansly_ng.ico;resources",
            # Base packages
            "--hidden-import=customtkinter",
            "--hidden-import=PIL",
            "--hidden-import=plyvel",
            "--hidden-import=requests",
            "--hidden-import=loguru",
            "--hidden-import=rich",
            "--hidden-import=m3u8",
            "--hidden-import=ImageHash",
            # OnlyFans modules
            "--hidden-import=api.onlyfans_api",
            "--hidden-import=api.onlyfans_auth",
            "--hidden-import=config.onlyfans_config",
            "--hidden-import=download_of",
            "--hidden-import=download_of.timeline",
            "--hidden-import=download_of.account",
            "--hidden-import=gui.tabs.onlyfans_tab",
            "--hidden-import=gui.widgets.onlyfans_auth",
            "--hidden-import=gui.widgets.credential_help",
            # Exclude heavy OCR/ML dependencies (installed on-demand via app)
            "--exclude-module=easyocr",
            "--exclude-module=torch",
            "--exclude-module=torchvision",
            "--exclude-module=torchaudio",
            "--exclude-module=scipy",
            "--exclude-module=cv2",
            "--exclude-module=skimage",
            "--exclude-module=shapely",
            "--clean",
            "--noconfirm",
        ]
    )

    dist_dir = Path("dist") / app_name
    exe_path = dist_dir / f"{app_name}.exe"

    if not exe_path.exists():
        print("⚠ Warning: Executable not found!")
        print("=" * 60)
        return None

    # Create zip for distribution
    zip_path = create_distribution_zip(dist_dir, app_name)

    print("\n" + "=" * 60)
    print("✓ Build complete!")
    print(f"✓ App folder: {dist_dir}")
    print(f"✓ Executable: {exe_path}")
    if zip_path:
        size_mb = os.path.getsize(zip_path) / 1024 / 1024
        print(f"✓ Distribution zip: {zip_path} ({size_mb:.1f} MB)")
    print("=" * 60)

    return str(zip_path) if zip_path else str(exe_path)


def create_distribution_zip(dist_dir: Path, app_name: str) -> Path | None:
    """Create a zip file from the onedir build for GitHub release."""
    zip_path = Path("dist") / f"{app_name}.zip"

    print(f"\nCreating distribution zip: {zip_path}")

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in dist_dir.rglob("*"):
                if file_path.is_file():
                    arcname = Path(app_name) / file_path.relative_to(dist_dir)
                    zf.write(file_path, arcname)

        return zip_path
    except Exception as e:
        print(f"⚠ Failed to create zip: {e}")
        return None


def main():
    """Main entry point"""
    release_mode = "--release" in sys.argv

    print("=" * 60)
    print("Fansly & OnlyFans Downloader NG - Build Script")
    print("=" * 60)

    try:
        if release_mode:
            # Check prerequisites
            if not check_gh_cli():
                print("\n⚠ GitHub CLI (gh) not found or not authenticated!")
                print("  Install: https://cli.github.com/")
                print("  Auth: gh auth login")
                sys.exit(1)

            # Version bump
            old_version, new_version = prompt_version_bump()

            if old_version != new_version:
                print(f"\nUpdating version: {old_version} -> {new_version}")
                update_version_in_files(new_version)
            else:
                print(f"\nKeeping version: {new_version}")

            # Changelog
            changelog = prompt_changelog()
            if not changelog:
                print("\n⚠ No changelog provided, using default")
                changelog = "Bug fixes and improvements"

            print(f"\nChangelog:\n{changelog}")

            # Build
            exe_path = build_exe()

            if exe_path and os.path.exists(exe_path):
                # Create release
                confirm = input("\nCreate GitHub release? [Y/n]: ").strip().lower()
                if confirm != "n":
                    create_github_release(new_version, changelog, exe_path)
            else:
                print("\n⚠ Build failed, skipping release")

        else:
            # Just build
            build_exe()
            print("\nTip: Run with --release to create a GitHub release")

    except KeyboardInterrupt:
        print("\n\nAborted by user")
        sys.exit(1)
    except Exception as ex:
        print(f"\n✗ Error: {ex}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
