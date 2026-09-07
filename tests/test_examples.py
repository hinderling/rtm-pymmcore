"""Execute the example notebooks and the templates on the virtual microscope.

The templates ship with ``TODO`` cells that end in ``raise NotImplementedError``
so nobody can run them unfilled. Here every TODO cell is swapped for a
virtual-scope filler (keyed by its ``todo:<name>`` tag) and the notebook is
executed in a real kernel. Cells tagged ``gui`` (napari) are dropped. The
examples' ``parameters`` cell is overridden with small frame counts so the
whole file stays fast.

Requires the ``virtual-microscope`` and ``test`` extras.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import pytest

nbformat = pytest.importorskip("nbformat")
nbclient = pytest.importorskip("nbclient")
pytest.importorskip("virtual_microscope")

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
TEMPLATES = ROOT / "templates"
README = ROOT / "README.md"

SKIP_TAGS = {"gui"}
TODO_PREFIX = "todo:"
TIMEOUT_S = 600

VIRTUAL_SCOPE = """
from virtual_microscope.backends.optogenetic import setup_optogenetic
from faro.microscope.simulation import UniMMCoreSimulation
core, sim = setup_optogenetic(n_cells=15)
mic = UniMMCoreSimulation(mmc=core)
mic.init_scope()
"""

# Fillers for every TODO cell of every template. A template TODO tag without
# a filler here fails the test, and so does a filler without a matching tag.
FILLERS: dict[str, dict[str, str]] = {
    "live_experiment/experiment.ipynb": {
        "todo:microscope": VIRTUAL_SCOPE,
        "todo:settings": """
import tempfile
STORAGE_ROOT = tempfile.mkdtemp(prefix="faro_template_live_")
EXPERIMENT_NAME = "test_run"
INTERVAL_S = 0.3
N_BASELINE = 2
N_STIM = 3
N_RECOVERY = 2
IMAGING_CHANNELS = [{"config": "phase-contrast", "exposure": 50}]
STIM_CHANNEL = {"config": "phase-contrast", "exposure": 50}
""",
        "todo:segmentation": """
from faro.segmentation.base import OtsuSegmentator
segmentators = [
    SegmentationMethod(name="labels", segmentation_class=OtsuSegmentator(), use_channel=0, save_tracked=True),
]
""",
        "todo:features": """
from faro.feature_extraction.simple import SimpleFE
feature_extractor = SimpleFE("labels")
""",
        "todo:stimulation": """
from faro.stimulation.base import StimWholeFOV
stimulator = StimWholeFOV()
""",
        "todo:positions": """
fov_positions = utils.generate_fov_positions_from_list(mic, [{"x": 0.0, "y": 0.0, "z": 0.0}])
""",
    },
    "reanalysis/reanalysis.ipynb": {
        # SRC_PATH is injected by the test after it has produced a source run.
        "todo:paths": """
SRC_PATH = os.environ["FARO_TEST_SRC_PATH"]
OUT_PATH = SRC_PATH + "_reanalysis"
""",
        "todo:pipeline": """
from faro.segmentation.base import OtsuSegmentator
from faro.feature_extraction.simple import SimpleFE
from faro.tracking.trackpy import TrackerTrackpy
segmentators = [
    SegmentationMethod(name="labels", segmentation_class=OtsuSegmentator(), use_channel=0, save_tracked=True),
]
feature_extractor = SimpleFE("labels")
tracker = TrackerTrackpy(search_range=30)
stimulator = None
USE_OLD_SEGMENTATIONS = False
USE_OLD_STIM_MASKS = True
""",
    },
}

EXAMPLE_PARAMS = {
    "live_experiment.ipynb": """
