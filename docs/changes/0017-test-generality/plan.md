# Test supported variations and report behavior

- Vary sample timing and continuity around documented thresholds. Check derived values against hand-calculated expectations.
- Exercise health scoring with uneven observations and raw diagnostic evidence. Verify that earlier trips retain their results as later trips arrive.
- Replay a short scripted serial exchange through the recorder and viewer. Check the commands, timing and exported values.
- Open an exported comparison in a headless browser and exercise drive selection and event focus by visible state. Run the browser test in one CI job to limit setup costs.
- Run the Python and browser suites against the installed wheel. Inject faults in the test process or a temporary export to check that the new assertions catch the previously identified regressions.
