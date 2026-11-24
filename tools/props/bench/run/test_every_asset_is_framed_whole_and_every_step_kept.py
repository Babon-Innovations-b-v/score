"""The benchmark's close-up frames each asset whole in the close-up style (turned and looking down, or straight above
when it lies flat), lays it on the grey backdrop while its RGBA keeps the true alpha, refuses a render whose box
slipped, gives both routes the material class its words or its kind name, and keeps every route step as a store object with its blobs in the bucket: a failing step is its branch's
gap, the steps after it are not run, and a run taken up again runs no kept step twice; a made model (glTF, Y up) and a
withdrawn one (a Y-up stage) are measured in the truth's frame, metres Z up. Branch B's finish (finish.py) offers
score_lib's surfaces with a recipe, never one painted for one model or with none, and gives every face of the made
model a part bound to a library surface, which the measures read as its finish groups and families.

Breaks that turn this red (each applied once and seen red, then reverted):
- bench.view_of: MARGIN left out of `reach` -> the box's outermost corner lands on the frame's edge, not inside it
- bench.view_of: LOOK_DOWN_DEGREES for every row, not check.look_down -> the tray is not seen from straight above
- bench.on_backdrop: the alpha left out (the render's RGB alone) -> the backdrop comes out black, not BACKDROP
- bench.material_for: a CLASS_WORDS word matched whole only -> the wooden tray is given plastic, not wood
- bench.render_asset: the box check dropped -> the render Blender laid in centimetres is kept
- bench.Kept.keep: the bucket push dropped -> the step's blobs are not in the bucket
- bench.run_steps: the gap's `return` dropped -> the step after a failing one runs
- bench.run_steps: a kept step not skipped -> taking the run up again makes the raw model twice
- bench.Y_UP the identity (glTF's Y up read as Z up) -> the made box comes back lying on its side
- bench.usd_side: a Y-up stage not turned -> the withdrawn model's box comes back lying on its side
- finish.offered_addresses: the `painted_for` tag not read -> the one-model surface is fetched, left out only for its
  missing recipe
- bench.made_side: the finish's parts not read -> the made model's faces carry no finish group
- bench.weighed_step: a part's surface class not read (the given class for every part) -> the plastic box touches
  with metal's 0.3; its parts' words not asked -> the ask does not name the grey plastic
- bench.parts_step (#177): the parts' masses not shared from the physics step's groups -> the lid and the body do not
  weigh the box's 2 kg; bench.parted: the axis left in glTF's Y up -> the door's hinge about -y is not turned to Z up; made_side not reading the parts -> the box's faces carry no part
- finish.same_family: a truth surface with no family counted as a mismatch -> its share is 0.0, not unjudged
- finish.look_job: the texels.npz check dropped -> a finish with none fails on numpy's own error, not its reason;
  its part's list settings not read (part_spec's `set_spec` dropped) -> the look's spec is not the listed roughness
  0.4; surface_masks' `found == index` -> `found != index` -> the box's one mask is empty (#182)
- bench.look_holes (#159): the look's background not read -> the box's holes are 100 of the square's pixels, not 200;
  the mesh alone's black not read -> 100, not 200; finish.look_axes: a fixed +z up for the close-up's own -> a
  camera straight down has no frame (NaN axes, the ceiling task light's empty look)
- finish.part_spec: a colour setting the variant names none of not filled -> painted_metal's look is drawn with no
  `bare` (the rack's KeyError, #182); a pictured recipe given no clear picture -> printed is drawn with no `image`
- route_settings.set_spec: the second shade not moved with the list's token (`moved` dropped) -> the grey leather's
  #686068 creases stay under the white #e8e8e8, dE 50.6 from it, not the variant's 8.1 (the surgical chair's granite
  seat, #186)
- finish.part_looks: a part's list settings not read (its surface's own spec for every part) -> the box's look is not
  the listed roughness 0.4; its class not read -> the box's look has no class
- A pictured case (#159, the cockpit row: no NVIDIA model) is rendered as its close-up kept in the store, keeps its own
  material, and its made box at its target size is measured against that close-up and size alone:
  bench.read_set reading it as a simready row -> it has no version and the set is not read; bench.render_one drawing
  it as a truth -> Blender's stand-in is asked for it; bench.pictured_render keeping the picture's RGB alone -> its
  rgba.png has no true alpha; bench.measure_all reading it as a truth -> its truth read is a gap and nothing is measured
"""
import ast
import json
import math
import pathlib

