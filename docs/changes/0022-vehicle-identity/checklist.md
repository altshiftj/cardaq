# Verification

- [x] Tested 11-bit and 29-bit frames, interleaved responders, repeated and conflicting VINs across controllers, missing or malformed data, and distinct vehicle codes for two cars of the same model.
- [x] Replayed the no-argument CLI with a simulated adapter. The same VIN resumed its file after reconnect. A different VIN ended it before another data poll. Verified unidentified standard captures, same-second filename collisions, local VIN metadata, CSV hashing, and vehicle identification after a rename.
- [x] Passed 105 unit tests, five browser tests, Ruff, the wheel build and the whitespace check. Opened Recording details for a renamed fixture in Chromium and verified the vehicle label and code. Added the one-command workflow to the README and recording guide.
- [ ] Confirm VIN readback while parked on each physical vehicle.
