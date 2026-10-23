"""CI acceptance check of installed system code, without opening any device."""
import runpy
import sys
from pathlib import Path

installed = Path('/usr/share/tenshi')
sys.path.insert(0, str(installed))
entry = runpy.run_path(str(installed / 'main.py'))
assert entry['smoke_test']() == 0
from recoverydesk import gui
from recoverydesk.branding import asset_path

assert Path(gui.__file__).resolve().is_relative_to(installed)
assert asset_path('tenshi_icon.png').is_file()
app = gui.RecoveryDeskApp()
try:
    app.update()
    assert app.winfo_ismapped(), 'Installed application window was not displayed'
    assert len(app.tabs.tabs()) == 2
    for language in ('en', 'de'):
        app.change_language(language)
        app.update()
finally:
    app.destroy()
print('Installed Tenshi: assets, offline help, window and language switch OK')
