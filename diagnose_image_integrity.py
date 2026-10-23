"""Read-only repeated comparison of regular image files; never reads raw devices.

Prints JSON to stdout. No repair, output image, or report file is created.
A stable repeat does not prove that data bypassed the operating-system cache.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
import stat
import sys


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@contextmanager
def _regular_reader(path):
    if os.path.islink(path):
        raise ValueError('Symbolische Links sind für diese Diagnose nicht erlaubt.')
    if not stat.S_ISREG(os.stat(path, follow_symlinks=False).st_mode):
        raise ValueError('Nur reguläre Image-Dateien sind erlaubt; keine Geräte oder FIFOs.')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags | getattr(os, 'O_BINARY', 0))
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('Nur reguläre Image-Dateien sind erlaubt; keine Geräte oder FIFOs.')
        with os.fdopen(fd, 'rb') as stream:
            fd = -1
            yield stream
    finally:
        if fd >= 0:
            os.close(fd)


def compare_images(source, target, *, offset=0, length=None, passes=2):
    if (type(offset) is not int or offset < 0 or type(passes) is not int or
            not 1 <= passes <= 5 or (length is not None and
                                    (type(length) is not int or length <= 0))):
        raise ValueError('Ungültiger Bereich oder Anzahl Durchläufe (1–5).')
    results = []
    for _ in range(passes):
        with _regular_reader(source) as left, _regular_reader(target) as right:
            before = [_identity(os.fstat(f.fileno())) for f in (left, right)]
            paths_before = [_identity(os.stat(p, follow_symlinks=False)) for p in (source, target)]
            if paths_before[0][:2] == paths_before[1][:2]:
                raise ValueError('Quelle und Vergleichsimage müssen verschiedene Dateien sein.')
            maximum = max(info[2] for info in before)
            if offset > maximum:
                raise ValueError('Startoffset liegt hinter beiden Dateien.')
            end = maximum if length is None else min(maximum, offset + length)
            left.seek(offset)
            right.seek(offset)
            hashes = [hashlib.sha256(), hashlib.sha256()]
            count, first, last, blocks = 0, None, None, 0
            samples = []
            position = offset
            while position < end:
                amount = min(1024 * 1024, end - position)
                a, b = left.read(amount), right.read(amount)
                hashes[0].update(a); hashes[1].update(b)
                if a != b:
                    blocks += 1
                    for index in range(max(len(a), len(b))):
                        av = a[index] if index < len(a) else None
                        bv = b[index] if index < len(b) else None
                        if av != bv:
                            at = position + index
                            count += 1
                            first = at if first is None else first
                            last = at
                            if len(samples) < 32:
                                samples.append({'offset': at, 'modulo_8': at % 8,
                                                'source_byte': av, 'image_byte': bv})
                position += amount
            after = [_identity(os.fstat(f.fileno())) for f in (left, right)]
            paths_after = [_identity(os.stat(p, follow_symlinks=False)) for p in (source, target)]
            # Compare each API against itself: Windows path and descriptor stat
            # can represent identity/ctime differently. Still detect changes to
            # either the open file or its path, and cross-check size and mtime.
            results.append({'offset': offset, 'length': end - offset,
                            'sizes': [info[2] for info in before],
                            'metadata_before': [dict(zip(('device', 'inode', 'size', 'mtime_ns', 'ctime_ns'), info))
                                                for info in before],
                            'sha256': [h.hexdigest() for h in hashes],
                            'different_bytes': count, 'different_blocks': blocks,
                            'first_difference': first, 'last_difference': last,
                            'samples': samples, 'metadata_unchanged':
                            before == after and paths_before == paths_after and
                            all(handle[2:4] == path[2:4]
                                for handle, path in zip(after, paths_after))})
    return {'passes': results, 'repeatable': all(r == results[0] for r in results),
            'metadata_unchanged': all(r['metadata_unchanged'] for r in results),
            'identical': all(r['different_bytes'] == 0 for r in results)}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Reguläre Images nur lesend vergleichen; keine Reparatur.')
    parser.add_argument('source')
    parser.add_argument('image')
    parser.add_argument('--offset', type=int, default=0, help='0-basierter Startoffset')
    parser.add_argument('--length', type=int, help='Anzahl Bytes; Standard: bis Dateiende')
    parser.add_argument('--passes', type=int, default=2, help='1–5 Durchläufe, Standard: 2')
    args = parser.parse_args(argv)
    try:
        result = compare_images(args.source, args.image, offset=args.offset,
                                length=args.length, passes=args.passes)
    except (OSError, ValueError) as exc:
        print(f'Diagnose fehlgeschlagen: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['identical'] and result['repeatable'] and result['metadata_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
