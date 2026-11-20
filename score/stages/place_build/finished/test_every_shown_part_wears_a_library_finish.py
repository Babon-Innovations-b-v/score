"""Invariant: every part a place_build scene shows wears a library finish, and what does not is told by object: a
generator painted part by part from the library (its own paint red and grey) under one grey look over its whole is
`one surface over its parts`, and a new whole surface on it is refused; a picture-made take in its own paint is
`own paint`; a piece with no material is `no material`; a look naming a surface the library does not hold is
`unknown surface`; a character's own paint passes only under a written exception (the player models'); an entry the
library withdrew is never its paint and is refused at `put`; while a one-paint box under one look passes. `refinish` mends each: the generator shows its own
library paint whole again; a lantern of the same paint under a whole glowing look keeps the glow on its red part
alone, its grey part in its own library paint; the take's parts laid as the palette variants nearest their colours
(its brown part a paint, never the sand ground of the same colour); and a take `put` after the palette is laid
re-finished at once. Afterwards the scene's finishes are told no fault.

Breaks that turn this red (each applied once and seen red, then reverted):
- finished.object_faults: the whole-look rule left out (`len(parts) >= PARTS` made `False`) -> the grey generator
  passes
- grade.parts: PART_DELTA made 1000 -> the generator's red and grey are one paint, its grey look passes
- finished.library_painted: always True -> the take's own paint passes
- place_build.surface: whole_over_parts unread -> the second whole grey look is laid, not refused
- place_build.put: own_paint_finished unread -> the take laid after the palette keeps its own paint
- finished.parts_laid: the own material left unbound -> the lantern's grey part has no material
- finished.earlier_look: the glow kept whatever the recipe (`recipe not in GLOWS` made `False`) -> the generator
  keeps its grey look on one part
- finished.variant_colours: every family kept -> the take's brown part wears the sand ground
- finished.library_painted: the withdrawn rule left out -> a withdrawn entry's paint passes
- place_build.fetch: the withdrawn refusal left out -> a withdrawn model is laid
- finished.library_painted: a character always passed (`bool(excepted(...))` made `True`) -> a character no written
  exception covers keeps its own paint
"""
import json

import pytest
from PIL import Image
from pxr import Sdf, Usd, UsdGeom, UsdShade, Vt

from score.stages import place_build
from score.stages.place_build import finished

BROWN, DARK, RED, GREY = (138, 106, 72), (40, 40, 44), (200, 30, 30), (170, 168, 164)


def model_text(name, texture):
    """A model of two triangles side by side, the first over its picture's left half, the second its right half."""
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    top = UsdGeom.Xform.Define(stage, f"/{name}")
    stage.SetDefaultPrim(top.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, f"/{name}/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray([(0, 0, 0), (1, 0, 0), (1, 1, 0), (2, 0, 0), (3, 0, 0), (3, 1, 0)]))
    mesh.CreateFaceVertexCountsAttr([3, 3])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3, 4, 5])
    st = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
    st.Set(Vt.Vec2fArray([(0.2, 0.5), (0.3, 0.5), (0.25, 0.6), (0.7, 0.5), (0.8, 0.5), (0.75, 0.6)]))
    own = UsdShade.Material.Define(stage, f"/{name}/paint")
    surface = UsdShade.Shader.Define(stage, f"/{name}/paint/surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    picture = UsdShade.Shader.Define(stage, f"/{name}/paint/base")
    picture.CreateIdAttr("UsdUVTexture")
    picture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"./{texture}")
    surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        picture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
    own.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")
    UsdGeom.Subset.CreateGeomSubset(mesh, "body", UsdGeom.Tokens.face, [0, 1], "materialBind")
    UsdShade.MaterialBindingAPI.Apply(stage.GetPrimAtPath(f"/{name}/geo/body")).Bind(own)
    return stage.GetRootLayer().ExportToString()


