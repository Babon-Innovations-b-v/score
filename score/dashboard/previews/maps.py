"""Top-down maps of where things stand, each from one output's own files: the plan with its labelled items, doors and
standing points; the positions any JSON output names (lights, views, joined places, lamps, objects by their matrix);
the settle (where each object came to rest, moved ones marked); and a USD layer's prims at their own transforms."""
import os
import pathlib
import tempfile

from score.dashboard.previews import canvas

POSITION_KEYS = ("at", "spot", "position", "translate", "centre", "center", "middle", "eye")
MOVED = "#b4583a"
KEPT = "#4c6a8a"
MANY = 200  # more placed things than this are drawn as fine dots


def plan_picture(plan, destination):
    """The plan drawn from above: floor, each item's box labelled, doors and where people stand."""
    figure, (axes,) = canvas.blank()
    canvas.floor(axes, plan)
    for number, item in enumerate(plan.get("items") or []):
        if item.get("box") and len(item["box"]) == 4:
            canvas.box(axes, item["box"], canvas.COLOURS[number % len(canvas.COLOURS)], 0.45,
                       canvas.short(item.get("name", "")))
    for door in plan.get("doors") or []:
        middle = door.get("middle") or []
        if len(middle) == 3:
            axes.plot(middle[0], middle[2], marker="s", markersize=6, color=canvas.INK)
            axes.text(middle[0], middle[2], f" door {door.get('name', '')}", fontsize=6, color=canvas.INK)
    for spot in plan.get("standing") or []:
        point = standing_point(spot)
        if point:
            axes.plot(point[0], point[1], marker="o", markersize=4, color=MOVED)
    canvas.title(axes, plan.get("title") or plan.get("place") or "plan")
    return canvas.save(figure, [axes], destination)


def standing_point(spot):
    """(x, z) of a standing point, written as {"at": [x, z]} or as the bare [x, z] or [x, y, z]; None otherwise."""
    return ground_point(spot.get("at")) if isinstance(spot, dict) else ground_point(spot)


def ground_point(value):
    """(x, z) of a 3-vector [x, y, z] or a 2-vector [x, z]; None for anything else."""
    if isinstance(value, list) and len(value) in (2, 3) and all(isinstance(number, (int, float)) for number in value):
        return (value[0], value[2]) if len(value) == 3 else (value[0], value[1])
    return None


def matrix_point(value):
    """(x, z) of a 4x4 row-major matrix whose last column is the translation; None otherwise."""
    if isinstance(value, list) and len(value) == 4 and all(isinstance(row, list) and len(row) == 4 for row in value):
        return value[0][3], value[2][3]
    return None


def name_of(found, key):
    for field in ("name", "path", "id"):
        if isinstance(found.get(field), str):
            return found[field].rsplit("/", 1)[-1]
    return key


def positions(value, key="", found=None):
    """[(name, x, z)] of everything a JSON document places: a dict with a position under a known key or a 4x4
    `matrix`, named by its own name or path or the key it sits under."""
    found = [] if found is None else found
    if isinstance(value, dict):
        point = next((ground_point(value[field]) for field in POSITION_KEYS if field in value
                      and ground_point(value[field])), None) or matrix_point(value.get("matrix"))
        if point:
            found.append((name_of(value, key), *point))
        for child_key, child in value.items():
            if isinstance(child, (dict, list)) and child_key not in POSITION_KEYS:
                positions(child, child_key if isinstance(child, dict) else key, found)
    elif isinstance(value, list):
        for child in value:
            positions(child, key, found)
    return found


def inside(placed, plan, margin=0.25):
    """The placed things on or near the place's floor (a joined place far outside it would shrink the map)."""
    found = (plan or {}).get("floor")
    if not found or len(found) != 2:
        return placed
    (x0, z0), (x1, z1) = found
    wide, deep = abs(x1 - x0) * margin, abs(z1 - z0) * margin
    return [(name, x, z) for name, x, z in placed
            if min(x0, x1) - wide <= x <= max(x0, x1) + wide and min(z0, z1) - deep <= z <= max(z0, z1) + deep]


def dots(axes, placed, colour, labelled):
    """Each placed thing as a dot (a fine one when there are many), named when there are few enough to read."""
    many = len(placed) > MANY
    if placed:
        axes.plot([x for _, x, _ in placed], [z for _, _, z in placed], linestyle="none", marker="o",
                  markersize=1.0 if many else 4, color=colour, markeredgecolor=colour if many else canvas.INK,
                  markeredgewidth=0.3, alpha=0.6 if many else 1.0)
    for name, x, z in placed if labelled else ():
        axes.text(x, z, f" {canvas.short(name, 18)}", fontsize=5.5, color=canvas.INK)


