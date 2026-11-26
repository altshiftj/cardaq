# Timing a cylinder counter change

The recorder saves the send and reply times for each cylinder's Mode 06 request. The health report already extracts the current-cycle count (test 0C) and shows when a different value first appeared. The drive viewer needs the preceding valid reply as well to show how precisely we can place a change.

A single reply can report several new counts. The first reply can also contain a value carried over from an earlier drive, and later replies can show a decrease. Treating every nonzero reply as a firing event would count the same observation many times.
