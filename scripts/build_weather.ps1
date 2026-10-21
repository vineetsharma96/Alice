param([string]$ToolchainBin='C:\mingw64\bin')
$ErrorActionPreference='Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$env:PATH="$ToolchainBin;$env:PATH"
$pythonExe=(Resolve-Path '.venv/Scripts/python.exe').Path
cmake -S weather_native -B build/weather -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$pythonExe"
if($LASTEXITCODE -ne 0){throw 'Weather configuration failed'}
cmake --build build/weather --parallel 2
if($LASTEXITCODE -ne 0){throw 'Weather build failed'}
Write-Host 'Separate weather runtime ready; original living-d runtime preserved.'
