"""Windows PhysicalDrive I/O regression tests, simulated, no real device access."""
from __future__ import annotations
import errno
import io
import sys
import unittest
from unittest.mock import patch

from recoverydesk.sources import AlignedDeviceReader, open_source
from recoverydesk.ntfs_browser import scan_ntfs_tree
from recoverydesk.filesystems import scan_tree
from test_browser import image_with_folders
from test_filesystems import fat_img, exfat_img, ext4_img


class RejectUnalignedDevice(io.BytesIO):
    """Mock Windows raw device: both seek offset and read size must align."""
    def __init__(self, content, sector_size):
        super().__init__(content)
        self.sector = sector_size
        self.requests = []
    def seek(self, offset, whence=0):
        if whence != 0 or offset % self.sector:
            raise OSError(errno.EINVAL, 'Invalid argument: unaligned device seek')
        return super().seek(offset, whence)
    def read(self, n=-1):
        if n < 0 or n % self.sector:
            raise OSError(errno.EINVAL, 'Invalid argument: unaligned read length')
        self.requests.append((self.tell(), n))
        return super().read(n)
    def write(self, _bytes):
        raise AssertionError('Quellmedium darf niemals beschrieben werden')


class PhysicalDriveReadTests(unittest.TestCase):
    def test_11_byte_ntfs_signature_and_odd_offsets(self):
        raw = bytearray(4*4096)
        raw[4096+3:4096+11] = b'NTFS    '
        device = RejectUnalignedDevice(bytes(raw), 4096)
        f = AlignedDeviceReader(device, len(raw), 4096)
        self.assertEqual(f.seek(4096), 4096)
        self.assertEqual(f.read(11)[3:11], b'NTFS    ')
        f.seek(4096+7)
        self.assertEqual(f.read(4), b'    ')
        self.assertEqual(f.tell(), 4107)
        self.assertTrue(all(off % 4096 == 0 and size % 4096 == 0 for off,size in device.requests))
        self.assertFalse(f.writable())
        self.assertFalse(hasattr(f, 'write'))

    def test_sector_boundary_large_chunks_and_end_of_disk(self):
        content = bytes(range(256)) * 256
        for sector in (512,4096):
            with self.subTest(sector=sector):
                d = RejectUnalignedDevice(content, sector)
                f = AlignedDeviceReader(d, len(content), sector)
                f.seek(4000)
                self.assertEqual(f.read(12000), content[4000:16000])
                f.seek(-15,2)
                self.assertEqual(f.read(100), content[-15:])
                self.assertEqual(f.read(12), b'')
                self.assertTrue(all(off%sector==0 and n%sector==0 for off,n in d.requests))

    def test_four_filesystems_through_open_source_physical(self):
        source = r'\\.\PhysicalDrive9'
        fixtures = [
            ('NTFS', image_with_folders(4096), 4096, 'Dokumente'),
            ('FAT32', fat_img(4096), 4096, 'DOCS'),
            ('exFAT', exfat_img(4096), 4096, 'folder'),
            ('ext4', ext4_img(4096), 4096, 'Ordner'),
        ]
        for fs, raw, offset, folder in fixtures:
            with self.subTest(fs=fs):
                self.assertEqual(len(raw)%4096, 0)
                def make_device(*_args, **_kwargs):
                    return RejectUnalignedDevice(raw, 4096)
                with (patch('recoverydesk.sources.validate_source', return_value=source),
                      patch('recoverydesk.sources.is_physical', return_value=True),
                      patch('recoverydesk.sources.open', make_device, create=True),
                      patch('recoverydesk.sources.source_size', return_value=len(raw)),
                      patch('recoverydesk.sources.physical_sector_size', return_value=4096)):
                    if fs == 'NTFS':
                        index = scan_ntfs_tree(source, partition_offset=offset)
                    else:
                        index = scan_tree(source, offset=offset)
                    names = [e.name for e in index.list_dir(5)]
                    self.assertIn(folder, names)

    def test_windows_read_failure_has_actionable_message(self):
        class FailingDevice(RejectUnalignedDevice):
            def read(self, n=-1):
                raise OSError(errno.EINVAL, 'Invalid argument')
        d = FailingDevice(bytes(65536), 4096)
        f = AlignedDeviceReader(d, 65536, 4096)
        expected = ('Linux hat den sektorausgerichteten Leseauftrag abgelehnt'
                    if sys.platform.startswith('linux') else
                    'Windows hat einen physikalischen Leseauftrag abgelehnt')
        with self.assertRaisesRegex(OSError, expected):
            f.read(11)

if __name__ == '__main__':
    unittest.main()
