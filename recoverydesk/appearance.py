"""Sun Valley colors and bounded, read-only OS appearance detection.

The upstream theme data is unchanged. Load its two themes directly so its
global font-changing bindings do not replace Tenshi's existing typography.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
from tkinter import ttk

THEME_DATA = Path(__file__).with_name('assets') / 'sun_valley'


def apply_theme(root, mode):
    if mode not in ('light', 'dark'):
        raise ValueError('Unknown effective appearance')
    style = ttk.Style(root)
    if 'sun-valley-light' not in style.theme_names():
        # Names referenced inside the upstream Tcl files, with Tenshi's fonts.
        for name in ('SunValleyBodyFont', 'SunValleyCaptionFont'):
            root.tk.call('font', 'create', name, '-family', 'Segoe UI', '-size', 10)
        for name in ('light', 'dark'):
            root.tk.call('source', str(THEME_DATA / 'theme' / (name + '.tcl')))
    style.theme_use('sun-valley-' + mode)
    return style


def _command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=2,
                                check=False, env={**os.environ, 'LC_ALL': 'C'})
        return result.stdout.strip() if result.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError, UnicodeError):
        return ''


def _gtk_theme(value):
    value = value.strip("'\" \n").lower()
    if not value:
        return None
    return 'dark' if re.search(r'(?:^|[-_ ])dark(?:$|[-_ ])', value) else 'light'


def detect_system_theme():
    """Return light/dark or None; never query source media or require privileges."""
    if sys.platform == 'win32':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                return {0: 'dark', 1: 'light'}.get(value)
        except OSError:
            return None
    if not sys.platform.startswith('linux'):
        return None
    # The portal exposes host preferences even inside Flatpak, without extra
    # filesystem or general session-bus permissions. Read also supports v1.
    result = _command(['gdbus', 'call', '--session', '--dest',
        'org.freedesktop.portal.Desktop', '--object-path',
        '/org/freedesktop/portal/desktop', '--method',
        'org.freedesktop.portal.Settings.Read', 'org.freedesktop.appearance', 'color-scheme'])
    match = re.search(r'uint32\s+([012])\b', result)
    if match and match[1] in ('1', '2'):
        return {'1': 'dark', '2': 'light'}[match[1]]
    if os.environ.get('FLATPAK_ID'):
        return None
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    if 'cinnamon' in desktop:
        return _gtk_theme(_command(['gsettings', 'get', 'org.cinnamon.desktop.interface', 'gtk-theme']))
    if 'xfce' in desktop:
        return _gtk_theme(_command(['xfconf-query', '-c', 'xsettings', '-p', '/Net/ThemeName']))
    value = _command(['gsettings', 'get', 'org.gnome.desktop.interface', 'color-scheme'])
    if value.strip("'\"") in ('prefer-dark', 'prefer-light'):
        return 'dark' if 'dark' in value else 'light'
    return _gtk_theme(_command(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme']))


def palette(mode):
    if mode == 'dark':
        return dict(bg='#1c1c1c', panel='#292929', text='#fafafa', muted='#c5c5c5',
                    input='#202020', select='#2f60d8', selection_text='#ffffff',
                    inactive='#292929', inactive_fg='#fafafa', nav='#005fb8',
                    warning='#ffbb75', divider='#454545', accent='#57c8ff',
                    accent_text='#00324d', accent_active='#7cd5ff')
    return dict(bg='#fafafa', panel='#ffffff', text='#1c1c1c', muted='#606060',
                input='#ffffff', select='#2f60d8', selection_text='#ffffff',
                inactive='#e7e7e7', inactive_fg='#1c1c1c', nav='#005fb8',
                warning='#9a3412', divider='#d0d0d0', accent='#005fb8',
                accent_text='#ffffff', accent_active='#1975c5')
