import json
import unittest
from contextlib import chdir, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cardaq.capture import CaptureResult
from cardaq.cli import main
from cardaq.config import SerialSettings


class CliOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.enterContext(chdir(self.directory))
        self.stdout = self.enterContext(redirect_stdout(StringIO()))

    def test_record_passes_automatic_output_when_no_path_is_supplied(self) -> None:
        generated = self.directory / "captures" / "recordings" / "generated.csv"
        with patch("cardaq.cli.record", return_value=CaptureResult(generated, "duration", 4)) as record:
            self.assertEqual(main(["record", "--port", "test-serial", "--duration", "5"]), 0)
        self.assertEqual(record.call_args.args, (SerialSettings("test-serial"), None, 5))
        self.assertIn(str(generated), self.stdout.getvalue())

    def test_go_loads_local_serial_and_vehicle_settings_without_flags(self) -> None:
        Path("cardaq.toml").write_text(
            '[serial]\nport = "test-usb"\n[vehicles."19XFC2F60LE000001"]\nlabel = "My Civic"\n',
            encoding="utf-8",
        )
        result = CaptureResult(Path("drive.csv"), "duration", 1)
        with patch("cardaq.cli.record", return_value=result) as record:
            self.assertEqual(main(["go"]), 0)
        self.assertEqual(record.call_args.args[0], SerialSettings("test-usb"))
        self.assertEqual(record.call_args.kwargs["profile"], "auto")
        self.assertEqual(record.call_args.kwargs["profiles"], {"19XFC2F60LE000001": ("My Civic", "honda-civic")})

    def test_view_with_no_output_saves_a_report_and_provenance(self) -> None:
        capture = self.directory / "trip.csv"
        capture.write_text("elapsed_s,ecm_vehicle_speed_kph\n0,0\n1,36\n", encoding="utf-8")

        self.assertEqual(main(["view", str(capture), "--label", "Example"]), 0)

        report, = (self.directory / "captures" / "views").glob("*.html")
        provenance = json.loads(report.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(provenance["output"], report.name)
        self.assertIn("Example", report.read_text(encoding="utf-8"))
        self.assertIn(str(report), self.stdout.getvalue())

    def test_health_with_no_output_writes_html_beside_the_manifest(self) -> None:
        capture = self.directory / "trip.csv"
        capture.write_text(
            "timestamp,elapsed_s,ecm_engine_speed_rpm\n2026-11-24T12:00:00-05:00,0,700\n",
            encoding="utf-8",
        )
        manifest = self.directory / "history.toml"
        manifest.write_text('vehicle = "Civic"\n[[trip]]\ncapture = "trip.csv"\ngroup = "Outbound"\n', encoding="utf-8")

        self.assertEqual(main(["health", str(manifest)]), 0)

        output = manifest.with_suffix(".html")
        self.assertIn('id="health-data"', output.read_text(encoding="utf-8"))
        self.assertIn(str(output), self.stdout.getvalue())
