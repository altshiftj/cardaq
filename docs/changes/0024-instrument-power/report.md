# Power supplies for the Civic instruments

The owner assigned the Mini-Box PWR-DCDC-USB to the Raspberry Pi 4B and the VIOFO HK4 to the three ESP32 hubs. Rev. 0.3 described a generic Pi supply and a 3 A target for the hub supply. The devices are now identified. The connections from their factory outputs to the Pi USB-C input and the PS1 distribution block still require hardware selection.

The [Mini-Box guide](../../../hardware/docs/PWR-DCDC-USB-manual.pdf) shows separate configuration and load connectors, a factory 12 V output and a selectable 5 V setting. Its voltage-jumper numbers disagree between the text and figure on page 3. The [HK4 manual](../../../hardware/docs/HK4%20Hardwire%20Kit%20English%20Manual.pdf) specifies one 5 V, 2 A output and identifies separate battery, accessory-sense and ground leads. No vehicle test or board-level measurement accompanied the documents.

The drawing changes pass the repository hooks. The supplied `ACC Hardwire Kit Installation.pdf` (4058 KiB) and `adxl345.pdf` (1453 KiB) exceed the existing 1 MiB Git hook limit. Both are available locally. The general installation guide contributes no Civic-specific wiring, and the hardware overview includes the manufacturer's ADXL345 link for readers without the local copy.
