@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if errorlevel 1 exit /b 1
set "PREFLIGHT_LOG=%CD%\tenshi-windows-check.log"
where py >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
) else (
  where python >nul 2>&1
  if errorlevel 1 goto no_python
  set "PYTHON_CMD=python"
)
echo [Tenshi 2.9.0] Windows-Vorabpruefung ohne Laufwerkszugriff...
%PYTHON_CMD% windows_preflight.py > "%PREFLIGHT_LOG%" 2>&1
if errorlevel 1 goto failure
echo ERFOLG: Voraussetzungen fuer Windows/Python pruefbar.
echo Es wurden KEINE physischen Laufwerke geoeffnet.
echo Bericht: "%PREFLIGHT_LOG%"
if /I not "%~1"=="--no-pause" if not defined CI pause
exit /b 0
:no_python
echo FEHLER: Python 3.11+ 64 Bit ist erforderlich.
goto failure
:failure
echo FEHLER: Windows-Vorabpruefung nicht erfolgreich.
echo Details: "%PREFLIGHT_LOG%"
if /I not "%~1"=="--no-pause" if not defined CI pause
exit /b 1
