"""Record read-only diagnostic traffic directly to a durable CSV."""

import csv
import hashlib
import json
import os
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import monotonic, sleep
from typing import TextIO
from uuid import uuid4

from serial import Serial

from .adapter import AdapterError, open_connection, request
from .config import SerialSettings
from .obd import SweepResult, discover_standard
from .obd_frames import has_pid_reply
from .pilot_measurements import MEASUREMENT_COLUMNS, pilot_measurements


_CIVIC_PIDS = (
    b"01 03 04 06 07 0B 0C 0D 0E 11 13 15 1C 1F 21 24 2E 2F 30 31 32 33 "
    b"3C 41 42 43 44 47 49 4A 51 55 56 62 63 66 67 68 6C 8E 9D 9E 9F A6"
).split()
_FAST_REQUESTS = (b"010C", b"010D", b"0167", b"0142")
_OTHER_REQUESTS = tuple(b"01" + pid for pid in _CIVIC_PIDS if b"01" + pid not in _FAST_REQUESTS)
_MONITOR_REQUESTS = (b"06A2", b"06A3", b"06A4", b"06A5")
_TCM_REQUESTS = (b"222301", b"222322")
_FUNCTIONAL_HEADER = b"ATSH18DB33F1"
_TCM_HEADER = b"ATSH18DA1EF1"
_RECONNECT_SECONDS = 1.0
_SYNC_SECONDS = 1.0
_MONITOR_SECONDS = 60.0


@dataclass(frozen=True)
class CaptureResult:
    path: Path
    stop_reason: str
    replies: int


class _CaptureCsv:
    def __init__(self, stream: TextIO, started: float) -> None:
        self.stream = stream
        self.started = self.last_sync = started
        self.writer = csv.DictWriter(
            stream, fieldnames=(
                "timestamp", "elapsed_s", "request_elapsed_s", "event", "request", "reply", "detail",
                *MEASUREMENT_COLUMNS,
            )
        )
        self.writer.writeheader()

    def write(
        self, event: str, command: bytes = b"", reply: tuple[bytes, ...] = (), detail: str = "",
        measurements: dict[str, int | float] | None = None,
        sent: float | None = None, *, timestamp: datetime | None = None,
    ) -> None:
        now = monotonic()
        frames = (line.decode("ascii", errors="backslashreplace") for line in reply)
        self.writer.writerow({
            "timestamp": (timestamp or datetime.now()).astimezone().isoformat(timespec="milliseconds"),
            "elapsed_s": f"{now - self.started:.3f}",
            "request_elapsed_s": "" if sent is None else f"{sent - self.started:.3f}",
            "event": event,
            "request": command.decode("ascii"),
            "reply": " | ".join(frames),
            "detail": detail,
            **(measurements or {}),
        })
        self.stream.flush()
        if event in ("start", "transport_error", "end") or now - self.last_sync >= _SYNC_SECONDS:
            os.fsync(self.stream.fileno())
            self.last_sync = now


def record(
    settings: SerialSettings, output: Path | None, duration: float, *, note: str = "",
    profile: str = "honda-civic", notify: Callable[[str], None] = print,
) -> CaptureResult:
    """Log the selected profile, using the dated capture library when output is absent."""
    if not isfinite(duration) or duration <= 0:
        raise ValueError("Capture duration must be a finite positive number of seconds.")

    if profile not in ("honda-civic", "standard"):
        raise ValueError(f"Unknown polling profile {profile!r}.")

    if output is not None:
        output = output.resolve()
        stop_path = output.with_suffix(output.suffix + ".stop")
        if stop_path.exists():
            raise FileExistsError(f"The stop file {stop_path} already exists. Use a fresh output path.")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="") as stream:
            return _record_csv(settings, output, stream, duration, note, profile, notify)

    created = datetime.now(timezone.utc)
    output, stream = _new_managed_capture(created)
    sidecar = output.with_suffix(".capture.json")
    metadata: dict[str, str | int | None] = {
        "schema_version": 1,
        "capture_id": output.stem,
        "csv": output.name,
        "created_utc": _utc_timestamp(created),
        "started_utc": None,
        "format": "cardaq-csv",
        "source": "cardaq-record",
        "polling_profile": profile,
        "status": "recording",
        "stop_reason": None,
        "replies": None,
        "sha256": None,
    }

    def mark_recording(started: datetime) -> None:
        metadata["started_utc"] = _utc_timestamp(started)
        _write_metadata(sidecar, metadata)

    try:
        with stream:
            result = _record_csv(settings, output, stream, duration, note, profile, notify, on_start=mark_recording)
        with output.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        _write_metadata(sidecar, {
            **metadata, "status": "complete", "stop_reason": result.stop_reason,
            "replies": result.replies, "sha256": digest,
        })
    except BaseException:
        with suppress(OSError):
            _write_metadata(sidecar, {**metadata, "status": "failed"})
        raise
    return result


