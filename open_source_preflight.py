"""Fail-fast technical MIT release check; no proof of third-party rights."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PLACEHOLDER = '[RECHTEINHABER_EINTRAGEN]'

def check() -> list[str]:
    errors = []
    p = ROOT / 'LICENSE'
    if not p.is_file():
        errors.append('LICENSE fehlt.')
        return errors
    content = p.read_text(encoding='utf-8')
    if not content.startswith('MIT License\n'):
        errors.append('LICENSE ist keine erwartete MIT-Vorlage.')
    if PLACEHOLDER in content or '[year]' in content or '[fullname]' in content:
        errors.append('LICENSE enthaelt noch Platzhalter fuer den Rechteinhaber.')
    if 'Copyright (c) 2026 ' not in content:
        errors.append('Copyright-Zeile fehlt oder wurde ungeprueft veraendert.')
    for relative in ['THIRD_PARTY_NOTICES.md', 'SECURITY.md', 'CONTRIBUTING.md', 'README.md']:
        if not (ROOT / relative).is_file():
            errors.append(relative + ' fehlt.')
    for relative in ['release_tools.py','installer/Tenshi.iss']:
        if not (ROOT / relative).is_file():
            errors.append(relative + ' fehlt.')
    return errors

def main() -> int:
    errors = check()
    if errors:
        for message in errors:
            print('NICHT FREIGEBEN:', message, file=sys.stderr)
        print('Technische Vorpruefung FEHLGESCHLAGEN. Bitte OPEN_SOURCE_START_HIER.md lesen.', file=sys.stderr)
        return 2
    print('MIT-Dateien und Rechteinhaber-Feld formal geprueft.')
    print('WICHTIG: Rechte an Assets/Drittkomponenten und Rechtstexte separat manuell pruefen!')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
