# Drive viewer report

CarDAQ records one diagnostic response per CSV row. Decoded metrics are sparse, use different polling rates, and include some provisional Honda CVT readings. The recorder remains active through key-off and transport interruptions.

The November 24 commute captures use the same schema. They have decoded samples through 25:36 on the way to work and 31:56 on the way home. The home speed stream has a gap of about eight minutes. The raw log durations include time well past the last reading.

A local comparison page should plot each metric against elapsed capture time using the observed samples. It should show gaps, identify provisional signals, and carry both drives in a file that opens directly in a browser.
