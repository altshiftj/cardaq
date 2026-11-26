# Record and compare drives

## Connect an adapter

`cardaq ports` lists serial devices without opening them. `cardaq identify` reads the selected adapter's hardware and firmware IDs. The USB OBDLink EX has been verified on Windows at 115200 baud. On Linux, pass the listed device path, for example `/dev/ttyUSB0`. Raspberry Pi hardware verification is still on the roadmap. The OBDLink CX uses a separate Bluetooth Low Energy transport. [OBDLink programming manual](https://www.scantool.net/scantool/downloads/682/obdlink_frpm_f.pdf) · [OBDLink CX developer notes](https://support.obdlink.com/support/solutions/articles/43000746707-obdlink-cx-adapter-notes)

For a repeatable setup, copy `cardaq.example.toml` to `cardaq.toml`, set `[serial].port`, and pass `--config cardaq.toml` to `identify`, `sweep`, or `record`. Explicit command-line settings take precedence over the file. The defaults are 115200 baud and a two-second serial timeout. If opening a listed port fails, check its name and close OBDwiz or another process using the adapter. [Example configuration](../cardaq.example.toml)

Use `sweep` to see which standard Mode 01 parameter identifiers (PIDs) each electronic control unit (ECU) advertises. Add `--sample` to read each distinct advertised PID once. On the project Civic, the engine and transmission modules both report coolant temperatures under PID `67`. The recorder uses a fixed Civic polling profile. Running a sweep does not change that profile. [Civic PID inventory](changes/0002-pid-sweep/pid-inventory.md)

## Start and finish a capture

```sh
uv run --locked cardaq record --config cardaq.toml --duration 1800 --output captures/drive-01.csv --note "Engine cold at start"
```

1. While parked, start the recorder with a new output filename. The `Ready` line confirms an ECM RPM response. Zero RPM is a valid observation with the ignition on and the engine off.
2. Leave the recorder running unattended during the drive. The CSV is flushed after every row and synced to disk periodically.
3. Once parked, press Ctrl+C for a foreground run, or create an empty file with `.stop` appended to the CSV filename. For the command above, that is `captures/drive-01.csv.stop`. The recorder also stops at the duration limit. A normal stop writes an `end` row. A foreground interruption exits with status 130.

After key-off the adapter can remain powered while the vehicle stops answering. The recorder retries during the remaining recording time. A parked break can therefore appear as a long gap followed by another drive. Use a fresh filename for each leg when you want to compare them individually.

## Read the CSV

Each row describes one recorder event. During polling, a single row can hold replies from multiple ECUs. Columns such as `ecm_engine_speed_rpm` carry the units in the name. An empty measurement cell means the row has no decoded observation for that signal. Zero is a measured value.

| Column | Contents |
| --- | --- |
| `timestamp` | Local wall-clock time with UTC offset, recorded when writing the row. |
| `elapsed_s` | Monotonic seconds since capture start. The viewer aligns samples using this clock. |
| `request_elapsed_s` | Monotonic time just before sending that query. Subtract it from `elapsed_s` to estimate reply latency. |
| `event` | `start`, `reply`, `no_data`, `adapter_status`, `transport_error`, or `end`. |
| `request` and `reply` | Query text and returned frames. Multiple response lines are joined with a vertical bar. |
| `detail` | Start note, transport error, or reason for stopping. |
| Measurement columns | Sparse standard readings and Honda-specific fields. The `candidate_` prefix marks provisional identities or scales. |

The viewer can recover additional standard signals, including fuel mass flow, from the saved raw replies. Keeping the original CSV allows later versions to decode more of the same drive. [Capture decoder](../src/cardaq/pilot_measurements.py) · [Viewer decoder](../src/cardaq/viewer/standard.py)

## Compare recordings

Choose a metric under **Signals**. Select **Chart guide** beside the metric title for a plain-language explanation and a suggested comparison. For example, if the pulley ratio changes, **Compare with** lets you open the two spinning parts’ speed readings in the same time window to see which one changed. Open **Where the number comes from** for sensor locations, formulas and details of Honda signals still being verified.

