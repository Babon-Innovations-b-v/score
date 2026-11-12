"""A thing's own lamps moved with it when room_clear moves the thing out of a wall it was laid in (room_clear.cleared,
moved_across; a thing it narrows stays where it hangs, so its lamps stay too). The record lays a lamp at its plan
item's spot, inside the thing's model, and the light layer frees it from that fixture (light/layer.py,
lamps_through_fixtures). Moved alone, walkway's floor lights left their seven lamps 2.7 cm inside wall_4 and wall_2,
no fixture round them to free them from, their light stopped by the wall: spot-2, whose picture is the floor round
floor light 2_2, read 0.079 against its concept's 0.237 (light@walkway, 2026-11-12).

    moved_with(stage, place, low, high, foot, scale, target)   the place's lamps within a thing's box (low, high), as
                                                               fitting.moved_by moved the thing; their paths
    laid_at(stage, path, spot)                                 where the record laid a lamp before it was carried

The light layer matches each record lamp to the stage's lamp by where the record laid it (layer.placed_lamps), so a
carried lamp keeps its carried spot (LAID_AT) instead of being put back in the wall.
"""
import numpy as np

# A lamp stands within a thing's box when inside it to this much (metres): a lamp on its model's face is its.
WITHIN = 1e-3
# A carried lamp's spot as the record laid it, before it was carried (world metres).
LAID_AT = "score:laid_at"


def moved_with(stage, place, low, high, foot, scale, target):
    """Each lamp under the place's Lights standing within the box (low, high) a thing had before it was moved (its
    foot middle `foot` to `target`, shrunk by `scale` about it: fitting.moved_by) moved to where that puts it; their
    paths."""
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux
    lights = stage.GetPrimAtPath(f"/{place}/Lights")
    moved = []
    for prim in Usd.PrimRange(lights) if lights else []:
        ops = UsdGeom.Xformable(prim).GetOrderedXformOps() if prim.HasAPI(UsdLux.LightAPI) else []
        if not ops or ops[0].GetOpType() != UsdGeom.XformOp.TypeTranslate:
            continue  # its spot is its first op's translate (scene.write_light), so that op alone moves it
        parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default()) \
            if prim.GetParent().IsA(UsdGeom.Xformable) else Gf.Matrix4d(1.0)
        spot = np.array(parent.Transform(Gf.Vec3d(ops[0].Get())))
        if np.any(spot < np.asarray(low) - WITHIN) or np.any(spot > np.asarray(high) + WITHIN):
            continue
        if not prim.HasAttribute(LAID_AT):
            prim.CreateAttribute(LAID_AT, Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*map(float, spot)))
        put = np.asarray(target, float) + (spot - np.asarray(foot, float)) * np.asarray(scale, float)
        ops[0].Set(parent.GetInverse().Transform(Gf.Vec3d(*map(float, put))))
        moved.append(str(prim.GetPath()))
    return moved


def laid_at(stage, path, spot):
    """Where the record laid the lamp at `path` (world), before a thing it stood in carried it (moved_with); its
    `spot` where nothing carried it."""
    attribute = stage.GetPrimAtPath(path).GetAttribute(LAID_AT)
    return np.asarray(attribute.Get(), dtype=float) if attribute and attribute.HasValue() else spot
