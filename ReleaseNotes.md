# Fansly Downloader NG

## 🗒️ Release Notes

### 1.8.8 - 2026-05-01
**New Features:**

- **Release notes driven releases** - `build_exe.py --release` now reads `ReleaseNotes.md`, detects the unreleased version, uses that section as the GitHub release notes, and stamps the entry with the release date before tagging
  - Release builds now publish versioned Windows zip assets like `FanslyOFDownloaderNG-Windows-x64-v1.8.8.zip`
  - The release script checks GitHub releases and existing tags before publishing so an already-released version is not reused accidentally
- **GUI auto-updater install flow** - The GUI updater now finds the Windows release zip, downloads it, extracts it over the installed app folder, and restarts the app without requiring users to download or unzip releases manually
  - The updater still supports the older `FanslyOFDownloaderNG.zip` asset name as a fallback
  - User config and GUI state files are preserved during update extraction so local settings are not overwritten by bundled defaults
  - Update notifications can show release notes from the GitHub release body

**Improvements:**

- **Shared version source** - Fansly, OnlyFans, and GUI startup state now read the app version from one shared module instead of hardcoded GUI placeholder versions
- **Updater/release tests** - Added unit coverage for release-note parsing/stamping, updater asset selection, and shared version wiring

### 1.8.7 - 2026-04-29

**Removed Features:**

- **Image Crop Tool removed** - Removed the built-in bulk image cropper from the downloader GUI
  - Removed the cropper launch buttons, tool handlers, drag-and-drop initialization, cropper UI modules, image processing modules, cropper test file, and cropper screenshot
  - Removed cropper-related README sections so the public documentation matches the downloader app
- **Watermark Auto-Crop Tool removed** - Removed OCR-based watermark detection and cropping from the downloader
  - Removed the OCR worker, watermark cropper UI, OCR install flow, and watermark processing modules
  - Trimmed downloader requirements and build inputs that only existed for cropper/OCR/compression support
- **Verification** - Ran downloader crypto tests, GUI import smoke check, stale-reference scan, and release-note formatting checks

### 1.8.6 - 2026-04-20

**Bug Fixes:**

- **Confirmation/warning popups rendering at tiny size** - Dialogs like "Process Batch?", overwrite/skip prompts, preset save, and compression warnings were clipping their title, message, and buttons
  - Dialogs now size themselves from the content's requested size instead of Tk's pre-layout default, so text, paths, and buttons no longer get cut off

### 1.8.5 - 2026-04-19

**Bug Fixes:**

- **UI sizing on smaller monitors** - Start Download / Stop buttons, "Single Post" radio, and "Import Subs" button no longer clip off-screen on 1080p and lower resolutions
  - Settings content now scrolls when the window is too short; Start/Stop and the status bar are pinned as a fixed footer so they're always reachable
  - Fixed inconsistent default geometry (`900x1000` vs `minsize 1000x700`); default is now `1280x900`, min `1000x600`
  - Removed a fixed inner tabview width that was squeezing the columns below the minimum
- **Console log window failing to open** - "Show Log" now reliably displays the log window on the first click
  - Fixed logic that hid the window immediately after creating it when the previous session had left it visible
  - Saved log window positions are now clamped to the current screen; windows left on a disconnected/smaller monitor no longer open off-screen
  - Window is now forced to the front on open (Windows z-order fix)
  - Prevented a crash in the log badge updater when log messages arrived before the window had been opened
- **Confirmation/warning popups rendering at tiny size** - Dialogs like "Process Batch?", overwrite/skip prompts, preset save, and compression warnings were clipping their title, message, and buttons
  - Dialogs now size themselves from the content's requested size instead of Tk's pre-layout default, so text, paths, and buttons no longer get cut off

### 1.8.4 - 2026-03-24

**Bug Fixes:**

- General bug fixing release

### 1.8.3 - 2026-02-27

**Bug Fixes:**

- Fixed high memory usage in the Auto Crop tool

### 1.8.2 - 2026-02-25

**Bug Fixes:**

- General bug fix release

### 1.8.1 - 2026-02-21

**Improvements:**

- Switched to a zip/folder release package to make EasyOCR installation easier
- Added automatic detection for CUDA-capable GPU acceleration

### 1.8.0 - 2026-02-20

**New Features:**

- **Watermark Auto-Crop Tool** - OCR-based tool that detects and crops watermark text bars from images
  - Blacklist matching with fuzzy matching for common OCR misreads
  - Sensitivity presets from Low through Max
  - Crop-all override for detected text regions
  - Batch processing, live preview, GPU acceleration support, and drag-and-drop

**Setup:**

- EasyOCR is not bundled with the executable; install instructions are provided in the app

### 1.7.2 - 2026-02-18

**Bug Fixes:**

- General bug fixes and improvements

### 1.7.1 - 2026-02-03

**Bug Fixes:**

- Fixed an error with the log window/log handling

### 1.6.1 - Maintenance notes (no GitHub release)

**Bug Fixes:**

- Fixed crash when GitHub release tag has unexpected format during update check
- Fixed potential crash when extracting post ID from malformed Fansly URLs
- Fixed timeline cursor navigation accessing unvalidated array index
- Fixed silent error swallowing in GUI - errors now logged to stderr if dialog fails
- Added 30-second timeout to all HTTP requests to prevent indefinite hangs
- Added 5-minute timeout to FFmpeg subprocess to prevent freezes on corrupted video
- Fixed unsafe URL file extension parsing - now uses proper URL parser with fallback

### 1.6.0 - 2026-01-24

