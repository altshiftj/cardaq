"""Build a standalone, read-only dashboard from CarDAQ recordings."""

import csv
import hashlib
import json
import re
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from math import isfinite
from os.path import relpath
from pathlib import Path
from statistics import median
from tempfile import NamedTemporaryFile

from ..monitors import diagnostic_observations
from ..pilot_measurements import MEASUREMENT_COLUMNS, transmission_status_byte
from .derived import ADDITIONAL_METRICS, derive_series
from .derived_lessons import DERIVED_LESSONS
from .events import trip_events
from .recorded import RECORDED_GUIDES
from .sensor_lessons import SENSOR_LESSONS
from .standard import STANDARD_CHANNELS, standard_observations
from .thermal import thermal_milestones
from .trip import TRIP_METRICS, derive_trip_series, speed_band_dwell


_UNITS = {"_kph": "km/h", "_rpm": "rpm", "_kpa": "kPa", "_c": "°C", "_v": "V", "_raw": "raw"}
_SOURCES = {"ecm": "ECM", "tcm": "TCM", "honda": "Honda"}
_ASSETS = {
    "__VIEWER_CSS__": "dashboard.css",
    "__VIEWER_RECORDINGS__": "recordings.css",
    "__VIEWER_CHART__": "chart.js",
    "__VIEWER_MISFIRES__": "misfires.js",
    "__VIEWER_APP__": "app.js",
}
_PLACEHOLDERS = re.compile(r"__VIEWER_(?:CSS|RECORDINGS|CHART|MISFIRES|APP|DATA)__")
_SHIFTER_STATUS = "tcm_2322_status_byte_23"
_REPLY_LATENCY = "observed_reply_latency_ms"
_LESSONS = {
    **SENSOR_LESSONS,
    **DERIVED_LESSONS,
    _SHIFTER_STATUS: {
        "plain": "The car sends a little number that may change when you move the gear lever. Each step means the number changed. We’re still matching those numbers to the letters on the dash.",
        "source": "The transmission controller returns a block of bytes for Honda identifier 2322. CarDAQ displays byte 23 exactly as received. Its connection to the physical selector is under investigation.",
        "reading": "Think of each flat stretch as a repeated code. During a parked selector sweep, compare the time of each dashboard position change with the step in this trace. Returning to a position tests whether its code repeats.",
        "caution": "A taller step means a larger byte value. Its height gives no ordering of gears, and the same byte could encode several conditions at once.",
    },
    _REPLY_LATENCY: {
        "plain": "The laptop asks the car questions as you drive. A higher point means it usually waited longer for an answer that second. At 100 milliseconds, that wait was about a tenth of a second.",
        "source": "The laptop timestamps each request and its reply. CarDAQ subtracts the send time from the reply time and plots the median delay for successful requests in each second.",
        "reading": "A point at 60 ms means half the observed round trips in that second took 60 ms or less. Compare a sustained rise with the spacing between samples on other charts.",
        "caution": "The delay includes the adapter, controller, serial link and recorder. A spike cannot identify which part took longer, and a timeout contributes no successful round trip.",
    },
}
_VIEWER_METRICS = {
    "derived_pulley_ratio": {
        "label": "Pulley ratio estimate",
        "unit": "",
        "group": "Derived",
        "precision": 3,
        "description": (
            "Candidate drive pulley RPM divided by candidate output RPM from the same Honda reply, "
            "at road speeds of 10 km/h or above."
        ),
        "interpretation": (
            "At the same road speed, a higher value means the input is turning faster relative to the output. "
            "Compare the relative change across drives while the output shaft scale is still provisional."
        ),
    },
    "derived_torque_converter_slip_rpm": {
        "label": "Torque converter slip estimate",
        "unit": "rpm",
        "group": "Derived",
        "description": (
            "Engine RPM minus candidate turbine RPM from Honda replies up to 150 ms apart, "
            "with the engine at 500 RPM or above."
        ),
        "interpretation": (
            "Positive values put the engine ahead of the turbine. Near zero during steady cruise means their "
            "speeds nearly match. Confirming converter lock-up requires a clutch-state reading."
        ),
    },
    "derived_drive_minus_turbine_rpm": {
        "label": "Drive pulley minus turbine",
        "unit": "rpm",
        "group": "Derived",
        "description": (
            "Candidate drive pulley RPM minus candidate turbine RPM from Honda replies up to 150 ms apart."
        ),
        "interpretation": (
            "Near zero means the two reported speeds track each other. During rapid RPM changes, "
            "the delay between readings can make a brief difference appear larger."
        ),
    },
    "derived_longitudinal_acceleration_m_s2": {
        "label": "Longitudinal acceleration estimate",
        "unit": "m/s²",
        "group": "Derived",
        "precision": 2,
        "description": "Change in road speed per second, estimated from engine module readings about three seconds apart.",
        "interpretation": (
            "Positive peaks mark gains in speed and negative dips mark slowing. Look at pedal position "
            "and fuel flow around a dip for clues about what the driver and engine were doing."
        ),
    },
    "derived_cvt_minus_coolant_c": {
        "label": "CVT fluid minus engine coolant",
        "unit": "°C",
        "group": "Derived",
        "description": "Candidate CVT fluid temperature minus coolant sensor 1, using readings within 0.55 seconds.",
        "interpretation": (
            "A negative value puts the estimated transmission fluid temperature below the coolant temperature. "
            "A climb from below toward zero shows the gap narrowing as the drive progresses."
        ),
    },
    _SHIFTER_STATUS: {
        "label": "Transmission status byte",
        "unit": "",
        "group": "Shifter verification",
        "style": "step",
        "format": "hex",
        "description": "The raw byte at offset 23 in the Honda transmission reply to DID 2322, shown in hexadecimal.",
        "interpretation": (
            "Look for steps that repeat when the selector moves into and out of the same position. "
            "A parked sweep with the dashboard positions recorded can test what the codes mean."
        ),
    },
    _REPLY_LATENCY: {
        "label": "Diagnostic reply latency",
        "unit": "ms",
        "group": "Capture quality",
        "precision": 1,
        "description": "Median time from sending a diagnostic request to receiving its reply, grouped by second.",
        "interpretation": (
            "Peaks mark seconds when successful requests typically took longer, leaving less time for other "
            "readings. Seconds with no successful reply have no latency value."
        ),
    },
    **STANDARD_CHANNELS,
    **TRIP_METRICS,
    **ADDITIONAL_METRICS,
}
_SUMMARY_SERIES = {
    "distanceKm": "derived_distance_km",
    "engineRevolutions": "derived_engine_revolutions",
    "fuelGrams": "derived_fuel_used_g",
    "engineOnStoppedSeconds": "derived_engine_on_stopped_s",
}


