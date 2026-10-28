import errno
import unittest
from recoverydesk.export_errors import export_error_message
from recoverydesk.i18n import LANGUAGES


class ExportErrorMessageTests(unittest.TestCase):
    def test_permission_readonly_and_unsupported_are_distinct(self):
        denied=export_error_message(PermissionError(errno.EACCES,'denied'))
        self.assertIn('Zugriff verweigert',denied)
        self.assertIn('Flatpak',denied)
        readonly=export_error_message(OSError(errno.EROFS,'read-only'))
        self.assertIn('schreibgeschützt',readonly)
        invalid=export_error_message(OSError(errno.EINVAL,'Invalid argument'))
        self.assertIn('kein eindeutiger Nachweis',invalid)
        self.assertIn('VM-Ordner',invalid)
        self.assertNotIn('Zugriff verweigert',invalid)

    def test_details_are_kept_and_hints_are_available_in_all_languages(self):
        for code in (errno.EACCES,errno.EPERM,errno.EROFS,errno.EINVAL,errno.ENOSPC,errno.ENOTSUP):
            error=OSError(code,'original diagnostic /path/never-translate')
            german=export_error_message(error)
            for language in LANGUAGES:
                with self.subTest(code=code,language=language):
                    message=export_error_message(error,language)
                    self.assertTrue(message.endswith(str(error)))
                    if language!='de':self.assertNotEqual(message,german)
        error=ValueError('Existing protection error')
        self.assertEqual(export_error_message(error),str(error))