import numpy as np
import pytest
from PIL import Image

import bench
import finish
from score.store import Store
from score.store.offload import FolderBucket

# id, its set kind, the class the routes are given, true box (low, high) in metres Z up, lies flat, the scale
# Blender's box comes back at, the route step that fails
ROWS = [
    ("simready_crate_blue_a01", "crate", "plastic", ([-0.3, -0.2, 0.0], [0.3, 0.2, 0.25]), False, 1.0, None),
    ("simready_utensil_serving_tray_wooden_b01", "tray (flat)", "wood", ([-0.14, -0.22, 0.0], [0.14, 0.22, 0.06]),
     True, 1.0, "finished"),
    ("simready_storage_locker_double_bench_b01", "cabinet / locker", "metal", ([0.0, 0.0, 0.0], [0.5, 0.5, 1.9]),
     False, 1.0, "raw"),
    ("simready_box_cardboard_a02", "box", "cardboard", ([-0.3, -0.2, 0.0], [0.3, 0.2, 0.25]), False, 100.0, None),
    ("cockpit_toggle_switch", "cockpit", "aluminium", ([-0.015, -0.016, 0.0], [0.015, 0.016, 0.036]), False, 1.0,
     None),
]
PIXELS = 64


def projected(view, point):
    """Where `point` lands in the frame, -1 to 1 at its edges: a pinhole camera worked out here, apart from bench."""
    eye, aim = np.asarray(view["eye"]), np.asarray(view["aim"])
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(forward, view["up"])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    offset = np.asarray(point) - eye
    depth = offset @ forward
    half = math.tan(math.radians(view["fov"]) / 2)
    return offset @ right / depth / half, offset @ up / depth / half


def y_up(points):
    """Z-up points in a Y-up frame (x across, y up, z toward the viewer), worked out here, apart from bench."""
    points = np.asarray(points, dtype=float)
    return np.stack([points[:, 0], points[:, 2], -points[:, 1]], 1)


def usd_box(path, low, high, up="z"):
    """A stage in metres holding one box mesh from `low` to `high` (Z up): a Z-up stage, or a Y-up one (`up` "y")
    holding the same box in its own axes."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z if up == "z" else UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    mesh = UsdGeom.Mesh.Define(stage, "/box")
    stage.SetDefaultPrim(mesh.GetPrim())
    corners = np.array([(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    mesh.CreatePointsAttr([tuple(point) for point in (corners if up == "z" else y_up(corners))])
    mesh.CreateFaceVertexCountsAttr([4] * 6)
    mesh.CreateFaceVertexIndicesAttr([0, 1, 3, 2, 4, 6, 7, 5, 0, 4, 5, 1, 2, 3, 7, 6, 0, 2, 6, 4, 1, 5, 7, 3])
    stage.Save()


def surface_library(root):
    """A small score_lib with three surfaces in its index: one adopted and tiling (a fitted plastic), one painted for
    one model, one a recipe's own entry; {address: its surface.json}."""
    (root / "index").mkdir(parents=True)
    rows = [("surface/simready_m_plastic_grey_a01@1", {}), ("surface/simready_m_atlas_a01@1", {"painted_for": ["x"]}),
            ("surface/rubber@1", {})]
    (root / "index/surface.json").write_text(json.dumps({"schema": "score-lib-index/1", "kind": "surface", "entries": [
        {"address": address, "state": "draft", "tags": tags} for address, tags in rows]}))
    for address, _ in rows:
        kind, rest = address.split("/")
        folder = root / "entries" / kind / rest.replace("@", "/")
        folder.mkdir(parents=True)
        (folder / "entry.json").write_text(json.dumps({"files": {"surface.json": {"role": "record"}}}))
    return {"surface/simready_m_plastic_grey_a01@1": {"recipe": {"recipe": "plastic", "settings": {
                "colour": [0.2, 0.2, 0.2], "roughness": 0.4, "metal": 0.0, "dirt_colour": [0.1, 0.1, 0.1]}}},
            "surface/rubber@1": {"recipe": "rubber"},
            "surface/simready_m_atlas_a01@1": {"recipe": None, "recipe_gap": "maps only"}}


