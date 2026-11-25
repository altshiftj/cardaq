import unittest
from datetime import datetime, timedelta, timezone

from cardaq.health.baseline import apply_baselines


def trip(hour, value, group="outbound", **feature_settings):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=hour)
    feature = {"key": "test_signal", "value": value, **feature_settings}
    return {"date": start.isoformat(), "group": group, "features": [feature]}


def baseline(record):
    return record["features"][0]["baseline"]


class BaselineTests(unittest.TestCase):
    def test_scores_against_prior_independent_trips_and_recognizes_repetition(self):
        records = [trip(i, v) for i, v in enumerate([9, 10, 11, 9, 11, 9, 10, 11])]
        shifted = trip(8, 18, count=10000)
        sparse = trip(9, None)
        repeated = trip(10, 19)
        reversed_shift = trip(11, 0)
        normal = trip(12, 10)
        isolated = trip(13, 25)
        records.extend([shifted, sparse, repeated, reversed_shift, normal, isolated])
        records.reverse()
        apply_baselines(records)
        self.assertEqual([baseline(row)["n"] for row in records[:8]], list(range(8)))
        self.assertTrue(all(baseline(row)["status"] == "building" for row in records[:8]))
        first = baseline(shifted)
        self.assertEqual((first["n"], first["median"], first["mad"]), (8, 10, 1))
        self.assertAlmostEqual(first["radius"], 3.5 / 0.6745)
        self.assertEqual((first["status"], first["direction"]), ("watch", "higher"))
        self.assertEqual(baseline(sparse)["status"], "insufficient_samples")
        self.assertEqual((baseline(repeated)["n"], baseline(repeated)["status"]), (9, "repeat"))
        self.assertEqual(baseline(reversed_shift)["direction"], "lower")
        self.assertEqual(baseline(reversed_shift)["status"], "watch")
        self.assertEqual(baseline(normal)["status"], "within_reference")
        self.assertEqual(baseline(isolated)["status"], "watch")

    def test_flat_history_abstains_without_resolution_and_uses_a_known_floor(self):
        records = [trip(i, 10, minimum_change=1) for i in range(8)]
        for index, record in enumerate(records):
            record["features"].append({"key": "other", "value": [0.6, 0.6000000000000001][index % 2]})
        boundary = trip(8, 11, minimum_change=1)
        boundary["features"].append({"key": "other", "value": 2})
        beyond = trip(9, 12, minimum_change=1)
        records.extend([boundary, beyond])
        apply_baselines(records)
        self.assertEqual(baseline(boundary)["status"], "within_reference")
        self.assertEqual(baseline(boundary)["radius"], 1)
        unscored = boundary["features"][1]["baseline"]
        self.assertEqual(unscored["status"], "flat_reference")
        self.assertIsNone(unscored["radius"])
        self.assertEqual(baseline(beyond)["status"], "watch")

    def test_nonflat_but_quantized_history_respects_the_feature_floor(self):
        records = [trip(i, v, minimum_change=1) for i, v in enumerate([0.9, 1.1] * 4 + [1.8])]
        apply_baselines(records)
        self.assertAlmostEqual(baseline(records[-1])["mad"], 0.1)
        self.assertEqual(baseline(records[-1])["radius"], 1)
        self.assertEqual(baseline(records[-1])["status"], "within_reference")

    def test_separate_groups_and_features_keep_only_the_last_30_eligible_trips(self):
        records = [trip(i, i) for i in range(31)]
        other_group = trip(31, 999, group="sport")
        sparse = trip(32, None)
        newest = trip(33, 32)
        newest["features"].append({"key": "new_sensor", "value": 10})
        records.extend([other_group, sparse, newest])
        apply_baselines(records)
        self.assertEqual(baseline(other_group)["n"], 0)
        self.assertEqual(baseline(newest)["n"], 30)
        self.assertEqual(baseline(newest)["median"], 15.5)
        self.assertEqual(newest["features"][1]["baseline"]["n"], 0)

    def test_orders_by_absolute_time_and_rejects_duplicate_starts_or_feature_keys(self):
        first, second = trip(0, 10), trip(1, 20)
        first["date"] = "2026-01-01T12:00:00+04:00"
        second["date"] = "2026-01-01T10:00:00+00:00"
        records = [second, first]
        apply_baselines(records)
        self.assertIs(records[0], first)
        self.assertEqual(baseline(second)["median"], 10)
        second["date"] = "2026-01-01T08:00:00+00:00"
        with self.assertRaisesRegex(ValueError, "same start"):
            apply_baselines(records)
        first["features"].append({"key": "test_signal", "value": 100})
        with self.assertRaisesRegex(ValueError, "Multiple values"):
            apply_baselines([first])

    def test_invalid_late_trip_does_not_leave_a_partial_report(self):
        good = trip(0, 10)
        invalid = trip(1, float("nan"))
        records = [invalid, good]
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            apply_baselines(records)
        self.assertIs(records[0], invalid)
        self.assertNotIn("baseline", good["features"][0])
