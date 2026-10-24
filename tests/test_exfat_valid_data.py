"""exFAT ValidDataLength: logical zero tail must not expose old media bytes."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from recoverydesk.filesystems import scan_tree, export_selection
from recoverydesk import batch_export
from recoverydesk.batch_export import export_batch
from recoverydesk.session_store import _encode_index, _decode_index, SessionError
from test_exfat_active_fat import dual_fat_image


def image(valid, contiguous=False, offset=0):
    raw = dual_fat_image(contiguous=contiguous, offset=offset)
    entry = offset + 32 * 512 + 64
    struct.pack_into('<Q', raw, entry + 40, valid)
    checksum = 0
    for i, byte in enumerate(raw[entry:entry + 96]):
        if i not in (2, 3):
            checksum = (((checksum & 1) << 15) + (checksum >> 1) + byte) & 0xffff
    struct.pack_into('<H', raw, entry + 2, checksum)
    return raw


class ExfatValidDataTests(unittest.TestCase):
    def test_export_preview_batch_and_resume_zero_undefined_tail(self):
        for contiguous in (False, True):
            for valid in (0, 1, 511, 512, 700, 1024):
                with self.subTest(contiguous=contiguous, valid=valid), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    source = root / 'source.img'
                    raw = image(valid, contiguous, offset=1024 * 1024)
                    source.write_bytes(raw)
                    index = scan_tree(str(source), offset=1024 * 1024)
                    entry = next(e for e in index.entries if e.name == 'chain.bin')
                    physical = b'A' * 512 + (b'X' if contiguous else b'B') * 512
                    expected = physical[:valid] + bytes(1024 - valid)
                    self.assertEqual(entry.valid_data_length, valid)
                    self.assertEqual(index.preview(str(source), entry), expected)
                    self.assertEqual(index.preview(str(source), entry, maximum=600), expected[:600])
                    output = root / 'out'
                    output.mkdir()
                    result = export_selection(str(source), index, [entry], str(output))
                    self.assertEqual(result.exported, 1, result.errors)
                    actual = (output / 'chain.bin').read_bytes()
                    self.assertEqual(len(actual), 1024)
                    self.assertEqual(hashlib.sha256(actual).digest(), hashlib.sha256(expected).digest())
                    if valid < 1024:
                        self.assertNotEqual(hashlib.sha256(actual).digest(), hashlib.sha256(physical).digest())
                    batch = export_batch(str(source), index, [entry], str(output))
                    self.assertEqual(batch.exported, 1, batch.errors)
                    status = json.loads(Path(batch.manifest).read_text(encoding='utf-8'))
                    self.assertEqual(status['results']['chain.bin']['valid_data_length'], valid)
                    self.assertEqual((Path(batch.root) / 'files' / 'chain.bin').read_bytes(), expected)
                    self.assertEqual(export_batch(str(source), index, [entry], str(output)).verified_existing, 1)
                    self.assertEqual(source.read_bytes(), raw)

    def test_session_preserves_valid_length_and_legacy_requires_rescan(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source.img'
            source.write_bytes(image(700))
            index = scan_tree(str(source))
            raw = _encode_index(index)
            restored = _decode_index(copy.deepcopy(raw), str(source))
            entry = next(e for e in restored.entries if e.name == 'chain.bin')
            self.assertEqual(restored.preview(str(source), entry), b'A' * 512 + b'B' * 188 + bytes(324))
            legacy = copy.deepcopy(raw)
            for row in legacy['entries']:
                row.pop('valid_data_length')
            restored = _decode_index(legacy, str(source))
            entry = next(e for e in restored.entries if e.name == 'chain.bin')
            self.assertFalse(entry.recoverable)
            with self.assertRaisesRegex(ValueError, 'ValidDataLength'):
                restored.preview(str(source), entry)
            for value in (-1, 1025, True, '700'):
                malformed = copy.deepcopy(raw)
                next(r for r in malformed['entries'] if r['name'] == 'chain.bin')['valid_data_length'] = value
                with self.assertRaises(SessionError):
                    _decode_index(malformed, str(source))

    def test_old_batch_with_wrong_tail_is_not_trusted_as_resumed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.img'
            source.write_bytes(image(700))
            index = scan_tree(str(source))
            entry = next(e for e in index.entries if e.name == 'chain.bin')
            target = root / 'exports'
            target.mkdir()
            old_identity = batch_export._identity(str(source), index)
            old_identity.pop('reader_semantics')
            wrong = b'A' * 512 + b'B' * 512
            with patch.object(batch_export, '_identity', return_value=old_identity), \
                    patch.object(index.volumes, 'iter_file', return_value=iter([wrong])):
                old = export_batch(str(source), index, [entry], str(target))
            self.assertEqual(old.exported, 1)
            corrected = export_batch(str(source), index, [entry], str(target))
            self.assertNotEqual(corrected.root, old.root)
            self.assertEqual(corrected.verified_existing, 0)
            self.assertEqual(corrected.exported, 1)
            self.assertEqual((Path(corrected.root) / 'files' / 'chain.bin').read_bytes(),
                             wrong[:700] + bytes(324))
            self.assertEqual((Path(old.root) / 'files' / 'chain.bin').read_bytes(), wrong)

    def test_invalid_valid_length_blocks_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source.img'
            source.write_bytes(image(1025))
            index = scan_tree(str(source))
            entry = next(e for e in index.entries if e.name == 'chain.bin')
            self.assertFalse(entry.recoverable)
