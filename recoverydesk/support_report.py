"""Local support snapshot: fixed metadata fields and bounded aggregate error codes."""
from collections import Counter
from dataclasses import asdict
import json
import platform
import re
import sys

from .diagnostics import diagnostic_log_path
from .version_info import build_info

LOG_LIMIT = 128 * 1024
_RECORD = re.compile(
    r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR '
    r'operation=[\w-]{0,40} error=[A-Za-z_][A-Za-z_0-9]* code=(-?[0-9]{1,10}|-)'
    r'(?: (?:offset|length|processed|total|attempt)=(?:-?[0-9]+|True|False)| phase=\w+)* *')


def error_summary(path=None):
    """Read only a bounded log tail. Never copy raw lines, operations or exceptions."""
    try:
        with (path or diagnostic_log_path()).open('rb') as stream:
            stream.seek(0, 2)
            start = max(0, stream.tell() - LOG_LIMIT)
            stream.seek(start)
            raw = stream.read(LOG_LIMIT)
        if start:
            raw = raw.partition(b'\n')[2]
    except FileNotFoundError:
        return dict(state='missing', records=0, codes={})
    except OSError:
        return dict(state='unavailable', records=0, codes={})
    counts = Counter()
    records = 0
    for line in raw.decode('utf-8', 'replace').splitlines():
        match = _RECORD.fullmatch(line)
        if match:
            records += 1
            counts[match[1]] += 1
    return dict(state='tail' if start else 'complete', records=records, codes=dict(sorted(counts.items())))


def collect_report(*, language='de', tk_version='', window_system=''):
    """No source, user settings, environment dump, hostname, device enumeration or file list."""
    distro = {}
    if sys.platform.startswith('linux'):
        try:
            values = platform.freedesktop_os_release()
            distro = {key: values[key] for key in ('ID', 'VERSION_ID')
                      if re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', values.get(key, ''))}
        except OSError:
            pass
    return dict(schema=1, product='Tenshi', build=asdict(build_info()),
                system=dict(os=platform.system(), release=platform.release(),
                            architecture=platform.machine(), distribution=distro),
                runtime=dict(python=platform.python_version(), bits=64 if sys.maxsize > 2**32 else 32,
                             tk=tk_version, window_system=window_system),
                language=language if language in ('de', 'en', 'es', 'zh', 'ru', 'ja') else 'unknown',
                errors=error_summary(),
                scope='Local metadata snapshot; no paths, filenames, file contents or raw logs. '
                      'Error codes summarize only the current log tail, not the complete history.')


def report_text(report):
    return json.dumps(report, ensure_ascii=False, indent=2) + '\n'


def save_report(path, text, sources=()):
    """Never replace an existing file, including a selected source or log file."""
    from .sources import ensure_safe_destination
    for source in set(filter(None, sources)):
        ensure_safe_destination(source, str(path))
    with open(path, 'x', encoding='utf-8') as stream:
        stream.write(text)
