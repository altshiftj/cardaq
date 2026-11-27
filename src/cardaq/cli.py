"""Command-line entry point for CarDAQ."""

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .adapter import AdapterError, available_ports, identify
from .capture import record
from .config import DEFAULT_BAUDRATE, DEFAULT_TIMEOUT, serial_settings
from .obd import SweepResult, sweep
from .viewer import write_managed_viewer, write_viewer


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cardaq", description="Vehicle data acquisition tools.")
    try:
        release = version("cardaq")
    except PackageNotFoundError:
        release = "unknown (uninstalled source tree)"
    parser.add_argument("--version", action="version", version=f"%(prog)s {release}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ports", help="list serial ports without opening them")
    identify_parser = commands.add_parser("identify", help="read OBDLink hardware and firmware IDs")
    sweep_parser = commands.add_parser("sweep", help="discover advertised standard OBD-II PIDs by ECU")
    sweep_parser.add_argument(
        "--sample", action="store_true", help="read each distinct advertised data PID once"
    )
    record_parser = commands.add_parser("record", help="record the Civic's live data to a new CSV")
    record_parser.add_argument(
        "--output", type=Path, help="new CSV path (default: automatically named under captures/recordings)"
    )
    record_parser.add_argument("--duration", type=float, default=2700, help="maximum capture seconds (default 2700)")
    record_parser.add_argument("--note", default="", help="record a note with the capture start")
    view_parser = commands.add_parser("view", help="graph one or more CarDAQ recording CSVs")
    view_parser.add_argument("captures", type=Path, nargs="+", metavar="CSV")
    view_parser.add_argument(
        "--output", type=Path, help="HTML viewer path (default: automatically named under captures/views)"
    )
    view_parser.add_argument("--label", action="append", help="drive name (repeat once per CSV)")
    view_parser.add_argument("--signal-notes", type=Path, help="include per-signal notes for these recordings from JSON")
    serve_parser = commands.add_parser("serve", help="watch a recordings folder in a local drive viewer")
    serve_parser.add_argument("folder", nargs="?", type=Path, default=Path("captures/recordings"))
    serve_parser.add_argument("--port", type=int, default=8765, help="local HTTP port (default 8765)")
    health_parser = commands.add_parser("health", help="track comparable engine and CVT observations across trips")
    health_parser.add_argument("manifest", type=Path, help="TOML file listing one vehicle's independent trips")
    health_parser.add_argument(
        "--output", type=Path, help="offline .html or .json path (default: HTML beside the manifest)"
    )
    for serial_parser in (identify_parser, sweep_parser, record_parser):
        serial_parser.add_argument("--config", type=Path, help="load serial settings from a TOML file")
        serial_parser.add_argument("--port", help="serial device, such as COM5 or /dev/ttyUSB0")
        serial_parser.add_argument(
            "--baudrate", type=int, help=f"serial baud rate (default {DEFAULT_BAUDRATE})"
        )
        serial_parser.add_argument(
            "--timeout", type=float, help=f"serial timeout in seconds (default {DEFAULT_TIMEOUT})"
        )
    args = parser.parse_args(argv)

    try:
        if args.command == "ports":
            ports = available_ports()
            if not ports:
                print("No serial ports found.")
            for device, description in ports:
                print(f"{device}\t{description}" if description and description != "n/a" else device)
        elif args.command == "serve":
            from .viewer.live import serve

            serve(args.folder, args.port)
        elif args.command == "view":
            if args.output is None:
                output = write_managed_viewer(args.captures, labels=args.label, signal_notes=args.signal_notes)
            else:
                output = args.output
                write_viewer(args.captures, output, labels=args.label, signal_notes=args.signal_notes)
            print(f"Open {output.resolve()} in a browser.")
        elif args.command == "health":
            from .health import write_health

            output = args.output or args.manifest.with_suffix(".html")
            write_health(args.manifest, output)
            print(f"Saved powertrain history to {output.resolve()}")
        else:
            settings = serial_settings(
                args.config, port=args.port, baudrate=args.baudrate, timeout=args.timeout
            )
            if args.command == "identify":
                identity = identify(settings)
                print(f"Port {settings.port} at {settings.baudrate} baud")
                print(f"Hardware: {identity.hardware}")
                print(f"Firmware: {identity.firmware}")
            elif args.command == "sweep":
                _print_sweep(sweep(settings, sample=args.sample))
            else:
                result = record(
                    settings, args.output, args.duration, note=args.note,
                    notify=lambda message: print(message, flush=True),
                )
                print(f"Saved {result.replies} replies to {result.path} ({result.stop_reason}).", flush=True)
                if result.stop_reason == "interrupted":
                    return 130
                if result.replies == 0:
                    return 1
    except (AdapterError, OSError, ValueError) as error:
        print(f"cardaq: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("cardaq: interrupted", file=sys.stderr)
        return 130
    return 0


def _print_sweep(result: SweepResult) -> None:
    for ecu in result.ecus:
        print(f"CAN {ecu.address} | {len(ecu.pids)} advertised data PIDs")
        if ecu.pids:
            print("  " + " ".join(f"{pid:02X}" for pid in ecu.pids))
    for sample in result.samples:
        print(f"PID {sample.pid:02X}")
        for line in sample.lines or ("Empty reply",):
            print(f"  {line}")
        for address, temperatures in sample.coolant:
            for sensor, celsius in enumerate(temperatures, start=1):
                if celsius is not None:
                    fahrenheit = celsius * 9 / 5 + 32
                    print(f"  CAN {address} coolant {sensor} = {celsius} C ({fahrenheit:.1f} F)")
