"""Build identity survives packaging and never mistakes unknown code for a release."""
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import main
from recoverydesk import __version__
from recoverydesk import version_info as identity


class IdentityTests(unittest.TestCase):
    def tearDown(self):
        identity.build_info.cache_clear()

    def test_embedded_identity_without_git_and_unknown_metadata_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / 'recoverydesk/version_info.py'
            module.parent.mkdir()
            path = module.with_name('_build_info.json')
            data = {'schema': 1, 'version': __version__, 'release': 'beta.5',
                    'commit': 'a' * 40, 'dirty': False, 'released': True}
            path.write_text(json.dumps(data))
            with patch.object(identity, '__file__', str(module)), patch.object(
                    identity.subprocess, 'check_output', side_effect=AssertionError('Git must not run')):
                self.assertEqual(identity.display_version(), '3.0.2 Beta.5 (aaaaaaaaaa)')
                for invalid in ('{}', 'not json', json.dumps({**data, 'commit': 'invalid'}),
                                json.dumps({**data, 'version': '0.0.0'}),
                                json.dumps({**data, 'dirty': True}), 'x' * 4097):
                    path.write_text(invalid)
                    identity.build_info.cache_clear()
                    self.assertIn('+dev (?)', identity.display_version())

    def test_cli_and_all_help_locales_show_same_identity(self):
        from recoverydesk.help_center import topic_text
        from recoverydesk.i18n import LANGUAGES
        info = identity.BuildInfo(commit='b' * 40)
        with patch.object(identity, 'build_info', return_value=info):
            out = io.StringIO()
            with patch('sys.stdout', out):
                self.assertEqual(main.main(['--version']), 0)
            self.assertEqual(out.getvalue(), f'Tenshi {info.display()}\n')
            for language in LANGUAGES:
                self.assertIn(info.display(), topic_text('about', language)[1])

    @unittest.skipUnless(shutil.which('git'), 'Git required for source identity test')
    def test_source_clean_dirty_tagged_and_archive_identities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args],
                                               stderr=subprocess.DEVNULL, text=True).strip()
            git('init')
            source = root / 'app.py'
            source.write_text('original')
            git('add', 'app.py')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                '-c', 'commit.gpgsign=false', 'commit', '-m', 'test')
            sha = git('rev-parse', 'HEAD')
            clean = identity.collect_build_info(root)
            self.assertEqual(clean.commit, sha)
            self.assertFalse(clean.released)
            self.assertIn('+dev', clean.display())
            git('tag', f'v{__version__}-beta.5')
            self.assertEqual(identity.collect_build_info(root).display(), f'3.0.2 Beta.5 ({sha[:10]})')
            source.write_text('modified')
            dirty = identity.collect_build_info(root)
            self.assertTrue(dirty.dirty)
            self.assertFalse(dirty.released)
            self.assertIn('+dirty', dirty.display())
            with self.assertRaises(ValueError):
                identity.collect_build_info(root, 'beta.5')
            child = root / 'archive'
            child.mkdir()
            self.assertIsNone(identity.collect_build_info(child).commit)
            with self.assertRaises(ValueError):
                identity.collect_build_info(child, 'beta.5')

    def test_windows_build_embeds_generated_metadata(self):
        root = Path(__file__).resolve().parents[1]
        script = (root / 'build_windows.bat').read_text()
        self.assertIn('write_build_info.py', script)
        self.assertIn('build/identity/recoverydesk/_build_info.json;recoverydesk', script)


if __name__ == '__main__':
    unittest.main()
