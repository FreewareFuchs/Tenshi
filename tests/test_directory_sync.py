"""Shared-folder directory sync limitations must not masquerade as write failures."""
import errno
import stat
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from recoverydesk import secure_target


class DirectorySyncTests(unittest.TestCase):
    def setUp(self):
        secure_target._note_unsupported_directory_sync.cache_clear()
        self.addCleanup(secure_target._note_unsupported_directory_sync.cache_clear)
        info=SimpleNamespace(st_mode=stat.S_IFDIR,st_dev=123)
        p=patch.object(secure_target.os,'fstat',return_value=info)
        p.start();self.addCleanup(p.stop)

    def test_supported_directory_sync_is_performed(self):
        with patch.object(secure_target.os,'fsync') as sync:
            self.assertTrue(secure_target.sync_directory(42))
        sync.assert_called_once_with(42)

    def test_only_unsupported_directory_sync_is_nonfatal_and_logged_once(self):
        for code in {errno.EINVAL,errno.ENOTSUP,errno.EOPNOTSUPP,errno.ENOSYS}:
            with self.subTest(code=code),patch.object(secure_target.os,'fsync',side_effect=OSError(code,'unsupported')),patch('recoverydesk.diagnostics.log_issue') as log:
                self.assertFalse(secure_target.sync_directory(42))
                self.assertFalse(secure_target.sync_directory(42))
                log.assert_called_once()

    def test_real_io_space_and_permission_errors_remain_fatal(self):
        for code in (errno.EIO,errno.ENOSPC,errno.EACCES,errno.EPERM,errno.EROFS,errno.EBADF):
            with self.subTest(code=code),patch.object(secure_target.os,'fsync',side_effect=OSError(code,'failure')):
                with self.assertRaises(OSError) as failure:secure_target.sync_directory(42)
                self.assertEqual(failure.exception.errno,code)

    def test_regular_file_cannot_use_directory_fallback(self):
        with patch.object(secure_target.os,'fstat',return_value=SimpleNamespace(st_mode=stat.S_IFREG)),patch.object(secure_target.os,'fsync') as sync:
            with self.assertRaises(ValueError):secure_target.sync_directory(42)
            sync.assert_not_called()
