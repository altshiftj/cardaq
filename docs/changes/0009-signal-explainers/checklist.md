# Signal explainer checklist

- [x] Inventory all 63 definitions, capture the baseline data hashes and identify which signals appear in each dashboard.
- [x] Verify definitions and interpretations for 25 capture columns, 12 supplemental ECM channels, 24 derived channels, the status byte and reply latency.
- [x] In offline Chromium, select every metric on both commute dashboards, the demo and a sparse fixture. Check counters, flags, state codes, singleton and missing samples, event focus and the distance axis. Inspect desktop and mobile layouts.
- [x] Run all 46 tests. Check the optional notes against recording fingerprints and input order, including invalid notes and safe embedding.
- [x] Compare both commute exports and the demo against their pre-change drive payload hashes. Verify the three original commute CSV hashes.
- [x] Embed a measured observation for each of the 62 available comparison signals. Keep the reusable notes file alongside the private captures. Independently check the highway sample counts and medians for engine RPM, pulley ratio and fuel rate.
