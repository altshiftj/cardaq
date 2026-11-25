import unittest

from cardaq.health.monitors import diagnostic_observations, monitor_summary


TWO_COUNTS = (
    "18 DA F1 10 10 13 46 A3 0B 24 00 00 | "
    "18 DA F1 10 21 00 00 FF FF A3 0C 24 | "
    "18 DA F1 10 22 00 03 00 00 FF FF 55"
)


def framed(records, with_dlc=True):
    payload = b"\x46" + b"".join(bytes.fromhex(record) for record in records)
    frames = [bytes((0x10, len(payload))) + payload[:6]]
    for index, start in enumerate(range(6, len(payload), 7), 1):
        frames.append(bytes((0x20 + index,)) + payload[start : start + 7])
    return " | ".join(
        "18DAF110 " + (f"{len(frame)} " if with_dlc else "") + frame.hex(" ")
        for frame in frames
    )


class MonitorTests(unittest.TestCase):
    def test_ecm_status_is_taken_from_the_matching_response(self):
        lamp = "18 DA F1 1E 06 41 01 00 00 00 00 | 18 DA F1 10 8 06 41 01 82 00 00 00 55"
        self.assertEqual(diagnostic_observations("01 01", lamp), {"ecm_mil_on": 1, "ecm_confirmed_dtc_count": 2})
        fuel = "18 DA F1 10 04 41 03 02 00"
        self.assertEqual(diagnostic_observations("0103", fuel), {"ecm_fuel_system_1_status": 2})
        self.assertEqual(diagnostic_observations("0101", fuel), {})
        self.assertEqual(diagnostic_observations("0103", fuel.replace("04 41", "03 41")), {})
        self.assertEqual(diagnostic_observations("0103", fuel.replace("10 04", "1E 04")), {})

    def test_decodes_single_test_and_multiple_records_without_assuming_order(self):
        weighted = "A3 0B 24 01 02 00 00 FF FF"
        current = "A3 0C 24 00 03 00 00 FF FF"
        other = "A3 81 24 00 00 00 00 FF FF"
        self.assertEqual(diagnostic_observations("06a3", framed([weighted])), {"ecm_cyl_2_misfires_weighted": 258})
        self.assertEqual(diagnostic_observations("06A3", framed([current, other, weighted])), {
            "ecm_cyl_2_misfires_cycle": 3, "ecm_cyl_2_misfires_weighted": 258,
        })
        self.assertEqual(diagnostic_observations("06A3", TWO_COUNTS), {
            "ecm_cyl_2_misfires_cycle": 3, "ecm_cyl_2_misfires_weighted": 0,
        })
        self.assertEqual(diagnostic_observations("06A3", framed([weighted.replace("0B 24", "0B 23"), current])),
                         {"ecm_cyl_2_misfires_cycle": 3})

    def test_damaged_ambiguous_or_unrelated_monitor_replies_give_no_count(self):
        first, middle, last = TWO_COUNTS.split(" | ")
        invalid = [
            "", "NO DATA", TWO_COUNTS.replace("18 DA F1 10", "18 DA F1 1E"),
            TWO_COUNTS.replace("46 A3", "46 A2"), TWO_COUNTS.replace("46 A3", "62 A3"),
            TWO_COUNTS.replace("21 00 00", "22 00 00"), TWO_COUNTS.replace("10 13 46", "10 12 46"),
            TWO_COUNTS.replace("10 13 46", "7 10 13 46"),
            " | ".join([first, last]), " | ".join([first, middle, last[:-6]]),
            " | ".join([first, middle, last, last]),
            TWO_COUNTS.replace("A3 0B", "A3 0C"), framed(["A3 0B 99 00 00 00 00 FF FF"]),
        ]
        for response in invalid:
            with self.subTest(response=response):
                self.assertEqual(diagnostic_observations("06A3", response), {})

    def test_reports_observed_counts_and_drops_without_summing_polls(self):
        cylinders, mil = monitor_summary({
            "ecm_cyl_2_misfires_cycle": [(2, 3), (62, 3), (122, 0), (182, 1), (242, 1)],
            "ecm_cyl_2_misfires_weighted": [(2, 0), (62, 0)],
            "ecm_mil_on": [(1, 0), (61, 1), (121, 0)],
            "ecm_confirmed_dtc_count": [(1, 0), (61, 2), (121, 1)],
        })
        self.assertEqual(len(cylinders), 4)
        self.assertEqual(cylinders[1], {
            "cylinder": 2, "polls": 5, "first": 3, "last": 1, "peak": 3, "peakElapsed": 2,
            "weightedLast": 0, "weightedPolls": 2,
            "transitions": [{"seconds": 2, "count": 3}, {"seconds": 122, "count": 0}, {"seconds": 182, "count": 1}],
        })
        self.assertEqual(cylinders[0]["polls"], 0)
        self.assertIsNone(cylinders[0]["peak"])
        self.assertIsNone(cylinders[0]["weightedLast"])
        self.assertEqual(mil, {"polls": 3, "everOn": True, "maxCount": 2})
        self.assertEqual(monitor_summary({})[1], {"polls": 0, "everOn": None, "maxCount": None})
