import unittest
from io import BytesIO
from unittest.mock import MagicMock, call, patch

from serial import Serial, SerialException

from cardaq.adapter import AdapterError, AdapterIdentity, identify, open_connection, request
from cardaq.config import SerialSettings


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = MagicMock(spec=Serial)
        self.connection.port = "test-serial"
        self.connection.write.side_effect = len
        serial_factory = patch("cardaq.adapter.serial.Serial", return_value=self.connection)
        serial_factory.start()
        self.addCleanup(serial_factory.stop)
        self.settings = SerialSettings(self.connection.port)

    def test_sends_only_identification_commands(self) -> None:
        replies = {
            b"STDI\r": b"ELM327 v1.4b\r>STDI\r\nOBDLink EX r1.0.0\r\n>",
            b"STI\r": b"STN2230 v5.10.3\r>",
        }

        def exchange(request: bytes) -> int:
            self.connection.read.side_effect = BytesIO(replies[request]).read
            return len(request)

        self.connection.write.side_effect = exchange

        identity = identify(self.settings)

        self.assertEqual(identity, AdapterIdentity("OBDLink EX r1.0.0", "STN2230 v5.10.3"))
        self.assertEqual(self.connection.write.call_args_list, [call(b"STDI\r"), call(b"STI\r")])
        self.connection.close.assert_called_once_with()

    def test_partial_reply_stops_before_firmware_query(self) -> None:
        self.connection.read.side_effect = BytesIO(b"OBDLink EX r1.0\r").read

        with self.assertRaisesRegex(AdapterError, "No complete STDI reply"):
            identify(SerialSettings(self.connection.port, timeout=0.02))

        self.connection.write.assert_called_once_with(b"STDI\r")
        self.connection.close.assert_called_once_with()

    def test_unsupported_identification_is_not_reported_as_hardware(self) -> None:
        self.connection.read.side_effect = BytesIO(b"STDI\r?\r>").read

        with self.assertRaisesRegex(AdapterError, "Unexpected STDI reply"):
            identify(self.settings)

        self.connection.write.assert_called_once_with(b"STDI\r")
        self.connection.close.assert_called_once_with()

    def test_disconnect_closes_the_port(self) -> None:
        self.connection.read.side_effect = SerialException("disconnected")

        with self.assertRaisesRegex(AdapterError, "disconnected"):
            identify(self.settings)

        self.connection.close.assert_called_once_with()

    def test_caller_io_error_preserves_its_cause_and_closes_port(self) -> None:
        disk_error = OSError("capture volume full")

        with self.assertRaises(OSError) as caught, open_connection(self.settings):
            raise disk_error

        self.assertIs(caught.exception, disk_error)
        self.connection.close.assert_called_once_with()

    def test_buffer_reset_error_closes_the_new_port(self) -> None:
        self.connection.reset_input_buffer.side_effect = OSError("USB disconnected")

        with self.assertRaisesRegex(AdapterError, "USB disconnected"):
            identify(self.settings)

        self.connection.write.assert_not_called()
        self.connection.close.assert_called_once_with()

    def test_exchange_returns_immutable_reply_lines(self) -> None:
        self.connection.read.side_effect = BytesIO(b"ATI\rfirst\rsecond\r>").read

        lines = request(self.connection, b"ATI", 2.0)

        self.assertEqual(lines, (b"first", b"second"))
        self.assertTrue(all(isinstance(line, bytes) for line in lines))
