# Instrument harness drawings

**PROPOSED** · 2020 Civic LX 2.0 L CVT. The Rev. 0.6 power drawings cover the recorder supply, the hub supply and the three distribution branches. The Rev. 0.3 sensor drawings follow each populated port to its instrument. [Vehicle power overview](../power.svg)

| Drawing | Connections |
| --- | --- |
| [Pi recorder supply](generated/pi-power.svg) | Vehicle battery, ignition and chassis return to the Mini-Box. Regulated output to the proposed USB-C source and Pi 4B. |
| [HK4 hub supply](generated/hk4-hub-power.svg) | Vehicle battery, accessory sense and chassis return to the HK4. The captive plug mates with a proposed USB-C adapter. Its feed pair ends at PS1 5V-IN and RTN-IN. |
| [PS1 hub branches](generated/power.svg) | Begin at PS1 5V-IN and RTN-IN. Follow the three fused positives and common return through P01–P03 to each hub's PWR1 and carrier VIN/GND. |
| [Front hub](generated/HUB-F.svg) | W101–W104, W201, W202 |
| [Cabin hub](generated/HUB-C.svg) | W105, W106, W203 |
| [Rear hub](generated/HUB-R.svg) | W107–W110, W204 |

## Rebuild and open a drawing on Windows

From the CarDAQ repository root, run this in PowerShell. It uses the portable Graphviz in this checkout, rebuilds all six WireViz sheets, and opens the two converter drawings.

```powershell
$env:Path = "$PWD\build\graphviz\bin;$env:Path"
uv run --script hardware/wiring/render.py
Invoke-Item .\hardware\wiring\generated\pi-power.svg
Invoke-Item .\hardware\wiring\generated\hk4-hub-power.svg
```

The two supply sheets have hand-edited WireViz sources, [pi-power.yaml](pi-power.yaml) and [hk4-hub-power.yaml](hk4-hub-power.yaml). Edit these for factory leads, converter terminals and proposed mating interfaces. The [cable schedule](cable_schedule.csv) sets lengths and endpoints for the three sensor harnesses and the PS1 branches. The [family definitions](families.yaml) set shared pinouts, conductor colors and the proposed PS1 branch fuse rating. The branch drawing takes its two input functions from the HK4 sheet. Run the project script to combine these inputs. Running WireViz on the family file alone produces an empty drawing.

## Read a drawing

- **Accelerometers (CBL-A).** Numbering follows T568B on the passive 8P8C bench interface. Power and SPI use the orange (SCK), green (SDIO), blue (CS), and brown (3.3 V) pairs, each with its own return. Pins 1, 3, 5, and 7 join GND inside each end. SH is the hub shield landing, separate from the eight contacts. Its bond is TBD. Insulate the sensor end of the shield. The 8P8C interface carries custom SPI and sensor power; label both ends **non-Ethernet**. Connector viewing direction, exterior hardware, and breakout header numbering require the actual parts.
- **Microphones (CBL-M).** Pins 1/2 carry audio and its return. Pins 3/4 carry 3.3 V and its return. The two returns join GND at each end. SIG-RTN and PWR-RTN identify the conductors landing on microphone ground. Shown terminal names indicate functions. Core colors, shield bonds, housing and breakout pin numbers are TBD.
- **Power (CBL-P).** All three hubs share the HK4's 5 V, 2 A output. The separate USB-C adapter's positive lead lands on PS1 5V-IN and its return on RTN-IN. Each red branch wire leaves PS1 through its own fuse and each black wire connects to the common return. Measure the combined startup current and voltage at the hub ends with Wi-Fi active before choosing the final fuses. [HK4 manual, p. 2](../docs/HK4%20Hardwire%20Kit%20English%20Manual.pdf#page=2)

On the HK4 vehicle side, red takes constant battery power, yellow senses switched ACC and black connects to vehicle ground. Check shutdown and low-voltage cutoff with the actual hub load because the kit can stay powered after key-off. The Civic tap locations and ratings still require verification. [HK4 installation, p. 3](../docs/HK4%20Hardwire%20Kit%20English%20Manual.pdf#page=3)

The W- and P-series lengths in the cable schedule are routing allowances. The 3 m on the HK4 sheet is the manufacturer's length for the captive converter-to-plug lead. Record measured cut lengths and connector part numbers against each scheduled cable ID. Check contact numbering against the mating-face drawing and verify continuity on the disconnected cable before applying power.

## Edit and regenerate

1. Edit one row in the [cable schedule](cable_schedule.csv) to change an assignment, proposed length, or mounting location. Edit the shared [family definitions](families.yaml) to change contact functions, core colors, or the shield landing for every cable of a type.
2. Install Graphviz with `dot` on the command path. From the repository root run the commands below. The script pins WireViz and PyYAML in its own uv environment. The checked-in drawings were rendered with Graphviz 16.1.2, WireViz 0.4.1 and the Arial font. [Graphviz downloads](https://graphviz.org/download/) · [WireViz syntax](https://github.com/wireviz/WireViz/blob/v0.4.1/docs/syntax.md)

   ```sh
   dot -V
   uv run --script hardware/wiring/render.py
   ```

3. Inspect the SVGs in [generated](generated). For scheduled cable changes, also review the generated YAML, [connector schedule](generated/connector_schedule.csv) and [harness BOM](generated/wiring_bom.csv). These tables cover the scheduled harnesses. The individual factory leads and proposed source adapters appear on the two converter sheets.

The connector schedule lists the HK4 plug as an assembly and the two PS1 input functions against the adapter feed pair. Spare hub ports have an empty cable field. The wiring BOM includes the owned HK4, stock and interface locations for the scheduled harnesses. Edit `CBL-P.branch_fuse_a` in the family definitions to update the proposed rating on both the branch sheet and the fuse line in the BOM. Purchase allowances include service and routing margin.