def positions_picture(placed, routes, plan, words, destination):
    """The placed things over the place, and each moving thing's route."""
    figure, (axes,) = canvas.blank()
    canvas.underlay(axes, plan)
    dots(axes, placed, MOVED, len(placed) <= 30)
    for number, (name, route) in enumerate(routes):
        drawn_route(axes, name, route, canvas.COLOURS[number % len(canvas.COLOURS)])
    moving = f", {len(routes)} moving" if routes else ""
    canvas.title(axes, f"{words}: {len(placed)} placed{moving}")
    return canvas.save(figure, [axes], destination)


def settle_picture(settle, plan, destination):
    """Where each object came to rest: moved to rest (marked) beside kept as laid, over the place."""
    objects = settle.get("objects") or {}
    moved = [(name, *matrix_point(item["matrix"])) for name, item in objects.items()
             if item.get("rested") and matrix_point(item.get("matrix"))]
    kept = [(name, *matrix_point(item["matrix"])) for name, item in objects.items()
            if not item.get("rested") and matrix_point(item.get("matrix"))]
    figure, (axes,) = canvas.blank()
    canvas.underlay(axes, plan)
    dots(axes, kept, KEPT, False)
    dots(axes, moved, MOVED, len(moved) <= 30)
    canvas.title(axes, f"settle: {len(moved)} moved to rest (orange), {len(kept)} kept as laid (blue)")
    return canvas.save(figure, [axes], destination)


def opened_layer(name, path, folder):
    """A USD layer opened on its own (every prim, defined or over), linked under its own suffix since a stored blob
    has none; None when it will not open."""
    from pxr import Tf, Usd
    linked = pathlib.Path(folder) / f"layer{pathlib.PurePosixPath(name).suffix or '.usda'}"
    os.symlink(path, linked)
    try:
        return Usd.Stage.Open(str(linked), Usd.Stage.LoadNone)
    except Tf.ErrorException:
        return None


def own_translate(prim, time):
    """A prim's own `xformOp:translate` at a time, plus its parents' (an over in a layer opened on its own has no
    op order to compose); (0, 0, 0) where none is authored."""
    total = [0.0, 0.0, 0.0]
    while prim and not prim.IsPseudoRoot():
        attribute = prim.GetAttribute("xformOp:translate")
        value = attribute.Get(time) if attribute and attribute.HasAuthoredValue() else None
        if value is not None:
            total = [total[axis] + value[axis] for axis in range(3)]
        prim = prim.GetParent()
    return total


def placed_at(prim, cache):
    """(x, z) of a prim the layer places: its composed transform, else its authored translates; None when the layer
    places it nowhere."""
    from pxr import Usd, UsdGeom
    if UsdGeom.Xformable(prim).GetOrderedXformOps():
        moved = cache.GetLocalToWorldTransform(prim).ExtractTranslation()
        return moved[0], moved[2]
    attribute = prim.GetAttribute("xformOp:translate")
    if not (attribute and attribute.HasAuthoredValue()):
        return None
    moved = own_translate(prim, Usd.TimeCode.EarliestTime())
    return moved[0], moved[2]


def layer_positions(name, path):
    """[(name, x, z)] of every prim a USD layer places; none when the layer will not open, so the output is
    pictured another way."""
    from pxr import Usd, UsdGeom
    with tempfile.TemporaryDirectory() as folder:
        stage = opened_layer(name, path, folder)
        if stage is None:
            return []
        cache = UsdGeom.XformCache(Usd.TimeCode.EarliestTime())
        found = []
        for prim in Usd.PrimRange.AllPrims(stage.GetPseudoRoot()):
            point = None if prim.IsPseudoRoot() else placed_at(prim, cache)
            if point:
                found.append((prim.GetName(), *point))
    return found


def layer_paths(name, path):
    """[(name, [(x, z), ...])] of every prim whose translate the layer animates (more than one place over time),
    at each of its time samples; none when the layer will not open."""
    from pxr import Usd
    with tempfile.TemporaryDirectory() as folder:
        stage = opened_layer(name, path, folder)
        if stage is None:
            return []
        found = []
        for prim in Usd.PrimRange.AllPrims(stage.GetPseudoRoot()):
            attribute = None if prim.IsPseudoRoot() else prim.GetAttribute("xformOp:translate")
            times = attribute.GetTimeSamples() if attribute else []
            route = [tuple(own_translate(prim, time)[axis] for axis in (0, 2)) for time in times]
            if len(set(route)) > 1:
                found.append((prim.GetName(), route))
    return found


def drawn_route(axes, name, route, colour):
    """A mover's route: a line through its places, a dot where it starts, an arrow to the farthest it goes."""
    across, down = [x for x, _ in route], [z for _, z in route]
    axes.plot(across, down, color=colour, linewidth=1.2)
    axes.plot(across[0], down[0], marker="o", markersize=4, color=colour)
    far = max(route, key=lambda point: (point[0] - route[0][0]) ** 2 + (point[1] - route[0][1]) ** 2)
    axes.annotate("", xy=far, xytext=route[0], arrowprops={"arrowstyle": "->", "color": colour, "lw": 1.2})
    axes.text(across[0], down[0], f" {canvas.short(name, 18)}", fontsize=6, color=canvas.INK)
