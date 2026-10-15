"""The machines stage (experimental, PRD #6, until the owner reviews it): a place's machines (the garage's rover, the
hangar's ship, the workshop's robot), each a model the prop route made and the surface line painted, laid in the place
on what holds it up, as the place's machines layer, which the assembly stage puts into the place's stage. Code lays
the machines out only; what shows is the made model (owner, 2026-10-05). Their motion and effects are the motion and
effects stages' (captain, 2026-10-12): they ride the machine's prim, /<place>/Objects/<model>.

    make     each machine of the place's record (data/machines/<place>.json) written as the assembly writes a baked
             model (export.write_asset: the surface line's bake, its paint's labelled parts) under assets/, and laid
             in layers/machines.usda: turned across or along what it stands on (`turn`: its long side against the
             support's long side, or "x" or "z": along the place's axis), centred on the support's footprint (`off`
             metres off it in x and z) and let down from `drop_from` metres over the
             ground to the first thing under it; placed.json holds each pose, the drop and the outline measure
    gates    outline        likeness.py's outline of the baked model from eight ways round against its take's
                            close-up (the prop route's likeness gate, its free half) at least OUTLINE_LEAST
             parts present  every finish the take's close-up lists is owned by a part of its split (surfaces-parts,
                            likeness_row.finishes_missing)
             resting        resting.py's verdict on the machine in the composed stage (the machines layer over the
                            place's seed): no gap over what is under it, its weight over what it touches, nothing of
                            it sunk, and it lies in no other object deeper than resting.TOLERANCE

A place without a record has no row. DINOv2's likeness is not judged here until likeness.LIKENESS_LEAST is set (the
prop route's likeness row blocks on it the same way); the outline alone does not tell like shapes apart.
"""
import json
import math
import pathlib
import shutil
import sys
import tempfile

import numpy as np

from score import checks, contracts
from score.store import PROPS_HOME
import score.stages.props.likeness as likeness
import score.stages.props.likeness_row as likeness_row

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))  # already on the path by the assembly stage's import: no new folder
import resting  # noqa: E402

FOLDER = REPO / "data/machines"
LAYER = "layers/machines.usda"
SCRATCH = "scratch"  # the laid place, in the output's own folder while the make runs (laid_stage), then removed
# The settle stage's layer in its output (settling.LAYER; not imported, so a settle edit moves no machines key).
SETTLE_LAYER = "layers/settle.usda"
# How far over the ground a machine is let down from when its record names none, in metres: above a lift's arms and
# a pad's deck, under a lift's top beam.
DROP_FROM = 0.5
# Points of a machine looked down from to find what it lands on.
DROP_SAMPLES = 6000


def applies(place):
    return (FOLDER / f"{place}.json").exists()


def record_of(place):
    return json.loads((FOLDER / f"{place}.json").read_text())


def files(place):
    """The place's machines record, its seed (the layout the machines are laid in), what the asset writer reads (the
    library, the surfaces' sounds, the design tokens) and each machine's close-up (its take's Pixal3D input)."""
    found = {"record": "{data}/machines/{place}.json", "seed": "{seeds}/usd-r3/{place}", "library": "{data}/library",
             "sounds": "{data}/sound/surfaces.json", "tokens": "{repo}/design/tokens/tokens.json",
             "kit": "{data}/kit/{place}.json", "surfaces": "{data}/surfaces/{place}.json"}
    if (REPO / "data/scene" / f"{place}.json").exists():  # the laid place's (grounded.py), as the settle reads them
        found["scene"] = "{data}/scene/{place}.json"
    for model, entry in record_of(place)["machines"].items() if applies(place) else ():
        found[f"close-up {model}"] = "{home}/work/pixal/" + f"{entry['take']}.svviews/input.png"
    return found


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


# --- the layout ---------------------------------------------------------------------------------------------------

