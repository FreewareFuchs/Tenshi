"""Regression tests for the Tenshi application startup function."""
import unittest
from unittest.mock import MagicMock, patch
from recoverydesk import gui


class TenshiStartTest(unittest.TestCase):
    def test_main_constructs_existing_application(self):
        fake_app = MagicMock()
        with patch.object(gui, "RecoveryDeskApp", return_value=fake_app) as cls:
            gui.main()
        cls.assert_called_once_with()
        fake_app.mainloop.assert_called_once_with()

    def test_title_and_logo_assets_present(self):
        from recoverydesk.branding import asset_path
        self.assertEqual(gui.APP_NAME, "Tenshi")
        self.assertTrue(asset_path("tenshi_logo.png").is_file())
        self.assertTrue(asset_path("tenshi_icon.png").is_file())


if __name__ == "__main__":
    unittest.main()
