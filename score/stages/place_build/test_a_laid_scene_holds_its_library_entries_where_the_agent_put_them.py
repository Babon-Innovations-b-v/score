"""Invariant: the placing agent's scene holds each library entry it lays, where it lays it: a kit piece referenced
from its own copy under the place's assets, in metres in a y-up stage, its spot and turns snapped onto the grid; a
surface bound over the model's own colour (a variant as the library makes it, a recipe in the palette colour asked,
refused without one), or on one named part alone while the rest keeps the whole look; a glTF-only model converted with a
part a material, each wearing its own bake (its base colour map beside it, read by the mesh's texture coordinates),
a take's finished model laid before its raw one; a ground disc laid as the ground; a character dressed in its made body (its far one hidden) and held still in its clip, its own
SkelRoot kept; a ground marked as the ground; the dome shell's glass skin, curved ribs and deck as three parts at its radius;
a batch of steps run in one call, a refused one named while the rest go on; a lamp where it is laid; an entry with no
USD refused by name, a removed object gone; a real terrain's heightfield (fine posts near its centre, wider out, its gaps
filled) laid as the ground with its building pads levelled to the laid height and the ground beyond untouched; a sky
laid as the place's own Environment with a sun shining from where it is asked; the place's palette (a scene's surface
library) laid as a recipe spec on a look at its wear and dirt; a dome cut at an opening (glass and plinth) and a tunnel
with a doorway in its end wall (its rim round on the tube's circle, never stepped), its skin trimmed by the dome it
joins and solid below its glass; a model's glow layer
laid with it as a part; a stair core whose treads look up (the walkers' floor reads them as floor) and rise no more
than a knee, its flat's doorway cut through its back wall; a final render at 1920x1080; a film's path held on the concept's view, round a wall at eye height and clear of it, easing to a stop; a named view listed beside the
concept's for the render; and the compare measures the render's silhouette against the concept's object masks (overlap, each object's cover) and the
colour difference of the two pictures, and draws them side by side; and a review of a region holds its laid objects
(never the ground or the sky), each dome shell structure a compartment, a door's eye-height view, a plan seen
straight down under its cut with +x right and +z down, and a physics fault boxed in red and named on the plan.

Breaks that turn this red (each applied once and seen red, then reverted):
- place_build.posed: the rotate op left out -> the turned piece's box stays unturned
- place_build.snap: `on_grid` on the height too -> the lifted piece drops to the grid
- place_build.tinted: the colour set on the diffuse input though a map feeds it -> the sand's map keeps no tint
- place_build.look_shader: `strongerThanDescendants` made `weakerThanDescendants` -> the piece's own look wins
- place_build.usd_file: the first file taken whatever its role -> a record-only entry is laid
- place_build.rebind: the whole look left off the unnamed parts -> the crate's lid keeps its baked green
- place_build.laid_reference: the prim defined as an Xform -> the character's prim is an Xform, not its SkelRoot
- place_build.dressed: WORN's "made" made "far" -> the far body shows and the made one is hidden
- gltf.part_name: the material's name dropped (`part_<n>` always) -> the glTF's parts lose their names
- gltf.look: the maps left out -> the door part wears no base colour map (its bake is lost)
- place_build.finished_first: `-final` not ranked first -> the take's raw model is laid
- place_build.ground: the ground mark left False -> the laid disc is no ground
- dome_shell.ribs: the rib lifted inward (`- out`) -> the dome's box stays inside its radius
- place_build.rested: the lift's sign flipped -> the shelf on the table sinks a metre under it
- dome_shell.hoop_ribs: the hoop lifted inward (`- out`) -> the tunnel's box stays inside its radius
- place_build.ground_height: the nearest point's x read for its height -> the stone floats far off the slope
- place_build.ground_height: no face searched (the nearest points' weighted height) -> the stone stands off the
  slope's plane by more than a millimetre
- place_build.batch: a refused step stops the batch -> the step after it is never laid
- measure.coverage: `shape & silhouette` made `shape` -> the uncovered object reads covered
- relief.graded_axis: FAR_GROWTH left off (every post 1 m) -> the far posts are not wider than the near ones
- relief.filled: the gap left NaN -> the terrain holds a NaN height
- relief.padded_file: the pad's share inverted (`keep = eased`) -> the pad keeps its slope, the far ground goes flat
- relief.turned_pads: the turn's sine signs swapped -> the pad lands off the dome's spot on the turned terrain
- place_build.sun_frame: `towards` negated -> the sun shines up from under the ground
- place_build.sky: the turn left off the dome -> the sky dome stays unturned
- render.views: the named views left out -> the inside view is not rendered
- render.views: `review` kept True when final -> the final render runs at the review's samples
- dome_shell.chamfered_box: the outward flip dropped -> a block's solid has negative volume (faces inward)
- place_build.blocks: the structure role not written -> a building's blocks read as a loose prop to the check
- place_build.put: role and support not written -> a window flush on its wall reads as a floating prop
- place_build.night: the exposure left off -> the night renders at the day's exposure
- dome_shell.skin: the opening's faces kept instead of dropped -> the holed dome's glass closes its opening
- dome_shell.end_wall: the doorway a third narrower -> the end wall stands in the doorway
- dome_shell.on_circle: a corner kept where it lies -> the end wall's rim steps out past the tube's circle
- dome_shell.tube_skin: the trim inverted -> the hall's skin stands inside the dome it joins
- dome_shell.tube_sides: no lower wall split off -> the hall's glass reaches its deck
- place_build.surface: the palette spec left off the look -> the panel's look carries no recipe spec
- film.route: every leg straight, never walked -> the lane's film finds no clear way round its wall
- film.distances: the hold drifting at 0.1 m a frame -> the film does not open still on the concept's view
- film.rounded: the cut corners kept unchecked -> a frame stands nearer the wall than the clearance
- film.distances: the walk's speed kept to the end -> the camera does not slow to a stop
- place_build.palette_spec: the place's wear and dirt replaced by 0 -> the spec's wear is not the palette's
- stair_core.outward: `volume > 0` made `volume < 0` -> the treads look down
- stair_core.holed: the holes left out -> the back wall stands in the flat's doorway
- render.views: FINAL_SIZE left off -> the final render keeps the concept's aspect
- place_build.layered: the layer mark left off -> the monitor's glow is no part and its screen takes no surface
- measure.lab: a and b read unsigned -> the concept's blue reads yellow (b over 0)
- review.region_of: the ground mark not read (`not item["ground"]` dropped) -> the terrain and sky join the region
- review.compartments_of: the dome shell address test dropped -> the wall is a compartment
- review.projected: the up axis negated -> the plan's +z lands up, the aim's point off the middle
- review.views_of: the plan's near cut at the floor (CUT left off) -> the plan's cut is not CUT over the floor
- review.boxed_faults: the fault's name test inverted -> no red box on the floating crate
"""
import json
import pathlib

