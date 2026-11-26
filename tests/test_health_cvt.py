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

    def test_cruise_takes_magnitudes_before_calculating_medians(self):
        series = cruise(range(15))
        slips = [400] * 5 + [-9, -8, -7, -6, -5, -4, 1, 2, 3, 100]
        rates = [8] * 5 + [-1.5, -1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 1.25, 4]
        series["derived_torque_converter_slip_rpm"] = [[t, value] for t, value in enumerate(slips)]
        series["derived_ratio_change_pct_s"] = [[t, value] for t, value in enumerate(rates)]

        slip, rate, *_ = cvt_features(series)
        self.assertEqual((slip["count"], slip["value"]), (10, 5.5))
        self.assertEqual((rate["count"], rate["value"]), (10, 0.625))

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

    def test_load_pairing_includes_the_tolerance_boundary(self):
        for first_load_time, expected in ((1.375, (10, 4)), (1.5, (10, 4)), (1.625, (9, None))):
            with self.subTest(first_load_time=first_load_time):
                series = cruise(range(15))
                # Only t=0 loses its matching load when the first load poll is too late.
                load_times = (first_load_time, 4.25, 6.75, 9.25, 11.75, 14)
                series["ecm_calculated_load_pct"] = [[t, 50] for t in load_times]

                slip, *_ = cvt_features(series)
                self.assertEqual((slip["count"], slip["value"]), expected)
