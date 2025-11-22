# Fansly Downloader NG

A powerful, feature-rich tool for downloading content from Fansly. Built with both GUI and CLI interfaces for maximum flexibility.

![Fansly Downloader NG Screenshot GUI](resources/FanslyDownloaderNG_6jF6RlrylQ.png)
![Fansly Downloader NG Screenshot](resources/fansly_ng_screenshot.png)

## Features

- **Multiple Download Modes** - Timeline posts, messages, and collections
- **Modern GUI** - Dark theme interface with real-time progress tracking
- **Command-Line Support** - Full CLI for automation and advanced users
- **Incremental Downloads** - Download only new content since last run
- **Smart Deduplication** - Skip files you already have
- **Cross-Platform** - Windows, Linux, and macOS support
- **Automatic Retry Logic** - Handles rate limiting and connection issues
- **M3U8 Support** - Download streaming videos automatically

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

## GUI Features

- **Setup Wizard** - Automatic configuration on first run
- **Creator Management** - Visual list to add/remove creators
- **Real-time Progress** - See downloads in progress with file counts
- **Connection Testing** - Verify credentials before downloading
- **Log Access** - Press Ctrl+L to view diagnostic logs
- **Incremental Mode** - Toggle to download only new content

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

### Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Linux users may need to install Tkinter separately:

```bash
sudo apt-get install python3-tk
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

## FAQ

**Q: Is this Windows-only?**
A: No. The executable is Windows-only, but the Python version works on Windows, macOS, and Linux.

**Q: Will I get banned?**
A: Among 24,000+ users, there have been no reported bans. The tool respects rate limits and mimics normal browser behavior.

**Q: Does this bypass paywalls?**
A: No. You can only download content you have legitimate access to through your subscriptions.

**Q: Why do antivirus programs flag the executable?**
A: The executable is not digitally signed (certificates are expensive), causing false positives. You can build your own executable from the source code or run the Python version directly.

**Q: Can I use this on mobile?**
A: No, mobile devices are not currently supported.

## Contributing

Contributions are welcome! Please open a pull request with your changes.

### Special Thanks

- **[@Avnsx](https://github.com/Avnsx)** - Original Fansly Downloader
- **[@liviaerxin](https://github.com/liviaerxin)** - Cross-platform plyvel package

## License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This project is not affiliated with, sponsored by, or endorsed by Fansly or Select Media LLC. This tool is for educational purposes only and is designed for downloading content you have legitimate access to. The developer is not responsible for end-user actions. No paywall bypassing features will be added. No user data is collected during usage.
