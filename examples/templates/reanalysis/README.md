# Re-analysis template

A copy-and-fill notebook that re-processes an experiment already on disk with
new segmentation, tracking or feature extraction. No microscope needed.

## Start

1. Copy this folder into your experiments repository and rename it.
2. In `pyproject.toml`, set `name` and pin faro.
3. Run `uv sync` in the folder, open `reanalysis.ipynb` with the `.venv`
   kernel, and fill in the cells marked **TODO** (delete their `raise` line).

The [live experiment template README](../live_experiment/README.md) explains
`uv sync`, pinning faro to a commit, updating the pin and working against a
local faro checkout. The same rules apply here.

Raw images are never rewritten. The output folder gets hard links to the raw
data plus fresh labels, tracks and `exp_data.parquet`. See
[Re-analysis](https://github.com/pertzlab/faro/blob/main/README.md#re-analysis)
in the faro README for the parameters.
