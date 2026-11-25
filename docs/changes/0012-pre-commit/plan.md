# Plan

1. Lock the hook runner as a development dependency and pin the hook implementations.
2. Check staged text, configuration files, Python code and changes to the uv dependency files. Follow the repository’s existing import layout.
3. Run the same hooks on pull requests and document installation and repair commands.
4. Exercise successful and rejected commits on a disposable copy of the intended tree and run the existing offline tests.
