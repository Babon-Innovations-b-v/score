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
- bench.MEMORY_GB 8 (the scope's own cap) -> the close-up's scope holds 8 GB, and the tool organizer cart (8.8 GB) is
  killed in every run (#159); render.KILLED not named -> a close-up killed past its cap reads only "exited 137"
- bench.render_asset: the `drawn_apart` check dropped -> a close-up its floor lights (the red square drawn pinker on
  the backdrop than in rgba.png) is kept (#202)
- bench.Kept.keep: the bucket push dropped -> the step's blobs are not in the bucket
- bench.run_steps: the gap's `return` dropped -> the step after a failing one runs
- bench.run_steps: a kept step not skipped -> taking the run up again makes the raw model twice
- bench.Y_UP the identity (glTF's Y up read as Z up) -> the made box comes back lying on its side
- bench.usd_side: a Y-up stage not turned -> the withdrawn model's box comes back lying on its side
- finish.offered_addresses: the `painted_for` tag not read -> the one-model surface is fetched, left out only for its
  missing recipe; the `pattern` family not read (#210) -> the vent pattern's record is fetched (KeyError)
- bench.made_side: the finish's parts not read -> the made model's faces carry no finish group
- bench.weighed_step: a part's surface class not read (the given class for every part) -> the plastic box touches
  with metal's 0.3; its parts' words not asked -> the ask does not name the grey plastic
- bench.parts_step (#177): the parts' masses not shared from the physics step's groups -> the lid and the body do not
  weigh the box's 2 kg; bench.parted: the axis left in glTF's Y up -> the door's hinge about -y is not turned to Z up; made_side not reading the parts -> the box's faces carry no part
- finish.same_family: a truth surface with no family counted as a mismatch -> its share is 0.0, not unjudged
- finish.look_job: the texels.npz check dropped -> a finish with none fails on numpy's own error, not its reason;
  its part's list settings not read (part_spec's `set_spec` dropped) -> the look's spec is not the listed roughness
  0.4; surface_masks' `found == index` -> `found != index` -> the box's one mask is empty (#182); the decoded mesh
  beside the model not named (`job["decoded"]` dropped) -> look.py shades no seam from it (#159); hardware_laid's
  cut point left in glTF's Y up (`dict(piece["cut"], at=z_up(...))` -> `piece["cut"]`) -> the blob cut away a frame
  off its piece, its piece's spec not its finish's (`part_spec(...)` -> `{}`) -> the lock drawn in no recipe (#212)
- bench.look_holes (#159): the look's background not read -> the box's holes are 100 of the square's pixels, not 200;
  the mesh alone's black not read -> 100, not 200; finish.look_axes: a fixed +z up for the close-up's own -> a
  camera straight down has no frame (NaN axes, the ceiling task light's empty look)
- finish.marks_read (#185): mark_crop's READ_MARGIN growth dropped -> the crops are the marks' boxes alone (200 x 200,
  not 260 x 260); an unanswered reading taken as read (`read = None if ...` -> `read = {"text": mark["text"], ...}`)
  -> the mark nobody read is read as its words; bench.look_step not reading the marks -> no read.json;
  bench.look_found not reading read.json (`if (looked / "read.json").exists()` -> `if False`) -> the look group holds
  its holes alone
- finish.part_spec: a colour setting the variant names none of not filled -> painted_metal's look is drawn with no
  `bare` (the rack's KeyError, #182); a pictured recipe given no clear picture -> printed is drawn with no `image`
- finish.drawn_patterns: the close-up read for the look too (`pictures["pattern"]` NVIDIA's) -> the box drawn
  speckled black on white holds NVIDIA's smooth pattern (the surgical chair's granite seat, #186); its colour read
  off the close-up for the look too (`drawn = {...}[key]` -> `drawn = "true_drawn"`) -> the flat grey look has no
  drawn colour (#198); its clipped share read off the close-up for the look too (`clipped = {...}[key]` ->
  `"true_clipped"`) -> the speckled look's white squares are not clipped (#159, tc6's blown-out locker); its shading
  read off the close-up for the look too (`shade = ...` -> `"true_shade"`) -> the speckled look has no spread (#206)
- finish.drawn_opacity: every spec drawn whole (1.0) -> the glass recipe's look is opaque, not its method's 0.2
  (the tc4r fridge's door, #186)
- route_settings.set_spec: the second shade not moved with the list's token (`moved` dropped) -> the grey leather's
  #686068 creases stay under the white #e8e8e8, dE 50.6 from it, not the variant's 8.1 (the surgical chair's granite
  seat, #186)
- finish.part_looks: a part's list settings not read (its surface's own spec for every part) -> the box's look is not
  the listed roughness 0.4; its class not read -> the box's look has no class
- The look's light held to the close-up (#206, light_held: NVIDIA's model drawn by the look, as its close-up):
  bench.render_one not running the light step -> the crate keeps no light row (TypeError); bench.exposure_held's
  `abs(gap)` -> `gap` -> a look drawn darker than its close-up is held; its CLIP_SLACK check dropped -> a look as light
  but clipped white more is held; bench.exposure counting the edge's part-covered pixels (`>= 255` -> `> 0`) -> a look
  drawn as its close-up is not held; bench.unheld_light not leaving a pictured case out -> the cockpit row's look is
  refused; bench.look_step's `uncalibrated` not refused -> a look is drawn under an unheld light
- A pictured case (#159, the cockpit row: no NVIDIA model) is rendered as its close-up kept in the store, keeps its own
  material, and its made box at its target size is measured against that close-up and size alone:
  bench.read_set reading it as a simready row -> it has no version and the set is not read; bench.render_one drawing
  it as a truth -> Blender's stand-in is asked for it; bench.pictured_render keeping the picture's RGB alone -> its
  rgba.png has no true alpha; bench.measure_all reading it as a truth -> its truth read is a gap and nothing is measured.
  Its look (#159 round 7, tc5's cockpit looks failed on TypeError 'NoneType' object is not a mapping): finish.look_view
  passing the row's camera on as it is -> the case's None reaches look_axes (TypeError); its aim behind the eye
  (`eye - ahead`) -> the look faces away, its axes not right, up and back as fitted; bench.measure_pictured not
  judging the look (judged_look's group not passed) -> B's measures hold no picture row and its shape fault passes;
  bench.judged_look not naming the case pictured -> the judge is asked about NVIDIA's render, not the close-up.
  The previous round's look is its made model drawn again by today's look (#205: tc5r's looks, drawn under an even grey
  world, held against tc6's under the close-up's light, were judged regressed in 26 of 30): bench.judged_look holding
  the previous run's kept look -> its model is never drawn again and the judge is shown the kept picture; the
  previous drawn from the row's own camera when it has none (`row["camera"]`) -> drawn from None, not its finish's fitted
  camera
"""
import ast
import base64
import io
import json
import math
import os
import pathlib
import shutil

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
    """A small score_lib with four surfaces in its index: one adopted and tiling (a fitted plastic), one painted for
    one model, one a recipe's own entry, one a vent pattern (#210, whose record is never fetched); {address: its
    surface.json} but the pattern's."""
    (root / "index").mkdir(parents=True)
    rows = [("surface/simready_m_plastic_grey_a01@1", {}), ("surface/simready_m_atlas_a01@1", {"painted_for": ["x"]}),
            ("surface/rubber@1", {}), ("surface/vent_round_holes@1", {"family": ["pattern"]})]
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
    """The made box's look step (#182) on its finish (finished_box's) with a stand-in look.py and a stand-in reader
    (#185): (whether its gap names the missing texels.npz; the masks its job wrote, its first mask's middle texel, its
    first spec's roughness, its small copy's size, its holes; the crops read, each its size; read.json) once the
    finish's texels name part 0 throughout. The stand-in draws the box as a square half the side across, a 10 x 10
    hole through the look and a 10 x 10 black patch on the mesh alone (#159: its holes 200 of the square's pixels),
    and two text marks (marks.json)."""
    folder, model = tmp_path / "finish", tmp_path / "made.glb"
    drawn, crops = [], []

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
        marks = [{"text": "03", "box": [100.0, 200.0, 300.0, 400.0]}, {"text": "Patient room", "box": [0, 0, 50, 10]}]
        (pathlib.Path(job["out"]).parent / "marks.json").write_text(json.dumps(marks))
        open(log, "w").write("drawn\n")
        return 0

    def ask(bodies):
        for key, body in sorted(bodies.items()):
            shown = base64.b64decode(body["contents"][0]["parts"][0]["inline_data"]["data"])
            crops.append(Image.open(io.BytesIO(shown)).size)
        return {"0": json.dumps({"reason": "clean", "text": "03"}), "1": RuntimeError("no answer")}
    bare = tmp_path / "look-bare"
    bare.mkdir()
    with pytest.raises(RuntimeError) as refused:
        bench.look_step(model, folder, {"id": name}, view, draw)(bare)
    np.savez(folder / "surfaces-parts" / name / "texels.npz", piece0=np.zeros((4, 4), np.uint16))
    out = tmp_path / "look"
    out.mkdir()
    shutil.copyfile(model, model.with_name("decoded.glb"))  # its decoded mesh beside it, as make's final step keeps it
    parts_file = folder / "surfaces-parts" / "parts.json"
    parts = json.loads(parts_file.read_text())
    parts["takes"][name]["hardware"] = [{"hardware": PIECE, "finish": 0, "part": 0, "at": [0.1, 0.2, 0.3],
                                         "normal": [0.0, 0.0, 1.0], "up": [0.0, 1.0, 0.0], "size": [0.03, 0.05],
                                         "cut": {"at": [0.12, 0.2, 0.3], "radius": 0.04, "falloff": 0.25}}]
    parts_file.write_text(json.dumps(parts))
    files = tmp_path / "library-files"
    (files / PIECE).mkdir(parents=True)
    (files / PIECE / "hardware.glb").write_bytes(b"glTF")
    os.environ["SCORE_LIB_FILES"] = str(files)
    try:
        bench.look_step(model, folder, {"id": name}, view, draw, ask)(out)
    finally:
        del os.environ["SCORE_LIB_FILES"]
    (job, script), = drawn
    assert script == bench.LOOK and job["eye"] == view["eye"] and job["glb"] == str(model) and \
        job["decoded"] == str(model.with_name("decoded.glb")), job
    with Image.open(out / f"look-{bench.LOOK_SMALL}.png") as small:
        size = small.size
    read = [(mark["text"], mark["read"]) for mark in json.loads((out / "read.json").read_text())]
    piece, = job["hardware"]
    return ("no texels.npz" in str(refused.value), sorted(path.name for path in out.glob("mask-*.png")),
            int(np.asarray(Image.open(job["masks"][0]["mask"]))[2, 2]), job["masks"][0]["spec"]["roughness"], size,
            json.loads((out / "holes.json").read_text())["holes"], crops, read,
            (piece["glb"] == str(files / PIECE / "hardware.glb"), piece["at"], piece["normal"], piece["up"],
             piece["cut"]["at"], piece["spec"]["roughness"]))


PIECE = "model/hardware_lock_box_0badcafe@1"  # a hardware piece the finish laid on the box (#212)


def patterned(tmp_path, name, close_up):
    """Each finish part's drawn pattern held to the close-up's (measures pattern_held) when its look (the look step's
    job, looked's) is drawn flat and when it is drawn speckled black on white in 64-pixel squares, coarser than the
    close-up's pixels (the 64-pixel close-up's box is read at its scale): (flat, the flat look's drawn colours, its
    clipped white, its spread, speckled, its clipped white, its spread)."""
    from tools.props.bench.measures import _finish
    held = []
    for look, pixels in (("flat", np.full((1080, 1080, 4), 200, np.uint8)),
                         ("speckled", np.where((np.indices((1080, 1080)) // 64).sum(0)[..., None] % 2, 255, 0).astype(
                             np.uint8).repeat(4, 2))):
        folder = tmp_path / f"look-{look}"
        folder.mkdir()
        (folder / "look.json").write_text((tmp_path / "look" / "look.json").read_text())
        pixels[..., 3] = 255
        Image.fromarray(pixels).save(folder / "look.png")
        found = finish.drawn_patterns(tmp_path / "made.glb", tmp_path / "finish", folder, close_up, name)
        held.append(sorted({_finish.pattern_held(pattern) for pattern in found.values()}, key=str))
        if look == "flat":  # each part's colour as the flat look draws it: sRGB 200 grey, L* 80.6 (#198)
            held.append(sorted({tuple(pattern["drawn"]) for pattern in found.values()}))
        # whether over a tenth of each part is drawn clipped white: none of the flat grey; the speckled look's white
        # squares, 0.19 of the box where the coarser grid's pixels lie wholly on one
        held.append(sorted({pattern["clipped"] > 0.1 for pattern in found.values()}))
        # each part's lightness spread as the look draws it, over 10 L*: none of the flat grey, every part speckled
        held.append(sorted({pattern["shade"]["spread"] > 10 for pattern in found.values()}))
    return tuple(held)


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


def pictured_case(tmp_path, monkeypatch, name, material, box):
    """The cockpit row: its close-up (a red square, true alpha) kept in the store, rendered as its close-up, and a
    made box at its target size measured against it (branch A's kept `finished`, no finish parts; branch B's the same
    box with a kept look, judged by a stand-in for Claude)."""
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
    # Branch B's look of it (#159 round 7): drawn from the camera its finish fitted on the close-up (its row keeps
    # none), and held by eye to the close-up itself, asked as such (a stand-in judge seeing its shape off).
    (tmp_path / "fitted").mkdir()  # a fitted camera 2 m out on glTF's +z, looking at the origin, glTF's +y up
    (tmp_path / "fitted" / "camera.json").write_text(json.dumps({"camera_angle_x": 0.5, "look": {
        "eye": [0.0, 0.0, 2.0], "right": [1.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0]}, "fitted": {"field_vertical": 30.0}}))
    view = finish.look_view(given["camera"], tmp_path / "fitted")
    assert np.allclose(finish.look_axes(view), [[1, 0, 0], [0, 0, 1], [0, -1, 0]]) and view["fov"] == 30.0, view
    assert finish.look_view({"eye": [1.0, 2.0, 3.0]}, tmp_path / "fitted") == {"eye": [1.0, 2.0, 3.0]}
    kept.keep(name, "B", "final", tmp_path / "finished", 0.0)
    (tmp_path / "look").mkdir()
    Image.fromarray(picture, "RGBA").save(tmp_path / "look" / "look.png")
    (tmp_path / "look" / "look.json").write_text(json.dumps(view))  # its camera, as look_job keeps it
    kept.keep(name, "B", "look", tmp_path / "look", 0.0)
    from tools.props.bench import judge
    asked = []
    said = json.dumps({"faults": [{"kind": "shape", "where": "body", "what": "squat"}], "cutout_faults": [],
                       "cutout": "clean", "verdicts": {kind: "fault" if kind == "shape" else "clean"
                                                       for kind in judge.KINDS}})
    monkeypatch.setattr(judge, "claude_asks", lambda bodies: {key: asked.append(body) or said
                                                              for key, body in bodies.items()})
    bench.measure_all([row], [row], kept, "trial")
    record = json.loads((kept.store.checkout(kept.entry(name, "A", "measures")["output"]) /
                         "measures.json").read_text())
    rows = {item["measure"]: item for item in record["judged"]["rows"]}
    assert record["truth"]["closeup"] == held and rows["size.size"]["value"] == 0.0, record["truth"]
    assert {"shape.closeup", "clean.open_length", "clean.thinnest", "finish.edge_wander"} <= set(rows), rows
    assert "labels.held" not in rows and "finish.picks" not in rows  # no finish parts: left out, never failed
    assert not any(measure.startswith("picture.") for measure in rows)  # branch A keeps no look
    looked_record = json.loads((kept.store.checkout(kept.entry(name, "B", "measures")["output"]) /
                                "measures.json").read_text())
    assert "picture.shape" in looked_record["judged"]["failed"], looked_record["judged"]
    assert len(asked) == 1 and "close-up picture" in asked[0]["contents"][0]["parts"][-1]["text"]
    # Held to a previous round (here the same run): its made model drawn again by today's look from its finish's
    # fitted camera, that drawing shown to the judge as the previous look, never the kept one.
    kept.keep(name, "B", "finish", tmp_path / "fitted", 0.0)
    redrawn = []

    def drawn_again(model, parted, asset, camera, folder, draw=None):
        redrawn.append((pathlib.Path(model).read_bytes(), camera))
        Image.fromarray(np.roll(picture, 3, axis=1), "RGBA").save(folder / "look.png")
        return folder / "look.png"
    monkeypatch.setattr(bench, "drawn_look", drawn_again)
    compared = json.dumps({"a_better": "", "b_better": "", "closer": "same"})
    shown = []
    monkeypatch.setattr(judge, "claude_asks", lambda bodies: {key: shown.append(body) or (
        said if key == "faults" else compared) for key, body in bodies.items()})
    found = bench.judged_look(kept, name, "B", kept, tmp_path / "judged")
    assert redrawn == [((tmp_path / "finished" / "final.glb").read_bytes(), view)], redrawn
    assert found["regressed"] == 0 and found["pictures"]["previous"] != found["pictures"]["made"], found


def light_held(tmp_path):
    """The look's light held to its close-up (#206): (held of a look drawn as the close-up, of one darker, of one as
    light but clipped white more; the reason a light step's gap gives, a pictured row's, a light step not run; whether
    a look under an unheld light was drawn)."""
    def picture(name, white, grey, edge=0):
        pixels = np.zeros((10, 10, 4), np.uint8)
        pixels[:, :, 3] = 255
        pixels.reshape(-1, 4)[:white, :3] = 255
        pixels.reshape(-1, 4)[white:, :3] = grey
        pixels.reshape(-1, 4)[100 - edge:] = (0, 0, 0, 128)  # the edge's part-covered pixels: never counted
        Image.fromarray(pixels, "RGBA").save(tmp_path / name)
        return tmp_path / name
    close_up = picture("light-close-up.png", 45, 155, edge=10)  # 45 clipped white of 90 opaque, the rest grey
    held = [bench.exposure_held(picture(f"light-{name}.png", white, grey), close_up)["held"]
            for name, white, grey in (("same", 50, 155), ("darker", 0, 120), ("clipped", 60, 130))]
    kept = bench.Kept(Store.in_folder(tmp_path / "light-store"), FolderBucket(tmp_path / "light-bucket"),
                      tmp_path / "light-index.json")
    kept.gap("simready_crate_blue_a01", "input", "light", "StepFailed: gap 0.2")
    reasons = [bench.unheld_light(kept, {"id": asset, **extra}) for asset, extra in (
        ("simready_crate_blue_a01", {}), ("cockpit_toggle_switch", {"picture": "a1"}), ("simready_desk_a01", {}))]
    drawn = []
    (tmp_path / "light-look").mkdir()
    with pytest.raises(bench.StepFailed, match="gap 0.2"):
        bench.look_step(None, None, {"id": "simready_crate_blue_a01"}, {}, lambda *given: drawn.append(given),
                        uncalibrated=reasons[0])(tmp_path / "light-look")
    return held, ["gap 0.2" in reasons[0], reasons[1], "not run" in reasons[2]], drawn


def drawer(scale, lit=0):
    """A stand-in for Blender: the object a red square with its true alpha; its shadow a half-dark band below it, the
    object there `lit` brighter (its floor lighting it). As look.py on NVIDIA's model (the light step's job, #206): the
    same red square."""
    def draw(_job_name, arguments, log, script=bench.SCRIPT):
        if script == bench.LOOK:
            rgba = np.zeros((PIXELS, PIXELS, 4), np.uint8)
            rgba[16:40, 16:48] = (200, 0, 0, 255)
            Image.fromarray(rgba, "RGBA").save(json.loads(open(arguments[0]).read())["out"])
            return 0
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
        shadow[16:40, 16:48, :3] += np.array([0, lit, lit], np.uint8)
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
        pictured_case(tmp_path, monkeypatch, name, material, box)
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
    if name == "simready_crate_blue_a01":  # the look's light held to the close-up (#206), once
        light = kept.store.checkout(kept.entry(name, "input", "light")["output"]) / "light.json"
        assert json.loads(light.read_text())["held"] is True
        assert light_held(tmp_path) == ([True, False, False], [True, None, True], [])
    if scale != 1.0:
        assert "gap" in found and "off" in found["gap"], found
        with pytest.raises(bench.StepFailed, match="exited 137 \\(killed past its 12 GB memory cap\\)"):
            bench.render_asset(row, {}, tmp_path / "killed", tmp_path / "killed-out", lambda *_: 137)
        ran = []
        monkeypatch.setattr(bench.subprocess, "run", lambda command, **_: ran.append(command) or
                            type("Done", (), {"returncode": 0})())
        bench.queued_blender("bench-cart", [], tmp_path / "queued.log")
        assert "MemoryMax=12G" in ran[0] and "OOMPolicy=continue" in ran[0], ran
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
    # the close-up draws the asset as the route's input does (#202): one its floor lights (tc6's stove walls read white
    # on the backdrop, steel in rgba.png) is refused
    with pytest.raises(bench.StepFailed, match="floor lights it"):
        bench.render_asset(row, {}, tmp_path / "lit-scratch", tmp_path / "lit", drawer(scale, lit=40))

    if failing is None:  # one asset through branch B's finish (the others' rows test the render and the steps)
        (variants, palette, addresses, left), side, family = finished_box(tmp_path, monkeypatch, name,
                                                                          tmp_path / "made.glb", folder / "rgba.png")
        assert set(addresses.values()) == {"surface/simready_m_plastic_grey_a01@1", "surface/rubber@1"}
        assert list(left) == ["surface/simready_m_atlas_a01@1", "surface/vent_round_holes@1"], left
        assert "one model" in left["surface/simready_m_atlas_a01@1"] and "pattern" in left["surface/vent_round_holes@1"]
        assert variants["families"]["plastic"]["variants"]["simready_m_plastic_grey_a01"]["token"] == \
            finish.token_of([0.2, 0.2, 0.2]) and finish.NEUTRAL in palette["tokens"]
        assert len(side["face_material"]) == len(side["faces"]) and (side["face_material"] >= 0).all()
        assert set(side["surfaces"].values()) <= set(addresses.values()), side["surfaces"]
        assert [(share["same_family"], share["unjudged"]) for share in family] == [(1.0, 0.0), (None, 1.0)], family
        # The marks read in their boxes grown by READ_MARGIN of the longer side (200 px: 30 each way); the one the
        # reader left unanswered is read as nothing (#185).
        looked_box = looked(tmp_path, name, view)
        assert patterned(tmp_path, name, folder / "rgba.png") == ([True], [(80.6, 0.0, 0.0)], [False], [False], [False], [True],
                                                                      [True])
        assert looked_box == (
            True, ["mask-0.png"], 255, 0.4, (bench.LOOK_SMALL, bench.LOOK_SMALL),
            round(200 / (finish.LOOK_SIDE // 2) ** 2, 5),
            [(260, 260), (57, 17)], [("03", "03"), ("Patient room", None)],
            (True, [0.1, -0.3, 0.2], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0], [0.12, -0.3, 0.2], 0.4)), name
        assert bench.look_found(tmp_path / "look") == {
            "holes": round(200 / (finish.LOOK_SIDE // 2) ** 2, 5), "read": 0.5,
            "misread": [{"text": "Patient room", "read": None}]}
        assert undrawn(tmp_path) == {}, "the look draws every recipe family"
        drawn, own = recoloured_step()
        assert drawn == pytest.approx(own, abs=0.5), (drawn, own)
        assert [finish.surface_look({"recipe": recipe})["opacity"] for recipe in ("glass", "rubber")] == [
            json.loads((pathlib.Path(finish.REPO) / "data/library/materials.json").read_text())["recipes"]["glass"][
                "opacity"], 1.0]  # a glass drawn see-through at its method's opacity, a rubber whole (#186)

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
