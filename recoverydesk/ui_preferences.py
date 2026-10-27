"""Persistent, validated display preferences for Tenshi.

Never store source devices, recovery filenames, or private file content.
UI settings share settings.json with the existing language setting.
"""
from __future__ import annotations
import json
import os
import re
import tempfile
from .i18n import settings_path

COLUMNS = ('#0', 'type', 'size', 'status', 'quality', 'mft', 'extension', 'modified', 'path')
PARTITION_COLUMNS = ('idx', 'scheme', 'confidence', 'offset', 'size', 'filesystem',
                     'usage', 'health', 'sector', 'type', 'name')
THEMES = ('system', 'light', 'dark')
_GEOMETRY_RE = re.compile(r'^(\d{3,4})x(\d{3,4})([+-]\d{1,5})([+-]\d{1,5})$')


def valid_geometry(value):
    if not isinstance(value, str):
        return None
    match = _GEOMETRY_RE.fullmatch(value)
    if not match:
        return None
    width, height = int(match[1]), int(match[2])
    if not 1024 <= width <= 4096 or not 650 <= height <= 2160:
        return None
    return value


def _valid_widths(values, allowed):
    if not isinstance(values, dict):
        return {}
    return {name: width for name, width in values.items()
            if name in allowed and type(width) is int and 60 <= width <= 1800}


def clean_ui_preferences(raw):
    if not isinstance(raw, dict):
        raw = {}
    split = raw.get('folder_ratio')
    return {
        'theme': raw.get('theme') if raw.get('theme') in THEMES else 'system',
        'geometry': valid_geometry(raw.get('geometry')),
        'folder_ratio': float(split) if type(split) in (float, int) and 0.22 <= split <= 0.66 else None,
        'files_columns': _valid_widths(raw.get('files_columns'), COLUMNS),
        'partitions_columns': _valid_widths(raw.get('partitions_columns'), PARTITION_COLUMNS),
        'maximized': raw.get('maximized') is True,
    }


def _read_settings():
    try:
        data = json.loads(settings_path().read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, TypeError, ValueError):
        return {}


def load_ui_preferences():
    return clean_ui_preferences(_read_settings().get('ui', {}))


def save_ui_preferences(changes):
    data = _read_settings()
    current = data.get('ui', {})
    if not isinstance(current, dict):
        current = {}
    data['ui'] = clean_ui_preferences({**current, **changes})
    destination = settings_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='tenshi-settings-', suffix='.tmp', dir=str(destination.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, destination)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
