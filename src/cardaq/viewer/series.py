"""Work with elapsed-time observations and gaps in recording coverage."""

from bisect import bisect_left, bisect_right
from math import isfinite
from operator import itemgetter


Series = list[list[float]]
SPEED_RPM_GAP_SECONDS = 1.5
FUEL_GAP_SECONDS = 5.0
_TIME = itemgetter(0)


def nearby(points: Series, time: float, tolerance: float) -> float | None:
    """Closest observed value within the tolerance, preferring the earlier sample on ties."""
    index = bisect_left(points, time, key=_TIME)
    neighbors = points[max(0, index - 1):index + 1]
    if not neighbors:
        return None
    timestamp, value = min(neighbors, key=lambda point: abs(point[0] - time))
    return value if abs(timestamp - time) <= tolerance else None


def nonnegative_segments(points: Series, maximum_gap: float) -> list[Series]:
    """Split sorted observations at gaps, skipping nonfinite points and negative values."""
    groups: list[Series] = []
    for point in points:
        time, value = point
        if not isfinite(time) or not isfinite(value) or value < 0:
            continue
        if not groups or time - groups[-1][-1][0] > maximum_gap:
            groups.append([])
        groups[-1].append(point)
    return groups


def interpolated_progress(segments: list[Series], time: float) -> tuple[int, float] | None:
    """Return the segment index and interpolated value if observations cover this time."""
    index = bisect_right(segments, time, key=lambda segment: segment[0][0]) - 1
    if index < 0 or time > segments[index][-1][0]:
        return None
    points = segments[index]
    after = bisect_left(points, time, key=_TIME)
    right_time, right_value = points[after]
    if right_time == time:
        return index, right_value
    left_time, left_value = points[after - 1]
    fraction = (time - left_time) / (right_time - left_time)
    return index, left_value + (right_value - left_value) * fraction
