@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "dist\Tenshi.exe" (
  echo FEHLER: dist\Tenshi.exe fehlt. Zuerst build_windows.bat ausfuehren.
  exit /b 1
)
if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD=%CD%\.venv\Scripts\python.exe"
  goto package
)
where py >nul 2>&1
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
) else (
  set "PYTHON_CMD=python"
)
:package
echo [Tenshi 3.0.4] Portable ZIP mit SHA-256-Pruefung erstellen...
if exist ".venv\Scripts\python.exe" (
  "%PYTHON_CMD%" release_tools.py portable --exe "dist\Tenshi.exe" --output "portable_output\Tenshi_Portable_3.0.4_Win64.zip" --overwrite
) else (
  %PYTHON_CMD% release_tools.py portable --exe "dist\Tenshi.exe" --output "portable_output\Tenshi_Portable_3.0.4_Win64.zip" --overwrite
)
if errorlevel 1 (
  echo FEHLER: Portable-Paket wurde nicht erstellt.
  if /I not "%~1"=="--no-pause" if not defined CI pause
  exit /b 1
)
echo ERFOLG: portable_output\Tenshi_Portable_3.0.4_Win64.zip
if /I not "%~1"=="--no-pause" if not defined CI pause
exit /b 0
