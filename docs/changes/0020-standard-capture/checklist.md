# Verification

- [x] Shared the addressed PID bitmap walk between `sweep --auto --sample` and `record --profile standard`. Verified the adapter commands and sampled PIDs on a simulated serial connection.
- [x] Replayed 11-bit and 29-bit replies, ignition-on zero RPM, other responders, invalid replies, and a reconnect with a different inventory. Exported a viewer from the simulated capture and checked the engine RPM, speed, and coolant samples.
- [x] Added the [parked start procedure](../../RECORDINGS.md#first-drive-in-another-vehicle). Passed 97 unit tests, five offline browser tests, Ruff on the changed Python files, and `git diff --check`.
- [ ] In the RAV4, save its responder inventory and verify a short parked CSV before recording the drive.
