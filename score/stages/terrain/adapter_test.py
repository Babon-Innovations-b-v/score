"""The terrain adapter's own checks, with no spend: an outdoor place's detail areas come from its ground plan alone
and land as prop-route rows, each one not landed is a missing hole of the prop route, and the join cuts the code ground
under a piece, seats the piece's rim into it, keeps the code ground where no piece was made and finds a gap at a seam.

Run: .venv/bin/python score/stages/terrain/adapter_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np
from pxr import Usd, UsdGeom

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
from score.stages.terrain import areas, gates, join, needs, outside, sight  # noqa: E402


def test_the_wreck_s_areas_are_its_plan_s_craters_in_its_patch():
    found = areas.detail_areas("wreck", REPO / "data")
    craters = [crater["name"] for crater in json.loads((REPO / "data/ground/plan/moon.json").read_text())["craters"]]
    assert found and all(area["kind"] == "crater" and area["landform"].split(" ")[1] in craters for area in found)
    assert all(area["size"][0] > 0 and area["size"][1] > 0 for area in found), found
    assert "craters, rough regolith" in found[0]["words"]  # the concept's ground element, read from the plan
    assert areas.detail_areas("hangar", REPO / "data") == []  # its patch reaches no landform of its plan


def test_areas_land_as_prop_route_rows_and_until_then_are_missing_holes():
    found = areas.detail_areas("wreck", REPO / "data")
    inventory, props, surfaces = areas.landed({"rows": [{"id": "aft_section"}]}, {"objects": {}},
                                              {"takes": {}, "bake": {"models": {}}}, "wreck", found)
    rows = {row["id"]: row for row in inventory["rows"]}
    first = found[0]["id"]
    assert rows[first]["kind"] == "generate" and rows[first]["anchor"] == "ground" and rows[first]["area"], rows[first]
    assert props["objects"][first] == {"route": "prop", "take": f"{first}-g1"}
    assert surfaces["bake"]["models"][first] == f"{first}-g1" and f"{first}-g1" in surfaces["takes"]
    holes = needs.holes("wreck", REPO / "data")
    assert len(holes) == len(found) and all(hole["rule"] == "missing" for hole in holes), holes
    assert holes[0]["work"] == "prop data for wreck: data/props/wreck.json" and holes[0]["node"] is None, holes[0]


def flat_ground(folder, place, side=40.0, step=1.0):
    """A terrain-like output: <ground>/places/<place>.usdc with a flat grid under /<place>/Outside/near."""
    path = folder / "moon/places" / f"{place}.usdc"
    path.parent.mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.Scope.Define(stage, f"/{place}/Outside")
    axis = np.arange(-side / 2, side / 2 + step, step)
    grid_x, grid_z = np.meshgrid(axis, axis)
    points = np.column_stack([grid_x.reshape(-1), np.zeros(grid_x.size), grid_z.reshape(-1)])
    columns = len(axis)
    corner = (np.arange(columns - 1)[:, None] * columns + np.arange(columns - 1)[None, :]).reshape(-1)
    triangles = np.concatenate([np.column_stack([corner, corner + columns, corner + 1]),
                                np.column_stack([corner + 1, corner + columns, corner + columns + 1])])
    outside.write_mesh(stage, f"/{place}/Outside/near", points, triangles, "ground")
    stage.GetRootLayer().Save()
    return path


def test_the_join_cuts_under_a_piece_and_seats_its_rim_into_the_ground():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        stage = Usd.Stage.Open(str(flat_ground(root, "yard")))
        mesh = join.ground_meshes(stage, "yard")[0]
        before = len(mesh.GetFaceVertexCountsAttr().Get())
        cut = join.cut_mesh(mesh, np.array([0.0, 0.0]), np.array([5.0, 5.0]))
        assert cut > 0 and len(mesh.GetFaceVertexCountsAttr().Get()) == before - cut
        bowl = np.array([[x, -1.0 + 0.05 * (x * x + z * z), z] for x in np.linspace(-5, 5, 11)
                         for z in np.linspace(-5, 5, 11)])  # a crater: rim up to 1.5 m over its foot
        rays = gates.caster(sight.gathered(Usd.Stage.Open(str(root / "moon/places/yard.usdc"))))
        points, lift = join.seated(bowl, np.array([3.0, -2.0]), np.array([5.0, 5.0]), rays)
        edge = points[join.rim(points, np.array([5.0, 5.0]))]
        assert lift < 0 and edge[:, 1].max() <= 1e-6, (lift, edge[:, 1].max())
        assert np.allclose(points[:, [0, 2]].mean(axis=0), [3.0, -2.0])
    finally:
        shutil.rmtree(root)


def test_with_no_piece_made_the_code_ground_stays_named_and_a_seam_gap_fails():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        terrain, out = root / "terrain", root / "out"
        flat_ground(terrain, "yard")
        out.mkdir()
        inventory = root / "yard.json"
        inventory.write_text(json.dumps({"place": "yard", "rows": [
            {"id": "ground_crater_a", "size": [8.0, 8.0, 1.0], "at": [{"x": 0.0, "y": 0.0, "z": 0.0}],
             "area": {"landform": "crater A"}}]}))
        join.make({"inventory": inventory, "terrain": terrain}, out, 0, {})
        joined = json.loads((out / join.JOIN).read_text())
        assert joined["pieces"] == {} and "ground_crater_a" in joined["code ground"], joined
        verdict = join.judge_seam(out, {}, {})
        assert verdict.answer == checks.PASS and "left to the code ground" in verdict.reason, verdict
        stage = Usd.Stage.Open(str(out / "moon/places/yard.usdc"))
        join.cut_mesh(join.ground_meshes(stage, "yard")[0], np.array([0.0, 0.0]), np.array([10.0, 10.0]))
        stage.GetRootLayer().Save()
        (out / join.JOIN).write_text(json.dumps({**joined, "pieces": {"ground_crater_a": {
            "middle": [0.0, 0.0], "half": [4.0, 4.0]}}}))
        verdict = join.judge_seam(out, {}, {})
        assert verdict.answer == checks.FAIL and verdict.measures["gaps"] > 0, verdict  # cut wider than the piece
    finally:
        shutil.rmtree(root)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
