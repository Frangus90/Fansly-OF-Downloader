# Fansly Downloader NG

## 🗒️ Release Notes

### 1.6.0 (Unreleased)

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

### 1.5.0 2026-01-03

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

### Historical Releases

For detailed version history prior to 1.5.0, see the [full release archive](https://github.com/Frangus90/fansly-downloader-ng/releases).