def _metric(column: str) -> dict[str, str | int | dict[str, str]]:
    if column in _VIEWER_METRICS:
        return {**_VIEWER_METRICS[column], "lesson": _LESSONS[column]}
    suffix = next(suffix for suffix in _UNITS if column.endswith(suffix))
    key = column.removesuffix(suffix)
    prefix, name = key.split("_", 1)
    label = name.replace("_", " ").capitalize()
    description, interpretation = RECORDED_GUIDES[column]
    if prefix == "candidate":
        if name.startswith("honda_"):
            label = label.removeprefix("Honda ").capitalize()
        label = label.replace("Cvt", "CVT")
        source = "Candidate"
    else:
        source = _SOURCES[prefix]
    return {
        "label": f"{label} · {source}",
        "unit": _UNITS[suffix],
        "group": "Recorded signals",
        "description": description,
        "interpretation": interpretation,
        "lesson": _LESSONS[column],
    }


def _number(text: str | None) -> float | None:
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if isfinite(value) else None


@dataclass
class CaptureSamples:
    timestamp: datetime | None
    timestamp_elapsed: float | None
    series: dict[str, list[list[float]]]
    reply_times: dict[int, list[float]]


def read_capture_samples(
    path: Path, *, extra_decoder: Callable[[str, str], dict] | None = None,
) -> CaptureSamples:
    """Read sorted observations, preserving the original clock for cross-trip comparisons."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        columns = [column for column in MEASUREMENT_COLUMNS if column in fields]
        if "elapsed_s" not in fields or not columns:
            raise ValueError(f"{path} is missing CarDAQ elapsed time or measurement columns.")

        started = None
        timestamp_elapsed = None
        series: dict[str, list[list[float]]] = {column: [] for column in columns}
        status_samples = []
        reply_times: dict[int, list[float]] = {}
        for row in reader:
            elapsed = _number(row.get("elapsed_s"))
            if started is None and row.get("timestamp"):
                try:
                    started = datetime.fromisoformat(row["timestamp"])
                    timestamp_elapsed = elapsed
                except ValueError:
                    pass
            if elapsed is None or elapsed < 0:
                continue
            for column in columns:
                value = _number(row.get(column))
                if value is not None:
                    series[column].append([elapsed, value])
            request = row.get("request") or ""
            reply = row.get("reply") or ""
            for column, value in standard_observations(request, reply).items():
                series.setdefault(column, []).append([elapsed, value])
            if extra_decoder is not None and row.get("event") == "reply":
                for column, value in extra_decoder(request, reply).items():
                    series.setdefault(column, []).append([elapsed, value])
            if request == "222322":
                status = transmission_status_byte(tuple(reply.encode().split(b" | ")))
                if status is not None:
                    status_samples.append([elapsed, status])
            sent = _number(row.get("request_elapsed_s"))
            if row.get("event") == "reply" and sent is not None and 0 <= sent <= elapsed:
                reply_times.setdefault(int(elapsed), []).append(round((elapsed - sent) * 1000, 1))

    series[_SHIFTER_STATUS] = status_samples
    series = {column: points for column, points in series.items() if points}
    if not series:
        raise ValueError(f"{path} has no decoded samples to plot.")
    for points in series.values():
        points.sort(key=lambda point: point[0])
    return CaptureSamples(started, timestamp_elapsed, series, reply_times)


def _misfire_polls(series: dict) -> list[dict]:
    """Keep the reply timestamp of each cycle-counter reading, including unchanged counts."""
    cylinders = []
    for cylinder in range(1, 5):
        polls = []
        previous_seconds = previous_count = None
        cumulative = 0
        for seconds, count in series.get(f"ecm_cyl_{cylinder}_misfires_cycle", []):
            delta = None if previous_count is None else count - previous_count
            if delta is not None and delta > 0:
                cumulative += delta
            polls.append({
                "seconds": seconds, "count": count, "previousSeconds": previous_seconds,
                "delta": delta, "cumulative": cumulative,
            })
            previous_seconds, previous_count = seconds, count
        cylinders.append({"cylinder": cylinder, "polls": polls})
    return cylinders


def _read_capture(path: Path, label: str) -> dict:
    samples = read_capture_samples(path, extra_decoder=diagnostic_observations)
    misfires = _misfire_polls(samples.series)
    series = {
        key: points for key, points in samples.series.items()
        if key in MEASUREMENT_COLUMNS or key in _VIEWER_METRICS
    }
    started = samples.timestamp
    reply_times = samples.reply_times
    end_times = [points[-1][0] for points in series.values()]
    end_times.extend(cyl["polls"][-1]["seconds"] for cyl in misfires if cyl["polls"])
    if not end_times:
        raise ValueError(f"{path} has no decoded samples to plot.")
    span = max(end_times)
    series.update(derive_series(series))
    series.update(derive_trip_series(series))
    if reply_times:
        series[_REPLY_LATENCY] = [
            [second, median(lags)] for second, lags in sorted(reply_times.items())
        ]
    return {
        "name": label,
        "started": (
            f"{started:%b} {started.day}, {started:%Y} · {started.hour % 12 or 12}:{started:%M %p}"
            if started else None
        ),
        "span": span,
        "misfires": misfires,
        "series": series,
        "events": trip_events(series),
        "thermal": thermal_milestones(series),
        "dwell": speed_band_dwell(series.get("ecm_vehicle_speed_kph", [])),
        "summary": {
            field: series[column][-1][1]
            for field, column in _SUMMARY_SERIES.items()
            if column in series
        },
    }


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _comparison_notes(path: Path, fingerprints: list[str], metrics: dict) -> dict[str, str]:
    with path.open(encoding="utf-8-sig") as stream:
        document = json.load(stream)
    if not isinstance(document, dict) or not isinstance(document.get("signals"), dict):
        raise ValueError(f"{path} must contain a signals object and a recording_sha256 list.")
    expected = document.get("recording_sha256")
    if not isinstance(expected, list) or not all(isinstance(digest, str) for digest in expected):
        raise ValueError(f"{path} must list recording_sha256 fingerprints in input order.")
    if [digest.lower() for digest in expected] != fingerprints:
        raise ValueError(f"{path} refers to different recording contents or a different input order.")
    notes = document["signals"]
    for column, note in notes.items():
        if column not in metrics or not isinstance(note, str) or not note.strip():
            raise ValueError(f"{path} needs a plotted signal and a nonempty note for {column!r}.")
    return notes


def _viewer_labels(paths: Sequence[Path], labels: Sequence[str] | None) -> list[str]:
    if not paths:
        raise ValueError("Provide at least one CarDAQ recording.")
    if labels is not None and len(labels) != len(paths):
        raise ValueError("Provide one --label per recording, or omit --label.")
    return [path.stem for path in paths] if labels is None else list(labels)


def _check_viewer_destination(output: Path, paths: Sequence[Path], signal_notes: Path | None) -> None:
    resolved = output.resolve()
    if any(path.resolve() == resolved for path in paths):
        raise ValueError("The viewer output must differ from the input recordings.")
    if signal_notes is not None and signal_notes.resolve() == resolved:
        raise ValueError("The viewer output must differ from the signal notes file.")


def write_viewer(
    paths: Sequence[Path], output: Path, *, labels: Sequence[str] | None = None,
    signal_notes: Path | None = None,
) -> None:
    """Write a single HTML file containing the selected CSVs' decoded readings."""
    names = _viewer_labels(paths, labels)
    if output.suffix.lower() != ".html":
        raise ValueError("The viewer output must have an .html extension.")
    _check_viewer_destination(output, paths, signal_notes)
    write_report_text(output, _viewer_page(paths, names, signal_notes))


