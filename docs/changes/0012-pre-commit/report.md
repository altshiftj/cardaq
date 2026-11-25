# Contribution checks

CarDAQ uses uv for its Python environment and unittest for offline tests. CI already builds and tests the installed wheel on Windows and Linux. Contributors currently get no feedback from Git about malformed configuration files, accidental large files or Python lint errors before committing.

The workspace includes source files awaiting their first commit. Checking tracked paths alone would miss these files. Git already ignores the local vehicle captures and machine configuration.
