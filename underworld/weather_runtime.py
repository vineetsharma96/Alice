"""Load only the additive UW10W runtime; never substitute it for a historical save."""
import importlib
import os
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
_dlls = []


def load():
    location = Path(os.environ.get('ALICE_WEATHER_BUILD', ROOT / 'build/weather')).resolve()
    for path in (location, location / 'Release'):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    if os.name == 'nt' and not _dlls:
        for path in (Path(os.environ.get('UNDERWORLD_TOOLCHAIN', 'C:/mingw64/bin')), location):
            if path.is_dir():
                _dlls.append(os.add_dll_directory(str(path)))
    module = importlib.import_module('_underworld_weather')
    if module.world_format != 'UW10W':
        raise RuntimeError('Weather format mismatch; use matching runtime and a new weather world.')
    return module


def climate(enabled=True, year_s=2400, transition_s=20, change_s=90, temperature_bias_c=0):
    return dict(enabled=enabled, year_s=year_s, transition_s=transition_s,
                change_s=change_s, temperature_bias_c=temperature_bias_c)


def configuration(path):
    with Path(path).open('rb') as stream:
        value = tomllib.load(stream)
    if set(value) != set(climate()):
        raise ValueError('Unknown or missing climate configuration field')
    # Native validation remains the authority, without initializing a live world.
    validator = load().World(scripted=False)
    validator.configure_climate(value)
    return value
