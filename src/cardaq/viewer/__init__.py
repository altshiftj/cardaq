"""Build a standalone, read-only dashboard from CarDAQ recordings."""

import csv
import json
import re
from collections.abc import Sequence
from datetime import datetime
from importlib.resources import files
from math import isfinite
from pathlib import Path
from tempfile import NamedTemporaryFile

from ..pilot_measurements import MEASUREMENT_COLUMNS, transmission_status_byte
from .derived import derive_series


_UNITS = {"_kph": "km/h", "_rpm": "rpm", "_kpa": "kPa", "_c": "°C", "_v": "V", "_raw": "raw"}
_SOURCES = {"ecm": "ECM", "tcm": "TCM", "honda": "Honda"}
_ASSETS = {
    "__VIEWER_CSS__": "dashboard.css",
    "__VIEWER_CHART__": "chart.js",
    "__VIEWER_APP__": "app.js",
}
_PLACEHOLDERS = re.compile(r"__VIEWER_(?:CSS|CHART|APP|DATA)__")
_SHIFTER_STATUS = "tcm_2322_status_byte_23"
_VIEWER_METRICS = {
    "derived_pulley_ratio": {
        "label": "Pulley ratio estimate",
        "unit": "",
        "group": "Derived",
        "precision": 3,
        "description": (
            "Drive pulley RPM divided by the candidate output RPM from the same reply, "
            "at 10 km/h or above. The output shaft scale still needs confirmation."
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
    },
    "derived_drive_minus_turbine_rpm": {
        "label": "Drive pulley minus turbine",
        "unit": "rpm",
        "group": "Derived",
        "description": (
            "Candidate drive pulley RPM minus turbine RPM from Honda replies up to 150 ms apart. "
            "The difference shows when the shafts spin at different speeds."
        ),
    },
    "derived_longitudinal_acceleration_m_s2": {
        "label": "Longitudinal acceleration estimate",
        "unit": "m/s²",
        "group": "Derived",
        "precision": 2,
        "description": "Rate of change in ECM vehicle speed over about three seconds. Negative values show slowing.",
    },
    "derived_cvt_minus_coolant_c": {
        "label": "CVT fluid minus engine coolant",
        "unit": "°C",
        "group": "Derived",
        "description": "Candidate CVT fluid temperature minus ECM coolant sensor 1 within 0.55 seconds.",
    },
    _SHIFTER_STATUS: {
        "label": "Transmission status byte",
        "unit": "",
        "group": "Shifter verification",
        "style": "step",
        "format": "hex",
        "description": (
            "DID 2322 data byte at offset 23. Values 0x70 and 0x78 marked the suspected Sport stretch "
            "on the home drive. Compare against known shifter positions to verify."
        ),
    },
}


def _metric(column: str) -> dict[str, str | int]:
    if column in _VIEWER_METRICS:
        return _VIEWER_METRICS[column]
    suffix = next(suffix for suffix in _UNITS if column.endswith(suffix))
    key = column.removesuffix(suffix)
    prefix, name = key.split("_", 1)
    label = name.replace("_", " ").capitalize()
    if prefix == "candidate":
        if name.startswith("honda_"):
            label = label.removeprefix("Honda ").capitalize()
        label = label.replace("Cvt", "CVT")
        return {
            "label": f"{label} · Candidate",
            "unit": _UNITS[suffix],
            "group": "Recorded signals",
            "description": "Provisional Honda signal. Its identification or scale still needs verification.",
        }
    return {
        "label": f"{label} · {_SOURCES[prefix]}",
        "unit": _UNITS[suffix],
        "group": "Recorded signals",
        "description": "",
    }


def _number(text: str | None) -> float | None:
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return value if isfinite(value) else None


def _start_time(timestamp: str | None) -> str | None:
    if not timestamp:
        return None
    try:
        started = datetime.fromisoformat(timestamp)
    except ValueError:
        return None
    return f"{started:%b} {started.day}, {started:%Y} · {started.hour % 12 or 12}:{started:%M %p}"


def _read_capture(path: Path, label: str) -> dict:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        columns = [column for column in MEASUREMENT_COLUMNS if column in fields]
        if "elapsed_s" not in fields or not columns:
            raise ValueError(f"{path} is missing CarDAQ elapsed time or measurement columns.")

        started = None
        series: dict[str, list[list[float]]] = {column: [] for column in columns}
        status_samples = []
        for row in reader:
            if started is None:
                started = _start_time(row.get("timestamp"))
            elapsed = _number(row.get("elapsed_s"))
            if elapsed is None or elapsed < 0:
                continue
            for column in columns:
                value = _number(row.get(column))
                if value is not None:
                    series[column].append([elapsed, value])
            if row.get("request") == "222322":
                reply = (row.get("reply") or "").encode().split(b" | ")
                status = transmission_status_byte(tuple(reply))
                if status is not None:
                    status_samples.append([elapsed, status])

    series[_SHIFTER_STATUS] = status_samples
    series = {column: points for column, points in series.items() if points}
    if not series:
        raise ValueError(f"{path} has no decoded samples to plot.")
    for points in series.values():
        points.sort(key=lambda point: point[0])
    series.update(derive_series(series))
    return {
        "name": label,
        "started": started,
        "span": max(points[-1][0] for points in series.values()),
        "series": series,
    }


def write_viewer(paths: Sequence[Path], output: Path, *, labels: Sequence[str] | None = None) -> None:
    """Write a single HTML file containing the selected CSVs' decoded readings."""
    if not paths:
        raise ValueError("Provide at least one CarDAQ recording.")
    if labels is not None and len(labels) != len(paths):
        raise ValueError("Provide one --label per recording, or omit --label.")
    if output.suffix.lower() != ".html":
        raise ValueError("The viewer output must have an .html extension.")
    if any(path.resolve() == output.resolve() for path in paths):
        raise ValueError("The viewer output must differ from the input recordings.")

    names = [path.stem for path in paths] if labels is None else labels
    drives = [_read_capture(path, name) for path, name in zip(paths, names, strict=True)]
    used_columns = {column for drive in drives for column in drive["series"]}
    metrics = {
        column: _metric(column)
        for column in (*MEASUREMENT_COLUMNS, *_VIEWER_METRICS)
        if column in used_columns
    }
    payload = json.dumps({"drives": drives, "metrics": metrics}, separators=(",", ":"))
    resources = files(__package__)
    replacements = {
        placeholder: resources.joinpath(filename).read_text(encoding="utf-8")
        for placeholder, filename in _ASSETS.items()
    }
    replacements["__VIEWER_DATA__"] = payload.replace("<", r"\u003c")
    template = resources.joinpath("dashboard.html").read_text(encoding="utf-8")
    page = _PLACEHOLDERS.sub(lambda match: replacements[match[0]], template)

    output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=output.parent, encoding="utf-8", mode="w", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(page)
            stream.close()
            temporary.replace(output)
        finally:
            temporary.unlink(missing_ok=True)
