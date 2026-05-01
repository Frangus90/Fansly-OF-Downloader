"""Tests for release-note driven release automation."""

import unittest

from build_exe import find_unreleased_release_notes, stamp_release_notes


class ReleaseNotesTests(unittest.TestCase):
    def test_finds_versioned_unreleased_section(self):
        content = """# Fansly Downloader NG

## Release Notes

### 1.8.8 - Unreleased

**Bug Fixes:**

- **Updater** - Downloads releases automatically

### 1.8.7 - 2026-04-29

**Bug Fixes:**

- Older entry
"""

        release_notes = find_unreleased_release_notes(content)

        self.assertEqual(release_notes.version, "1.8.8")
        self.assertEqual(
            release_notes.notes,
            "**Bug Fixes:**\n\n- **Updater** - Downloads releases automatically",
        )

    def test_rejects_plain_unreleased_heading_without_version(self):
        content = """# Fansly Downloader NG

## Release Notes

### Unreleased

- Missing version
"""

        with self.assertRaises(ValueError):
            find_unreleased_release_notes(content)

    def test_stamps_unreleased_heading_with_release_date(self):
        content = """# Fansly Downloader NG

## Release Notes

### 1.8.8 - Unreleased

- Release body

### 1.8.7 - 2026-04-29

- Older body
"""

        stamped = stamp_release_notes(content, "1.8.8", "2026-05-01")

        self.assertIn("### 1.8.8 - 2026-05-01", stamped)
        self.assertNotIn("### 1.8.8 - Unreleased", stamped)
        self.assertIn("### 1.8.7 - 2026-04-29", stamped)


if __name__ == "__main__":
    unittest.main()
