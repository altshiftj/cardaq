"""Read classic CAN frames and OBD replies from OBDLink's text output."""

import re
from collections.abc import Iterable


_HEX = re.compile(rb"[0-9A-F]+")
ENGINE_RESPONSE_IDS = {3: "7E8", 8: "18DAF110"}


def pid_bitmaps(
    lines: tuple[bytes, ...], pid: int, address_width: int
) -> tuple[tuple[str | None, int], ...]:
    """Return support bitmaps with their CAN IDs when headers are visible."""
    prefix = bytes((0x41, pid))
    bare_prefix = prefix.hex().upper().encode("ascii")
    replies: list[tuple[str | None, int]] = []
    for line in lines:
        compact = compact_hex(line)
        if compact is None:
            continue
        if len(compact) == 12 and compact.startswith(bare_prefix):
            replies.append((None, int(compact[4:], 16)))
            continue

        frame = single_frame(compact, address_width)
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
        compact = compact_hex(line)
        if compact is None:
            continue
        frame = single_frame(compact, address_width)
        if frame is None:
            continue

        address, payload = frame
        if len(payload) == 5 and payload.startswith(b"\x41\x67"):
            flags, sensor_one, sensor_two = payload[2:]
            first = sensor_one - 40 if flags & 0x01 else None
            second = sensor_two - 40 if flags & 0x02 else None
            readings.append((address, (first, second)))
    return tuple(readings)


def compact_hex(line: bytes) -> bytes | None:
    """Return uppercase hex digits from a spaced or compact adapter line."""
    compact = b"".join(line.split()).upper()
    return compact if _HEX.fullmatch(compact) else None


def can_frame(compact: bytes, address_width: int) -> tuple[str, bytes] | None:
    """Read the CAN address and frame bytes from a compact_hex result."""
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

    return address.decode("ascii"), bytes.fromhex(frame_hex.decode("ascii"))


def responder_frames(lines: Iterable[bytes], address: bytes) -> list[bytes]:
    """Collect one responder's hex frames, rejecting bad frame lengths anywhere in its sequence."""
    frames = []
    for line in lines:
        compact = compact_hex(line)
        if compact is None or not compact.startswith(address):
            continue
        parsed = can_frame(compact, len(address))
        if parsed is None:
            return []
        frames.append(parsed[1])
    return frames


def single_frame(compact: bytes, address_width: int) -> tuple[str, bytes] | None:
    parsed = can_frame(compact, address_width)
    if parsed is None:
        return None
    address, frame = parsed
    payload = single_frame_payload(frame)
    return (address, payload) if payload is not None else None


def single_frame_payload(frame: bytes) -> bytes | None:
    length = frame[0]
    if not 1 <= length <= 7 or length >= len(frame):
        return None
    return frame[1 : 1 + length]


def has_positive_reply(lines: tuple[bytes, ...], command: bytes, addresses: set[str], width: int) -> bool:
    """Recognize a positive single or first frame for a diagnostic request from an expected ECU."""
    query = bytes.fromhex(command.decode("ascii"))
    prefix = bytes((query[0] + 0x40,)) + query[1:]
    for line in lines:
        compact = compact_hex(line)
        parsed = can_frame(compact, width) if compact else None
        if parsed is None or parsed[0] not in addresses:
            continue
        frame = parsed[1]
        payload = single_frame_payload(frame)
        if payload and len(payload) > len(prefix) and payload.startswith(prefix):
            return True
        if (len(frame) == 8 and frame[0] >> 4 == 1 and frame[2:].startswith(prefix)
                and (int.from_bytes(frame[:2], "big") & 0xFFF) > 7):
            return True
    return False
