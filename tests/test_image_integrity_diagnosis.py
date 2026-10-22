"""Forensic comparison never modifies test evidence or opens special files."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from diagnose_image_integrity import compare_images, main


class ImageIntegrityDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.a = Path(self.tmp.name) / 'source.raw'
        self.b = Path(self.tmp.name) / 'copy.img'
        self.data = bytes(2 * 1024 * 1024 + 31)
        self.a.write_bytes(self.data)
        self.b.write_bytes(self.data)

    def test_identical_full_files_and_readonly_open_flags(self):
        with mock.patch('diagnose_image_integrity.os.open', wraps=os.open) as opener:
            result = compare_images(self.a, self.b)
        self.assertTrue(result['identical'])
        self.assertTrue(result['repeatable'])
        self.assertTrue(result['metadata_unchanged'])
        for call in opener.call_args_list:
            self.assertEqual(call.args[1] & os.O_ACCMODE, os.O_RDONLY)

    def test_original_style_corruption_is_counted_and_repeatable(self):
        offsets = [1024 * 1024 + 2, 1024 * 1024 + 10, 1024 * 1024 + 18]
        with self.b.open('r+b') as stream:
            for offset, value in zip(offsets, (8, 16, 8)):
                stream.seek(offset); stream.write(bytes([value]))
        before = self.b.read_bytes()
        result = compare_images(self.a, self.b)
        self.assertFalse(result['identical'])
        self.assertTrue(result['repeatable'])
        record = result['passes'][0]
        self.assertEqual(record['different_bytes'], 3)
        self.assertEqual(record['different_blocks'], 1)
        self.assertEqual(record['first_difference'], offsets[0])
        self.assertEqual(record['last_difference'], offsets[-1])
        self.assertEqual([s['modulo_8'] for s in record['samples']], [2, 2, 2])
        self.assertEqual(self.a.read_bytes(), self.data)
        self.assertEqual(self.b.read_bytes(), before)

    def test_bounded_window_and_different_lengths(self):
        with self.b.open('ab') as stream:
            stream.write(b'extra')
        result = compare_images(self.a, self.b)
        self.assertEqual(result['passes'][0]['different_bytes'], 5)
        self.assertEqual(result['passes'][0]['first_difference'], len(self.data))
        self.assertTrue(compare_images(self.a, self.b, offset=10, length=20)['identical'])

    def test_same_file_links_and_fifo_are_rejected(self):
        with self.assertRaises(ValueError):
            compare_images(self.a, self.a)
        if os.name != 'nt':
            link = self.a.parent / 'link'
            link.symlink_to(self.a)
            with self.assertRaises(ValueError):
                compare_images(self.a, link)
            fifo = self.a.parent / 'fifo'
            os.mkfifo(fifo)
            with self.assertRaises(ValueError):
                compare_images(self.a, fifo)

    def test_mutation_between_passes_is_reported(self):
        original = os.stat
        changed = []
        target_stats = []
        def swap(path, *args, **kwargs):
            info = original(path, *args, **kwargs)
            if Path(path) == self.b:
                target_stats.append(True)
                if len(target_stats) == 2 and not changed:
                    self.b.write_bytes(b'X' + self.data[1:])
                    changed.append(True)
            return info
        with mock.patch('diagnose_image_integrity.os.stat', side_effect=swap):
            result = compare_images(self.a, self.b)
        self.assertFalse(result['repeatable'])
        self.assertFalse(result['identical'])

    def test_cli_exit_status_and_invalid_arguments(self):
        with mock.patch('builtins.print'):
            self.assertEqual(main([str(self.a), str(self.b)]), 0)
            self.b.write_bytes(b'bad')
            self.assertEqual(main([str(self.a), str(self.b)]), 1)
            self.assertEqual(main([str(self.a), str(self.b), '--passes', '0']), 2)
