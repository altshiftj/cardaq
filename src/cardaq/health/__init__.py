"""Build an offline powertrain history from one vehicle's recorded drives."""

import json
import tomllib
from datetime import timedelta, timezone
from importlib.resources import files
from itertools import pairwise
from pathlib import Path
from statistics import median

from ..viewer import read_capture_samples, write_report_text
from ..viewer.derived import derive_series
from ..viewer.series import Series, nearby
from .baseline import MAX_HISTORY, MIN_HISTORY, apply_baselines
from .cvt import cvt_features
from .drift import apply_drift
from .engine import engine_features
from .lessons import FEATURE_LESSONS
from .monitors import diagnostic_observations, monitor_summary


def _text(entry: dict, key: str, default: str | None = None) -> str:
    value = entry.get(key, default)
    if not isinstance(value, str) or (key != "note" and not value.strip()):
        raise ValueError(f"Expected nonempty text for {key!r} in the health manifest.")
    return value.strip()


def _highway_crank_output(series: dict[str, Series]) -> dict:
    torque = dict(series.get("derived_crank_torque_nm", []))
    speed = series.get("ecm_vehicle_speed_kph", [])
    torques, powers = [], []
    for time, kw in series.get("derived_crank_power_kw", []):
        road_speed = nearby(speed, time, 0.75)
        if road_speed is not None and 110 <= road_speed < 120:
            torques.append(torque[time])
            powers.append(kw)
    return {
        "samples": len(powers),
        "medianTorqueNm": median(torques) if torques else None,
        "medianPowerKw": median(powers) if powers else None,
    }


def write_health(manifest: Path, output: Path) -> None:
    """Rebuild a local HTML or JSON history from the CSVs named in the manifest."""
    extension = output.suffix.lower()
    if extension not in (".html", ".json"):
        raise ValueError("Use an .html or .json output for the health history.")
    if output.resolve() == manifest.resolve():
        raise ValueError("Choose a health report output separate from the manifest.")
    with manifest.open("rb") as stream:
        config = tomllib.load(stream)
    vehicle = _text(config, "vehicle")
    entries = config.get("trip")
    if not isinstance(entries, list) or not entries:
        raise ValueError("List at least one [[trip]] in the health manifest.")

    trips = []
    intervals = []
    known_vehicle_code = None
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError("Each [[trip]] must be a table.")
        path = (manifest.parent / _text(entry, "capture")).resolve()
        if output.resolve() == path:
            raise ValueError("Choose a health report output separate from every input recording.")
        label = _text(entry, "label", path.stem)
        group = _text(entry, "group")
        note = _text(entry, "note", "")
        samples = read_capture_samples(path, extra_decoder=diagnostic_observations)
        if samples.vehicle and (code := samples.vehicle["vin_sha256"]):
            if known_vehicle_code is not None and code != known_vehicle_code:
                raise ValueError(f"Trip {index} belongs to a different vehicle. Use one vehicle per health manifest.")
            known_vehicle_code = code
        if samples.timestamp is None or samples.timestamp.utcoffset() is None or samples.timestamp_elapsed is None:
            raise ValueError(f"{path} needs a timestamp with UTC offset and elapsed time for trip history.")
        # Subtract elapsed time on the UTC timeline, including for a subset of a capture.
        start = samples.timestamp.astimezone(timezone.utc) - timedelta(seconds=samples.timestamp_elapsed)
        series = samples.series
        end = start + timedelta(seconds=max(points[-1][0] for points in series.values()))
        intervals.append((start, end, label))
        series.update(derive_series(series))
        cylinders, mil = monitor_summary(series)
        trips.append({
            "date": start.astimezone(samples.timestamp.tzinfo).isoformat(timespec="milliseconds"),
            "label": label, "group": group, "note": note,
            "features": engine_features(series) + cvt_features(series),
            "highwayCrankOutput": _highway_crank_output(series),
            "cylinders": cylinders, "mil": mil,
        })

    intervals.sort()
    for previous, current in pairwise(intervals):
        if current[0] <= previous[1]:
            raise ValueError(
                f"Recordings {previous[2]!r} and {current[2]!r} overlap. "
                "Use one independent recording per journey, including just one version of a culled drive."
            )
    apply_baselines(trips)
    apply_drift(trips)
    report = {"vehicle": vehicle, "minimumHistory": MIN_HISTORY, "maximumHistory": MAX_HISTORY,
              "lessons": FEATURE_LESSONS, "trips": trips}
    if extension == ".html":
        data = json.dumps(report, allow_nan=False, separators=(",", ":")).replace("<", r"\u003c")
        template = files(__package__).joinpath("report.html").read_text(encoding="utf-8")
        contents = template.replace("__HEALTH_DATA__", data)
    else:
        contents = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    write_report_text(output, contents)