def library(root, files):
    def entry(kind, entry_id, named, made_with=()):
        folder = root / "entries" / kind / entry_id / "1"
        folder.mkdir(parents=True)
        folder.joinpath("entry.json").write_text(json.dumps({
            "schema": "score-lib-entry/1", "address": f"{kind}/{entry_id}@1", "kind": kind, "id": entry_id,
            "version": 1, "files": {name: {"role": role} for name, (role, _) in named.items()},
            "provenance": {"made_with": [{"by": by, "what": what} for by, what in made_with]}}))
        for name, (_, content) in named.items():
            target = files / f"{kind}/{entry_id}@1/{name}"
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, Image.Image):
                content.save(target)
            else:
                target.write_text(content)

    def halves(left, right):
        picture = Image.new("RGB", (2, 1), left)
        picture.putpixel((1, 0), right)
        return picture
    entry("model", "generator", {"model.usda": ("usd", model_text("generator", "paint.png")),
                                 "paint.png": ("texture", halves(RED, GREY))},
          [("pixal3d", "its shape"), ("score", "split, painted from the library surfaces and baked")])
    entry("model", "box", {"model.usda": ("usd", model_text("box", "paint.png")),
                           "paint.png": ("texture", halves(GREY, GREY))},
          [("score", "split, painted from the library surfaces and baked")])
    entry("take", "stool", {"model.usda": ("usd", model_text("stool", "paint.png")),
                            "paint.png": ("texture", halves(BROWN, DARK))}, [("pixal3d", "its shape and paint")])
    bare = model_text("bare", "none.png").replace('rel material:binding = </bare/paint>', "")
    entry("model", "bare", {"model.usda": ("usd", bare)}, [("score", "painted from the library surfaces")])
    for recipe in ("painted_metal", "glowing"):
        entry("surface", recipe, {"surface.json": ("record", json.dumps({"settings": {"roughness": 0.5}}))})


def kinds(found, name):
    return {fault["kind"] for fault in found.get(name, ())}


