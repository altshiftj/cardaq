# Derived signal report

The viewer plots the sparse readings already decoded by CarDAQ. The work and home recordings contain the inputs for comparing the CVT pulley speeds, torque converter speed, acceleration, and warm-up. Several CVT inputs still have provisional identities or scales.

The driver used Drive on the way to work and changed from Drive to Sport early on the way home. The byte at zero-based data offset 23 of reply `62 23 22` was `0x70` or `0x78` for 861 consecutive replies from 1:14.672 into the home capture to the approach to the grocery stop. Those values were absent from the work drive and the home drive after restart. A stationary sweep with independently noted shifter positions can test whether this is a selector field or related status.

The existing CSVs preserve the raw replies, so the viewer can extract the byte and calculate the derived signals from both old and future recordings. The grocery interruption establishes a real test case for avoiding derivatives across missing data.
