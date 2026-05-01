"""Tests for shared application version wiring."""

import unittest

import gui.state as gui_state
from app_version import APP_VERSION


class AppVersionTests(unittest.TestCase):
    def test_gui_states_use_shared_app_version(self):
        self.assertEqual(gui_state.DEFAULT_PROGRAM_VERSION, APP_VERSION)


if __name__ == "__main__":
    unittest.main()
