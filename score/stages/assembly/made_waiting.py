"""A scene record entry that waits on its model (`waiting`: no released model yet) laid with its inventory row's model
the place's own surface line baked (the prop route's take, painted and baked), once that bake has it (captain,
2026-10-13: the camp grounds' cairn). Kept out of record.py: the light and settle stages hash record.py, and an edit
there re-keys their paid rows.

    lay   each waiting entry naming a `row` the bake made: an Xform at /<place>/Fixtures/<name> referencing the
          assembly's asset of that model (take_bake writes it), turned by the entry's rotation, its middle over the
          entry's spot and its lowest point on it; the entry leaves the root's score:waiting. A design's object
          (the scene record's: its `bake` the model, its `row` its inventory row) is laid so at
          /<place>/Objects/<name>, where the settle, physics and motion find a laid object; then each object
          with an `on` (what holds it: in its opening, against a wall, on, within or against a holder) is laid by it
          at its built size (fitting.py), and LAID written: every design object's box as laid and what was fitted
          An entry whose row ground-join joined into the ground (`joined`, its join.json pieces: a terrain row, the
          terrain's) is laid there alone, under /<place>/Outside/Detail: it leaves score:waiting and is laid nowhere
          else (2026-10-30: camp's rocks stood twice, as an object and as ground)
"""
import json

from score.stages.assembly import fitting
from score.stages.assembly.record import BASE_LAYER, RECORD, WAITING

# {objects: [{name, row, low, high}], holders: [{name, low, high}] (holders laid as structure: a tube's ribs), walls:
# [{name, low, high}] (the built structure an opening's door is sunk into), fitted: fitting.fitted's}: what the plan
# page shows laid and the `held` gate measures
LAID = "laid.json"


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


def laid_by_relations(stage, out, place, record, objects, baked=None):
    """The laid design objects (`objects`, their names) fitted by their relations (fitting.fitted, a door in the recess
    its holder's bake cut: `baked`, baked.json), and LAID written: each one's box as laid after, the built walls, and
    the fits."""
    fits = fitting.fitted(stage, place, record.get("objects") or [], set(objects),
                          {model: entry.get("cuts") for model, entry in (baked or {}).items()})
    rows = {entry["name"]: entry["row"] for entry in record.get("objects") or []}
    boxes = [(name, fitting.world_box(stage, f"/{place}/Objects/{name}")) for name in objects]
    held = sorted({(on.get("holder scope"), name) for entry in record.get("objects") or [] if (on := entry.get("on"))
                   and on.get("holder scope") for name in on.get("holder") or []
                   if stage.GetPrimAtPath(f"/{place}/{on['holder scope']}/{name}")})

    def listed(name, low, high, **more):
        return {"name": name, **more, "low": [round(float(value), 4) for value in low],
                "high": [round(float(value), 4) for value in high]}
    (out / LAID).write_text(json.dumps({
        "objects": [listed(name, *box, row=rows[name]) for name, box in boxes],
        "holders": [listed(name, *fitting.world_box(stage, f"/{place}/{scope}/{name}")) for scope, name in held],
        "walls": [listed(name, *box) for name, box in fitting.walls(stage, place)],
        "fitted": fits}, indent=1))


def lay(out, place, bake, joined=frozenset()):
    """Every waiting entry of the record whose row the bake made, laid in the base layer and taken off the root's
    score:waiting (one whose row is in `joined` only taken off: the ground lays it), its design objects then laid by
    their relations (laid_by_relations); the rows laid."""
    from pxr import Sdf, Usd, UsdGeom
    baked = json.loads((bake / "baked.json").read_text())
    record = json.loads((out / RECORD).read_text())
    layer = Sdf.Layer.FindOrOpen(str(out / BASE_LAYER))
    stage = Usd.Stage.Open(layer)
    root = stage.GetPrimAtPath(f"/{place}")
    waiting = list(root.GetAttribute(WAITING).Get() or []) if root.HasAttribute(WAITING) else []
    laid, objects = [], []
    for part, entries in record.items():
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            if entry.get("waiting") and entry.get("row") in joined:
                waiting.remove(f"{part} {entry.get('name', '?')}: {entry['waiting']}")
                continue
            model = entry["bake"] if "bake" in entry else entry.get("row")
            if not (entry.get("waiting") and model in baked):
                continue
            scope = f"/{place}/Objects" if "bake" in entry else f"/{place}/Fixtures"
            if not stage.GetPrimAtPath(scope):
                UsdGeom.Scope.Define(stage, scope)
            xform = UsdGeom.Xform.Define(stage, f"{scope}/{entry['name']}")
            xform.GetPrim().GetReferences().AddReference(f"../assets/{model}.usdc")
            xform.AddTransformOp().Set(placement(entry, *asset_bounds(out / "assets" / f"{model}.usdc")))
            for name, value in (("score:kind", entry.get("kind", "fixture")), ("score:model", model),
                                ("score:row", entry["row"]), ("score:from", f"{entry.get('from', '')}; laid by the "
                                                                            f"assembly with the surface line's baked "
                                                                            f"{model}")):
                xform.GetPrim().CreateAttribute(name, Sdf.ValueTypeNames.String).Set(value)
            waiting.remove(f"{part} {entry.get('name', '?')}: {entry['waiting']}")
            laid.append(model)
            if "bake" in entry:
                objects.append(entry["name"])
    laid_by_relations(stage, out, place, record, objects, baked)
    if waiting:
        root.GetAttribute(WAITING).Set(waiting)
    elif root.HasAttribute(WAITING):
        root.RemoveProperty(WAITING)
    layer.Save()
    return list(dict.fromkeys(laid))
