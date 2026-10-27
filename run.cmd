@echo off
setlocal
cd /d "%~dp0"
rem Default mode keeps the historical model-off desktop runner.
rem Alice integrated-life modes are explicit:
rem   run.cmd --readonly --db data\my-life.sqlite --port 8781
rem   run.cmd --control --db data\my-life.sqlite --port 8782
rem Aliases without the leading dashes are also accepted.
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
