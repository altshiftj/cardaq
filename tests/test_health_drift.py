import unittest
from datetime import date, timedelta

from cardaq.health.baseline import apply_baselines
from cardaq.health.drift import apply_drift


def trip(day, value, *, group="D", **settings):
    start = date(2026, 1, 1) + timedelta(days=day)
    feature = {"key": "idle", "value": value, **settings}
    return {"date": f"{start}T09:00:00+00:00", "group": group, "features": [feature]}


def score(records):
    apply_baselines(records)
    apply_drift(records)
    return [row["features"][0]["drift"] for row in records]


class AnchoredDriftTests(unittest.TestCase):
    def test_gradual_change_moves_away_from_anchor_while_remaining_in_rolling_reference(self):
        records = [trip(i, i) for i in range(40)]
        results = score(records)
        self.assertEqual(results[7]["anchorMedian"], 3.5)
        self.assertEqual(results[7]["recentN"], 0)
        self.assertEqual(results[11]["status"], "building")
        self.assertEqual(results[12]["status"], "within_reference")
        self.assertEqual(results[12]["recentMedian"], 10)
        self.assertEqual(results[-1]["status"], "shift")
        self.assertEqual(results[-1]["direction"], "higher")
        self.assertEqual(results[-1]["anchorMedian"], 3.5)
        self.assertEqual(results[-1]["recentMedian"], 37)
        self.assertAlmostEqual(results[-1]["radius"], 2 * 3.5 / 0.6745)
        self.assertTrue(all(row["features"][0]["baseline"]["status"] == "within_reference"
                            for row in records[8:]))

    def test_gaps_cohorts_and_features_preserve_independent_histories(self):
        records = [trip(i, 10, minimum_change=1) for i in range(8)]
        records += [trip(8, None), trip(9, 120, group="S"), trip(10, 5, minimum_change=1)]
        for i in range(11, 15):
            row = trip(i, 5, minimum_change=1)
            row["features"].append({"key": "new_signal", "value": 90})
            records.append(row)
        records += [trip(15, None), trip(16, 7, minimum_change=1)]
        results = score(records[::-1])
        self.assertEqual(results[8]["status"], "insufficient_samples")
        self.assertEqual((results[9]["anchorN"], results[9]["anchorMedian"]), (1, 120))
        self.assertEqual((results[10]["anchorN"], results[10]["recentN"]), (8, 1))
        self.assertEqual(results[14]["status"], "shift")
        self.assertEqual(results[14]["direction"], "lower")
        self.assertEqual(results[14]["radius"], 1)
        other = records[14]["features"][1]["drift"]
        self.assertEqual((other["anchorN"], other["recentN"], other["status"]), (4, 0, "building"))
        self.assertEqual((results[15]["status"], results[15]["recentN"]), ("insufficient_samples", 5))
        self.assertEqual(results[16]["recentMedian"], 5)

    def test_flat_guard_floor_boundary_and_isolated_recent_spike(self):
        values = [10] * 8 + [11] * 4 + [100]
        guarded = score([trip(i, value, minimum_change=1) for i, value in enumerate(values)])
        self.assertEqual(guarded[-1]["status"], "within_reference")
        self.assertEqual(guarded[-1]["recentMedian"], 11)
        self.assertEqual(guarded[-1]["radius"], 1)
        unknown = score([trip(i, value) for i, value in enumerate(values)])
        self.assertEqual(unknown[-1]["status"], "flat_reference")
        self.assertIsNone(unknown[-1]["radius"])
