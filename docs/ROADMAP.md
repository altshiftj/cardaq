# Development roadmap

Each milestone should be testable with recorded or simulated data where practical and verified against the Civic when it changes the hardware behavior.

## Serial foundation

- Implemented serial port enumeration through pySerial, explicit adapter selection, and OBDLink hardware and firmware identification.
- Verified on Windows over USB with an OBDLink EX r2.7.1, firmware `STN2232 v5.10.3`, on `COM5` at `115200` baud. [Physical verification](changes/0001-serial-bootstrap/checklist.md)

## Standard OBD-II data

- Evaluate python-OBD against the confirmed adapter transport. Keep adapter identification available independently through pySerial.
- A one-off read-only probe confirmed the Civic responds over ISO 15765-4 CAN (29-bit, 500 kbps). It returned Mode 01 support bitmaps and live engine RPM. Standard coolant PID `05` returned `NO DATA` on this connection. [Probe results](changes/0001-serial-bootstrap/checklist.md)
- `sweep` and `sweep --sample` verified on the Civic. CAN IDs `18DAF110` and `18DAF11E` advertised 44 and 14 standard Mode 01 data PIDs and both returned coolant sensor readings under `0x67`. [Live sweep and OBDwiz comparison](changes/0002-pid-sweep/report.md#physical-validation-and-obdwiz-comparison)
- Standard `090A` confirmed the engine and transmission ECU names. The inventory also records their advertised freeze-frame, monitor, and vehicle information identifiers. [Complete PID inventory](changes/0002-pid-sweep/pid-inventory.md)
- Add focused CLI queries for individual signals. Verify which parameters contribute to the counts shown by OBDwiz.
- Start a machine-readable signal registry with identifiers, units, decoding rules, source references, and verification status. Track protocol, subsystem, ECU address, expected range, and sampling metadata as those fields become available.

## Continuous acquisition

- Run configurable headless sessions with per-signal polling intervals. Measure command latency and achieved polling frequency separately from the requested rates.
- Write original observations to CSV with a session ID, signal ID, source, UTC and monotonic timestamps, value, unit, raw response where available, and communication status. Define timeout and disconnect behavior and verify that completed observations survive interruptions.
- Add live visualization and session comparison from recorded data. Keep transformations such as resampling, interpolation, and filtering downstream of the original observations.

## Expanded signals and sensing

- Add Honda-specific diagnostics only when supported by documented definitions. Keep standardized, manufacturer-specific, and experimentally identified signals identifiable in the registry.
- Evaluate passive CAN monitoring and decoding with a suitable interface. Verify listen-only behavior on the chosen hardware and record evidence for experimentally identified messages.
- Integrate external accelerometers, GPS, and temperature and pressure sensors as available. Establish time alignment for independent acquisition sources, then use it for FFT, order tracking, and correlation with vehicle operating parameters.
- Assess long-term condition monitoring and anomaly detection after collecting repeatable baseline data.

## Raspberry Pi deployment

- Verify serial access, storage, and headless operation on Linux. Measure startup, shutdown, power, and storage behavior before enabling automatic capture at vehicle startup or installing the Pi permanently.

## Open questions

- What sustained polling rates can the adapter and vehicle support for the selected signals?
- How should acquisition sources share timestamps, and how much storage will a typical session require?
