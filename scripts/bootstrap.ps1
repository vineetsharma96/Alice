param([string]$ToolchainBin = 'C:\mingw64\bin', [switch]$SkipTests)
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
$build = 'build/living-d'
if (Test-Path (Join-Path $ToolchainBin 'g++.exe')) {
    $env:PATH = "$ToolchainBin;$env:PATH"
    cmake -S . -B $build -G 'MinGW Makefiles' -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$pythonExe"
} else {
    cmake -S . -B $build -DCMAKE_BUILD_TYPE=Release "-DPython_EXECUTABLE=$pythonExe"
}
Assert-Exit
cmake --build $build --config Release --parallel 2
Assert-Exit
$env:UNDERWORLD_BUILD = (Resolve-Path $build).Path
$core = Join-Path $build 'underworld_core.exe'
if (-not (Test-Path $core)) { $core = Join-Path $build 'Release/underworld_core.exe' }
$env:UNDERWORLD_CORE = (Resolve-Path $core).Path
if (-not $SkipTests) {
    $evidence = 'artifacts/bootstrap-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N') + '.json'
    .\.venv\Scripts\python.exe scripts/verify_living_world.py --build $build --output $evidence
    Assert-Exit
    Write-Host "Verification evidence: $evidence"
}
Write-Host 'Ready. Run .\run.cmd or bash run.sh to launch the model-off living world.'
