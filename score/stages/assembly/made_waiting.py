"""A scene record entry that waits on its model (`waiting`: no released model yet) laid with its inventory row's model
the place's own surface line baked (the prop route's take, painted and baked), once that bake has it (captain,
2026-10-13: the camp grounds' cairn). Kept out of record.py: the light and settle stages hash record.py, and an edit
there re-keys their paid rows.

    lay   each waiting entry naming a `row` the bake made: an Xform at /<place>/Fixtures/<name> referencing the
          assembly's asset of that model (take_bake writes it), turned by the entry's rotation, its middle over the
          entry's spot and its lowest point on it; the entry leaves the root's score:waiting
"""
import json

from score.stages.assembly.record import BASE_LAYER, RECORD, WAITING


def asset_bounds(path):
    """(low, high) corners of an asset's drawn meshes in its own frame."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(path))
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]) \
        .ComputeWorldBound(stage.GetPseudoRoot()).ComputeAlignedRange()
    return box.GetMin(), box.GetMax()


def placement(entry, low, high):
    """The matrix that turns a model by the entry's rotation ([x, y, z, w]) and stands its turned box's middle over
    the entry's `at`, its lowest point on it."""
    from pxr import Gf
    x, y, z, w = (float(value) for value in entry["rotation"])
    turn = Gf.Matrix4d().SetRotate(Gf.Quatd(w, Gf.Vec3d(x, y, z)))
    corners = [turn.Transform(Gf.Vec3d(cx, cy, cz)) for cx in (low[0], high[0]) for cy in (low[1], high[1])
               for cz in (low[2], high[2])]
    least = [min(corner[axis] for corner in corners) for axis in range(3)]
    most = [max(corner[axis] for corner in corners) for axis in range(3)]
    at = [float(value) for value in entry["at"]]
    move = Gf.Vec3d(at[0] - (least[0] + most[0]) / 2, at[1] - least[1], at[2] - (least[2] + most[2]) / 2)
    return turn * Gf.Matrix4d().SetTranslate(move)


def lay(out, place, bake):
    """Every waiting entry of the record whose row the bake made, laid in the base layer and taken off the root's
    score:waiting; the rows laid."""
    from pxr import Sdf, Usd, UsdGeom
    baked = json.loads((bake / "baked.json").read_text())
    record = json.loads((out / RECORD).read_text())
    layer = Sdf.Layer.FindOrOpen(str(out / BASE_LAYER))
    stage = Usd.Stage.Open(layer)
    root = stage.GetPrimAtPath(f"/{place}")
    waiting = list(root.GetAttribute(WAITING).Get() or []) if root.HasAttribute(WAITING) else []
    laid = []
    for part, entries in record.items():
        for entry in entries if isinstance(entries, list) else []:
            if not (isinstance(entry, dict) and entry.get("waiting") and entry.get("row") in baked):
                continue
            row = entry["row"]
            if not stage.GetPrimAtPath(f"/{place}/Fixtures"):
                UsdGeom.Scope.Define(stage, f"/{place}/Fixtures")
            xform = UsdGeom.Xform.Define(stage, f"/{place}/Fixtures/{entry['name']}")
            xform.GetPrim().GetReferences().AddReference(f"../assets/{row}.usdc")
            xform.AddTransformOp().Set(placement(entry, *asset_bounds(out / "assets" / f"{row}.usdc")))
            for name, value in (("score:kind", entry.get("kind", "fixture")), ("score:model", row),
                                ("score:row", row), ("score:from", f"{entry.get('from', '')}; laid by the assembly "
                                                                   f"with the surface line's baked {row}")):
                xform.GetPrim().CreateAttribute(name, Sdf.ValueTypeNames.String).Set(value)
            waiting.remove(f"{part} {entry.get('name', '?')}: {entry['waiting']}")
            laid.append(row)
    if laid and waiting:
        root.GetAttribute(WAITING).Set(waiting)
    elif laid:
        root.RemoveProperty(WAITING)
    layer.Save()
    return laid
