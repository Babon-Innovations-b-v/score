"""A thing nothing holds, standing on the floor by itself, that the scene record lays over what is under it by more
than the settle lets a thing down (DRIFT_MOST), let straight down onto the first surface under it: the floor, a built
deck or static, the made ground or another thing. Less is the plan's base estimate, which the settle lets down; more
the settle keeps as laid, floating, its layout's fault (settling.judge_rested's laid_wrong).

settle@hangar, 2026-11-13: its spaceship (a creator's plan, data/definitions/ship_floor.json) is laid at the plan's
base, the keel's lowest over the ground on its landing gear, 1.039 m, but the baked model stands on its own feet from
its foot up: its lowest point stood 0.94 m over the floor. The drop let it down 1.0 m flat (0.35 degrees), past the
settle's 0.3 m, so it was kept as laid and failed rested and resting, both attempts.

    downs(stage, place, record)   {name: metres down} of each such thing: the least gap of its points straight down
                                  to the first surface under them (face_down.gap_under), less CLEAR, where that gap is
                                  over DRIFT_MOST and finite
    let_down(folder, place)       each such thing of the place at `folder` moved down, with what it holds; the fits
                                  [{name, how "floored", ...}], laid.json written again
"""
import json
import pathlib
import sys

from score.stages.assembly import BASE_LAYER, RECORD, even_feet, face_down, fitting, made_waiting, on_ground, parting

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# How far, metres, the settle lets a thing down or moves it at most (tools/usd/settle.py's DRIFT_MOST, named here so
# settle.py stays out of the assembly's code version): a thing laid further over what is under it is this module's.
DRIFT_MOST = 0.3
# How far, metres, a thing is left over what is under it: the snap's own clearance (snap.CLEARANCE).
CLEAR = 0.002


def downs(stage, place, record):
    """{name: metres} each thing nothing holds (parting.loose) standing on the floor by itself (even_feet.floor_thing)
    is let down by: the least gap of its points to the first surface under them (the made ground, the built statics
    the resting check reads, triage.static_meshes, or any other thing but those it holds, which move with it), less
    CLEAR, where that gap is over DRIFT_MOST and finite."""
    import resting
    import triage
    import trimesh
    ground = resting.ground_height(stage, place)
    things = stage.GetPrimAtPath(f"/{place}/Objects")
    meshes = {**triage.static_meshes(stage, place),
              **{prim.GetName(): mesh for prim in (things.GetChildren() if things else []) if prim.IsActive()
                 and (mesh := fitting.surface_mesh(stage, str(prim.GetPath()))) is not None}}
    holding, found = fitting.holders_of(record), {}
    for entry in record.get("objects") or []:
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{entry['name']}")
        if not (prim and prim.IsActive() and parting.loose(entry) and even_feet.floor_thing(prim)) or \
                entry.get("under roof"):  # hung from the roof (fitting.hung_by_parts), never on the floor
            continue
        points = on_ground.world_points(prim)
        if not len(points):
            continue
        held = {entry["name"], *parting.carried(entry["name"], holding)}
        under = [mesh for name, mesh in meshes.items() if name not in held and below(mesh.bounds, points)]
        gap = face_down.gap_under(points, ground, trimesh.util.concatenate(under) if under else None)
        if DRIFT_MOST < gap < float("inf"):
            found[entry["name"]] = gap - CLEAR
    return found


def below(bounds, points):
    """Whether a mesh's box (`bounds`: low, high) reaches under the box of `points` [n, 3] seen from above, its low
    under their top: only such a mesh can lie under them."""
    low, high = points.min(axis=0), points.max(axis=0)
    return bool((bounds[0][[0, 2]] <= high[[0, 2]]).all() and (bounds[1][[0, 2]] >= low[[0, 2]]).all()
                and bounds[0][1] <= high[1])


def let_down(folder, place):
    """Each thing of the place at `folder` laid further over what is under it than the settle lets down (downs) moved
    down onto it, what it holds moved with it; the base layer saved and laid.json's boxes and fits written again. The
    fits, [] and nothing written when none moves."""
    from pxr import Gf, Sdf, Usd
    folder = pathlib.Path(folder)
    laid_path, record_path = folder / made_waiting.LAID, folder / RECORD
    if not laid_path.exists() or not record_path.exists():
        return []
    laid, record = json.loads(laid_path.read_text()), json.loads(record_path.read_text())
    stage = Usd.Stage.Open(str(folder / f"{place}.usda"))
    layer = Sdf.Layer.FindOrOpen(str(folder / BASE_LAYER))
    stage.SetEditTarget(Usd.EditTarget(layer))
    entries = {entry["name"]: entry for entry in record.get("objects") or []}
    holding = fitting.holders_of(record)
    fits = []
    for name, drop in sorted(downs(stage, place, record).items()):
        held = [other for other in parting.carried(name, holding)
                if other in entries and stage.GetPrimAtPath(f"/{place}/Objects/{other}")]
        for one in (name, *held):
            path = f"/{place}/Objects/{one}"
            fitting.changed_by(stage.GetPrimAtPath(path), Gf.Matrix4d(on_ground.moved([0.0, -drop, 0.0]).tolist()))
            fits.append(fitting.laid_fit(stage, path, entries[one], "floored", None, drop, 1.0,
                                         f"let down {drop:.2f} m onto what is under it: laid over it past what the "
                                         "settle lets down" + ("" if one == name else f" with {name}, which holds it")))
    if not fits:
        return []
    layer.Save()
    moved = {fit["name"]: fit for fit in fits}
    laid["objects"] = [{**entry, "low": moved[entry["name"]]["low"], "high": moved[entry["name"]]["high"],
                        **({"corners": [[round(float(value), 4) for value in point] for point in
                                        fitting.oriented_corners(stage, f"/{place}/Objects/{entry['name']}")]}
                           if "corners" in entry else {})}
                       if entry["name"] in moved else entry for entry in laid.get("objects", [])]
    laid["fitted"] = [*laid.get("fitted", []), *fits]
    laid_path.write_text(json.dumps(laid, indent=1))
    return fits