def _utc_timestamp(when: datetime) -> str:
    return when.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _new_managed_capture(created: datetime) -> tuple[Path, TextIO]:
    directory = (Path.cwd() / "captures" / "recordings" / created.date().isoformat()).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    prefix = created.strftime("%Y%m%dT%H%M%S.%fZ")
    for _ in range(10):
        output = directory / f"{prefix}-{uuid4().hex}.csv"
        if output.with_suffix(".capture.json").exists() or output.with_suffix(".csv.stop").exists():
            continue
        try:
            return output, output.open("x", encoding="utf-8", newline="")
        except FileExistsError:
            continue
    raise FileExistsError(f"Could not allocate a unique capture in {directory}.")


def _write_metadata(path: Path, metadata: dict[str, str | int | None]) -> None:
    stream = NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", newline="\n", delete=False)
    temporary = Path(stream.name)
    try:
        with stream:
            json.dump(metadata, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


def _record_csv(
    settings: SerialSettings, output: Path, stream: TextIO, duration: float, note: str,
    profile: str, notify: Callable[[str], None], *, on_start: Callable[[datetime], None] | None = None,
) -> CaptureResult:
    started = monotonic()
    log = _CaptureCsv(stream, started)
    if on_start is None:
        log.write("start", detail=note)
    else:
        timestamp = datetime.now(timezone.utc)
        log.write("start", detail=note, timestamp=timestamp)
        on_start(timestamp)
    notify(f"Recording to {output}")
    stop_path = output.with_suffix(output.suffix + ".stop")
    capture = _Capture(settings, log, stop_path, started + duration, notify)
    try:
        reason = capture.run(profile)
    except KeyboardInterrupt:
        reason = "interrupted"
    log.write("end", detail=reason)
    return CaptureResult(output, reason, capture.replies)


class _Capture:
    def __init__(
        self, settings: SerialSettings, log: _CaptureCsv, stop_path: Path, deadline: float,
        notify: Callable[[str], None],
    ) -> None:
        self.settings = settings
        self.log = log
        self.stop_path = stop_path
        self.deadline = deadline
        self.notify = notify
        self.replies = 0
        self.ecm_ready = False
        self.next_monitors = log.started
        self.next_progress = log.started + 30.0

    def stop_reason(self) -> str | None:
        if self.stop_path.exists():
            return "stop_requested"
        if monotonic() >= self.deadline:
            return "duration"
        return None

    def run(self, profile: str) -> str:
        while (reason := self.stop_reason()) is None:
            try:
                with open_connection(self.settings) as port:
                    if profile == "standard":
                        try:
                            inventory = discover_standard(port, self.settings.timeout)
                            self.capture_standard(port, inventory)
                        finally:
                            with suppress(AdapterError):
                                self.configure(port, b"ATH0")
                        continue
                    self.configure(port, b"ATTP7", b"ATAR", _FUNCTIONAL_HEADER, b"ATH1", b"ATCAF1", b"ATCFC1")
                    self.capture_connected(port)
                    self.configure(port, _FUNCTIONAL_HEADER, b"ATAR", b"ATH0")
            except AdapterError as error:
                self.log.write("transport_error", detail=str(error))
                if profile == "standard":
                    self.notify(f"Retrying standard discovery: {error}")
                self.wait_for_retry()
        return reason

    def capture_standard(self, port: Serial, inventory: SweepResult) -> None:
        responders: dict[bytes, set[str]] = {}
        for ecu in inventory.ecus:
            for pid in ecu.pids:
                responders.setdefault(f"01{pid:02X}".encode("ascii"), set()).add(ecu.address)
        detail = {ecu.address: [f"{pid:02X}" for pid in ecu.pids] for ecu in inventory.ecus}
        self.log.write("inventory", detail=json.dumps(detail))
        if not responders:
            raise AdapterError("No standard data PIDs advertised.")
        width = len(inventory.ecus[0].address)
        commands = sorted(responders, key=lambda cmd: (cmd not in (b"010C", b"010D"), cmd))
        ready = False
        while self.stop_reason() is None:
            before = self.replies
            for command in commands:
                if self.stop_reason() is not None:
                    return
                self.poll(port, command, standard_width=width, responders=responders[command])
                if not ready and self.replies > before:
                    self.notify(f"Ready: received {command.decode()} data; polling {len(commands)} advertised PIDs.")
                    ready = True
            if self.replies == before:
                raise AdapterError("No advertised data PID returned a positive reply.")

    def configure(self, port: Serial, *commands: bytes) -> None:
        for command in commands:
            if request(port, command, self.settings.timeout) != (b"OK",):
                raise AdapterError(f"Adapter did not acknowledge {command.decode('ascii')}.")

    def capture_connected(self, port: Serial) -> None:
        while self.stop_reason() is None:
            rpm = self.poll(port, _FAST_REQUESTS[0]).get("ecm_engine_speed_rpm")
            if rpm is None:
                self.wait_for_retry()
                continue

            for command in _FAST_REQUESTS[1:]:
                self.poll(port, command)
            self.poll_tcm(port)
            if not self.ecm_ready and self.stop_reason() is None:
                self.ecm_ready = True
                self.notify(f"Ready: ECM answered at {rpm:g} RPM. Initial reads are in the CSV.")

            for index, command in enumerate(_OTHER_REQUESTS):
                if self.stop_reason() is not None:
                    return
                if index in (13, 26):
                    for fast_command in _FAST_REQUESTS:
                        self.poll(port, fast_command)
                if index == 20:
                    self.poll_tcm(port)
                self.poll(port, command)

            if monotonic() >= self.next_monitors:
                for command in _MONITOR_REQUESTS:
                    self.poll(port, command)
                self.next_monitors = monotonic() + _MONITOR_SECONDS
            self.poll(port, b"ATRV")

    def poll_tcm(self, port: Serial) -> None:
        if self.stop_reason() is not None:
            return
        self.configure(port, _TCM_HEADER)
        for command in _TCM_REQUESTS:
            self.poll(port, command)
        self.configure(port, _FUNCTIONAL_HEADER)

    def poll(
        self, port: Serial, command: bytes, *, standard_width: int | None = None, responders: set[str] | None = None,
    ) -> dict[str, int | float]:
        if self.stop_reason() is not None:
            return {}
        sent = monotonic()
        reply = request(port, command, self.settings.timeout)
        measurements = pilot_measurements(command, reply, standard_width=standard_width)
        if standard_width is not None and responders is not None:
            positive = has_pid_reply(reply, int(command[2:], 16), responders, standard_width)
        else:
            positive = bool(measurements) or any(line[:2] == b"18" for line in reply)
        if not reply or reply == (b"NO DATA",):
            event = "no_data"
        elif positive:
            event = "reply"
            self.replies += 1
        else:
            event = "adapter_status"
        self.log.write(event, command, reply, measurements=measurements, sent=sent)
        if monotonic() >= self.next_progress:
            self.notify(f"{self.replies} replies saved after {monotonic() - self.log.started:.0f} seconds.")
            self.next_progress = monotonic() + 30.0
        return measurements

    def wait_for_retry(self) -> None:
        if self.stop_reason() is None:
            sleep(min(_RECONNECT_SECONDS, max(0.0, self.deadline - monotonic())))
