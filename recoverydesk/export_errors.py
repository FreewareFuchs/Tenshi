"""Explain OS errors without guessing permissions from an unrelated errno."""
import errno
from .i18n import translate


def export_error_message(error, language='de'):
    if isinstance(error, PermissionError) or getattr(error, 'errno', None) in (errno.EACCES, errno.EPERM):
        hint = 'Zugriff verweigert. Prüfe Leserechte für die Quelle und Schreibrechte für den Zielordner. Bei Flatpak muss der Zielordner auch für Tenshi freigegeben sein.'
    elif getattr(error, 'errno', None) == errno.EROFS:
        hint = 'Das Laufwerk ist schreibgeschützt eingebunden. Wähle einen beschreibbaren Zielordner oder prüfe die Einbindung und Freigabe.'
    elif getattr(error, 'errno', None) in (errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP):
        hint = 'Eine benötigte Dateioperation wird nicht unterstützt oder wurde als ungültig abgelehnt. Prüfe die Einbindung des Zielordners; gemeinsam genutzte VM-Ordner können eingeschränkt sein. Versuche einen lokalen Linux-Zielordner. Dies ist kein eindeutiger Nachweis fehlender Schreibrechte.'
    elif getattr(error, 'errno', None) == errno.ENOSPC:
        hint = 'Auf dem Laufwerk ist kein Speicherplatz mehr verfügbar. Prüfe den freien Platz im Zielordner.'
    else:
        return str(error)
    return translate(hint, language)+'\n\n'+str(error)
