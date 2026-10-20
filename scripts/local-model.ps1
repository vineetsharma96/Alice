param([switch]$Start)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
$archive = Join-Path $root '.tools/llama-b11721.zip'
$binaryDir = Join-Path $root '.tools/llama-b11721'
$weight = Join-Path $root 'models/smollm2-360m-instruct-q8_0.gguf'
New-Item -ItemType Directory -Force (Join-Path $root '.tools'),(Join-Path $root 'models') | Out-Null
if (-not (Test-Path -LiteralPath $archive)) {
    Invoke-WebRequest 'https://github.com/ggml-org/llama.cpp/releases/download/b11721/llama-b11721-bin-win-cpu-x64.zip' -OutFile $archive
}
if ((Get-FileHash -LiteralPath $archive).Hash -ne '19F5A91CFBD906FADFB36975A65A0C165C7DB1A533D5DB129DFA0A533DFDEAA1') { throw 'llama.cpp archive checksum mismatch' }
if (-not (Test-Path -LiteralPath $binaryDir)) { Expand-Archive -LiteralPath $archive -DestinationPath $binaryDir }
if (-not (Test-Path -LiteralPath $weight)) {
    Invoke-WebRequest 'https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF/resolve/593b5a2e04c8f3e4ee880263f93e0bd2901ad47f/smollm2-360m-instruct-q8_0.gguf' -OutFile $weight
}
if ((Get-FileHash -LiteralPath $weight).Hash -ne '48AB3034D0DD401FBC721EB1DF3217902FEE7DAB9078992D66431F09B7750201') { throw 'model checksum mismatch' }
if ($Start) {
    if (Get-NetTCPConnection -LocalPort 8081 -State Listen -ErrorAction SilentlyContinue) { throw 'Port 8081 is already in use; no second model server started' }
    $server = Start-Process -FilePath (Join-Path $binaryDir 'llama-server.exe') -WorkingDirectory $root -ArgumentList @(
        '-m','models/smollm2-360m-instruct-q8_0.gguf','--host','127.0.0.1','--port','8081',
        '-c','2048','-t','2','-tb','2','--parallel','1','-ngl','0','--no-ui') -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $root '.tools/server.stdout.log') -RedirectStandardError (Join-Path $root '.tools/server.stderr.log')
    Write-Output "Local CPU server PID: $($server.Id); health: http://127.0.0.1:8081/health. Stop this PID when finished."
} else { Write-Output 'Pinned CPU binary and model verified. Add -Start to start the loopback server.' }
