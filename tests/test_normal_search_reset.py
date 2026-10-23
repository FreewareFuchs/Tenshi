"""Normal empty search clears all criteria; advanced empty-name search remains usable."""
from types import SimpleNamespace
from unittest import TestCase, mock
from recoverydesk.gui import RecoveryDeskApp

class NormalSearchResetTests(TestCase):
    def test_empty_normal_search_resets_before_searching(self):
        for text in ('', '  '):
            calls = []
            app = SimpleNamespace(browser_search=SimpleNamespace(get=lambda: text),
                _clear_advanced_search=lambda: calls.append('reset'),
                _search_browser=lambda: calls.append('search'))
            RecoveryDeskApp._normal_search_browser(app)
            self.assertEqual(calls, ['reset', 'search'])
    def test_named_normal_search_preserves_advanced_filters(self):
        app = SimpleNamespace(browser_search=SimpleNamespace(get=lambda: 'BILD'),
            _clear_advanced_search=mock.Mock(), _search_browser=mock.Mock())
        RecoveryDeskApp._normal_search_browser(app)
        app._clear_advanced_search.assert_not_called()
        app._search_browser.assert_called_once_with()