def test_every_shown_part_wears_a_library_finish(tmp_path, monkeypatch):
    root, files, folder = tmp_path / "lib", tmp_path / "files", tmp_path / "place"
    library(root, files)
    monkeypatch.setenv("SCORE_LIB_ROOT", str(root))
    monkeypatch.setenv("SCORE_LIB_FILES", str(files))
    Image.new("RGB", (8, 8)).save(tmp_path / "concept.png")
    place_build.start(folder, "camp", tmp_path / "concept.png")
    hexed = "#" + "".join(f"{value:02x}" for value in BROWN)
    (tmp_path / "palette.json").write_text(json.dumps({
        "recipes": {"painted_metal": {"roughness": 0.5}, "glowing": {"roughness": 0.3}},
        "tokens": {"glow": "#d03828", "grey": "#aaa8a4", "brown": "#9a7a58", "ground": hexed, "dark": "#303034", "dust": "#a05030"},
        "dirt": "dust",
        "families": {"paint": {"variants": {"grey_paint": {"recipe": "painted_metal", "token": "grey", "seed": 1},
                                            "wood_paint": {"recipe": "painted_metal", "token": "brown", "seed": 2},
                                            "dark_paint": {"recipe": "painted_metal", "token": "dark", "seed": 3}}},
                     "lamp": {"variants": {"lamp_glow": {"recipe": "glowing", "token": "glow", "seed": 5}}},
                     "sand": {"variants": {"sand_ground": {"recipe": "painted_metal", "token": "ground", "seed": 4}}}}}))
    for name, address, at in (("gen", "model/generator", 0), ("box", "model/box", 4), ("stool", "take/stool", 8),
                              ("bare", "model/bare", 12), ("lantern", "model/generator", 20)):
        place_build.put(folder, name, address, at=(at, 0, 0))
    place_build.palette(folder, tmp_path / "palette.json", wear=0.4, dirt=0.3)
    with monkeypatch.context() as patched:  # the generator as a scene laid before the refusal held it
        patched.setattr(place_build, "whole_over_parts", lambda prim: None)
        place_build.surface(folder, "gen", "palette/grey_paint")
        place_build.surface(folder, "lantern", "palette/lamp_glow")
    place_build.surface(folder, "box", "palette/grey_paint")
    refused = place_build.batch(folder, [{"step": "surface", "name": "gen", "address": "palette/grey_paint"}])
    stage, _ = place_build.opened(folder)
    stage.GetPrimAtPath("/camp/Looks/box").GetAttribute("score:surface").Set("surface/nowhere@1")
    place_build.saved(stage)
    found = finished.faults(Usd.Stage.Open(str(place_build.scene_path(folder))), "camp")
    assert "refused" in refused[0] and "2 parts" in refused[0]["refused"], refused
    assert kinds(found, "gen") == {"one surface over its parts"}, found.get("gen")
    assert kinds(found, "stool") == {"own paint"} and kinds(found, "bare") == {"no material"}, found
    assert kinds(found, "box") == {"unknown surface"}, found.get("box")
    stage, _ = place_build.opened(folder)
    stage.GetPrimAtPath("/camp/Looks/box").GetAttribute("score:surface").Set("surface/painted_metal@1")
    place_build.saved(stage)
    mended = {name: place_build.refinish(folder, name) for name in ("gen", "stool", "lantern")}
    put_after = place_build.put(folder, "stool2", "take/stool", at=(16, 0, 0))
    stage = Usd.Stage.Open(str(place_build.scene_path(folder)))
    found = finished.faults(stage, "camp")
    assert set(found) == {"bare"}, found
    assert mended["gen"]["finish"] == "its model's own library paint" and not finished.part_looks(stage, "camp", \
        stage.GetPrimAtPath("/camp/Objects/gen")), mended
    assert set(mended["lantern"]["parts"].values()) == {"palette/lamp_glow", "its model's own library paint"}, mended
    assert sorted(mended["stool"]["parts"].values()) == ["palette/dark_paint", "palette/wood_paint"], mended
    assert put_after["finish"]["parts"] == mended["stool"]["parts"], put_after
    bound = finished.bound_parts(stage.GetPrimAtPath("/camp/Objects/lantern/geo"))
    looks = {part.GetName(): str(material.GetPath()) if material else None for part, material in bound}
    glow = [name for name, look in looks.items() if look and look.startswith("/camp/Looks/lantern__")]
    assert len(looks) == 2 and set(looks.values()) - {looks[name] for name in glow} \
        == {"/camp/Objects/lantern/paint"}, looks
    subset = UsdGeom.Subset(stage.GetPrimAtPath(f"/camp/Objects/lantern/geo/{glow[0]}"))
    assert list(subset.GetIndicesAttr().Get()) == [0], looks  # the red half alone keeps the glow
    assert {str(material.GetPath()) for _, material in finished.bound_parts(
        stage.GetPrimAtPath("/camp/Objects/gen/geo"))} == {"/camp/Objects/gen/paint"}
    held = Usd.Stage.CreateInMemory()
    pilot = held.DefinePrim("/camp/Objects/pilot")
    pilot.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("character")
    player = {"place": "*", "prim": "/*/Characters/*", "aspect": "finish", "what": "a player model's own texture",
              "why": "repainting loses its seams", "allowed_by": "@owner", "allowed_on": "2026-11-19"}
    assert not finished.library_painted(pilot, None, []) and finished.library_painted(pilot, None, [player])
    assert not finished.library_painted(pilot, {"state": "withdrawn"}, [player])
    retired = root / "entries/model/retired/1"
    retired.mkdir(parents=True)
    retired.joinpath("entry.json").write_text(json.dumps({
        "schema": "score-lib-entry/1", "address": "model/retired@1", "kind": "model", "id": "retired", "version": 1,
        "state": "withdrawn", "files": {}, "provenance": {}}))
    with pytest.raises(place_build.Refused, match="withdrawn"):
        place_build.put(folder, "old", "model/retired")