def _provenance_path(path: Path, directory: Path) -> str:
    resolved = path.resolve()
    try:
        return Path(relpath(resolved, directory.resolve())).as_posix()
    except ValueError:
        # A relative path cannot span drive letters or UNC shares on Windows.
        return resolved.as_uri()


def write_managed_viewer(
    paths: Sequence[Path], *, labels: Sequence[str] | None = None, signal_notes: Path | None = None,
) -> Path:
    """Export to captures/views with an adjacent JSON record of the ordered inputs."""
    names = _viewer_labels(paths, labels)
    fingerprints = [_file_sha256(path) for path in paths]
    notes_fingerprint = _file_sha256(signal_notes) if signal_notes is not None else None
    identity = json.dumps([list(zip(fingerprints, names, strict=True)), notes_fingerprint], separators=(",", ":"))
    identifier = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    directory = Path.cwd() / "captures" / "views"
    output = directory / f"view-{identifier}.html"
    provenance = output.with_suffix(".json")
    for destination in (output, provenance):
        _check_viewer_destination(destination, paths, signal_notes)
        if destination.is_dir():
            raise IsADirectoryError(f"{destination} is a directory.")

    page = _viewer_page(paths, names, signal_notes, fingerprints=fingerprints)
    if fingerprints != [_file_sha256(path) for path in paths]:
        raise ValueError("A recording changed during export. Finish recording and try again.")

    metadata = {
        "version": 1,
        "output": output.name,
        "inputs": [
            {"path": _provenance_path(path, directory), "sha256": fingerprint, "label": name}
            for path, fingerprint, name in zip(paths, fingerprints, names, strict=True)
        ],
    }
    if signal_notes is not None:
        if notes_fingerprint != _file_sha256(signal_notes):
            raise ValueError("The signal notes changed during export. Try again.")
        metadata["signal_notes"] = {"path": _provenance_path(signal_notes, directory), "sha256": notes_fingerprint}
    contents = json.dumps(metadata, indent=2) + "\n"
    with _stage_report_text(output, page) as staged_page, _stage_report_text(provenance, contents) as staged_provenance:
        staged_page.replace(output)
        staged_provenance.replace(provenance)
    return output


