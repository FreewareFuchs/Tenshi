"""Check Windows build entrypoints and packaging without executing Windows shell."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class WindowsBuildScriptTests(unittest.TestCase):
    def test_build_does_not_run_failing_platform_specific_unit_tests(self):
        script = (ROOT / 'build_windows.bat').read_text(encoding='ascii')
        self.assertNotIn('unittest discover', script)
        self.assertIn('tenshi-build.log', script)
        self.assertIn('PyInstaller', script)

    def test_diagnostics_tests_are_independent_and_isolated(self):
        script = (ROOT / 'run_tests.bat').read_text(encoding='ascii')
        self.assertIn('unittest discover', script)
        self.assertIn('TENSHI_LOG_DIR', script)
        self.assertIn('tenshi-tests.log', script)

    def test_package_keeps_logo_icon_and_entrypoint(self):
        for rel in ['main.py', 'recoverydesk/assets/tenshi.ico',
                    'recoverydesk/assets/tenshi_logo.png',
                    'installer/Tenshi.iss']:
            self.assertTrue((ROOT / rel).is_file(), rel)

    def test_build_has_stage_specific_failures(self):
        script = (ROOT / 'build_windows.bat').read_text(encoding='ascii')
        for marker in ('env_failed', 'install_failed', 'build_failed', 'missing_exe'):
            self.assertIn(marker, script)

if __name__ == '__main__':
    unittest.main()