**OnlyFans Messages Support:**

- **Message Downloads** - Download media from OnlyFans direct messages
  - Messages-only mode for downloading DMs without timeline posts
  - Normal mode downloads both timeline and messages
  - Message ID-based pagination (not timestamp-based)
  - Incremental mode support with last message ID tracking
  - Downloads to `CreatorName-of/Messages/` folder
  - Filename format: `msg_{message_id}_{media_id}.{ext}`
  - Supports photos, videos, GIFs (audio skipped by default)
  - Improved video URL extraction from `source` field
  - Better handling of paywall-locked content with clear warnings

**GUI Performance Improvements:**

- **Startup Optimization** - Significantly faster application startup
  - Lazy loading for OnlyFans tab (builds on first access)
  - Lazy loading for log window (creates on first show)
  - Reduced excessive logging during config loading
  - Minimal startup diagnostics
  - Deferred update check (5 seconds after startup)
- **UI Responsiveness** - Smoother interactions and reduced lag
  - Progress update throttling (max 10 updates/second)
  - Log message batching (150ms intervals)
  - Batched creator widget creation for large lists (100+ creators)
  - Optimized progress widget updates (only updates changed values)
  - Log window line limiting (1000 max lines) with conditional auto-scroll
  - Debounced creator section saves (500ms delay)
- **Overall Performance** - UI feels responsive immediately after startup
  - Startup time reduced from ~3-5 seconds to ~1-2 seconds
  - Tab switching is instant
  - Window resizing is smooth
  - Large creator lists load progressively without blocking UI

**Release Metadata:**

- Published on GitHub as tag `1.6.0`; local tags `1.6.0` and `v1.7.0` point to the same release commit

### 1.5.0 - 2026-01-03

**New Features:**

- **Single Post Download** - Download individual posts by URL or ID (both platforms)
  - GUI integration with dedicated input field and mode selection
  - Auto-detects creator from post - creates correct folder automatically
  - Works with existing deduplication - files go to Timeline folder
  - Supports both URL format and raw post ID input
- **Compression Preview** - Real-time estimated file size display without actual compression
- **Before/After Comparison** - Side-by-side slider to compare original vs compressed quality
  - Drag slider left/right to reveal differences
  - Zoom in/out (scroll wheel or +/- buttons) to inspect fine details
  - Pan when zoomed (right-click drag)
  - SSIM quality score with color-coded indicator
  - Smart PNG detection with lossless format warning
- **Advanced Compression Options** - Enhanced file size compression with quality preservation
  - **MozJPEG Optimization** - 10-15% smaller files at same quality using optimized encoding
  - **SSIM Quality Validation** - Warns when compression reduces perceptual quality below threshold
  - **Chroma Subsampling Control** - Choose between best quality (4:4:4), balanced (4:2:2), or smallest (4:2:0)
  - **Configurable Quality Floor** - Set minimum quality (60-90) to prevent over-compression
  - **Progressive JPEG** - Option for better web loading experience

**Improvements:**

- Removed plyvel-ci dependency for easier installation (auto-token extraction now optional)

### 1.3.0 - 2025-12-15

**New Features:**

- **Auto-update foundation** - Checks for a new version on startup with optional one-click install
- **Check for Update button** - Added a manual update check button in the status bar
- **Skip This Version** - Added an option to dismiss a specific update version

### 1.2.5 - 2025-12-15

**Improvements:**

- Added video and photo checkboxes on both the Fansly and OnlyFans sides
- Made backend maintenance changes

### 1.2.0 - 2025-12-04

**Major Addition:**

- **OnlyFans Support** - Full platform integration with a dedicated GUI tab and CLI (`onlyfans_downloader.py`)
  - Separate configuration system (`onlyfans_config.ini`)
  - Independent authentication and state management
  - Timeline downloads, account information, and built-in credential extraction guide

**New Features:**

- **Subscription Import** - Automatically import subscribed creators on both platforms
- **Post Limit Settings** - Configure initial download limits for new creators
- **Image Crop Tool** - Built-in bulk image cropping and batch processing

**Improvements:**

- Enhanced crop tool cursors, drag-to-create behavior, resize handles, aspect ratio handling, output browsing, filename preservation, and file size compression options
- Improved error handling and logging throughout

### 1.1.0 - 2025-11-30

**New Features:**

- **Image Crop Tool** - Built-in bulk image cropping and batch processing tool
  - Interactive crop canvas with real-time preview
  - Drag-and-drop image input
  - Custom aspect ratio presets with save/load support
  - Crop alignment options, batch processing, multiple export formats, quality control, smart conflict handling, and common image format support

### 1.0.1 - 2025-11-22

**Performance:**

- Improved startup time by roughly 1-1.5 seconds through lazy imports

**GUI Improvements:**

- Added an "Open Folder" button to open the download directory on demand
- Removed the "Open folder when done" checkbox
- Info-level log messages now appear in the in-app console

**Build:**

- Added application icon to the GUI executable

### 1.0 - 2025-11-16

**Initial Release:**

- Download timeline posts, messages, and collections from Fansly creators
- Modern GUI with dark theme and setup wizard
- Command-line interface for advanced users
- Automatic duplicate detection and smart file organization
- M3U8 streaming video support with automatic conversion
- Incremental downloads with per-creator progress tracking
- Smart rate limiting, automatic retry logic, detailed logging, graceful error handling, and flexible configuration

### Historical Releases

For the full GitHub release archive, see the [release archive](https://github.com/Frangus90/fansly-downloader-ng/releases).
