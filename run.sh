#!/usr/bin/env bash
# Git Bash on Windows, or Bash on Linux/macOS with an existing C++20 toolchain.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
if [[ "${OS:-}" == "Windows_NT" ]]; then
  if [[ "${UNDERWORLD_SOURCE:-0}" != 1 && -x dist/UnderworldLab.exe ]]; then exec ./dist/UnderworldLab.exe "$@"; fi
  if [[ ! -x .venv/Scripts/python.exe ]] || ! compgen -G "build/living-d/_underworld*.pyd" >/dev/null; then
    powershell.exe -NoProfile -File scripts/bootstrap.ps1 -SkipTests
  fi
  export UNDERWORLD_BUILD="$(cygpath -w "$ROOT/build/living-d")"
  exec .venv/Scripts/python.exe -m underworld.app "$@"
fi
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
fi
if ! compgen -G 'build/living-d/_underworld*.so' >/dev/null; then
  cmake -S . -B build/living-d -DCMAKE_BUILD_TYPE=Release -DPython_EXECUTABLE="$ROOT/.venv/bin/python"
  cmake --build build/living-d --parallel 2
fi
export UNDERWORLD_BUILD="$ROOT/build/living-d"
exec .venv/bin/python -m underworld.app "$@"
