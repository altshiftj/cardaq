# Verification

- [x] Align local, editor and installed-wheel test commands. The test dependency group exports pytest and its locked dependencies separately from the wheel.
- [x] Verify reply classification and CAN frame handling with replay tests. The capture replay checks the CSV event, reply count and viewer latency for rejected and unrelated responses. The shifter replay covers frames with and without a length digit and rejects a mismatched length.
- [x] Verify health report behavior for identified and older recordings. The health and vehicle suites passed, including a conflict between two identically labeled vehicles and a history spanning a nickname change.
- [x] Run `uv lock --check`, the pre-commit hooks on the changed files, and `uv build`. The wheel lists pyserial as its only runtime dependency.
- [x] Install the wheel in fresh Windows environments for Python 3.11 and 3.15. On each version, `python -m pytest -q` passed 108 tests and 131 subtests. On Python 3.11, `python -m pytest -q tests/browser/offline_viewer.py` passed all five Chromium tests. Vehicle data came from fixtures and simulated serial exchanges.
