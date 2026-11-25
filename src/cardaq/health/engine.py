"""Per-trip engine indicators at comparable, observed operating conditions."""

from bisect import bisect_right
from collections.abc import Iterable
from operator import itemgetter

from ..viewer.series import SPEED_RPM_GAP_SECONDS, Series
from .samples import feature, nearby


_TIME = itemgetter(0)
_FAST_AGE = 0.65
_FUEL_CONTROL_AGE = 0.75
_WARM_COOLANT = 75
_IDLE_CONDITION = "Stopped for at least 5 s, 500–1100 rpm, coolant at least 75 °C."
_CLOSED_LOOP = " Bank 1 in normal closed loop (fuel status 0x02)."
_CRUISE_BANDS = (("low", 1750, 2250), ("high", 3250, 3750))
_TRIMS = (
    ("stft", "Short-term fuel trim", "ecm_short_term_fuel_trim_pct"),
    ("ltft", "Long-term fuel trim", "ecm_long_term_fuel_trim_pct"),
)


def _settled_periods(samples: Iterable[tuple[float, bool]], delay: float) -> list[tuple[float, float]]:
    """Keep the observed part of each uninterrupted qualifying run after the delay."""
    periods = []
    start = previous = None
    for time, active in samples:
        if not active:
            start = None
        else:
            if start is None or not 0 < time - previous <= SPEED_RPM_GAP_SECONDS:
                start = time
            if time - start >= delay:
                if periods and periods[-1][0] == start + delay:
                    periods[-1] = (start + delay, time)
                else:
                    periods.append((start + delay, time))
        previous = time
    return periods


def _inside(periods: list[tuple[float, float]], time: float) -> bool:
    index = bisect_right(periods, time, key=_TIME) - 1
    return index >= 0 and time <= periods[index][1]


def _warm_idle(rpm: float | None, coolant: float | None) -> bool:
    return rpm is not None and 500 <= rpm <= 1100 and coolant is not None and coolant >= _WARM_COOLANT


def _cruise_band(series: dict[str, Series], time: float) -> str | None:
    speed = nearby(series.get("ecm_vehicle_speed_kph", []), time, _FAST_AGE)
    rpm = nearby(series.get("ecm_engine_speed_rpm", []), time, _FAST_AGE)
    load = nearby(series.get("ecm_calculated_load_pct", []), time, _FUEL_CONTROL_AGE)
    acceleration = nearby(series.get("derived_longitudinal_acceleration_m_s2", []), time, _FAST_AGE)
    if speed is None or not 100 <= speed < 120 or load is None or not 30 <= load < 60:
        return None
    if rpm is None or acceleration is None or abs(acceleration) > 0.3:
        return None
    return next((name for name, lower, upper in _CRUISE_BANDS if lower <= rpm < upper), None)


def engine_features(series: dict[str, Series]) -> list[dict]:
    """Summarize original RPM, fuel-trim and coolant observations once per channel."""
    rpm = series.get("ecm_engine_speed_rpm", [])
    coolant = series.get("ecm_coolant_sensor_1_c", [])
    status = series.get("ecm_fuel_system_1_status", [])
    idle = _settled_periods((
        (time, speed == 0 and _warm_idle(nearby(rpm, time, _FAST_AGE), nearby(coolant, time, _FAST_AGE)))
        for time, speed in series.get("ecm_vehicle_speed_kph", [])
    ), 5)
    idle_rpm = [
        value for time, value in rpm
        if _inside(idle, time) and _warm_idle(value, nearby(coolant, time, _FAST_AGE))
    ]
    features = [
        feature("engine_idle_rpm", "Warm stopped engine speed", "rpm", _IDLE_CONDITION, idle_rpm,
                minimum_change=0.25),
        feature("engine_idle_rpm_iqr", "Warm stopped RPM spread", "rpm", _IDLE_CONDITION, idle_rpm,
                minimum=10, statistic="iqr", minimum_change=0.25),
    ]

    cruise = {name: {"stft": [], "ltft": [], "coolant": []} for name, _, _ in _CRUISE_BANDS}
    for key, label, channel in _TRIMS:
        idle_values = []
        for time, value in series.get(channel, []):
            if nearby(status, time, _FUEL_CONTROL_AGE) != 2:
                continue
            temperature = nearby(coolant, time, _FAST_AGE)
            if temperature is None or temperature < _WARM_COOLANT:
                continue
            if _inside(idle, time) and _warm_idle(nearby(rpm, time, _FAST_AGE), temperature):
                idle_values.append(value)
            band = _cruise_band(series, time)
            if band is not None:
                cruise[band][key].append(value)
        features.append(feature(f"engine_idle_{key}_pct", f"{label} at warm stop", "%",
                                _IDLE_CONDITION + _CLOSED_LOOP, idle_values, minimum_change=100 / 128))

    # Qualify coolant with observed engine run time independently of coolant's value.
    running = _settled_periods(((time, value >= 500) for time, value in rpm), 600)
    for time, temperature in coolant:
        if _inside(running, time):
            band = _cruise_band(series, time)
            if band is not None:
                cruise[band]["coolant"].append(temperature)

    for band, lower, upper in _CRUISE_BANDS:
        condition = (f"100–<120 km/h, {lower}–<{upper} rpm, 30–<60% load, "
                     "absolute acceleration at most 0.3 m/s².")
        for key, label, _ in _TRIMS:
            features.append(feature(f"engine_cruise_{band}_{key}_pct", f"{label} at {band}-RPM cruise", "%",
                                    condition + " Coolant at least 75 °C." + _CLOSED_LOOP,
                                    cruise[band][key], minimum_change=100 / 128))
        features.append(feature(f"engine_cruise_{band}_coolant_c", f"Coolant at {band}-RPM cruise", "°C",
                                condition + " Engine continuously observed running for at least 10 min.",
                                cruise[band]["coolant"], minimum_change=1))
    return features
