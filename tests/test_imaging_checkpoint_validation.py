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
