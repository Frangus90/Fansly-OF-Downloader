# Fansly Downloader NG

## 🗒️ Release Notes

### 1.6.0 (Unreleased)

**Compression System Rewrite:**
- **Two-Mode Compression Panel** - Simplified Quick mode and powerful Advanced mode
  - Quick mode: Set target file size, auto-selects optimal format
  - Advanced mode: Full manual control over all settings
- **Modular Compression Architecture** - New `imageprocessing/compression/` package
  - Format-specific encoders with unified API
  - Strategy pattern for Quick vs Advanced workflows
  - FormatAdvisor for intelligent format selection
- **Enhanced Format Support** - JPEG, PNG, WebP, and AVIF (optional)
  - Automatic format availability detection
  - Graceful degradation when optional formats unavailable

**Improvements:**
- Refactored image processing pipeline for better maintainability
- Separated compression logic from crop settings UI
- Enhanced compression preview with real-time mode switching
- Updated dependencies for latest compression features

### 1.5.0 2026-01-04

**Major Addition:**
- **OnlyFans Support** - Full platform integration with dedicated GUI tab and CLI (`onlyfans_downloader.py`)
  - Separate configuration system (`onlyfans_config.ini`)
  - Independent authentication and state management
  - Timeline downloads and account information
  - Built-in credential extraction guide

**New Features:**
- **Single Post Download** - Download individual posts by URL or ID (both platforms)
- **Subscription Import** - Import all subscribed creators (both platforms)
- **Image Crop Tool** - Built-in bulk cropping and batch processing
  - Drag-and-drop support with interactive canvas
  - Custom aspect ratio presets and alignment
  - Compression preview with before/after slider
  - SSIM quality validation
  - Export to JPEG, PNG, WebP, AVIF (optional)

**Improvements:**
- Removed plyvel-ci dependency for easier installation

### Historical Releases

For detailed version history prior to 1.5.0, see the [full release archive](https://github.com/Frangus90/fansly-downloader-ng/releases).
