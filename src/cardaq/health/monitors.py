"""Summarize ECM diagnostic observations for longitudinal health history."""

from ..monitors import diagnostic_observations as diagnostic_observations


def monitor_summary(series: dict) -> tuple[list[dict], dict]:
    """Summarize sorted counter snapshots, retaining decreases and first observed peaks."""
    cylinders = []
    for cylinder in range(1, 5):
        current = series.get(f"ecm_cyl_{cylinder}_misfires_cycle", [])
        weighted = series.get(f"ecm_cyl_{cylinder}_misfires_weighted", [])
        peak_time, peak = max(current, key=lambda p: p[1], default=(None, None))
        transitions = []
        for seconds, count in current:
            if not transitions or count != transitions[-1]["count"]:
                transitions.append({"seconds": seconds, "count": count})
        cylinders.append({
            "cylinder": cylinder, "polls": len(current),
            "first": current[0][1] if current else None, "last": current[-1][1] if current else None,
            "peak": peak, "peakElapsed": peak_time, "transitions": transitions,
            "weightedLast": weighted[-1][1] if weighted else None, "weightedPolls": len(weighted),
        })
    lamps = series.get("ecm_mil_on", [])
    counts = series.get("ecm_confirmed_dtc_count", [])
    mil = {
        "polls": len(lamps), "everOn": any(value for _, value in lamps) if lamps else None,
        "maxCount": max((value for _, value in counts), default=None),
    }
    return cylinders, mil
