import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cardaq.cli import main
from cardaq.health import write_health


class HealthReportTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.manifest = self.root / "history.toml"
        self.manifest.write_text(
            'vehicle = "Civic"\n[[trip]]\ncapture = "trip.csv"\ngroup = "Outbound D"\n'
            'label = "</script> morning"\n', encoding="utf-8",
        )
        self.capture = self.root / "trip.csv"
        self.capture.write_text(
            "timestamp,elapsed_s,event,request,reply,ecm_engine_speed_rpm\n"
            "2026-11-24T12:00:00.000-05:00,0,start,,,\n"
            "2026-11-24T12:00:01.000-05:00,1,reply,010C,,700\n",
            encoding="utf-8",
        )

    def test_html_and_json_from_cli_preserve_missing_evidence(self):
        output = self.root / "report.json"
        self.assertEqual(main(["health", str(self.manifest), "--output", str(output)]), 0)
        report = json.loads(output.read_text(encoding="utf-8"))
        trip, = report["trips"]
        self.assertEqual(trip["date"], "2026-11-24T12:00:00.000-05:00")
        self.assertTrue(trip["features"])
        self.assertEqual(report["lessons"].keys(), {f["key"] for f in trip["features"]})
        for lesson in report["lessons"].values():
            self.assertTrue(all(lesson[field].strip() for field in ("plain", "source", "example", "compare")))
        self.assertTrue(all(f["baseline"]["status"] == "insufficient_samples" for f in trip["features"]))
        self.assertTrue(all(f["drift"]["status"] == "insufficient_samples" for f in trip["features"]))
        self.assertTrue(all(c["last"] is None for c in trip["cylinders"]))
        self.assertIsNone(trip["mil"]["everOn"])
        page = self.root / "report.html"
        write_health(self.manifest, page)
        html = page.read_text(encoding="utf-8")
        self.assertNotIn("</script> morning", html)
        data = re.search(r'<script\b[^>]*id="health-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        self.assertEqual(json.loads(data[1]), report)

    def test_overlap_is_rejected_without_replacing_the_existing_report(self):
        trimmed = self.root / "cut.csv"
        trimmed.write_text(self.capture.read_text(encoding="utf-8").replace(
            "2026-11-24T12:00:00.000-05:00,0,start,,,\n", ""
        ), encoding="utf-8")
        with self.manifest.open("a", encoding="utf-8") as f:
            f.write('[[trip]]\ncapture = "cut.csv"\ngroup = "Other label"\n')
        output = self.root / "saved.json"
        output.write_text("previous report", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "overlap"):
            write_health(self.manifest, output)
        self.assertEqual(output.read_text(encoding="utf-8"), "previous report")

    def test_requires_absolute_recording_time(self):
        self.capture.write_text(self.capture.read_text(encoding="utf-8").replace("-05:00", ""), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            write_health(self.manifest, self.root / "report.json")

    def test_replayed_warm_stops_detect_a_persistent_rpm_change(self):
        # Each synthetic file represents a separate dated trip in one comparison group.
        manifest = ['vehicle = "Fixture"']
        for day, rpm in enumerate([699, 700, 701, 700, 699, 700, 701, 700, 760, 760, 700, 760, 760], 1):
            day_file = self.root / f"stop-{day}.csv"
            rows = ["timestamp,elapsed_s,ecm_vehicle_speed_kph,ecm_engine_speed_rpm,ecm_coolant_sensor_1_c"]
            for second in range(20):
                rows.append(f"2026-11-{day:02}T08:00:{second:02}-05:00,{second},0,{rpm},80")
            day_file.write_text("\n".join(rows), encoding="utf-8")
            manifest.extend(["[[trip]]", f'capture = "{day_file.name}"', 'group = "Warm stops"'])
        self.manifest.write_text("\n".join(manifest), encoding="utf-8")
        output = self.root / "series.json"
        write_health(self.manifest, output)
        trips = json.loads(output.read_text(encoding="utf-8"))["trips"]
        idle = [next(f for f in trip["features"] if f["key"] == "engine_idle_rpm") for trip in trips]
        self.assertEqual(idle[8]["baseline"]["status"], "watch")
        self.assertEqual(idle[9]["baseline"]["status"], "repeat")
        self.assertEqual(idle[11]["drift"]["status"], "building")
        self.assertEqual(idle[12]["drift"]["status"], "shift")
        self.assertEqual(idle[12]["drift"]["recentMedian"], 760)
