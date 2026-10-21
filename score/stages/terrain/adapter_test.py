"""The terrain adapter's own checks, with no spend: an outdoor place's detail areas come from its ground plan alone
and land as prop-route rows, each one not landed is a missing gap of the prop route, and the join cuts the code ground
under a piece, seats the piece's rim into it, keeps the code ground where no piece was made and finds a gap at a seam.

Run: .venv/bin/python score/stages/terrain/adapter_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np
import pytest
import trimesh
from pxr import Usd, UsdGeom, UsdShade

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))

from score import checks  # noqa: E402
from score.stages.surfaces import route_settings  # noqa: E402
from score.stages.terrain import areas, gates, join, needs, outside, sight  # noqa: E402
import score.stages.shapes_first.align as align  # noqa: E402
import export_test  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402
import score.stages.surfaces  # noqa: E402
from score.stages.surfaces import surface_data  # noqa: E402

# These tests hold their own hand-ins; a designed place's hand-in (the home's design/, which
# the sandbox links) is prepare_test.py's, so none is read here.
prop_data.DESIGN = surface_data.DESIGN = pathlib.Path(tempfile.mkdtemp()) / "no design"
score.stages.surfaces.data.DESIGN = surface_data.DESIGN  # the table's own import of it (bare `surface_data`)


def test_the_wreck_s_areas_are_its_plan_s_craters_in_its_patch():
    found = areas.detail_areas("wreck", REPO / "data")
    craters = [crater["name"] for crater in json.loads((REPO / "data/ground/plan/moon.json").read_text())["craters"]]
    assert found and all(area["kind"] == "crater" and area["landform"].split(" ")[1] in craters for area in found)
    assert all(area["size"][0] > 0 and area["size"][1] > 0 for area in found), found
    assert all(area["words"].startswith("ground detail: crater") for area in found), found  # its landform, named
    assert areas.detail_areas("hangar", REPO / "data") == []  # its patch reaches no landform of its plan


def test_areas_land_as_prop_route_rows_and_until_then_are_missing_gaps():
    found = areas.detail_areas("wreck", REPO / "data")
    inventory, props, surfaces = areas.landed({"rows": [{"id": "aft_section"}]}, {"objects": {}},
                                              {"takes": {}, "bake": {"models": {}}}, "wreck", found)
    rows = {row["id"]: row for row in inventory["rows"]}
    first = found[0]["id"]
    assert rows[first]["kind"] == "generate" and rows[first]["anchor"] == "ground" and rows[first]["area"], rows[first]
    assert props["objects"][first] == {"route": "prop", "take": f"{first}-g1", "layer": "terrain"}
    assert surfaces["bake"]["models"][first] == f"{first}-g1" and f"{first}-g1" in surfaces["takes"]
    gaps = needs.gaps("wreck", REPO / "data")
    assert len(gaps) == len(found) and all(gap["rule"] == "missing" for gap in gaps), gaps
    assert gaps[0]["work"] == "prop data for wreck: its design hand-in (prepare)" and gaps[0]["node"] is None, gaps[0]


def registered(root, rough_model, floor):
    """A rough-align output of a rough model (a trimesh) registered onto a plan's floor."""
    rough, plan, out = root / "rough", root / "plan", root / "aligned"
    for folder in (rough, plan, out):
        folder.mkdir()
    rough_model.export(rough / "rough.glb")
    (rough / "rough.json").write_text(json.dumps({"take": "wreck-rough-0"}))
    (plan / "plan.json").write_text(json.dumps({"place": "wreck", "floor": floor, "floor_height": 0.0,
                                                "walls": {"high": None}}))
    align.make({"rough-model": rough, "plan": plan}, out, 0, {})
    return out


def bowl(half=4.0, steps=17, depth=0.1):
    """A crater-like ground: a grid from -half to half across and along, its height depth times the square of the
    distance from its middle."""
    axis = np.linspace(-half, half, steps)
    grid_x, grid_z = np.meshgrid(axis, axis)
    points = np.column_stack([grid_x.reshape(-1), depth * (grid_x ** 2 + grid_z ** 2).reshape(-1), grid_z.reshape(-1)])
    corner = (np.arange(steps - 1)[:, None] * steps + np.arange(steps - 1)[None, :]).reshape(-1)
    triangles = np.concatenate([np.column_stack([corner, corner + steps, corner + 1]),
                                np.column_stack([corner + 1, corner + steps, corner + steps + 1])])
    return trimesh.Trimesh(points, triangles, process=False)


