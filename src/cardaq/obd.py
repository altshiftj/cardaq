"""Discover and sample advertised standard Mode 01 PIDs on ISO 15765-4 CAN."""

from dataclasses import dataclass

from serial import Serial

from .adapter import AdapterError, open_connection, request
from .config import SerialSettings
from .obd_frames import coolant_temperatures, pid_bitmaps


@dataclass(frozen=True)
class EcuPids:
    address: str
    pids: tuple[int, ...]


@dataclass(frozen=True)
class PidSample:
    pid: int
    lines: tuple[str, ...]
    coolant: tuple[tuple[str, tuple[int | None, int | None]], ...] = ()


@dataclass(frozen=True)
class SweepResult:
    ecus: tuple[EcuPids, ...]
    samples: tuple[PidSample, ...]


def _can_address_width(connection: Serial, timeout: float) -> int:
    protocol = request(connection, b"ATDPN", timeout)
    number = protocol[0].upper().removeprefix(b"A") if len(protocol) == 1 else b""
    if number not in (b"6", b"7", b"8", b"9"):
        raise AdapterError("PID discovery requires an active ISO 15765-4 CAN protocol.")
    return 3 if number in (b"6", b"8") else 8


def discover_standard(connection: Serial, timeout: float, *, sample: bool = False) -> SweepResult:
    """Start a fresh functional OBD session and leave addressed replies enabled for polling."""
    for command in (b"ATD", b"ATTP0", b"ATAR", b"ATH1", b"ATCAF1", b"ATCFC1"):
        if request(connection, command, timeout) != (b"OK",):
            raise AdapterError(f"Adapter did not acknowledge {command.decode('ascii')}.")
    # Automatic protocol search may take longer than subsequent data requests.
    initial = request(connection, b"0100", max(timeout, 15.0))
    width = _can_address_width(connection, timeout)
    bitmaps = _addressed_bitmaps(pid_bitmaps(initial, 0, width), 0)
    return _sweep_addressed(connection, timeout, width, bitmaps, sample)


def sweep(settings: SerialSettings, *, sample: bool = False, auto: bool = False) -> SweepResult:
    with open_connection(settings) as connection:
        if auto:
            try:
                return discover_standard(connection, settings.timeout, sample=sample)
            finally:
                _set_headers(connection, b"ATH0", settings.timeout)
        initial_reply = request(connection, b"0100", settings.timeout)
        address_width = _can_address_width(connection, settings.timeout)
        initial = pid_bitmaps(initial_reply, 0, address_width)
        if not initial:
            raise AdapterError("The vehicle did not return a Mode 01 PID support bitmap.")

        if all(address is not None for address, _ in initial):
            bitmaps = _addressed_bitmaps(initial, 0)
            return _sweep_addressed(connection, settings.timeout, address_width, bitmaps, sample)
        if any(address is not None for address, _ in initial):
            raise AdapterError("The adapter returned a mix of replies with and without CAN headers.")

        try:
            _set_headers(connection, b"ATH1", settings.timeout)
            addressed_reply = request(connection, b"0100", settings.timeout)
            addressed = pid_bitmaps(addressed_reply, 0, address_width)
            addressed_bitmaps = _addressed_bitmaps(addressed, 0)
            if sorted(addressed_bitmaps.values()) != sorted(bitmap for _, bitmap in initial):
                raise AdapterError("Mode 01 responders changed after enabling CAN headers. Retry the sweep.")
            return _sweep_addressed(connection, settings.timeout, address_width, addressed_bitmaps, sample)
        finally:
            try:
                _set_headers(connection, b"ATH0", settings.timeout)
            except (AdapterError, OSError) as error:
                raise AdapterError(
                    f"Could not restore the original CAN header format. {error}"
                ) from error


def _set_headers(connection: Serial, command: bytes, timeout: float) -> None:
    if request(connection, command, timeout) != (b"OK",):
        raise AdapterError(f"The adapter did not acknowledge {command.decode('ascii')}.")


def _sweep_addressed(
    connection: Serial,
    timeout: float,
    address_width: int,
    bitmaps: dict[str, int],
    sample: bool,
) -> SweepResult:
    pids: dict[str, list[int]] = {address: [] for address in bitmaps}
    for base in range(0, 0x100, 0x20):
        if base:
            command = f"01{base:02X}".encode("ascii")
            replies = _addressed_bitmaps(
                pid_bitmaps(request(connection, command, timeout), base, address_width), base
            )
            missing = bitmaps.keys() - replies.keys()
            if missing:
                addresses = ", ".join(sorted(missing))
                raise AdapterError(f"Missing PID support bitmap {base:02X} from CAN ID {addresses}.")
            bitmaps = {address: replies[address] for address in bitmaps}

        for address, bitmap in bitmaps.items():
            pids[address].extend(base + offset for offset in range(1, 32) if bitmap & (1 << (32 - offset)))
        bitmaps = {address: bitmap for address, bitmap in bitmaps.items() if bitmap & 1}
        if not bitmaps:
            break

    ecus = tuple(EcuPids(address, tuple(pids[address])) for address in sorted(pids))
    samples = []
    if sample:
        for pid in sorted({pid for ecu in ecus for pid in ecu.pids}):
            lines = request(connection, f"01{pid:02X}".encode("ascii"), timeout)
            coolant = coolant_temperatures(lines, address_width) if pid == 0x67 else ()
            display_lines = tuple(line.decode("ascii", errors="backslashreplace") for line in lines)
            samples.append(PidSample(pid, display_lines, coolant))
    return SweepResult(ecus, tuple(samples))


def _addressed_bitmaps(
    replies: tuple[tuple[str | None, int], ...], pid: int
) -> dict[str, int]:
    bitmaps: dict[str, int] = {}
    for address, bitmap in replies:
        if address is None:
            raise AdapterError(f"PID support bitmap {pid:02X} arrived without a CAN header.")
        if address in bitmaps and bitmaps[address] != bitmap:
            raise AdapterError(f"Conflicting PID support bitmaps {pid:02X} from CAN ID {address}.")
        bitmaps[address] = bitmap
    if pid == 0 and not bitmaps:
        raise AdapterError("The vehicle did not return a PID support bitmap with a CAN header.")
    return bitmaps
