"""Summarize candidate CVT behavior during comparable stretches of observed cruise."""

from collections import deque
from collections.abc import Iterator

from ..viewer.series import Series
from .samples import feature, nearby


_RPM_BANDS = ((1500, 2500), (2500, 4000))
_MIN_STEADY_SECONDS = 5.0
_MAX_POLL_GAP_SECONDS = 2.0
_LOAD_MATCH_SECONDS = 1.5


def _settled_cruise(series: dict[str, Series], low_rpm: int, high_rpm: int) -> Iterator[float]:
    """Yield sample times with a continuous qualifying speed and load history."""
    speed = series.get("honda_vehicle_speed_kph", [])
    fluid = series.get("candidate_cvt_fluid_temperature_c", [])
    load = series.get("ecm_calculated_load_pct", [])
    window: deque[tuple[float, float, float]] = deque()

    for time, rpm in series.get("honda_engine_speed_rpm", []):
        road_speed = nearby(speed, time, 0)
        temperature = nearby(fluid, time, 0)
        demand = nearby(load, time, _LOAD_MATCH_SECONDS)
        in_profile = (
            low_rpm <= rpm < high_rpm
            and road_speed is not None and 110 <= road_speed < 120
            and temperature is not None and temperature >= 60
            and demand is not None and 35 <= demand <= 60
        )
        if not in_profile:
            window.clear()
            continue
        if window and not 0 < time - window[-1][0] <= _MAX_POLL_GAP_SECONDS:
            window.clear()
        window.append((time, road_speed, demand))
        # Retain the reading that brackets the beginning of the five-second window.
        while len(window) > 1 and window[1][0] <= time - _MIN_STEADY_SECONDS:
            window.popleft()
        if time - window[0][0] < _MIN_STEADY_SECONDS:
            continue
        speeds = [point[1] for point in window]
        loads = [point[2] for point in window]
        if max(speeds) - min(speeds) <= 2 and max(loads) - min(loads) <= 8:
            yield time


def cvt_features(series: dict[str, Series]) -> list[dict]:
    """Return per-trip magnitude estimates in fixed, observable engine RPM bands."""
    slip = series.get("derived_torque_converter_slip_rpm", [])
    ratio_rate = series.get("derived_ratio_change_pct_s", [])
    result = []
    for low, high in _RPM_BANDS:
        slip_magnitudes = []
        ratio_magnitudes = []
        for time in _settled_cruise(series, low, high):
            observed_slip = nearby(slip, time, 0)
            observed_rate = nearby(ratio_rate, time, 0)
            if observed_slip is not None:
                slip_magnitudes.append(abs(observed_slip))
            if observed_rate is not None:
                ratio_magnitudes.append(abs(observed_rate))
        band = f"{low:,}–<{high:,} rpm"
        condition = (
            f"110–119 km/h, {band}, candidate CVT fluid ≥60 °C and calculated load 35–60%. "
            "At least 5 s with speed spanning ≤2 km/h and load spanning ≤8 percentage points. "
            "Honda samples are at most 2 s apart and load is matched within 1.5 s."
        )
        result.append(feature(
            f"cvt_slip_rpm_{low}_{high}", f"Absolute converter slip estimate · {band}", "rpm",
            condition, slip_magnitudes, minimum=10, minimum_change=1.0,
        ))
        result.append(feature(
            f"cvt_ratio_rate_{low}_{high}", f"Absolute pulley ratio change rate · {band}", "%/s",
            condition, ratio_magnitudes, minimum=10,
        ))
    return result
