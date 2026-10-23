"""Reject damaged resume digests before opening the destination for writes."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from recoverydesk import imaging


class CheckpointValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.raw'
        self.source.write_bytes(bytes(range(256)) * 65)
        self.dest = self.root / 'copy.img'
        self.state = imaging.create_image(str(self.source), str(self.dest), block_size=4096)
        self.sidecar = Path(imaging.sidecar_path(self.dest))

    def reject(self, state):
        self.sidecar.write_text(json.dumps(state))
        before = self.dest.read_bytes()
        source_before = self.source.read_bytes()
        with mock.patch.object(imaging, 'open_regular_output') as output:
            with self.assertRaises(imaging.ImagingError):
                imaging.create_image(str(self.source), str(self.dest), resume=True)
            output.assert_not_called()
        self.assertEqual(self.dest.read_bytes(), before)
        self.assertEqual(self.source.read_bytes(), source_before)

    def test_invalid_first_and_last_digest_fields(self):
        for key in ('first', 'last'):
            for field, value in (('start', -1), ('start', '0'), ('start', True),
                                 ('length', 0), ('length', '4096'), ('length', True),
                                 ('length', 2**60), ('sha256', None),
                                 ('sha256', 'z' * 64), ('sha256', 'a' * 63)):
                with self.subTest(checkpoint=key, field=field, value=value):
                    state = copy.deepcopy(self.state)
                    state[key][field] = value
                    self.reject(state)

    def test_missing_or_non_object_digests(self):
        for key in ('first', 'last'):
            for value in (None, [], 'invalid', {}):
                with self.subTest(checkpoint=key, value=value):
                    state = copy.deepcopy(self.state)
                    state[key] = value
                    self.reject(state)

    def test_well_formed_but_wrong_block_range_is_rejected(self):
        for key in ('first', 'last'):
            with self.subTest(checkpoint=key):
                state = copy.deepcopy(self.state)
                state[key]['start'] += 1
                state[key]['length'] -= 1
                self.reject(state)

    def test_complete_final_partial_block_can_still_resume(self):
        state = imaging.create_image(str(self.source), str(self.dest), resume=True)
        self.assertEqual(state['verification']['status'], 'verified')
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())

    def test_missing_required_fields_are_rejected_before_writes(self):
        for key in ('first', 'last', 'state', 'bad_ranges', 'unreadable_bytes'):
            with self.subTest(key=key):
                state = copy.deepcopy(self.state)
                del state[key]
                self.reject(state)

    def test_invalid_error_ranges_are_rejected_before_writes(self):
        for ranges in (None, {}, [[0, 0]], [[-1, 1]], [[True, 1]],
                       [[0, True]], [[0, '1']], [[0, 2], [1, 2]],
                       [[4096, 1], [0, 1]], [[self.state['processed'], 1]]):
            with self.subTest(ranges=ranges):
                state = copy.deepcopy(self.state)
                state['bad_ranges'] = ranges
                self.reject(state)

    def test_inconsistent_error_counters_and_states_are_rejected(self):
        for field, value in (('unreadable_bytes', True), ('unreadable_bytes', 1),
                             ('unreadable_bytes', -1), ('state', 'unknown'),
                             ('state', None), ('state', [])):
            with self.subTest(field=field, value=value):
                state = copy.deepcopy(self.state)
                state[field] = value
                self.reject(state)
        state = copy.deepcopy(self.state)
        state['bad_ranges'] = [[0, 512]]
        self.reject(state)

    def test_zero_progress_checkpoint_can_resume(self):
        self.dest.unlink()
        self.sidecar.unlink()
        paused = imaging.create_image(str(self.source), str(self.dest),
                                      block_size=4096, cancel=lambda: True)
        self.assertEqual(paused['processed'], 0)
        self.assertEqual(paused['state'], 'paused')
        resumed = imaging.create_image(str(self.source), str(self.dest), resume=True)
        self.assertEqual(resumed['verification']['status'], 'verified')
        self.assertEqual(self.dest.read_bytes(), self.source.read_bytes())

    def test_consistent_error_map_remains_readable_without_verified_claim(self):
        state = copy.deepcopy(self.state)
        state['bad_ranges'] = [[0, 512], [4096, 512]]
        state['unreadable_bytes'] = 1024
        self.sidecar.write_text(json.dumps(state))
        resumed = imaging.create_image(str(self.source), str(self.dest), resume=True)
        self.assertEqual(resumed['bad_ranges'], state['bad_ranges'])
        self.assertEqual(resumed['unreadable_bytes'], 1024)
        self.assertEqual(resumed['verification']['status'], 'not_possible')

    def test_malformed_and_deeply_nested_json_never_opens_output(self):
        for payload in (b'{"processed":', b'\xff', b'[' * 2000 + b']' * 2000):
            with self.subTest(payload_length=len(payload)):
                self.sidecar.write_bytes(payload)
                before = self.dest.read_bytes()
                with mock.patch.object(imaging, 'open_regular_output') as output:
                    with self.assertRaises(imaging.ImagingError):
                        imaging.create_image(str(self.source), str(self.dest), resume=True)
                    output.assert_not_called()
                self.assertEqual(self.dest.read_bytes(), before)

    def test_oversized_status_file_is_rejected_before_writes(self):
        with mock.patch.object(imaging, 'MAX_MANIFEST_BYTES', 128):
            self.reject(self.state)

    def test_status_read_request_is_bounded(self):
        from contextlib import contextmanager
        import io

        class BoundedReader(io.BytesIO):
            def read(self, size=-1):
                self.requested = size
                return super().read(size)

        stream = BoundedReader(b'x' * 1024)

        @contextmanager
        def opener(*args):
            yield stream

        with mock.patch.object(imaging, 'MAX_MANIFEST_BYTES', 128), \
             mock.patch.object(imaging, 'open_regular_input', side_effect=opener):
            with self.assertRaisesRegex(imaging.ImagingError, 'Größe'):
                imaging._load_manifest(str(self.sidecar), str(self.dest), self.state['source'])
        self.assertEqual(stream.requested, 129)

    def test_invalid_base_progress_with_journal_is_controlled_error(self):
        journal = Path(imaging.journal_path(str(self.sidecar)))
        journal.write_bytes(imaging._journal_encoding(self.state))
        for value in (None, 'bad', [], True, -1):
            with self.subTest(value=value):
                state = copy.deepcopy(self.state)
                state['processed'] = value
                self.reject(state)