INTERVAL_S = 0.3
N_BASELINE = 2
N_STIM = 4
N_RECOVERY = 2
N_EXTRA = 2
STIM_FRACTION = 0.2
""",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _tags(cell) -> list[str]:
    return list(cell.get("metadata", {}).get("tags", []))


def _todo_tag(cell) -> str | None:
    for tag in _tags(cell):
        if tag.startswith(TODO_PREFIX):
            return tag
    return None


def _prepare(nb_path: Path, fillers: dict[str, str], params: str | None):
    """Return a copy of the notebook with TODO cells filled and gui cells dropped."""
    nb = nbformat.read(nb_path, as_version=4)
    cells = []
    seen: set[str] = set()
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        tags = set(_tags(cell))
        if tags & SKIP_TAGS:
            continue
        todo = _todo_tag(cell)
        if todo is not None:
            assert todo in fillers, f"{nb_path.name}: no filler for {todo}"
            seen.add(todo)
            cell.source = fillers[todo]
        elif "parameters" in tags and params is not None:
            cell.source = cell.source + "\n" + params
        # magics do not survive a plain kernel run without IPython extensions
        cell.source = "\n".join(
            line for line in cell.source.splitlines() if not line.lstrip().startswith("%")
        )
        cells.append(cell)
    missing = set(fillers) - seen
    assert not missing, f"{nb_path.name}: fillers without a TODO cell: {sorted(missing)}"
    nb.cells = cells
    return nb


def _execute(nb, cwd: Path) -> None:
    env_backup = os.environ.get("MPLBACKEND")
    os.environ["MPLBACKEND"] = "Agg"
    try:
        client = nbclient.NotebookClient(
            nb,
            timeout=TIMEOUT_S,
            kernel_name="python3",
            resources={"metadata": {"path": str(cwd)}},
        )
        # nbclient's DEBUG records do not survive pytest's log capture
        client.log.setLevel(logging.WARNING)
        client.execute()
    finally:
        if env_backup is None:
            os.environ.pop("MPLBACKEND", None)
        else:
            os.environ["MPLBACKEND"] = env_backup


def _readme_anchors() -> set[str]:
    anchors = set()
    for line in README.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(#{1,6})\s+(.*?)\s*$", line)
        if not m:
            continue
        title = re.sub(r"`", "", m.group(2))
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        anchors.add(slug)
    return anchors


def _notebook_readme_links(nb_path: Path) -> set[str]:
    text = nb_path.read_text(encoding="utf-8")
    return set(re.findall(r"README\.md#([\w\-]+)", text))


def _all_notebooks() -> list[Path]:
    return sorted(EXAMPLES.rglob("*.ipynb")) + sorted(TEMPLATES.rglob("*.ipynb"))


# ---------------------------------------------------------------------------
# structure checks (fast, no kernel)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("nb_path", _all_notebooks(), ids=lambda p: p.name)
def test_readme_anchors_exist(nb_path: Path):
    anchors = _readme_anchors()
    missing = _notebook_readme_links(nb_path) - anchors
    assert not missing, f"{nb_path.name} links to README sections that do not exist: {sorted(missing)}"


@pytest.mark.parametrize("rel", sorted(FILLERS), ids=lambda r: r.split("/")[0])
def test_template_todo_cells_raise(rel: str):
    nb = nbformat.read(TEMPLATES / rel, as_version=4)
    todo_cells = [c for c in nb.cells if c.cell_type == "code" and _todo_tag(c)]
    assert todo_cells, "template has no TODO cells"
    for cell in todo_cells:
        assert "raise NotImplementedError" in cell.source, (
            f"{rel}: TODO cell {_todo_tag(cell)} must end in raise NotImplementedError"
        )
    tags = {_todo_tag(c) for c in todo_cells}
    assert tags == set(FILLERS[rel]), f"{rel}: TODO tags {tags} != fillers {set(FILLERS[rel])}"


def test_template_folders_are_complete():
    assert (TEMPLATES / "README.md").exists(), "templates/README.md is missing"
    for folder in TEMPLATES.iterdir():
        if not folder.is_dir():
            continue
        assert (folder / "pyproject.toml").exists(), f"{folder.name}: missing pyproject.toml"
        assert list(folder.glob("*.ipynb")), f"{folder.name}: missing notebook"


# ---------------------------------------------------------------------------
# execution (kernel, virtual microscope)
# ---------------------------------------------------------------------------
@pytest.mark.examples
@pytest.mark.parametrize("name", ["live_experiment.ipynb"])
def test_example_runs(name: str):
    nb_path = EXAMPLES / name
    nb = _prepare(nb_path, fillers={}, params=EXAMPLE_PARAMS.get(name))
    _execute(nb, cwd=EXAMPLES)


@pytest.mark.examples
def test_live_template_runs():
    rel = "live_experiment/experiment.ipynb"
    nb = _prepare(TEMPLATES / rel, fillers=FILLERS[rel], params=None)
    _execute(nb, cwd=(TEMPLATES / rel).parent)


@pytest.mark.examples
def test_reanalysis_template_runs(tmp_dir):
    """Produce a small source run on the virtual scope, then re-analyse it."""
    src = _make_source_run(Path(tmp_dir) / "source")
    rel = "reanalysis/reanalysis.ipynb"
    nb = _prepare(TEMPLATES / rel, fillers=FILLERS[rel], params=None)
    previous = os.environ.get("FARO_TEST_SRC_PATH")
    os.environ["FARO_TEST_SRC_PATH"] = str(src)
    try:
        _execute(nb, cwd=(TEMPLATES / rel).parent)
    finally:
        if previous is None:
            os.environ.pop("FARO_TEST_SRC_PATH", None)
        else:
            os.environ["FARO_TEST_SRC_PATH"] = previous
    out = Path(str(src) + "_reanalysis")
    assert (out / "exp_data.parquet").exists()


def _make_source_run(path: Path) -> Path:
    from virtual_microscope.backends.optogenetic import setup_optogenetic

    from faro.core.controller import Controller
    from faro.core.data_structures import RTMSequence, SegmentationMethod
    from faro.core.pipeline import ImageProcessingPipeline
    from faro.core.writers import OmeZarrWriter
    from faro.feature_extraction.simple import SimpleFE
    from faro.microscope.simulation import UniMMCoreSimulation
    from faro.segmentation.base import OtsuSegmentator
    from faro.tracking.trackpy import TrackerTrackpy

    core, _ = setup_optogenetic(n_cells=15)
    mic = UniMMCoreSimulation(mmc=core)
    mic.init_scope()
    path = Path(path)
    pipeline = ImageProcessingPipeline(
        storage_path=str(path),
        segmentators=[
            SegmentationMethod("labels", OtsuSegmentator(), use_channel=0, save_tracked=True)
        ],
        feature_extractor=SimpleFE("labels"),
        tracker=TrackerTrackpy(search_range=30),
    )
    events = list(
        RTMSequence(
            time_plan={"interval": 0.3, "loops": 3},
            stage_positions=[{"x": 0.0, "y": 0.0, "z": 0.0}],
            channels=[{"config": "phase-contrast", "exposure": 50}],
        )
    )
    ctrl = Controller(mic, pipeline, writer=OmeZarrWriter(storage_path=str(path)))
    ctrl.run_experiment(events).wait()
    ctrl.finish_experiment()
    assert (path / "events.json").exists()
    return path