def _viewer_page(
    paths: Sequence[Path], names: Sequence[str], signal_notes: Path | None, *, fingerprints: list[str] | None = None,
) -> str:
    drives = [_read_capture(path, name) for path, name in zip(paths, names, strict=True)]
    used_columns = {column for drive in drives for column in drive["series"]}
    metrics = {
        column: _metric(column)
        for column in (*MEASUREMENT_COLUMNS, *_VIEWER_METRICS)
        if column in used_columns
    }
    data = {"drives": drives, "metrics": metrics}
    if signal_notes is not None:
        if fingerprints is None:
            fingerprints = [_file_sha256(path) for path in paths]
        data["comparisonNotes"] = _comparison_notes(signal_notes, fingerprints, metrics)
    payload = json.dumps(data, separators=(",", ":"))
    resources = files(__package__)
    replacements = {
        placeholder: resources.joinpath(filename).read_text(encoding="utf-8")
        for placeholder, filename in _ASSETS.items()
    }
    replacements["__VIEWER_DATA__"] = payload.replace("<", r"\u003c")
    template = resources.joinpath("dashboard.html").read_text(encoding="utf-8")
    return _PLACEHOLDERS.sub(lambda match: replacements[match[0]], template)


def write_report_text(output: Path, contents: str) -> None:
    """Replace a generated report only after writing it successfully."""
    with _stage_report_text(output, contents) as temporary:
        temporary.replace(output)


@contextmanager
def _stage_report_text(output: Path, contents: str) -> Iterator[Path]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=output.parent, encoding="utf-8", mode="w", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(contents)
            stream.close()
            yield temporary
        finally:
            temporary.unlink(missing_ok=True)
