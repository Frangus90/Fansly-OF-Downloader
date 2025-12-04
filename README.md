# Fansly Downloader NG

<div align="center">
  
  <a href="https://github.com/Frangus90/fansly-downloader-ng/releases/latest">
    <img src="https://img.shields.io/github/v/release/prof79/fansly-downloader-ng?color=%23b02d4a&display_name=tag&label=%F0%9F%9A%80%20Latest%20Compiled%20Release&style=flat-square" alt="Latest Release" />
  </a>
  </div>


A powerful, feature-rich tool for downloading content from Fansly. Built with both GUI and CLI interfaces for maximum flexibility.

![Fansly Downloader NG Screenshot GUI](resources/python_0E3fR5BqPK.png)
![Fansly Downloader NG Bulk Cropper Screenshot](resources/python_yGNIgdcM4X.png)
![Fansly Downloader NG Screenshot](resources/fansly_ng_screenshot.png)

This is a rewrite/refactoring of [Avnsx](https://github.com/Avnsx)'s original [Fansly Downloader](https://github.com/Avnsx/fansly-downloader). **Fansly Downloader NG** supports new features:

* Full command-line support for all options
* `config.ini` not required to start the program anymore - a `config.ini` with all program defaults will be generated automatically
* Support for minimal `config.ini` files - missing options will be added from program defaults automatically
* True multi-user support - put one or more creators as a list into `config.ini` (`username = creator1, creator2, creator3`) or supply via command-line
* Run it in non-interactive mode (`-ni`) without any user intervention - eg. when downloading while being away from the computer
* You may also run it in fully silent mode without the close prompt at the very end (`-ni -npox`) - eg. running **Fansly Downloader NG** from another script or from a scheduled task/cron job
* Logs all relevant messages (`Info`, `Warning`, `Error`, ...) of the last few sessions to `fansly_downloader_ng.log`. A history of 5 log files with a maximum size of 1 MiB will be preserved and can be deleted at your own discretion.
* Easier-to-extend, modern, modular and robust codebase
* It doesn't care about starring the repository

**Fansly Downloader NG** is the go-to app for all your bulk media downloading needs. Download photos, videos, audio or any other media from Fansly. This powerful tool has got you covered! Say goodbye to the hassle of individually downloading each piece of media – now you can download them all or just some in one go.

## Features

- **Multiple Download Modes** - Timeline posts, messages, and collections
- **Modern GUI** - Dark theme interface with real-time progress tracking
- **Command-Line Support** - Full CLI for automation and advanced users
- **Incremental Downloads** - Download only new content since last run
- **Smart Deduplication** - Skip files you already have
- **Cross-Platform** - Windows, Linux, and macOS support
- **Automatic Retry Logic** - Handles rate limiting and connection issues
- **M3U8 Support** - Download streaming videos automatically
- **Bulk Processing** - Easily update prior download folders
- **Customizable** - Separate media into sub-folders, download previews, and more

For detailed configuration settings, see the [Wiki](https://github.com/prof79/fansly-downloader-ng/wiki/Explanation-of-provided-programs-&-their-functionality#explanation-of-configini).

## Quick Start

### Windows (Executable)

1. Download the latest release from the [releases page](https://github.com/prof79/fansly-downloader-ng/releases/latest)
2. Extract and run `fansly_downloader_gui.exe`
3. Complete the setup wizard with your Fansly auth token
4. Add creators and start downloading

### Python (All Platforms)

**Requirements:** Python 3.11 or higher

1. Clone or download this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the GUI:
   ```bash
   python fansly_downloader_gui.py
   ```
   Or use the CLI:
   ```bash
   python fansly_downloader_ng.py
   ```

**Note:** Using a [Python virtual environment](https://docs.python.org/3/library/venv.html) is recommended but out-of-scope of this guide.

On Linux, you may need to install Tkinter separately:
```bash
sudo apt-get install python3-tk
```

On Windows and macOS, the `Tkinter` module is typically included in the Python installer.

Raw Python code versions of **Fansly Downloader NG** do not receive automatic updates. If an update is available you will be notified but need to manually download and set-up the [current repository](https://github.com/prof79/fansly-downloader-ng/archive/refs/heads/master.zip) again.

## GUI Features

- **Setup Wizard** - Automatic configuration on first run
- **Creator Management** - Visual list to add/remove creators
- **Real-time Progress** - See downloads in progress with file counts
- **Connection Testing** - Verify credentials before downloading
- **Log Access** - Press Ctrl+L to view diagnostic logs
- **Incremental Mode** - Toggle to download only new content
- **Image Crop Tool** - Built-in bulk image cropping with drag-and-drop support

### Image Crop Tool

The built-in Image Crop Tool allows you to batch process and crop downloaded images:

**Features:**
- **Bulk Processing** - Crop multiple images at once with individual settings
- **Drag & Drop** - Drag images directly onto the window to add them
- **Custom Aspect Ratios** - Apply specific aspect ratios (1:1, 16:9, 4:5, custom)
- **Crop Alignment** - Position crops (center, top, bottom, left, right)
- **Custom Presets** - Save frequently-used aspect ratios for quick access
- **Live Preview** - Interactive canvas with real-time crop preview
- **Format Options** - Export as JPEG, PNG, or WebP with quality control
- **Batch Export** - Process entire queue with one click

**Usage:**
1. Open Tools → Image Crop Tool from the main menu
2. Upload images or drag-and-drop them onto the window
3. Adjust crop box on each image or apply aspect ratio to all
4. Choose output format and quality settings
5. Process batch to export all cropped images

**File Handling:**
- Automatically detects existing files and offers overwrite/skip options
- Preserves original filenames by default
- Supports all common image formats (.jpg, .png, .webp, .gif, .bmp)

## CLI Usage

The command-line version supports all features with additional options for automation:

```bash
# Basic usage
python fansly_downloader_ng.py

# Non-interactive mode (no prompts)
python fansly_downloader_ng.py -ni

# Incremental mode (download only new content)
python fansly_downloader_ng.py -i

# Specify creators via command line
python fansly_downloader_ng.py -u creator1,creator2

# Silent mode for scripts/scheduled tasks
python fansly_downloader_ng.py -ni -npox
```

Run with `--help` to see all available options.

## Configuration

Settings are stored in `config.ini` which is created automatically on first run. You can edit this file to customize:

- Download directory
- Download modes (timeline, messages, collections)
- Rate limiting delays
- Duplicate handling
- Incremental mode settings
- Debug logging

See the [Wiki](https://github.com/prof79/fansly-downloader-ng/wiki) for detailed configuration options.

## Incremental Downloads

Incremental mode downloads only new content since your last run:

1. Enable in GUI Settings or use `-i` flag in CLI
2. First run downloads everything and saves position
3. Future runs download only new posts/messages
4. State tracked per creator in `download_history.json`

This saves bandwidth and time for regular downloads.

## Building from Source

### Create Windows Executable

```bash
pip install pyinstaller
python build_exe.py
```

The executable will be in `dist/fansly_downloader_gui.exe`

The build script automatically includes all required assets, icons, and dependencies.

### Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Troubleshooting

**Empty fields after setup wizard:**
- Check `fansly_downloader.log` for errors (Ctrl+L in GUI)
- Ensure complete token and user agent are pasted
- Try running setup wizard again

**Downloads failing:**
- Verify auth token using "Test Connection"
- Check download path exists and has write permissions
- Review log file for specific errors
- Ensure active subscriptions to creators

**Application crashes:**
- Check `fansly_downloader.log` in application directory
- Try deleting `config.ini` and `gui_state.json` for fresh setup
- Ensure Python 3.11+ if running from source

**Where is the log file?**
- Same directory as the application executable or Python script
- Named `fansly_downloader.log` (or `fansly_downloader_ng.log` for CLI)
- Contains all diagnostic output including errors and progress

## FAQ

**Q: Is this Windows-only?**
A: No. The executable is Windows-only, but the Python version works on Windows, macOS, and Linux.

**Q: Will I get banned?**
A: While there are no guarantees, it's worth noting that among the 24,000+ previous users, there have been no reported incidents. The tool respects rate limits and mimics normal browser behavior.

**Q: Does this bypass paywalls?**
A: No. You can only download content you have legitimate access to through your subscriptions. No paywall bypassing features will be added.

**Q: Why do antivirus programs flag the executable?**
A: The executable is not digitally signed (certificates are expensive), causing false positives. You can build your own executable from the source code or run the Python version directly. If you're knowledgeable with Python, you can decompile a PyInstaller executable using tools like [uncompyle6](https://github.com/rocky/python-uncompyle6/) to verify no harmful code is included.

**Q: Can I use this on mobile?**
A: No, mobile devices are not currently supported.

**Q: Could you add X feature or do X change?**
A: I'm regrettably very limited on time and thus primarily do stuff I find useful myself. You can contribute code by [opening a pull request](https://github.com/prof79/fansly-downloader-ng/pulls).

Please note that "Issue" tickets are reserved for reporting genuine or suspected bugs in the codebase of the downloader which require attention from the developer. They are not for general computer user problems.

## What's New

For the latest release notes and version history, see [ReleaseNotes.md](ReleaseNotes.md).

⚠️ Due to a [hashing bug](../../issues/13) duplicate videos might be downloaded if a creator re-posts a lot. Downloaded videos will have to be renamed in a future version when video hashing is perfected.

## Contributing

Contributions are welcome! Please open a pull request with your changes.

### Special Thanks

- **[@Avnsx](https://github.com/Avnsx)** - Original Fansly Downloader
- **[@liviaerxin](https://github.com/liviaerxin)** - Cross-platform plyvel package

A heartfelt thank you goes out to [@liviaerxin](https://github.com/liviaerxin) for their invaluable contribution in providing the cross-platform package [plyvel](https://github.com/wbolster/plyvel). Due to [these builds](https://github.com/liviaerxin/plyvel/releases/latest) Fansly downloader NG's initial interactive cross-platform setup has become a reality.

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This project is not affiliated with, sponsored by, or endorsed by Fansly or Select Media LLC. This tool is for educational purposes only and is designed for downloading content you have legitimate access to. The developer is not responsible for end-user actions. No paywall bypassing features will be added. No user data is collected during usage.

"Fansly" or [fansly.com](https://fansly.com/) is operated by Select Media LLC as stated on their "Contact" page. This repository and the provided content in it isn't in any way affiliated with, sponsored by, or endorsed by Select Media LLC or "Fansly". The developer (referred to: "prof79" in the following) of this code is not responsible for the end users actions, no unlawful activities of any kind are being encouraged. Statements and processes described in this repository only represent best practice guidance aimed at fostering an effective software usage. The repository was written purely for educational purposes, in an entirely theoretical environment. Thus, any information is presented on the condition that the developer of this code shall not be held liable in no event to you or anyone else for any direct, special, incidental, indirect or consequential damages of any kind, or any damages whatsoever, including without limitation, loss of profit, loss of use, savings or revenue, or the claims of third parties, whether the developer has advised of the possibility of such loss, however caused and on any theory of liability, arising out of or in connection with the possession, use or performance of this software. The material embodied in this repository is supplied to you "as-is" and without warranty of any kind, express, implied or otherwise, including without limitation, any warranty of fitness. This code does not bypass any paywalls & no end user information is collected during usage. Finally it is important to note that this GitHub repository is the sole branch maintained and owned by the developer and any third-party websites or entities, that might refer to or be referred from it are in no way affiliated with Fansly Downloader, either directly or indirectly. This disclaimer is preliminary and is subject to revision.
