"""Checks for the path-based output branch, also exercised on native Windows."""
from contextlib import ExitStack, contextmanager
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from recoverydesk import imaging, secure_target


class PathOutputIdentityTests(unittest.TestCase):
    def test_image_reopen_rejects_replacement_before_truncate(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'source.raw'
            source.write_bytes(bytes(range(256)) * 4096)
            destination = root / 'copy.img'
            saved = root / 'created.img'
            protected = b'unrelated file must survive'
            opener = imaging.open_regular_output

            @contextmanager
            def swapped(path, mode, src, **kwargs):
                if mode == 'r+b':
                    destination.rename(saved)
                    destination.write_bytes(protected)
                with ExitStack() as stack:
                    with mock.patch.object(secure_target, '_linux', return_value=False):
                        handle = stack.enter_context(opener(path, mode, src, **kwargs))
                    yield handle

            with mock.patch.object(imaging, 'open_regular_output', side_effect=swapped):
                with self.assertRaisesRegex(ValueError, 'ausgetauscht'):
                    imaging.create_image(str(source), str(destination))
            self.assertEqual(destination.read_bytes(), protected)
            self.assertEqual(saved.read_bytes(), b'')
            self.assertEqual(source.read_bytes(), bytes(range(256)) * 4096)

    def test_matching_opened_identity_accepts_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.raw'
            destination = Path(folder) / 'copy.img'
            source.write_bytes(b'original')
            with mock.patch.object(secure_target, '_linux', return_value=False):
                with secure_target.open_regular_output(str(destination), 'xb', str(source)) as out:
                    st = os.fstat(out.fileno())
                    identity = st.st_dev, st.st_ino
                with secure_target.open_regular_output(str(destination), 'r+b', str(source),
                                                       expected_identity=identity) as out:
                    out.write(b'copy')
            self.assertEqual(destination.read_bytes(), b'copy')
            self.assertEqual(source.read_bytes(), b'original')

    def test_source_hardlink_is_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.raw'
            destination = Path(folder) / 'alias.img'
            source.write_bytes(b'original')
            os.link(source, destination)
            with mock.patch.object(secure_target, '_linux', return_value=False):
                with self.assertRaisesRegex(ValueError, 'dieselbe Datei'):
                    with secure_target.open_regular_output(str(destination), 'r+b', str(source)):
                        self.fail('source alias was exposed for writing')
            self.assertEqual(source.read_bytes(), b'original')
