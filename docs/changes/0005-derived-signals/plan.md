# Derived signal plan

1. Compute derived signals in the viewer from the actual sample timestamps. Use same-reply speed measurements for the pulley ratio, pair adjacent Honda polls for RPM differences, align coolant and CVT samples within a short window, and estimate acceleration from local ECM speed readings.
2. Extract the raw transmission byte using the existing Honda reply decoder. Present its numeric values without assigning selector positions.
3. Add metric groups, a ratio overview chart, and a short time view for checking the first minute of a parked recording.
4. Check timing and missing-data behavior with focused tests. Regenerate the commute viewer and inspect the derived and raw trace values against both CSVs.
5. Document a parked, brake-held shifter sweep. Check the byte against independently recorded selector positions when that capture is available.

## Parked shifter check

Use a flat, open spot with room around the car. Start in Park with the parking brake set. Keep the service brake firmly held throughout the sweep and leave the engine at idle. Have a passenger note the time and displayed position if available. Otherwise, use a fixed sequence and write it down before starting.

Run the recorder from the repository root using a fresh output filename.

```powershell
.\.venv\Scripts\python.exe -m cardaq record --port COM5 --duration 120 --output captures/civic_shifter_check.csv --note "Parked shifter check at idle"
```

Once recording, hold each marked position for about five seconds. Start with P, then R, N, D, and S. Include L if it is marked on the shifter. Return to D and repeat the D → S → D sequence to check whether the pattern repeats. Finish in P before using the laptop. [Honda Civic shifting instructions](https://cdn.dealereprocess.org/cdn/servicemanuals/honda/2020-civic.pdf#page=445)

```powershell
.\.venv\Scripts\python.exe -m cardaq view captures/civic_shifter_check.csv --output captures/shifter-viewer.html
```

Select **Shifter verification → Transmission status byte**. Check settled readings against the actual dash positions, including both Sport holds and the return to Drive. The byte could reflect a control state linked to the position. Treat it as provisional until the pattern repeats.
