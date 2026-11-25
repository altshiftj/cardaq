"""Recover supplemental ECM observations from saved standard OBD replies."""

from dataclasses import dataclass

from ..obd_frames import _compact_hex, _single_frame


_ECM = b"18DAF110"
_PERCENT_SCALE = 100 / 255


@dataclass(frozen=True)
class _Channel:
    name: str
    label: str
    unit: str
    length: int
    description: str
    interpretation: str
    offset: int = 0
    width: int = 1
    scale: float = 1
    bias: float = 0
    support_mask: int = 0


_CHANNELS = {
    "0104": _Channel(
        "calculated_load_pct", "Calculated engine load", "%", 1,
        "The engine computer's estimate of how much of the load available at the current RPM is in use.",
        "At similar RPM, a higher percentage means the engine is working harder. "
        "Compare a launch with steady cruising to see how demand changes.",
        scale=_PERCENT_SCALE,
    ),
    "0106": _Channel(
        "short_term_fuel_trim_pct", "Short-term fuel trim, bank 1", "%", 1,
        "The immediate fuel adjustment for bank 1 while the engine computer uses exhaust-sensor feedback.",
        "Positive values add fuel and negative values remove it. Small swings around zero "
        "show the controller fine-tuning the mixture in both directions.",
        scale=100 / 128, bias=-100,
    ),
    "0107": _Channel(
        "long_term_fuel_trim_pct", "Long-term fuel trim, bank 1", "%", 1,
        "The learned adjustment to base fueling for bank 1 at the current operating condition.",
        "A persistent positive offset adds fuel and a negative one removes it. Compare warm idle "
        "with warm idle across drives, since a different load can use a different learned adjustment.",
        scale=100 / 128, bias=-100,
    ),
    "010E": _Channel(
        "ignition_timing_deg", "Ignition timing advance", "°", 1,
        "Cylinder 1 spark timing in crankshaft degrees relative to the top of the compression stroke.",
        "Positive values place the spark before the piston reaches the top, negative values after. "
        "Compare timing at similar RPM and load to see when the engine computer moves the spark earlier or later.",
        scale=0.5, bias=-64,
    ),
    "0111": _Channel(
        "throttle_pct", "Absolute throttle position", "%", 1,
        "The throttle plate position on the sensor's percentage scale.",
        "A higher reading means the plate is farther open. Compare it with accelerator pedal "
        "position to see how the electronic throttle responds to the driver's input.",
        scale=_PERCENT_SCALE,
    ),
    "012E": _Channel(
        "evap_purge_pct", "Commanded evaporative purge", "%", 1,
        "How much purge the engine computer requests to draw stored fuel vapor from the canister into the intake.",
        "Zero means no purge requested. A rising trace means a stronger request. "
        "The amount of vapor that actually reaches the engine requires a separate measurement.",
        scale=_PERCENT_SCALE,
    ),
    "013C": _Channel(
        "catalyst_temperature_c", "ECU-reported catalyst temperature", "°C", 2,
        "The engine computer's reported temperature for the bank 1, sensor 1 catalyst channel.",
        "Compare the time to reach the same temperature on each drive to see which catalyst warm-up was quicker. "
        "The value can come from an engine-computer model.",
        width=2, scale=0.1, bias=-40,
    ),
    "0149": _Channel(
        "accelerator_pedal_pct", "Accelerator pedal position D", "%", 1,
        "The position of the accelerator pedal on sensor channel D's percentage scale.",
        "A rise above the resting level shows the driver pressing the pedal. A return to that "
        "level marks a lift, even when the released pedal reads above zero.",
        scale=_PERCENT_SCALE,
    ),
    "0166": _Channel(
        "mass_airflow_g_s", "Mass airflow sensor A", "g/s", 5,
        "Grams of intake air passing mass airflow sensor A each second.",
        "At the same RPM, higher airflow means more air enters per engine revolution. "
        "Use the air-per-intake-event estimate to compare stretches at different RPM.",
        offset=1, width=2, scale=1 / 32, support_mask=1,
    ),
    "0168": _Channel(
        "intake_air_temperature_c", "Intake air temperature, bank 1 sensor 1", "°C", 7,
        "Air temperature at the first intake temperature sensor on bank 1.",
        "A rise while stopped followed by a drop once moving is consistent with heat building up "
        "around the intake and cooler air flowing through again.",
        offset=1, bias=-40, support_mask=1,
    ),
    "019D": _Channel(
        "engine_fuel_rate_g_s", "Engine fuel rate", "g/s", 4,
        "Grams of fuel the engine computer reports using each second.",
        "Higher readings use fuel faster. A stretch at zero while the engine is turning and the "
        "pedal is released can mark fuel cut during coasting.",
        width=2, scale=0.02,
    ),
    "01A6": _Channel(
        "odometer_km", "Odometer", "km", 4,
        "The vehicle's total accumulated distance as reported by the engine computer.",
        "Subtract the first reading from the last to check trip distance against integrated speed. "
        "The odometer can stay flat between updates while the car is moving.",
        width=4, scale=0.1,
    ),
}

STANDARD_CHANNELS = {
    f"ecm_{channel.name}": {
        "label": f"{channel.label} · ECM",
        "unit": channel.unit,
        "group": "Recorded signals",
        "description": channel.description,
        "interpretation": channel.interpretation,
        "request": request,
    }
    for request, channel in _CHANNELS.items()
}
STANDARD_CHANNELS["ecm_odometer_km"]["summary"] = "change"


def standard_observations(request: str, reply: str) -> dict[str, int | float]:
    """Decode selected Mode 01 readings from the Civic ECM's saved CAN frames."""
    command = "".join(request.split()).upper()
    channel = _CHANNELS.get(command)
    if channel is None:
        return {}

    frames = [
        compact
        for line in reply.split("|")
        if (compact := _compact_hex(line.encode())) is not None and compact.startswith(_ECM)
    ]
    expected_prefix = bytes.fromhex("41" + command[2:])
    if channel.length > 5:
        payload = _intake_air_payload(frames)
    else:
        payload = next(
            (
                frame[1]
                for compact in frames
                if (frame := _single_frame(compact, len(_ECM))) is not None
                and len(frame[1]) == channel.length + 2
                and frame[1].startswith(expected_prefix)
            ),
            None,
        )
    if payload is None or not payload.startswith(expected_prefix):
        return {}
    data = payload[2:]
    if channel.support_mask and not data[0] & channel.support_mask:
        return {}
    raw = int.from_bytes(data[channel.offset : channel.offset + channel.width], "big")
    return {f"ecm_{channel.name}": raw * channel.scale + channel.bias}


def _intake_air_payload(frames: list[bytes]) -> bytes | None:
    """PID 68 is the only selected response that uses two ISO-TP frames."""
    if len(frames) != 2:
        return None
    data = []
    for compact in frames:
        frame = compact[len(_ECM):]
        if len(frame) % 2:
            dlc = int(frame[:1], 16)
            frame = frame[1:]
            if dlc * 2 != len(frame):
                return None
        if not 8 <= len(frame) <= 16:
            return None
        data.append(bytes.fromhex(frame.decode("ascii")))

    first, second = data
    if len(first) != 8 or first[:2] != b"\x10\x09" or second[0] != 0x21:
        return None
    return first[2:] + second[1:4]