import trimesh

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdSkel, Vt

from score.stages import place_build
from score.stages.place_build import film, measure, relief, render, review, stair_core


def library(root, files):
    """A small library: a kit piece (a 1 x 2 x 0.5 m box in its own baked green), a variant surface and a recipe,
    a lamp, and a record-only kit entry; its files under `files` by their references."""
    def entry(kind, entry_id, named):
        folder = root / "entries" / kind / entry_id / "1"
        folder.mkdir(parents=True)
        folder.joinpath("entry.json").write_text(json.dumps({
            "schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1", "kind": kind, "id": entry_id,
            "version": 1, "files": {name: {"role": role} for name, (role, _) in named.items()}}))
        for name, (_, text) in named.items():
            target = files / f"{kind}/{entry_id}@1/{name}"
            target.parent.mkdir(parents=True, exist_ok=True)
            if text is not None:
                target.write_text(text)
    piece = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(piece, UsdGeom.Tokens.y)
    root_prim = UsdGeom.Xform.Define(piece, "/box")
    piece.SetDefaultPrim(root_prim.GetPrim())
    cube = UsdGeom.Cube.Define(piece, "/box/geo")
    cube.AddTranslateOp().Set(Gf.Vec3d(0.5, 1.0, 0.25))
    cube.AddScaleOp().Set(Gf.Vec3f(0.5, 1.0, 0.25))
    cube.CreateSizeAttr(2.0)
    own = UsdShade.Material.Define(piece, "/box/baked")
    baked = UsdShade.Shader.Define(piece, "/box/baked/surface")
    baked.CreateIdAttr("UsdPreviewSurface")
    baked.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.0, 1.0, 0.0))
    own.CreateSurfaceOutput().ConnectToSource(baked.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(cube.GetPrim()).Bind(own)
    lid = UsdGeom.Mesh.Define(piece, "/box/lid")
    lid.CreatePointsAttr(Vt.Vec3fArray([(0, 2, 0), (1, 2, 0), (1, 2, 0.5), (0, 2, 0.5)]))
    lid.CreateFaceVertexCountsAttr([3, 3])
    lid.CreateFaceVertexIndicesAttr([0, 1, 2, 0, 2, 3])
    UsdGeom.Subset.CreateGeomSubset(lid, "top", UsdGeom.Tokens.face, [0], "materialBind")
    rim = UsdGeom.Subset.CreateGeomSubset(lid, "rim", UsdGeom.Tokens.face, [1], "materialBind")
    UsdShade.MaterialBindingAPI.Apply(rim.GetPrim()).Bind(own)  # a part in its own baked green
    entry("kit", "box_piece", {"piece.usda": ("usd", piece.GetRootLayer().ExportToString()),
                               "piece.json": ("record", "{}")})
    entry("kit", "plan_only", {"plan.json": ("record", "{}")})
    glb = tmp_glb(root.parent)
    entry("model", "cabinet", {"cabinet.glb": ("gltf", None)})
    (files / "model/cabinet@1/cabinet.glb").write_bytes(glb)
    entry("take", "cup", {"cup.glb": ("gltf", None), "cup-final.glb": ("gltf", None)})
    for name in ("cup.glb", "cup-final.glb"):
        (files / f"take/cup@1/{name}").write_bytes(glb)
    entry("character", "walker", {"character.usda": ("usd", character())})
    variant = ('#usda 1.0\n(\n defaultPrim = "steel"\n)\ndef Material "steel"\n{\n token outputs:surface.connect = '
               '</steel/surface.outputs:surface>\n def Shader "surface"\n {\n  uniform token info:id = '
               '"UsdPreviewSurface"\n  color3f inputs:diffuseColor = (0.3, 0.3, 0.4)\n  token outputs:surface\n }\n}\n')
    entry("surface", "steel", {"material.usda": ("usd", variant), "surface.json": ("record", "{}")})
    mapped = ('#usda 1.0\n(\n defaultPrim = "sand"\n)\ndef Material "sand"\n{\n token outputs:surface.connect = '
              '</sand/surface.outputs:surface>\n def Shader "colour"\n {\n  uniform token info:id = "UsdUVTexture"\n'
              '  asset inputs:file = @./colour.jpg@\n  float3 outputs:rgb\n }\n def Shader "surface"\n {\n'
              '  uniform token info:id = "UsdPreviewSurface"\n  color3f inputs:diffuseColor.connect = '
              '</sand/colour.outputs:rgb>\n  token outputs:surface\n }\n}\n')
    entry("surface", "sand", {"material.usda": ("usd", mapped), "surface.json": ("record", "{}")})
    entry("surface", "boards", {"surface.json": ("record", json.dumps({"settings": {"roughness": 0.7}}))})
    entry("light", "lamp", {"lamps.json": ("record", "{}")})
    screen_glow = piece.GetRootLayer().ExportToString().replace('"box"', '"glow"').replace("</box/", "</glow/")
    entry("model", "monitor", {"model.usda": ("usd", piece.GetRootLayer().ExportToString()),
                               "model_glow.usda": ("usd", screen_glow)})
    entry("model", "slope", {"terrain.usdc": ("usd", None)})
    heights = np.add.outer(np.arange(301) * 0.1, np.zeros(301))  # rising 0.1 m a metre down the rows, 300 m square
    heights[150, 40] = np.nan  # a no-data post
    relief.heightfield_file(relief.filled(heights), 1.0, files / "model/slope@1/terrain.usdc", near=20.0)
    sky = ('#usda 1.0\n(\n defaultPrim = "sky_dome"\n)\ndef Xform "sky_dome"\n{\n def DomeLight "Environment"\n {\n'
           '  float inputs:intensity = 0.2\n }\n}\n')
    entry("light", "sky", {"sky.usda": ("usd", sky)})


def part_middles(mesh, part):
    """The middles of a mesh's faces in one named part (its GeomSubset), in its own frame."""
    points = np.array(mesh.GetPointsAttr().Get())
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.array(mesh.GetFaceVertexIndicesAttr().Get())
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    subset = next(item for item in UsdGeom.Subset.GetAllGeomSubsets(mesh) if item.GetPrim().GetName() == part)
    return np.array([points[indices[starts[face]:starts[face] + counts[face]]].mean(axis=0)
                     for face in subset.GetIndicesAttr().Get()])


def part_facings(mesh, part):
    """Each face of a named part as its middle (x, y, z) and its unit normal by its winding (nx, ny, nz)."""
    points = np.array(mesh.GetPointsAttr().Get(), dtype=float)
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.array(mesh.GetFaceVertexIndicesAttr().Get())
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    subset = next(item for item in UsdGeom.Subset.GetAllGeomSubsets(mesh) if item.GetPrim().GetName() == part)
    found = []
    for face in subset.GetIndicesAttr().Get():
        corners = points[indices[starts[face]:starts[face] + counts[face]]]
        normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
        found.append(np.concatenate([corners.mean(axis=0), normal / np.linalg.norm(normal)]))
    return np.array(found)


def part_bounds(mesh, part):
    """Each face of a named part as its box: (faces, 2, 3), low and high corners."""
    points = np.array(mesh.GetPointsAttr().Get(), dtype=float)
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.array(mesh.GetFaceVertexIndicesAttr().Get())
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    subset = next(item for item in UsdGeom.Subset.GetAllGeomSubsets(mesh) if item.GetPrim().GetName() == part)
    return np.array([[points[indices[starts[face]:starts[face] + counts[face]]].min(axis=0) - 1e-6,
                      points[indices[starts[face]:starts[face] + counts[face]]].max(axis=0) + 1e-6]
                     for face in subset.GetIndicesAttr().Get()])


def tmp_glb(folder):
    """A glTF of two boxes, one in a material named `door` baked in a red map, one in an unnamed one, the second
    lifted 1 m."""
    door = trimesh.creation.box((1, 1, 1))
    door.visual = trimesh.visual.TextureVisuals(
        uv=np.zeros((len(door.vertices), 2)), material=trimesh.visual.material.PBRMaterial(
            name="door", baseColorTexture=Image.new("RGB", (4, 4), (200, 0, 0))))
    body = trimesh.creation.box((1, 1, 1))
    body.apply_translation((0, 1, 0))
    body.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial())
    return trimesh.Scene([door, body]).export(file_type="glb")


