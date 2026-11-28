# Development roadmap

**Build a history that can answer “Did warm idle change after the Civic’s 5,000-mile service, and which drives support that comparison?”** Collect repeat outbound trips before service and make per-vehicle history the first software milestone. The parked RAV4 check can run in parallel. [Civic progress review](changes/0013-progress-review/report.md) · [Health history guide](HEALTH_HISTORY.md)

## Now · collect the evidence that has a deadline

| Priority | Next action | What would count as progress |
| --- | --- | --- |
| Pre-service reference | Repeat the same outbound commute in Drive. Use the existing manifest note for heater use, outside temperature and any unusual stops. Record the actual date and odometer for each fluid or tire change. | For each indicator, count trips with enough readings in its driving window. Eight earlier eligible trips enable the first rolling comparison on trip 9. Even fewer trips are worth preserving before service. [Health history guide](HEALTH_HISTORY.md) |
| Selector verification | Record a parked sweep with time-stamped dashboard positions. Return to Drive and repeat the Sport holds. | Compare the settled codes in Honda reply `2322` against the independently observed positions. Document repeatable matches and ambiguous states. Use mixed-mode trip labels until the observations justify finer labels. This experiment tests the selector field only. [Parked procedure](changes/0005-derived-signals/plan.md#parked-shifter-check) |
| Block-heater comparison | Compare outbound starts with the heater on and off, after similar overnight parking, at similar outdoor temperatures. Keep direction and mode consistent. | For each drive, report starting coolant at both probes, the engine-side dip in the first minute, and fuel consumed over the first two miles. Compare repeated runs with adequate speed and fuel coverage. Record whether heater operation was observed or only scheduled. [Recording guide](RECORDINGS.md) |

## Development priorities

### 1. Connect recordings to a vehicle’s service history

The recorder now identifies cars across trips. The health report still relies on a hand-written manifest to say which drives belong to a vehicle and comparison group. In the first two-commute review, each drive qualified for nine of fourteen indicators, with only four indicators in common. Let the owner select a car, confirm comparable drives, and assign older captures whose vehicle identity is unknown. [Recording identity](RECORDINGS.md#local-capture-library) · [Observed coverage](changes/0013-progress-review/report.md#what-the-first-two-commutes-can-tell-us)

The first release should show a dated service marker, the eligible drives on each side, and why other drives did not contribute to the selected indicator. Keep the pre-service reference available and record simultaneous fluid and tire changes as one combined event. Check the result with an older manifest and with two cars of the same model. [Proposed service comparison](HEALTH_HISTORY.md#proposed-workflow-for-comparing-trips-across-service)

### 2. Trace a crank-power estimate back to the car

Two Civic observations at 118 km/h used different ECU reference torques, 204 and 185 N·m. Use them as the first worked examples. A reader should be able to select either power estimate, see the four source replies and their timestamps, and reproduce the displayed kW. For a positive reference reading that produced no estimate, identify which input was missing or outside the half-second pairing window. Extend the inspector to the candidate CVT pulley ratio next. [Crank-output findings](changes/0021-crank-output/report.md) · [Inspector and coverage checks](DERIVED_SIGNALS_ROADMAP.md#instrumentation-and-evidence)

### 3. Verify a second vehicle on the road

The 2021 Toyota RAV4 XLE has a recognized VIN pattern and uses standard CAN polling. The recorder and viewer have been tested together with simulated replies. On the RAV4, confirm VIN readback while parked, save the responder inventory, compare RPM with the tachometer and road speed with zero, then record a drive. For each controller, distinguish channels it advertised, channels that returned readings, and channels CarDAQ could decode. Use that inventory to decide which additional signals to support. [First-drive procedure](RECORDINGS.md#first-drive-in-another-vehicle) · [Outstanding hardware checks](changes/0020-standard-capture/checklist.md)

Use verified vehicle details where a calculation needs them. For example, air mass per intake event currently assumes a four-cylinder, four-stroke engine. Check the result on a known engine and show the missing prerequisite when engine configuration is unknown. [Air-per-intake calculation](../src/cardaq/viewer/trip.py)

### 4. Browse a year of recordings

On November 27, 2026, `cardaq serve` generated 5.85 MiB of HTML for the four recordings in the local library. The server caches unchanged CSVs, but the page embeds traces for every decoded drive. Open the library with a list by vehicle and date, then load traces for the selected drives. Keep `cardaq view` as the portable, self-contained comparison. [Folder server](../src/cardaq/viewer/live.py) · [Recording guide](RECORDINGS.md#compare-recordings)

Benchmark with a year of synthetic commute-length recordings. Measure time and bytes to open the list, compare two drives, and refresh after an active recording grows. Adding unselected drives should grow the list without adding their trace data to the response.

## Civic instrumentation

The acoustic and vibration rig can progress on the bench while the OBD recorder collects pre-service drives. The first hardware milestone is one front-hub recording with all four accelerometers and both microphones active. Save the raw samples and counters, check for gaps with Wi-Fi streaming, and measure the offset and drift between two sensors exposed to the same vibration. The drawings and checkout procedure are ready to use. The hub firmware and Pi sensor recorder still need implementation. [Hardware package](../hardware/README.md) · [Front hub checkout](../hardware/bench.md)

For a first combined vehicle run, verify the OBDLink EX on the Pi under Linux, check recording continuity through engine start, and confirm the Pi closes its SSD recording before power is cut at key-off. Keep the instrument run and OBD capture linked so the same event can be examined in both. [Power checkout](../hardware/bench.md#qualify-the-two-vehicle-power-paths-on-the-bench) · [Acoustic and vibration analysis](DERIVED_SIGNALS_ROADMAP.md#acoustic-and-vibration-measurements)

## Diagnostic follow-up

When a cylinder counter rises, link it to a read-only snapshot of confirmed, pending and permanent trouble codes, readiness, and available freeze-frame readings (the conditions the car saved with a fault). Distinguish a valid empty list from an unsupported query or lost reply, keep the original frames, and show which controller answered. Verify with fixtures and a parked read. [Existing diagnostic inventory](changes/0002-pid-sweep/pid-inventory.md)

## Serial foundation

The USB OBDLink EX r2.7.1 with STN2232 v5.10.3 firmware was verified on Windows at 115200 baud. The Civic uses 29-bit CAN at 500 kbps. Its engine and transmission controllers advertised 44 and 14 standard live-data identifiers respectively. Both supplied coolant readings through PID `67`. The usual `05` query returned no data. The recorder preserves raw replies and survives gaps. Ignition-off and recorder shutdown are separate events. [Physical verification](changes/0001-serial-bootstrap/checklist.md) · [Live sweep](changes/0002-pid-sweep/report.md#physical-validation-and-obdwiz-comparison) · [Recorder behavior](RECORDINGS.md)

## Later · choose hardware for a demonstrated need

- **CVT reference measurements.** Use independent shaft speeds, pulley ratio, fluid temperature and clutch command to check candidate mappings. A dashboard selector match or two nearly equal RPM readings cannot establish the pulley scale or clutch state.
- **Acquisition improvements.** Measure signal cadence and gaps before changing the poll schedule. Consider configurable rates, focused queries, live charts, alternative OBD libraries or passive CAN when saved replies and existing tools cannot answer the question.
- **Route studies.** Add synchronized position and elevation when a comparison needs the same road segment or a measure of climb.
