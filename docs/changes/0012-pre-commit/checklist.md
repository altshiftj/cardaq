# Verification

- [x] Installed the Git hook and both pinned environments on Windows. Validated the configuration with the locked runner.
- [x] Ran all 11 hooks on a disposable Git snapshot of 104 tracked and untracked project files, including the new viewer and health packages.
- [x] Tested real commits. Malformed JSON, an undefined Python name, trailing spaces and a file over 1 MiB blocked the commit. After repair and staging, Git accepted it.
- [x] Verified the lockfile and passed all 72 unittest tests. Built the source distribution and wheel and confirmed the wheel lists only pyserial as a runtime dependency.
