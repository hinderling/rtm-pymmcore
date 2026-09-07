# Live experiment template

A copy-and-fill notebook for a feedback (or plain timelapse) experiment on a
real microscope. Every step is explained in the
[live experiment example](../../02_live_experiment.ipynb), which runs the same
structure on a virtual microscope.

## Start a new experiment

1. Copy this folder into your experiments repository and rename it, for
   example `2026-01-01_erk_pulses`.
2. In `pyproject.toml`, set `name` and pin faro (see below).
3. Open a terminal in the folder and run `uv sync`.
4. Open `experiment.ipynb`, select the `.venv` kernel, and work through the
   cells marked **TODO**. Each one ends with a `raise` line that you delete
   once the cell is filled in.

`uv sync` creates a `.venv` folder next to the notebook with faro and all its
dependencies. Never `pip install` into it by hand; use the commands below so
`pyproject.toml` and `uv.lock` stay in sync.

## uv in five commands

| Task | Command |
|------|---------|
| Create or update the environment | `uv sync` |
| Start Jupyter in this environment | `uv run --no-sync jupyter lab` |
| Run a script in this environment | `uv run --no-sync python my_script.py` |
| Add a package | `uv add <name>` |
| Re-resolve faro after changing its pin | `uv lock --upgrade-package faro` then `uv sync` |

In VS Code, pick the interpreter `.venv/Scripts/python.exe` (Windows) or
`.venv/bin/python` (Linux, macOS) as the notebook kernel.

## Pinning faro

`pyproject.toml` starts with faro on `branch = "main"`, so every `uv sync`
may pull newer code. Before the experiment goes to the scope, pin it to the
exact faro commit you tested with:

1. Find the commit: `git -C <path to faro checkout> rev-parse HEAD`.
2. In `pyproject.toml`, replace the `branch = "main"` line with the
   `rev = "..."` line and paste the commit hash.
3. Run `uv lock --upgrade-package faro` and `uv sync`.
4. Commit `pyproject.toml` and `uv.lock` together.

`uv.lock` records the exact version of every package, not only faro. With it
in the repository, `uv sync` rebuilds the same environment on any machine.

## Moving to a newer faro

Change the `rev` hash, run `uv lock --upgrade-package faro` and `uv sync`,
rerun the notebook, and fix what changed. Commit the two files once it works.
Older experiments keep their own pins and are not affected.

## Working on faro itself

To run this experiment against a local faro checkout, switch the source in
`pyproject.toml` to the `path = ...` line (adjust the relative path), then
`uv sync`. Code edits in the checkout are picked up immediately. Switch back
to a `rev` pin and re-lock before the experiment goes dormant, so it stays
reproducible.

## When things look stale

`uv sync` again. If faro was updated in place, `uv sync --reinstall-package faro`.
