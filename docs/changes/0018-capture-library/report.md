# Organize the local capture library

The local captures directory mixes original recordings, a clipped copy, imported logs, viewer reports, notes, health history, and synthetic data. Starting a recording requires inventing an output filename. The existing report notes bind to recording hashes, and the health manifest links to independent recordings by relative path.

Use date-based placement and automatic recording identifiers. Keep originals byte-for-byte, identify derived data and its inputs, and use machine-readable metadata to make the library easier to find and reuse locally. CarDAQ recordings can include routes, odometer readings, timestamps, and personal notes, so the library stays outside version control. [FAIR Guiding Principles](https://doi.org/10.1038/sdata.201618)
