# Contributing to CarDAQ

You can work on the CLI, decoders, and dashboard using simulated serial replies and small CSVs. The hardware verification notes record which adapter and vehicle have been tried. [Hardware notes](docs/ROADMAP.md#serial-foundation)

## Set up and check a change

Run these commands in the repository root with uv and Python 3.11 or later.

```sh
uv sync --locked
uv run --locked pre-commit install
uv run --locked cardaq --version
uv run --locked python -m unittest discover -s tests -v
uv build
```

Install the Git hook once per clone. On each commit it checks the staged files. Ruff fixes safe Python lint issues and sorts imports. Other hooks trim whitespace, check file endings, parse JSON/TOML/YAML, and catch conflict markers, case-colliding filenames, recognizable private keys, and files larger than 1 MiB. Changes to the dependency files also run `uv lock --check`.

If a hook edits a file, review the diff, stage the intended changes, and retry the commit. If you changed dependencies, regenerate and stage `uv.lock` along with `pyproject.toml`. To run the same checks as CI on every tracked file, use `uv run --locked pre-commit run --all-files --show-diff-on-failure`. The first run downloads the pinned hooks. The full test suite and package build run separately in CI.

To run one test module, use a discovery pattern such as `uv run --locked python -m unittest discover -s tests -p test_viewer_trip.py -v`. VS Code's checked-in settings use the same unittest suite. For viewer changes, open the offline demo and inspect the changed metric or control. The HTML, CSS, and JavaScript ship in the Python wheel. [Demo commands](README.md#try-the-viewer)

CI also opens an exported HTML file in headless Chromium. Run those browser tests locally with the browser dependency group.

```sh
uv run --locked --group browser python -m playwright install --only-shell chromium
uv run --locked --group browser python -m unittest discover -s tests/browser -p offline_viewer.py -v
```

## Where changes belong

| If you are changing… | Start here |
| --- | --- |
| CLI arguments, exit codes, or serial settings | [cli.py](src/cardaq/cli.py) and [config.py](src/cardaq/config.py) |
| Serial commands, framing, or standard PID discovery | [adapter.py](src/cardaq/adapter.py), [obd_frames.py](src/cardaq/obd_frames.py), and [obd.py](src/cardaq/obd.py) |
| Polling, reconnects, or CSV rows | [capture.py](src/cardaq/capture.py) |
| Measurements written during recording | [pilot_measurements.py](src/cardaq/pilot_measurements.py) and the attributed [Honda field tables](src/cardaq/honda_fields.py) |
| A standard PID already present in historical raw replies | [standard.py](src/cardaq/viewer/standard.py) |
| A calculated signal, trip total, event, or warm-up milestone | [derived.py](src/cardaq/viewer/derived.py), [trip.py](src/cardaq/viewer/trip.py), [events.py](src/cardaq/viewer/events.py), and [thermal.py](src/cardaq/viewer/thermal.py) |
| Metric selection, plots, or the offline export | [viewer package](src/cardaq/viewer) and [viewer tests](tests/test_viewer.py) |

For a decoder change, include a small input reply, the responder and request, the expected value and unit, and the source of the mapping. Distinguish independent reference measurements from inferences based on one vehicle. For a derived signal, document how it handles sparse samples and gaps and cover the boundary that matters in its test. Keep existing captures readable when adding CSV fields.

Each selectable metric has a short definition and an interpretation. Describe one pattern a reader can recognize and what it implies. The capture-column guides live in `viewer/recorded.py`. Supplemental and derived signals carry their guides in their metric definitions. Keep findings from a specific drive in a recording-bound notes file. [Signal notes](docs/RECORDINGS.md#include-observations-about-specific-recordings)

## Issues and pull requests

In a bug report, include the CarDAQ version, OS, command, expected result, and observed output. A minimal synthetic CSV is enough for many viewer issues. For a hardware report, add the vehicle year, engine and transmission, adapter model and firmware, and which step first failed. Review raw data and generated HTML before attaching either. [Recording format](docs/RECORDINGS.md#read-the-csv) · [Issue tracker](https://github.com/altshiftj/cardaq/issues)

For a substantial change, use the next numbered folder under `docs/changes/` for a short report, plan, and verification checklist. Record the commands you ran and which results came from fixtures or a physical vehicle. Small fixes can explain their verification in the pull request. Attribute third-party signal definitions and include their source and terms. [Example change record](docs/changes/0005-derived-signals) · [Third-party notices](THIRD_PARTY_NOTICES.md)
