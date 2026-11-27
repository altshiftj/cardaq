"""Decode selected measurements from the Civic pilot's raw diagnostic replies."""

from .honda_fields import HONDA_FIELDS
from .obd_frames import ENGINE_RESPONSE_IDS, _compact_hex, _single_frame, coolant_temperatures


_ECUS = {"18DAF110": "ecm", "18DAF11E": "tcm"}
_STANDARD_MEASUREMENTS = {
    b"010B": ("manifold_pressure_kpa", 1, 1),
    b"010C": ("engine_speed_rpm", 2, 4),
    b"010D": ("vehicle_speed_kph", 1, 1),
    b"0133": ("barometric_pressure_kpa", 1, 1),
    b"0142": ("control_module_voltage_v", 2, 1000),
}
MEASUREMENT_COLUMNS = (
    *(
        f"{ecu}_{name}"
        for ecu in _ECUS.values()
        for name, _, _ in _STANDARD_MEASUREMENTS.values()
    ),
    *(
        f"{ecu}_coolant_sensor_{sensor}_c"
        for ecu in _ECUS.values()
        for sensor in (1, 2)
    ),
    *dict.fromkeys(name for fields in HONDA_FIELDS.values() for name in fields),
)


def pilot_measurements(
    command: bytes, reply: tuple[bytes, ...], *, standard_width: int | None = None,
) -> dict[str, int | float]:
    """Return usable values for known requests, leaving other data in the raw reply."""
    command = _compact_hex(command)
    width = standard_width or 8
    ecus = _ECUS if standard_width is None else {ENGINE_RESPONSE_IDS[width]: "ecm"}
    if command == b"0167":
        return {
            f"{ecus[address]}_coolant_sensor_{sensor}_c": value
            for address, temperatures in coolant_temperatures(reply, width)
            if address in ecus
            for sensor, value in enumerate(temperatures, 1)
            if value is not None
        }
    if command in _STANDARD_MEASUREMENTS:
        name, length, divisor = _STANDARD_MEASUREMENTS[command]
        prefix = b"\x41" + bytes.fromhex(command[2:].decode("ascii"))
        values = {}
        for line in reply:
            compact = _compact_hex(line)
            frame = _single_frame(compact, width) if compact else None
            if frame is None:
                continue
            address, payload = frame
            if address in ecus and len(payload) == length + 2 and payload.startswith(prefix):
                raw = int.from_bytes(payload[2:], "big")
                values[f"{ecus[address]}_{name}"] = raw if divisor == 1 else raw / divisor
        return values
    if standard_width is None and command in HONDA_FIELDS:
        data = _honda_data(command, reply)
        if data is not None:
            return {
                name: int.from_bytes(data[offset:offset + length], "big") + adjustment
                for name, (offset, length, adjustment) in HONDA_FIELDS[command].items()
            }
    return {}


def transmission_status_byte(reply: tuple[bytes, ...]) -> int | None:
    """Read data byte 23 from DID 2322 for comparison with known shifter positions."""
    data = _honda_data(b"222322", reply)
    return data[23] if data is not None else None


def _honda_data(command: bytes, reply: tuple[bytes, ...]) -> bytes | None:
    payload = _honda_payload(reply)
    prefix = b"\x62" + bytes.fromhex(command[2:].decode("ascii"))
    return payload[len(prefix):] if payload is not None and payload.startswith(prefix) else None


def _honda_payload(lines: tuple[bytes, ...]) -> bytes | None:
    frames = []
    for line in lines:
        compact = _compact_hex(line)
        if not compact or not compact.startswith(b"18DAF11E"):
            continue
        frame_hex = compact[8:]
        # When ATD1 is enabled the adapter inserts a DLC digit before each frame.
        if len(frame_hex) % 2:
            dlc = int(frame_hex[:1], 16)
            frame_hex = frame_hex[1:]
            if len(frame_hex) != 2 * dlc:
                return None
        if not 4 <= len(frame_hex) <= 16:
            return None
        frames.append(bytes.fromhex(frame_hex.decode("ascii")))

    # These two Honda identifiers return 39 application bytes in six classic CAN frames.
    if len(frames) != 6 or frames[0][:2] != b"\x10\x27":
        return None
    if any(len(frame) != 8 for frame in frames[:-1]) or len(frames[-1]) < 6:
        return None
    if any(frame[0] != 0x20 + index for index, frame in enumerate(frames[1:], 1)):
        return None
    return (frames[0][2:] + b"".join(frame[1:] for frame in frames[1:]))[:39]
