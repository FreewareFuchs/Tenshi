@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "TEST_LOG=%CD%\tenshi-tests.log"
set "TENSHI_SETTINGS_FILE=%TEMP%\Tenshi-test-settings-%RANDOM%-%RANDOM%.json"
set "TENSHI_LOG_DIR=%TEMP%\Tenshi-test-logs-%RANDOM%-%RANDOM%"
if exist ".venv\Scripts\python.exe" (
    set "TEST_PYTHON="%CD%\.venv\Scripts\python.exe""
) else (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "TEST_PYTHON=py -3"
    ) else (
        set "TEST_PYTHON=python"
    )
)
echo [Tenshi] Starte automatische Tests (unabhaengig vom EXE-Build)...
%TEST_PYTHON% -m unittest discover -v -s tests > "%TEST_LOG%" 2>&1
if errorlevel 1 (
    echo TESTS FEHLGESCHLAGEN.
    echo Details: "%TEST_LOG%"
    echo Die letzten Testfehler stehen am Ende der Datei.
    pause
    exit /b 1
)
echo Tests erfolgreich. Protokoll: "%TEST_LOG%"
echo Testfehlersimulationen werden in einem getrennten temporaeren Verzeichnis protokolliert.
pause
exit /b 0
