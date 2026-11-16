"""Invariant: the placing agent's scene holds each library entry it lays, where it lays it: a kit piece referenced
from its own copy under the place's assets, in metres in a y-up stage, its spot and turns snapped onto the grid; a
surface bound over the model's own colour (a variant as the library makes it, a recipe in the palette colour asked,
refused without one), or on one named part alone while the rest keeps the whole look; a glTF-only model converted with a
part a material, each wearing its own bake (its base colour map beside it, read by the mesh's texture coordinates),
a take's finished model laid before its raw one; a ground disc laid as the ground; a character dressed in its made body (its far one hidden) and held still in its clip, its own
SkelRoot kept; a ground marked as the ground; the dome shell's glass skin, curved ribs and deck as three parts at its radius;
a batch of steps run in one call, a refused one named while the rest go on; a lamp where it is laid; an entry with no
USD refused by name, a removed object gone; and the compare measures the render's silhouette against the concept's object masks (overlap, each object's cover) and the
colour difference of the two pictures, and draws them side by side.

Breaks that turn this red (each applied once and seen red, then reverted):
- place_build.posed: the rotate op left out -> the turned piece's box stays unturned
- place_build.snap: `on_grid` on the height too -> the lifted piece drops to the grid
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
- place_build.batch: a refused step stops the batch -> the step after it is never laid
- measure.coverage: `shape & silhouette` made `shape` -> the uncovered object reads covered
- measure.lab: a and b read unsigned -> the concept's blue reads yellow (b over 0)
"""
import json
import pathlib

import trimesh

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdSkel, Vt

from score.stages import place_build
from score.stages.place_build import measure


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
    entry("surface", "boards", {"surface.json": ("record", json.dumps({"settings": {"roughness": 0.7}}))})
    entry("light", "lamp", {"lamps.json": ("record", "{}")})


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
    place_build.light(folder, "bulb", at=(0, 2.5, 0), watts=100)
    batched = place_build.batch(folder, [
        {"step": "put", "name": "floor", "address": "kit/box_piece", "at": [0, -2, 0], "scale": 4, "ground": True},
        {"step": "put", "name": "missing", "address": "kit/plan_only"},
        {"step": "put", "name": "cabinet", "address": "model/cabinet"},
        {"step": "put", "name": "walker", "address": "character/walker", "at": [2, 0, 2]},
        {"step": "dome", "name": "dome", "radius": 5.0, "meridians": 8, "rings": 2, "rib": 0.1},
        {"step": "ground", "name": "regolith", "radius": 3.0},
        {"step": "put", "name": "cup", "address": "take/cup"}])
    refusals = []
    for step in (lambda: place_build.put(folder, "plan", "kit/plan_only"),
                 lambda: place_build.surface(folder, "wall", "surface/boards")):
        try:
            step()
        except place_build.Refused as why:
            refusals.append(str(why))
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
    assert ["no USD file" in answer.get("refused", "") for answer in batched] == [False, True] + [False] * 5
    door_look = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath("/yard/Objects/cabinet/geo/door")).ComputeBoundMaterial()[0]
    door_map = UsdShade.Shader(stage.GetPrimAtPath(f"{door_look.GetPath()}/base")).GetInput("file").Get()
    assert np.allclose(Image.open(door_map.resolvedPath).getpixel((0, 0)), (200, 0, 0))
    assert UsdGeom.PrimvarsAPI(stage.GetPrimAtPath("/yard/Objects/cabinet/geo")).GetPrimvar("st").HasValue()
    assert batched[6]["usd"].endswith("cup-final.usdc") and shown_ground(stage, shown) == (True, {"ground": None})
    assert stage.GetPrimAtPath("/yard/Objects/floor").GetAttribute("score:ground").Get() is True
    cabinet_parts = sorted(next(item for item in shown["objects"] if item["name"] == "cabinet")["parts"])
    assert cabinet_parts[0] == "door" and cabinet_parts[1].startswith("part_") and len(cabinet_parts) == 2
    assert np.allclose(boxes["cabinet"], [[-0.5, -0.5, -0.5], [0.5, 1.5, 0.5]], atol=1e-3)
    walker = stage.GetPrimAtPath("/yard/Objects/walker")
    shown_groups = {group: UsdGeom.Imageable(stage.GetPrimAtPath(f"/yard/Objects/walker/Turned/Body/{group}"))
                    .ComputeVisibility() for group in ("far", "made")}
    held = UsdSkel.Animation(stage.GetPrimAtPath("/yard/Objects/walker/Held"))
    assert (walker.GetTypeName(), shown_groups) == ("SkelRoot", {"far": "invisible", "made": "inherited"})
    assert list(held.GetTranslationsAttr().Get()) == [Gf.Vec3f(0, 1, 0)] and batched[3]["clip"] == "standing"
    assert sorted(next(item for item in shown["objects"] if item["name"] == "dome")["parts"]) == ["deck", "ribs", "shell"]
    assert np.allclose(boxes["dome"], [[-5.1, 0.0, -5.1], [5.1, 5.1, 5.1]], atol=0.02)
    assert shown["lights"] == [{"name": "bulb", "at": [0.0, 2.5, 0.0], "watts": 100.0}]
    assert "no USD file" in refusals[0] and "give --colour" in refusals[1] and len(refusals) == 2
    assert set(boxes) == {"wall", "crate", "floor", "cabinet", "walker", "dome", "regolith", "cup"} and not stage.GetPrimAtPath("/yard/Objects/gone")
    assert (compared["layout_iou"], compared["objects"][0]["covered"], compared["colour"]["mean"]) == (0.5, 0.5, 0.0)
    assert measure.lab(Image.open(folder / "concept.png").convert("RGB"))[0, 0, 2] < -40
    assert Image.open(compared["picture"]).size == (3 * measure.PANEL, measure.PANEL // 2)
