# Verification checklist

- [x] Inspect the available captures and identify independent journeys and raw diagnostic fields.
- [x] Implement 14 conditioned indicators, the rolling comparison and the fixed eight-trip reference with five-trip drift screening.
- [x] Verify 26 outbound and 21 return cycle-counter polls per cylinder. Cylinder 2 reached three outbound and initially retained that value on return. The first return reset and the unchanged values on the other cylinders remain visible.
- [x] Test missing observations, duplicate captures, historical isolation, repeated departures and gradual drift. A 13-recording synthetic CLI test detected an induced warm-idle change.
- [x] Pass all 72 tests in the development environment and from the installed Python 3.11 wheel. Reproduce the real HTML byte for byte from the wheel.
- [x] Exercise all 14 metric selectors, counter transitions, group filters and mobile layout in offline Chromium. Verify the JSON export matches the embedded data. Document how to add future trips.
