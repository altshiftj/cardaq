"""Discover serial ports, identify OBDLink adapters, and exchange serial commands."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from time import monotonic

import serial
from serial.tools.list_ports import comports

from .config import SerialSettings


_HARDWARE_ID = re.compile(rb"[\x20-\x7e]+ r[0-9]+(?:\.[0-9]+){1,2}")
_FIRMWARE_ID = re.compile(rb"STN[0-9]+ v[0-9]+(?:\.[0-9]+){2}")
_MAX_REPLY_BYTES = 256
_READ_INTERVAL = 0.05


class AdapterError(RuntimeError):
    """Serial discovery, communication, or an expected adapter response failed."""


@dataclass(frozen=True)
class AdapterIdentity:
    hardware: str
    firmware: str


def available_ports() -> list[tuple[str, str | None]]:
    try:
        return [(port.device, port.description) for port in sorted(comports())]
    except OSError as error:
        raise AdapterError(f"Could not enumerate serial ports: {error}") from error


def identify(settings: SerialSettings) -> AdapterIdentity:
    with open_connection(settings) as connection:
        hardware = _request_id(connection, b"STDI", _HARDWARE_ID, settings.timeout)
        firmware = _request_id(connection, b"STI", _FIRMWARE_ID, settings.timeout)
    return AdapterIdentity(hardware, firmware)


@contextmanager
def open_connection(settings: SerialSettings) -> Iterator[serial.Serial]:
    with _serial_io(settings.port):
        connection = serial.Serial(
            port=settings.port,
            baudrate=settings.baudrate,
            timeout=min(settings.timeout, _READ_INTERVAL),
            write_timeout=settings.timeout,
        )
    try:
        with _serial_io(settings.port):
            connection.reset_input_buffer()
        yield connection
    finally:
        with _serial_io(settings.port):
            connection.close()


@contextmanager
def _serial_io(port: str | None) -> Iterator[None]:
    try:
        yield
    except (OSError, ValueError, OverflowError) as error:
        raise AdapterError(
            f"Serial I/O on {port!r} failed: {error}. "
            "Check the connection and close other applications using the port."
        ) from error


def _request_id(
    connection: serial.Serial, command: bytes, expected: re.Pattern[bytes], timeout: float
) -> str:
    lines = request(connection, command, timeout, max_reply_bytes=_MAX_REPLY_BYTES)
    if len(lines) == 1 and expected.fullmatch(lines[0]):
        return lines[0].decode("ascii")
    raise AdapterError(
        f"Unexpected {command.decode('ascii')} reply on {connection.port!r}. "
        "Check that the selected port and baud rate match the OBDLink adapter."
    )


def request(
    connection: serial.Serial, command: bytes, timeout: float, *, max_reply_bytes: int = 8192
) -> tuple[bytes, ...]:
    label = command.decode("ascii")
    wire_command = command + b"\r"
    with _serial_io(connection.port):
        if connection.write(wire_command) != len(wire_command):
            raise AdapterError(f"Could not send the complete {label} command to {connection.port!r}.")

        deadline = monotonic() + timeout
        response = bytearray()
        bytes_read = 0
        while bytes_read < max_reply_bytes and monotonic() < deadline:
            byte = connection.read(1)
            if not byte:
                continue
            bytes_read += 1
            if byte != b">":
                response.extend(byte)
                continue

            lines = [line.strip() for line in bytes(response).splitlines() if line.strip()]
            if lines and lines[0].upper() == command:
                lines.pop(0)
            if command == b"STDI" and (not lines or (len(lines) == 1 and lines[0].startswith(b"ELM327 "))):
                # A startup prompt can arrive just after opening the port.
                response.clear()
                continue
            return tuple(lines)

    raise AdapterError(
        f"No complete {label} reply from {connection.port!r}. "
        "Check adapter power, the selected port, and the baud rate."
    )
