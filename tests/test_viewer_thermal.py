import unittest

from cardaq.viewer.thermal import thermal_milestones


RPM = "ecm_engine_speed_rpm"
COOLANT = "ecm_coolant_sensor_1_c"
CVT = "candidate_cvt_fluid_temperature_c"
CATALYST = "ecm_catalyst_temperature_c"
DISTANCE = "derived_distance_km"


class ThermalMilestoneTests(unittest.TestCase):
    def test_reports_preheated_coolant_and_times_the_first_held_crossing(self):
        milestones = thermal_milestones({
            RPM: [[0, 0], [1, 150], [2, 900], [3, 950], [4, 900], [5, 900], [6, 900], [7, 900]],
            COOLANT: [[1.5, 45], [2.25, 45], [3.25, 80], [4.25, 53], [5.5, 75], [6.5, 75]],
            DISTANCE: [[float(t), 0.1 * t] for t in range(8)],
        })

        self.assertEqual([result["target"] for result in milestones], [40, 50, 75])
        warm, rising, hot = milestones
        self.assertTrue(warm["alreadyWarm"])
        self.assertEqual(warm["seconds"], 0)
        self.assertEqual(warm["distanceKm"], 0)
        self.assertEqual(rising["seconds"], 1.25)
        self.assertAlmostEqual(rising["distanceKm"], 0.125)
        self.assertEqual(hot["seconds"], 3.5)
        self.assertAlmostEqual(hot["distanceKm"], 0.35)

    def test_drops_above_target_readings_after_temperature_and_rpm_outages(self):
        milestones = thermal_milestones({
            RPM: [
                [0, 0], [1, 850], [2, 850], [5, 850], [8, 850], [10, 850], [12, 850],
                [30, 0], [31, 950], [32, 950], [33, 950],
            ],
            CVT: [[0, 29], [1, 33], [2, 35], [9, 41], [10, 42], [31, 70], [32, 71]],
            CATALYST: [[0, 60], [2, 80], [5, 290], [8, 310], [10, 320], [31, 450], [32, 460]],
        })

        self.assertEqual(milestones, [{"label": "ECU-reported catalyst", "target": 300, "seconds": 7}])

    def test_keeps_milestone_time_when_distance_has_no_local_coverage(self):
        milestones = thermal_milestones({
            RPM: [[0, 0], [1, 850], [2, 850], [3, 850], [4, 850], [5, 850]],
            CVT: [[0, 29], [1, 32], [2, 38], [3.5, 40], [4.5, 40]],
            DISTANCE: [[0, 0], [1, 0], [2, 0.01], [5, 0.01]],
        })

        self.assertEqual(milestones, [{"label": "CVT fluid estimate", "target": 40, "seconds": 2.5}])

    def test_capture_already_running_cannot_anchor_first_warm_up_at_later_restart(self):
        milestones = thermal_milestones({
            RPM: [[0, 850], [1, 850], [2, 0], [3, 0], [4, 950], [5, 950], [6, 950]],
            COOLANT: [[0, 75], [4, 75], [5, 75]],
        })

        self.assertEqual(milestones, [])
