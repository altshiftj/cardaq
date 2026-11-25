# CarDAQ

CarDAQ records OBD-II data to CSV and turns one or more recordings into an interactive HTML dashboard. Compare two drives at the same road speed, see how long the coolant took to warm up, or select a stop to inspect the samples around it. The viewer runs locally in a browser.

The recorder was developed on a **2020 Honda Civic LX sedan, 2.0 L with CVT**, using a **USB OBDLink EX on Windows**. It reads standard engine data and two Honda transmission identifiers. The viewer and test suite run without a vehicle. [Hardware verification](docs/changes/0002-pid-sweep/report.md#physical-validation-and-obdwiz-comparison)

## Try the viewer

From the repository root, use uv with Python 3.11 or later. The generator creates two fictional three-minute trips with identical road speeds, different starting coolant temperatures, and different engine RPM. [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

```sh
uv sync --locked
uv run --locked python examples/generate_demo.py
uv run --locked cardaq view captures/demo/synthetic-cool.csv captures/demo/synthetic-warm.csv --label "Cool start" --label "Warm start" --output captures/demo/comparison.html
```

Open `captures/demo/comparison.html` in your browser. Select **Engine speed · ECM** and switch the horizontal axis to **Observed distance**. Both trips cover 1.92 km, but the warm-start example turns about 920 more engine revolutions. In the **Trip notebook**, select a launch to zoom in on the readings around it.

![Engine speed over time for the two synthetic drives, with the warm-start trace above the cool-start trace while moving.](docs/images/signal-explorer.png)

To compare your own drives, pass their CSV paths to `cardaq view`. Supply one `--label` per file or let the viewer use the filenames. Each HTML export embeds the selected drives and works offline. [Capture format and viewer guide](docs/RECORDINGS.md)

## Record a drive

Connect the adapter, close other applications using it, and find its serial port. Replace `COM5` below with the listed device. The recording command uses the Civic-specific polling profile.

```sh
uv run --locked cardaq ports
uv run --locked cardaq identify --port COM5
uv run --locked cardaq sweep --port COM5
uv run --locked cardaq record --port COM5 --duration 2700 --output captures/drive.csv
uv run --locked cardaq view captures/drive.csv --output captures/drive.html
```

Start the recorder while parked and wait for its `Ready` message. Use a fresh CSV filename for each recording. Turning the ignition off can leave the process retrying until the duration expires. Once parked, press Ctrl+C to finish early. The recording guide covers the stop file, serial settings, supported signals, and missing data. [Recording guide](docs/RECORDINGS.md) · [Example serial configuration](cardaq.example.toml)

## Track one vehicle over time

`cardaq health` follows cylinder misfire counters, closed-loop fuel trims, warm idle RPM and coolant, and candidate CVT slip and ratio movement under comparable cruise conditions. Add each independent drive to a local TOML manifest. Give it a comparison group such as outbound in Drive, and record relevant changes in mode or maintenance.

```sh
uv run --locked cardaq health captures/health-history.toml --output captures/health-history.html
```

The offline report shows observed counts from the first trip and builds per-trip references as comparable drives accumulate. A JSON export is also available. [Manifest example and interpretation guide](docs/HEALTH_HISTORY.md)

## Contribute

The contributor guide covers installing the Git hooks, running the offline tests, and tracing a raw reply to a plotted signal. It also describes the evidence that helps verify a new mapping. [Contributing](CONTRIBUTING.md) · [Development roadmap](docs/ROADMAP.md) · [Derived signal roadmap](docs/DERIVED_SIGNALS_ROADMAP.md)

CarDAQ's original code, documentation, and examples use the MIT license. The Honda field tables adapted from OBDb carry CC BY-SA 4.0. [License](LICENSE) · [Third-party notices](THIRD_PARTY_NOTICES.md)
