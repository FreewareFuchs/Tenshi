"""Tenshi 3.0.2: USB / Windows-device failure simulations and read-only safety."""
import errno
import io
import json
from contextlib import redirect_stdout
import unittest
from unittest.mock import patch

from recoverydesk.sources import AlignedDeviceReader, ensure_safe_destination
from recoverydesk.imaging import _recover_read, ImagingError
import windows_preflight


class SyntheticDevice(io.BytesIO):
    def __init__(self, content: bytes, sector=4096):
        super().__init__(content)
        self.sector = sector
        self.calls = []

    def read(self, n=-1):
        self.calls.append((self.tell(), n))
        assert self.tell() % self.sector == 0
        assert 0 < n <= 256 * 1024 and n % self.sector == 0
        return super().read(n)

    def write(self, content):
        raise AssertionError('Write to a source device!')


class FailedDevice(SyntheticDevice):
    def __init__(self, content, error_code):
        super().__init__(content)
        self.error_code = error_code

    def read(self, n=-1):
        exc = OSError(errno.EIO, 'simulated windows device problem')
        exc.winerror = self.error_code
        raise exc


class USBDeviceHandlingTests(unittest.TestCase):
    def test_small_metadata_request_does_not_read_ahead_64k(self):
        d = SyntheticDevice(bytes(128 * 1024))
        f = AlignedDeviceReader(d, 128 * 1024, 4096)
        self.assertEqual(f.read(11), bytes(11))
        self.assertEqual(d.calls, [(0, 4096)])
        f.seek(13)
        self.assertEqual(f.read(32), bytes(32))
        self.assertEqual(d.calls, [(0, 4096)], 'reuse already read sector')

    def test_larger_reads_are_bounded_and_exact(self):
        data = bytes(range(256)) * 3584
        device = SyntheticDevice(data)
        reader = AlignedDeviceReader(device, len(data), 4096)
        self.assertEqual(reader.read(len(data)), data)
        self.assertTrue(all(size <= 256 * 1024 for _, size in device.calls))
        self.assertFalse(reader.writable())
        self.assertFalse(hasattr(reader, 'write'))

    def test_short_read_fails_closed_without_advancing_position(self):
        class ShortDevice(SyntheticDevice):
            def read(self, n=-1):
                return super().read(n)[:n // 2]
        d = ShortDevice(bytes(128 * 1024))
        reader = AlignedDeviceReader(d, 128 * 1024, 4096)
        with self.assertRaisesRegex(OSError, 'unvollstaendigen') as caught:
            reader.read(4096)
        self.assertEqual(caught.exception.errno, errno.EINVAL)
        self.assertEqual(reader.tell(), 0)

    def test_zero_length_response_is_not_eof(self):
        class MissingDevice(SyntheticDevice):
            def read(self, n=-1):
                return b''
        reader = AlignedDeviceReader(MissingDevice(bytes(4096)), 4096, 4096)
        with self.assertRaises(OSError) as caught:
            reader.read(11)
        self.assertEqual(caught.exception.errno, errno.EINVAL)

    def test_short_usb_read_aborts_imaging_without_zero_filling(self):
        class ShortDevice(SyntheticDevice):
            def read(self, n=-1):
                return super().read(n)[:-1]
        reader = AlignedDeviceReader(ShortDevice(bytes(4096)), 4096, 4096)
        bad = []
        with self.assertRaises(ImagingError):
            _recover_read(reader, 0, 4096, 4096, bad, strict_short_read=True)
        self.assertEqual(bad, [])

    def test_usb_disconnected_errors_are_not_media_errors(self):
        for error_code in (21, 31, 55, 433, 1167):
            with self.subTest(code=error_code):
                reader = AlignedDeviceReader(FailedDevice(bytes(4096), error_code), 4096, 4096)
                bad = []
                with self.assertRaises(ImagingError):
                    _recover_read(reader, 0, 4096, 4096, bad, strict_short_read=True)
                self.assertEqual(bad, [])

    def test_access_denied_is_fatal_not_bad_sector(self):
        for code in (5, 32, 33):
            with self.subTest(code=code):
                reader = AlignedDeviceReader(FailedDevice(bytes(4096), code), 4096, 4096)
                with self.assertRaises(PermissionError):
                    reader.read(32)

    def test_confirmed_media_error_remains_classified_as_media_error(self):
        for code in (23, 1117):
            with self.subTest(code=code):
                reader = AlignedDeviceReader(FailedDevice(bytes(4096), code), 4096, 4096)
                bad = []
                result = _recover_read(reader, 0, 4096, 4096, bad, strict_short_read=True)
                self.assertEqual(result, bytes(4096))
                self.assertEqual(bad, [[0, 4096]])

    def test_destination_does_not_overlap_source_disk_even_spanned_volume(self):
        with patch('recoverydesk.sources.volume_disk_numbers', return_value={7, 11}), \
             patch('recoverydesk.sources.disk_numbers_of_destination', return_value={11}):
            with self.assertRaisesRegex(ValueError, 'denselben physischen'):
                ensure_safe_destination(r'\\.\Q:', 'C:\\Export\\image.raw')


class WindowsPreflightTests(unittest.TestCase):
    def test_preflight_does_not_enumerate_or_open_physical_drives(self):
        with patch('recoverydesk.sources.open_source', side_effect=AssertionError('raw disk opened')), \
             patch('recoverydesk.sources.list_physical_sources', side_effect=AssertionError('raw enumerated')), \
             patch.object(windows_preflight.platform, 'system', return_value='Windows'), \
             patch.object(windows_preflight, '_admin_status', return_value=False):
            info = windows_preflight.gather_report()
        self.assertTrue(info['passed'])
        self.assertFalse(info['administrator'])
        self.assertFalse(info['raw_disk_access_tested'])
        self.assertFalse(info['usb_source_tested'])
        self.assertNotIn('C:\\', json.dumps(info))

    def test_nongenuine_windows_platform_does_not_claim_validated(self):
        with patch.object(windows_preflight.platform, 'system', return_value='Linux'):
            info = windows_preflight.gather_report()
        self.assertFalse(info['passed'])
        self.assertFalse(info['checks']['windows'])

    def test_test_report_stdout_is_json_and_no_private_path(self):
        buffer = io.StringIO()
        with patch.object(windows_preflight.platform, 'system', return_value='Windows'), \
             patch.object(windows_preflight, '_admin_status', return_value=None), \
             redirect_stdout(buffer):
            self.assertEqual(windows_preflight.main([]), 0)
        obj = json.loads(buffer.getvalue())
        self.assertEqual(obj['tenshi_version'], '3.0.2')
        self.assertFalse(obj['installer_tested'])


if __name__ == '__main__':
    unittest.main()
