import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cardaq.viewer import _read_capture
from cardaq.viewer.live import RecordingFolder


class RecordingFolderTests(unittest.TestCase):
    def test_library_lifecycle_and_parse_cache(self):
        root = Path(self.enterContext(TemporaryDirectory()))
        library = RecordingFolder(root)

        def data():
            page = library.page()
            return json.loads(re.search(r'id="capture-data">(.*?)</script>', page).group(1))

        empty = data()
        self.assertEqual(empty["drives"], [])
        day = root / "day"
        day.mkdir()
        capture = day / "trip.CSV"
        capture.write_text("wrong,header\n")
        self.assertEqual(data()["live"]["skipped"], ["day/trip.CSV"])
        capture.write_text("elapsed_s,ecm_vehicle_speed_kph\n0,0\n1,42\n")
        with patch("cardaq.viewer.live._read_capture", wraps=_read_capture) as decode:
            first = data()
            self.assertEqual(first["drives"][0]["name"], "day/trip")
            self.assertEqual(first["live"]["skipped"], [])
            self.assertEqual(data()["live"], first["live"])
            self.assertEqual(decode.call_count, 1)
            with capture.open("a") as stream:
                stream.write("2,50\n")
            second = data()
            self.assertNotEqual(first["live"]["revision"], second["live"]["revision"])
            self.assertEqual(second["drives"][0]["series"]["ecm_vehicle_speed_kph"][-1], [2, 50])
        capture.unlink()
        self.assertEqual(data(), empty)
