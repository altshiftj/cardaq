"""Generate two fictional trips on the same speed trace for the offline viewer."""

import argparse
import csv
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from itertools import pairwise
from pathlib import Path

from cardaq.pilot_measurements import MEASUREMENT_COLUMNS, pilot_measurements


# Seconds since recording start and road speed in km/h at each turn in the trace.
SPEED_PROFILE = (
    (0, 0), (15, 0), (30, 45), (46, 45), (61, 0), (74, 0),
    (99, 75), (148, 75), (160, 39), (172, 0), (180, 0),
)


def road_speeds() -> Iterator[int]:
    for (start, start_speed), (end, end_speed) in pairwise(SPEED_PROFILE):
        for second in range(start, end):
            fraction = (second - start) / (end - start)
            yield round(start_speed + fraction * (end_speed - start_speed))
    yield SPEED_PROFILE[-1][1]


def generate_trip(path: Path, initial_coolant: int, rpm_per_kph: int) -> None:
    started = datetime(2025, 1, 1, 8, tzinfo=timezone.utc)
    fields = ("timestamp", "elapsed_s", "request_elapsed_s", "event", "request", "reply", "detail")
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=(*fields, *MEASUREMENT_COLUMNS))
        writer.writeheader()
        previous_speed = 0
        for second, speed in enumerate(road_speeds()):
            running = 3 <= second < 178
            change = speed - previous_speed
            previous_speed = speed
            coasting = change < 0 and speed >= 10
            rpm = 720 + speed * rpm_per_kph + 150 * max(change, 0) if running else 0
            coolant = min(84, initial_coolant + max(second - 3, 0) // 5)
            pedal_pct = 15 + (10 if speed and not coasting else 0) + 4 * max(change, 0)
            fuel_g_s = 0 if coasting or not running else 0.15 + (rpm - 720) / 2200

            # Encode single-frame ECM replies so the demo exercises the real CSV decoders.
            readings = (
                (0x0C, (rpm * 4).to_bytes(2, "big")),
                (0x0D, bytes([speed])),
                (0x67, bytes([1, coolant + 40, 0])),
                (0x49, bytes([round(pedal_pct * 255 / 100)])),
                (0x9D, round(fuel_g_s / 0.02).to_bytes(2, "big") + bytes(2)),
            )
            for index, (pid, data) in enumerate(readings):
                elapsed = second + (index + 1) * 0.05
                request = f"01{pid:02X}"
                payload = bytes([0x41, pid]) + data
                reply = f"18DAF110 {len(payload):02X} {payload.hex(' ').upper()}"
                writer.writerow({
                    "timestamp": (started + timedelta(seconds=elapsed)).isoformat(timespec="milliseconds"),
                    "elapsed_s": f"{elapsed:.3f}", "request_elapsed_s": f"{elapsed - 0.02:.3f}",
                    "event": "reply", "request": request, "reply": reply,
                    **pilot_measurements(request.encode("ascii"), (reply.encode("ascii"),)),
                })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("captures/demo"),
        help="directory for the two new CSVs (default: captures/demo)",
    )
    directory = parser.parse_args().output_dir
    directory.mkdir(parents=True, exist_ok=True)
    trips = [(directory / "synthetic-cool.csv", 36, 17), (directory / "synthetic-warm.csv", 56, 25)]
    for path, _, _ in trips:
        if path.exists():
            parser.exit(1, f"{path} already exists. View the existing demo or choose a fresh --output-dir.\n")
    for path, initial_coolant, rpm_per_kph in trips:
        generate_trip(path, initial_coolant, rpm_per_kph)
        print(path)


if __name__ == "__main__":
    main()
