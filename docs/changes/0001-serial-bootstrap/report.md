# Serial bootstrap report

## Starting state

On 2026-11-23, `git status --short --branch` showed an unborn `main` branch. The workspace contained only `.git`, with no project files or local workflow instructions. Python 3.12.7 was available on Windows.

The project brief reports that OBDwiz successfully read and plotted coolant temperature on the 2020 Honda Civic LX. At bootstrap, the adapter model, firmware, connection type, and host serial endpoint still needed to be recorded for CarDAQ. The physical check is recorded in the [checklist](checklist.md).

## Target

Create an installable Python project with a headless CLI and external serial settings. List the serial ports Windows exposes and retrieve hardware and firmware IDs from a user-selected OBDLink serial endpoint. Use the same Python interface on Linux when that environment is available.

## Findings and evidence

- Timecop's `docs/project/WORKFLOW.md` and its bootstrap RPC provide the local precedent for numbered change folders with separate report, plan, and checklist files. Gym Journal's bootstrap tracks software and physical checks independently. CarDAQ adopts the numbered folders and records the command and result for each completed verification step.
- CarDAQ uses uv for the project environment and dependency lock. The existing setuptools build configuration already supports editable installation through `uv sync`, and `uv.lock` records the resolved runtime dependencies. [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- pySerial exposes a common port enumeration and serial API across Windows and Linux. Port descriptions depend on operating system metadata. [pySerial port enumeration](https://pyserial.readthedocs.io/en/latest/tools.html#serial-tools-list-ports)
- `STDI` returns hardware identification and `STI` returns firmware identification. Commands end in carriage return and the adapter signals completion with `>`. A bare carriage return repeats the previous command. USB adapters default to 115200 baud and Bluetooth settings vary by device. [OBDLink programming manual, sections 6 and 8.4](https://www.scantool.net/scantool/downloads/682/obdlink_frpm_f.pdf)
- Some OBDLink connections use a custom BLE service. OBDwiz's success alone does not establish the availability of a serial endpoint for this adapter. [OBDLink CX adapter notes](https://support.obdlink.com/support/solutions/articles/43000746707-obdlink-cx-adapter-notes)

## Risks and open questions

- The physical check established the adapter model, firmware, USB transport, and working serial settings. Windows may assign a different COM port on a future connection.
- The generic Mode 01 coolant request returned `NO DATA` in the physical check. The OBDwiz screenshots later identified the coolant channels as SAE PID `67`. The next sweep tracks the responding CAN IDs. [PID sweep report](../0002-pid-sweep/report.md)
- A busy port, wrong baud rate, sleeping device, or disconnect can interrupt identification. Bound command I/O, report the failure clearly, and close the port on all paths.
