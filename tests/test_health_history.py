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
        self.assertEqual(trip["label"], "</script> morning")
        self.assertTrue(trip["features"])
        self.assertEqual(report["lessons"].keys(), {f["key"] for f in trip["features"]})
        for lesson in report["lessons"].values():
            self.assertTrue(all(lesson[field].strip() for field in ("plain", "source", "example", "compare")))
        self.assertTrue(all(f["baseline"]["status"] == "insufficient_samples" for f in trip["features"]))
        self.assertTrue(all(f["drift"]["status"] == "insufficient_samples" for f in trip["features"]))
        self.assertEqual(
            [(row["cylinder"], row["last"]) for row in trip["cylinders"]],
            [(1, None), (2, None), (3, None), (4, None)],
        )
        self.assertEqual(trip["mil"], {"polls": 0, "everOn": None, "maxCount": None})
        page = self.root / "report.html"
        write_health(self.manifest, page)
        html = page.read_text(encoding="utf-8")
        self.assertNotIn("</script> morning", html)
        data = re.search(r'<script\b[^>]*id="health-data"[^>]*>(.*?)</script>', html, re.DOTALL)
        self.assertEqual(json.loads(data[1]), report)

    def test_raw_diagnostic_replies_preserve_observed_counts_and_missing_polls(self):
        with self.capture.open("a", encoding="utf-8") as capture:
            capture.write(
                "2026-11-24T12:00:02-05:00,2,reply,06A2,"
                "18DAF110 10 0A 46 A2 0C 24 00 00 | 18DAF110 21 00 00 FF FF,\n"
                "2026-11-24T12:00:03-05:00,3,reply,06A3,"
                "18DAF110 10 13 46 A3 0B 24 00 07 | 18DAF110 21 00 00 FF FF A3 0C 24 | "
                "18DAF110 22 00 03 00 00 FF FF,\n"
                "2026-11-24T12:00:04-05:00,4,no_data,06A4,NO DATA,\n"
                "2026-11-24T12:00:05-05:00,5,reply,0101,18DAF110 06 41 01 82 00 00 00,\n"
                "2026-11-24T12:00:06-05:00,6,reply,0101,18DAF110 06 41 01 00 00 00 00,\n"
            )
        output = self.root / "report.json"

        write_health(self.manifest, output)

        trip, = json.loads(output.read_text(encoding="utf-8"))["trips"]
        cylinders = trip["cylinders"]
        self.assertEqual(
            [(row["cylinder"], row["polls"], row["last"]) for row in cylinders],
            [(1, 1, 0), (2, 1, 3), (3, 0, None), (4, 0, None)],
        )
        self.assertEqual(cylinders[1]["weightedLast"], 7)
        self.assertEqual(cylinders[1]["transitions"], [{"seconds": 3, "count": 3}])
        self.assertEqual(trip["mil"], {"polls": 2, "everOn": True, "maxCount": 2})

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
            manifest.append(f'[[trip]]\ncapture = "{day_file.name}"\ngroup = "Warm stops"')
        output = self.root / "series.json"
        self.manifest.write_text("\n".join(manifest[:-1]), encoding="utf-8")
        write_health(self.manifest, output)
        previous_trips = json.loads(output.read_text(encoding="utf-8"))["trips"]

        self.manifest.write_text("\n".join(manifest), encoding="utf-8")
        write_health(self.manifest, output)
        trips = json.loads(output.read_text(encoding="utf-8"))["trips"]
        self.assertEqual(trips[:-1], previous_trips)
        idle = [next(f for f in trip["features"] if f["key"] == "engine_idle_rpm") for trip in trips]
        self.assertEqual(idle[8]["baseline"]["status"], "watch")
        self.assertEqual(idle[9]["baseline"]["status"], "repeat")
        self.assertEqual(idle[11]["drift"]["status"], "building")
        self.assertEqual(idle[12]["drift"]["status"], "shift")
        self.assertEqual(idle[12]["drift"]["recentMedian"], 760)