def character():
    """A character asset as tools/characters makes one: its body groups `far` and `made` invisible, a one-joint
    skeleton and its clip `standing` (the joint 1 m up at its start)."""
    body = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(body, UsdGeom.Tokens.y)
    root = UsdSkel.Root.Define(body, "/Character")
    body.SetDefaultPrim(root.GetPrim())
    root.GetPrim().SetCustomDataByKey("score:clip_seconds", {"standing": 1.0})
    UsdGeom.Xform.Define(body, "/Character/Turned")
    UsdSkel.Skeleton.Define(body, "/Character/Turned/Skeleton").CreateJointsAttr(["hips"])
    for group in ("far", "made"):
        UsdGeom.Xform.Define(body, f"/Character/Turned/Body/{group}").MakeInvisible()
        UsdGeom.Cube.Define(body, f"/Character/Turned/Body/{group}/shape")
    clip = UsdSkel.Animation.Define(body, "/Character/Animations/standing")
    clip.CreateJointsAttr(["hips"])
    clip.CreateTranslationsAttr().Set(Vt.Vec3fArray([(0, 1, 0)]), 0)
    clip.CreateRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(1)]), 0)
    clip.CreateScalesAttr().Set(Vt.Vec3hArray([Gf.Vec3h(1)]), 0)
    return body.GetRootLayer().ExportToString()


