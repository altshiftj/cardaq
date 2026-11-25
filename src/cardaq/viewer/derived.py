"""Calculate optional series from observed, time-aligned capture samples."""

from bisect import bisect_left
from collections.abc import Iterator
from itertools import pairwise
from math import log

from .series import SPEED_RPM_GAP_SECONDS, Series


_TCM_PAIR_SECONDS = 0.150
_TEMPERATURE_MATCH_SECONDS = 0.55
_ACCELERATION_HALF_WINDOW_SECONDS = 1.5
_ACCELERATION_WINDOW_TOLERANCE_SECONDS = 0.55
_MAX_RATIO_SAMPLE_GAP_SECONDS = 2.5
_THERMAL_WINDOW_SECONDS = 60.0
_THERMAL_WINDOW_TOLERANCE_SECONDS = 2.0
_MAX_THERMAL_SAMPLE_GAP_SECONDS = 5.0

_WARMING_CHANNELS = {
    "derived_engine_coolant_warming_rate": (
        "ecm_coolant_sensor_1_c", "Engine coolant warming rate",
        "Positive values show coolant sensor 1 warming. A return toward zero means the temperature is "
        "leveling off. Compare trips from similar starting temperatures.",
    ),
    "derived_cvt_fluid_warming_rate": (
        "candidate_cvt_fluid_temperature_c", "CVT fluid warming rate estimate",
        "A positive value means the candidate fluid reading rose over the past minute. Compare the "
        "timing of its peak with the coolant peak to see whether their fastest warming happened together.",
    ),
    "derived_catalyst_warming_rate": (
        "ecm_catalyst_temperature_c", "Catalyst warming rate",
        "A high positive value shows the reported catalyst temperature climbing quickly. A negative "
        "value shows cooling over the preceding minute. Check the absolute temperature alongside the rate.",
    ),
}
ADDITIONAL_METRICS = {
    "derived_converter_slip_pct": {
        "label": "Torque converter slip estimate",
        "unit": "%",
        "description": "Engine RPM minus candidate turbine RPM as a percentage of engine RPM.",
        "interpretation": (
            "At +10%, the turbine reading is 90% of engine speed. Use the percentage to compare "
            "speed differences at low and high RPM."
        ),
    },
    "derived_ratio_change_pct_s": {
        "label": "Pulley ratio change rate",
        "unit": "%/s",
        "description": "Relative change per second in the estimated pulley ratio, calculated on a logarithmic scale.",
        "interpretation": (
            "Positive means the input is turning faster relative to the output than before. Negative "
            "means the ratio is falling. Near zero marks a steady ratio even when road speed changes."
        ),
    },
    "derived_output_speed_change_pct_s": {
        "label": "CVT output speed change rate",
        "unit": "%/s",
        "description": "Relative change per second in candidate output-shaft RPM, calculated on a logarithmic scale.",
        "interpretation": (
            "Positive values show the output shaft speeding up. Add this rate to the pulley ratio change rate "
            "at the same sample to see how quickly the input pulley sped up or slowed down."
        ),
    },
    "derived_manifold_vacuum_kpa": {
        "label": "Intake manifold vacuum",
        "unit": "kPa",
        "description": "Atmospheric pressure minus ECM manifold pressure, matched within two seconds.",
        "interpretation": (
            "A larger positive gap means manifold pressure is farther below ambient. Watch whether the gap "
            "shrinks as the throttle opens and the engine draws air at closer to atmospheric pressure."
        ),
    },
    "derived_coolant_sensor_difference_c": {
        "label": "Coolant sensor 1 minus 2",
        "unit": "°C",
        "description": "ECM coolant sensor 1 minus sensor 2 at the same recorded time.",
        "interpretation": (
            "A positive value means sensor 1 reads warmer. A widening gap during warm-up shows that the "
            "two readings are responding at different rates."
        ),
    },
    **{
        key: {
            "label": label,
            "unit": "°C/min",
            "description": "Average temperature change per minute over the preceding minute of continuous readings.",
            "interpretation": interpretation,
        }
        for key, (_, label, interpretation) in _WARMING_CHANNELS.items()
    },
}
for metric in ADDITIONAL_METRICS.values():
    metric.update(group="Derived", precision=2)


def derive_series(series: dict[str, Series]) -> dict[str, Series]:
    """Return available derived series without modifying the original observations."""
    drive_pulley = _exact_samples(series.get("candidate_drive_pulley_rpm", []))
    output_pulley = _exact_samples(series.get("candidate_driven_pulley_rpm", []))
    honda_engine = _exact_samples(series.get("honda_engine_speed_rpm", []))
    ratios = _pulley_ratios(
        drive_pulley,
        output_pulley,
        _exact_samples(series.get("honda_vehicle_speed_kph", [])),
    )
    slip, pulley_difference = _converter_differences(
        honda_engine,
        drive_pulley,
        series.get("candidate_torque_converter_turbine_rpm", []),
    )
    ratio_rates, output_rates = _cvt_change_rates(ratios, output_pulley)
    coolant1 = series.get("ecm_coolant_sensor_1_c", [])
    coolant2 = _exact_samples(series.get("ecm_coolant_sensor_2_c", []))
    results = {
        "derived_pulley_ratio": ratios,
        "derived_torque_converter_slip_rpm": slip,
        "derived_drive_minus_turbine_rpm": pulley_difference,
        "derived_longitudinal_acceleration_m_s2": _acceleration(
            series.get("ecm_vehicle_speed_kph", []),
        ),
        "derived_cvt_minus_coolant_c": [
            [timestamp, cvt - coolant]
            for timestamp, cvt, coolant in _nearby_pairs(
                series.get("candidate_cvt_fluid_temperature_c", []), coolant1, _TEMPERATURE_MATCH_SECONDS
            )
        ],
        "derived_converter_slip_pct": [
            [timestamp, 100 * difference / honda_engine[timestamp]] for timestamp, difference in slip
        ],
        "derived_ratio_change_pct_s": ratio_rates,
        "derived_output_speed_change_pct_s": output_rates,
        "derived_manifold_vacuum_kpa": [
            [timestamp, baro - manifold]
            for timestamp, manifold, baro in _nearby_pairs(
                series.get("ecm_manifold_pressure_kpa", []), series.get("ecm_barometric_pressure_kpa", []), 2.0
            )
        ],
        "derived_coolant_sensor_difference_c": [
            [timestamp, value - coolant2[timestamp]]
            for timestamp, value in _exact_samples(coolant1).items() if timestamp in coolant2
        ],
        **{
            key: _warming_rate(series.get(source, []))
            for key, (source, _, _) in _WARMING_CHANNELS.items()
        },
    }
    return {key: points for key, points in results.items() if points}


