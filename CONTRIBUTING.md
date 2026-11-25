# Contributing to CarDAQ

## Set up and check a change

Run these commands in the repository root with uv and Python 3.11 or later.

```sh
uv sync --locked
uv run --locked pre-commit install
uv run --locked python -m unittest discover -s tests -v
uv build
```

Install the Git hook once per clone. On each commit it checks the staged files. Ruff fixes safe Python lint issues and sorts imports. Other hooks trim whitespace, check file endings, parse JSON/TOML/YAML, and catch conflict markers, case-colliding filenames, recognizable private keys, and files larger than 1 MiB. Changes to the dependency files also run `uv lock --check`.

If a hook edits a file, review the diff, stage the intended changes, and retry the commit. If you changed dependencies, regenerate and stage `uv.lock` along with `pyproject.toml`. To run the same checks as CI on every tracked file, use `uv run --locked pre-commit run --all-files --show-diff-on-failure`. The first run downloads the pinned hooks. The full test suite and package build run separately in CI.
