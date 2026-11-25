"""Compare the first observed engine warm-up across recordings."""

from bisect import bisect_left, bisect_right
from itertools import pairwise
from operator import itemgetter
from typing import NotRequired, TypedDict

from .series import SPEED_RPM_GAP_SECONDS, Series, interpolated_progress, nonnegative_segments


_TIME = itemgetter(0)
_RUNNING_RPM = 500
_MAX_ENGINE_GAP_SECONDS = 5.0
_MAX_TEMPERATURE_GAP_SECONDS = 5.0
_TEMPERATURE_TARGETS = (
    ("ecm_coolant_sensor_1_c", "Engine coolant sensor 1", (40, 50, 75)),
    ("candidate_cvt_fluid_temperature_c", "CVT fluid estimate", (40, 70)),
    ("ecm_catalyst_temperature_c", "ECU-reported catalyst", (300, 400)),
)


class ThermalMilestone(TypedDict):
    label: str
    target: int
    seconds: float
    distanceKm: NotRequired[float]
    alreadyWarm: NotRequired[bool]


def thermal_milestones(series: dict[str, Series]) -> list[ThermalMilestone]:
    """Return held temperature targets relative to the first observed engine start."""
    run = _first_engine_run(series.get("ecm_engine_speed_rpm", []))
    if run is None:
        return []
    start, end = run
    distance = nonnegative_segments(series.get("derived_distance_km", []), SPEED_RPM_GAP_SECONDS)
    start_distance = interpolated_progress(distance, start)
    milestones: list[ThermalMilestone] = []
    for signal, label, targets in _TEMPERATURE_TARGETS:
        samples = series.get(signal, [])
        first = bisect_left(samples, start, key=_TIME)
        stop = bisect_right(samples, end, key=_TIME)
        for target in targets:
            reached = _first_held_crossing(samples, first, stop, target, start)
            if reached is None:
                continue
            timestamp, already_warm = reached
            milestone: ThermalMilestone = {
                "label": label,
                "target": target,
                "seconds": timestamp - start,
            }
            if already_warm:
                milestone["alreadyWarm"] = True
            position = interpolated_progress(distance, timestamp)
            if start_distance is not None and position is not None:
                milestone["distanceKm"] = position[1] - start_distance[1]
            milestones.append(milestone)
    return milestones


def _first_engine_run(rpm: Series) -> tuple[float, float] | None:
    for index, (current, following) in enumerate(pairwise(rpm)):
        if min(current[1], following[1]) < _RUNNING_RPM:
            continue
        if not 0 < following[0] - current[0] <= _MAX_ENGINE_GAP_SECONDS:
            continue
        if index == 0:
            return None
        preceding_time, preceding_rpm = rpm[index - 1]
        if preceding_rpm >= _RUNNING_RPM or not 0 < current[0] - preceding_time <= _MAX_ENGINE_GAP_SECONDS:
            return None
        return current[0], _end_of_run(rpm, index + 1)
    return None


def _end_of_run(rpm: Series, running_index: int) -> float:
    last_running = rpm[running_index][0]
    for previous, current in pairwise(rpm[running_index:]):
        if current[0] - previous[0] > _MAX_ENGINE_GAP_SECONDS:
            break
        if current[1] >= _RUNNING_RPM:
            last_running = current[0]
        elif previous[1] < _RUNNING_RPM:
            break
    return last_running


def _first_held_crossing(
    samples: Series, first: int, stop: int, target: int, start: float,
) -> tuple[float, bool] | None:
    for index in range(first, stop - 1):
        timestamp, value = samples[index]
        confirmation_time, confirmation = samples[index + 1]
        if min(value, confirmation) < target or not 0 < confirmation_time - timestamp <= _MAX_TEMPERATURE_GAP_SECONDS:
            continue
        if index == 0 or not 0 < timestamp - samples[index - 1][0] <= _MAX_TEMPERATURE_GAP_SECONDS:
            # A sustained reading above target cannot date a crossing inside an outage.
            return None
        if samples[index - 1][1] >= target:
            return (start, True) if index == first else None
        return timestamp, False
    return None
