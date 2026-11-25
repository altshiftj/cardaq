# Civic OBD-II PID inventory

The probe ran on 2026-11-23 at 10:13 p.m. Eastern over `COM5` using ISO 15765-4 CAN with 29-bit identifiers at 500 kbps. The standard Mode 09 ECU-name request `090A` identified `18DAF110` as `ECM-EngineControl` and `18DAF11E` as `TCM-TransmisCtrl`. [SAE J1979 diagnostics definitions](https://saemobilus.sae.org/standards/j1979_201202-e-e-diagnostic-test-modes)

## Mode 01 live data

The ECM advertised 44 data PIDs and the TCM advertised 14, all shared with the ECM. The ECM's final support response was for `01A0`, and the TCM's was for `0160`. Both cleared the continuation bit on their final page. A one-shot sweep sampled the advertised data PIDs. The names below describe the PID or its channel group. [OBDwiz SAE PID catalog](https://www.obdlink.com/obd-apps/obdwiz-app/)

| PID (hex) | Data | ECM | TCM |
| --- | --- | --- | --- |
| `01` | Monitor status since codes cleared | Yes | Yes |
| `03` | Fuel system status | Yes | |
| `04` | Calculated engine load | Yes | Yes |
| `06` | Short-term fuel trim, bank 1 | Yes | |
| `07` | Long-term fuel trim, bank 1 | Yes | |
| `0B` | Intake manifold absolute pressure | Yes | |
| `0C` | Engine speed | Yes | Yes |
| `0D` | Vehicle speed | Yes | Yes |
| `0E` | Ignition timing advance | Yes | |
| `11` | Absolute throttle position | Yes | Yes |
| `13` | Oxygen sensor locations | Yes | |
| `15` | Oxygen sensor voltage and trim, bank 1 sensor 2 | Yes | |
| `1C` | OBD compliance standard | Yes | |
| `1F` | Time since engine start | Yes | Yes |
| `21` | Distance traveled with malfunction indicator on | Yes | Yes |
| `24` | Wideband oxygen sensor lambda and voltage, bank 1 sensor 1 | Yes | |
| `2E` | Commanded evaporative purge | Yes | |
| `2F` | Fuel level | Yes | |
| `30` | Warm-ups since codes cleared | Yes | |
| `31` | Distance traveled since codes cleared | Yes | Yes |
| `32` | Evaporative system vapor pressure | Yes | |
| `33` | Barometric pressure | Yes | Yes |
| `3C` | Catalyst temperature, bank 1 sensor 1 | Yes | |
| `41` | Monitor status this drive cycle | Yes | Yes |
| `42` | Control module voltage | Yes | Yes |
| `43` | Absolute engine load | Yes | |
| `44` | Commanded equivalence ratio | Yes | |
| `47` | Absolute throttle position B | Yes | |
| `49` | Accelerator pedal position D | Yes | Yes |
| `4A` | Accelerator pedal position E | Yes | |
| `51` | Fuel type | Yes | |
| `55` | Short-term secondary oxygen sensor trim | Yes | |
| `56` | Long-term secondary oxygen sensor trim | Yes | |
| `62` | Actual engine percent torque | Yes | |
| `63` | Engine reference torque | Yes | |
| `66` | Mass airflow sensors | Yes | |
| `67` | Coolant temperature sensors | Yes | Yes |
| `68` | Intake air temperature sensors | Yes | |
| `6C` | Throttle actuator command and relative position | Yes | Yes |
| `8E` | Engine friction percent torque | Yes | |
| `9D` | Engine and vehicle fuel rates | Yes | |
| `9E` | Engine exhaust flow rate | Yes | |
| `9F` | Fuel system usage percentages | Yes | |
| `A6` | Odometer | Yes | |

### Support bitmap evidence

| Request | ECM bitmap | TCM bitmap |
| --- | --- | --- |
| `0100` | `B63CA813` | `90188003` |
| `0120` | `9007E011` | `8000A001` |
| `0140` | `F2C08C01` | `C0800001` |
| `0160` | `67100001` | `02100000` |
| `0180` | `0004000F` | |
| `01A0` | `04000000` | |

The sample verified one supported mass airflow channel (`66`, ECM flags `01`), one intake air temperature channel (`68`, ECM flags `01`), and two coolant channels per ECU (`67`, flags `03`). Throttle PID `6C` reported two fields for the ECM (`03`) and one for the TCM (`02`). Each of these PIDs can carry multiple fields, and the exact definition of OBDwiz's 80 and 24 selector counts remains open. [OBDwiz channel definitions](https://www.obdlink.com/obd-apps/obdwiz-app/) · [SAE J1979 digital annex](https://doi.org/10.4271/J1979DA_201905)

### OBDwiz PID Setup screenshots

The first batch of screenshots shows 113 distinct PID codes after deduplicating overlapping pages and rows that share a code. The visible codes span `01–1F`, `21–3F`, `41–4E`, `51–5F`, and `61–76`. The Civic advertised 39 of those codes on the ECM and 14 on the TCM as Mode 01 live data. The 14 TCM codes are included in the ECM's 39.

The second batch shows 44 distinct codes across `76–7F`, `81–9F`, and `A1–A3`. Code `76` overlaps the first batch, bringing the combined total to 156 distinct catalog codes. This batch includes four ECM matches (`8E`, `9D`, `9E`, and `9F`).

The third batch shows 37 distinct codes across `A3–BF`, `C1–C6`, and `C8–C9`, including odometer `A6`. Code `A3` overlaps the second batch, bringing the combined total to 192 distinct catalog codes. The supplied screenshots now cover all 44 verified ECM live-data PIDs and all 14 TCM PIDs.

The final batch shows `C9–DA` and `101–103`. Removing the overlap at `C9` adds 20 distinct labels, for 212 across the full screenshot set. Of these, 209 fit in one byte. The three higher labels describe readiness and grouped cylinder misfire counters. The exact requests OBDwiz uses for those labels remain unverified. [Publisher's SAE catalog](https://www.obdsoftware.net/software/obdfusion)

| PID Setup entries | What the Civic reported |
| --- | --- |
| `02` freeze-frame DTC | Both ECUs advertised it in Mode 02 for freeze frame `00`. |
| `05` and `67` coolant temperature | `0105` returned `NO DATA`. Both ECUs returned two coolant readings under `0167`. |
| `0F` and `68` intake air temperature | The ECM advertised `68` and reported one supported channel. |
| `10` and `66` mass airflow | The ECM advertised `66` and reported sensor A as supported. |
| `70–72` boost, turbo control, and wastegate | Neither ECU advertised these in Mode 01. |
| `7F` total engine and idle runtime | The verified live runtime is `1F`, time since the current engine start. Neither ECU advertised `7F`. |
| `9D` fuel rates and `9F` fuel system usage | The ECM returned both PIDs. The setup catalog lists two rows for `9D` and eight for `9F`. |
| `A4` actual transmission gear ratio and status | Neither ECU advertised `A4` under Mode 01. A direct `01A4` request returned `NO DATA`. |
| `A6` vehicle odometer | The ECM advertised and returned this PID. |

The screenshots show which entries the setup menu offers, including multiple rows per PID and entries that the Civic did not advertise. OBDLink documents that OBDwiz can display definitions unavailable on a particular vehicle. The 80 and 24 ECU-selector counts remain open. [OBDwiz on Windows](https://support.obdlink.com/support/solutions/articles/43000727094-get-started-with-your-obdlink-adapter-windows-)

The installed OBDwiz Help topic **PID Setup** identifies priority `1` as the fastest polling setting. The screenshots show RPM and vehicle speed set to `1`, and the `67` coolant channels set to `20`. The manual describes relative polling rates and gives no fixed frequency in hertz for these settings.

## Other standard diagnostic identifiers

| Service | ECM | TCM |
| --- | --- | --- |
| `02` freeze-frame PIDs for frame `00` | `02` | `02 04 0C 0D 11 1F 33 42 49 67 6C` |
| `06` onboard monitor IDs | `01 02 21 35 3A 3C 3D 81 A2 A3 A4 A5` | No support bitmap reply during this probe |
| `09` vehicle information types | `02 04 06 08 0A 13 14 16 17 18 19` | `04 06 0A` |

These are capability lists. Freeze-frame support applies to frame `00` as reported during this probe. The `090A` payloads were read to confirm ECU names.

### Follow-up misfire monitor check

At 10:28 p.m. Eastern on 2026-11-23, the ECM repeated its final Mode 01 bitmap `04000000` at `01A0`. Direct `01A4`, `01C0`, and `01E0` reads returned `NO DATA`. The Mode 06 support bitmap at `06A0` was `78000000`, confirming cylinder monitors `A2` through `A5`.

The ECM at `18DAF110` returned both tests for each of the four cylinder monitors. Test `0C`, the last/current driving-cycle count, read zero for cylinders 1 through 4. Test `0B`, the weighted average over the last ten driving cycles, also read zero for each cylinder. Both records used count scaling ID `24`. [Mode 06 test definitions](https://gsi.ext.gm.com/gmspo/mode6/pdf/GM%20CAN%20mode%20%2406%20data%20final_dm.pdf)

## Passive CAN and Honda TCM reads

On 2026-11-23, the parked Civic idled during two silent raw CAN captures on OBD-II pins 6 and 14 at 500 kbit/s. The OBDLink EX used `STCMM 0` and `STM`. A six-second capture with `STP 31` and an eight-second capture with `STP 32` and explicit pass filters for both CAN ID widths each captured zero frames. Both modules answered separate ISO 15765-4 queries before or after monitoring. Engine speed was approximately 745–756 rpm and vehicle speed was zero. The result applies to the diagnostic connector at idle. [OBDLink programming manual](https://www.scantool.net/scantool/downloads/682/obdlink_frpm_f.pdf) · [Honda diagnostic connector wiring](https://honcivic.automotive-manuals.com/techinfo/html/en/civic-fc-fk/T010729.html)

The TCM at `18DAF11E` returned complete 39-byte ISO-TP application responses to physical read requests `22 2301` and `22 2322` sent to `18DA1EF1`. In two `2301` responses, the OBDb mappings yielded 752 and 750 rpm, 29 and 28 kPa manifold pressure, and 101 kPa barometric pressure. Separate standard reads corroborated the RPM range and returned 29 kPa manifold and 101 kPa barometric pressure. The candidate CVT fluid temperature byte advanced from `78` to `79` hex, or 80 to 81 °C using the OBDb offset. The adjacent candidate sensor voltage byte fell from `2B` to `2A` hex. Temperature scaling still needs comparison against Honda Diagnostic System data. The `2322` candidate secondary shaft speeds were zero and the candidate turbine speed was 737 rpm at idle. Pulley ratio remains unverified. [OBDb capture analysis and field mappings](https://github.com/OBDb/Honda-Civic/pull/1912)
