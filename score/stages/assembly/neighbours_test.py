"""The neighbours stage stands each place its scene record shows in the place's assembly, read from its own output,
and its gate fails a shown place that resolves to nothing. Toy stages named as world 1's launch, square and far city,
whose record (the assembly's scene.json beside its stage) shows the square and the far city.

Run: .venv/bin/python score/stages/assembly/neighbours_test.py
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

# Scratch on disk under $PROPS_HOME/tmp, never /tmp (a RAM-backed tmpfs on the PC).
tempfile.tempdir = str(pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "tmp")
pathlib.Path(tempfile.tempdir).mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks  # noqa: E402
from score.stages import assembly, scene_record  # noqa: E402
from score.stages.assembly import neighbours  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]


def a_place(root, place, shows=(), ground_shows=()):
    """A place's stage as the assembly leaves it: a root over layers/ground.usdc (the terrain's, with the shown places
    the seed lacks) and layers/base.usda, its shown places referenced the seed's way (../../<other>/<other>.usda)."""
    from pxr import Usd, UsdGeom
    folder = root / place
    (folder / "layers").mkdir(parents=True)
    for layer, others in (("base.usda", shows), ("ground.usdc", ground_shows)):
        base = Usd.Stage.CreateNew(str(folder / "layers" / layer))
        UsdGeom.Xform.Define(base, f"/{place}/Objects/crate_1")
        for other in others:
            UsdGeom.Xform.Define(base, f"/{place}/Places/{other}").GetPrim().GetReferences().AddReference(
                f"../../{other}/{other}.usda")
        base.GetRootLayer().Save()
    stage = Usd.Stage.CreateNew(str(folder / f"{place}.usda"))
    stage.GetRootLayer().subLayerPaths.append("./layers/ground.usdc")
    stage.GetRootLayer().subLayerPaths.append("./layers/base.usda")
    stage.SetDefaultPrim(stage.GetPrimAtPath(f"/{place}"))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.GetRootLayer().Save()
    return folder


def judge(output):
    return neighbours.judge_neighbours(output, {}, None)


def test_the_launch_shows_the_square_and_the_far_city_from_their_own_outputs():
    """Fault (2026-10-12): the launch's accepted assembly showed Places/square and Places/far_city with no children,
    its references pointing at round-three seed files the store does not hold."""
    assert neighbours.record_of("gdoor") == {}  # a door's kit: no record row, no seed record
    for place in ("hangar", "hub", "garage"):  # a place without a record row reads its seed record
        if not scene_record.written(place):
            assert neighbours.record_of(place) == json.loads((REPO / f"data/scene/{place}.json").read_text())
    assert "far_city" in neighbours.shown("launch") and "far_city" not in neighbours.neighbours("launch")
    assert "seen far_city" in neighbours.files("launch")
    assert neighbours.applies("square") and not neighbours.applies("gdoor")
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        launch = a_place(root / "kept", "launch", ("square", "far_city"))
        (launch / assembly.RECORD).write_text(json.dumps({"places": [{"name": "square", "stage": "square"},
                                                                     {"name": "far_city", "stage": "far_city"}]}))
        inputs = {"assembly@square": a_place(root / "kept", "square"),
                  "seen far_city": a_place(root / "kept", "far_city")}
        shutil.move(str(launch), root / "alone")  # away from its neighbours, as the store keeps it
        alone = judge(root / "alone")
        assert alone.answer == checks.FAIL and alone.measures["faults"] == 4, alone
        assert any("resolves to no file" in finding for finding in alone.findings), alone.findings
        out = root / "out"
        out.mkdir()
        neighbours.make({**inputs, "assembly": root / "alone"}, out, 0, {})
        shutil.rmtree(root / "kept")
        verdict = judge(out)
        assert verdict.answer == checks.PASS and verdict.measures["shown"] == 2, verdict
    finally:
        shutil.rmtree(root)


def test_the_stairwell_shows_the_flat_its_terrain_added():
    """Fault (2026-10-15): the stairwell's Places/flat, which its seed lacks and the terrain's ground layer adds,
    kept its reference ../../flat/flat.usda: the stage pointed only the base layer's references at the copies."""
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        stairwell = a_place(root / "kept", "stairwell", ("street",), ("flat",))
        (stairwell / assembly.RECORD).write_text(json.dumps({"places": [{"name": "street", "stage": "street"},
                                                                        {"name": "flat", "stage": "flat"}]}))
        inputs = {"assembly": stairwell, "assembly@street": a_place(root / "kept", "street"),
                  "assembly@flat": a_place(root / "kept", "flat", ("stairwell",))}
        out = root / "out"
        out.mkdir()
        neighbours.make(inputs, out, 0, {})
        shutil.rmtree(root / "kept")
        verdict = judge(out)
        assert verdict.answer == checks.PASS and verdict.measures["shown"] == 2, verdict
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
