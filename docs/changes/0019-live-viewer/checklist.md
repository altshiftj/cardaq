# Verification

- [x] Tested recursive discovery, cache reuse, edits, removal and invalid-to-valid CSV recovery with temporary files.
- [x] Started with an empty fixture folder in Edge, added a dated subfolder and three recordings, and verified the automatic refresh preserved the chosen drives, time window and RPM overlay. Opened the real four-drive library and verified eight speed/RPM readouts.
- [x] Ran `python -m unittest discover -s tests -q` (93 tests), the Chromium offline viewer suite (3 tests), and the repository hooks. Regenerated the saved commute and demo viewers.
