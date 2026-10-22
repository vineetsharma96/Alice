"""Checked derivation of our own frozen profile, preserving historical sources.

Only fixed repository paths and developer-authored literal hooks are compiled.
No world data, model output or user text can become executable source.
"""
import hashlib
import json
from pathlib import Path
from types import ModuleType

ROOT=Path(__file__).resolve().parents[1]


def legacy_pins():
    pins=json.loads((ROOT/'artifacts/emotion_registration.json').read_text(encoding='utf8'))['files']
    for path,expected in pins.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Frozen F0-F3 source drift: '+path)
    return pins


def derive(name, relative, hooks, helpers=None):
    legacy_pins()
    source=(ROOT/relative).read_text(encoding='utf8')
    for hook in hooks:
        old,new=hook[:2];expected=hook[2] if len(hook)==3 else 1
        count=source.count(old)
        if count!=expected:raise ValueError(f'Profile hook expected{expected}, got{count}: {old[:80]}')
        source=source.replace(old,new,expected)
    module=ModuleType(name)
    module.__dict__.update(__package__='underworld',__file__=str(ROOT/relative))
    module.__dict__.update(helpers or {})
    exec(compile(source, f'<{name}:checked-own-source>', 'exec'),module.__dict__)
    return module
