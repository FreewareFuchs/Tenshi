"""Volume-driver boundary simulation; no real disks or admin rights needed."""
import ctypes
import errno
import io
import unittest
from unittest.mock import MagicMock, patch

from recoverydesk import sources, partition_scan


class VolumeDriver(io.BytesIO):
    def __init__(self, data, filesystem_size, sector):
        super().__init__(data)
        self.partition_size = len(data)
        self.filesystem_size = filesystem_size
        self.sector = sector
        self.allow_tail = False
        self.requests = []

    def read(self, size=-1):
        position = self.tell()
        assert size > 0 and position % self.sector == 0 and size % self.sector == 0
        assert position + size <= self.partition_size, 'Read beyond partition boundary'
        self.requests.append((position, size))
        if not self.allow_tail:
            size = max(0, min(size, self.filesystem_size-position))
        return super().read(size)

    def write(self, data):
        raise AssertionError('Writing to source')


class WindowsVolumeTailTests(unittest.TestCase):
    def test_unconfigured_volume_reproduces_short_read_at_tail(self):
        driver = VolumeDriver(bytes(8192), 4096, 512)
        reader = sources.AlignedDeviceReader(driver, 8192, 512)
        reader.seek(8192-512)
        with self.assertRaisesRegex(OSError, 'unvollstaendigen'):
            reader.read(512)
        self.assertEqual(driver.requests, [(7680, 512)])
        self.assertEqual(reader.tell(), 7680)

    def test_volume_setup_uses_existing_handle_and_no_input_output_buffers(self):
        registry = MagicMock()
        registry.get_osfhandle.return_value = 123
        raw = MagicMock()
        raw.fileno.return_value = 17
        kernel = MagicMock()
        kernel.DeviceIoControl.return_value = True
        with patch.dict('sys.modules', {'msvcrt': registry}), patch.object(sources, '_kernel', return_value=kernel):
            sources._enable_volume_tail_reads(raw)
        registry.get_osfhandle.assert_called_once_with(17)
        args = kernel.DeviceIoControl.call_args.args
        self.assertEqual(args[:6], (123, sources._FSCTL_ALLOW_EXTENDED_DASD_IO, None, 0, None, 0))
        self.assertIsNone(args[7])
        kernel.CreateFileW.assert_not_called()
        raw.read.assert_not_called()
        raw.write.assert_not_called()

    def test_complete_partition_analysis_with_filesystem_smaller_than_partition(self):
        # Both 512-byte and 4Kn partitions, including bytes outside filesystem
        # clusters. Their contents must remain readable, never replaced by zeros.
        for sector in (512, 4096):
            data = bytes(range(256)) * (65536//256)
            driver = VolumeDriver(data, len(data)-4096, sector)
            def enable(raw):
                self.assertIs(raw, driver)
                raw.allow_tail = True
            with patch.object(sources.os, 'name', 'nt'), \
                 patch.object(sources, 'source_size', return_value=len(data)), \
                 patch.object(partition_scan, 'source_size', return_value=len(data)), \
                 patch.object(sources, 'physical_sector_size', return_value=sector), \
                 patch.object(sources, '_enable_volume_tail_reads', side_effect=enable) as setup, \
                 patch('builtins.open', return_value=driver) as opened:
                report = partition_scan.analyze_image(r'\\.\C:', sector_size=sector)
            setup.assert_called_once_with(driver)
            opened.assert_called_once_with(r'\\.\C:', 'rb', buffering=0)
            self.assertEqual(report.image_size, len(data))
            self.assertIn((len(data)-sector, sector), driver.requests)
            self.assertTrue(driver.closed)

    def test_tail_contents_and_partition_bounds_remain_exact(self):
        for sector in (512,4096):
            data = bytes(range(256))*256
            driver = VolumeDriver(data,len(data)-4096,sector)
            driver.allow_tail = True
            reader = sources.AlignedDeviceReader(driver,len(data),sector)
            reader.seek(-511,2)
            self.assertEqual(reader.read(1024),data[-511:])
            self.assertEqual(reader.read(512),b'')
            self.assertFalse(reader.writable())
            self.assertFalse(hasattr(reader,'write'))

    def test_failed_setup_closes_volume_without_yielding_reader(self):
        raw = io.BytesIO(bytes(8192))
        with patch.object(sources.os,'name','nt'), \
             patch('builtins.open',return_value=raw), \
             patch.object(sources,'_enable_volume_tail_reads',side_effect=OSError('unsupported')), \
             patch.object(sources,'source_size') as size:
            with self.assertRaisesRegex(OSError,'unsupported'):
                with sources.open_source(r'\\.\C:'):
                    self.fail('Unconfigured reader yielded')
        self.assertTrue(raw.closed)
        size.assert_not_called()

    def test_setup_failure_is_reported_instead_of_silently_ignored(self):
        kernel = MagicMock()
        kernel.DeviceIoControl.return_value = False
        registry = MagicMock()
        with patch.dict('sys.modules',{'msvcrt':registry}), \
             patch.object(sources,'_kernel',return_value=kernel), \
             patch.object(ctypes,'WinError',create=True,return_value=OSError('denied')), \
             patch.object(ctypes,'get_last_error',create=True,return_value=5), \
             patch.object(sources,'log_issue') as logged:
            with self.assertRaisesRegex(OSError,'Volume-Sektoren'):
                sources._enable_volume_tail_reads(MagicMock())
        logged.assert_called_once()

    def test_physical_disks_and_image_files_do_not_get_volume_control(self):
        for path in (r'\\.\PhysicalDrive0','fixture.img'):
            raw = io.BytesIO(bytes(8192))
            with patch.object(sources.os,'name','nt'), \
                 patch.object(sources,'validate_source'), patch('builtins.open',return_value=raw), \
                 patch.object(sources,'source_size',return_value=8192), \
                 patch.object(sources,'physical_sector_size',return_value=512), \
                 patch.object(sources,'_enable_volume_tail_reads') as setup:
                with sources.open_source(path) as reader:
                    self.assertEqual(reader.read(512),bytes(512))
            setup.assert_not_called()

    def test_genuine_short_read_still_aborts_after_volume_configuration(self):
        class Faulty(VolumeDriver):
            def read(self,size=-1):
                return super().read(size)[:-1]
        raw = Faulty(bytes(8192),4096,512)
        raw.allow_tail=True
        reader=sources.AlignedDeviceReader(raw,8192,512)
        reader.seek(7680)
        with self.assertRaises(OSError) as failure:
            reader.read(512)
        self.assertEqual(failure.exception.errno,errno.EINVAL)
        self.assertEqual(reader.tell(),7680)
