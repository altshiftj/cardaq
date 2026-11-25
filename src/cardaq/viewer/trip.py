"""Derive trip accounting and operating signals from observed ECM readings."""

from bisect import bisect_right
from collections.abc import Callable, Iterable
from itertools import pairwise
from math import expm1, inf, isfinite
from operator import itemgetter

from .series import (
    FUEL_GAP_SECONDS,
    SPEED_RPM_GAP_SECONDS,
    Series,
    interpolated_progress,
    nearby as _nearest,
    nonnegative_segments,
)


_TIME = itemgetter(0)
_FAST_MATCH_SECONDS = 0.65
_PEDAL_MATCH_SECONDS = 1.25
_ROLLING_DISTANCE_KM = 0.5
_ROLLING_REVOLUTIONS = 1000
_DWELL_EDGES = (0, 30, 60, 90, 110, inf)
_DWELL_LABELS = (
    "Stopped", "Moving below 30 km/h", "30 to <60 km/h", "60 to <90 km/h", "90 to <110 km/h", "110+ km/h",
)

TRIP_METRICS = {
    "derived_distance_km": {
        "label": "Distance from vehicle speed",
        "unit": "km",
        "description": "Distance accumulated from road-speed readings no more than 1.5 seconds apart.",
        "interpretation": (
            "On the time axis, steeper sections mean faster travel. The total resumes after a gap "
            "using only the distance covered by available readings."
        ),
        "summary": "change",
        "precision": 3,
    },
    "derived_engine_revolutions": {
        "label": "Cumulative engine revolutions",
        "unit": "rev",
        "description": "Total crankshaft turns accumulated from RPM readings no more than 1.5 seconds apart.",
        "interpretation": (
            "For drives of equal distance, a higher total means the engine turned more times. "
            "Idling adds turns even while the distance trace stays flat."
        ),
        "summary": "change",
        "precision": 0,
    },
    "derived_fuel_used_g": {
        "label": "Cumulative fuel used",
        "unit": "g",
        "description": "Total fuel mass estimated from engine fuel-flow readings no more than five seconds apart.",
        "interpretation": (
            "A steeper climb on the time axis means fuel was used faster. Compare endpoints at equal "
            "distances and check for gaps, since missing fuel-flow intervals add nothing to the total."
        ),
        "summary": "change",
        "precision": 1,
    },
    "derived_rolling_fuel_g_km": {
        "label": "Rolling fuel per kilometer",
        "unit": "g/km",
        "description": "Fuel mass per kilometer over the most recent continuous stretch spanning at least 0.5 km.",
        "interpretation": (
            "Higher values mean more fuel went into covering the same distance. An engine-on stop can "
            "raise this figure as fuel use continues while distance holds steady."
        ),
        "precision": 1,
    },
    "derived_rolling_revolutions_per_km": {
        "label": "Rolling engine revolutions per kilometer",
        "unit": "rev/km",
        "description": "Crankshaft turns per kilometer over the most recent continuous stretch spanning at least 0.5 km.",
        "interpretation": (
            "At steady road speed, a higher value means the engine ran at higher RPM to cover the "
            "same distance. A recent engine-on stop can also lift the reading."
        ),
        "precision": 0,
    },
    "derived_rolling_fuel_per_1000_rev": {
        "label": "Rolling fuel per 1,000 engine revolutions",
        "unit": "g/1,000 rev",
        "description": "Fuel mass per 1,000 crankshaft turns over a recent window spanning at least that many turns.",
        "interpretation": (
            "Higher values mean more fuel was used per engine turn. Read alongside turns per kilometer "
            "to see how a drive can use less fuel per turn yet more fuel per kilometer."
        ),
        "precision": 1,
    },
    "derived_engine_on_stopped_s": {
        "label": "Engine-on stopped time",
        "unit": "s",
        "description": "Time accumulated between consecutive zero-speed readings with engine speed at or above 500 RPM.",
        "interpretation": (
            "Rising stretches mark time spent stationary with the engine running, including warm-up or "
            "traffic stops. An engine-off wait adds no time."
        ),
        "summary": "change",
        "precision": 1,
    },
    "derived_engine_on_stopped_fuel_g": {
        "label": "Fuel used while stopped",
        "unit": "g",
        "description": "Total fuel mass estimated over observed intervals when road speed was zero and the engine was running.",
        "interpretation": (
            "A rise shows how much fuel a stop added to the trip. Compare it with engine-on stopped time "
            "to distinguish a long wait from a short stop with a higher fuel rate."
        ),
        "summary": "change",
        "precision": 1,
    },
    "derived_positive_speed_energy_j_kg": {
        "label": "Speed cycling energy per unit mass",
        "unit": "J/kg",
        "description": "Sum of gains in kinetic energy per kilogram, calculated from road speed smoothed over about 1.5 seconds.",
        "interpretation": (
            "Each gain in speed adds to the total. Repeated accelerations and runs to higher speeds can "
            "both raise it. Gaining speed on a downhill coast counts too."
        ),
        "summary": "change",
        "precision": 1,
    },
    "derived_air_mass_per_cylinder_mg": {
        "label": "Air per cylinder intake event",
        "unit": "mg",
        "description": "Average air mass per cylinder intake stroke, estimated from airflow and RPM for a four-cylinder, four-stroke engine.",
        "interpretation": (
            "At the same RPM, a higher value means more air entered per intake stroke. Compare it with "
            "throttle position and calculated load during a climb or acceleration."
        ),
        "precision": 1,
    },
    "derived_fuel_cut_candidate": {
        "label": "Fuel-cut coasting candidate",
        "unit": "",
        "style": "step",
        "description": (
            "A 1 marks successive zero-fuel readings at 10 km/h or above with the engine running and "
            "the pedal near rest. Other samples with enough data are 0."
        ),
        "interpretation": (
            "A run of 1s is consistent with fuel delivery pausing as the car coasts. The inference "
            "uses reported fuel flow and pedal position. Injector commands would confirm it."
        ),
        "summary": "flag",
        "precision": 0,
    },
}
for _metric in TRIP_METRICS.values():
    _metric["group"] = "Derived"


