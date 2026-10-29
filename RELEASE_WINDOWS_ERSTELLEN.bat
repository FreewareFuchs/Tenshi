@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo =====================================================
echo  Tenshi 3.0.8 - Windows Release-Vorbereitung
 echo =====================================================
echo.
echo Es werden Tests, EXE, Portable-ZIP und Installer erstellt.
echo Voraussetzung: Windows 64 Bit, Python 3.11+, Inno Setup 6.3+
echo Keine Images oder Quell-Laufwerke werden automatisch geoeffnet.
echo.
py -3 sync_release_version.py --check
if errorlevel 1 goto failed
py -3 open_source_preflight.py
if errorlevel 1 goto failed
call check_windows.bat --no-pause
if errorlevel 1 goto failed
call run_tests.bat --no-pause
if errorlevel 1 goto failed
call build_windows.bat --no-pause
if errorlevel 1 goto failed
if not exist "dist\Tenshi.exe" goto failed
echo [Smoke-Test] Start ohne GUI oder Laufwerkszugriff...
"dist\Tenshi.exe" --smoke-test
if errorlevel 1 goto failed
call build_portable.bat --no-pause
if errorlevel 1 goto failed
call build_installer.bat --no-pause
if errorlevel 1 goto failed
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" release_finalize.py
) else (
  py -3 release_finalize.py
)
if errorlevel 1 goto failed
echo.
echo ERFOLG. Dateien liegen unter VEROEFFENTLICHUNG\UPLOAD
 echo ACHTUNG: Lizenz und Rechtsangaben vor Upload pruefen.
if not defined CI pause
exit /b 0
:failed
echo.
echo FEHLER: Release-Ablauf angehalten. Siehe Build-/Test-Logs.
if not defined CI pause
exit /b 1
