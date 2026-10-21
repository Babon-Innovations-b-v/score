"""A place's bake job written from git (bake_job.py) through the bake's own entries (place_line.bake_entries), on toy
surface data and labelled takes in a folder of their own under $PROPS_HOME: an entry the data writes out taken as
written, a design's written without a turn turned by its take, and a model the data writes no entry for stopped by
name; and every place's bake declares no file under the work folder. No old job was ever committed (git log: no
job-chunky*.json), so none is compared.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/stages/surfaces/bake_job_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.stages.surfaces import place_line, surface_data  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

import bake_job  # noqa: E402  (place_line puts its folder and tools/props/library on the path)
import library  # noqa: E402
import place_route  # noqa: E402
import route  # noqa: E402

# The people line's bake takes its specs and wear from the repository's library by place; every old material was
# retired (2026-10-21), so these entry checks give it a stand-in library's (no surface: the entries are the subject).
WEAR = (0.4, 0.3)
bake_job.specs_of = lambda library_name: {}
library.wear_of = lambda place_id, *_: WEAR


def a_folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(prefix="bake-job-", dir=PROPS_HOME / "store-tests"))


def written(folder, name, record):
    path = folder / f"{name}.json"
    path.write_text(json.dumps(record))
    return path


def a_box_take(folder, take, extents):
    """A labelled take of one part: a box of `extents` (x, y, z) written as a .ply, as labels.py writes parts."""
    import trimesh
    labelled = folder / "labelled" / take
    labelled.mkdir(parents=True)
    trimesh.creation.box(extents=extents).export(labelled / "hull_white.ply")
    return labelled


def test_an_entry_the_data_writes_out_is_taken_as_written_and_a_model_with_none_stops_the_bake():
    folder = a_folder()
    try:
        written_out = {"base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [0.5, 0.9, 1.1], "faces": 19000, "foot": 0.0}
        surfaces = written(folder, "surfaces", {"place": "hangar", "library": "hangar", "bake": {
            "models": {"pedestal_1": "pedestal-t1", "lost_1": "lost-t1"}, "entries": {"pedestal_1": written_out}}})
        inputs = {"surfaces": surfaces}
        job, (entry,) = place_line.bake_entries(inputs, {"pedestal-t1": folder / "pedestal-t1"})
        assert {key: entry[key] for key in written_out} == written_out and entry["regions"] == []
        assert (job["wear"], job["dirt"]) == WEAR and job["density"] == route.NEAR
        assert job["faces"] == route.CHUNKY_FACES
        try:
            place_line.bake_entries(inputs, {"pedestal-t1": folder / "p", "lost-t1": folder / "l"})
            raise AssertionError("a model with no entry was baked")
        except bake_job.NoEntry as refused:
            assert "no entry for lost_1" in str(refused), refused
    finally:
        shutil.rmtree(folder)


def test_a_design_entry_written_without_a_turn_is_turned_by_its_take_s_measured_footprint():
    """A design's take has no hand-set turn: of 0 and 90 degrees, the one whose labelled model's footprint fits its
    row's wide and deep. A take built long along z for a row wide along x is turned a quarter round; one already wide
    along x is not; with no take yet the bake is not refused (it measures once the take is there)."""
    folder = a_folder()
    try:
        labelled = a_box_take(folder, "bench-t1", (0.5, 0.9, 2.0))
        design = {"size": [2.0, 0.9, 0.5], "faces": 19000, "foot": 0.0}
        surfaces = written(folder, "surfaces", {"place": "hub", "library": "hub", "bake": {
            "models": {"bench_1": "bench-t1"}, "entries": {"bench_1": design}}})
        _, (entry,) = place_line.bake_entries({"surfaces": surfaces}, {"bench-t1": labelled})
        assert entry["base"] == bake_job.TURNS[90] and place_route.yaw_of(entry["base"]) == 90.0, entry
        assert bake_job.measured_turn(labelled, [0.5, 0.9, 2.0]) == bake_job.TURNS[0]
        assert bake_job.refusal("bench_1", design) is None
        assert "the data writes none" in bake_job.refusal("lost_1", None)
    finally:
        shutil.rmtree(folder)


def test_every_place_s_bake_is_written_from_git_or_blocks_on_a_named_entry():
    """Every place's bake declares no file under the work folder; a model no entry can be written for is declared
    as a file that is never there, naming it (the old kinds' details retired on 2026-10-21, so an old place's laid
    kit models are each named so)."""
    for path in sorted(surface_data.FOLDER.glob("*.json")):
        declared = surface_data.bake_files(path.stem)
        # the work folder ({seeds}, {home}/work); a designed place's surface data, {home}/design, prepare writes again
        assert not any("{home}/work" in pattern or "{seeds}" in pattern for pattern in declared.values()), path.stem
        assert "library bake" in declared, path.stem
        # the old kinds' details and composites retired (2026-10-21): no bake waits on them by name
        assert not {"details", "composites"} & set(declared), path.stem


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
