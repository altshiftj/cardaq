# Verification

- [x] A fixture change from 1 A to 0.5 A updated both the rendered PS1 branch sheet and the fuse line in the BOM. The two PS1 input functions and six branch contacts match the schedule.
- [x] Compared all eight bypass straps and all four chip selects with a fresh KiCad netlist. Checked the three-wire startup sequence against the ADXL345 register map and the dummy-load cutoff procedure against the Mini-Box timing table.
- [x] Rebuilt all 12 WireViz outputs and three Graphviz drawings byte-for-byte in a copy containing only shareable hardware files. Checked 75 local Markdown links, five drawing-to-drawing browser links and the fit of the rendered labels. Inspected the KiCad PDF and direct-bus drawing. Repository hooks passed for the hardware package and this change record.
- [x] Verified both original PDFs remain in place and the four empty exports retain their original hashes in the local build archive.
- [ ] Physical checkout remains open. Record shutdown timing, cranking behavior, hub current, sensor readback and sample continuity with the actual equipment.