def seed_stage(seed, settled=None):
    """The place's seed stage, with its accepted settle layer over it where the place is settled (`settled`, the
    settle output): a machine stands on its support where the assembly stands it (assembly@garage, 2026-10-15: the
    settle let the rover's lift down 14 cm off and 3 degrees round, and the rover laid on the seed's lift lay 8.8 cm
    inside it)."""
    from pxr import Usd
    seed = pathlib.Path(seed)
    if settled is None:
        return Usd.Stage.Open(str(seed / f"{seed.name}.usda"))
    return Usd.Stage.Open(layered([pathlib.Path(settled) / SETTLE_LAYER, seed / f"{seed.name}.usda"], seed.name))


def laid_layers(inputs, folder):
    """The layers of the place as the assembly lays it, strongest first: its accepted settle layer, then its seed
    written in `folder` as the assembly lays it (grounded.py: its scene record, kit spots, bakes and made ground); the
    raw seed where the place's ground is not read (the tests' toy). The hangar's ship, laid on the raw seed, landed on
    the game's old ship that its structure still held and stood 48 cm up in the assembly, where the scene record lays
    no such ship (2026-10-15)."""
    seed = pathlib.Path(inputs["seed"])
    settled = [pathlib.Path(inputs["settle"]) / SETTLE_LAYER] if "settle" in inputs else []
    if "terrain" not in inputs:
        return [*settled, seed / f"{seed.name}.usda"]
    from score.stages.assembly.grounded import grounded_seed
    return [*settled, grounded_seed(inputs, pathlib.Path(folder))]


def laid_stage(inputs, folder):
    """The place as the assembly lays it (laid_layers), opened as one stage."""
    from pxr import Usd
    return Usd.Stage.Open(layered(laid_layers(inputs, folder), pathlib.Path(inputs["seed"]).name))


def layered(paths, place):
    """An anonymous root layer with `paths` as its sublayers, strongest first, its default prim the place."""
    from pxr import Sdf
    root = Sdf.Layer.CreateAnonymous(".usda")
    root.subLayerPaths = [str(path) for path in paths]
    root.defaultPrim = place
    return root


def drawn(prim):
    """An object's drawn mesh (its `geo`, never its collision) in the stage's frame."""
    import trimesh
    points, triangles = resting.in_stage(prim.GetChild("geo"))
    return trimesh.Trimesh(points, triangles, process=False)


def support_mesh(stage, place, name):
    """The drawn mesh of the object a machine stands on, in the stage's frame."""
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    if not (prim and prim.GetChild("geo").IsValid()):
        raise KeyError(f"/{place}/Objects/{name}: the support the record names is not in the place")
    return drawn(prim)


def everything_near(stage, place, low, high, leave_out="//"):
    """Every object's drawn mesh (but `leave_out` and its children), the structure's and the fixtures', whose box
    reaches over the footprint, joined; None when nothing does."""
    meshes = {path: drawn(prim) for path, prim in resting.objects_of(stage, place).items()
              if path != leave_out and not path.startswith(leave_out + "/")}
    return resting.neighbours({**meshes, **resting.structure_of(stage, place), **resting.fixtures_of(stage, place)},
                              leave_out, low, high)


def long_axis(extent):
    """0 when x is the longer horizontal side of a box's extent, 2 when z is."""
    return 0 if extent[0] >= extent[2] else 2


def turned(points, turn, support):
    """The machine's points and yaw (degrees) turned about y so its long side lies across or along the support's, or
    along the place's own x or z (`turn` "x" or "z": a square support has no long side, and the hangar's 31 m ship
    laid "along" its 7.2 m square pad lay across the 26 m hangar, 1.4 m in its walls, 2026-10-15).
    shortcut: the sides are read off world-axis boxes, so a support laid off the axes needs its own frame first."""
    mine = long_axis(np.ptp(points, axis=0))
    if turn in ("x", "z"):
        yaw = 0.0 if mine == "x?z".index(turn) else 90.0
    else:
        theirs = long_axis(np.ptp(support.vertices, axis=0))
        yaw = 0.0 if (mine == theirs) == (turn == "along") else 90.0
    cosine, sine = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    rotation = np.array([[cosine, 0.0, -sine], [0.0, 1.0, 0.0], [sine, 0.0, cosine]])  # row vectors, y up
    return points @ rotation, yaw, rotation


