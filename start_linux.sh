#!/usr/bin/env bash
# Tenshi Linux launcher: never request sudo, mount, or change device rights.
set -e
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Tenshi benötigt Python 3. Bitte Python 3 installieren.' >&2
    exit 1
fi

if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
    printf '%s\n' 'Tkinter fehlt. Unter Linux Mint: sudo apt install python3-tk' >&2
    exit 1
fi

exec python3 main.py "$@"
