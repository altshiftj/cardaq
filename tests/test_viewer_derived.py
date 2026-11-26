import unittest
from math import log

from cardaq.viewer.derived import derive_series


class DerivedSeriesTests(unittest.TestCase):
    def test_pulley_ratio_requires_matching_moving_honda_observations(self):
        results = derive_series({
            "candidate_drive_pulley_rpm": [[1, 600], [2, 0], [3, 800], [4, 500], [5, 500], [6, 500]],
            "candidate_driven_pulley_rpm": [[1, 500], [2, 800], [3, 700], [4, 0], [5, 400], [6.1, 400]],
            "honda_vehicle_speed_kph": [[1, 12], [2, 10], [3, 9], [4, 10], [5, 10], [5, 0], [6, 12]],
        })
        self.assertEqual(results, {"derived_pulley_ratio": [[1, 1.2], [2, 0]]})

    def test_converter_pair_is_forward_bounded_and_used_once(self):
        results = derive_series({
            "honda_engine_speed_rpm": [[1, 1000], [1.02, 1800], [2, 600], [3, 499], [4, 900], [5, 900]],
            "candidate_drive_pulley_rpm": [[1, 0], [1.02, 1800], [2, 640], [3, 300], [5, 900]],
            "candidate_torque_converter_turbine_rpm": [
                [0.99, 500], [1, 600], [1.10, 940], [2.15, 640], [3.05, 320], [4.151, 901], [5.1, 900],
            ],
        })
        self.assertEqual(results["derived_torque_converter_slip_rpm"], [[1, 60], [2, -40], [5, 0]])
        self.assertEqual(results["derived_drive_minus_turbine_rpm"], [[1, -940], [2, 0], [5, 0]])

    def test_acceleration_uses_observed_readings_and_does_not_bridge_gaps(self):
        results = derive_series({"ecm_vehicle_speed_kph": [
            [0, 0], [1, 3.6], [2, 7.2], [3, 10.8],
            [5, 36], [6, 36], [7, 36], [8, 36],
            [493, 50.4], [494, 46.8], [495, 43.2], [496, 39.6],
        ]})
        points = results["derived_longitudinal_acceleration_m_s2"]
        self.assertEqual([timestamp for timestamp, _ in points], [1, 2, 6, 7, 494, 495])
        for (_, actual), expected in zip(points, [1, 1, 0, 0, -1, -1], strict=True):
            self.assertAlmostEqual(actual, expected)

    def test_temperature_difference_uses_nearest_coolant_within_tolerance(self):
        results = derive_series({
            "candidate_cvt_fluid_temperature_c": [[1, 12], [2, 15], [3, 20], [4, 50]],
            "ecm_coolant_sensor_1_c": [[0.6, 30], [1.125, 22], [1.875, 15], [2.125, 7], [3.55, 30], [4.2, 40]],
        })
        self.assertEqual(results, {"derived_cvt_minus_coolant_c": [[1, -10], [2, 0], [4, 10]]})

    def test_omits_unavailable_metrics_and_preserves_original_series(self):
        original = {"candidate_drive_pulley_rpm": [[1, 0]], "candidate_driven_pulley_rpm": [[1, 200]]}
        self.assertEqual(derive_series(original), {})
        self.assertEqual(original, {"candidate_drive_pulley_rpm": [[1, 0]], "candidate_driven_pulley_rpm": [[1, 200]]})

    def test_cvt_change_rates_add_to_drive_pulley_change_and_skip_gaps(self):
        results = derive_series({
            "candidate_drive_pulley_rpm": [[1, 600], [2, 1800], [4, 1800], [20, 2000]],
            "candidate_driven_pulley_rpm": [[1, 500], [2, 1000], [4, 1500], [20, 1200]],
            "honda_vehicle_speed_kph": [[1, 15], [2, 30], [4, 35], [20, 40]],
        })
        ratio_rates = results["derived_ratio_change_pct_s"]
        output_rates = results["derived_output_speed_change_pct_s"]
        self.assertEqual([time for time, _ in ratio_rates], [2, 4])
        self.assertEqual([time for time, _ in output_rates], [2, 4])
        # The ratio moves 1.2 to 1.8 to 1.2 while output RPM rises on both intervals.
        for (time, ratio_rate), (_, output_rate), (expected_ratio, expected_output, expected_drive) in zip(
            ratio_rates, output_rates,
            ((100 * log(1.5), 100 * log(2), 100 * log(3)), (50 * log(2 / 3), 50 * log(1.5), 0)),
            strict=True,
        ):
            with self.subTest(time=time):
                self.assertAlmostEqual(ratio_rate, expected_ratio)
                self.assertAlmostEqual(output_rate, expected_output)
                self.assertAlmostEqual(ratio_rate + output_rate, expected_drive)

    def test_warming_rate_requires_one_minute_of_contiguous_data(self):
        results = derive_series({"ecm_coolant_sensor_1_c": [
            [time, 10 + time / 10] for time in (*range(0, 66, 3), *range(90, 156, 3))
        ]})
        by_time = dict(results["derived_engine_coolant_warming_rate"])
        self.assertEqual(sorted(by_time), [60, 63, 150, 153])
        self.assertAlmostEqual(by_time[60], 6)
