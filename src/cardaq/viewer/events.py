"""Identify events supported by observations in a recorded trip."""

from collections.abc import Iterator
from heapq import merge
from itertools import groupby, pairwise
from typing import TypedDict

from .series import FUEL_GAP_SECONDS, SPEED_RPM_GAP_SECONDS, Series, nonnegative_segments
from .trip import engine_on_stop_flags


_RUNNING_RPM = 500
_STOP_SECONDS = 5
_LAUNCH_STOP_SECONDS = 3
_LAUNCH_WINDOW_SECONDS = 5
_LAUNCH_SPEED_KPH = 5
_CRUISE_SPEED_KPH = 65
_CRUISE_MAX_SPREAD_KPH = 10
_CRUISE_SECONDS = 20
_GAP_SECONDS = 10


class TripEvent(TypedDict):
    kind: str
    label: str
    start: float
    end: float
    description: str


def trip_events(series: dict[str, Series]) -> list[TripEvent]:
    """Return timestamped events supported by a capture's sorted observations."""
    speed = series.get("ecm_vehicle_speed_kph", [])
    rpm = series.get("ecm_engine_speed_rpm", [])
    fuel_cut = series.get("derived_fuel_cut_candidate", [])
    speed_segments = nonnegative_segments(speed, SPEED_RPM_GAP_SECONDS)
    events: list[TripEvent] = [
        *_engine_starts(rpm),
        *_motion_events(speed_segments),
    ]
    for segment in engine_on_stop_flags(speed_segments, rpm):
        for start, end in _active_ranges(segment, _STOP_SECONDS):
            events.append({
                "kind": "stopped",
                "label": "Stopped with engine on",
                "start": start,
                "end": end,
                "description": "Consecutive zero-speed readings with the engine running.",
            })
    for segment in nonnegative_segments(fuel_cut, FUEL_GAP_SECONDS):
        for start, end in _active_ranges(segment, 2):
            events.append({
                "kind": "fuel-cut",
                "label": "Possible fuel-cut coast",
                "start": start,
                "end": end,
                "description": "Reported fuel flow was zero with the car moving and the pedal near its resting value.",
            })
    times = merge((t for t, _ in speed), (t for t, _ in rpm))
    for before, after in pairwise(times):
        if after - before > _GAP_SECONDS:
            events.append({
                "kind": "telemetry-gap",
                "label": "Telemetry gap",
                "start": before,
                "end": after,
                "description": "No ECM road-speed or engine-RPM samples between these readings.",
            })
    return sorted(events, key=lambda event: (event["start"], event["end"], event["kind"]))


def _engine_starts(rpm: Series) -> list[TripEvent]:
    events: list[TripEvent] = []
    has_run = False
    for segment in nonnegative_segments(rpm, SPEED_RPM_GAP_SECONDS):
        zero_samples = 0
        for time, value in segment:
            if value == 0:
                zero_samples += 1
            elif value >= _RUNNING_RPM:
                if zero_samples >= 2:
                    events.append({
                        "kind": "engine-restart" if has_run else "engine-start",
                        "label": "Engine restart" if has_run else "Engine start",
                        "start": time,
                        "end": time,
                        "description": "First running RPM after at least two observed zero-RPM samples.",
                    })
                has_run = True
                zero_samples = 0
    return events


def _motion_events(speed_segments: list[Series]) -> list[TripEvent]:
    events: list[TripEvent] = []
    for segment in speed_segments:
        stopped = None
        for stationary, run in groupby(segment, key=lambda point: point[1] == 0):
            points = list(run)
            start, end = points[0][0], points[-1][0]
            if stationary:
                stopped = end if end - start >= _LAUNCH_STOP_SECONDS else None
                continue
            if stopped is not None:
                moving = next((time for time, speed in points if speed >= _LAUNCH_SPEED_KPH), None)
                if moving is not None and moving - start <= _LAUNCH_WINDOW_SECONDS:
                    events.append({
                        "kind": "launch",
                        "label": "Launch from stop",
                        "start": stopped,
                        "end": moving,
                        "description": "Road speed reached 5 km/h after at least three seconds of observed zero speed.",
                    })
                stopped = None
            events.extend(_cruises(points))
    return events


def _cruises(points: Series) -> list[TripEvent]:
    events: list[TripEvent] = []
    start = None
    end = low = high = 0.0
    for time, speed in points:
        if start is not None and (
            speed < _CRUISE_SPEED_KPH or max(high, speed) - min(low, speed) > _CRUISE_MAX_SPREAD_KPH
        ):
            if end - start >= _CRUISE_SECONDS:
                events.append(_cruise_event(start, end, low, high))
            start = None
        if speed >= _CRUISE_SPEED_KPH:
            low = speed if start is None else min(low, speed)
            high = speed if start is None else max(high, speed)
            start = time if start is None else start
            end = time
    if start is not None and end - start >= _CRUISE_SECONDS:
        events.append(_cruise_event(start, end, low, high))
    return events


def _cruise_event(start: float, end: float, low: float, high: float) -> TripEvent:
    speed_range = f"{low:g} km/h" if low == high else f"{low:g}–{high:g} km/h"
    return {
        "kind": "cruise",
        "label": "Steady-speed stretch",
        "start": start,
        "end": end,
        "description": f"Observed road speed stayed within {speed_range} for at least 20 seconds.",
    }


def _active_ranges(points: Series, minimum_seconds: float) -> Iterator[tuple[float, float]]:
    for active, observations in groupby(points, key=lambda point: point[1] == 1):
        if active:
            run = list(observations)
            start, end = run[0][0], run[-1][0]
            if end - start >= minimum_seconds:
                yield start, end
