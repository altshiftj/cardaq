# cardaq

`cardaq` is a Python vehicle data acquisition and diagnostics project for a 2020 Honda Civic LX sedan with a 2.0 L engine and CVT. It starts on Windows and targets Linux on a Raspberry Pi for later deployment.

The initial CLI lists operating system serial ports and reads an OBDLink adapter's hardware and firmware IDs with the documented `STDI` and `STI` commands. Adapter identification has been verified on Windows with a USB OBDLink EX. [OBDLink programming manual](https://www.scantool.net/scantool/downloads/682/obdlink_frpm_f.pdf)

## Install

Install uv, then run the following from the repository root on Windows or Linux. uv creates `.venv` with a compatible Python interpreter and installs CarDAQ using `uv.lock`. The project requires Python 3.11 or later. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

```text
uv sync --locked
```

## Use the CLI

```text
uv run --locked cardaq ports
uv run --locked cardaq identify --port COM5
uv run --locked cardaq identify --port /dev/ttyUSB0 --baudrate 115200 --timeout 2
uv run --locked cardaq sweep --port COM5
uv run --locked cardaq sweep --port COM5 --sample
uv run --locked cardaq record --port COM5 --duration 2700 --output captures/civic_pilot.csv
```

Choose the adapter's port from the list and close OBDwiz before identifying it. The default baud rate is 115200, the documented default for USB OBDLink adapters. Serial access depends on the adapter model and how it connects. An OBDLink CX uses Bluetooth Low Energy and requires a BLE transport when it has no OS serial port. [OBDLink programming manual](https://www.scantool.net/scantool/downloads/682/obdlink_frpm_f.pdf) · [OBDLink CX developer notes](https://support.obdlink.com/support/solutions/articles/43000746707-obdlink-cx-adapter-notes)

`sweep` lists the standard Mode 01 data PIDs advertised by each CAN response ID. Disconnect OBDwiz from the adapter before running it. With `--sample`, the sweep sends one read request for each distinct advertised PID, prints the raw replies, and decodes supported coolant sensors under PID `67`. [PID sweep checklist](docs/changes/0002-pid-sweep/checklist.md)

`record` streams the Civic's raw diagnostic replies and selected decoded values to a new CSV. It includes the known standard live data and two Honda CVT requests. [Civic pilot runbook](docs/changes/0003-civic-pilot/plan.md)

## View recorded drives

```text
uv run --locked cardaq view captures/civic_20261124_0806_pilot.csv captures/civic_drive_home_261124.csv --label "To work" --label "Home" --output captures/drive-viewer.html
```

Open `captures/drive-viewer.html` in a browser. Choose a metric and time window, or use the overview charts to jump to speed, RPM, coolant temperature, and the pulley ratio estimate. The **Derived** group includes the ratio, RPM differences, estimated acceleration, and the difference between candidate CVT fluid and engine coolant temperatures. Hover over the large graph or focus it and use the arrow keys to inspect readings. Each drive uses elapsed time from the start of its recording. The HTML works offline.

Pass one CSV or several CSVs to view other drives. Without labels, the viewer uses the filenames. Use **Shifter verification** to inspect the raw transmission byte against independently noted selector positions. [Parked shifter check](docs/changes/0005-derived-signals/plan.md#parked-shifter-check)

## Configure the adapter

For repeatable runs, copy `cardaq.example.toml` to `cardaq.toml` and set `port` under `[serial]`. Pass the file with `uv run --locked cardaq identify --config cardaq.toml`. The CLI loads configuration files when explicitly supplied and uses command-line values when both are set. [Example configuration](cardaq.example.toml)

## Architecture

The package lives in `src/cardaq`. The CLI handles input and output, `config.py` loads serial settings, and `adapter.py` handles discovery and adapter communication through pySerial. [Roadmap](docs/ROADMAP.md)

## Development workflow

Run the adapter tests with `uv run --locked python -m unittest discover -s tests -v`.

For each substantial change, use the next numbered folder under `docs/changes/` with a `report.md`, `plan.md`, and live `checklist.md`. Record verification commands and results in the checklist. Close physical checks when they have been reproduced on the device. [Report](docs/changes/0001-serial-bootstrap/report.md) · [Plan](docs/changes/0001-serial-bootstrap/plan.md) · [Checklist](docs/changes/0001-serial-bootstrap/checklist.md)
