# Standard OBD-II PID sweep report

The first physical check found two Mode 01 support bitmaps and two RPM replies, with the CAN headers hidden. The adapter reported ISO 15765-4 CAN, 29-bit, 500 kbps. A direct `0105` request returned `NO DATA`. [Serial bootstrap checklist](../0001-serial-bootstrap/checklist.md)

The new OBDwiz screenshots show two selectable ECUs, `ECM-EngineControl` with 80 supported PIDs and `TCM-TransmisCtrl` with 24. OBDwiz labels both coolant channels SAE `0x67`, and the charts show approximately 163.4 °F and 82.4 °F. These are reference values from the screenshots. The times, enabled OBDwiz features, and counting rules may differ from a standard Mode 01 sweep.

Mode 01 support bitmap requests describe the following 32 PIDs, with the last bit indicating whether that ECU supports the next bitmap. PID `67` carries two coolant temperatures and individual sensor support bits. [SAE J1979, sections 6 and 7 and table B83](https://www.autonerdz.com/yabbfiles/Attachments/1979v3.pdf)

OBDLink can expose CAN response IDs with `ATH1`. The current serial output must be examined to determine whether headers are already enabled. CAN identifiers, transport bytes, and ECU support bits are independent pieces of evidence. [OBDLink programming manual, sections 7 and 12](https://www.scantool.net/scantool/downloads/682/obdlink_frpm_f.pdf)

Windows exposed `COM5`, and an identification attempt returned access denied while OBDwiz was running. The physical sweep succeeded after OBDwiz disconnected. A follow-up `090A` read confirmed the names for both CAN IDs. [Complete PID inventory](pid-inventory.md)

## Physical validation and OBDwiz comparison

On 2026-11-23 Eastern time, `cardaq sweep` found two Mode 01 responders on the Civic. `18DAF110` advertised 44 data PIDs and `18DAF11E` advertised 14. The 14 PIDs were also advertised by `18DAF110`. `--sample` sent 44 data requests and received positive responses from every advertised ECU/PID pair. The definition of the OBDwiz counts of 80 and 24 remains open.

The supplied `CSVLog_20261123_215823.csv` contains 411 timestamped rows over 25.738 seconds and 75 logged fields. Its first 18 rows contain zeros in all 75 logged fields. The two coolant channels stay at the values below for all 391 rows with coolant readings. The CSV includes derived values and adapter metrics such as PID refresh rate, and the median row interval of 63.6 ms measures CSV row cadence.

| Signal | OBDwiz recording, populated rows | Later CarDAQ snapshot |
| --- | --- | --- |
| Coolant sensor 1 (`67`) | 172.4 °F (78 °C) | 179.6 °F (82 °C) from both CAN IDs |
| Coolant sensor 2 (`67`) | 120.2 °F (49 °C) | 176.0 °F (80 °C) from both CAN IDs |
| Barometric pressure (`33`) | 29.5301–29.8254 inHg | 101 kPa (29.83 inHg) from both CAN IDs |
| Engine speed (`0C`) | 747–762 rpm | 753 rpm from `18DAF110` and 751 rpm from `18DAF11E` |
| Time since engine start (`1F`) | 668–684 s | 948 s from `18DAF110` and 947 s from `18DAF11E` |

Both live coolant responses carried `41 67 03 7A 78`, with both sensor flags set. The engine runtime fields place the two captures several minutes apart. [OBDwiz SAE PID list](https://www.obdlink.com/obd-apps/obdwiz-app/) · [python-OBD command definitions and units](https://github.com/brendan-w/python-OBD/blob/master/docs/Command%20Tables.md)
