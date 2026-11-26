# Monitor engine and CVT changes across trips

`cardaq health` compares one vehicle with its own history. It uses saved recordings and gives each comparable trip one vote. Start with the ECU's own diagnostic evidence, then look for changes that recur at the same temperature, speed, RPM and load.

## Build a local report

Create `captures/health/health-history.toml`. Use one `[[trip]]` entry per drive. Choose either a full recording or its culled copy for that drive. Capture paths are relative to the manifest. Each recording needs an absolute timestamp with UTC offset and its elapsed time. The report rejects overlapping recordings. `label` and `note` are optional.

```toml
vehicle = "Civic LX 2.0 CVT"

[[trip]]
capture = "../recordings/2026-11-24/outbound.csv"
group = "outbound-D"
label = "Morning commute"
note = "Driver reported D throughout."

[[trip]]
capture = "../derived/2026-11-24/return-culled.csv"
group = "return-mixed"
label = "Evening commute"
note = "Started in D and switched to S early."
```

```sh
uv run --locked cardaq health captures/health/health-history.toml
uv run --locked cardaq health captures/health/health-history.toml --output captures/health/health-history.json
```

The default HTML report goes beside the manifest with the same base name. Open it locally or use the JSON for analysis. Add new recordings to the manifest and rerun the command. Reuse group names for comparable directions and reported selector use. Keep a mixed-mode trip in its own group until the selector signal is verified. The vehicle label can be a nickname. Keep any VIN, precise route details, captures and personal trip notes local.

## What to examine first

Select a metric under **Measurement history** to see which part of the engine or transmission supplies the reading, how the qualifying samples become one trip value, and which other signals can help explain a change. The worked numbers illustrate the calculation. The table underneath contains the measurements from your selected trips. For background on the sensing principles, see [Bosch on crankshaft pickups](https://www.bosch-mobility.com/en/solutions/sensors/crankshaft-speed-sensor/) and [DENSO on oxygen and air/fuel sensors](https://www.densoautoparts.com/reference-o2-and-af-sensor-troubleshooting/).

| Indicator | What would draw attention | What to inspect alongside it |
| --- | --- | --- |
| **Cylinder misfire counters and malfunction indicator lamp (MIL)** | Mode 06 tests `0C` and `0B` give each cylinder's last/current driving-cycle count and weighted history, respectively. A recurring increase on the same cylinder is worth following. Request `0101` reports the MIL state and confirmed emissions-related trouble-code count. | A key-on poll can still show the previous cycle's counter. Follow successive polls and the final reading. Repeated observations of the same counter represent one count. Retrieve the actual diagnostic trouble code (DTC) and its freeze-frame conditions when available. |
| **Short- and long-term fuel trim** | A repeated positive shift means the engine computer is adding more fuel correction. A shift confined to warm stops gives a different pattern from one that persists under cruise load. | Compare short-term correction with the learned long-term value in the same state. Then inspect manifold pressure, airflow, commanded purge and fuel rate. Trims qualify only during observed normal closed-loop operation. |
| **Warm stopped RPM and RPM spread** | A persistent change in median RPM or a wider interquartile range (the middle half of readings) shows a change in observed idle behavior. | Check the cylinder counters and trim at the same stops. Accessory load and selector position can affect idle. Brief vibration between RPM polls needs a faster measurement. |
| **Cruise coolant temperature** | A sustained shift in coolant sensor 1 after ten minutes of observed engine operation is worth comparing with the warm-up trace. | Check the starting temperature, second coolant sensor and ambient conditions. A block heater changes the starting point. A gap in RPM coverage restarts the ten-minute clock. |
| **Candidate converter slip and pulley-ratio change rate** | At steady speed and load, repeated increases in the median absolute engine-to-turbine RPM difference or in the magnitude of ratio changes can identify a stretch for closer inspection. | Open the signed traces beside road speed, load and candidate fluid temperature. Verify the selected mode, shaft identities, scales and clutch command before interpreting the difference mechanically. Honda's i-HDS can display and capture reference data. [Honda diagnostic tools](https://techinfo.honda.com/Rjanisis/pubs/web/RJAAI001_TOOLS1.htm) |

The report prints each indicator's operating window and sample count. Engine trim windows separate warm stops from low- and high-RPM cruise. CVT windows require five seconds of nearly steady speed and load with warm candidate fluid. A missing value means that the recording lacked enough qualifying observations. In the drive viewer, **Cylinder misfires** shows when each higher counter reading arrived, the interval since the previous check, and the running total for that drive. [Recording guide](RECORDINGS.md#compare-recordings)

## Read a watch or repeat

Each indicator uses up to **30 earlier eligible trips** in the same manifest group. Screening starts after eight previous values. The reference center is their median and the spread is their median absolute deviation (MAD). A value draws a watch when its absolute modified Z-score exceeds 3.5 and its distance from the median exceeds the feature's measurement floor, where defined. When the previous MAD is effectively zero, a known floor supplies the comparison radius. Otherwise the report marks the reference as flat. [NIST guidance on potential outliers](https://itl.nist.gov/div898/handbook/eda/section3/eda35h.htm)

Two successive eligible trips beyond the reference in the same direction earn a repeat. Missing trips for that indicator contribute no vote. The review threshold describes how unusual a measurement was for this vehicle and group. A component diagnosis needs independent evidence.

## Spot gradual changes

Previously flagged values enter the rolling reference, so it can follow slow drift. A second comparison keeps the **first eight eligible trip values** as a fixed reference for each group and indicator. Beginning with the thirteenth eligible trip, it compares the median of the **latest five eligible trips after those first eight**, including the current one, with the original median. A **shift** means this recent median moved beyond the same MAD and measurement-floor bounds used for a single-trip watch.

A single unusual measurement can earn a watch while the five-trip median stays steady. Conversely, an indicator can accumulate a shift from the early trips even when each recent trip fell within its rolling bounds. Check whether service, seasonal temperatures or a change in driving conditions coincided with the trend. The early trips establish the anchor regardless of the vehicle's condition at the time.

## Next evidence to collect

Track which cylinders accumulate counts across completed cycles. Add read-only snapshots of confirmed, pending and permanent DTCs, readiness status and freeze frames. Verify the selector byte against observed D/S changes and the converter against a known lock-up command. Record ambient temperature and relevant maintenance so later shifts in the history have a date and context. [Civic PID inventory](changes/0002-pid-sweep/pid-inventory.md) · [Derived signal roadmap](DERIVED_SIGNALS_ROADMAP.md)
