# Civic pilot capture report

The 60-second capture read all 44 advertised Mode 01 PIDs and two Honda transmission identifiers on the Civic through the OBDLink EX. It used a one-off serial script and converted the saved replies to CSV after the run. The same car has answered on COM5 at 115200 baud using ISO 15765-4 CAN with 29-bit IDs at 500 kbit/s. [PID inventory](../0002-pid-sweep/pid-inventory.md)

The pilot needs a local recorder that starts at key-on, keeps running through crank and the commute, and leaves a readable file after key-off or adapter loss. The capture must retain raw replies for later decoding, especially the Honda CVT fields whose scale or shaft identity still needs a reference. The 4 a.m. block heater makes the morning key-on coolant readings a heated baseline. Record the actual key-on time and outside temperature as context. [Honda temperature check](https://honcivic.automotive-manuals.com/techinfo/html/en/civic-fc-fk/T004808.html)

Use the known Civic read-only request profile and the existing serial adapter API. Write directly to a new CSV throughout the run, so exporting or stopping the recorder is unnecessary to read the data. Log outages explicitly and retry briefly interrupted connections. Validate normal completion, parked stop, ignition-off and USB loss in simulation. The trip and comparison against Honda i-HDS remain physical pilot work.
