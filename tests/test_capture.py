import csv
import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cardaq.adapter import AdapterError
from cardaq.capture import record
from cardaq.config import SerialSettings


_ENGINE_OFF = b"18 DA F1 10 04 41 0C 00 00"
_ENGINE_RUNNING = b"18 DA F1 10 04 41 0C 1F 40"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


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
        with patch("cardaq.capture.request", side_effect=request):
            return record(self.settings, self.output, duration, note="Heater on at 04:00; outside, 5 °C", notify=lambda _: None)

    def assert_finished(self, result, reason: str) -> list[dict[str, str]]:
        self.assertEqual(result.path, self.output)
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

    def test_existing_capture_is_left_intact(self) -> None:
        previous = b"timestamp,reply\r\n2026-11-23T23:05:00,recorded\r\n"
        self.output.write_bytes(previous)

        with self.assertRaises(FileExistsError):
            self.capture(lambda *_: self.fail("An existing capture must be refused before polling"))

        self.assertEqual(self.output.read_bytes(), previous)
        self.assertEqual(self.opened, 0)
