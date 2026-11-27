import unittest
from collections import deque
from io import BytesIO
from unittest.mock import MagicMock, patch

from serial import Serial

from cardaq.adapter import AdapterError
from cardaq.config import SerialSettings
from cardaq.obd import sweep


_WITHOUT_HEADERS = b"0100\r41 00 00 10 00 01\r41 00 00 10 00 00\r>"
_WITH_HEADERS = (
    b"0100\r18 DA F1 10 06 41 00 00 10 00 01\r"
    b"18 DA F1 18 06 41 00 00 10 00 00\r>"
)


class SweepTests(unittest.TestCase):
    def set_up_serial(self, *exchanges: tuple[bytes, bytes]) -> None:
        connection = MagicMock(spec=Serial)
        connection.port = "test-serial"
        pending = deque(exchanges)

        def exchange(request: bytes) -> int:
            self.assertTrue(pending, f"Unexpected serial write {request!r}")
            expected, response = pending.popleft()
            self.assertEqual(request, expected)
            connection.read.side_effect = BytesIO(response).read
            return len(request)

        connection.write.side_effect = exchange
        serial_factory = patch("cardaq.adapter.serial.Serial", return_value=connection)
        serial_factory.start()
        self.addCleanup(serial_factory.stop)
        self.addCleanup(connection.close.assert_called_once_with)
        self.addCleanup(self.assertFalse, pending, "Expected more serial exchanges")

    def test_sweeps_per_ecu_and_samples_shared_pid_once(self) -> None:
        self.set_up_serial(
            (b"0100\r", _WITHOUT_HEADERS),
            (b"ATDPN\r", b"ATDPN\rA7\r>"),
            (b"ATH1\r", b"ATH1\rOK\r>"),
            (b"0100\r", _WITH_HEADERS),
            (b"0120\r", b"18 DA F1 10 06 41 20 00 00 00 01\r>"),
            (b"0140\r", b"18 DA F1 10 06 41 40 00 00 00 01\r>"),
            (b"0160\r", b"18 DA F1 10 06 41 60 02 00 00 00\r>"),
            (b"010C\r", b"18 DA F1 10 04 41 0C 0B B8\r18 DA F1 18 04 41 0C 0B E0\r>"),
            (b"0167\r", b"18 DA F1 10 05 41 67 03 71 44\r>"),
            (b"ATH0\r", b"ATH0\rOK\r>"),
        )

        result = sweep(SerialSettings("test-serial"), sample=True)

        self.assertEqual(
            {ecu.address: ecu.pids for ecu in result.ecus},
            {"18DAF110": (0x0C, 0x67), "18DAF118": (0x0C,)},
        )
        self.assertEqual(tuple(sample.pid for sample in result.samples), (0x0C, 0x67))
        self.assertEqual(
            result.samples[0].lines,
            ("18 DA F1 10 04 41 0C 0B B8", "18 DA F1 18 04 41 0C 0B E0"),
        )
        self.assertEqual(result.samples[1].coolant, (("18DAF110", (73, 28)),))

    def test_missing_required_continuation_fails_and_restores_headers(self) -> None:
        self.set_up_serial(
            (b"0100\r", _WITHOUT_HEADERS),
            (b"ATDPN\r", b"7\r>"),
            (b"ATH1\r", b"OK\r>"),
            (b"0100\r", _WITH_HEADERS),
            (b"0120\r", b"NO DATA\r>"),
            (b"ATH0\r", b"OK\r>"),
        )

        with self.assertRaisesRegex(AdapterError, "Missing PID support bitmap 20 from CAN ID 18DAF110"):
            sweep(SerialSettings("test-serial"))

    def test_missing_ecu_after_enabling_headers_fails_and_restores_headers(self) -> None:
        self.set_up_serial(
            (b"0100\r", _WITHOUT_HEADERS),
            (b"ATDPN\r", b"7\r>"),
            (b"ATH1\r", b"OK\r>"),
            (b"0100\r", b"18 DA F1 10 06 41 00 00 10 00 01\r>"),
            (b"ATH0\r", b"OK\r>"),
        )

        with self.assertRaisesRegex(AdapterError, "responders changed"):
            sweep(SerialSettings("test-serial"))

    def test_preserves_existing_headers_and_handles_compact_frames_with_dlc(self) -> None:
        self.set_up_serial(
            (b"0100\r", b"7E8706410000100000\r>"),
            (b"ATDPN\r", b"A6\r>"),
        )

        result = sweep(SerialSettings("test-serial"))

        self.assertEqual([(ecu.address, ecu.pids) for ecu in result.ecus], [("7E8", (0x0C,))])
        self.assertEqual(result.samples, ())

    def test_auto_sweep_samples_only_advertised_data_after_protocol_search(self) -> None:
        self.set_up_serial(
            *((cmd + b"\r", b"OK\r>") for cmd in (b"ATD", b"ATTP0", b"ATAR", b"ATH1", b"ATCAF1", b"ATCFC1")),
            (b"0100\r", b"SEARCHING...\r7E8 06 41 00 08 10 00 00\r>"),
            (b"ATDPN\r", b"A6\r>"),
            (b"0105\r", b"7E8 03 41 05 63\r>"),
            (b"010C\r", b"7E8 04 41 0C 00 00\r>"),
            (b"ATH0\r", b"OK\r>"),
        )
        result = sweep(SerialSettings("test-serial"), auto=True, sample=True)
        self.assertEqual(result.ecus[0].pids, (5, 12))
        self.assertEqual(result.samples[1].lines, ("7E8 04 41 0C 00 00",))
