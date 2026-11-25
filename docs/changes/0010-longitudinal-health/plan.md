# Implementation plan

1. Use a local trip manifest for one vehicle. Carry a comparison group, recording timestamp and optional context for each independent trip.
2. Reuse the capture reader and existing signal decoders. Evaluate closed-loop engine behavior and provisional CVT indicators only in defined operating conditions. Preserve coverage and missing observations.
3. Read the Civic's saved cylinder-monitor results separately and show the reported counts, including zeros and unavailable reports.
4. Compare a trip with its own earlier group history. Display reference size, direction and repeated deviations with an offline trend report. Document the assumptions and signals to verify next.
5. Exercise the two recorded commutes and controlled histories with known changes. Check partial data, duplicate journeys, chronology and the installed CLI.
