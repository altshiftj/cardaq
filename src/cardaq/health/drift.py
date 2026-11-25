"""Compare the recent typical trip with a fixed early reference for each indicator."""

from collections import defaultdict, deque
from statistics import median

from .baseline import MIN_HISTORY, _compare


RECENT_TRIPS = 5


def apply_drift(trips: list[dict]) -> None:
    """Annotate trips already validated and chronologically ordered by apply_baselines."""
    anchors = defaultdict(deque)
    recent_windows = defaultdict(lambda: deque(maxlen=RECENT_TRIPS))
    for trip in trips:
        for feature in trip["features"]:
            key = (trip["group"], feature["key"])
            anchor = anchors[key]
            recent = recent_windows[key]
            value = feature["value"]
            if value is not None:
                if len(anchor) < MIN_HISTORY:
                    anchor.append(value)
                else:
                    recent.append(value)

            recent_median = median(recent) if recent else None
            ready = value is not None and len(recent) == RECENT_TRIPS
            score = _compare(recent_median if ready else None, anchor, None, feature.get("minimum_change", 0.0))
            status = score["status"]
            if value is not None and not ready:
                status = "building"
            elif status == "watch":
                status = "shift"
            feature["drift"] = {
                "status": status,
                "direction": score["direction"],
                "anchorN": len(anchor),
                "recentN": len(recent),
                "anchorMedian": score["median"],
                "recentMedian": recent_median,
                "radius": score["radius"],
            }
