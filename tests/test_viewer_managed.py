import hashlib
import json
import unittest
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cardaq.viewer import write_managed_viewer


SPEED = "ecm_vehicle_speed_kph"


class ManagedViewerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.captures = self.root / "captures"
        self.views = self.captures / "views"
        self.enterContext(chdir(self.root))

    def capture(self, relative_path: str, speed: int) -> Path:
        path = self.captures / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"elapsed_s,{SPEED}\n0,{speed}\n", encoding="utf-8")
        return path

    def test_reuses_export_with_effective_default_labels_and_relative_provenance(self) -> None:
        first = self.capture("recordings/first.csv", 12)
        second = self.capture("imports/second.csv", 24)

        output = write_managed_viewer([first, second])
        relative_paths = [first.relative_to(self.root), second.relative_to(self.root)]
        self.assertEqual(output, write_managed_viewer(relative_paths, labels=["first", "second"]))

        self.assertEqual(output.parent, self.views)
        self.assertEqual(set(self.views.iterdir()), {output, output.with_suffix(".json")})
        self.assertEqual(json.loads(output.with_suffix(".json").read_text(encoding="utf-8")), {
            "version": 1,
            "output": output.name,
            "inputs": [
                {
                    "path": "../recordings/first.csv",
                    "sha256": hashlib.sha256(first.read_bytes()).hexdigest(),
                    "label": "first",
                },
                {
                    "path": "../imports/second.csv",
                    "sha256": hashlib.sha256(second.read_bytes()).hexdigest(),
                    "label": "second",
                },
            ],
        })
        self.assertIn('"name":"first"', output.read_text(encoding="utf-8"))

    def test_reuses_export_when_source_moves_and_updates_the_reference(self) -> None:
        capture = self.capture("recordings/commute.csv", 12)
        output = write_managed_viewer([capture])
        moved = self.captures / "imports" / "commute.csv"
        moved.parent.mkdir()
        capture.rename(moved)

        self.assertEqual(write_managed_viewer([moved]), output)
        metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["inputs"][0]["path"], "../imports/commute.csv")
        self.assertEqual((output.parent / metadata["inputs"][0]["path"]).resolve(), moved.resolve())

    def test_changes_to_recording_bytes_order_or_labels_get_separate_exports(self) -> None:
        first = self.capture("first.csv", 12)
        second = self.capture("second.csv", 24)
        labels = ["Drive", "Drive"]
        original = write_managed_viewer([first, second], labels=labels)
        reordered = write_managed_viewer([second, first], labels=labels)
        relabeled = write_managed_viewer([first, second], labels=["Morning", "Drive"])
        original_bytes = original.read_bytes()

        self.capture("first.csv", 36)
        revised = write_managed_viewer([first, second], labels=labels)

        self.assertEqual(len({original, reordered, relabeled, revised}), 4)
        self.assertEqual(original.read_bytes(), original_bytes)

    def test_signal_note_changes_get_separate_exports_with_note_provenance(self) -> None:
        capture = self.capture("recordings/commute.csv", 12)
        notes = self.captures / "commute-notes.json"
        fingerprint = hashlib.sha256(capture.read_bytes()).hexdigest()
        output_without_notes = write_managed_viewer([capture])
        outputs = {output_without_notes}
        for comment in ("The first observation.", "A revised observation."):
            with self.subTest(comment=comment):
                notes.write_text(json.dumps({"recording_sha256": [fingerprint], "signals": {SPEED: comment}}),
                                 encoding="utf-8")
                output = write_managed_viewer([capture], signal_notes=notes)
                self.assertNotIn(output, outputs)
                outputs.add(output)
                self.assertIn(comment, output.read_text(encoding="utf-8"))
                metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
                self.assertEqual(metadata["signal_notes"], {
                    "path": "../commute-notes.json", "sha256": hashlib.sha256(notes.read_bytes()).hexdigest(),
                })

    def test_cross_volume_provenance_uses_a_file_uri(self) -> None:
        capture = self.capture("recordings/commute.csv", 12)
        with patch("cardaq.viewer.relpath", side_effect=ValueError("path is on a different drive")):
            output = write_managed_viewer([capture])

        metadata = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["inputs"][0]["path"], capture.as_uri())

    def test_invalid_input_does_not_publish_an_export_or_provenance(self) -> None:
        capture = self.capture("recordings/commute.csv", 12)
        notes = self.captures / "commute-notes.json"
        notes.write_text(json.dumps({"recording_sha256": ["0" * 64], "signals": {SPEED: "Other drive"}}),
                         encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "different recording contents"):
            write_managed_viewer([capture], signal_notes=notes)

        self.assertFalse(self.views.exists())
