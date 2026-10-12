"""The worked example on world 1's real round-three stages, with no spend: the hangar's seed fails on its code-built
ship, the hangar door's has no drop run and answers unknown, neither place can complete, a second run makes nothing,
and a change to the door's kit reruns the door's assembly alone. Skipped, and says so, on a machine without the seeds.

The store is a folder of its own under $PROPS_HOME (never /tmp, never the framework's own store), removed at the end.

Run: .venv/bin/python score/stages/stages_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import checks, contracts, graph, review, stages  # noqa: E402
from score.store import PROPS_HOME, Store, file_hash  # noqa: E402

SEEDS = PROPS_HOME / "work"
PLACES = ("hangar", "hdoor")
DATA = ("kit", "inventory", "library/fittings.json", "checks")


def world_data_copy(root):
    """The world files the assembly stage reads, copied so the test may change one."""
    for part in DATA:
        source, target = REPO / "data" / part, root / part
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if source.is_dir() else shutil.copy2)(source, target)
    return root


def scenario(root):
    world = graph.World("world1", 3, {"data": str(world_data_copy(root / "data")), "seeds": str(SEEDS)})
    store = Store.in_folder(root / "store")
    # The worked example's own stages: terrain (a world node) spends and has its own test beside its module, so a
    # terrain that made no ground for these places stands in for it.
    return world, store, lambda: graph.Runner((NO_GROUND, stages.EFFECTS, stages.ASSEMBLY, stages.COMPLETE), world,
                                                 store)


def no_ground(inputs, out, seed, params):
    (out / "none").mkdir()


def made(output, inputs, evidence):
    return checks.Verdict("made", checks.PASS, "no ground made for these places")


NO_GROUND = graph.Stage("terrain", "world", no_ground,
                        contracts.Contract("grounds", 1, lambda folder: [], {"length": "metre", "up axis": "Y"}),
                        (checks.Check("made", made),))


def test_the_worked_example_on_world_1s_seeds():
    if not all((SEEDS / "usd-r3" / place / f"{place}.usda").exists() for place in PLACES):
        print("skipped: no round-three stages of the hangar and its door on this machine")
        return
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    root = pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))
    try:
        world, store, runner = scenario(root)
        first = runner().run(PLACES)
        assert first["assembly@hangar"] == "made: fail", first
        assert first["complete@hangar"].startswith("blocked: assembly@hangar answered fail: placeholders: 12 meshes "
                                                   "stand in for made pieces; resting: no evidence"), first
        assert first["assembly@hdoor"] == "made: unknown", first
        assert first["complete@hdoor"] == ("blocked: assembly@hdoor answered unknown: resting: no evidence: a drop "
                                           "run (settle.py --dry-run) for this output is missing"), first

        assert set(runner().run(PLACES).values()) == {"fresh", *(first[f"complete@{place}"] for place in PLACES)}

        kit = pathlib.Path(world.roots["data"]) / "kit/hdoor.json"
        kit.write_text(json.dumps({**json.loads(kit.read_text()), "note": "a creator's edit"}, indent=1))
        assert runner().status(PLACES)["assembly@hdoor"] == "to run: kit changed"
        third = runner().run(PLACES)
        assert third["assembly@hdoor"] == "made: unknown" and third["assembly@hangar"] == "fresh", third
        assert len(store.records("assembly@hdoor")) == 2 and len(store.records("assembly@hangar")) == 1

        page = review.page(store, "assembly@hangar").read_text()
        assert "Unverified seed." in page and "/hangar/Structure/ship" in page and "It cannot be accepted" in page
        why = runner().why("assembly@hangar")[0]
        assert why.startswith("assembly@hangar: output") and "fail, not accepted" in why and "seed " in why
    finally:
        shutil.rmtree(root)


def terrain_code_after_editing(edited):
    """Terrain's code version as if the repository file `edited` had changed (its hash moved; nothing written)."""
    stage = stages.TERRAIN
    functions = [stage.make, stage.contract.faults, *(check.judge for check in stage.checks)]
    return graph._code.code_version(functions, lambda path: file_hash(path) + ("+edit" if path == REPO / edited
                                                                               else ""))


def test_terrain_s_code_version_moves_with_its_own_code_only():
    """Another line's edits to the runner, the stage table or another stage's module leave terrain's key alone (they
    re-made terrain under the effects line, 2026-10-12); its own module and what it imports move it."""
    before = terrain_code_after_editing("nothing")
    for unrelated in ("score/stages/__init__.py", "score/graph/__init__.py", "score/review/__init__.py",
                      "score/adapters/compute/__init__.py", "score/stages/effects/__init__.py",
                      "score/stages/assembly/__init__.py", "score/stages/surfaces/__init__.py"):
        assert terrain_code_after_editing(unrelated) == before, unrelated
    for own in ("score/stages/terrain/__init__.py", "score/stages/terrain/landforms.py", "tools/usd/ground.py",
                "tools/props/cloud/depth.py"):
        assert terrain_code_after_editing(own) != before, own


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
