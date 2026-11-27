import csv
import hashlib
import json
import os
import re
import unittest
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from serial import Serial

from cardaq.adapter import AdapterError
from cardaq.capture import record
from cardaq.config import SerialSettings
from cardaq.obd import EcuPids, SweepResult
from cardaq.vehicle import Vehicle
from cardaq.viewer import read_capture_samples, write_viewer
from cardaq.viewer.derived import derive_series


_ENGINE_OFF = b"18 DA F1 10 04 41 0C 00 00"
_ENGINE_RUNNING = b"18 DA F1 10 04 41 0C 1F 40"
_CIVIC_INVENTORY = SweepResult((EcuPids("18DAF110", (0x0C,)),), ())
_CIVIC = Vehicle("19XFC2F60LE000001", "identified", ("18DAF110",), "2020 Honda Civic LX", "honda-civic")


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class CaptureReplayTests(unittest.TestCase):
    def test_serial_recording_replays_diagnostic_values_and_timing(self) -> None:
        directory = Path(self.enterContext(TemporaryDirectory()))
        capture = directory / "drive.csv"
        viewer = directory / "drive.html"
        clock = FakeClock()
        self.enterContext(patch("cardaq.capture.monotonic", clock.monotonic))
        self.enterContext(patch("cardaq.adapter.monotonic", clock.monotonic))
        self.enterContext(patch("cardaq.capture.sleep", clock.sleep))
        connection = MagicMock(spec=Serial)
        connection.port = "test-serial"
        self.enterContext(patch("cardaq.adapter.serial.Serial", return_value=connection))

        functional, transmission = b"18DB33F1", b"18DA1EF1"
        active_header = None
        headers_visible = False
        sent_at = defaultdict(list)
        transmission_reply = (
            b"18 DA F1 1E 10 27 62 23 22 BE 7F 7F",
            b"18 DA F1 1E 21 FF 32 00 00 00 00 00",
            b"18 DA F1 1E 22 00 00 00 04 D2 02 58",
            b"18 DA F1 1E 23 1B 00 14 00 00 00 30",
            b"18 DA F1 1E 24 00 00 64 00 A1 05 00",
            b"18 DA F1 1E 25 3B 00 83 FC EA 55 55",
        )
        replies = {
            b"010C": (_ENGINE_RUNNING,),
            b"010D": (b"18 DA F1 10 03 41 0D 32",),
            b"222322": transmission_reply,
            b"ATRV": (b"12.5V",),
        }

        def exchange(wire_command: bytes) -> int:
            nonlocal active_header, headers_visible
            self.assertTrue(wire_command.endswith(b"\r"), wire_command)
            command = wire_command[:-1]
            if command.startswith(b"AT") and command != b"ATRV":
                if command.startswith(b"ATSH"):
                    active_header = command[4:]
                    self.assertIn(active_header, (functional, transmission))
                if command in (b"ATH0", b"ATH1"):
                    headers_visible = command == b"ATH1"
                reply = (b"OK",)
            else:
                if command != b"ATRV":
                    self.assertTrue(headers_visible, command)
                    self.assertTrue(command.startswith((b"01", b"06", b"22")), command)
                    self.assertEqual(active_header, transmission if command.startswith(b"22") else functional, command)
                sent_at[command].append(clock.now)
                clock.sleep(0.125)
                reply = replies.get(command, (b"NO DATA",))
                if command == b"06A3":
                    count = b"03" if len(sent_at[command]) == 1 else b"05"
                    reply = (b"18 DA F1 10 10 0A 46 A3 0C 24 00 " + count, b"18 DA F1 10 21 00 00 FF FF")
            connection.read.side_effect = BytesIO(b"\r".join((command, *reply, b">"))).read
            return len(wire_command)

        connection.write.side_effect = exchange
        self.enterContext(patch("cardaq.capture.discover_standard", return_value=_CIVIC_INVENTORY))
        self.enterContext(patch("cardaq.capture._read_vehicle", return_value=_CIVIC))
        with patch("cardaq.capture.os.fsync"):
            result = record(SerialSettings(connection.port), capture, 90, notify=lambda _: None)

        self.assertEqual(result.stop_reason, "duration")
        self.assertEqual(active_header, functional)
        self.assertFalse(headers_visible)
        connection.close.assert_called_once_with()
        self.assertIn(b"222301", sent_at)
        self.assertIn(b"222322", sent_at)
        for command in (b"06A2", b"06A3", b"06A4", b"06A5"):
            with self.subTest(command=command):
                self.assertEqual(len(sent_at[command]), 2)
                first, second = sent_at[command]
                self.assertLess(first, 15)
                self.assertGreaterEqual(second - first, 60)
                self.assertLessEqual(second - first, 75)

        with capture.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, strict=True))
        self.assertEqual(result.replies, sum(row["event"] == "reply" for row in rows))
        first_rpm = next(row for row in rows if row["request"] == "010C")
        self.assertEqual(
            [float(first_rpm[field]) for field in ("request_elapsed_s", "elapsed_s", "ecm_engine_speed_rpm")],
            [0.0, 0.125, 2000.0],
        )
        did = next(row for row in rows if row["request"] == "222322")
        self.assertEqual(did["reply"], " | ".join(frame.decode("ascii") for frame in transmission_reply))
        self.assertEqual(float(did["candidate_torque_converter_turbine_rpm"]), 1234)
        monitor_rows = [row for row in rows if row["request"] == "06A3"]
        self.assertEqual([row["event"] for row in monitor_rows], ["reply", "reply"])
        self.assertEqual(
            [(float(row["request_elapsed_s"]), float(row["elapsed_s"])) for row in monitor_rows],
            [(sent, sent + 0.125) for sent in sent_at[b"06A3"]],
        )

        write_viewer([capture], viewer)
        html = viewer.read_text(encoding="utf-8")
        script = re.search(r'<script\b[^>]*\bid="capture-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        self.assertIsNotNone(script)
        drive, = json.loads(script[1])["drives"]
        cylinder = next(item for item in drive["misfires"] if item["cylinder"] == 2)
        first, second = (sent + 0.125 for sent in sent_at[b"06A3"])
        self.assertEqual(cylinder["polls"], [
            {"seconds": first, "count": 3, "previousSeconds": None, "delta": None, "cumulative": 0},
            {"seconds": second, "count": 5, "previousSeconds": first, "delta": 2, "cumulative": 2},
        ])
        latency = dict(drive["series"]["observed_reply_latency_ms"])
        self.assertEqual([latency[0], latency[int(second)]], [125, 125])


class CaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = self.enterContext(TemporaryDirectory())
        self.output = Path(directory) / "commute.csv"
        self.stop_file = self.output.with_suffix(".csv.stop")
        self.settings = SerialSettings("test-serial")
        self.clock = FakeClock()
        self.opened = 0
        self.closed = 0
        self.enterContext(patch("cardaq.capture.monotonic", self.clock.monotonic))
        self.enterContext(patch("cardaq.capture.sleep", self.clock.sleep))
        self.enterContext(patch("cardaq.capture.open_connection", self.connect))
        self.enterContext(patch("cardaq.capture._read_vehicle", return_value=_CIVIC))

    def simulate_civic_discovery(self):
        self.enterContext(patch("cardaq.capture.discover_standard", return_value=_CIVIC_INVENTORY))

    @contextmanager
    def connect(self, settings):
        self.assertEqual(settings, self.settings)
        self.opened += 1
        try:
            yield self.opened
        finally:
            self.closed += 1

    def rows(self) -> list[dict[str, str]]:
        with self.output.open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream, strict=True))

    def capture(self, request, duration: float = 60):
        self.simulate_civic_discovery()
        with patch("cardaq.capture.request", side_effect=request):
            return record(self.settings, self.output, duration, note="Heater on at 04:00; outside, 5 °C", notify=lambda _: None)

    def test_standard_profile_discovers_per_connection_and_records_11_bit_responders(self) -> None:
        messages = []
        commands = defaultdict(list)
        self.enterContext(patch("cardaq.capture.Path.cwd", return_value=self.output.parent))

        def exchange(port, command, _timeout):
            commands[port].append(command)
            self.clock.sleep(0.1)
            if command == b"ATDPN":
                return (b"A6",)
            if command in (b"ATD", b"ATTP0", b"ATAR", b"ATH1", b"ATCAF1", b"ATCFC1", b"ATH0"):
                return (b"OK",)
            if command == b"0100":
                if port == 1:
                    return (b"7E8 06 41 00 08 18 00 00", b"7EA 06 41 00 00 08 00 00")
                return (b"7EA 06 41 00 00 08 00 00",)
            if command == b"010C":
                return (b"7E8 04 41 0C 00 00",)
            if command == b"010D":
                if port == 2:
                    return (b"7EA 03 41 0D 13",)
                return (b"7EA 03 41 0D 29", b"7E8 03 41 0D 1E")
            if command == b"0105" and commands[port].count(command) == 1:
                return (b"7E8 03 41 05 63",)
            if command == b"0105":
                raise AdapterError("simulated disconnect")
            self.fail(f"Unexpected standard-profile request {command!r}")

        with patch("cardaq.capture.request", side_effect=exchange), patch("cardaq.obd.request", side_effect=exchange):
            result = record(self.settings, None, 6, profile="standard", notify=messages.append)
        self.assertEqual(self.opened, 2)
        self.assertEqual(self.closed, 2)
        self.assertEqual(sum(msg.startswith("Ready") for msg in messages), 2)
        self.assertEqual(set(commands[2]) & {b"010C", b"0105"}, set())
        metadata = json.loads(result.path.with_suffix(".capture.json").read_text())
        self.assertEqual(metadata["polling_profile"], "standard")
        with result.path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        inventory = [json.loads(row["detail"]) for row in rows if row["event"] == "inventory"]
        self.assertEqual(inventory, [{"7E8": ["05", "0C", "0D"], "7EA": ["0D"]}, {"7EA": ["0D"]}])
        self.assertEqual(result.replies, sum(row["event"] == "reply" for row in rows))
        other = next(row for row in rows if row["reply"] == "7EA 03 41 0D 13")
        self.assertEqual((other["event"], other["ecm_vehicle_speed_kph"]), ("reply", ""))
        series = read_capture_samples(result.path).series
        self.assertEqual(series["ecm_engine_speed_rpm"][0][1], 0)
        self.assertEqual(series["ecm_vehicle_speed_kph"][0][1], 30)
        self.assertEqual(series["ecm_engine_coolant_c"][0][1], 59)
        write_viewer([result.path], self.output.with_suffix(".html"))

    def test_standard_profile_requires_matching_positive_data_before_ready(self) -> None:
        messages = []
        def exchange(port, command, _timeout):
            self.clock.sleep(0.05)
            if command == b"ATDPN":
                return (b"A7",)
            if command == b"0100":
                return (b"18 DA F1 10 06 41 00 01 00 00 00",)  # PID 08 only
            if command == b"0108":
                if port == 1:
                    return (b"18 DA F1 12 03 41 08 42", b"18 DA F1 10 03 41 05 42", b"18 DA F1 10 03 7F 01 12")
                self.stop_file.touch()
                return (b"18 DA F1 10 03 41 08 42",)
            self.assertTrue(command.startswith(b"AT"))
            return (b"OK",)
        with patch("cardaq.capture.request", side_effect=exchange), patch("cardaq.obd.request", side_effect=exchange):
            result = record(self.settings, self.output, 10, profile="standard", notify=messages.append)
        self.assertEqual(result.replies, 1)
        self.assertEqual(result.stop_reason, "stop_requested")
        self.assertEqual(sum(msg.startswith("Ready") for msg in messages), 1)
        self.assertEqual([r["event"] for r in self.rows() if r["request"] == "0108"], ["adapter_status", "reply"])

    def test_standard_polling_keeps_advertised_crank_inputs_within_one_cycle(self) -> None:
        pids = (0x05, 0x0C, 0x0D, 0x62, 0x63, 0x8E)
        inventory = SweepResult((EcuPids("7E8", pids),), ())
        frames = {
            b"010C": b"04 41 0C 1F 40", b"010D": b"03 41 0D 76", b"0162": b"03 41 62 C1",
            b"0163": b"04 41 63 00 B9", b"018E": b"03 41 8E 88", b"0105": b"03 41 05 63",
        }
        def exchange(_port, command, _timeout):
            if command == b"ATH0":
                return (b"OK",)
            self.clock.sleep(0.125)
            return (b"7E8 " + frames[command],)

        with patch("cardaq.capture.discover_standard", return_value=inventory), patch("cardaq.capture.request", exchange):
            result = record(self.settings, self.output, 0.75, profile="standard", notify=lambda _: None)
        self.assertEqual(result.replies, len(pids))
        rows = [row["request"] for row in self.rows() if row["event"] == "reply"]
        self.assertEqual(rows, ["010C", "010D", "0162", "0163", "018E", "0105"])
        output = derive_series(read_capture_samples(result.path).series)
        self.assertEqual(output["derived_crank_torque_nm"], [[0.5, 105.45]])
        self.assertAlmostEqual(output["derived_crank_power_kw"][0][1], 22.0854, places=3)

    def assert_finished(self, result, reason: str) -> list[dict[str, str]]:
        self.assertEqual(result.path, self.output)
        self.assertFalse(self.output.with_suffix(".capture.json").exists())
        self.assertEqual(result.stop_reason, reason)
        rows = self.rows()
        self.assertEqual(rows[0]["event"], "start")
        self.assertIn("Heater on at 04:00; outside, 5 °C", rows[0]["detail"])
        self.assertEqual(rows[-1]["event"], "end")
        self.assertIn(reason, rows[-1]["detail"])
        self.assertTrue(all(None not in row and None not in row.values() for row in rows))
        elapsed = [float(row["elapsed_s"]) for row in rows]
        self.assertEqual(elapsed, sorted(elapsed))
        self.assertTrue(all(row["timestamp"] for row in rows))
        self.assertEqual(self.opened, self.closed)
        return rows

    def test_full_commute_preserves_readings_through_key_off(self) -> None:
        saw_live_file = False

        def request(_port, command, _timeout):
            nonlocal saw_live_file
            if command.startswith(b"AT"):
                return (b"12.5V",) if command == b"ATRV" else (b"OK",)
            self.clock.sleep(3)
            if self.clock.now >= 1830:
                if not saw_live_file:
                    current = self.rows()
                    self.assertEqual(current[0]["event"], "start")
                    self.assertTrue(any(row["event"] == "reply" for row in current))
                    self.assertNotIn("end", {row["event"] for row in current})
                    saw_live_file = True
                return (b"NO DATA",)
            if command == b"010C":
                return (_ENGINE_OFF if self.clock.now < 10 else _ENGINE_RUNNING,)
            if command == b"010D" and self.clock.now >= 10:
                return (b"18 DA F1 10 03 41 0D 32",)
            if command.startswith(b"22"):
                return (b"18 DA F1 1E 04 62 " + command[2:4] + b" " + command[4:6] + b" BB",)
            return (b"18 DA F1 10 03 41 " + command[2:4] + b" 00",)

        result = self.capture(request, duration=1860)

        rows = self.assert_finished(result, "duration")
        self.assertTrue(saw_live_file)
        self.assertGreater(float(rows[-1]["elapsed_s"]), 1800)
        self.assertGreater(result.replies, 0)
        self.assertIn(_ENGINE_OFF.decode(), [row["reply"] for row in rows])
        readings = [row for row in rows if row["reply"] == _ENGINE_RUNNING.decode()]
        self.assertTrue(readings)
        self.assertTrue(any(row["ecm_vehicle_speed_kph"] == "50" for row in rows))
        self.assertTrue(any(row["event"] == "reply" and float(row["elapsed_s"]) >= 1800 for row in rows))
        self.assertTrue(any(row["event"] == "no_data" and row["reply"] == "NO DATA" for row in rows))
        commands = {row["request"].replace(" ", "") for row in rows if row["event"] == "reply"}
        self.assertEqual(sum(command.startswith("01") for command in commands), 44)
        self.assertTrue({"222301", "222322"} <= commands)

    def test_disconnect_recovers_in_same_file_then_honors_parked_stop(self) -> None:
        first_sample = True

        def request(port, command, _timeout):
            nonlocal first_sample
            self.clock.sleep(0.1)
            if command.startswith(b"AT"):
                return (b"OK",)
            if port == 1:
                if first_sample and command == b"010C":
                    first_sample = False
                    return (_ENGINE_OFF,)
                raise AdapterError("USB adapter disconnected")
            if command == b"010C":
                self.stop_file.touch()
                return (_ENGINE_RUNNING,)
            return (b"NO DATA",)

        sync = os.fsync
        events_at_sync = []

        def sync_and_observe(descriptor):
            events_at_sync.append(self.rows()[-1]["event"])
            sync(descriptor)

        with patch("cardaq.capture.os.fsync", side_effect=sync_and_observe):
            result = self.capture(request)

        rows = self.assert_finished(result, "stop_requested")
        self.assertEqual(self.opened, 2)
        disconnect = next(i for i, row in enumerate(rows) if row["event"] == "transport_error")
        self.assertTrue(any(row["reply"] == _ENGINE_OFF.decode() for row in rows[:disconnect]))
        self.assertTrue(any(row["reply"] == _ENGINE_RUNNING.decode() for row in rows[disconnect + 1:]))
        self.assertEqual(events_at_sync[0], "start")
        self.assertIn("transport_error", events_at_sync)
        self.assertEqual(events_at_sync[-1], "end")

    def test_interrupt_closes_port_and_preserves_complete_records(self) -> None:
        replied = False

        def request(_port, command, _timeout):
            nonlocal replied
            if command.startswith(b"AT"):
                return (b"OK",)
            if command == b"010C" and not replied:
                replied = True
                return (_ENGINE_OFF,)
            raise KeyboardInterrupt

        result = self.capture(request)

        rows = self.assert_finished(result, "interrupted")
        self.assertIn(_ENGINE_OFF.decode(), [row["reply"] for row in rows])

    def test_syncs_flushed_samples_periodically_before_the_end(self) -> None:
        def request(_port, command, _timeout):
            if command.startswith(b"AT"):
                return (b"OK",)
            self.clock.sleep(0.25)
            return (_ENGINE_RUNNING,) if command == b"010C" else (b"NO DATA",)

        sync = os.fsync
        sync_times = []

        def sync_and_observe(descriptor):
            last = self.rows()[-1]
            if last["event"] in {"reply", "no_data"}:
                sync_times.append(float(last["elapsed_s"]))
            sync(descriptor)

        with patch("cardaq.capture.os.fsync", side_effect=sync_and_observe):
            result = self.capture(request, duration=3.25)

        self.assert_finished(result, "duration")
        self.assertEqual(sync_times, [1, 2, 3])

    def test_existing_capture_is_left_intact(self) -> None:
        previous = b"timestamp,reply\r\n2026-11-23T23:05:00,recorded\r\n"
        self.output.write_bytes(previous)

        with self.assertRaises(FileExistsError):
            self.capture(lambda *_: self.fail("An existing capture must be refused before polling"))

        self.assertEqual(self.output.read_bytes(), previous)
        self.assertEqual(self.opened, 0)

    def test_managed_captures_use_unique_utc_ids_and_finalize_their_metadata(self) -> None:
        self.simulate_civic_discovery()
        root = self.output.parent
        folder = root / "captures" / "recordings" / "2026-11-26"
        now = datetime(2026, 11, 26, 0, 1, 2, 345678, tzinfo=timezone.utc)
        self.enterContext(patch("cardaq.capture.Path.cwd", return_value=root))
        wall_clock = self.enterContext(patch("cardaq.capture.datetime", wraps=datetime))
        wall_clock.now.return_value = now
        messages = []
        in_progress = []

        def notify(message):
            messages.append(message)
            if message.startswith("Recording to "):
                path = Path(message.removeprefix("Recording to "))
                in_progress.append(json.loads(path.with_suffix(".capture.json").read_text(encoding="utf-8")))

        def request(_port, command, _timeout):
            if command.startswith(b"AT"):
                return (b"OK",)
            self.clock.sleep(0.25)
            return (_ENGINE_RUNNING,)

        folder.mkdir(parents=True)
        blocked = folder / f"20261126T000102Z_{_CIVIC.file_tag}.csv"
        blocked.write_bytes(b"previous raw capture")
        with patch("cardaq.capture.request", side_effect=request):
            first = record(self.settings, None, 0.25, notify=notify)
            second = record(self.settings, None, 0.25, notify=notify)

        self.assertNotEqual(first.path, second.path)
        self.assertEqual(blocked.read_bytes(), b"previous raw capture")
        for result, live in zip((first, second), in_progress, strict=True):
            with self.subTest(path=result.path):
                path = result.path
                self.assertEqual(path.parent, folder)
                self.assertRegex(path.name, rf"^20261126T000102Z_{_CIVIC.file_tag}_[0-9a-f]{{8}}\.csv$")
                self.assertIn(f"Recording to {path}", messages)
                with path.open(encoding="utf-8", newline="") as stream:
                    rows = list(csv.DictReader(stream, strict=True))
                self.assertEqual([row["event"] for row in rows], ["start", "vehicle", "reply", "end"])
                started = datetime.fromisoformat(rows[0]["timestamp"]).astimezone(timezone.utc)
                metadata = json.loads(path.with_suffix(".capture.json").read_text(encoding="utf-8"))
                self.assertEqual(live, {
                    "schema_version": 2,
                    "capture_id": path.stem,
                    "csv": path.name,
                    "created_utc": "2026-11-26T00:01:02.345Z",
                    "started_utc": started.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
                    "format": "cardaq-csv",
                    "source": "cardaq-record",
                    "polling_profile": "honda-civic",
                    "vehicle": {**_CIVIC.provenance(), "vin": _CIVIC.vin},
                    "status": "recording",
                    "stop_reason": None,
                    "replies": None,
                    "sha256": None,
                })
                self.assertEqual(metadata, {
                    **live, "status": "complete", "stop_reason": "duration", "replies": 1,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                })

    def test_managed_capture_preserves_raw_data_after_a_failure(self) -> None:
        self.simulate_civic_discovery()
        root = self.output.parent
        self.enterContext(patch("cardaq.capture.Path.cwd", return_value=root))

        def request(_port, command, _timeout):
            if command.startswith(b"AT"):
                return (b"OK",)
            if command == b"010C":
                return (_ENGINE_RUNNING,)
            raise OSError("recording fixture failed")

        with patch("cardaq.capture.request", side_effect=request):
            with self.assertRaisesRegex(OSError, "recording fixture failed"):
                record(self.settings, None, 1, notify=lambda _: None)

        path, = (root / "captures" / "recordings").glob("*/*.csv")
        sidecar, = path.parent.glob("*.capture.json")
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, strict=True))
        self.assertEqual([row["event"] for row in rows], ["start", "vehicle", "reply"])
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        self.assertEqual(metadata["status"], "failed")
        self.assertIsNone(metadata["sha256"])
        self.assertEqual(set(path.parent.iterdir()), {path, sidecar})

    def test_managed_capture_finalizes_after_interrupt(self) -> None:
        self.simulate_civic_discovery()
        root = self.output.parent
        self.enterContext(patch("cardaq.capture.Path.cwd", return_value=root))
        with patch("cardaq.capture.request", side_effect=KeyboardInterrupt):
            result = record(self.settings, None, 1, notify=lambda _: None)

        path = result.path
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream, strict=True))
        self.assertEqual([row["event"] for row in rows], ["start", "vehicle", "end"])
        self.assertEqual(result.stop_reason, "interrupted")
        metadata = json.loads(path.with_suffix(".capture.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["status"], "complete")
        self.assertEqual(metadata["stop_reason"], "interrupted")
        self.assertEqual(metadata["replies"], 0)
        self.assertEqual(metadata["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
