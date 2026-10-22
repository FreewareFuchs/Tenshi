"""Bounded, fail-closed parsing of untrusted imaging checkpoint journals."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from recoverydesk import imaging


class JournalValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'checkpoint.journal'

    def test_oversized_records_rejected_with_or_without_newline(self):
        for ending in (b'', b'\n'):
            with self.subTest(ending=ending):
                self.path.write_bytes(b'x' * 129 + ending)
                with mock.patch.object(imaging, 'MAX_JOURNAL_RECORD_BYTES', 128):
                    with self.assertRaisesRegex(imaging.ImagingError, 'übergroßen'):
                        imaging._read_journal(str(self.path))

    def test_readline_is_bounded_before_allocating_record(self):
        class BoundedReader(io.BytesIO):
            def readline(self, size=-1):
                self.requested = size
                return super().readline(size)

        self.path.touch()
        stream = BoundedReader(b'x' * 1024)
        with mock.patch.object(imaging, 'MAX_JOURNAL_RECORD_BYTES', 128), \
             mock.patch('builtins.open', return_value=stream):
            with self.assertRaises(imaging.ImagingError):
                imaging._read_journal(str(self.path))
        self.assertEqual(stream.requested, 129)

    def test_invalid_checkpoint_shapes_are_rejected(self):
        for state in (None, [], 'bad', 123, {'processed': True},
                      {'processed': -1}, {'processed': 1.5}, {}):
            with self.subTest(state=state):
                # Correct checksum must not make an invalid checkpoint valid.
                self.path.write_bytes(imaging._journal_encoding(state))
                with self.assertRaisesRegex(imaging.ImagingError, 'beschädigten'):
                    imaging._read_journal(str(self.path))

    def test_invalid_record_shapes_are_rejected(self):
        for record in (None, [], 'bad', 123, {}, {'checkpoint': {}}):
            with self.subTest(record=record):
                self.path.write_text(json.dumps(record) + '\n')
                with self.assertRaises(imaging.ImagingError):
                    imaging._read_journal(str(self.path))

    def test_small_torn_tail_preserves_last_committed_offset(self):
        state = {'processed': 4096}
        committed = imaging._journal_encoding(state)
        self.path.write_bytes(committed + b'{"checkpoint":')
        self.assertEqual(imaging._read_journal(str(self.path)), (state, len(committed)))

    def test_deeply_nested_record_is_controlled_error(self):
        self.path.write_bytes(b'[' * 2000 + b']' * 2000 + b'\n')
        with self.assertRaises(imaging.ImagingError):
            imaging._read_journal(str(self.path))
