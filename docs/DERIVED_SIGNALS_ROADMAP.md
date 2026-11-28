# Derived signal roadmap

The next signal work supports three questions. Does preheating change early fuel use on comparable drives? Which transmission readings follow an independently observed selector change? Which engine or transmission changes recur across eligible trips? The main roadmap gives the order of work. This page tracks the calculations and measurements behind it. [Development roadmap](ROADMAP.md) · [November progress report](changes/0013-progress-review/report.md) · [PID inventory](changes/0002-pid-sweep/pid-inventory.md)

## Available in the viewer

- Decode additional ECM channels from existing raw replies, including fuel flow, airflow, pedal, throttle, load, odometer, fuel trims, temperatures and the three crank-torque inputs.
- Plot trip integrals, rolling fuel and revolution ratios, moving fuel-cut candidates, stopped engine-on time and fuel, speed cycling, and air per cylinder intake. Use elapsed time or observed distance as the horizontal axis.
- Inspect CVT ratio and output-speed change rates, slip as a percentage of RPM, manifold vacuum, coolant sensor difference, and one-minute warming rates. Use the Capture quality group for median diagnostic reply latency.
- Compare median and middle-half values across speed bands for pulley ratio, RPM, fuel rate, air per cylinder, and estimated crank torque and power. Filter by load and inspect the exact band values.
- Open inferred trip events in the timeline. Compare first-run warm-up milestones in minutes and miles and time spent in each road-speed band. [Trip notebook](changes/0007-trip-notebook/plan.md)

