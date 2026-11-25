import hashlib
import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cardaq.pilot_measurements import MEASUREMENT_COLUMNS
from cardaq.viewer import _VIEWER_METRICS, _metric, write_viewer
from cardaq.viewer.recorded import RECORDED_GUIDES


SPEED = "ecm_vehicle_speed_kph"
COOLANT = "ecm_coolant_sensor_1_c"


class ViewerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(self.enterContext(TemporaryDirectory()))
        self.output = self.directory / "drives.html"

    def capture(self, name: str, contents: str) -> Path:
        path = self.directory / name
        path.write_text(contents, encoding="utf-8-sig")
        return path

    def data(self) -> dict:
        html = self.output.read_text(encoding="utf-8")
        script = re.search(r'<script\b[^>]*\bid="capture-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        self.assertIsNotNone(script)
        return json.loads(script[1])

    def test_every_selectable_metric_explains_the_measurement_and_its_interpretation(self) -> None:
        self.assertEqual(set(RECORDED_GUIDES), set(MEASUREMENT_COLUMNS))
        for column in (*MEASUREMENT_COLUMNS, *_VIEWER_METRICS):
            with self.subTest(column=column):
                metric = _metric(column)
                self.assertTrue(metric["description"].strip())
                self.assertTrue(metric["interpretation"].strip())
                self.assertNotEqual(metric["description"], metric["interpretation"])
                for field in ("plain", "source", "reading", "caution"):
                    self.assertTrue(metric["lesson"][field].strip())

    def test_embeds_sparse_readings_for_each_drive_in_elapsed_order(self) -> None:
        work = self.capture(
            "work.csv",
            f"timestamp,elapsed_s,event,detail,{SPEED},{COOLANT},unknown\n"
            '2026-11-24T08:07:11.520-05:00,0,start,"Heater on, engine off",,,2\n'
            ",4,reply,,35,,9\n"
            ",1,reply,,0,,3\n"
            ",2,reply,,,46,5\n"
            ",3,reply,,NaN,inf,9\n"
            ",bad time,reply,,60,30,9\n"
            ",6,reply,,bad speed,,9\n"
            ",980,end,,,,\n",
        )
        home = self.capture("home.csv", f"elapsed_s,{SPEED}\n0.5,0\n5.25,12\n")
        unsafe_label = "Home </script><script>alert(1)</script>"

        write_viewer([work, home], self.output, labels=["To work", unsafe_label])

        self.assertNotIn(unsafe_label, self.output.read_text(encoding="utf-8"))
        data = self.data()
        self.assertEqual(set(data["metrics"]), {SPEED, COOLANT})
        for metric in data["metrics"].values():
            self.assertTrue({"label", "unit", "description", "interpretation"} <= metric.keys())
        first, second = data["drives"]
        self.assertEqual(first["name"], "To work")
        self.assertTrue(first["started"])
        self.assertEqual(first["span"], 4)
        self.assertEqual(first["series"], {SPEED: [[1, 0], [4, 35]], COOLANT: [[2, 46]]})
        self.assertEqual(second["name"], unsafe_label)
        self.assertIsNone(second["started"])
        self.assertEqual(second["span"], 5.25)
        self.assertEqual(second["series"], {SPEED: [[0.5, 0], [5.25, 12]]})

    def test_rejects_capture_without_required_headers_or_decoded_readings(self) -> None:
        cases = [
            f"timestamp,{SPEED}\n2026-11-24T08:07:11,0\n",
            "elapsed_s,unknown\n0,50\n",
            f"elapsed_s,{SPEED}\n0,\n1,invalid\n2,-inf\n",
        ]
        for index, contents in enumerate(cases):
            with self.subTest(contents=contents):
                capture = self.capture(f"invalid-{index}.csv", contents)
                with self.assertRaises(ValueError):
                    write_viewer([capture], self.output)
                self.assertFalse(self.output.exists())

    def test_extracts_shifter_byte_from_saved_honda_replies(self) -> None:
        reply = (
            "18 DA F1 1E 10 27 62 23 22 BE 7F 7F | 18 DA F1 1E 21 FF 00 00 00 00 00 00 | "
            "18 DA F1 1E 22 00 00 00 00 00 00 00 | 18 DA F1 1E 23 1B 00 14 00 00 00 30 | "
            "18 DA F1 1E 24 00 00 64 00 A1 05 00 | 18 DA F1 1E 25 3B 00 83 FC EA 55 55"
        )
        capture = self.capture(
            "shifter.csv",
            f"elapsed_s,request,reply,{SPEED}\n"
            f"1.4,222322,{reply},0\n"
            f"2.8,222322,{reply.replace('00 00 00 30', '00 00 00 78')},\n"
            f"4.2,222322,{reply.replace('62 23 22', '62 23 01')},\n"
            "5.6,222322,NO DATA,\n",
        )

        write_viewer([capture], self.output)

        data = self.data()
        metric = "tcm_2322_status_byte_23"
        self.assertEqual(data["drives"][0]["series"][metric], [[1.4, 0x30], [2.8, 0x78]])
        self.assertEqual(data["metrics"][metric]["group"], "Shifter verification")
        self.assertEqual(data["metrics"][metric]["style"], "step")

    def test_rejects_mismatched_labels_and_protects_the_input(self) -> None:
        capture = self.capture("commute.csv", f"elapsed_s,{SPEED}\n0,0\n")
        original = capture.read_bytes()

        with self.assertRaises(ValueError):
            write_viewer([capture], self.output, labels=["First", "Second"])
        self.assertFalse(self.output.exists())
        with self.assertRaises(ValueError):
            write_viewer([capture], capture)
        self.assertEqual(capture.read_bytes(), original)

        html_input = self.capture("capture.html", f"elapsed_s,{SPEED}\n0,0\n")
        original = html_input.read_bytes()
        with self.assertRaises(ValueError):
            write_viewer([html_input], html_input)
        self.assertEqual(html_input.read_bytes(), original)

    def test_notes_belong_to_the_recording_contents_and_input_order(self) -> None:
        paths = [self.capture(f"drive-{i}.csv", f"elapsed_s,{SPEED}\n0,{i}\n") for i in (1, 2)]
        notes = self.directory / "notes.json"
        note = "The second drive was faster. </script>"
        document = {
            "recording_sha256": [hashlib.sha256(path.read_bytes()).hexdigest().upper() for path in paths],
            "signals": {SPEED: note},
        }
        notes.write_text(json.dumps(document), encoding="utf-8")
        write_viewer(paths, self.output, signal_notes=notes)
        self.assertEqual(self.data()["comparisonNotes"], {SPEED: note})
        self.assertNotIn(note, self.output.read_text(encoding="utf-8"))
        original = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, "input order"):
            write_viewer(paths[::-1], self.output, signal_notes=notes)
        for signals in ({"unknown": note}, {SPEED: ""}, {SPEED: 123}):
            notes.write_text(json.dumps({**document, "signals": signals}), encoding="utf-8")
            with self.assertRaises(ValueError):
                write_viewer(paths, self.output, signal_notes=notes)
        self.assertEqual(self.output.read_bytes(), original)

    def test_backfills_fuel_and_publishes_round_trip_summary(self) -> None:
        reply = "18 DA F1 10 06 41 9D 00 32 00 32"
        capture = self.capture(
            "fuel.csv",
            f"elapsed_s,request_elapsed_s,event,request,reply,{SPEED}\n"
            f"0.1,0.05,reply,019D,{reply},36\n"
            "0.5,0.4,no_data,010D,NO DATA,\n"
            f"1.1,1.05,reply,019D,{reply},36\n",
        )
        write_viewer([capture], self.output)
        data = self.data()
        drive = data["drives"][0]
        self.assertEqual(drive["series"]["ecm_engine_fuel_rate_g_s"], [[0.1, 1], [1.1, 1]])
        self.assertEqual(drive["series"]["observed_reply_latency_ms"], [[0, 50], [1, 50]])
        self.assertAlmostEqual(drive["summary"]["distanceKm"], 0.01)
        self.assertAlmostEqual(drive["summary"]["fuelGrams"], 1)