def drop_to_first(points, others, ground):
    """How far the points fall straight down before the first of them meets the ground or another surface."""
    sample = points[np.unique(np.concatenate([np.argsort(points[:, 1])[:resting.FOOTPRINT],
                                              np.linspace(0, len(points) - 1, DROP_SAMPLES).astype(int)]))]
    falls = sample[:, 1] - ground(sample[:, [0, 2]])
    if others is not None:
        hits, rays, _ = others.ray.intersects_location(sample, np.tile([0.0, -1.0, 0.0], (len(sample), 1)))
        under = np.full(len(sample), np.inf)
        np.minimum.at(under, rays, sample[rays, 1] - hits[:, 1])
        falls = np.minimum(falls, under)
    return float(np.nanmin(falls))


def pose(points, entry, stage, place):
    """A machine's placement: its 4x4 matrix (row vectors, as USD writes it), its yaw and how far it was let down."""
    support = support_mesh(stage, place, entry["on"])
    spun, yaw, rotation = turned(points, entry.get("turn", "along"), support)
    middle = (support.bounds[0] + support.bounds[1]) / 2
    ground = resting.ground_height(stage, place)
    centre = (spun.min(axis=0) + spun.max(axis=0)) / 2
    off = entry.get("off", (0.0, 0.0))  # metres off the support's middle in x and z: a machine longer than its room
    move = np.array([middle[0] - centre[0] + off[0], 0.0, middle[2] - centre[2] + off[1]])
    move[1] = float(np.nanmax(ground((spun + move)[:, [0, 2]]))) + entry.get("drop_from", DROP_FROM) - spun[:, 1].min()
    placed = spun + move
    low, high = placed.min(axis=0), placed.max(axis=0)
    drop = drop_to_first(placed, everything_near(stage, place, low, high), ground)
    move[1] -= drop
    matrix = np.eye(4)
    matrix[:3, :3], matrix[3, :3] = rotation, move
    return matrix, yaw, drop


# How near a mounted piece is set to its host's hull (metres), and how many of its points look for it (onto).
MOUNT_CLEAR, MOUNT_SAMPLES = 0.002, 2000
NOSES = {"+x": (1.0, 0.0, 0.0), "-x": (-1.0, 0.0, 0.0), "+z": (0.0, 0.0, 1.0), "-z": (0.0, 0.0, -1.0)}


def mount_point(low, high, nose, at):
    """Where a mounted piece's middle goes in the stage's frame: its host's placed box (low, high), the host's nose
    direction in the stage (+x, -x, +z or -z) and the piece's place in the host's own plan frame (x across, starboard
    positive; y back from the nose's tip; z up from the host's foot), metres (the ship plan's frame,
    data/definitions/ship.json)."""
    forward, up = np.array(NOSES[nose]), np.array([0.0, 1.0, 0.0])
    low, high = np.asarray(low, dtype=float), np.asarray(high, dtype=float)
    tip = (low + high) / 2 + forward * float(np.abs(forward) @ (high - low)) / 2
    tip[1] = low[1]
    return tip - forward * at[1] + np.cross(forward, up) * at[0] + up * at[2]


def onto_way(onto, points, low, high, nose):
    """The unit way a mounted piece moves onto its host's hull (`onto`): "up", or "in" (across, toward the host's
    middle line)."""
    if onto == "up":
        return np.array([0.0, 1.0, 0.0])
    if onto != "in":
        raise ValueError(f"`onto` {onto!r}: up or in")
    across = np.cross(np.array(NOSES[nose]), np.array([0.0, 1.0, 0.0]))
    side = float((points.mean(axis=0) - (np.asarray(low) + np.asarray(high)) / 2) @ across)
    return -np.sign(side) * across if side else across