def nearest_reading(root, rough_model):
    """The nearest wreck area's reading over a rough model registered over that area, and the areas read over it."""
    nearest = areas.detail_areas("wreck", REPO / "data")[0]
    middle, half = np.array(nearest["at"])[[0, 2]], np.array(nearest["size"][:2]) / 2
    floor = [list(middle - half), list(middle + half)]  # the rough model registered over the nearest area
    rough = areas.rough_points(registered(root, rough_model, floor))
    found = {area["id"]: area for area in areas.detail_areas("wreck", REPO / "data", rough)}
    return nearest, middle, rough, found


def test_areas_are_read_over_the_registered_rough_model():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        nearest, middle, rough, found = nearest_reading(root, bowl())
        span = rough[:, [0, 2]].min(axis=0), rough[:, [0, 2]].max(axis=0)  # in the place's frame, by its matrix
        assert np.allclose((span[0] + span[1]) / 2, middle, atol=1e-3)
        reading = found[nearest["id"]]["rough"]
        assert reading["share"] > 0.9 and reading["relief"] > 0, reading
        assert "the concept's rough model shows" in found[nearest["id"]]["words"]
        assert found["ground_crater_e"]["rough"] == {"share": 0.0, "relief": None}  # 70 m off: the plan's alone
        assert "rough model" not in found["ground_crater_e"]["words"]
        row = areas.inventory_rows("wreck", [found[nearest["id"]]])[0]
        assert row["area"]["rough"] == reading
    finally:
        shutil.rmtree(root)


def test_a_hull_standing_over_an_area_is_no_relief():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        tall = trimesh.creation.box(bounds=[(0.0, 0.0, 0.0), (2.0, 5.0, 2.0)])  # a hull on flat ground
        nearest, _, rough, found = nearest_reading(root, tall)
        reading = found[nearest["id"]]["rough"]
        assert np.ptp(rough[:, 1]) > 1.0 and reading["share"] > 0.9, (np.ptp(rough[:, 1]), reading)
        assert reading["relief"] < 0.01 * np.ptp(rough[:, 1]), reading  # its ground side, not its height
    finally:
        shutil.rmtree(root)


def test_an_unregistered_rough_model_lands_no_areas():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        out = root / "aligned"
        out.mkdir()
        (out / align.REGISTRATION).write_text(json.dumps({"place": "wreck", "unregistrable": ["no triangles"]}))
        with pytest.raises(ValueError, match="not registered"):
            areas.write("wreck", out, root / "data")
    finally:
        shutil.rmtree(root)


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
        terrain, out, split, likeness = root / "terrain", root / "out", root / "split", root / "likeness"
        flat_ground(terrain, "yard")
        for folder in (out, split, likeness):
            folder.mkdir()
        inventory = root / "yard.json"
        inventory.write_text(json.dumps({"place": "yard", "rows": [
            {"id": "ground_crater_a", "size": [8.0, 8.0, 1.0], "at": [{"x": 0.0, "y": 0.0, "z": 0.0}],
             "area": {"landform": "crater A"}},
            {"id": "ground_crater_b", "size": [4.0, 4.0, 1.0], "at": [{"x": 9.0, "y": 0.0, "z": 9.0}],
             "area": {"landform": "crater B"}}]}))
        (split / "rows.json").write_text(json.dumps({"rows": [
            {"id": "ground_crater_a", "take": "ground_crater_a-g1", "layer": "terrain"},
            {"id": "ground_crater_b", "take": "ground_crater_b-g1", "layer": "terrain"},
            {"id": "crate", "take": "crate-g1", "layer": "objects"}]}))
        (likeness / "likeness.json").write_text(json.dumps({"objects": {
            "ground_crater_b": {"route": "code", "model": "/code/crater_b.gltf"}}}))
        join.make({"inventory": inventory, "terrain": terrain, "props-inputs": split, "likeness": likeness}, out, 0,
                  {})
        joined = json.loads((out / join.JOIN).read_text())
        assert joined["pieces"] == {} and set(joined["code ground"]) == {"ground_crater_a", "ground_crater_b"}
        assert joined["code ground"]["ground_crater_a"] == "no likeness record: the loop never reached its model"
        assert "pipeline failed" in joined["code ground"]["ground_crater_b"], joined  # the named fallback
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