def listing(bodies):
    """A stand-in for the list's ask: one finish, the first surface and token offered, every region of every view."""
    found = {}
    for take, body in bodies.items():
        schema = body["generationConfig"]["responseSchema"]["properties"]
        finish = schema["finishes"]["items"]["properties"]
        views = schema["labels"]["items"]["properties"]["view"]["enum"]
        found[take] = json.dumps({"finishes": [{"parts": "all of it", "finish": "grey plastic",
                                                "surface": finish["surface"]["enum"][0],
                                                "token": finish["token"]["enum"][0], "roughness": 0.4, "metal": 0.0,
                                                "fits": True}],
                                  "labels": [{"view": view, "region": region, "finish": 1}
                                             for view in views for region in range(1, 9)]})
    return found


def finished_box(tmp_path, monkeypatch, name, model, close_up):
    """The made box through branch B's finish on a small library; its family share against a truth of the surface
    it took and against one painted for one model (no family): (the library, the side the measures read, both)."""
    root = tmp_path / "score_lib"
    held = surface_library(root)
    monkeypatch.setenv("SCORE_LIB_ROOT", str(root))
    monkeypatch.setattr(finish, "records", lambda addresses: {address: held[address] for address in addresses})
    library = finish.bench_library(root)
    folder = tmp_path / "finish"
    folder.mkdir()
    row = {"id": name, "words": f"{name} a thing", "size": [0.6, 0.4, 0.25]}
    finish.finished(model, close_up, row, library, folder, ask=listing)
    import shutil
    import trimesh
    from score.stages.place_build.maker import sim
    folders = {"final": tmp_path / "final", "sim": tmp_path / "sim", "finish": folder}
    for step in ("final", "sim", "physics"):
        (tmp_path / step).mkdir()
    shutil.copyfile(model, folders["final"] / "final.glb")
    trimesh.load(str(model), force="mesh").export(str(folders["sim"] / "hulls.glb"))
    asked = []
    monkeypatch.setattr(sim, "claude_ask", lambda body: asked.append(body) or json.dumps(
        {"whole_kg": 2.0, "reason": "a box", "parts": [{"part": 0, "kg": 2.0}]}))
    bench.weighed_step(folders, {**row, "size": [0.6, 0.4, 0.25]}, "metal", close_up)(tmp_path / "physics")
    from score.stages.place_build.maker import parts
    monkeypatch.setattr(parts, "claude_ask", lambda body: json.dumps({"reason": "its lid", "parts": [
        {"name": "lid", "joint": "slide", "box": [0.0, 0.0, 1.0, 1.0], "hinge": "none", "opens": 0.1, "thick_m": 1.0}]}))
    (tmp_path / "parts").mkdir()
    bench.parts_step({**folders, "physics": tmp_path / "physics"}, row, close_up)(tmp_path / "parts")
    cut = json.loads((tmp_path / "parts" / "parts.json").read_text())
    side = bench.made_side(model, tmp_path / "physics", folder, name, tmp_path / "parts")
    lid = cut["parts"][0]
    assert len(side["face_part"]) == len(side["faces"]) and (side["face_part"] == 0).any()
    assert math.isclose(lid["kg"] + cut["body"]["kg"], 2.0) and side["joints"][0]["type"] == "prismatic"
    assert np.allclose(y_up([side["joints"][0]["axis"]])[0], lid["sign"] * np.eye(3)["xyz".index(lid["axis"])])
    (tmp_path / "door").mkdir()  # a door hinged about the model's -y at (1, 2, 3), glTF's Y up
    (tmp_path / "door" / "parts.json").write_text(json.dumps({"parts": [
        {"joint": "hinge", "axis": "y", "sign": -1, "pivot": [1.0, 2.0, 3.0], "limits": [0.0, 90.0]}]}))
    np.save(tmp_path / "door" / "face_parts.npy", np.array([-1, 0]))
    door = bench.parted(tmp_path / "door")["joints"][0]
    assert np.allclose(y_up([door["axis"], door["pivot"]]), [[0.0, -1.0, 0.0], [1.0, 2.0, 3.0]]), door
    taken = sim.surface_class(held[side["surfaces"][0]])
    assert (side["mass"], side["friction"]) == (2.0, sim.material(taken)["static"]) and taken != "metal"
    assert {(look["class"], tuple(np.round(look["colour"], 4)), look["roughness"]) for look in side["looks"].values()} \
        <= {(taken, tuple(np.round(finish.linear_of(token), 4)), 0.4) for token in library[1]["tokens"]}, side["looks"]
    assert "grey plastic" in asked[0]["contents"][0]["parts"][-1]["text"]
    from tools.props.bench import measures
    split = measures.measured({**side, "face_material": np.zeros(len(side["faces"]), int),
                               "materials": [{"name": "body", "surface": "surface/simready_m_atlas_a01@1"}]},
                              side)["finish"]
    return library, side, [finish.same_family(split["pairs"], side["surfaces"], [truth]) for truth in
                           (side["surfaces"][0], "surface/simready_m_atlas_a01@1")]


