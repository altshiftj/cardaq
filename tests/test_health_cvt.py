import unittest

from cardaq.health.cvt import cvt_features


def cruise(times, rpm=2100):
    return {
        "honda_engine_speed_rpm": [[t, rpm] for t in times],
        "honda_vehicle_speed_kph": [[t, 115] for t in times],
        "candidate_cvt_fluid_temperature_c": [[t, 70] for t in times],
        "ecm_calculated_load_pct": [[t, 50] for t in times],
        "derived_torque_converter_slip_rpm": [[t, -4] for t in times],
        "derived_ratio_change_pct_s": [[t, -0.25] for t in times],
    }


class CvtHealthTests(unittest.TestCase):
    def test_observed_rpm_selects_a_profile_and_missing_slip_preserves_ratio_coverage(self):
        series = cruise(range(15), rpm=2500)
        series["tcm_2322_status_byte_23"] = [[t, 0x29] for t in range(15)]
        series["derived_torque_converter_slip_rpm"].pop()

        lower_slip, lower_rate, upper_slip, upper_rate = cvt_features(series)

        self.assertEqual((lower_slip["count"], lower_rate["count"]), (0, 0))
        self.assertEqual(upper_slip["count"], 9)
        self.assertIsNone(upper_slip["value"])
        self.assertEqual(upper_rate["count"], 10)
        self.assertEqual(upper_rate["value"], 0.25)

    def test_absolute_median_preserves_negative_slip_magnitudes(self):
        slip, rate, *_ = cvt_features(cruise(range(15)))
        self.assertEqual(slip["value"], 4)
        self.assertEqual(slip["count"], 10)
        self.assertEqual(rate["value"], 0.25)

    def test_short_runs_on_either_side_of_a_gap_cannot_make_one_window(self):
        series = cruise([0, 1, 2, 3, 4, 12, 13, 14, 15, 16])
        self.assertTrue(all(row["count"] == 0 for row in cvt_features(series)))

    def test_changing_load_or_speed_cold_fluid_and_missing_inputs_exclude_a_window(self):
        for channel, value in (
            ("ecm_calculated_load_pct", 60),
            ("honda_vehicle_speed_kph", 118),
            ("candidate_cvt_fluid_temperature_c", 59),
            ("honda_engine_speed_rpm", 2600),
        ):
            with self.subTest(channel=channel):
                series = cruise(range(30))
                for point in series[channel][::3]:
                    point[1] = value
                self.assertTrue(all(row["count"] == 0 for row in cvt_features(series)))
        self.assertTrue(all(row["value"] is None for row in cvt_features({})))

    def test_load_can_be_paired_within_tolerance_only(self):
        series = cruise(range(15))
        series["ecm_calculated_load_pct"] = [[0, 50], [14, 50]]
        self.assertTrue(all(row["count"] == 0 for row in cvt_features(series)))
