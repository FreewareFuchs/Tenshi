"""Windows-backed VM shares refuse to unlink a file held open for readback."""
from contextlib import ExitStack, nullcontext
from io import BytesIO
import errno
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from recoverydesk import secure_target


class SharedChecksumCleanupTests(unittest.TestCase):
    def setup_share(self, stack, *, changed_after_close=False, payload=b'owned'):
        class Readback(BytesIO):
            def fileno(self):return 23
        stream=Readback(payload)
        stack.enter_context(patch.object(secure_target.sys,'platform','linux'))
        stack.enter_context(patch.object(secure_target,'secure_parent',return_value=nullcontext(7)))
        stack.enter_context(patch.object(secure_target.os,'O_NOFOLLOW',0,create=True))
        stack.enter_context(patch.object(secure_target.os,'O_NONBLOCK',0,create=True))
        stack.enter_context(patch.object(secure_target.os,'O_CLOEXEC',0,create=True))
        stack.enter_context(patch.object(secure_target.os,'open',return_value=23))
        stack.enter_context(patch.object(secure_target.os,'fdopen',return_value=stream))
        stack.enter_context(patch.object(secure_target,'_validate_output'))
        def named(*args,**kwargs):
            self.assertTrue(stream.closed, 'Identity must be checked again after closing')
            return SimpleNamespace(st_dev=1,st_ino=3 if changed_after_close else 2,st_mode=stat.S_IFREG)
        stack.enter_context(patch.object(secure_target.os,'stat',side_effect=named))
        def unlink(*args,**kwargs):
            if not stream.closed:raise OSError(errno.ETXTBSY,'Text file busy')
        remove=stack.enter_context(patch.object(secure_target.os,'unlink',side_effect=unlink))
        stack.enter_context(patch.object(secure_target,'sync_directory'))
        return stream,remove

    def test_own_readback_is_closed_before_shared_folder_unlink(self):
        with ExitStack() as stack:
            stream,remove=self.setup_share(stack)
            secure_target.remove_owned_output('file.sha256','source.img',(1,2),b'owned')
            self.assertTrue(stream.closed)
            remove.assert_called_once_with('file.sha256',dir_fd=7)

    def test_replaced_file_after_close_is_preserved(self):
        with ExitStack() as stack:
            _,remove=self.setup_share(stack,changed_after_close=True)
            with self.assertRaisesRegex(ValueError,'ausgetauscht'):
                secure_target.remove_owned_output('file.sha256','source.img',(1,2),b'owned')
            remove.assert_not_called()

    def test_changed_contents_are_preserved(self):
        with ExitStack() as stack:
            _,remove=self.setup_share(stack,payload=b'changed')
            with self.assertRaisesRegex(ValueError,'verändert'):
                secure_target.remove_owned_output('file.sha256','source.img',(1,2),b'owned')
            remove.assert_not_called()