def looked(tmp_path, name, view):
    """The made box's look step (#182) on its finish (finished_box's) with a stand-in look.py: (whether its gap names
    the missing texels.npz; the masks its job wrote, its first mask's middle texel, its first spec's roughness,
    its small copy's size, its holes) once the finish's texels name part 0
    throughout. The stand-in draws the box as a square half the side across, a 10 x 10 hole through the look and a
    10 x 10 black patch on the mesh alone (#159: its holes 200 of the square's pixels)."""
    folder, model = tmp_path / "finish", tmp_path / "made.glb"
    drawn = []

    def draw(_job_name, arguments, log, script):
        job = json.loads(open(arguments[0]).read())
        drawn.append((job, script))
        side = job["side"]
        square = np.zeros((side, side, 4), np.uint8)
        square[side // 4:side // 4 + side // 2, side // 4:side // 4 + side // 2] = 200
        look, bare = square.copy(), square.copy()
        look[side // 2:side // 2 + 10, side // 2:side // 2 + 10] = 0
        bare[side // 3:side // 3 + 10, side // 3:side // 3 + 10, :3] = 0
        Image.fromarray(look).save(job["out"])
        Image.fromarray(bare).save(job["bare"])
        open(log, "w").write("drawn\n")
        return 0
    bare = tmp_path / "look-bare"
    bare.mkdir()
    with pytest.raises(RuntimeError) as refused:
        bench.look_step(model, folder, {"id": name}, view, draw)(bare)
    np.savez(folder / "surfaces-parts" / name / "texels.npz", piece0=np.zeros((4, 4), np.uint16))
    out = tmp_path / "look"
    out.mkdir()
    bench.look_step(model, folder, {"id": name}, view, draw)(out)
    (job, script), = drawn
    assert script == bench.LOOK and job["eye"] == view["eye"] and job["glb"] == str(model), job
    with Image.open(out / f"look-{bench.LOOK_SMALL}.png") as small:
        size = small.size
    return ("no texels.npz" in str(refused.value), sorted(path.name for path in out.glob("mask-*.png")),
            int(np.asarray(Image.open(job["masks"][0]["mask"]))[2, 2]), job["masks"][0]["spec"]["roughness"], size,
            json.loads((out / "holes.json").read_text())["holes"])


RECIPES = pathlib.Path(finish.REPO) / "tools/props/library/recipes.py"
# What recipes.arguments gives every recipe on its own: the place's wear and dirt, the job's seed, the piece's foot.
ARGUMENTS_GIVEN = {"wear", "dirt", "seed", "foot", "kicks"}


def undrawn(tmp_path):
    """Each recipe of recipes.py (its RECIPES, read by ast: ProcFunc is Blender's) as score_lib's own recipe entry
    (finish.variant_of's: a token alone) through the look's part_spec: {recipe: the arguments it needs that the spec
    leaves out}, the empty ones dropped."""
    tree = ast.parse(RECIPES.read_text())
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    table = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                 and getattr(node.targets[0], "id", None) == "RECIPES")
    method = json.loads((pathlib.Path(finish.REPO) / "data/library/materials.json").read_text())
    library = {"recipes": method["recipes"], "colour_settings": method["colour_settings"],
               "tokens": {finish.NEUTRAL: finish.NEUTRAL}, "dirt": finish.NEUTRAL, "pictures": {},
               "families": {key.value: {"surface": None, "variants": {key.value: {"recipe": key.value,
                                                                                    "token": finish.NEUTRAL}}}
                            for key in table.keys}}
    import library as surface_library
    colours = surface_library.token_colours(library)
    found = {}
    for key in table.keys:
        spec = finish.part_spec(library, {"judge": key.value}, colours, None, tmp_path)
        listed = functions[key.value].args
        needed = [argument.arg for argument in listed.args[:len(listed.args) - len(listed.defaults)]]
        found[key.value] = [name for name in needed if name not in spec and name not in ARGUMENTS_GIVEN]
    return {recipe: missing for recipe, missing in found.items() if missing}


def recoloured_step():
    """The CIELAB step from colour to second shade of a fitted grey leather (#707070, creases #686068) as the look
    paints it under the list's white token (#e8e8e8): (that step, the variant's own)."""
    import library as surface_library
    from score.stages.props import prop_data
    with prop_data.tools("props/library/likeness"):
        import colour as lab_colour
    method = json.loads((pathlib.Path(finish.REPO) / "data/library/materials.json").read_text())
    tokens = {token: token for token in ("#707070", "#686068", "#e8e8e8")}
    library = {"recipes": method["recipes"], "colour_settings": method["colour_settings"], "tokens": tokens,
               "dirt": "#707070", "pictures": {}, "families": {"leather": {"surface": None, "variants": {
                   "grey_leather": {"recipe": "leather", "token": "#707070", "second": "#686068"}}}}}
    colours = surface_library.token_colours(library)
    row = {"judge": "grey_leather", "settings": {"token": "#e8e8e8", "roughness": 0.5, "metal": 0.0, "seed": 1}}
    spec = finish.part_spec(library, row, colours, None, None)
    def step(one, other):
        return float(np.linalg.norm(lab_colour.lab(np.asarray(one)) - lab_colour.lab(np.asarray(other))))
    return step(spec["colour"], spec["second"]), step(colours["#707070"], colours["#686068"])


def pictured_case(tmp_path, name, material, box):
    """The cockpit row: its close-up (a red square, true alpha) kept in the store, rendered as its close-up, and a
    made box at its target size measured against it (branch A's kept `finished`, no finish parts)."""
    low, high = box
    target = [round(value, 4) for value in np.subtract(high, low)]
    picture = np.zeros((PIXELS, PIXELS, 4), np.uint8)
    picture[16:48, 20:44] = (200, 0, 0, 255)
    (tmp_path / "picture").mkdir()
    Image.fromarray(picture, "RGBA").save(tmp_path / "picture" / "closeup.png")
    bucket = FolderBucket(tmp_path / "bucket")
    kept = bench.Kept(Store.in_folder(tmp_path / "store"), bucket, tmp_path / "index.json")
    held = kept.store.put_tree(tmp_path / "picture")
    case = {"id": name, "kind": "cockpit", "split": "tune", "withdrawn": [], "material": material, "made_before": [],
            "picture": {"closeup": held, "size": target, "size_from": "a test", "words": "a toggle switch",
                        "labels": ["ON"], "classes": ["metal"], "never": ["cloth"]}}
    (tmp_path / "set.json").write_text(json.dumps({"objects": [case]}))
    [row] = bench.read_set(tmp_path / "set.json")
    assert (row["id"], row["address"], bench.material_for(row)) == (name, None, material)

    def refused(*_):
        raise AssertionError("a pictured case is never drawn")
    bench.render_all([row], {}, kept, "trial", refused)
    folder = kept.store.checkout(kept.entry(name, "input", "render")["output"])
    given = json.loads((folder / "row.json").read_text())
    assert (given["size"], given["words"], given["picture"]) == (target, "a toggle switch", held)
    assert (np.asarray(Image.open(folder / "rgba.png"))[..., 3] == picture[..., 3]).all()
    assert tuple(np.asarray(Image.open(folder / "closeup.png"))[2, 2]) == bench.BACKDROP
    import trimesh
    made = trimesh.creation.box(bounds=[low, high])
    made.vertices = y_up(made.vertices)
    (tmp_path / "finished").mkdir()
    made.export(str(tmp_path / "finished" / "final.glb"))
    kept.keep(name, "A", "finished", tmp_path / "finished", 0.0)
    bench.measure_all([row], [row], kept, "trial")
    record = json.loads((kept.store.checkout(kept.entry(name, "A", "measures")["output"]) /
                         "measures.json").read_text())
    rows = {item["measure"]: item for item in record["judged"]["rows"]}
    assert record["truth"]["closeup"] == held and rows["size.size"]["value"] == 0.0, record["truth"]
    assert {"shape.closeup", "clean.open_length", "clean.thinnest", "finish.edge_wander"} <= set(rows), rows
    assert "labels.held" not in rows and "finish.picks" not in rows  # no finish parts: left out, never failed


def drawer(scale):
    """A stand-in for Blender: the object a red square with its true alpha; its shadow a half-dark band below it."""
    def draw(_job_name, arguments, log):
        root, job, out = arguments
        job = json.loads(open(job).read())
        from pathlib import Path
        out = Path(out)
        out.mkdir(parents=True)
        rgba = np.zeros((PIXELS, PIXELS, 4), np.uint8)
        rgba[16:40, 16:48] = (200, 0, 0, 255)
        Image.fromarray(rgba, "RGBA").save(out / "rgba.png")
        shadow = rgba.copy()
        shadow[40:48, 16:48] = (0, 0, 0, 128)
        Image.fromarray(shadow, "RGBA").save(out / "shadow.png")
        low, high, _ = bench.true_box(root)
        (out / "report.json").write_text(json.dumps({"box": [[side * scale for side in low],
                                                             [side * scale for side in high]], "job": job}))
        Path(log).write_text("drawn\n")
        return 0
    return draw


@pytest.mark.parametrize("name, kind, material, box, flat, scale, failing", ROWS)
def test_every_asset_is_framed_whole_and_every_step_kept(tmp_path, monkeypatch, name, kind, material, box, flat, scale,
                                                         failing):
    if kind == "cockpit":
        pictured_case(tmp_path, name, material, box)
        return
    set_file = tmp_path / "set.json"
    set_file.write_text(json.dumps({"objects": [{"address": f"model/{name}@1", "kind": kind, "split": "tune"}]}))
    [row] = bench.read_set(set_file)
    assert (row["id"], bench.material_for(row)) == (name, material)
    low, high = box
    usd_box(tmp_path / f"{name}.usda", low, high)

    import trimesh  # a made model as a route writes one: glTF, Y up; and a withdrawn one on a Y-up stage
    made = trimesh.creation.box(bounds=[low, high])
    made.vertices = y_up(made.vertices)
    made.export(str(tmp_path / "made.glb"))
    usd_box(tmp_path / "old.usda", low, high, up="y")
    for side in (bench.gltf_side(tmp_path / "made.glb"), bench.usd_side(tmp_path / "old.usda")):
        assert np.allclose(side["box"], [low, high], atol=1e-6), side["box"]
    monkeypatch.setattr(bench, "fetched", lambda address, values, into: (
        {"title": name, "tags": {"description": ["a thing"]}}, tmp_path / f"{name}.usda"))
    monkeypatch.setattr(bench, "SIZE", PIXELS)
    bucket = FolderBucket(tmp_path / "bucket")
    kept = bench.Kept(Store.in_folder(tmp_path / "store"), bucket, tmp_path / "index.json")
    bench.render_all([row], {}, kept, "trial", drawer(scale))

    found = kept.entry(name, "input", "render")
    if scale != 1.0:
        assert "gap" in found and "off" in found["gap"], found
        return
    folder = kept.store.checkout(found["output"])
    for sha in set(kept.store.listing(found["output"]).values()):
        assert (tmp_path / "bucket" / f"blobs/{sha}").is_file(), sha
    given = json.loads((folder / "row.json").read_text())
    assert given["lies_flat"] is flat and given["words"] == f"{name} a thing"
    assert np.allclose(given["size"], np.subtract(high, low), atol=1e-4)
    view = given["camera"]
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    seen = np.abs([projected(view, corner) for corner in corners])
    assert seen.max() == pytest.approx(1 - bench.MARGIN, abs=1e-6), seen.max()  # whole, and as near as it can be
    looking = np.subtract(view["eye"], view["aim"])
    rise = math.degrees(math.asin(looking[2] / np.linalg.norm(looking)))
    turn = math.degrees(math.atan2(looking[0], -looking[1]))
    assert (rise, turn if not flat else 0.0) == pytest.approx((90.0, 0.0) if flat else (15.0, 35.0), abs=1e-6)
    # The look's camera on the close-up's view and up (#159), and on the ceiling task light's: straight down, exactly.
    for camera in (view, {"eye": [0.0, 0.0, 2.6], "aim": [0.0, 0.0, 0.08], "up": [0.0, 1.0, 0.0]}):
        axes = np.array(finish.look_axes(camera))
        assert np.allclose(axes @ axes.T, np.eye(3)) and axes[1] @ camera["up"] > 0.9, axes

    laid = np.asarray(Image.open(folder / "closeup.png"))
    assert laid.shape[2] == 3 and tuple(laid[2, 2]) == bench.BACKDROP and tuple(laid[20, 20]) == (200, 0, 0)
    assert laid[44, 30].sum() < sum(bench.BACKDROP)  # its shadow darker than the backdrop
    alpha = np.asarray(Image.open(folder / "rgba.png"))[..., 3]
    assert alpha[20, 20] == 255 and alpha[44, 30] == 0  # the true alpha holds no shadow

    if failing is None:  # one asset through branch B's finish (the others' rows test the render and the steps)
        (variants, palette, addresses, left), side, family = finished_box(tmp_path, monkeypatch, name,
                                                                          tmp_path / "made.glb", folder / "rgba.png")
        assert set(addresses.values()) == {"surface/simready_m_plastic_grey_a01@1", "surface/rubber@1"}
        assert list(left) == ["surface/simready_m_atlas_a01@1"] and "one model" in left[list(left)[0]], left
        assert variants["families"]["plastic"]["variants"]["simready_m_plastic_grey_a01"]["token"] == \
            finish.token_of([0.2, 0.2, 0.2]) and finish.NEUTRAL in palette["tokens"]
        assert len(side["face_material"]) == len(side["faces"]) and (side["face_material"] >= 0).all()
        assert set(side["surfaces"].values()) <= set(addresses.values()), side["surfaces"]
        assert [(share["same_family"], share["unjudged"]) for share in family] == [(1.0, 0.0), (None, 1.0)], family
        assert looked(tmp_path, name, view) == (
            True, ["mask-0.png"], 255, 0.4, (bench.LOOK_SMALL, bench.LOOK_SMALL),
            round(200 / (finish.LOOK_SIDE // 2) ** 2, 5)), name
        assert undrawn(tmp_path) == {}, "the look draws every recipe family"
        drawn, own = recoloured_step()
        assert drawn == pytest.approx(own, abs=0.5), (drawn, own)

    made = []

    def step(label):
        def make(out):
            made.append(label)
            if label == failing:
                raise bench.StepFailed(f"{label} made nothing")
            (out / f"{label}.txt").write_text(label)
        return make
    steps = [(label, step(label)) for label in ("raw", "finished", "straight")]
    for _ in range(2):  # the run, then the run taken up again
        bench.run_steps(kept, name, "A", steps, tmp_path / "scratch")
    order = ["raw", "finished", "straight"]
    expected = order[:order.index(failing) + 1] if failing else order
    assert made == expected
    for label in order:
        entry = kept.entry(name, "A", label)
        if failing and order.index(label) > order.index(failing):
            assert entry is None
        elif label == failing:
            assert "made nothing" in entry["gap"]
        else:
            assert (kept.store.checkout(entry["output"]) / f"{label}.txt").read_text() == label
