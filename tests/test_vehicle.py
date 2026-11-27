import csv
import hashlib
import json
import unittest
from contextlib import chdir, contextmanager, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cardaq.adapter import AdapterError, recording_port
from cardaq.cli import main
from cardaq.vehicle import identify_vehicle
from cardaq.viewer import read_capture_samples


def vin_reply(vin, address=b"7E8"):
    payload = b"\x49\x02\x01" + vin.encode("ascii")
    frames = (b"\x10\x14" + payload[:6], b"\x21" + payload[6:13], b"\x22" + payload[13:])
    return tuple(address + b" 8 " + frame.hex(" ").encode() for frame in frames)


class VehicleTests(unittest.TestCase):
    def test_automatic_port_selection_prefers_a_named_adapter_and_rejects_ambiguity(self):
        with patch("cardaq.adapter.available_ports", return_value=[("COM3", "Bluetooth"), ("COM5", "OBDLink EX")]):
            self.assertEqual(recording_port(), "COM5")
        with patch("cardaq.adapter.available_ports", return_value=[("COM5", "USB Serial Port")]):
            self.assertEqual(recording_port(), "COM5")
        with patch("cardaq.adapter.available_ports", return_value=[("COM3", "Bluetooth"), ("COM4", "Bluetooth")]):
            with self.assertRaises(AdapterError):
                recording_port()

    def test_unavailable_vin_still_records_standard_samples_with_explicit_status(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(chdir(root))
        self.enterContext(redirect_stdout(StringIO()))

        @contextmanager
        def connect(_settings):
            yield "fixture"

        def exchange(_port, cmd, _timeout):
            if cmd == b"ATDPN":
                return (b"A6",)
            if cmd.startswith(b"AT"):
                return (b"OK",)
            if cmd == b"0100":
                return (b"7E8 06 41 00 00 10 00 00",)
            if cmd == b"0902":
                return (b"NO DATA",)
            self.assertEqual(cmd, b"010C")
            path, = (root / "captures/recordings").glob("*/*.csv")
            path.with_suffix(".csv.stop").touch()
            return (b"7E8 04 41 0C 1F 40",)

        self.enterContext(patch("cardaq.capture.open_connection", connect))
        self.enterContext(patch("cardaq.capture.request", exchange))
        self.enterContext(patch("cardaq.obd.request", exchange))
        self.assertEqual(main(["record", "--port", "fixture"]), 0)
        path, = (root / "captures/recordings").glob("*/*.csv")
        self.assertTrue(path.name.endswith("_unidentified.csv"))
        meta = json.loads(path.with_suffix(".capture.json").read_text())
        self.assertEqual((meta["polling_profile"], meta["vehicle"]["status"], meta["vehicle"]["vin"]), ("standard", "unavailable", None))
        self.assertEqual(read_capture_samples(path).series["ecm_engine_speed_rpm"][0][1], 2000)

    def test_vin_requires_a_complete_consistent_response(self):
        vin = "JTMP1RFV0MD000001"
        other = "JTMP1RFV0MD000002"
        primary = vin_reply(vin)
        second = vin_reply(vin, b"7EA")
        interleaved = tuple(frame for pair in zip(primary, second, strict=True) for frame in pair)
        car = identify_vehicle(interleaved, 3, {})
        self.assertEqual((car.vin, car.responders, car.profile), (vin, ("7E8", "7EA"), "standard"))
        self.assertTrue(car.file_tag.startswith("2021-toyota-rav4-xle-"))
        self.assertNotEqual(car.file_tag, identify_vehicle(vin_reply(other), 3, {}).file_tag)
        renamed = identify_vehicle(primary, 3, {vin: ("Parents' car", "standard")})
        self.assertEqual(car.fingerprint, renamed.fingerprint)
        self.assertTrue(renamed.file_tag.startswith("parents-car-"))
        honda = identify_vehicle(vin_reply("2HGFC2F60LH000001", b"18 DA F1 10"), 8, {})
        self.assertEqual((honda.label, honda.profile), ("2020 Honda Civic LX", "honda-civic"))
        unknown = identify_vehicle(vin_reply("1ABCDEFG0AA000001"), 3, {})
        self.assertEqual((unknown.label, unknown.profile, unknown.status), ("Vehicle", "standard", "identified"))
        for lines in (primary[:2], (primary[0], primary[2], primary[1]), (primary[0], *second[1:]),
                      vin_reply("0" * 17), vin_reply("JTMP1RFVIMD000001"), (b"NO DATA",)):
            self.assertEqual(identify_vehicle(lines, 3, {}).file_tag, "unidentified")
        conflicting = identify_vehicle(primary + vin_reply(other, b"7EA"), 3, {})
        self.assertEqual((conflicting.vin, conflicting.status, conflicting.profile), (None, "conflicting", "standard"))

    def test_go_names_and_seals_the_file_before_accepting_a_different_vehicle(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(chdir(root))
        Path("cardaq.toml").write_text('[serial]\nport = "simulated"\n', encoding="utf-8")
        output = self.enterContext(redirect_stdout(StringIO()))
        vin = "JTMP1RFV0MD000001"
        expected_hash = hashlib.sha256(vin.encode()).hexdigest()
        opened, closed, poll_ports = [], [], []

        @contextmanager
        def connect(settings):
            self.assertEqual(settings.port, "simulated")
            port = len(opened) + 1
            opened.append(port)
            try:
                yield port
            finally:
                closed.append(port)

        def exchange(port, cmd, _timeout):
            if cmd == b"ATDPN":
                return (b"A6",)
            if cmd.startswith(b"AT"):
                return (b"OK",)
            if cmd == b"0100":
                return (b"7E8 06 41 00 00 10 00 00",)
            if cmd == b"0902":
                return vin_reply(vin if port < 3 else "JTMP1RFV0MD000002")
            self.assertEqual(cmd, b"010C")
            poll_ports.append(port)
            if poll_ports.count(port) == 2:
                raise AdapterError("simulated disconnect")
            return (b"7E8 04 41 0C 1F 40",)

        self.enterContext(patch("cardaq.capture.open_connection", connect))
        self.enterContext(patch("cardaq.capture.request", exchange))
        self.enterContext(patch("cardaq.obd.request", exchange))
        self.enterContext(patch("cardaq.capture.sleep", lambda _: None))
        self.assertEqual(main(["go"]), 1)
        self.assertEqual(poll_ports, [1, 1, 2, 2])
        self.assertEqual(opened, closed)
        path, = (root / "captures/recordings").glob("*/*.csv")
        self.assertRegex(path.name, rf"^\d{{8}}T\d{{6}}Z_2021-toyota-rav4-xle-{expected_hash[:12]}\.csv$")
        metadata = json.loads(path.with_suffix(".capture.json").read_text())
        self.assertEqual(metadata["stop_reason"], "vehicle_changed")
        self.assertEqual(metadata["replies"], 2)
        self.assertEqual(metadata["vehicle"]["vin"], vin)
        self.assertEqual(metadata["vehicle"]["vin_sha256"], expected_hash)
        self.assertEqual(metadata["polling_profile"], "standard")
        self.assertEqual(metadata["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertNotIn(vin, path.read_text())
        self.assertNotIn(vin, output.getvalue())
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row["event"] for row in rows][-2:], ["vehicle_change", "end"])
        renamed = root / "my-trip.csv"
        path.rename(renamed)
        self.assertEqual(read_capture_samples(renamed).vehicle, {"label": "2021 Toyota RAV4 XLE", "vin_sha256": expected_hash})