def gap_to(points, hull, way):
    """How far a piece's points go along `way` before the first of them meets the hull, less MOUNT_CLEAR (0 where
    it already meets it); refused where nothing of the hull lies that way."""
    sample = points[np.linspace(0, len(points) - 1, min(len(points), MOUNT_SAMPLES)).astype(int)]
    hits, rays, _ = hull.ray.intersects_location(sample, np.tile(way, (len(sample), 1)))
    if not len(hits):
        raise ValueError("a mounted piece has no hull of its host its `onto` way")
    return max(0.0, float(((hits - sample[rays]) @ way).min()) - MOUNT_CLEAR)


def mounted_pose(points, entry, hosts, record):
    """A mounted piece's placement (the hangar ship's thrusters, set into its hull): turned as its host is and its
    middle at its mount point, then moved its `onto` way until it meets the host's baked hull (the plan's mount
    heights put the lift thrusters 0.15 to 1.07 m under the hull, judged floating 0.4 m up, 2026-10-15); never let
    down (its host holds it).
    shortcut: the piece keeps its host's turn, so a take modelled off the ship's axes needs a `turn` of its own."""
    host = entry["mounted"]["on"]
    nose = record["machines"][host].get("nose")
    if nose not in NOSES:
        raise ValueError(f"{host}: its nose's direction in the place (`nose`: +x, -x, +z or -z) is not in the "
                         "machines record; read it off the placed host's baked model")
    low, high, rotation, _, hull = hosts[host]
    spun = points @ rotation
    move = mount_point(low, high, nose, entry["mounted"]["at"]) - (spun.min(axis=0) + spun.max(axis=0)) / 2
    if entry["mounted"].get("onto"):
        way = onto_way(entry["mounted"]["onto"], spun + move, low, high, nose)
        move = move + way * gap_to(spun + move, hull, way)
    matrix = np.eye(4)
    matrix[:3, :3], matrix[3, :3] = rotation, move
    return matrix


# --- the make -----------------------------------------------------------------------------------------------------

def write_model(model, bake, paint, out):
    """The baked model under out/assets as the assembly writes it (assembly.take_bake); its baked .gltf."""
    import export
    import library
    baked = read_json(bake / "baked.json")
    if model not in baked:
        raise FileNotFoundError(f"{bake}: the surface line baked no {model} (is its take in the place's surface data?)")
    entry = baked[model]
    export.write_asset(model, bake / "made", {model: paint / "labelled" / entry["parts"]}, None, entry["base"],
                       entry["size"], out, library.variants(library.theme_library()),
                       json.loads(export.SOUNDS.read_text()))
    return bake / "made" / f"{model}.gltf"


def held_by(entry):
    """What holds a machine up: the support it stands on, or the host a mounted piece is set into."""
    return entry["mounted"]["on"] if "mounted" in entry else entry["on"]


def lay(layer, place, model, entry, matrix, sha256):
    """One machine's prim in the layer: the model's asset referenced (a piece laid more than once, the asset of the
    one model the bake made of its take: `model` in its entry), its record's words, its placement; its row is
    the record's inventory row (`row`), as every laid object's is, never the model's name: the garage's rover_idle sound
    plays at row rover, and the completion gate counts rows (assembly@garage, 2026-10-15: the rover laid as row rover_1
    left its sound playing at nothing)."""
    from pxr import Gf, Sdf
    objects = Sdf.CreatePrimInLayer(layer, f"/{place}/Objects")
    for path in (f"/{place}", f"/{place}/Objects"):
        layer.GetPrimAtPath(path).specifier = Sdf.SpecifierOver
    spec = Sdf.PrimSpec(objects, model, Sdf.SpecifierDef, "Xform")
    spec.referenceList.Prepend(Sdf.Reference(f"../assets/{entry.get('model', model)}.usdc"))
    values = {"score:kind": entry["kind"], "score:model": model, "score:model_sha256": sha256, "score:anchor": "floor",
              "score:row": entry["row"], "score:machine": entry["take"], "score:on": held_by(entry)}
    for name, value in values.items():
        Sdf.AttributeSpec(spec, name, Sdf.ValueTypeNames.String).default = value
    Sdf.AttributeSpec(spec, "score:fixed", Sdf.ValueTypeNames.Bool).default = False
    Sdf.AttributeSpec(spec, "xformOp:transform", Sdf.ValueTypeNames.Matrix4d).default = Gf.Matrix4d(matrix.tolist())
    Sdf.AttributeSpec(spec, "xformOpOrder", Sdf.ValueTypeNames.TokenArray, variability=Sdf.VariabilityUniform
                      ).default = ["xformOp:transform"]


