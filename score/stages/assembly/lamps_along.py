"""A thing's own lamps moved with it when room_clear moves the thing out of a wall it was laid in (room_clear.cleared,
moved_across; a thing it narrows stays where it hangs, so its lamps stay too). The record lays a lamp at its plan
item's spot, inside the thing's model, and the light layer frees it from that fixture (light/layer.py,
lamps_through_fixtures). Moved alone, walkway's floor lights left their seven lamps 2.7 cm inside wall_4 and wall_2,
no fixture round them to free them from, their light stopped by the wall: spot-2, whose picture is the floor round
floor light 2_2, read 0.079 against its concept's 0.237 (light@walkway, 2026-11-12).

    moved_with(stage, place, low, high, foot, scale, target)   the place's lamps within a thing's box (low, high), as
                                                               fitting.moved_by moved the thing; their paths
    laid_at(stage, path, spot)                                 where the record laid a lamp before it was carried
    onto_models(stage, place, record, objects)                 each record lamp off its row's laid model put on it
                                                               (made_waiting.lay, after the fitting); their paths

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


def drawn_box(stage, path):
    """(low, high) world bound of a prim's drawn meshes, None when it draws nothing."""
    from pxr import Usd, UsdGeom
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]) \
        .ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
    return None if box.IsEmpty() else (np.array(box.GetMin()), np.array(box.GetMax()))


def glowing_part(stage, path):
    """The world bound of a model's glowing parts (its meshes with glow in their path under it, as the light layer
    names a lens: layer.lamps_through_fixtures), None for a model with none."""
    from pxr import Usd, UsdGeom
    boxes = [drawn_box(stage, str(prim.GetPath())) for prim in Usd.PrimRange(stage.GetPrimAtPath(path))
             if prim.IsA(UsdGeom.Mesh) and "glow" in str(prim.GetPath())[len(path):].lower()]
    boxes = [box for box in boxes if box]
    return (np.min([low for low, _ in boxes], axis=0), np.max([high for _, high in boxes], axis=0)) if boxes else None


def on_model(entry, thing, low, high, glow=None):
    """Where a record lamp (`entry`) stands on its laid model (`thing`, the record's object it is nearest, laid in the
    box low, high): the middle of the model's glowing part (`glow`) where it has one, else carried as far as the model
    was in plan (its spot's offset from the object's record spot, from the laid box's middle) and held inside the box,
    at its own height where that is inside the box, else the box's middle height (a lamp laid at a shape with no
    height stood on the floor: quarters' wall lights and string lights at 0 m under models laid 2.2 m up)."""
    if glow is not None:
        return (glow[0] + glow[1]) / 2
    at, laid = np.asarray(entry["at"], float), np.asarray(thing["at"], float)
    middle = (low + high) / 2
    spot = np.clip(middle + at - laid, low, high)
    spot[1] = at[1] if low[1] - WITHIN <= at[1] <= high[1] + WITHIN else middle[1]
    return spot


def onto_models(stage, place, record, objects):
    """Each record lamp of a row the record lays as design objects (`objects`, their names, as laid and fitted) put
    on its own model, the object of its row nearest its record spot in plan (on_model; one already within its model's
    box stays), its record spot kept
    (LAID_AT) so the light layer still matches it (layer.placed_lamps). The record lays a lamp at its plan item, the
    assembly then fits the model by its relations, so lamps sat off their models (2026-11-15, #128: quarters' on the
    floor, shiplock's in its roof, storage's door glow at the plan spot). {lamp path: metres moved}."""
    import scene
    from pxr import Gf, Sdf, Usd, UsdGeom
    things = {}
    for entry in record.get("objects") or []:
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{entry.get('name')}")
        if entry.get("name") in objects and entry.get("row") and prim and prim.IsActive():
            things.setdefault(entry["row"], []).append(entry)
    entries = record.get("lights") or []
    moved = {}
    for name, entry in zip(scene.light_names(entries), entries):
        prim = stage.GetPrimAtPath(f"/{place}/Lights/{name}")
        own = things.get(entry.get("row")) if entry["type"] != "sun" else None
        ops = UsdGeom.Xformable(prim).GetOrderedXformOps() if prim and own else []
        if not ops or ops[0].GetOpType() != UsdGeom.XformOp.TypeTranslate:
            continue
        at = np.asarray(entry["at"], float)
        thing = min(own, key=lambda one: float(np.hypot(*(np.asarray(one["at"], float) - at)[[0, 2]])))
        path = f"/{place}/Objects/{thing['name']}"
        box = drawn_box(stage, path)
        if box is None:
            continue
        parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default()) \
            if prim.GetParent().IsA(UsdGeom.Xformable) else Gf.Matrix4d(1.0)
        spot = np.array(parent.Transform(Gf.Vec3d(ops[0].Get())))
        if np.all(spot >= box[0] - WITHIN) and np.all(spot <= box[1] + WITHIN):
            continue  # on its model already: the light layer frees it from its fixture
        put = on_model(entry, thing, *box, glowing_part(stage, path))
        if not prim.HasAttribute(LAID_AT):
            prim.CreateAttribute(LAID_AT, Sdf.ValueTypeNames.Double3).Set(Gf.Vec3d(*map(float, spot)))
        ops[0].Set(parent.GetInverse().Transform(Gf.Vec3d(*map(float, put))))
        moved[str(prim.GetPath())] = round(float(np.linalg.norm(put - spot)), 4)
    return moved
