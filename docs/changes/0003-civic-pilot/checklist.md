# Civic pilot checklist

- [x] Review the minute capture, PID inventory, known COM5 settings, and block-heater schedule.
- [x] Write the pilot runbook and define the acceptance checks.
- [x] Implement the reusable `record` command with a new CSV, explicit gap records, periodic sync, and parked stop.
- [x] Run the Windows test suite. All 12 tests passed, including a simulated commute with readings beyond 30 minutes, ignition-off, USB loss and reconnection, and both stop methods. A separate detached Windows process with an absent COM port wrote a readable CSV and exited cleanly when another process created its stop file.
- [ ] Complete the key-on, startup, drive, and shutdown sequence on the Civic.
- [ ] Verify the pilot file and compare candidate CVT fields against a reference when available.

The November 24 pilot contains key-on, engine start and driving samples. The final row records a duration stop after loss of communication. Later work verified the exported series and recording fingerprints. A separately observed key-off time and independent CVT reference readings remain open. [Commute verification](../0006-commute-lab/checklist.md) · [Progress report](../0013-progress-review/report.md)
