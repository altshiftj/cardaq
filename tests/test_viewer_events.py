import unittest

from cardaq.viewer.events import trip_events


class TripEventTests(unittest.TestCase):
    def test_engine_start_and_restart_require_observed_zero_rpm(self):
        rpm = [[0, 0], [1, 0], [2, 200], [3, 700], [4, 750], [20, 720], [21, 730],
               [22, 0], [23, 0], [24, 690]]
        events = trip_events({"ecm_engine_speed_rpm": rpm})
        self.assertEqual([(e["kind"], e["start"], e["end"]) for e in events], [
            ("engine-start", 3, 3), ("telemetry-gap", 4, 20), ("engine-restart", 24, 24),
        ])

    def test_launch_stop_and_cruise_are_bounded_by_speed_observations(self):
        speed = [[time, 0] for time in range(7)]
        speed.extend([[7, 2], [8, 6], [9, 25], [10, 62]])
        speed.extend([time, 70 + (time % 2)] for time in range(11, 35))
        speed.extend([[35, 87], [36, 85]])
        rpm = [[time, 750] for time in range(37)]
        events = trip_events({"ecm_vehicle_speed_kph": speed, "ecm_engine_speed_rpm": rpm})
        self.assertEqual([(e["kind"], e["start"], e["end"]) for e in events], [
            ("stopped", 0, 6), ("launch", 6, 8), ("cruise", 11, 34),
        ])

    def test_gap_needs_both_motion_channels_to_be_missing(self):
        speed = [[1, 0], [2, 0], [22, 0]]
        rpm = [[time, 700] for time in range(23)]
        events = trip_events({"ecm_vehicle_speed_kph": speed, "ecm_engine_speed_rpm": rpm})
        self.assertEqual(events, [])

    def test_fuel_cut_spans_do_not_cross_gaps_or_include_isolated_samples(self):
        fuel_cut = [[1, 1], [4, 1], [7, 0], [10, 1], [20, 1], [23, 1]]
        events = trip_events({"derived_fuel_cut_candidate": fuel_cut})
        self.assertEqual([(e["kind"], e["start"], e["end"]) for e in events], [
            ("fuel-cut", 1, 4), ("fuel-cut", 20, 23),
        ])
