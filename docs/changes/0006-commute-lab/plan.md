# Commute lab plan

1. Give derived signals a dedicated roadmap organized around trip comparison, CVT behavior, engine and fuel, thermal and condition trends, and future instrumentation.
2. Decode the supported ECM replies already in saved recordings. Keep acquisition and the source CSV schema independent of offline analysis.
3. Add gap-aware trip totals and rolling series, estimated fuel-cut coast, air charge, CVT changes, time-based warm-up metrics, and sample-quality diagnostics.
4. Add a speed-binned operating map with load filtering and per-drive summaries. Expose distance and elapsed time views where the data permits.
5. Check parser, join, and integration edge cases. Regenerate both existing viewer pages, then verify the new controls in Chromium and check the cut home segment against the source.
