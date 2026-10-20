param([string]$ToolchainBin = 'C:\mingw64\bin')
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
function Assert-Exit { if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" } }
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
    Assert-Exit
}
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Assert-Exit
$pythonExe = (Resolve-Path '.venv\Scripts\python.exe').Path
$env:UNDERWORLD_TOOLCHAIN = $ToolchainBin
if (Test-Path (Join-Path $ToolchainBin 'g++.exe')) {
    $env:PATH = "$ToolchainBin;$env:PATH"
    cmake -S . -B build -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$pythonExe"
} else {
    # Run from an MSVC developer shell, or supply a MinGW bin directory.
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$pythonExe"
}
Assert-Exit
cmake --build build --config Release --parallel 2
Assert-Exit
$core = 'build\underworld_core.exe'
if (-not (Test-Path $core)) { $core = 'build\Release\underworld_core.exe' }
$env:UNDERWORLD_CORE = (Resolve-Path $core).Path
.\.venv\Scripts\python.exe scripts\verify.py --core $core
Assert-Exit