def derive_trip_series(series: dict[str, Series]) -> dict[str, Series]:
    """Return estimates supported by this capture's sorted observations."""
    speed = series.get("ecm_vehicle_speed_kph", [])
    rpm = series.get("ecm_engine_speed_rpm", [])
    fuel = series.get("ecm_engine_fuel_rate_g_s", [])
    pedal = series.get("ecm_accelerator_pedal_pct", [])
    airflow = series.get("ecm_mass_airflow_g_s", [])

    speed_segments = nonnegative_segments(speed, SPEED_RPM_GAP_SECONDS)
    fuel_segments = nonnegative_segments(fuel, FUEL_GAP_SECONDS)
    distance = _sum_rates(speed_segments, 1 / 3600)
    revolutions = _sum_rates(nonnegative_segments(rpm, SPEED_RPM_GAP_SECONDS), 1 / 60)
    fuel_used = _sum_rates(fuel_segments, 1)
    stopped = list(engine_on_stop_flags(speed_segments, rpm))
    results = {
        "derived_distance_km": _flatten(distance),
        "derived_engine_revolutions": _flatten(revolutions),
        "derived_fuel_used_g": _flatten(fuel_used),
        "derived_rolling_fuel_g_km": _rolling_ratio(fuel_used, distance, _ROLLING_DISTANCE_KM),
        "derived_rolling_revolutions_per_km": _rolling_ratio(revolutions, distance, _ROLLING_DISTANCE_KM),
        "derived_rolling_fuel_per_1000_rev": _rolling_ratio(
            fuel_used, revolutions, _ROLLING_REVOLUTIONS, scale=1000,
        ),
        "derived_engine_on_stopped_s": _flatten(_accumulate(
            stopped, lambda earlier, later: later[0] - earlier[0] if earlier[1] == later[1] == 1 else 0,
        )),
        "derived_engine_on_stopped_fuel_g": _flatten(_accumulate(
            _stopped_fuel_segments(fuel_segments, stopped),
            lambda earlier, later: _trapezoid(earlier, later) if later[2] == 1 else 0,
        )),
        "derived_positive_speed_energy_j_kg": _speed_cycling(speed_segments),
        "derived_air_mass_per_cylinder_mg": _air_per_intake(airflow, rpm),
        "derived_fuel_cut_candidate": _fuel_cut(fuel_segments, pedal, speed, rpm),
    }
    return {key: points for key, points in results.items() if points}