def shown_ground(stage, shown):
    """(the laid ground disc's ground mark, its parts)."""
    return (stage.GetPrimAtPath("/yard/Objects/regolith").GetAttribute("score:ground").Get(),
            next(item for item in shown["objects"] if item["name"] == "regolith")["parts"])


def bound_colour(stage, path):
    look = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath(path)).ComputeBoundMaterial()[0]
    return tuple(UsdShade.Shader(stage.GetPrimAtPath(f"{look.GetPath()}/surface")).GetInput("diffuseColor").Get())


def pictures(folder):
    """A concept (blue left half, its object the left half) and a render (blue, its silhouette the left quarter)."""
    concept = np.zeros((40, 80, 3), np.uint8)
    concept[:, :40] = (30, 60, 200)
    Image.fromarray(concept).save(folder / "concept.png")
    Image.fromarray(concept).save(folder / "render.png")
    silhouette = np.zeros((40, 80, 4), np.uint8)
    silhouette[:, :20, 3] = 255
    Image.fromarray(silhouette).save(folder / "render-mask.png")
    object_mask = np.zeros((40, 80), np.uint8)
    object_mask[:, :40] = 255
    Image.fromarray(object_mask).save(folder / "left.png")
    (folder / "objects.json").write_text(json.dumps([{"word": "wall", "box": [0, 0, 40, 40], "score": 0.9,
                                                      "mask": str(folder / "left.png")}]))


