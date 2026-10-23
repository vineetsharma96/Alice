"""Opt-in custom-build path resolution without changing frozen native loaders."""
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def configure_build(build=None):
    """Resolve a custom build from the checkout before importing the loader.

    This changes this process's explicit build setting only when called.
    The historical underworld.native module remains byte-identical.
    """
    configured=Path(build if build is not None else os.environ.get('UNDERWORLD_BUILD',ROOT/'build'))
    resolved=(configured if configured.is_absolute() else ROOT/configured).resolve()
    os.environ['UNDERWORLD_BUILD']=str(resolved)
    return resolved
