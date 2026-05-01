"""
Build script to create standalone .exe for Fansly & OnlyFans Downloader NG GUI
Usage:
    python build_exe.py          # Build only
    python build_exe.py --release # Build and create GitHub release
"""

import PyInstaller.__main__
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


APP_NAME = "FanslyOFDownloaderNG"
RELEASE_NOTES_PATH = Path("ReleaseNotes.md")
RELEASE_REPO = "Frangus90/fansly-downloader-ng"

# Files containing version strings to update
VERSION_FILES = [
    ("app_version.py", r"^APP_VERSION\s*=\s*['\"](.+?)['\"]", 'APP_VERSION = "{version}"'),
]


@dataclass(frozen=True)
class ReleaseNotes:
    """Release notes parsed from ReleaseNotes.md."""

    version: str
    notes: str


def get_current_version() -> str:
    """Read current version from the shared version file."""
    with open("app_version.py", "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"^APP_VERSION\s*=\s*['\"](.+?)['\"]", content, re.MULTILINE)
    if match:
        return match.group(1)

    raise ValueError("Could not find APP_VERSION in app_version.py")


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


def find_unreleased_release_notes(content: str) -> ReleaseNotes:
    """Find the single versioned unreleased section in ReleaseNotes.md."""
    versioned_pattern = re.compile(
        r"^###\s+(\d+\.\d+\.\d+)\s*-\s*Unreleased\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(versioned_pattern.finditer(content))

    if len(matches) > 1:
        raise ValueError("ReleaseNotes.md must contain only one unreleased version section")

    if not matches:
        plain_unreleased = re.search(
            r"^###\s+Unreleased\s*$",
            content,
            re.IGNORECASE | re.MULTILINE,
        )
        if plain_unreleased:
            raise ValueError("ReleaseNotes.md unreleased heading must include a version, e.g. ### 1.8.8 - Unreleased")
        raise ValueError("Could not find a versioned unreleased section in ReleaseNotes.md")

    match = matches[0]
    next_heading = re.search(r"^###\s+", content[match.end():], re.MULTILINE)
    section_end = match.end() + next_heading.start() if next_heading else len(content)
    notes = content[match.end():section_end].strip()

    if not notes:
        raise ValueError(f"ReleaseNotes.md section for {match.group(1)} is empty")

    return ReleaseNotes(version=match.group(1), notes=notes)


def read_unreleased_release_notes(path: Path = RELEASE_NOTES_PATH) -> ReleaseNotes:
    """Read and parse the unreleased release notes from disk."""
    with path.open("r", encoding="utf-8") as f:
        return find_unreleased_release_notes(f.read())


def stamp_release_notes(content: str, version: str, release_date: str) -> str:
    """Replace a versioned Unreleased heading with the release date."""
    pattern = re.compile(
        rf"^###\s+{re.escape(version)}\s*-\s*Unreleased\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    stamped, count = pattern.subn(f"### {version} - {release_date}", content, count=1)

    if count != 1:
        raise ValueError(f"Could not find unreleased heading for version {version}")

    return stamped


def stamp_release_notes_file(
    version: str,
    release_date: str,
    path: Path = RELEASE_NOTES_PATH,
) -> None:
    """Stamp ReleaseNotes.md with the release date."""
    content = path.read_text(encoding="utf-8")
    stamped = stamp_release_notes(content, version, release_date)
    path.write_text(stamped, encoding="utf-8")
    print(f"  Updated {path}: marked v{version} as released ({release_date})")


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


def get_current_branch() -> str:
    """Return the current git branch name."""
    result = run_command(["git", "branch", "--show-current"])
    branch = result.stdout.strip()
    if not branch:
        raise RuntimeError("Cannot create a release from detached HEAD")
    return branch


def has_upstream_branch() -> bool:
    """Check whether the current branch has an upstream configured."""
    result = run_command(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        check=False,
    )
    return result.returncode == 0


def push_current_branch():
    """Push the current branch, setting origin as upstream when needed."""
    branch = get_current_branch()
    if has_upstream_branch():
        run_command(["git", "push"])
        return

    print(f"  No upstream configured for {branch}; setting origin/{branch}")
    run_command(["git", "push", "--set-upstream", "origin", branch])


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


def get_latest_github_release_version() -> str | None:
    """Return the latest GitHub release version without the leading v."""
    result = run_command(["gh", "release", "view", "--json", "tagName"], check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        release = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    tag_name = release.get("tagName")
    if not tag_name:
        return None

    return tag_name.removeprefix("v")


def github_release_exists(version: str) -> bool:
    """Return True if a GitHub release already exists for version."""
    result = run_command(
        ["gh", "release", "view", f"v{version}", "--json", "tagName"],
        check=False,
    )
    return result.returncode == 0


def git_tag_exists(tag: str) -> bool:
    """Return True if the local git tag already exists."""
    result = run_command(["git", "tag", "-l", tag], check=False)
    return tag in result.stdout.splitlines()


def remote_git_tag_exists(tag: str) -> bool:
    """Return True if the remote git tag already exists."""
    result = run_command(["git", "ls-remote", "--tags", "origin", tag], check=False)
    return result.returncode == 0 and bool(result.stdout.strip())


def validate_release_can_publish(version: str, latest_version: str | None) -> None:
    """Validate that the release version can be published."""
    parse_version(version)

    if latest_version is not None and parse_version(version) <= parse_version(latest_version):
        raise RuntimeError(
            f"Release version {version} must be newer than latest GitHub release {latest_version}"
        )

    tag = f"v{version}"
    if github_release_exists(version):
        raise RuntimeError(f"GitHub release {tag} already exists")

    if git_tag_exists(tag):
        raise RuntimeError(f"Git tag {tag} already exists")

    if remote_git_tag_exists(tag):
        raise RuntimeError(f"Remote git tag {tag} already exists")


def create_github_release(version: str, changelog: str, asset_path: str):
    """Create a GitHub release with the built asset (zip or exe)"""
    tag = f"v{version}"

    print(f"\nCreating GitHub release {tag}...")

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
    push_current_branch()
    run_command(["git", "push", "origin", tag])

    # Create GitHub release with executable
    print("\nCreating GitHub release...")
    release_notes_file = Path(tempfile.gettempdir()) / f"fansly-release-notes-{version}.md"
    release_notes_file.write_text(changelog, encoding="utf-8")

    try:
        cmd = [
            "gh", "release", "create", tag,
            asset_path,
            "--title", f"Fansly & OnlyFans Downloader NG {tag}",
            "--notes-file", str(release_notes_file),
        ]

        run_command(cmd)
    finally:
        release_notes_file.unlink(missing_ok=True)
    print(f"\n✓ Release {tag} created successfully!")
    print(f"  https://github.com/{RELEASE_REPO}/releases/tag/{tag}")


def build_exe(version: str | None = None) -> str | None:
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

    app_name = APP_NAME

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
            "--hidden-import=imagehash",
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
            # Exclude heavy ML dependencies not used by the downloader
            "--exclude-module=easyocr",
            "--exclude-module=torch",
            "--exclude-module=torchvision",
            "--exclude-module=torchaudio",
            "--exclude-module=scipy",
            "--exclude-module=cv2",
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
    zip_path = create_distribution_zip(dist_dir, app_name, version=version)

    print("\n" + "=" * 60)
    print("✓ Build complete!")
    print(f"✓ App folder: {dist_dir}")
    print(f"✓ Executable: {exe_path}")
    if zip_path:
        size_mb = os.path.getsize(zip_path) / 1024 / 1024
        print(f"✓ Distribution zip: {zip_path} ({size_mb:.1f} MB)")
    print("=" * 60)

    return str(zip_path) if zip_path else str(exe_path)


def create_distribution_zip(dist_dir: Path, app_name: str, version: str | None = None) -> Path | None:
    """Create a zip file from the onedir build for GitHub release."""
    if version:
        zip_path = Path("dist") / f"{app_name}-Windows-x64-v{version}.zip"
    else:
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


def run_release_flow() -> None:
    """Run the release flow driven by ReleaseNotes.md."""
    release_notes = read_unreleased_release_notes()
    new_version = release_notes.version
    changelog = release_notes.notes

    latest_version = get_latest_github_release_version()
    if latest_version:
        print(f"\nLatest GitHub release: v{latest_version}")
    else:
        print("\nNo existing GitHub release found")

    validate_release_can_publish(new_version, latest_version)

    print(f"\nDetected unreleased version: v{new_version}")
    print(f"\nRelease notes:\n{changelog}")

    confirm = input("\nProceed with release? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    old_version = get_current_version()
    if old_version != new_version:
        print(f"\nUpdating version: {old_version} -> {new_version}")
    else:
        print(f"\nKeeping version: {new_version}")
    update_version_in_files(new_version)

    release_date = datetime.now().date().isoformat()
    stamp_release_notes_file(new_version, release_date)

    exe_path = build_exe(version=new_version)

    if exe_path and os.path.exists(exe_path):
        create_github_release(new_version, changelog, exe_path)
    else:
        print("\nBuild failed, skipping release")


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

            run_release_flow()
            return

            # Changelog
            changelog = prompt_changelog()
            if not changelog:
                print("\n⚠ No changelog provided, using default")
                changelog = "Bug fixes and improvements"

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
