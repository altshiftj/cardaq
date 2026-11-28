# Verification

- [x] Compared Mini-Box manual pp. 2–5 and HK4 manual pp. 2–3 with the previous package. Inspected the converter layout and jumper diagram.
- [x] Inspected raster previews of both Rev. 0.4 drawings. The overview contains two separate converter-to-load paths. The WireViz export contains the HK4, PS1, all three branch IDs and all three hub inputs. The harness BOM counts one owned HK4.
- [x] Regenerated the supply overview using Graphviz and all ten harness outputs using `uv run --script hardware/wiring/render.py`. Repeated outputs matched byte for byte. All six sensor SVG/YAML files also matched the previous Rev. 0.3 build. Checked links to all eight local references.
- [ ] On the bench, verify the converter voltage and both USB-C interfaces, load margin, hub behavior at key-off and Pi shutdown with the SSD attached.
