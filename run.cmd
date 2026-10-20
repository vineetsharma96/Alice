@echo off
setlocal
cd /d "%~dp0"
if not "%UNDERWORLD_SOURCE%"=="1" if exist "dist\UnderworldLab.exe" (
  "dist\UnderworldLab.exe" %*
  exit /b
)
if not exist ".venv\Scripts\python.exe" goto setup
if not exist "build\living-d\_underworld*.pyd" goto setup
goto launch
:setup
powershell.exe -NoProfile -File scripts\bootstrap.ps1 -SkipTests
if errorlevel 1 exit /b 1
:launch
set "UNDERWORLD_BUILD=%CD%\build\living-d"
.venv\Scripts\python.exe -m underworld.app %*
