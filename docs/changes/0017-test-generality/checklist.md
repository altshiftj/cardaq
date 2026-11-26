# Verification

- [x] Check derived values across reordered CSVs, compact and spaced replies, irregular or shifted sampling, and both sides of a telemetry gap limit.
- [x] Check varied health inputs, CVT load matching, raw diagnostic values in the JSON report, and earlier results after appending a trip.
- [x] Verify serial routing, cylinder poll cadence, numeric CSV values, periodic sync and replay into the viewer with a scripted adapter.
- [x] Open a CLI-generated report in headless Chromium. Verify drive selection, event focus, keyboard access to misfire intervals, and cumulative counts across a counter reset.
- [x] Build with `uv build`. From the installed wheel on Windows and Python 3.11, pass 80 tests with `python -m unittest discover -s tests -q` and two browser tests with `python -m unittest discover -s tests/browser -p offline_viewer.py -v`. These runs used a simulated adapter and synthetic recordings.
- [x] Confirm representative probes fail as expected, including missing dashboard JavaScript, stale event focus, incorrect CAN routing, omitted cylinder polling, fixed-interval smoothing, swapped CVT rates, and mean substituted for median.
- [x] Pass `uv lock --check`, `uvx ruff@0.17.6 check tests` and `git diff --check`.
