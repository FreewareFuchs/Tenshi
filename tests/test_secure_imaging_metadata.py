"""Resume metadata stays bound to its opened Linux directory; no raw devices."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from recoverydesk import imaging


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux directory descriptors')
class ImagingMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.raw'
        self.source.write_bytes(bytes(range(256)) * 32)
        self.output = self.root / 'output'
        self.output.mkdir()
        self.destination = self.output / 'copy.img'
        self.state = imaging.create_image(str(self.source), str(self.destination))
        self.manifest = Path(imaging.sidecar_path(self.destination))

    def test_resume_manifest_parent_swap_reads_original_and_refuses_changed_destination(self):
        original = self.root / 'original-output'
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / self.manifest.name).write_text('{}')
        real_open = os.open
        swapped = []

        def swap(name, flags, *args, **kwargs):
            if name == self.manifest.name and kwargs.get('dir_fd') is not None and not swapped:
                self.output.rename(original)
                self.output.symlink_to(outside, target_is_directory=True)
                swapped.append(True)
            return real_open(name, flags, *args, **kwargs)

        loaded = []
        real_load = json.loads

        def record_load(stream):
            value = real_load(stream)
            loaded.append(value)
            return value

        with mock.patch('recoverydesk.secure_target.os.open', side_effect=swap), \
             mock.patch('recoverydesk.imaging.json.loads', side_effect=record_load):
            with self.assertRaisesRegex(imaging.ImagingError, 'Fortsetzung verweigert'):
                imaging._load_manifest(str(self.manifest), str(self.destination), self.state['source'])
        self.assertEqual(swapped, [True])
        self.assertEqual(loaded, [self.state])
        self.assertEqual((outside / self.manifest.name).read_text(), '{}')

    def test_manifest_swapped_to_symlink_after_precheck_is_rejected(self):
        victim = self.root / 'victim.json'
        victim.write_text(json.dumps(self.state))
        real_open = os.open

        def swap(name, flags, *args, **kwargs):
            if name == self.manifest.name and kwargs.get('dir_fd') is not None:
                self.manifest.unlink()
                self.manifest.symlink_to(victim)
            return real_open(name, flags, *args, **kwargs)

        with mock.patch('recoverydesk.secure_target.os.open', side_effect=swap):
            with self.assertRaises(imaging.ImagingError):
                imaging._load_manifest(str(self.manifest), str(self.destination), self.state['source'])
        self.assertEqual(json.loads(victim.read_text()), self.state)

    def test_fifo_manifest_is_rejected_without_waiting_for_writer(self):
        self.manifest.unlink()
        os.mkfifo(self.manifest)
        with self.assertRaises(imaging.ImagingError):
            imaging._load_manifest(str(self.manifest), str(self.destination), self.state['source'])

    def test_journal_parent_swap_reads_original_record(self):
        journal = Path(imaging.journal_path(str(self.manifest)))
        journal.write_bytes(imaging._journal_encoding(self.state))
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / journal.name).write_bytes(b'invalid\n')
        original = self.root / 'original-output'
        real_open = os.open
        swapped = []

        def swap(name, flags, *args, **kwargs):
            if name == journal.name and kwargs.get('dir_fd') is not None and not swapped:
                self.output.rename(original)
                self.output.symlink_to(outside, target_is_directory=True)
                swapped.append(True)
            return real_open(name, flags, *args, **kwargs)

        with mock.patch('recoverydesk.secure_target.os.open', side_effect=swap):
            state, end = imaging._read_journal(str(journal), source=str(self.source))
        self.assertEqual(swapped, [True])
        self.assertEqual(state, self.state)
        self.assertEqual(end, len(imaging._journal_encoding(self.state)))
        self.assertEqual((outside / journal.name).read_bytes(), b'invalid\n')
