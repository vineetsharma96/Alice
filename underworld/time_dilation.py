"""User-selectable wall-clock pacing for the manual life runner.

Time dilation changes how aggressively the control loop paces committed native
work. It does not skip native ticks, fabricate births, or make a short run
equivalent to centuries of native physics. The extreme preset is an explicit
SAO-inspired nominal ratio for experimentation and carries that limitation in
its metadata.
"""

from __future__ import annotations

from dataclasses import dataclass


SECONDS_PER_DAY = 86400.0
NOMINAL_DAYS_PER_YEAR = 365.0
SAO_YEARS = 300.0
SAO_REAL_DAYS = 21.0
SAO_NOMINAL_SCALE = SAO_YEARS * NOMINAL_DAYS_PER_YEAR / SAO_REAL_DAYS


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    scale: float
    warning: str
    target_world_years: float | None = None
    target_real_days: float | None = None


PRESETS = {
    'normal': Preset('normal', 'Normal · 1×', 1.0, 'Native pacing baseline.'),
    'fast': Preset('fast', 'Fast · 20×', 20.0, 'Wall-clock pacing only; native work remains authoritative.'),
    'sao_300y_3w': Preset(
        'sao_300y_3w',
        'Alicization nominal · 300 years / 3 weeks',
        SAO_NOMINAL_SCALE,
        'Nominal pacing target. It does not skip native ticks or guarantee 300 years in 21 days.',
        SAO_YEARS,
        SAO_REAL_DAYS,
    ),
}


def get(preset: str) -> Preset:
    try:
        return PRESETS[preset]
    except KeyError:
        raise ValueError(f'unknown time-dilation preset: {preset}') from None


def public(preset: str) -> dict:
    value = get(preset)
    return {
        'preset': value.id,
        'label': value.label,
        'scale': value.scale,
        'warning': value.warning,
        'target_world_years': value.target_world_years,
        'target_real_days': value.target_real_days,
    }
