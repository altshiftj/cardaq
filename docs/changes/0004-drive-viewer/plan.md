# Drive viewer plan

1. Add a `cardaq view` command that accepts CarDAQ recording CSVs and generates a self-contained HTML file. Preserve the CSVs and the original units.
2. Plot each metric against elapsed capture time, ending the view at the last available sample. Provide metric selection, shorter time windows, crosshair readouts, and overview charts.
3. Label tentative Honda signals and plot large sampling gaps as breaks.
4. Generate and inspect the page for both Civic drives. Check parser behavior, the command entry point, and browser interactions.

The viewer uses recorded data and requires only a browser. The recorder and the adapter workflow stay independent of the viewer.
