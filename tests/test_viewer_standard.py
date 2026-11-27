import unittest

from cardaq.viewer.standard import STANDARD_CHANNELS, standard_observations


class StandardObservationTests(unittest.TestCase):
    def test_decodes_scaled_values_from_the_ecm(self) -> None:
        cases = (
            ("0162", "7E9 03 41 62 AA | 7E8 03 41 62 79", "indicated_torque_pct", -4),
            ("0163", "18 DA F1 10 04 41 63 01 08", "reference_torque_nm", 264),
            ("018E", "18 DA F1 10 03 41 8E 88", "friction_torque_pct", 11),
            ("01 9d", "18 DA F1 10 06 41 9D 00 32 00 25", "engine_fuel_rate_g_s", 1),
            ("019D", "18 DA F1 10 06 41 9D 00 00 00 00", "engine_fuel_rate_g_s", 0),
            ("0104", "18 DA F1 10 03 41 04 33", "calculated_load_pct", 20),
            ("0149", "18 DA F1 10 03 41 49 33", "accelerator_pedal_pct", 20),
            ("0166", "18 DA F1 10 07 41 66 01 01 00 FF FF", "mass_airflow_g_s", 8),
            ("01A6", "18 DA F1 10 06 41 A6 00 11 BA 34", "odometer_km", 116178),
            ("013C", "18 DA F1 10 04 41 3C 03 E8", "catalyst_temperature_c", 60),
            ("0106", "18 DA F1 10 03 41 06 70", "short_term_fuel_trim_pct", -12.5),
            ("0107", "18 DA F1 10 03 41 07 90", "long_term_fuel_trim_pct", 12.5),
            ("010E", "18 DA F1 10 03 41 0E 70", "ignition_timing_deg", -8),
            ("0111", "18 DA F1 10 03 41 11 33", "throttle_pct", 20),
            ("012E", "18 DA F1 10 03 41 2E 33", "evap_purge_pct", 20),
        )
        for command, frame, name, value in cases:
            with self.subTest(command=command, name=name, value=value):
                key = f"ecm_{name}"
                self.assertIn(key, STANDARD_CHANNELS)
                observation = standard_observations(command, frame)
                self.assertEqual(set(observation), {key})
                self.assertAlmostEqual(observation[key], value)

    def test_ignores_other_ecus_and_incomplete_or_unrelated_frames(self) -> None:
        reply = (
            "NO DATA | 18 DA F1 1E 03 41 49 FF | 18 DA F1 10 04 41 49 00 00 |"
            " 18 DA F1 10 03 41 11 FF | 18 DA F1 10 03 41 49 | 18 DA F1 10 4 03 41 49 00"
        )
        self.assertEqual(standard_observations("0149", reply), {"ecm_accelerator_pedal_pct": 0})
        self.assertEqual(standard_observations("0166", "18 DA F1 10 07 41 66 02 01 00 00 00"), {})
        self.assertEqual(standard_observations("0111", "18 DA F1 1E 03 41 11 FF"), {})
        self.assertEqual(standard_observations("0163", "7E8 03 41 63 B9"), {})
        self.assertEqual(standard_observations("018E", "7E8 03 41 62 88"), {})
        self.assertEqual(standard_observations("22 23 22", reply), {})

    def test_reassembles_both_intake_temperature_frames(self) -> None:
        first = "18 DA F1 10 8 10 09 41 68 01 31 00 00"
        second = "18 DA F1 10 21 00 00 00 55 55 55 55"
        self.assertEqual(
            standard_observations("0168", f"{first} | {second}"), {"ecm_intake_air_temperature_c": 9},
        )
        for malformed in (
            first,
            f"{second} | {first}",
            f"{first} | {second.replace('21 00', '22 00')}",
            f"{first} | {second.replace('F1 10', 'F1 1E')}",
            f"{first.replace('68 01', '68 02')} | {second}",
        ):
            with self.subTest(reply=malformed):
                self.assertEqual(standard_observations("0168", malformed), {})

    def test_11_bit_engine_multiframe_ignores_interleaved_other_responder(self) -> None:
        first = "7E8 8 10 09 41 68 01 31 00 00"
        unrelated = "7EA 21 FF FF FF FF FF FF FF"
        self.assertEqual(standard_observations("0168", f"{first} | {unrelated}"), {})
        self.assertEqual(
            standard_observations("0168", f"{first} | {unrelated} | 7E8 21 00 00 00"),
            {"ecm_intake_air_temperature_c": 9},
        )
