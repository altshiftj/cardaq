"""Decode single-frame Service 01 replies from OBDLink's CAN text output."""

import re


_HEX = re.compile(rb"[0-9A-F]+")


def pid_bitmaps(
    lines: tuple[bytes, ...], pid: int, address_width: int
) -> tuple[tuple[str | None, int], ...]:
    """Return support bitmaps with their CAN IDs when headers are visible."""
    prefix = bytes((0x41, pid))
    bare_prefix = prefix.hex().upper().encode("ascii")
    replies: list[tuple[str | None, int]] = []
    for line in lines:
        compact = _compact_hex(line)
        if compact is None:
            continue
        if len(compact) == 12 and compact.startswith(bare_prefix):
            replies.append((None, int(compact[4:], 16)))
            continue

        frame = _single_frame(compact, address_width)
        if frame is not None:
            address, payload = frame
            if len(payload) == 6 and payload.startswith(prefix):
                replies.append((address, int.from_bytes(payload[2:], "big")))
    return tuple(replies)


def coolant_temperatures(
    lines: tuple[bytes, ...], address_width: int
) -> tuple[tuple[str, tuple[int | None, int | None]], ...]:
    """Return PID 0x67 temperatures in Celsius for supported sensors."""
    readings = []
    for line in lines:
        compact = _compact_hex(line)
        if compact is None:
            continue
        frame = _single_frame(compact, address_width)
        if frame is None:
            continue

        address, payload = frame
        if len(payload) == 5 and payload.startswith(b"\x41\x67"):
            flags, sensor_one, sensor_two = payload[2:]
            first = sensor_one - 40 if flags & 0x01 else None
            second = sensor_two - 40 if flags & 0x02 else None
            readings.append((address, (first, second)))
    return tuple(readings)


def _compact_hex(line: bytes) -> bytes | None:
    compact = b"".join(line.split()).upper()
    return compact if _HEX.fullmatch(compact) else None


def _single_frame(compact: bytes, address_width: int) -> tuple[str, bytes] | None:
    address = compact[:address_width]
    frame_hex = compact[address_width:]
    if len(frame_hex) < 4:
        return None
    if int(address, 16) > (0x7FF if address_width == 3 else 0x1FFFFFFF):
        return None

    # ATD1 puts a single DLC digit before the frame bytes.
    if len(frame_hex) % 2:
        dlc = int(frame_hex[:1], 16)
        frame_hex = frame_hex[1:]
        if dlc * 2 != len(frame_hex):
            return None
    if len(frame_hex) > 16:
        return None

    frame = bytes.fromhex(frame_hex.decode("ascii"))
    length = frame[0]
    if not 1 <= length <= 7 or length >= len(frame):
        return None
    return address.decode("ascii"), frame[1 : 1 + length]
