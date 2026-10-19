"""The holes layer: an overlay over a place's accepted stage, never inside it (the accepted assembly's bytes, and every
key after it, stay as they are).

    stage = layer.opened(folder, place, laid)   # holes.usda: [layers/holes.usda, ./stage/<place>.usda], editing the first
    layer.write_box(stage, box, values)          # a missing object: a guide box at its size
    layer.write_mark(stage, path, gates)         # an `over` on a made prim: score:hole "gate" and the gates it fails
    layer.write_place(stage, place, kinds)       # the root's score:holes:place, the route's steps it lacks
    low, high = layer.bounds(stage, path, purposes)

A missing object is an Xform /<place>/Holes/<row>_<n> (nested under its missing parent's when it stands on one), its
frame its spot's (no scale; no transform when unplaced), holding a UsdGeom.Cube `box` of size 1 scaled to the row's
size (wide, tall, deep) with its foot on the frame, purpose guide so no render or game export draws it. It carries
score:hole "missing", score:hole:row, score:hole:size, score:hole:placed, score:kind, score:anchor and
score:hole:node or score:hole:work; never score:row, which the rows, contents, library and reach checks count as a
made object.
"""
import pathlib

from pxr import Gf, Sdf, Usd, UsdGeom

ROOT = "holes.usda"
LAYER = "layers/holes.usda"
BOX = "box"


def opened(folder, place, laid):
    """The holes root over the laid stage file (or none), its edit target the holes layer, both written new."""
    folder = pathlib.Path(folder)
    (folder / LAYER).parent.mkdir(parents=True, exist_ok=True)
    for name in (ROOT, LAYER):
        (folder / name).unlink(missing_ok=True)
    overlay = Sdf.Layer.CreateNew(str(folder / LAYER))
    root = Sdf.Layer.CreateNew(str(folder / ROOT))
    root.subLayerPaths.append(f"./{LAYER}")
    if laid is not None:
        root.subLayerPaths.append(f"./{pathlib.Path(laid).relative_to(folder).as_posix()}")
    root.defaultPrim = place
    stage = Usd.Stage.Open(root)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.SetEditTarget(Usd.EditTarget(overlay))
    if not stage.GetPrimAtPath(f"/{place}"):
        UsdGeom.Xform.Define(stage, f"/{place}")
    holes = UsdGeom.Scope.Define(stage, f"/{place}/Holes")
    UsdGeom.Imageable(holes).CreatePurposeAttr(UsdGeom.Tokens.guide)
    return stage


def strings(prim, values):
    for name, value in values.items():
        prim.CreateAttribute(name, Sdf.ValueTypeNames.String).Set(value)


def matrix_of(frame):
    """A frame {origin, axes} as USD's row-major 4x4: the axes as rows, the origin last."""
    (x, y, z), origin = frame["axes"], frame["origin"]
    return [[*map(float, x), 0.0], [*map(float, y), 0.0], [*map(float, z), 0.0], [*map(float, origin), 1.0]]


def write_box(stage, box, values):
    """One missing object at its frame, its box at the row's size; `values` its string attributes."""
    xform = UsdGeom.Xform.Define(stage, box["path"])
    if box["frame"] is not None:
        xform.AddTransformOp().Set(Gf.Matrix4d(matrix_of(box["frame"])))
    wide, deep, tall = (float(value) for value in box["row"]["size"])
    cube = UsdGeom.Cube.Define(stage, f"{box['path']}/{BOX}")
    cube.CreateSizeAttr(1.0)
    cube.CreatePurposeAttr(UsdGeom.Tokens.guide)
    cube.AddTranslateOp().Set(Gf.Vec3d(0.0, tall / 2, 0.0))
    cube.AddScaleOp().Set(Gf.Vec3f(wide, tall, deep))
    prim = xform.GetPrim()
    strings(prim, values)
    prim.CreateAttribute("score:hole:size", Sdf.ValueTypeNames.Float3).Set(Gf.Vec3f(wide, deep, tall))


def write_mark(stage, path, gates):
    """An `over` on a made prim: the gates it fails, merged with any already marked on it."""
    prim = stage.OverridePrim(path)
    attribute = prim.GetAttribute("score:hole:gates")
    before = list(attribute.Get() or []) if attribute else []
    strings(prim, {"score:hole": "gate"})
    prim.CreateAttribute("score:hole:gates", Sdf.ValueTypeNames.StringArray).Set(sorted(set(before) | set(gates)))


def write_place(stage, place, kinds):
    """The root's score:holes:place: the route's steps the place lacks."""
    stage.OverridePrim(f"/{place}").CreateAttribute("score:holes:place", Sdf.ValueTypeNames.StringArray).Set(
        list(kinds))


def bounds(stage, path, purposes):
    """(low, high) of a prim's world box under the purposes, or (None, None) when it is empty."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), purposes)
    box = cache.ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
    if box.IsEmpty():
        return None, None
    return [round(value, 4) for value in box.GetMin()], [round(value, 4) for value in box.GetMax()]


def saved(stage):
    """Write the holes layer and the root."""
    stage.GetEditTarget().GetLayer().Save()
    stage.GetRootLayer().Save()
