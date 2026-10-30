@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "dist\Tenshi.exe" (
  echo FEHLER: dist\Tenshi.exe fehlt. Zuerst build_windows.bat ausfuehren.
  exit /b 1
)
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
  echo FEHLER: Inno Setup 6 ist nicht installiert. https://jrsoftware.org/isinfo.php
  exit /b 1
)
set "INSTALL_LOG=%CD%\tenshi-installer-build.log"
> "%INSTALL_LOG%" echo Tenshi 3.0.10 - Windows installer build
"%ISCC%" "installer\Tenshi.iss" >> "%INSTALL_LOG%" 2>&1
if errorlevel 1 goto failed
if not exist "installer_output\Tenshi_Setup_3.0.10.exe" goto failed
echo ERFOLG: installer_output\Tenshi_Setup_3.0.10.exe
echo Protokoll: "%INSTALL_LOG%"
if /I not "%~1"=="--no-pause" if not defined CI pause
exit /b 0
:failed
echo FEHLER beim Installer-Build. Details: "%INSTALL_LOG%"
if /I not "%~1"=="--no-pause" if not defined CI pause
exit /b 1
