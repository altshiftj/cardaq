# Verification

- [x] Compared the Rev. 0.3 port assignments, cable schedule and electrical interfaces with the existing recording and contributor guides.
- [x] Checked all 30 carrier contact labels against the supplied USB-down pinout. Espressif's module datasheet v3.3, tables 2 and 5, confirms the input-only ADC1 channels and the module supply range.
- [x] Compared the 17 cable IDs, families, endpoints and proposed lengths and all 14 instrument locations and ports with sections 4 and 11 of the supplied design. Total proposed cable lengths are 59 ft of Cat6, 24 ft of shielded two-pair and 30 ft of duplex.
- [x] Checked all 44 front-hub sensor contacts in the generated connector schedule against an XML netlist exported by `kicad-cli sch export netlist --format kicadxml`. Each accelerometer cable has four individually numbered return conductors, one per twisted pair. All four share the hub ground net.
- [x] Checked the 32 components and 40 named nets, including both microphone filters, eight switched multiplexer paths, the 16 used or reserved carrier contacts, and the four separate shield landings. `kicad-cli sch erc --severity-all` reported zero errors and four warnings. Each warning identifies a shield landing whose final bond is TBD.
- [x] Rendered the A3 schematic with KiCad 10.0.8, opened it as a rasterized PDF page and inspected the header, labels, connectors and component values. Opened the harness and data-path artwork and verified the local links in the package.
- [x] Rebuilt the drawing package from the [documented commands](../../../hardware/README.md#regenerate-the-drawings). A clean copy of the wiring inputs gave byte-identical YAML, SVG and CSV outputs for all ten files. The Graphviz overview also matched, and a fresh KiCad PDF export had the same extracted text.
- [x] Ran the existing CarDAQ unit suite with `uv run --locked python -m unittest discover -s tests -q` (105 passed).
- [ ] Identify the sensor breakout variants and the carrier power circuitry, then record continuity, power, cable and timing measurements on the bench.
