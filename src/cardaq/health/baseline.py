"""Compare a vehicle's trip summaries with earlier observations from the same cohort."""

from collections import defaultdict, deque
from datetime import datetime
from math import isfinite, ulp
from statistics import median


MIN_HISTORY = 8
MAX_HISTORY = 30
MODIFIED_Z_LIMIT = 3.5
MAD_SCALE = 0.6745


def _compare(value: float | None, history: deque, previous_direction: str | None, floor: float) -> dict:
    center = median(history) if history else None
    mad = median(abs(prior - center) for prior in history) if history else None
    result = {
        "n": len(history), "median": center, "mad": mad, "radius": None,
        "direction": None, "status": "building",
    }
    if value is None:
        result["status"] = "insufficient_samples"
        return result
    if len(history) < MIN_HISTORY:
        return result

    # Ignore spread at the precision of the arithmetic. A known measurement
    # resolution still permits comparison when earlier medians were identical.
    flat = mad <= 8 * ulp(max(abs(center), 1.0))
    if flat and floor == 0:
        result["status"] = "flat_reference"
        return result
    radius = floor if flat else max(floor, MODIFIED_Z_LIMIT * mad / MAD_SCALE)
    result["radius"] = radius
    delta = value - center
    if abs(delta) <= radius:
        result["status"] = "within_reference"
        return result

    direction = "higher" if delta > 0 else "lower"
    result["direction"] = direction
    result["status"] = "repeat" if previous_direction == direction else "watch"
    return result


def _start(trip: dict) -> datetime:
    start = datetime.fromisoformat(trip["date"])
    if start.utcoffset() is None:
        raise ValueError("Health history requires trip start times with a UTC offset.")
    return start


def apply_baselines(trips: list[dict]) -> None:
    """Sort one vehicle's trips and attach a baseline dict to each feature.

    Each eligible trip contributes one value per (group, feature key). Its
    comparison uses up to 30 strictly earlier eligible trips, including prior
    review flags. Eight earlier values are required to screen a new value.
    A positive minimum_change bounds the review radius in the feature's units.
    Equal-to-boundary values stay within the reference. Two successive eligible
    departures in the same direction produce "repeat". Missing values carry no
    vote and leave the previous direction intact.
    """
    ordered = sorted(trips, key=_start)
    previous_start = None
    history = defaultdict(lambda: deque(maxlen=MAX_HISTORY))
    previous_directions = {}
    annotations = []
    for trip in ordered:
        start = _start(trip)
        if start == previous_start:
            raise ValueError(f"Two trips have the same start instant: {trip['date']}. Use one recording per trip.")
        previous_start = start
        seen_features = set()
        for feature in trip["features"]:
            key = (trip["group"], feature["key"])
            if key in seen_features:
                raise ValueError(f"Multiple values for feature {feature['key']!r} on {trip['date']}.")
            seen_features.add(key)
            value = feature["value"]
            if value is not None and not isfinite(value):
                raise ValueError(f"Non-finite trip feature {feature['key']!r} on {trip['date']}.")
            floor = feature.get("minimum_change", 0.0)
            if not isfinite(floor) or floor < 0:
                raise ValueError(f"Invalid minimum change for feature {feature['key']!r}.")
            prior = history[key]
            baseline = _compare(value, prior, previous_directions.get(key), floor)
            annotations.append((feature, baseline))
            if value is not None:
                prior.append(value)
                previous_directions[key] = baseline["direction"]

    for feature, baseline in annotations:
        feature["baseline"] = baseline
    trips[:] = ordered
