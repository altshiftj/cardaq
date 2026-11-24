"""Calculate optional series from observed, time-aligned capture samples."""

from bisect import bisect_left
from itertools import pairwise


_TCM_PAIR_SECONDS = 0.150
_TEMPERATURE_MATCH_SECONDS = 0.55
_ACCELERATION_HALF_WINDOW_SECONDS = 1.5
_ACCELERATION_WINDOW_TOLERANCE_SECONDS = 0.55
_MAX_SPEED_SAMPLE_GAP_SECONDS = 1.5

Series = list[list[float]]


def derive_series(series: dict[str, Series]) -> dict[str, Series]:
    """Return available derived series without modifying the original observations."""
    drive_pulley = _exact_samples(series.get("candidate_drive_pulley_rpm", []))
    ratios = _pulley_ratios(
        drive_pulley,
        _exact_samples(series.get("candidate_driven_pulley_rpm", [])),
        _exact_samples(series.get("honda_vehicle_speed_kph", [])),
    )
    slip, pulley_difference = _converter_differences(
        _exact_samples(series.get("honda_engine_speed_rpm", [])),
        drive_pulley,
        series.get("candidate_torque_converter_turbine_rpm", []),
    )
    results = {
        "derived_pulley_ratio": ratios,
        "derived_torque_converter_slip_rpm": slip,
        "derived_drive_minus_turbine_rpm": pulley_difference,
        "derived_longitudinal_acceleration_m_s2": _acceleration(
            series.get("ecm_vehicle_speed_kph", []),
        ),
        "derived_cvt_minus_coolant_c": _temperature_difference(
            series.get("candidate_cvt_fluid_temperature_c", []),
            series.get("ecm_coolant_sensor_1_c", []),
        ),
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
        segments.append(segments[-1] + (later - earlier > _MAX_SPEED_SAMPLE_GAP_SECONDS))

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


def _temperature_difference(cvt: Series, coolant: Series) -> Series:
    if not coolant:
        return []
    times = [timestamp for timestamp, _ in coolant]
    difference = []
    for timestamp, cvt_temperature in cvt:
        index = _nearest_index(times, timestamp, 0, len(times))
        tolerance = _TEMPERATURE_MATCH_SECONDS
        if timestamp - tolerance < times[index] < timestamp + tolerance:
            difference.append([timestamp, cvt_temperature - coolant[index][1]])
    return difference