def make(inputs, out, seed, params):
    """Every machine of the place's record made into its asset and laid in the machines layer; placed.json."""
    import trimesh
    from pxr import Sdf
    import stage_inputs
    record = read_json(inputs["record"])
    place = record["place"]
    stage = laid_stage(inputs, out / SCRATCH)
    (out / "layers").mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(out / LAYER))
    placed, hosts, written = {}, {}, {}
    # Hosts first, so a mounted piece finds its host laid.
    for model, entry in sorted(record["machines"].items(), key=lambda item: ("mounted" in item[1], item[0])):
        asset = entry.get("model", model)
        if asset not in written:
            written[asset] = write_model(asset, pathlib.Path(inputs["surfaces-bake"]),
                                         pathlib.Path(inputs["surfaces-paint"]), out)
        gltf = written[asset]
        points, triangles = likeness.gltf_mesh(gltf)
        if "mounted" in entry:
            matrix, yaw, drop = mounted_pose(points, entry, hosts, record), None, 0.0
        else:
            matrix, yaw, drop = pose(points, entry, stage, place)
            laid = points @ matrix[:3, :3] + matrix[3, :3]
            hosts[model] = (laid.min(axis=0), laid.max(axis=0), matrix[:3, :3], yaw,
                            trimesh.Trimesh(laid, np.asarray(triangles).reshape(-1, 3), process=False))
        lay(layer, place, model, entry, matrix, stage_inputs.model_hash(gltf))
        placed[model] = {"prim": f"/{place}/Objects/{model}", "take": entry["take"], "on": held_by(entry),
                         "asset": asset, "yaw": yaw, "at": matrix[3, :3].round(4).tolist(), "dropped": round(drop, 4),
                         **({"mounted": True} if "mounted" in entry else {}),
                         **likeness.best_way(gltf, inputs[f"close-up {model}"])}
    layer.Save()
    (out / "placed.json").write_text(json.dumps({"place": place, "machines": placed}, indent=1) + "\n")
    del stage
    shutil.rmtree(out / SCRATCH, ignore_errors=True)


def layer_faults(folder):
    folder = pathlib.Path(folder)
    if not (folder / LAYER).exists() or not (folder / "placed.json").exists():
        return [f"no {LAYER} or placed.json"]
    return [f"{model}: no asset" for model, entry in read_json(folder / "placed.json")["machines"].items()
            if not (folder / "assets" / f"{entry.get('asset', model)}.usdc").exists()]


# --- the gates ----------------------------------------------------------------------------------------------------

def placed_of(output):
    return read_json(pathlib.Path(output) / "placed.json")["machines"]


def composed(output, inputs, folder):
    """The machines layer over the place as the assembly lays it (laid_stage, written in `folder`), as one stage."""
    from pxr import Usd
    return Usd.Stage.Open(layered([pathlib.Path(output) / LAYER, *laid_layers(inputs, folder)],
                                  pathlib.Path(inputs["seed"]).name))


def verdict(name, failing, total, measures):
    return checks.Verdict(name, checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} of {total} machines fail" if failing else f"all {total} pass",
                          {"failing": len(failing), **measures}, {"failing": "lower"}, tuple(failing))


def judge_outline(output, inputs, evidence):
    """Each machine's best outline against its close-up at least likeness.OUTLINE_LEAST."""
    placed = placed_of(output)
    failing = [f"{model}: outline {entry['outline']:.3f} under {likeness.OUTLINE_LEAST}"
               for model, entry in sorted(placed.items()) if entry["outline"] < likeness.OUTLINE_LEAST]
    return verdict("outline", failing, len(placed), {"least outline": min(e["outline"] for e in placed.values())})