On the Civic’s 2.0 L K20C2 engine, coolant sensor 1 samples the engine side of the cooling system and sensor 2 samples the radiator side. The ECM and TCM can report the same probe. During a preheated start, comparing the two probes tells you more about the distribution of heat than comparing two controllers’ copies of sensor 1. [K20C2 thermostat housing procedure](https://honcivic.automotive-manuals.com/techinfo/html/en/civic-fc-fk/R003104.html) · [K20C2 radiator procedure](https://honcivic.automotive-manuals.com/techinfo/html/en/civic-fc-fk/R003108.html) · [Honda’s 2020 Civic component list](https://owners.honda.com/Documentum/Warranty/Partslist/2020_Honda_Civic_Sedan_and_Coupe_-_EWPL_-_APL12747_SIS.pdf)

```sh
uv run --locked cardaq view captures/outbound.csv captures/return.csv --label "Outbound" --label "Return" --output captures/comparison.html
```

Use the checkboxes in **Recordings** to choose the drives to compare. Select the **Recordings** heading to collapse or reopen the list. Your selected drives stay on the charts. Chart sections, misfire plots and notebook panels also fold independently. Use **Collapse all** for an outline of the report, or **Expand all** to open every panel and its details. Open **Trip details** for start times, peak readings and trip totals. In a four-drive report, try checking just the two outbound trips and selecting **Cumulative fuel used** on the distance axis. The charts, summaries, speed bands and notebook use the same selection. Hiding the drive that supplied a focused event clears that event. Notes written for the full set reappear when all drives are selected in the entire-recording window.

- **Signal explorer.** Each metric explains what it measures and how to read its trace. Below the graph, compare the samples in the selected window. Continuous signals show the sample median and range, temperatures show first and last readings, and cumulative signals show the observed change. Flags count positive samples and status bytes show the most frequent codes. Sample counts reflect polling frequency. Hover, tap, or use the arrow keys on the graph for individual readings.
- **Horizontal axis.** Elapsed time starts at recorder launch. Observed distance integrates vehicle speed over nearby readings. Two return journeys can pass different physical locations at the same distance.
- **Quick looks.** Opening the section shows all its charts together. Each chart has a table of readings for the selected drives. Select **Explore in Signals** to open the full graph and chart guide.
- **Cylinder misfires.** Choose a drive under **Cylinder misfires**. The recorder asks the engine computer for each cylinder's cycle counter about once a minute. A colored dot marks the first reply with a higher count. The line to its left reaches back to the previous valid check for that cylinder. A change of +2 means the computer reported two more misfires between checks. The CSV gives a timestamp for each reply, so the individual firing times within that window are unknown.
- **Cumulative misfires.** Each cylinder starts at zero on its first reading. The steps add up observed increases. A first reading of 3 followed by 3 and then 4 contributes one new count. If the counter drops, the lower reading becomes the baseline for the next comparison. A missing reply extends the time until the next comparison.
- **Trip notebook.** Select an engine start, launch, stop, steady-speed stretch, possible fuel-cut coast, or telemetry gap to focus the graph. Warm-up milestones use the first observed engine run with sufficient data. Speed-band dwell includes stationary time before engine start. The summary card's stopped time requires a running engine.
- **Operating map.** Compare RPM, pulley ratio, fuel flow, or air per intake event in 10 km/h speed bands. Dots show medians and whiskers show the middle half of observations in each band. Filter by load when available and expand **Speed band values** for the counts.
- **Derived and candidate signals.** Read the selected metric's description for its inputs and assumptions. Trip totals span observed intervals. Speed and RPM integration skip gaps over 1.5 seconds, and fuel integration skips gaps over five seconds. The pulley-ratio estimate uses a candidate output RPM whose scale still needs independent verification. [Derived signal roadmap](DERIVED_SIGNALS_ROADMAP.md) · [Shifter verification procedure](changes/0005-derived-signals/plan.md#parked-shifter-check)

The generated HTML contains the drive labels, displayed start times and plotted samples, including odometer readings when available. Raw CSVs also contain timestamps, notes and diagnostic replies. For a public bug report, the synthetic demo or a minimal redacted CSV usually provides a smaller reproduction. [Offline demo](../README.md#try-the-viewer)

### Include observations about specific recordings

Pass `--signal-notes path/to/notes.json` to `cardaq view` to embed your own observations under the graph. They appear in the **Entire recording** window while all original drives are selected. Shorter windows and event views show statistics for their own plotted samples.

The notes file contains a `recording_sha256` list with the CSV fingerprints in command-line order and a `signals` object keyed by plotted metric ID. For example, an entry in `signals` could read `"ecm_engine_speed_rpm": "Both drives held 75 km/h, but the second ran about 600 RPM higher."` On Windows, `Get-FileHash -Algorithm SHA256` gives the fingerprints. On Linux, use `sha256sum`. The fingerprints bind the notes to the recordings used to draw the conclusions.
