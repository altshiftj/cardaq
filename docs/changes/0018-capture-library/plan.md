# Automate capture placement and preserve provenance

- Save new recordings by capture date under `captures/recordings/` when no explicit output is given. Issue a unique identifier, retain the CSV format, and write adjacent metadata with provenance and an integrity hash on completion.
- Give unnamed viewer exports a repeatable location under `captures/views/` and save their ordered input fingerprints. Let health HTML default to the manifest's location.
- Organize existing captures under `recordings`, `derived`, `imports`, `views`, `health`, and `demo`. Preserve content and labels, update relative manifest paths, and record provenance for the clipped copy. Check existing exports and notes after the move.
- Update the quickstart and document the layout, timestamps, metadata, and explicit path options. Verify the default CLI workflow with a simulated adapter and run the full test suite.