def test_a_laid_scene_holds_its_library_entries_where_the_agent_put_them(tmp_path, monkeypatch):
    root, files, folder = tmp_path / "lib", tmp_path / "files", tmp_path / "place"
    library(root, files)
    monkeypatch.setenv("SCORE_LIB_ROOT", str(root))
    monkeypatch.setenv("SCORE_LIB_FILES", str(files))
    Image.new("RGB", (80, 40)).save(tmp_path / "concept.png")
    place_build.start(folder, "yard", tmp_path / "concept.png")
    laid = place_build.put(folder, "wall", "kit/box_piece", at=(1.2, 0.3, -0.8), turn=(0, 80, 0))
    snapped = place_build.snap(folder, "wall", grid=0.5)
    place_build.put(folder, "crate", "kit/box_piece@1", at=(3, 0, 0))
    place_build.surface(folder, "wall", "surface/steel")
    place_build.surface(folder, "crate", "surface/boards", colour="#ff0000")
    place_build.surface(folder, "crate", "surface/steel", part="top")
    place_build.put(folder, "dune", "kit/box_piece", at=(6, 0, 0))
    place_build.surface(folder, "dune", "surface/sand", colour="#ff8000")
    place_build.light(folder, "bulb", at=(0, 2.5, 0), watts=100)
    (tmp_path / "palette.json").write_text(json.dumps({
        "recipes": {"boards": {"roughness": 0.7}}, "tokens": {"hull": "#ff0000", "dust": "#00ff00"}, "dirt": "dust",
        "families": {"paint": {"variants": {"hull_paint": {"recipe": "boards", "token": "hull", "seed": 3}}}}}))
    place_build.palette(folder, tmp_path / "palette.json", wear=0.4, dirt=0.3)
    place_build.put(folder, "screen", "model/monitor", at=(12, 0, 0))
    place_build.surface(folder, "screen", "palette/hull_paint", part="glow")
    place_build.put(folder, "panel", "kit/box_piece", at=(14, 0, 0))
    place_build.surface(folder, "panel", "palette/hull_paint")
    batched = place_build.batch(folder, [
        {"step": "put", "name": "floor", "address": "kit/box_piece", "at": [0, -2, 0], "scale": 4, "ground": True},
        {"step": "put", "name": "missing", "address": "kit/plan_only"},
        {"step": "put", "name": "cabinet", "address": "model/cabinet"},
        {"step": "put", "name": "walker", "address": "character/walker", "at": [2, 0, 2]},
        {"step": "dome", "name": "dome", "radius": 5.0, "meridians": 8, "rings": 2, "rib": 0.1},
        {"step": "dome", "name": "holed", "radius": 5.0, "at": [40, 0, 0], "openings": [[0, 1.2, 1.0]]},
        {"step": "tube", "name": "hall", "radius": 1.5, "length": 3.0, "at": [60, 0, 0], "cap": [1.6, 2.0],
         "trims": [[0, 0, -3.0, 4.0]]},
        {"step": "ground", "name": "regolith", "radius": 3.0},
        {"step": "put", "name": "cup", "address": "take/cup"},
        {"step": "tube", "name": "tunnel", "radius": 1.5, "length": 4.0, "at": [20, 0, 0], "hoops": 3},
        {"step": "put", "name": "shelf", "address": "model/cabinet", "at": [9, 0.75, 0], "rest": True},
        {"step": "stairs", "name": "stairwell", "storeys": 1, "mirror": True}])
    refusals = []
    for step in (lambda: place_build.put(folder, "plan", "kit/plan_only"),
                 lambda: place_build.surface(folder, "wall", "surface/boards")):
        try:
            step()
        except place_build.Refused as why:
            refusals.append(str(why))
    place_build.terrain(folder, "plain", "model/slope", at=(0, 0, 0), turn=(0, 90, 0), pads=[(30.0, 0.0, 5.0)])
    place_build.sky(folder, "light/sky", elevation=30, heading=0, turn=30)
    place_build.view(folder, "inside", eye=(0, 1.6, 0), aim=(1, 1.6, 0), fov=70)
    stone = place_build.put(folder, "stone", "model/cabinet", at=(80, -0.1, 0), rest=True, on_ground=True)
    place_build.put(folder, "gone", "kit/box_piece")
    place_build.remove(folder, "gone")
    shown = place_build.listing(folder)
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    boxes = {item["name"]: item["box"] for item in shown["objects"]}
    pictures(folder)
    compared = measure.compare(folder)
    assert (laid["usd"], snapped["at"], snapped["turn"]) == ("./assets/kit/box_piece/1/piece.usda", [1.0, 0.3, -1.0],
                                                             [0.0, 90.0, 0.0])
    assert (UsdGeom.GetStageUpAxis(stage), UsdGeom.GetStageMetersPerUnit(stage)) == ("Y", 1.0)
    assert np.allclose(boxes["wall"], [[1.0, 0.3, -2.0], [1.5, 2.3, -1.0]], atol=1e-3)
    assert np.allclose(boxes["crate"], [[3.0, 0.0, 0.0], [4.0, 2.0, 0.5]], atol=1e-3)
    assert np.allclose(bound_colour(stage, "/yard/Objects/wall/geo"), (0.3, 0.3, 0.4))
    assert np.allclose(bound_colour(stage, "/yard/Objects/crate/geo"), (1.0, 0.0, 0.0))
    assert np.allclose(bound_colour(stage, "/yard/Objects/crate/lid/top"), (0.3, 0.3, 0.4))
    assert np.allclose(bound_colour(stage, "/yard/Objects/crate/lid/rim"), (1.0, 0.0, 0.0))
    tint = UsdShade.Shader(stage.GetPrimAtPath("/yard/Looks/dune/colour")).GetInput("scale").Get()
    assert np.allclose(tint, (1.0, 0.2158605, 0.0, 1.0), atol=1e-5)
    assert ["no USD file" in answer.get("refused", "") for answer in batched] == [False, True] + [False] * 10
    door_look = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath("/yard/Objects/cabinet/geo/door")).ComputeBoundMaterial()[0]
    door_map = UsdShade.Shader(stage.GetPrimAtPath(f"{door_look.GetPath()}/base")).GetInput("file").Get()
    assert np.allclose(Image.open(door_map.resolvedPath).getpixel((0, 0)), (200, 0, 0))
    assert UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/yard/Objects/cabinet/geo")).GetPrimvar("st").HasValue()
    assert batched[8]["usd"].endswith("cup-final.usdc") and shown_ground(stage, shown) == (True, {"ground": None})
    assert stage.GetPrimAtPath("/yard/Objects/floor").GetAttribute("score:ground").Get() is True
    cabinet_parts = sorted(next(item for item in shown["objects"] if item["name"] == "cabinet")["parts"])
    assert cabinet_parts[0] == "door" and cabinet_parts[1].startswith("part_") and len(cabinet_parts) == 2
    assert np.allclose(boxes["cabinet"], [[-0.5, -0.5, -0.5], [0.5, 1.5, 0.5]], atol=1e-3)
    assert np.allclose(boxes["shelf"], [[8.5, 0.75, -0.5], [9.5, 2.75, 0.5]], atol=1e-3)
    walker = stage.GetPrimAtPath("/yard/Objects/walker")
    shown_groups = {group: UsdGeom.Imageable(stage.GetPrimAtPath(f"/yard/Objects/walker/Turned/Body/{group}"))
                    .ComputeVisibility() for group in ("far", "made")}
    held = UsdSkel.Animation(stage.GetPrimAtPath("/yard/Objects/walker/Held"))
    assert (walker.GetTypeName(), shown_groups) == ("SkelRoot", {"far": "invisible", "made": "inherited"})
    assert list(held.GetTranslationsAttr().Get()) == [Gf.Vec3f(0, 1, 0)] and batched[3]["clip"] == "standing"
    spec = json.loads(stage.GetPrimAtPath("/yard/Looks/panel").GetAttribute("score:recipe:spec").Get())
    assert (spec["recipe"], spec["wear"], spec["dirt"], spec["dirt_colour"], spec["hex"]) == ("boards", 0.4, 0.3,
                                                                                               [0.0, 1.0, 0.0], "#ff0000")
    assert stage.GetPrimAtPath("/yard/Objects/panel").GetAttribute("score:surface").Get() == "surface/boards@1"
    assert np.allclose(bound_colour(stage, "/yard/Objects/screen/glow/geo"), (1.0, 0.0, 0.0))
    assert np.allclose(bound_colour(stage, "/yard/Objects/screen/geo"), (0.0, 1.0, 0.0))
    holed = UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/holed/geo"))
    shell_middles = part_middles(holed, "shell")
    in_hole = (shell_middles[:, 0] > 0) & (np.hypot(shell_middles[:, 1] - 1.0, shell_middles[:, 2]) < 1.2)
    base_middles = part_middles(holed, "base")
    assert not in_hole.any() and len(shell_middles) > 1000
    assert not ((base_middles[:, 0] > 4.0) & (np.abs(base_middles[:, 2]) < 0.5)).any() and len(base_middles)
    hall = UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/hall/geo"))
    cap_middles, hall_skin = part_middles(hall, "cap"), np.vstack([part_middles(hall, "shell"), part_middles(hall, "wall")])
    doorway = (np.abs(cap_middles[:, 0]) < 0.75) & (cap_middles[:, 1] > 0.5) & (cap_middles[:, 1] < 2.4)
    assert len(cap_middles) and not doorway.any() and np.allclose(cap_middles[:, 2].max(), 3.0, atol=0.01)
    cap_points = np.array(hall.GetPointsAttr().Get())[np.array(hall.GetFaceVertexIndicesAttr().Get()).reshape(-1, 4)[
        np.array(next(item for item in UsdGeom.Subset.GetAllGeomSubsets(hall) if item.GetPrim().GetName() == "cap")
                 .GetIndicesAttr().Get())]].reshape(-1, 3)
    off_axis = np.hypot(cap_points[:, 0], cap_points[:, 1] - 1.5)
    assert off_axis.max() <= 1.5 + 1e-5 and np.count_nonzero(off_axis > 1.5 - 1e-5) > 50
    assert np.linalg.norm(hall_skin - [0.0, 0.0, -3.0], axis=1).min() >= 4.0 and hall_skin[:, 2].min() < 0.5
    assert part_middles(hall, "wall")[:, 1].max() < 0.45 + 0.8 < part_middles(hall, "shell")[:, 1].min()
    assert sorted(next(item for item in shown["objects"] if item["name"] == "dome")["parts"]) == ["base", "deck", "ribs", "shell"]
    assert sorted(next(item for item in shown["objects"] if item["name"] == "tunnel")["parts"]) == ["deck", "ribs", "shell", "wall"]
    assert np.allclose(boxes["tunnel"], [[18.38, -0.12, 0.0], [21.62, 3.12, 4.0]], atol=0.01)
    assert np.allclose(boxes["dome"], [[-5.18, 0.0, -5.18], [5.18, 5.1, 5.18]], atol=0.02)  # its plinth
    assert shown["lights"] == [{"name": "bulb", "at": [0.0, 2.5, 0.0], "watts": 100.0},
                              {"name": "sun", "at": [0, 0, 0], "watts": 1.0}]
    assert "no USD file" in refusals[0] and "give --colour" in refusals[1] and len(refusals) == 2
    assert set(boxes) == {"wall", "crate", "floor", "cabinet", "walker", "dome", "regolith", "cup", "plain", "sky", "shelf", "tunnel", "stone", "dune", "screen", "holed", "hall", "panel", "stairwell"} and not stage.GetPrimAtPath("/yard/Objects/gone")
    laid_terrain = stage.GetPrimAtPath("/yard/Objects/plain")
    ground_points = np.array(UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/plain/geo")).GetPointsAttr().Get())
    in_pad = np.hypot(ground_points[:, 0], ground_points[:, 2] - 30.0) < 5.0  # the terrain's own frame
    far = np.abs(ground_points[:, 2]) > 100.0
    posts = np.diff(np.unique(ground_points[:, 0]))
    assert laid_terrain.GetAttribute("score:ground").Get() and np.isfinite(ground_points).all()
    assert np.allclose(ground_points[in_pad, 1], 0.0) and np.ptp(ground_points[far, 1]) > 20.0
    assert posts.max() > 2.0 and np.isclose(posts.min(), 1.0)
    assert np.isclose(stone["at"][1], 0.5 + 8.0 - 0.1, atol=0.001)  # 80 m along the turned slope: 8 m up, on its face
    sun = UsdGeom.Xformable(stage.GetPrimAtPath("/yard/Lights/sun")).ComputeLocalToWorldTransform(0)
    shines = sun.TransformDir(Gf.Vec3d(0, 0, -1))
    assert stage.GetPrimAtPath("/yard/Environment").GetAttribute("inputs:intensity").Get() == np.float32(0.2)
    assert np.allclose(shines, (-np.cos(np.radians(30)), -0.5, 0.0), atol=1e-6)
    assert place_build.pose_of(stage.GetPrimAtPath("/yard/Objects/sky"))[1] == [0.0, 30.0, 0.0]
    final = render.views(place_build.record_of(folder), 80, [], final=True)
    assert final["review"] is False and final["size"] == [1920, 1080]
    core = UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/stairwell/geo"))
    treads, walls = part_facings(core, "steps"), part_bounds(core, "wall")
    up = treads[np.abs(treads[:, 4]) > 0.99]
    rises = np.diff(np.unique(np.round(up[up[:, 4] > 0, 1], 3)))
    door = batched[11]["doorways"][1]  # the first floor's flat door, in the back wall
    middle = (stair_core.LONG - (door[1] + door[2]) / 2, (door[3] + door[4]) / 2, stair_core.DEEP + stair_core.WALL / 2)
    in_door = np.all((walls[:, 0, :2] <= middle[:2]) & (walls[:, 1, :2] >= middle[:2]), axis=1) \
        & (np.abs(walls[:, 0, 2] - middle[2]) <= stair_core.WALL / 2 + 1e-3)  # a wall face across the doorway
    assert len(up) and (up[:, 4] > 0).all() and rises.max() <= 0.3 and not in_door.any()
    listed_views = render.views(place_build.record_of(folder), 80, ["inside"])["views"]
    assert [view["name"] for view in listed_views] == ["concept", "inside"] and listed_views[1]["look_only"]
    assert (compared["layout_iou"], compared["objects"][0]["covered"], compared["colour"]["mean"]) == (0.5, 0.5, 0.0)
    assert measure.lab(Image.open(folder / "concept.png").convert("RGB"))[0, 0, 2] < -40
    assert Image.open(compared["picture"]).size == (3 * measure.PANEL, measure.PANEL // 2)
    built = place_build.blocks(folder, "kerb", [[0, 0, 0, 2, 0.15, 0.3, "kerb"], [0, 0, 0.3, 2, 0.004, 0.5, "line"]],
                               at=(50, 0, 50))
    place_build.blocks(folder, "road", [[0, -0.3, 0, 4, 0, 4, "road"]], at=(60, 0, 60), ground=True)
    place_build.put(folder, "sill", "kit/box_piece", at=(50, 1, 52), role="mount", support="wall:kerb")
    place_build.night(folder, [0.01, 0.04, 0.08], [0.01, 0.04, 0.08], 2.5,
                      {"elevation": 30, "heading": 90, "strength": 0.01, "colour": [0.5, 0.7, 1.0]})
    stage = Usd.Stage.Open(str(folder / "scene.usda"))
    kerb = trimesh.Trimesh(*[np.array(value) for value in (
        UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/kerb/geo")).GetPointsAttr().Get(),
        np.array(UsdGeom.Mesh(stage.GetPrimAtPath("/yard/Objects/kerb/geo")).GetFaceVertexIndicesAttr().Get()
                 ).reshape(-1, 3))]).split(only_watertight=False)
    marks = {name: [stage.GetPrimAtPath(f"/yard/Objects/{name}").GetAttribute(f"score:{key}").Get()
                    for key in ("role", "support", "ground")] for name in ("kerb", "road", "sill")}
    moon = UsdGeom.Xformable(stage.GetPrimAtPath("/yard/Lights/moon")).ComputeLocalToWorldTransform(0)
    assert built["boxes"] == 2 and len(kerb) == 2 and all(piece.is_watertight and piece.volume > 0 for piece in kerb)
    assert sorted(subset.GetPrim().GetName() for subset in UsdGeom.Subset.GetAllGeomSubsets(
        UsdGeom.Imageable(stage.GetPrimAtPath("/yard/Objects/kerb/geo")))) == ["kerb", "line"]
    assert marks == {"kerb": ["structure", None, False], "road": [None, None, True], "sill": ["mount", "wall:kerb", False]}
    assert stage.GetPrimAtPath("/yard/Environment").GetAttribute("score:exposure").Get() == np.float32(2.5)
    assert np.allclose(moon.TransformDir(Gf.Vec3d(0, 0, -1)), (0.0, -0.5, -np.cos(np.radians(30))), atol=1e-6)
    reviewed(folder)
    filmed(tmp_path)


def reviewed(folder):
    """The review's region, views, projection and fault marks on the laid scene (no Blender)."""
    objects = review.scene_objects(folder)
    region = review.region_of(objects, box=(-6.0, -6.0, 6.0, 6.0))
    compartments = review.compartments_of({}, objects, region)
    door = {"name": "airlock", "address": "model/airlock_door", "low": np.array([4.0, 0.0, -1.0]),
            "high": np.array([5.0, 2.0, 1.0]), "ground": False}
    region["names"].append("airlock")
    views = review.views_of(region, compartments, review.doors_of(objects + [door], region),
                            review.floor_of(objects, compartments, region))
    left_out = {"plain", "sky", "floor", "regolith", "tunnel"}
    assert {"wall", "crate", "dome"} <= set(region["names"]) and not left_out & set(region["names"])
    assert [part["name"] for part in compartments] == ["dome"]
    assert [view["name"] for view in views] == ["plan", "corner_wn", "corner_en", "corner_es", "corner_ws",
                                                "door_airlock", "middle", "part_dome"]
    plan, door_view = views[0], views[5]
    assert np.isclose(plan["eye"][1] - plan["near"], review.CUT) and np.allclose(door_view["eye"][1], review.EYE)
    size = (400, 300)
    middle = (np.array(plan["aim"]))
    seen, _ = review.projected(plan, size, [middle, middle + [1, 0, 0], middle + [0, 0, 1]])
    scale = size[0] / plan["ortho"]
    assert np.allclose(seen, [[200, 150], [200 + scale, 150], [200, 150 + scale]])
    assert np.allclose(review.projected(door_view, size, [door_view["aim"]])[0], [[200, 150]])
    (folder / review.CHECK).write_text(json.dumps({"faults": [{"object": "crate", "kind": "floating"}]}))
    faults = review.faults_of(folder)
    marked = np.asarray(review.annotated(Image.new("RGB", size), plan, objects, region, faults))
    crate = review.projected(plan, size, [[3.0, 0.0, 0.0], [4.0, 0.0, 0.5]])[0].round().astype(int)
    red = (marked[..., 0] > 200) & (marked[..., 1] < 50) & (marked[..., 2] < 50)
    around = red[crate[0][1] - 2:crate[1][1] + 3, crate[0][0] - 2:crate[1][0] + 3].sum()
    assert faults == {"crate": "floating"} and around > 10 and red.sum() == around


def filmed(tmp_path):
    """A film's path on a lane walled across but for a gap: still on the concept's view first, round the wall
    (never through it) at eye height, every frame clear of every solid, and slowing to a stop at its end."""
    folder = tmp_path / "lane"
    place_build.start(folder, "lane", tmp_path / "concept.png")
    place_build.blocks(folder, "road", [[-12, -0.3, -12, 12, 0, 30, "road"]], ground=True)
    place_build.blocks(folder, "wall", [[-12, 0, 9.5, 1, 3, 10.5, "wall"]])
    place_build.camera(folder, (0, 8, -12), (0, 0, 10), 40)
    made = film.path(folder, ["-4,4", "-4,16>-4,1.6,30"], seconds=6.0)
    frames = json.loads((folder / "film" / "path.json").read_text())["views"]
    eyes = np.array([frame["eye"] for frame in frames])
    crossing = eyes[np.abs(eyes[:, 2] - 10.0) < 0.6]
    steps = np.linalg.norm(np.diff(eyes, axis=0), axis=1)
    assert made["frames"] == 6 * film.FPS == len(frames) and made["frames_too_near"] == 0
    assert np.allclose(eyes[:film.FPS], [0, 8, -12], atol=0.05) and frames[0]["fov"] == 40
    assert np.allclose(frames[0]["aim"], np.array([0, 8, -12]) + 10 * np.array([0, -8, 22]) / np.hypot(8, 22), atol=0.01)
    assert len(crossing) and (crossing[:, 0] > 1.0 + film.CLEAR).all() and np.isclose(eyes[-1, 1], film.EYE, atol=0.01)
    assert made["least_clearance"] >= film.CLEAR and steps[-3:].max() < steps.max() / 4