def made_piece(root, row_id, settings):
    """The loop's ends for one terrain row it made: a baked crater (export_test.box_gltf of a bowl) under
    <bake>/made with its baked.json, the paint's labelled parts (one part painted as its settings variant), the
    surfaces-parts row of that finish, the split's row and its likeness record."""
    folders = {name: root / name for name in ("surfaces-bake", "surfaces-paint", "surfaces-parts", "props-inputs",
                                              "likeness")}
    take = f"{row_id}-g1"
    (folders["surfaces-bake"] / "made").mkdir(parents=True)
    crater = bowl()
    export_test.box_gltf(folders["surfaces-bake"] / "made", row_id, crater)
    (folders["surfaces-bake"] / "baked.json").write_text(json.dumps({row_id: {
        "parts": take, "base": [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
        "size": np.ptp(crater.vertices, axis=0).tolist()}}))
    labelled = folders["surfaces-paint"] / "labelled" / take
    labelled.mkdir(parents=True)
    crater.export(labelled / f"{route_settings.settings_name('regolith', settings)}.ply")
    folders["surfaces-parts"].mkdir()
    (folders["surfaces-parts"] / "parts.json").write_text(json.dumps({"takes": {take: {"parts": [
        {"part": 0, "surface": "regolith", "settings": settings}]}}}))
    folders["props-inputs"].mkdir()
    (folders["props-inputs"] / "rows.json").write_text(json.dumps({"rows": [
        {"id": row_id, "take": take, "layer": "terrain"}]}))
    folders["likeness"].mkdir()
    (folders["likeness"] / "likeness.json").write_text(json.dumps({"objects": {row_id: {"route": "prop"}}}))
    return folders


def test_a_piece_the_loop_made_is_joined_with_the_finish_route_s_own_finish():
    root = pathlib.Path(tempfile.mkdtemp())
    try:
        terrain, out = root / "terrain", root / "out"
        flat_ground(terrain, "yard")
        out.mkdir()
        settings = {"token": "grey-500", "roughness": 0.8, "metal": 0.0, "seed": 7, "wear": 0.3}
        variant = route_settings.settings_name("regolith", settings)
        inventory = root / "yard.json"
        inventory.write_text(json.dumps({"place": "yard", "rows": [
            {"id": "ground_crater_a", "size": [8.0, 8.0, 1.6], "at": [{"x": 2.0, "y": 0.0, "z": -3.0}],
             "area": {"landform": "crater A"}}]}))
        ends = made_piece(root, "ground_crater_a", settings)
        join.make({"inventory": inventory, "terrain": terrain, **ends}, out, 0, {})
        joined = json.loads((out / join.JOIN).read_text())
        piece = joined["pieces"]["ground_crater_a"]
        assert joined["code ground"] == {} and piece["cut faces"] > 0 and piece["finishes"] == [variant], joined
        assert variant.endswith("_s7_w030"), variant  # the finish's own seed and wear
        stage = Usd.Stage.Open(str(out / "moon/places/yard.usdc"))
        mesh = stage.GetPrimAtPath("/yard/Outside/Detail/ground_crater_a/geo")
        subset = UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Mesh(mesh))[0]
        look = UsdShade.MaterialBindingAPI(subset.GetPrim()).GetDirectBinding().GetMaterial()
        assert look.GetPrim().GetAttribute("score:surface").Get() == variant
        files = [shader.GetInput("file").Get().path for shader in
                 (UsdShade.Shader(prim) for prim in look.GetPrim().GetChildren())
                 if shader.GetInput("file")]
        assert files and all(path.startswith("./textures/ground_crater_a_") for path in files), files  # its bake's
        assert all((out / "moon/places" / path).exists() for path in files)
        verdict = join.judge_seam(out, {}, {})
        assert verdict.answer == checks.PASS and verdict.measures["joined"] == 1, verdict
    finally:
        shutil.rmtree(root)

if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
