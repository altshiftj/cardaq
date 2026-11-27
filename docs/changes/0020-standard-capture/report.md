# First drive in a second vehicle

The USB OBDLink EX can already inventory standard Mode 01 data on 11-bit and 29-bit CAN. The recorder currently forces the Civic's 29-bit protocol, waits for its engine responder, and sends two Honda transmission queries. A successful standalone sweep therefore does not establish that the recorder can log another car. [Discovery](../../../src/cardaq/obd.py) · [Recorder](../../../src/cardaq/capture.py)

The first target is a 2021 Toyota RAV4 XLE AWD with the 2.5 L gasoline engine and eight-speed automatic. Its responders and advertised parameters need a parked hardware check. Preserve the raw replies so that a first drive is useful even for signals whose decoding comes later.
