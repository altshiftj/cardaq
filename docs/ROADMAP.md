# Development roadmap

**The next milestone is a pre-service baseline for one Civic.** Recording, charting and health screening already work. Repeating a few comparable trips now will give later measurements a reference, especially across the planned 5,000-mile service. The November review records what has been demonstrated on the car and what has been tested with synthetic data. [Progress report · November 24, 2026](changes/0013-progress-review/report.md) · [Derived signal roadmap](DERIVED_SIGNALS_ROADMAP.md)

## Now · collect the evidence that has a deadline

| Priority | Next action | What would count as progress |
| --- | --- | --- |
| Pre-service reference | Repeat the same outbound commute in Drive. Use the existing manifest note for heater use, outside temperature and any unusual stops. Record the actual date and odometer for each fluid or tire change. | For each indicator, count trips with enough readings in its driving window. Eight earlier eligible trips enable the first rolling comparison on trip 9. Even fewer trips are worth preserving before service. [Health history guide](HEALTH_HISTORY.md) |
| Selector verification | Record a parked sweep with time-stamped dashboard positions. Return to Drive and repeat the Sport holds. | Compare the settled codes in Honda reply `2322` against the independently observed positions. Document repeatable matches and ambiguous states. Use mixed-mode trip labels until the observations justify finer labels. This experiment tests the selector field only. [Parked procedure](changes/0005-derived-signals/plan.md#parked-shifter-check) |
| Block-heater comparison | Compare outbound starts with the heater on and off, after similar overnight parking, at similar outdoor temperatures. Keep direction and mode consistent. | For each drive, report starting coolant at both probes, the engine-side dip in the first minute, and fuel consumed over the first two miles. Compare repeated runs with adequate speed and fuel coverage. Record whether heater operation was observed or only scheduled. [Recording guide](RECORDINGS.md) |

## Next · make the growing history useful

1. **Show service events and baseline coverage in the health report.** Add optional structured heater, odometer and service information alongside existing notes. Show how many trips qualify for each indicator, where readings are missing, and where a service event falls. Test this with an older manifest, an ineligible drive that adds no vote, and a service marker that preserves the earlier reference. If fluids and tires change together, label that as a combined change. Reassess the longer trend when the first eight and latest five eligible trips can be compared, starting at trip 13. [Current rules](HEALTH_HISTORY.md#spot-gradual-changes)
2. **Capture the car’s explanation when a counter moves.** Add a read-only snapshot of confirmed, pending and permanent trouble codes, readiness, and available freeze-frame readings (the conditions the car saved with a fault). The decoder should distinguish a valid empty list from an unsupported query or lost reply, keep the original frames, and show which controller answered. Verify with fixtures and a parked read. [Existing diagnostic inventory](changes/0002-pid-sweep/pid-inventory.md)
3. **Make a suspicious chart point traceable.** Start with a pulley-ratio point. Show the two contributing readings, their timestamps, the calculation and the confidence in the shaft labels. Expose sampling gaps and per-request timing where they affect interpretation. The inspector is ready when a contributor can reproduce the displayed value from saved replies and see why a nearby point is missing. Extend the same metadata into a signal registry as other calculations need it. [Detailed analysis backlog](DERIVED_SIGNALS_ROADMAP.md)

## In parallel · prepare the contributor snapshot

Review and group the outstanding working-tree changes into shareable commits, using synthetic recordings for public examples. Verify the documented demo, installed-wheel tests and hooks from a fresh checkout and confirm the hosted Windows and Linux workflow runs. Local packaging and real Git-hook smoke tests already provide a starting point. [Contributor setup](../CONTRIBUTING.md) · [Packaging evidence](changes/0008-project-housekeeping/checklist.md) · [Hook verification](changes/0012-pre-commit/checklist.md)

## Serial foundation

The USB OBDLink EX r2.7.1 with STN2232 v5.10.3 firmware was verified on Windows at 115200 baud. The Civic uses 29-bit CAN at 500 kbps. Its engine and transmission controllers advertised 44 and 14 standard live-data identifiers respectively. Both supplied coolant readings through PID `67`. The usual `05` query returned no data. The recorder preserves raw replies and survives gaps. Ignition-off and recorder shutdown are separate events. [Physical verification](changes/0001-serial-bootstrap/checklist.md) · [Live sweep](changes/0002-pid-sweep/report.md#physical-validation-and-obdwiz-comparison) · [Recorder behavior](RECORDINGS.md)

## Later · choose hardware for a demonstrated need

- **CVT reference measurements.** Use independent shaft speeds, pulley ratio, fluid temperature and clutch command to check candidate mappings. A dashboard selector match or two nearly equal RPM readings cannot establish the pulley scale or clutch state.
- **Acquisition improvements.** Measure signal cadence and gaps before changing the poll schedule. Consider configurable rates, focused queries, live charts, alternative OBD libraries or passive CAN when saved replies and existing tools cannot answer the question.
- **Route and vibration studies.** Add synchronized position and elevation for same-road comparisons, or a high-rate motion sensor and RPM reference for vibration work. Define the required timing and verify alignment before interpreting correlations.
- **Unattended Raspberry Pi recording.** If laptop capture becomes the obstacle to repeated trips, test the real adapter on Linux, ignition-off handling, power draw, shutdown and recovery, and storage over a representative drive. Desktop and simulated serial tests cover a different environment.
