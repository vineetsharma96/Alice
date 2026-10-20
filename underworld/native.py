"""Load the locally built extension; native runtime DLLs remain in the toolchain."""
import importlib
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
_dll_directories = []


def load_native():
    build = Path(os.environ.get("UNDERWORLD_BUILD", ROOT / "build")).resolve()
    for location in (build, build / "Release"):
        if str(location) not in sys.path:
            sys.path.insert(0, str(location))
    if os.name == "nt" and not _dll_directories:
        # Python 3.8+ does not use PATH for extension dependency resolution.
        candidates = [os.environ.get("UNDERWORLD_TOOLCHAIN", r"C:\mingw64\bin"), str(build)]
        for candidate in candidates:
            if Path(candidate).is_dir():
                _dll_directories.append(os.add_dll_directory(candidate))
    try:
        return importlib.import_module("_underworld")
    except ImportError as error:
        raise RuntimeError("Native module unavailable. Run scripts/bootstrap.ps1 or documented CMake build; "
                           "set UNDERWORLD_BUILD / UNDERWORLD_TOOLCHAIN for custom paths.") from error
