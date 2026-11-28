# Verification

- [x] Identify the two factory interfaces and the standard hub input from the supplied references.
- [x] Inspected the rendered Mini-Box, HK4 and PS1 branch sheets. Compared the eight Mini-Fit Jr positions with figure 1.0, the HK4 leads with its manual, and PWR1 polarity and U1 contacts L15/L14/R14 with a fresh KiCad XML netlist.
- [x] Ran `uv run --script hardware/wiring/render.py` twice. All 12 generated files matched byte for byte, and the six sensor drawing files retained their earlier hashes. A fresh `dot -Tsvg hardware/power.dot` matched the overview.
- [x] Followed the three SVG links from the overview and the HK4-to-PS1 link in Chromium. Checked local documentation links, SVG text bounds and the repository hooks for the changed files.
- [ ] Bench work remains open. Identify the mating hardware and vehicle taps, load-test both supplies and verify key-off behavior with the recorder and hubs.