def _exact_samples(points: Series) -> dict[float, float]:
    # Equal timestamps can only stand in for a source row when the values agree.
    samples: dict[float, float] = {}
    conflicts: set[float] = set()
    for timestamp, value in points:
        if timestamp in samples and samples[timestamp] != value:
            conflicts.add(timestamp)
        samples[timestamp] = value
    for timestamp in conflicts:
        del samples[timestamp]
    return samples


def _pulley_ratios(
    drive: dict[float, float], output: dict[float, float], speed: dict[float, float],
) -> Series:
    return [
        [timestamp, rpm / output[timestamp]]
        for timestamp, rpm in drive.items()
        if speed.get(timestamp, 0) >= 10 and output.get(timestamp, 0) > 0
    ]


def _converter_differences(
    engine: dict[float, float], drive: dict[float, float], turbine: Series,
) -> tuple[Series, Series]:
    slip: Series = []
    pulley_difference: Series = []
    turbine_samples = iter(turbine)
    following = next(turbine_samples, None)
    for timestamp, engine_rpm in engine.items():
        while following is not None and following[0] <= timestamp:
            following = next(turbine_samples, None)
        if following is None:
            break
        if following[0] <= timestamp + _TCM_PAIR_SECONDS:
            turbine_rpm = following[1]
            following = next(turbine_samples, None)
            if engine_rpm >= 500:
                slip.append([timestamp, engine_rpm - turbine_rpm])
                if timestamp in drive:
                    pulley_difference.append([timestamp, drive[timestamp] - turbine_rpm])
    return slip, pulley_difference


def _nearest_index(times: list[float], target: float, start: int, end: int) -> int:
    following = bisect_left(times, target, start, end)
    if following == start:
        return following
    if following == end or target - times[following - 1] <= times[following] - target:
        return following - 1
    return following


def _acceleration(speed: Series) -> Series:
    if len(speed) < 3:
        return []
    times = [timestamp for timestamp, _ in speed]
    segments = [0]
    for earlier, later in pairwise(times):
        segments.append(segments[-1] + (later - earlier > SPEED_RPM_GAP_SECONDS))

    acceleration = []
    for index in range(1, len(times) - 1):
        timestamp = times[index]
        left_target = timestamp - _ACCELERATION_HALF_WINDOW_SECONDS
        right_target = timestamp + _ACCELERATION_HALF_WINDOW_SECONDS
        left = _nearest_index(times, left_target, 0, index)
        right = _nearest_index(times, right_target, index + 1, len(times))
        if (
            segments[left] == segments[right]
            and abs(times[left] - left_target) <= _ACCELERATION_WINDOW_TOLERANCE_SECONDS
            and abs(times[right] - right_target) <= _ACCELERATION_WINDOW_TOLERANCE_SECONDS
        ):
            speed_change_m_s = (speed[right][1] - speed[left][1]) / 3.6
            acceleration.append([timestamp, speed_change_m_s / (times[right] - times[left])])
    return acceleration


def _nearby_pairs(samples: Series, reference: Series, tolerance: float) -> Iterator[tuple[float, float, float]]:
    if not reference:
        return
    times = [timestamp for timestamp, _ in reference]
    for timestamp, value in samples:
        index = _nearest_index(times, timestamp, 0, len(times))
        if timestamp - tolerance < times[index] < timestamp + tolerance:
            yield timestamp, value, reference[index][1]


def _cvt_change_rates(ratios: Series, output: dict[float, float]) -> tuple[Series, Series]:
    ratio_rates = []
    output_rates = []
    for (before, old_ratio), (after, ratio) in pairwise(ratios):
        dt = after - before
        if 0 < dt <= _MAX_RATIO_SAMPLE_GAP_SECONDS and old_ratio > 0 and ratio > 0:
            ratio_rates.append([after, 100 * (log(ratio) - log(old_ratio)) / dt])
            output_rates.append([after, 100 * (log(output[after]) - log(output[before])) / dt])
    return ratio_rates, output_rates


def _warming_rate(points: Series) -> Series:
    if len(points) < 2:
        return []
    rates = []
    times = [timestamp for timestamp, _ in points]
    start = 0
    for index, (timestamp, temperature) in enumerate(points[1:], 1):
        if timestamp - times[index - 1] > _MAX_THERMAL_SAMPLE_GAP_SECONDS:
            start = index
            continue
        target = timestamp - _THERMAL_WINDOW_SECONDS
        previous = _nearest_index(times, target, start, index)
        if abs(times[previous] - target) <= _THERMAL_WINDOW_TOLERANCE_SECONDS:
            rates.append([timestamp, 60 * (temperature - points[previous][1]) / (timestamp - times[previous])])
    return rates
