"""Hardware-free Linux block-reader tests for 512/4096-byte sectors.

All /dev paths below are mocked. No test opens, mounts or writes a real disk.
"""
from __future__ import annotations

import errno
import io
import os
import sys
import unittest
from unittest import mock

from recoverydesk import imaging, sources


@unittest.skipUnless(sys.platform.startswith('linux'), 'Linux raw reader tests')
class LinuxReadOnlyBlockTests(unittest.TestCase):
    def test_mocked_block_source_opens_rb_and_reads_aligned(self):
        for sector in (512, 4096):
            with self.subTest(sector=sector):
                data = bytes(range(256)) * (sector * 3 // 256)

                class ReadOnlyFakeDisk(io.BytesIO):
                    def __init__(self, payload):
                        super().__init__(payload)
                        self.requests = []

                    def read(self, n=-1):
                        self.requests.append((self.tell(), n))
                        if self.tell() % sector or n <= 0 or n % sector:
                            raise AssertionError('Underlying block read not sector-aligned')
                        return super().read(n)

                    def write(self, value):
                        raise AssertionError('Source device write attempted')

                raw = ReadOnlyFakeDisk(data)
                path = '/dev/fake-tenshi-disk'
                with mock.patch.object(sources, 'validate_source', return_value=path), \
                     mock.patch.object(sources, 'is_device_source', return_value=True), \
                     mock.patch.object(sources, 'source_size', return_value=len(data)), \
                     mock.patch.object(sources, 'physical_sector_size', return_value=sector), \
                     mock.patch('builtins.open', return_value=raw) as opened:
                    with sources.open_source(path) as reader:
                        self.assertFalse(reader.writable())
                        self.assertFalse(hasattr(reader, 'write'))
                        reader.seek(13)
                        self.assertEqual(reader.read(37), data[13:50])
                        reader.seek(len(data) - 21)
                        self.assertEqual(reader.read(100), data[-21:])
                        self.assertEqual(reader.read(1), b'')
                    opened.assert_called_once_with(path, 'rb', buffering=0)
                self.assertTrue(raw.closed)
                self.assertTrue(raw.requests)

    def test_linux_read_failures_do_not_advise_windows_rights(self):
        for code, expected in ((errno.EINVAL, 'Sektorgroesse'),
                               (errno.EACCES, 'Geraeteberechtigungen'),
                               (errno.ENODEV, 'nicht mehr erreichbar')):
            with self.subTest(errno=code):
                class FailingDisk(io.BytesIO):
                    def read(self, n=-1):
                        raise OSError(code, 'simulated Linux failure')
                device = FailingDisk(bytes(8192))
                reader = sources.AlignedDeviceReader(device, 8192, 4096)
                with mock.patch.object(sources, 'log_issue'):
                    with self.assertRaises(OSError) as caught:
                        reader.read(512)
                self.assertIn(expected, str(caught.exception))
                self.assertNotIn('Windows', str(caught.exception))
                self.assertEqual(reader.tell(), 0)

    def test_disconnected_linux_source_does_not_zero_fill(self):
        class DisconnectedDisk:
            def seek(self, offset, whence=0):
                pass

            def read(self, count):
                raise OSError(errno.ENODEV, 'USB disconnected')

        bad_ranges = []
        retries = [0]
        with self.assertRaises(imaging.ImagingError):
            imaging._recover_read(DisconnectedDisk(), 0, 4096, 4096,
                                  bad_ranges, read_retries=3,
                                  retry_counter=retries)
        self.assertEqual(bad_ranges, [])
        self.assertEqual(retries, [0])


if __name__ == '__main__':
    unittest.main()
