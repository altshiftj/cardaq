# Verification

- [x] Verify exclusive UTC capture names, recording and completion metadata, interruption, and preservation of partial raw data on failure. The recorder tests use a simulated adapter.
- [x] Check the default CLI paths, stable viewer identity, ordered input fingerprints, and compatibility with explicit paths.
- [x] Move 19 local files into the library layout. Update the two relative capture references in the health manifest. Verify SHA-256 on all other original files, including the demo.
- [x] Reproduce four moved viewer exports and both health reports byte for byte. Save the local migration inventory with file hashes, trim provenance, and report inputs.
- [x] Update the guides. Pass 92 Python tests and two browser tests locally and against an installed wheel on Windows with Python 3.11. Pass Ruff, `uv lock --check`, and `git diff --check`.
