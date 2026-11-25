import unittest

from cardaq.health.engine import engine_features


def by_key(series):
    return {row["key"]: row for row in engine_features(series)}


class EngineFeatureTests(unittest.TestCase):
    def test_idle_settling_and_closed_loop_use_observed_samples(self):
        # Two stops separated by a telemetry outage must settle independently.
        times = [*range(9), *range(20, 30)]
        trims = [[t, 4] for t in (5, 7, 20, 25, 26, 27, 28, 29)]
        series = {
            "ecm_engine_speed_rpm": [[t, 710] for t in times],
            "ecm_coolant_sensor_1_c": [[t, 80] for t in times],
            "ecm_vehicle_speed_kph": [[t, 0] for t in times],
            "ecm_short_term_fuel_trim_pct": trims,
            "ecm_fuel_system_1_status": [[t, 4 if t == 26 else 2] for t in (5, 7, 20, 25, 26, 27, 29)],
        }
        rows = by_key(series)
        self.assertEqual(rows["engine_idle_rpm"]["count"], 9)
        self.assertEqual(rows["engine_idle_rpm"]["value"], 710)
        self.assertIsNone(rows["engine_idle_rpm_iqr"]["value"])
        self.assertEqual(rows["engine_idle_stft_pct"]["count"], 5)
        self.assertEqual(rows["engine_idle_stft_pct"]["value"], 4)
        self.assertEqual(rows["engine_idle_ltft_pct"]["count"], 0)
        del series["ecm_fuel_system_1_status"]
        self.assertEqual(by_key(series)["engine_idle_stft_pct"]["count"], 0)

    def test_cruise_bands_exclude_load_speed_rpm_temperature_and_acceleration_mismatches(self):
        times = range(16)
        series = {
            "ecm_engine_speed_rpm": [[t, 2000 if t < 6 else 3500] for t in times],
            "ecm_coolant_sensor_1_c": [[t, 80] for t in times],
            "ecm_vehicle_speed_kph": [[t, 115] for t in times],
            "ecm_calculated_load_pct": [[t, 40] for t in times],
            "derived_longitudinal_acceleration_m_s2": [[t, 0] for t in times],
            "ecm_fuel_system_1_status": [[t, 2] for t in times],
            "ecm_long_term_fuel_trim_pct": [[t, 5 if t < 6 else 8] for t in times],
        }
        series["ecm_engine_speed_rpm"][11][1] = 3750
        series["ecm_vehicle_speed_kph"][12][1] = 120
        series["ecm_calculated_load_pct"][13][1] = 60
        series["derived_longitudinal_acceleration_m_s2"][14][1] = -0.31
        series["ecm_coolant_sensor_1_c"][15][1] = 74
        rows = by_key(series)
        self.assertEqual(rows["engine_cruise_low_ltft_pct"]["count"], 6)
        self.assertEqual(rows["engine_cruise_low_ltft_pct"]["value"], 5)
        self.assertEqual(rows["engine_cruise_high_ltft_pct"]["count"], 5)
        self.assertEqual(rows["engine_cruise_high_ltft_pct"]["value"], 8)

    def test_coolant_counts_its_own_samples_after_ten_observed_running_minutes(self):
        times = [*range(606), *range(700, 704)]
        temperatures = [[t, 69] for t in [0, 599, *range(600, 606), 700, 701, 702]]
        series = {
            "ecm_engine_speed_rpm": [[t, 2000] for t in times],
            "ecm_coolant_sensor_1_c": temperatures,
            "ecm_vehicle_speed_kph": [[t, 115] for t in times],
            "ecm_calculated_load_pct": [[t, 40] for t in times],
            "derived_longitudinal_acceleration_m_s2": [[t, 0] for t in times],
        }
        rows = by_key(series)
        self.assertEqual(rows["engine_cruise_low_coolant_c"]["count"], 6)
        self.assertEqual(rows["engine_cruise_low_coolant_c"]["value"], 69)
        self.assertEqual(rows["engine_cruise_high_coolant_c"]["count"], 0)

    def test_missing_streams_leave_all_indicators_unmeasured(self):
        rows = engine_features({})
        self.assertTrue(rows)
        for row in rows:
            self.assertEqual(row["count"], 0)
            self.assertIsNone(row["value"])
