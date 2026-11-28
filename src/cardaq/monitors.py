"""Read ECM fuel-system status, MIL status and per-cylinder monitor snapshots."""

from .obd_frames import responder_frames, single_frame_payload


_ECM = b"18DAF110"
_CYLINDERS = {f"06{mid:02X}": mid for mid in range(0xA2, 0xA6)}
_COUNT_TESTS = {0x0B: "weighted", 0x0C: "cycle"}


def _multiframe(frames: list[bytes]) -> bytes | None:
    """Assemble one classic CAN ISO-TP response."""
    payload = bytearray()
    length = 0
    for index, frame in enumerate(frames):
        if index == 0:
            if len(frame) != 8 or frame[0] >> 4 != 1:
                return None
            length = ((frame[0] & 0x0F) << 8) | frame[1]
            remaining = length - 6
            if length <= 7 or len(frames) - 1 != (remaining + 6) // 7:
                return None
            payload.extend(frame[2:])
        else:
            needed = min(7, length - len(payload))
            if frame[0] != (0x20 | (index % 16)) or len(frame) - 1 < needed:
                return None
            payload.extend(frame[1 : needed + 1])
    return bytes(payload) if len(payload) == length else None


def diagnostic_observations(request: str, reply: str) -> dict[str, int]:
    """Decode selected ECM requests from a single saved query and its reply."""
    command = "".join(request.split()).upper()
    mid = _CYLINDERS.get(command)
    if mid is None and command not in ("0101", "0103"):
        return {}
    frames = responder_frames(reply.encode().split(b"|"), _ECM)
    if not frames:
        return {}
    if mid is None:
        if len(frames) != 1 or (payload := single_frame_payload(frames[0])) is None:
            return {}
        if command == "0103" and len(payload) == 4 and payload[:2] == b"\x41\x03":
            return {"ecm_fuel_system_1_status": payload[2]}
        if command == "0101" and len(payload) == 6 and payload[:2] == b"\x41\x01":
            return {"ecm_mil_on": payload[2] >> 7, "ecm_confirmed_dtc_count": payload[2] & 0x7F}
        return {}

    payload = _multiframe(frames)
    # After the service byte, each nine-byte record holds MID, TID, UASID,
    # test value, lower limit and upper limit. Only UASID 24 is a unit count.
    if not payload or payload[0] != 0x46 or (len(payload) - 1) % 9:
        return {}
    decoded = {}
    cylinder = mid - 0xA1
    for index in range(1, len(payload), 9):
        record_mid, tid, scaling = payload[index : index + 3]
        if record_mid != mid:
            return {}
        if tid in _COUNT_TESTS and scaling == 0x24:
            key = f"ecm_cyl_{cylinder}_misfires_{_COUNT_TESTS[tid]}"
            if key in decoded:
                return {}
            decoded[key] = int.from_bytes(payload[index + 3 : index + 5], "big")
    return decoded