def speed_band_dwell(speed: Series) -> list[dict[str, str | float]]:
    """Count observed seconds by road speed, with a separate zero-speed band."""
    seconds = [0.0] * len(_DWELL_LABELS)
    for segment in nonnegative_segments(speed, SPEED_RPM_GAP_SECONDS):
        for (before, earlier), (after, later) in pairwise(segment):
            elapsed = after - before
            if earlier == later:
                band = bisect_right(_DWELL_EDGES, earlier) if earlier > 0 else 0
                seconds[band] += elapsed
                continue
            low, high = sorted((earlier, later))
            for index, (floor, ceiling) in enumerate(pairwise(_DWELL_EDGES), 1):
                overlap = min(high, ceiling) - max(low, floor)
                if overlap > 0:
                    seconds[index] += elapsed * overlap / (high - low)
    if not any(seconds):
        return []
    return [
        {"label": label, "seconds": duration}
        for label, duration in zip(_DWELL_LABELS, seconds, strict=True)
    ]


def _flatten(segments: Iterable[Series]) -> Series:
    return [point for segment in segments for point in segment]


def _trapezoid(earlier: list[float], later: list[float]) -> float:
    return (later[0] - earlier[0]) * (earlier[1] / 2 + later[1] / 2)


def _sum_rates(segments: Iterable[Series], scale: float) -> list[Series]:
    return _accumulate(segments, lambda earlier, later: _trapezoid(earlier, later) * scale)


def _accumulate(
    segments: Iterable[Series], increment: Callable[[list[float], list[float]], float],
) -> list[Series]:
    total = 0.0
    accumulated = []
    for segment in segments:
        if len(segment) < 2:
            continue
        points = [[segment[0][0], total]]
        for earlier, later in pairwise(segment):
            updated = total + increment(earlier, later)
            if isfinite(updated):
                total = updated
                points.append([later[0], total])
        accumulated.append(points)
    return accumulated


def _rolling_ratio(
    cumulative: list[Series], progress: list[Series], window: float, *, scale: float = 1,
) -> Series:
    ratios = []
    for segment in cumulative:
        aligned: list[tuple[float, float]] = []
        previous_segment = None
        left = 0
        for time, total in segment:
            match = interpolated_progress(progress, time)
            if match is None:
                aligned.clear()
                left = 0
                continue
            index, position = match
            if previous_segment != index:
                aligned.clear()
                left = 0
                previous_segment = index
            aligned.append((position, total))
            if position - aligned[0][0] < window:
                continue
            while position - aligned[left + 1][0] >= window:
                left += 1
            origin, initial_total = aligned[left]
            value = (total - initial_total) / (position - origin) * scale
            if isfinite(value):
                ratios.append([time, value])
    return ratios


def engine_on_stop_flags(speed_segments: list[Series], rpm: Series) -> Iterable[Series]:
    """Yield zero-or-one stop flags for speed observations with nearby engine RPM."""
    for samples in speed_segments:
        stopped = []
        for time, speed in samples:
            engine = _nearest(rpm, time, _FAST_MATCH_SECONDS)
            if engine is None:
                if stopped:
                    yield stopped
                stopped = []
                continue
            stopped.append([time, float(speed == 0 and engine >= 500)])
        if stopped:
            yield stopped


