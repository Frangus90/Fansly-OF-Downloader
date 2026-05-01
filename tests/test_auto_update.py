"""Tests for GUI auto-update release asset selection."""

import unittest
from pathlib import Path
from unittest.mock import patch

from updater.auto_update import check_for_update, create_windows_update_script


def make_asset(name, url, created_at="2026-05-01T12:00:00Z", downloads=3):
    return {
        "name": name,
        "browser_download_url": url,
        "created_at": created_at,
        "download_count": downloads,
    }


class AutoUpdateTests(unittest.TestCase):
    @patch("updater.auto_update.platform.system", return_value="Windows")
    @patch("updater.auto_update.get_release_info_from_github")
    def test_selects_versioned_windows_zip_and_keeps_full_release_notes(
        self, get_release_info, _platform_system
    ):
        body = "## What's Changed\n\n" + ("- Detailed release note\n" * 40)
        get_release_info.return_value = {
            "draft": False,
            "prerelease": False,
            "tag_name": "v1.8.8",
            "body": body,
            "assets": [
                make_asset("fansly-downloader-ng-source.zip", "https://example/source.zip"),
                make_asset(
                    "FanslyOFDownloaderNG-Windows-x64-v1.8.8.zip",
                    "https://example/windows.zip",
                    downloads=9,
                ),
            ],
        }

        update = check_for_update("1.8.7")

        self.assertIsNotNone(update)
        self.assertEqual(update.version, "1.8.8")
        self.assertEqual(update.download_url, "https://example/windows.zip")
        self.assertEqual(update.release_name, "FanslyOFDownloaderNG-Windows-x64-v1.8.8.zip")
        self.assertEqual(update.download_count, 9)
        self.assertEqual(update.release_notes, body)

    @patch("updater.auto_update.platform.system", return_value="Windows")
    @patch("updater.auto_update.get_release_info_from_github")
    def test_accepts_legacy_windows_zip_name_as_fallback(self, get_release_info, _platform_system):
        get_release_info.return_value = {
            "draft": False,
            "prerelease": False,
            "tag_name": "v1.8.8",
            "body": "Legacy asset release",
            "assets": [
                make_asset("FanslyOFDownloaderNG.zip", "https://example/legacy.zip"),
            ],
        }

        update = check_for_update("1.8.7")

        self.assertIsNotNone(update)
        self.assertEqual(update.download_url, "https://example/legacy.zip")
        self.assertEqual(update.release_name, "FanslyOFDownloaderNG.zip")

    def test_windows_zip_update_script_preserves_user_configs(self):
        script_path = create_windows_update_script(
            Path(r"C:\Apps\FanslyOFDownloaderNG\FanslyOFDownloaderNG.exe"),
            Path(r"C:\Temp\FanslyOFDownloaderNG-Windows-x64-v1.8.8.zip"),
        )

        try:
            script = script_path.read_text()
        finally:
            script_path.unlink(missing_ok=True)

        self.assertIn("fansly_update_preserve", script)
        self.assertIn("config.ini", script)
        self.assertIn("onlyfans_config.ini", script)
        self.assertLess(script.index("fansly_update_preserve"), script.index("xcopy /s /y /q"))
        self.assertGreater(script.rindex("onlyfans_config.ini"), script.index("xcopy /s /y /q"))


if __name__ == "__main__":
    unittest.main()