def judge_parts(output, inputs, evidence):
    """Every finish each machine's close-up lists is owned by a part of its take's split."""
    parts = read_json(pathlib.Path(inputs["surfaces-parts"]) / "parts.json")
    placed, failing, untold = placed_of(output), [], []
    for model, entry in sorted(placed.items()):
        missing = likeness_row.finishes_missing(entry["take"], parts)
        if missing is None:
            untold.append(model)
        failing += [f"{model}: misses {finish}" for finish in missing or ()]
    if untold and not failing:
        return checks.Verdict("parts present", checks.UNKNOWN, f"no split of {', '.join(untold)}'s take")
    return verdict("parts present", failing + [f"{model}: no split" for model in untold], len(placed),
                   {"missing finishes": len(failing)})


def overlapped(stage, place, name, mesh):
    """[(other object, depth)] of the objects the machine lies in deeper than resting.TOLERANCE."""
    found = []
    for path, prim in resting.objects_of(stage, place).items():
        if path == name or path.startswith(name + "/"):
            continue
        other = drawn(prim)
        low, high = np.maximum(mesh.bounds[0], other.bounds[0]), np.minimum(mesh.bounds[1], other.bounds[1])
        if np.any(low > high):
            continue
        depth = max(resting.overlap_depth(mesh, other), resting.overlap_depth(other, mesh))
        if depth > resting.TOLERANCE:
            found.append((path.removeprefix(f"/{place}/Objects/"), round(depth, 3)))
    return found


def rested(stage, place, model):
    """resting.py's verdict on one machine in the composed stage, with what it lies in."""
    name = f"/{place}/Objects/{model}"
    prim = stage.GetPrimAtPath(name)
    mesh = drawn(prim)
    found = resting.judged(model, prim, mesh, resting.ground_height(stage, place),
                           everything_near(stage, place, *mesh.bounds, leave_out=name))
    found["overlaps"] = overlapped(stage, place, name, mesh)
    return found


def judge_resting(output, inputs, evidence):
    """Every machine rests on what is under it and lies in nothing (resting.py, on the composed stage)."""
    with tempfile.TemporaryDirectory(prefix="machines-", dir=PROPS_HOME / "store/cache") as folder:
        return resting_verdict(output, composed(output, inputs, pathlib.Path(folder)))


def resting_verdict(output, stage):
    """judge_resting's verdict on the composed stage."""
    place = stage.GetDefaultPrim().GetName()
    failing, gaps = [], []
    for model, entry in sorted(placed_of(output).items()):
        if entry.get("mounted"):  # set into its host, which holds it: it lies in nothing else
            name = f"/{place}/Objects/{model}"
            failing += [f"{model}: lies {depth * 100:.0f} cm inside {other}"
                        for other, depth in overlapped(stage, place, name, drawn(stage.GetPrimAtPath(name)))
                        if other != entry["on"]]
            continue
        found = rested(stage, place, model)
        gaps.append(found.get("gap") or 0.0)
        if not found.get("passed", True):
            failing.append(f"{model}: {found['result']}")
        failing += [f"{model}: lies {depth * 100:.0f} cm inside {other}" for other, depth in found["overlaps"]
                    if not placed_of(output).get(other, {}).get("mounted")]
    return verdict("resting", failing, len(placed_of(output)), {"largest gap": max(gaps)})


LAYER_CONTRACT = contracts.Contract("machines-layer", 1, layer_faults, {"length": "metre", "up axis": "Y"})
AFTER = {"surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1),
         "surfaces-parts": ("surfaces-parts", 1), "settle": ("settle-layer", 1),
         "scene-record": ("scene-record", 1), "terrain": ("grounds", 1)}
CHECKS = (checks.Check("outline", judge_outline), checks.Check("parts present", judge_parts),
          checks.Check("resting", judge_resting))
