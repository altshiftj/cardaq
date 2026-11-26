import unittest
from math import exp

from cardaq.viewer.trip import TRIP_METRICS, derive_trip_series, speed_band_dwell


SPEED = "ecm_vehicle_speed_kph"
RPM = "ecm_engine_speed_rpm"
FUEL = "ecm_engine_fuel_rate_g_s"
PEDAL = "ecm_accelerator_pedal_pct"
AIRFLOW = "ecm_mass_airflow_g_s"


class DerivedTripTests(unittest.TestCase):
    def test_integrals_carry_observed_totals_across_disconnected_intervals(self):
        results = derive_trip_series({
            SPEED: [[0, 36], [1, 36], [2, 36], [500, 72], [501, 72]],
            RPM: [[0, 600], [1, 600], [2, 600], [500, 1800], [501, 1800]],
            FUEL: [[0, 1], [2, 2], [500, 4], [501, 4]],
        })
        self.assertEqual(results["derived_distance_km"], [
            [0, 0], [1, 0.01], [2, 0.02], [500, 0.02], [501, 0.04],
        ])
        self.assertEqual(results["derived_engine_revolutions"], [
            [0, 0], [1, 10], [2, 20], [500, 20], [501, 50],
        ])
        self.assertEqual(results["derived_fuel_used_g"], [[0, 0], [2, 3], [500, 3], [501, 7]])
        self.assertEqual(results["derived_positive_speed_energy_j_kg"], [[0, 0], [1, 0], [2, 0], [500, 0], [501, 0]])
        self.assertNotIn("derived_rolling_fuel_g_km", results)

    def test_distance_and_revolutions_use_intervals_up_to_the_gap_limit(self):
        for gap, distance, revolutions in (
            (1.49, 0.05235, 52.35),
            (1.50, 0.05250, 52.50),
            (1.51, 0.03000, 30.00),
        ):
            with self.subTest(gap=gap):
                times = [0, 1, 1 + gap, 2 + gap]
                results = derive_trip_series({
                    SPEED: [[time, speed] for time, speed in zip(times, (36, 36, 72, 72), strict=True)],
                    RPM: [[time, rpm] for time, rpm in zip(times, (600, 600, 1200, 1200), strict=True)],
                })
                # The final one-second interval covers 0.02 km and 20 engine turns.
                for metric, expected in (
                    ("derived_distance_km", [0, 0.01, distance - 0.02, distance]),
                    ("derived_engine_revolutions", [0, 10, revolutions - 20, revolutions]),
                ):
                    points = results[metric]
                    self.assertEqual([time for time, _ in points], times, metric)
                    for (_, value), total in zip(points, expected, strict=True):
                        self.assertAlmostEqual(value, total, msg=metric)

    def test_distance_and_positive_speed_energy_allow_irregular_sample_times(self):
        regular = [(0, 0), (1, 36), (2, 36), (3, 0), (4, 0), (6, 72), (7, 72)]
        irregular = [(0, 0), (1, 36), (1.375, 36), (2, 36), (3, 0), (3.625, 0), (4, 0), (6, 72), (7, 72)]
        # The 10 m/s step has two seconds to raise smoothed speed before braking.
        cruise_speed_m_s = 10 * (1 - exp(-2 / 1.5))
        expected_energy = cruise_speed_m_s**2 / 2
        for case, samples, offset in (("regular", regular, 0), ("irregular", irregular, 0), ("shifted", irregular, 23.25)):
            with self.subTest(case=case):
                speed = [[time + offset, kph] for time, kph in samples]
                results = derive_trip_series({SPEED: speed})
                distance = dict(results["derived_distance_km"])
                energy = dict(results["derived_positive_speed_energy_j_kg"])
                self.assertEqual(list(distance), [time for time, _ in speed])
                self.assertEqual(list(energy), list(distance))
                self.assertEqual(energy[offset], 0)
                self.assertGreater(energy[1 + offset], 0)
                self.assertLess(energy[1 + offset], expected_energy)
                for time, total in ((2, 0.015), (3, 0.02), (4, 0.02), (6, 0.02), (7, 0.04)):
                    self.assertAlmostEqual(distance[time + offset], total)
                # Braking and the unobserved jump to 72 km/h leave accumulated energy in place.
                for time, total in energy.items():
                    if time >= 2 + offset:
                        self.assertAlmostEqual(total, expected_energy, msg=f"Sample at {time} seconds")

    def test_rolling_values_need_new_observed_distance_after_gap(self):
        times = [*range(41), *range(500, 541)]
        results = derive_trip_series({
            SPEED: [[time, 72] for time in times],
            RPM: [[time, 1800] for time in times],
            FUEL: [[time, 1.44 if time < 500 else 2.88] for time in times],
        })
        fuel_per_km = results["derived_rolling_fuel_g_km"]
        self.assertEqual(min(time for time, _ in fuel_per_km), 25)
        self.assertGreaterEqual(min(time for time, _ in fuel_per_km if time >= 500), 525)
        for time, rate in fuel_per_km:
            self.assertAlmostEqual(rate, 72 if time < 500 else 144)
        for _, rate in results["derived_rolling_revolutions_per_km"]:
            self.assertAlmostEqual(rate, 1500)
        for time, rate in results["derived_rolling_fuel_per_1000_rev"]:
            self.assertAlmostEqual(rate, 48 if time < 500 else 96)

    def test_stopped_fuel_excludes_moving_and_key_off_intervals(self):
        stopped_speeds = [0, 0, 0, 10, 10, 0, 0, 0, 0, 0]
        results = derive_trip_series({
            SPEED: [[time, value] for time, value in enumerate(stopped_speeds)],
            RPM: [[time, 800 if time < 8 else 0] for time in range(10)],
            FUEL: [[time, 2] for time in range(10)],
        })
        self.assertEqual(results["derived_engine_on_stopped_s"][-1], [9, 4])
        self.assertEqual(results["derived_engine_on_stopped_fuel_g"][-1], [9, 8])
        fuel_only = derive_trip_series({FUEL: [[0, 1], [1, 2]]})
        self.assertNotIn("derived_engine_on_stopped_fuel_g", fuel_only)

    def test_fuel_cut_requires_a_released_pedal_and_consecutive_moving_samples(self):
        times = [*range(10), 20]
        rates = [1, 1, 1, 0, 0, 1, 0, 1, 0, 0, 0]
        results = derive_trip_series({
            SPEED: [[time, 0 if time < 3 else 30] for time in times],
            RPM: [[time, 900 if time < 3 else 1500] for time in times],
            PEDAL: [[time, 25 if time == 8 else 18.8] for time in times],
            FUEL: [[time, fuel] for time, fuel in zip(times, rates, strict=True)],
        })
        states = results["derived_fuel_cut_candidate"]
        self.assertEqual([time for time, state in states if state == 1], [3, 4])
        self.assertEqual([time for time, _ in states], times)

    def test_air_per_intake_uses_running_rpm_from_a_nearby_observation(self):
        results = derive_trip_series({
            RPM: [[0, 0], [1, 3000], [2, 4000]],
            AIRFLOW: [[0, 2], [1.04, 20], [2.5, 40], [6, 40]],
        })
        self.assertEqual(results["derived_air_mass_per_cylinder_mg"], [[1.04, 200], [2.5, 300]])
        self.assertTrue(all(key in TRIP_METRICS for key in results))

    def test_speed_dwell_splits_crossings_and_omits_outages(self):
        data = speed_band_dwell([[0, 0], [1, 0], [2, 60], [3, 60], [4, 120], [500, 120], [501, 120]])
        seconds = {item["label"]: item["seconds"] for item in data}
        for label, expected in {
            "Stopped": 1,
            "Moving below 30 km/h": 0.5,
            "30 to <60 km/h": 0.5,
            "60 to <90 km/h": 1.5,
            "90 to <110 km/h": 1 / 3,
            "110+ km/h": 1 + 1 / 6,
        }.items():
            self.assertAlmostEqual(seconds[label], expected)
        self.assertAlmostEqual(sum(seconds.values()), 5)
        self.assertEqual(speed_band_dwell([[0, 0], [30, 0]]), [])
