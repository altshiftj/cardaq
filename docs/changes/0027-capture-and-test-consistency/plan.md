# Changes and verification

1. Use locked pytest dependencies for local development and installed-wheel CI. Keep browser tests separately selectable. Existing unittest cases can run alongside new pytest functions.
2. Give Civic and standard polling a consistent definition of a successful reply. Replay positive, negative and unrelated replies and check the logged event and count.
3. Share the textual CAN frame reader across decoders. Exercise frames with and without an adapter length digit and retain each signal decoder’s payload checks.
4. Check available vehicle identities before combining trips. Cover matching, conflicting and missing identities. Run the ordinary and Chromium suites against the built wheel.
