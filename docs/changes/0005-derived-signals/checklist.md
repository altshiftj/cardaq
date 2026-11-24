# Derived signal checklist

- [x] Confirm the existing CSVs contain the required readings and raw replies.
- [x] Compute five derived series and extract the transmission status byte.
- [x] Expose the new metrics in the viewer and regenerate both drives.
- [x] Pass all 21 Python tests with `python -m unittest discover -s tests -v`. Check chart controls in offline Chromium at desktop and mobile widths.
- [x] Verify the 861-reply status sequence in the home capture and the acceleration gap across the grocery stop.
- [ ] Record and verify the parked shifter sweep on the Civic.