The derived charts have plain-English guides and links to related traces. An inspector that shows the exact input samples behind a selected point is still open. [Chart guide](RECORDINGS.md#compare-recordings)

## Trip and driving dynamics

| Working today | Next extension or check |
|---|---|
| Integrated distance, engine turns and engine-on stopped time | Check distance against odometer change over the same covered interval. Treat a gap separately from a stop. |
| Cumulative fuel, rolling fuel and turns per kilometer, and gains in speed-related energy per kilogram | Compare early-trip fuel over the same distance after similar overnight parking. Report fuel and speed coverage alongside the result. |
| Clickable starts, launches, stops, steady-speed stretches, possible fuel cut and gaps | Link an event to raw samples. Add ignition or lift-off markers and playback when the events can be independently identified. |
| Time spent in speed bands | Compare the duration and pattern of stops across repeat commutes. |
| Time and observed-distance overlays | Add route progress or reversed-distance views only for known shared roads and matched endpoints. Use GNSS for location-level comparison. |

## CVT and power flow

| Signal or view | Inputs and verification |
|---|---|
| Ratio and RPM operating maps | Speed bins, load filters, counts and spread are available. Test temperature and acceleration/coasting filters after the selector sweep gives independent evidence about mode. |
| Ratio change rate and RPM attribution | The viewer calculates ratio and output-speed change rates over bounded intervals. Their sum gives the input-speed change rate on the same logarithmic scale. Expose both inputs and timing for a worked sample. A constant scaling error cancels in the change rate but still affects the absolute ratio. |
| Converter coupling | Plot signed slip and slip normalized to engine RPM. Summarize near-equal engine and turbine speeds with time weighting. Use a verified clutch-state channel to validate lock-up. |
| Dwell, hysteresis, and ratio hunting | Compare ratio changes on acceleration and lift-off. Look for repeated oscillation only within sustained speed and load windows. |
| Shifter and Honda field verification | Compare the raw DID 2322 byte with repeated stationary dash positions. Use i-HDS or a separately verified selector signal to validate the mapping, pulley scale, and candidate fluid temperature. [Parked shifter check](changes/0005-derived-signals/plan.md#parked-shifter-check) |

## Engine, fuel, and air

| Signal or view | Inputs and verification |
|---|---|
| Fuel budget and overrun | Integrate ECU-reported fuel mass. Compare idle, launch, cruise, and lift-off budgets. Use released pedal, a running engine, and sustained reported zero fuel to label candidate fuel cut. |
| Air charge and demand | The air-per-intake calculation uses airflow, RPM and a four-cylinder, four-stroke assumption. For other vehicles, use a verified cylinder count and engine cycle before showing this estimate. When either is unknown, show the measured airflow and RPM. Compare manifold vacuum (barometric minus manifold pressure), pedal, throttle, load and pulley ratio in steady windows. |
| Mixture behavior | Map fuel trims and purge by load and temperature. Check closed-loop status and equivalence-ratio conventions before comparing commanded and observed mixture. |
| Crank torque, power, and efficiency | The viewer estimates signed crank torque from indicated, friction, and reference torque and uses RPM to display power in kW or hp. Verify the Civic's changing PID 63 scale against an independent reference before using the absolute values for efficiency. |
| Exhaust mass balance | Test whether exhaust flow agrees with airflow plus ECU-reported fuel during steady operation. Compare units and determine how independently the ECU estimates each channel. |

## Thermal behavior and long-term trends

- The offline health history now tracks cylinder-counter changes, ECM warning-lamp and code-count observations, closed-loop fuel trims, idle RPM and spread, conditioned coolant temperature, and settled-cruise CVT estimates. Its unit of comparison is one eligible trip in the same comparison group. [History and interpretation guide](HEALTH_HISTORY.md)
- Coolant sensor 1, candidate CVT fluid and reported catalyst temperature already have first-run milestones and one-minute warming rates. Both coolant probes and their difference are plotted. Next, compare the engine-side starting temperature, its first-minute minimum and fuel used in the first two miles of matched heater-on/off drives.
- The health report already summarizes warm stopped RPM and its spread, and fuel trims under comparable conditions. Next, annotate service events and show per-indicator coverage. Further options include time below temperature targets, intake temperature milestones, heat soak at restart and starting-voltage recovery.
- Extend the observed Mode 06 counter histories with readiness transitions, pending and confirmed DTC identifiers, and matching freeze-frame data. Refine the operating windows as more routes, seasons and independent selector observations are captured.

## Instrumentation and evidence

### Trace a derived OBD signal

- **Start the point inspector with crank power.** For one selected point, show the raw ECM replies, decoded values and units for reference torque (PID `63`), indicated torque (`62`), friction torque (`8E`) and RPM (`0C`). Show each reply's elapsed time and offset from the reference. A reader should be able to reproduce the displayed kW using `N·m = reference × (indicated % − friction %) / 100` and `kW = N·m × RPM × 2π / 60,000`. [Crank calculation and validation status](changes/0021-crank-output/report.md)
- **Explain missing points and measure coverage.** For the selected interval, count reference-torque observations, valid torque estimates and valid power estimates. Flag nonpositive references and identify missing inputs or replies outside the 0.5-second pairing window. For example, timely torque inputs with the nearest RPM 0.6 seconds away yield torque only. Compare these counts alongside per-request latency, cadence and gaps before changing the poll schedule.
- Extend the inspector to a pulley-ratio point with both shaft readings, their timestamps and the confidence in their labels and scale. Track duplicate ECM/TCM residuals and disagreement with a reference tool.

### Acoustic and vibration measurements

For a first Civic comparison, find a repeatable peak in a microphone or accelerometer spectrum and compare its frequency across intervals with similar road speed and different engine RPM. Then check which sensor locations show the same peak. Keep sensor ID, mounting position, accelerometer orientation, microphone gain and sample rate with the run so comparisons are repeatable. [Instrument assignments](../hardware/wiring/cable_schedule.csv) · [Bench checkout](../hardware/bench.md)

OBD RPM and road speed give operating context. For phase comparisons between hubs, measure clock offset and drift using a common vibration at the start and end of the run. For **order tracking** (frequency relative to shaft speed), establish a synchronized RPM reference and verify its cadence and timing uncertainty over the speed changes being studied. A shared capture ID identifies the drive. Sample alignment needs its own measurement. [OBD timestamp fields](RECORDINGS.md#read-the-csv) · [NI order analysis](https://www.ni.com/en/shop/labview/performing-order-analysis-in-labview-with-sound-and-vibration-so.html)

### Other reference measurements

Add synchronized GNSS and elevation for matched road segments and climb energy. Add an IMU, brake state, and wheel speeds for grade-aware deceleration, cornering, and wheel-speed residuals.
