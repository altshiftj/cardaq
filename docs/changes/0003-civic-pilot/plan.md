# Civic verification pilot

**Tuesday, November 24, 2026 · Eastern time**

The goal is to capture key-on, engine start, and a roughly 30-minute commute in one continuous log. The recorder runs locally with a 45-minute cap to cover the pre-start readings, drive and arrival.

## The evening before

1. Leave the block heater on its usual **4:00 a.m.** schedule. Use the same laptop and OBDLink EX from the first capture. Keep the laptop powered and prevent sleep through the drive. Secure the laptop and cable so they stay clear of the pedals and are out of the driver's way.
2. Close OBDwiz so COM5 is available. The recorder is ready to launch from the project's existing Python environment.

## Key-on and start

1. Unplug the block heater. With the Civic parked, put the key in **ON** with the engine off. Tell me the key-on time, outside temperature with units, and how you measured it. Include whether 4:00 a.m. was the scheduled start or an observed start.
2. I’ll launch the recorder while the engine is off. Wait for confirmation that the engine module answered and the pre-start readings are in the file. If we have to recover the connection first, keep the car parked and wait for the updated status.
3. Start the engine when I confirm recording. Capture the transition from zero RPM to running, including any gap during crank. The heater may already have raised coolant temperature. Those readings are a useful heated baseline for this trip. An independent cold-soak comparison belongs on a heater-off day. [Honda temperature check](https://honcivic.automotive-manuals.com/techinfo/html/en/civic-fc-fk/T004808.html)

## Drive and arrival

1. Drive to work normally with the recorder running unattended. Ordinary acceleration and steady cruising give the CVT shaft-speed candidates enough variation for a first comparison. Leave the laptop and adapter alone while driving.
2. At work, park and switch off the Civic. Leave the laptop running and the USB adapter connected briefly. Tell me the time the key went off so I can stop the recorder after it logs the transition. If the adapter loses power, the recorder keeps the rows already written, logs the loss, and retries until stopped or the cap expires.
3. After the recorder stops, confirm the start and end times, data through arrival, and any communication gaps. Open the CSV only after the recorder exits if the spreadsheet app holds an exclusive lock.

## Recorder commands

I’ll launch the recorder as a local background process. To start it yourself while parked, use this foreground command from the repository root in PowerShell. Replace the example note with the reported observations. Wait for `Ready` at 0 RPM before cranking.

```powershell
.\.venv\Scripts\python.exe -m cardaq record --port COM5 --duration 2700 `
  --output .\captures\civic_20261124_pilot.csv `
  --note 'Block heater scheduled 04:00 ET. Key-on <time>. Outside <temperature, unit and source>.'
```

When parked, `Ctrl+C` stops a foreground run. I’ll stop the background run by creating a file with `.stop` appended to the CSV path. For the example filename, the command is `New-Item -ItemType File -Path .\captures\civic_20261124_pilot.csv.stop`. The recorder writes an end row on either stop or at the time limit. Keep the CSV from any interrupted attempt and use a new filename when restarting.

## What the CSV records

- The 44 standard live-data requests, both Honda CVT requests, periodic cylinder misfire monitor reads, and OBD port voltage. Each request row keeps all raw response frames, including replies from both modules when available.
- Local timestamps with UTC offset, monotonic elapsed time, a start note for key-on and heater conditions, and explicit rows for no data or transport errors.
- Decoded columns for engine RPM, speed, coolant, pressure, module voltage, and the Honda CVT fields under study. CVT temperature and the shaft-speed candidates are labeled in the column names.

The recorder flushes completed rows as they arrive and syncs them to disk about once per second and at shutdown. If the vehicle stops responding at key-off, the earlier rows are already written and the recorder can close the CSV on request.

## Review and verification

- Confirm the file contains key-on rows with zero RPM, the transition to running, normal driving data, and the last valid response near arrival. Inspect timestamps and any no-data or disconnect events. Record the actual trip times if the boundaries differ from the planned times.
- Compare Honda engine RPM and pressure fields with the standard OBD readings. Compare candidate CVT fluid temperature and shaft speeds with Honda i-HDS when a reference is available. Check drive versus driven pulley speed while moving and compare their quotient against the i-HDS `Pulley Ratio`. The secondary shaft runs through a fixed gear pair. Its RPM needs a verified conversion before using it as pulley RPM. [Honda power flow](https://honcivic.automotive-manuals.com/techinfo/html/en/civic-fc-fk/C010796.html) · [Honda i-HDS Data List](https://techinfo.honda.com/Rjanisis/pubs/web/RJAAI001_TOOLS1.htm)
- Preserve the unmodified CSV as the pilot source. The LX's published forward ratio range of 0.408–2.526 is a plausibility check for a decoded value. [Honda LX specifications](https://www.hondainfocenter.com/2020/Civic-Sedan/Feature-Guide/Civic-Sedan-Specifications/)
