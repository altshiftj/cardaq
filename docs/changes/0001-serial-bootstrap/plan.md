# Serial bootstrap plan

## Success criteria

- `uv sync --locked` can install CarDAQ in a fresh Python 3.11 or later project environment using the repository's `uv.lock`, with pySerial as its sole runtime dependency.
- `cardaq ports` lists host serial endpoints and reports an empty result clearly without opening ports.
- `cardaq identify` opens a port selected through CLI flags or an explicitly loaded TOML file. It reports hardware and firmware identification after two documented adapter commands.
- The CLI reports configuration and serial failures with actionable messages and a nonzero exit status. The serial connection closes after success or failure.
- The README describes setup, the module layout and both commands. The roadmap tracks the remaining acquisition and analysis work.

## Approach

1. Use a `src/cardaq` package with an `argparse` CLI and separate configuration and adapter modules. Use standard-library TOML parsing and record the runtime dependency in `uv.lock`.
2. Require a port for identification. Let CLI settings override `[serial]` values in an explicitly selected TOML file. Use 115200 baud as the documented USB starting point and a two-second command timeout.
3. Send `STDI` and `STI` to the chosen endpoint and validate their prompt-terminated replies. Handle command echo and CR or CRLF without changing adapter settings. Keep an explicit command set containing only these adapter-local reads.
4. Walk through the locked uv setup in the README and smoke-test both CLI entry points with `uv run --locked`. Exercise the read-only wire sequence and failure paths with scripted serial I/O. Record the Windows port enumeration result and keep the physical adapter check open until the correct endpoint is known.

## Scope

This change covers packaging, configuration, adapter transport, and documentation. Vehicle communication, standard PID discovery and querying, polling, CSV, direct BLE, and analysis are subsequent roadmap items. The next vehicle-facing change starts with a documented read-only standard OBD-II request.
