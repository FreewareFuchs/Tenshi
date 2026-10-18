"""Regression checks for the streamlined RecoveryDesk GUI."""
import unittest
from pathlib import Path
from recoverydesk.gui import RecoveryDeskApp
import recoverydesk.core as core

class RemovedToolTests(unittest.TestCase):
    def test_removed_tabs_and_methods(self):
        for name in ("_build_carving", "start_carve", "recover_selected",
                     "_build_hex", "load_hex"):
            self.assertFalse(hasattr(RecoveryDeskApp, name), name)

    def test_removed_core_functions(self):
        for name in ("search_signatures", "recover_range", "read_bytes"):
            self.assertFalse(hasattr(core, name), name)
        self.assertTrue(callable(core.list_volumes))

    def test_tabs_and_preview(self):
        source = (Path(__file__).resolve().parents[1] / "recoverydesk" / "gui.py").read_text(encoding="utf-8")
        self.assertIn('text="Partitionen"', source)
        self.assertIn('text="Dateien & Ordner"', source)
        self.assertNotIn('text="Signatursuche (optional)"', source)
        self.assertNotIn('text="Sektor / Hex-Editor"', source)
        self.assertIn("def preview_entry(self):", source)

if __name__ == "__main__":
    unittest.main()
