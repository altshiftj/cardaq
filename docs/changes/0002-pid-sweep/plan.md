# Standard OBD-II PID sweep plan

1. Add `cardaq sweep` using the existing serial settings. Confirm the adapter reports an ISO 15765-4 CAN protocol and preserve CAN response IDs. Temporarily enable headers when the initial replies show that they are off, and restore the format when the session ends.
2. Discover support starting with `0100`. Walk subsequent bitmap ranges only when at least one responder advertises them. Track each CAN response ID independently and report a missing advertised bitmap as an error.
3. Add optional `--sample` to issue one Mode 01 request for each distinct advertised data PID. Preserve the raw replies with CAN headers. Decode `0167` as coolant temperatures in Celsius and Fahrenheit when the corresponding sensor support flags are set.
4. Verify the exact wire commands and timeout handling with simulated serial exchanges. Run discovery and sampling against the Civic when the port is free. Compare the available ECU counts and coolant channels with the OBDwiz screenshots.

The sweep uses the adapter's existing protocol configuration and documented standard current-data requests. Continuous logging, manufacturer-specific requests, and mapping CAN IDs to ECU names are later work.
