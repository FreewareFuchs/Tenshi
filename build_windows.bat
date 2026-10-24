@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if errorlevel 1 (
  echo FEHLER: Projektordner kann nicht geoeffnet werden.
  exit /b 1
)
set "BUILD_LOG=%CD%\tenshi-build.log"
> "%BUILD_LOG%" echo Tenshi 3.0.2 - Windows EXE build

echo [Tenshi 3.0.2] Windows-EXE erstellen
echo [1/5] Python 3.11+ in 64 Bit pruefen...
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 goto missing_python
    set "PYTHON_CMD=python"
)
%PYTHON_CMD% -c "import sys,struct; print(sys.version); sys.exit(0 if sys.version_info >= (3,11) and struct.calcsize('P')==8 else 1)" >> "%BUILD_LOG%" 2>&1
if errorlevel 1 goto unsupported_python

echo [2/5] Virtuelle Python-Umgebung vorbereiten...
if not exist ".venv\Scripts\python.exe" (
    %PYTHON_CMD% -m venv ".venv" >> "%BUILD_LOG%" 2>&1
    if errorlevel 1 goto env_failed
)
set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
"%VENV_PYTHON%" -m pip --version >> "%BUILD_LOG%" 2>&1
if errorlevel 1 goto env_failed

echo [3/5] PyInstaller installieren/pruefen...
"%VENV_PYTHON%" -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: --force-reinstall -r "requirements-build-windows.txt" >> "%BUILD_LOG%" 2>&1
if errorlevel 1 goto install_failed
"%VENV_PYTHON%" -m pip check >> "%BUILD_LOG%" 2>&1
if errorlevel 1 goto install_failed

echo [4/5] Tenshi.exe mit Programmsymbol und Versionsinformationen bauen...
if not exist "build\version_info.txt" goto missing_version
"%VENV_PYTHON%" write_build_info.py >> "%BUILD_LOG%" 2>&1
if errorlevel 1 goto build_failed
"%VENV_PYTHON%" -m PyInstaller --noconfirm --clean --windowed --onefile --name Tenshi --icon "recoverydesk/assets/tenshi.ico" --version-file "build/version_info.txt" --add-data "recoverydesk/assets;recoverydesk/assets" --add-data "build/identity/recoverydesk/_build_info.json;recoverydesk" main.py >> "%BUILD_LOG%" 2>&1
if errorlevel 1 goto build_failed
if not exist "dist\Tenshi.exe" goto missing_exe
"%VENV_PYTHON%" -m pip freeze --all > "build\windows-build-requirements.txt" 2>> "%BUILD_LOG%"
if errorlevel 1 goto build_failed
"%VENV_PYTHON%" -VV > "build\windows-build-python.txt" 2>> "%BUILD_LOG%"
if errorlevel 1 goto build_failed

echo [5/5] Portable-Paket bei Bedarf ueber build_portable.bat erstellen.
echo.
echo ERFOLG: "%CD%\dist\Tenshi.exe"
echo Build-Protokoll: "%BUILD_LOG%"
echo Portable ZIP: build_portable.bat ^| Installer: build_installer.bat
echo Tests: run_tests.bat
if /I not "%~1"=="--no-pause" if not defined CI pause
exit /b 0

:missing_python
echo FEHLER: Kein Python gefunden. Python 3.11+ (64 Bit) installieren.
goto failed
:unsupported_python
echo FEHLER: Python muss Version 3.11 oder neuer und 64 Bit sein.
goto failed
:env_failed
echo FEHLER in Schritt 2: Python-Umgebung konnte nicht eingerichtet werden.
goto failed
:install_failed
echo FEHLER in Schritt 3: PyInstaller konnte nicht installiert werden. Internet/Proxy/Antivirus pruefen.
goto failed
:missing_version
echo FEHLER: build\version_info.txt fehlt.
goto failed
:build_failed
echo FEHLER in Schritt 4: PyInstaller konnte Tenshi.exe nicht erstellen.
goto failed
:missing_exe
echo FEHLER: PyInstaller hat keine dist\Tenshi.exe erstellt.
goto failed
:failed
echo.
echo Details im Build-Protokoll: "%BUILD_LOG%"
echo Bitte die letzten Zeilen aus tenshi-build.log bereitstellen.
if /I not "%~1"=="--no-pause" if not defined CI pause
exit /b 1
