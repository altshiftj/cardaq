# Project housekeeping checklist

- [x] Review the existing repository, run the 41-test baseline, confirm the maintainer's MIT choice, and trace the Honda mappings to their licensed source.
- [x] Generate the two fictional trips in a fresh environment. Both cover 1.924 km. Check the 18-metric viewer in offline Chromium and capture the RPM plot for the README.
- [x] Verify regression coverage for filesystem errors, reset/disconnect handling, and immutable reply lines.
- [x] Resolve 65 local links and section anchors across 31 project documents. Verify the editor selects unittest discovery with the same test directory and pattern.
- [x] Build the sdist and wheel. Check the combined SPDX expression and all three license/notice files in both archives, the viewer assets in the wheel, and the config, demo, lockfile, docs and screenshot in the sdist.
- [x] Install the wheel into clean environments on Windows (Python 3.11.15 and 3.15.2) and Debian under WSL (Python 3.11.2). Run both CLI entry points, all 44 tests, and the two-drive quickstart on each. Hosted Actions runs on a push or pull request.
- [x] Re-export both commute dashboards to temporary files. All embedded series, events, thermal milestones, dwell and summary values match their earlier exports exactly. Check all 62 metric definitions, the three original CSV hashes, and their measurement column order.