def _stopped_fuel_segments(fuel_segments: list[Series], stopped: list[Series]) -> Iterable[Series]:
    # Use contiguous stopped observations to avoid attributing fuel to a missed launch or shutdown.
    stops = []
    for segment in stopped:
        start = None
        for time, value in segment:
            if value == 1:
                if start is None:
                    start = time
                end = time
            elif start is not None:
                stops.append((start, end))
                start = None
        if start is not None:
            stops.append((start, end))
    for segment in fuel_segments:
        tagged = []
        previous_coverage = None
        for time, rate in segment:
            coverage = bisect_right(stopped, time, key=lambda group: group[0][0]) - 1
            if previous_coverage != coverage or coverage < 0 or time > stopped[coverage][-1][0]:
                if tagged:
                    yield tagged
                tagged = []
                previous_coverage = coverage
            if coverage < 0 or time > stopped[coverage][-1][0]:
                continue
            preceding = tagged[-1][0] if tagged else time
            stop_index = bisect_right(stops, preceding, key=_TIME) - 1
            if stop_index >= 0 and time <= stops[stop_index][1]:
                tagged.append([time, rate, 1])
            else:
                tagged.append([time, rate, 0])
        # The tag on the right endpoint covers exactly the interval being integrated.
        if tagged:
            yield tagged


def _speed_cycling(segments: list[Series]) -> Series:
    smoothed = []
    for segment in segments:
        smooth = segment[0][1] / 3.6
        points = [[segment[0][0], smooth]]
        for earlier, later in pairwise(segment):
            weight = -expm1(-(later[0] - earlier[0]) / 1.5)
            smooth += (later[1] / 3.6 - smooth) * weight
            points.append([later[0], smooth])
        smoothed.append(points)
    return _flatten(_accumulate(
        smoothed, lambda earlier, later: max(0, (later[1] - earlier[1]) * (later[1] + earlier[1]) / 2),
    ))


def _air_per_intake(airflow: Series, rpm: Series) -> Series:
    air = []
    for time, flow in airflow:
        engine = _nearest(rpm, time, _FAST_MATCH_SECONDS)
        if engine is not None and engine >= 500:
            # Each cylinder takes one intake stroke per two revolutions.
            mass = flow / engine * 30000
            if isfinite(mass):
                air.append([time, mass])
    return air


def _fuel_cut(fuel: list[Series], pedal: Series, speed: Series, rpm: Series) -> Series:
    resting = []
    for time, value in pedal:
        road_speed = _nearest(speed, time, _FAST_MATCH_SECONDS)
        engine = _nearest(rpm, time, _FAST_MATCH_SECONDS)
        if road_speed == 0 and engine is not None and 500 <= engine <= 1400:
            resting.append(value)
    if len(resting) < 3:
        return []
    resting.sort()
    baseline = resting[(len(resting) - 1) // 10]
    candidate = []
    for samples in fuel:
        run = []
        for time, flow in samples:
            road_speed = _nearest(speed, time, _FAST_MATCH_SECONDS)
            engine = _nearest(rpm, time, _FAST_MATCH_SECONDS)
            position = _nearest(pedal, time, _PEDAL_MATCH_SECONDS)
            if road_speed is None or engine is None or position is None:
                _mark_fuel_cut(candidate, run)
                run = []
                continue
            eligible = flow == 0 and road_speed >= 10 and engine >= 500 and abs(position - baseline) <= 1
            run.append([time, float(eligible)])
        _mark_fuel_cut(candidate, run)
    return candidate


def _mark_fuel_cut(output: Series, run: Series) -> None:
    for index, (time, eligible) in enumerate(run):
        neighbor = (index > 0 and run[index - 1][1] == 1) or (index + 1 < len(run) and run[index + 1][1] == 1)
        output.append([time, float(eligible and neighbor)])
