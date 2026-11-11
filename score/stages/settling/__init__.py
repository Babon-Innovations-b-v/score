"""The settle stage (experimental, PRD #6, until the owner reviews it): where a place's objects come to rest on its made
ground, laid as an OpenUSD settle layer that the assembly stage puts into the place's stage over the seed's base.

    make     the seed (world 1's round-three stage) on the terrain stage's made ground (assembly.take_ground), every
             loose object dropped once in Newton on a rented card (tools/usd/settle.py's drop job, run by
             tools/usd/drop.py: an object an old settle left tipped onto uneven feet stood upright first, one stacked
             on another meeting it, a hollow one (a crate, a tray, a bin, a shelf) by its convex parts so what is stacked in it
             meets its floor: tools/usd/convex_parts.py, written beside the dropped stage), and each one's rest (settle.rest_poses: a small correction written, a large one left as laid,
             a tip onto uneven feet stood upright for the paint to level; one that fell into the hollow piece it
             lay on and rests inside it laid where it lands, landed_in_hollows); then each fixed one the triage finds
             floating as laid let down onto what is under it (held.fixed_let_down); then each held object stood
             upright and snapped down onto its holder as it rests (held.held_rests); and each object that then rests
             worse than as laid kept as laid with what it holds (kept_where_worse; one stood flush on its slope that
             rests worse goes back to the drop's own rest first, judged again: fallen_back); all laid as layers/settle.usda
             (an over of each moved object's transform), with settle.json (each object's rest and what it did) and the drop's own
             record (drop/settle-job.json, drop/settled.json). A drop is bought only when something loose is to be
             stood up or unstacked or the triage finds a fault on it (free, first); a drop already paid for (the same
             job, drop script and stage) is read back from DROPS, not bought again.
    gates    rested    the drop did not break: nothing still moving at its end, no two inside each other as the layer
                       lays them that were not as laid; and nothing left as laid inside another or a static ("laid
                       inside": a pair crossing as laid, kept as laid) or floating over what is under it: the layout's
                       fault, failed, back to the assembly's parting (laid_wrong); one kept as laid (it would turn or
                       drift past the settle's limits: its layout's or its model's fault) or stood upright on uneven
                       feet for the paint is named, not failed
             resting   the settle layer makes nothing rest worse: no object the resting triage finds a real fault on
                       on the seed with its made ground and the layer that it found none on without it (the feet
                       and lean of one stood upright for the paint aside), and no real overlap with it at all, as laid
                       or not; what is left is named, for the assembly's own drop and triage to judge on the baked
                       models

Only a place whose design shows a loose object has the row (score/stages/design_layers.py, physics), and its
assembly waits on it; any other place's assembly lays the seed's poses. The surface
stage's bakes are dropped, the very models the assembly lays (take_bakes, 2026-10-15): the seed's models, dropped so
the row need not wait on the paint, rested otherwise than the repainted bakes laid under their poses (the hangar's
control desk 2 degrees over, its keyboards on its sloping front).
"""
import json
import pathlib
import shutil
import sys
import tempfile

from score import checks, contracts
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import convex_parts  # noqa: E402
import drop  # noqa: E402
import settle  # noqa: E402
import snap  # noqa: E402
import triage  # noqa: E402
import whole_layer  # noqa: E402
from score.stages.settling import held as snapped  # noqa: E402
from score.stages.assembly.grounded import grounded_seed  # noqa: E402

LAYER = "layers/settle.usda"
RECORD = "settle.json"
DROP = "drop"
# One drop run's estimate: as the assembly's (up to half an hour of the physics trial's card with its start).
EUROS = 1.0
# Drops already paid for, by their job, drop script, its Python and stage (drop.drop_key): never bought twice.
DROPS = PROPS_HOME / "store/cache/drops"
# Each loose model's convex parts, once worked out (convex_parts.py, by its mesh): a library model's paid once.
PARTS = PROPS_HOME / "store/cache/convex-parts"
# Where the gates put a seed together to judge it (on disk, beside the store's cache).
SCRATCH = PROPS_HOME / "store/cache"
# How far round an object, and over or under its bottom, another may lie and hold it up (metres; supports_of).
SUPPORT_REACH = 0.1
# A rest the paint finishes: the faults the triage raises of an object stood upright on uneven feet.
FOR_THE_PAINT = ("foot off", "leans", "tips")
# How settle.dropped_pose says an object it keeps as laid past its limits (a turn or a drift).
PAST_LIMITS = "would not rest as laid:"


def files(place):
    """What the stage reads: the place's seed stage, kit (its seat and its pieces' spots), its design's surface data
    and scene inventory (what holds each object up), the resting rules, the row kinds (which rows swing, read by the
    assembly's fitting the grounded seed is laid by), and the drop script its machine runs with
    the trial script it borrows from and the Python both run in."""
    import stage_inputs
    found = {"seed": "{seeds}/usd-r3/{place}", "kit": "{data}/kit/{place}.json",
             "surfaces": "{home}/design/surfaces/{place}.json",
             "inventory": stage_inputs.inventory_pattern(place),
             "resting rules": "{data}/checks/resting.json",
             "row kinds": "{data}/checks/row-kinds.json",  # the assembly's fitting reads which rows swing from it
             "drop script": "{repo}/score/stages/settling/inside/settle_drop.py",  # run by path on the machine
             "trial script": "{repo}/score/stages/physics/inside/physics_trial.py",
             "drop env": "{repo}/score/stages/physics/inside/newton_env.sh"}
    return found


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def place_of(inputs):
    return pathlib.Path(inputs["seed"]).name


# --- the stage dropped -------------------------------------------------------------------------------------------

def with_anchors(inventory):
    """The inventory with a row's `anchor` read as no anchor where the reading wrote none (`null`): settle.py's
    held_on_loose reads it as text (settle@habitat, 2026-10-30), and settle.py sits in about 230 paid rows' code."""
    return {**inventory, "rows": [{**row, "anchor": row.get("anchor") or ""} for row in inventory["rows"]]}


def as_they_rest(inventory, record):
    """The inventory (with_anchors) with each row on a wall or ceiling row given that support (assembly/mounted.
    mounted: judged by touching, never as standing on what is under it) and each the scene `record` says rests
    leaning or attached the `fixed` support (mounted.resting_as_laid), as the assembly's resting check reads both:
    never dropped or snapped down, never judged on its feet; the settle leans a leaning one itself (leaning_phase).
    2026-11-07: settle@storage judged its wall lights 2.5 m up the left wall as floating and its wall pipes as
    standing on nothing, the assembly as mounted."""
    from score.stages.assembly.mounted import mounted, resting_as_laid
    rows = with_anchors(inventory)["rows"]
    given = {**mounted({row["id"]: row for row in rows}), **resting_as_laid(record or {})}
    return {**inventory, "rows": [{**row, "support": given[row["id"]]} if row["id"] in given and not row.get("support")
                                  else row for row in rows]}


def scene_record(root):
    """The scene record grounded_seed wrote beside the stage at `root`, None where it wrote none."""
    import score.stages.assembly.record as laid_record  # this form: as grounded_seed reads it
    path = pathlib.Path(root).parent / laid_record.RECORD
    return read_json(path) if path.is_file() else None


def rested_inputs(inputs, root, inventory):
    """The inputs with their inventory the one the settle judges by (as_they_rest), written beside `root`."""
    path = pathlib.Path(root).parent / "rested-inventory.json"
    path.write_text(json.dumps(inventory))
    return {**inputs, "inventory": str(path)}


def make(inputs, out, seed, params):
    """Drop the place's loose objects on its made ground and lay where each comes to rest. The grounded seed is put
    together in the output's own folder and taken out again once the drop is read."""
    from pxr import Usd
    place = place_of(inputs)
    scratch = out / "scratch"
    try:
        root = grounded_seed(inputs, scratch)
        record = scene_record(root)
        inventory = as_they_rest(read_json(inputs["inventory"]), record)
        inputs = rested_inputs(inputs, root, inventory)
        seed = laid_stage(root)  # the poses as laid, which no settle layer moves
        stage = Usd.Stage.Open(str(root))
        loose, ignore, starts, under = settle.drop_job(stage, place, inventory, upright=True, kit_path=inputs["kit"])
        found = judged(root, inputs)
        laid = faulty(found, place)
        hollow, unsplit = {}, {}  # the objects dropped as convex parts; those CoACD failed on, as their one hull
        if starts or under or laid & set(loose):
            hollow, unsplit = convex_parts.hollow_parts(stage, place, loose, PARTS)
            (root.parent / convex_parts.FILE).write_text(json.dumps(hollow, indent=1))
            simulated = drop.simulate(root, loose, out / DROP, cloud=True, ignore=ignore, start=starts, under=under,
                                      cache=DROPS)
        else:  # nothing loose to stand up, unstack or put right: no drop is bought, each rests as laid
            simulated = still(loose, out / DROP)
        poses = settle.rest_poses(stage, place, inventory, simulated, starts,
                                  room="room" in read_json(inputs["kit"]))
        poses = landed_in_hollows(stage, place, poses, simulated, under, hollow)
        meshes = snap.read_place(root) if simulated["overlaps"] else None  # as laid: no layer is over the root yet
        bedding = beds(stage, place, inputs)
        as_laid = crossing(meshes, simulated["overlaps"], {}, bedding)
        poses = laid_inside_each_other(poses, as_laid)
        poses = kept_with_their_supports(poses, under)
        laid_over(root, seed, place, poses, scratch / "dropped.usda")
        poses = merged(poses, fixed_phase(root, found, place), seed, place)  # before the held: they lie on these
        poses = merged(poses, held_phase(root, scratch / "fixed.usda", inputs, inventory, poses, seed), seed, place)
        ways = snapped.leaning(record or {})
        poses = merged(poses, leaning_phase(root, scratch / "leant.usda", place, ways, poses, seed), seed, place)
        laid_over(root, seed, place, poses, scratch / "held.usda")
        rested = judged(root, inputs)
        poses = merged(poses, fixed_phase(root, rested, place, ("floor",)), seed, place)  # a hull's hollow on the drop
        worse = faulty(rested, place) - laid
        poses, fell_back = fallen_back(poses, worse)
        if fell_back:  # each now at the drop's own rest, judged again
            laid_over(root, seed, place, poses, scratch / "fallback.usda")
            worse = faulty(judged(root, inputs), place) - laid
        rested_stage = Usd.Stage.Open(str(root))
        poses = kept_where_worse(poses, worse | supports_of(rested_stage, place, worse), inventory,
                                 lambda name: supports_of(rested_stage, place, {name}))
        write_layer(seed, place, moved(poses), out / LAYER)
        overlaps = crossing(meshes, [pair for pair in simulated["overlaps"] if pair not in as_laid], motions(poses),
                            bedding)
        del stage, seed
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    (out / RECORD).write_text(json.dumps({
        "place": place, "overlaps": overlaps, "laid inside each other": as_laid, "one hull": unsplit,
        **({"leaning": ways} if ways else {}),
        "objects": {name: {"rested": pose["rested"], "said": pose["said"], "matrix": pose["after"].tolist()}
                    for name, pose in sorted(poses.items())}}, indent=1))


def laid_stage(root):
    """The grounded seed at `root` as laid, before any settle layer is put over it: a copy of its root layer opened
    on its own (laid_over writes each step's layer into the root's own). Not the seed folder's root: an earth seed lays
    no object, its scene record does (grounded_seed's take_record), and every held object's laid matrix read there was
    an invalid prim (settle@engineroom and @greenhouse, 2026-10-28)."""
    from pxr import Usd
    laid = root.with_name(f"laid-{root.name}")
    shutil.copyfile(root, laid)
    return Usd.Stage.Open(str(laid))


def landed_in_hollows(stage, place, poses, simulated, under, hollow):
    """The poses with each object the drop would have kept as laid (past the settle's limits) that fell into the
    hollow piece it is stacked on and came to rest inside it laid where it lands (laid_where_it_lands), read off the
    stage and the drop."""
    import numpy as np
    for name, pose in list(poses.items()):
        support = (under.get(name) or [None])[0]
        if support not in poses or name not in simulated["objects"]:
            continue
        rest = np.asarray(simulated["objects"][name]["motion"]) @ pose["before"]
        middle = (rest @ np.append(settle.object_middle(stage, place, name), 1.0))[:3]
        moved_support = poses[support]["after"] @ np.linalg.inv(poses[support]["before"])
        corners = np.c_[settle.box_corners(stage, place, support), np.ones(8)] @ moved_support.T
        poses[name] = laid_where_it_lands(pose, rest, middle, under.get(name, []), hollow, poses[support],
                                          corners[:, :3])
    return poses


def laid_where_it_lands(pose, rest, middle, supports, hollow, support_pose, corners):
    """An object's pose, laid where the drop leaves it (`rest`, rested) when it would not rest as laid only because it
    fell into a hollow piece: its one support (`supports`) is dropped as its convex parts (named in `hollow`), rests
    itself (`support_pose`), and the object's middle at rest (`middle`, stage frame) lies inside that support's box as
    it rests (`corners`, its 8 corners in the stage's frame, settle.box_corners' order). Falling straight into an open
    crate is where it belongs, not a drift (owner's rule, 2026-10-26); anything else keeps the limits."""
    if pose["rested"] or not pose["said"].startswith(PAST_LIMITS) or len(supports) != 1 \
            or supports[0] not in hollow or not support_pose["rested"]:
        return pose
    frame = settle.upright_frame(corners)
    low, high = settle.box_in(frame, corners)
    if not ((low <= frame @ middle) & (frame @ middle <= high)).all():
        return pose
    return {**pose, "after": rest, "rested": True,
            "said": f"fell into {supports[0]}, a hollow piece, and rests inside it: laid where it lands "
                    f"({pose['said'].removeprefix(PAST_LIMITS).strip()})"}


def crossing(laid, pairs, motions, beds):
    """The pairs of objects (names) one of which lies inside the other by the resting triage's own rule
    (triage.overlap_faults): their drawn triangles cross, one lies deeper inside the other than TOLERANCE plus its own
    bedding allowance (`beds`, {name: metres}, triage.bedding), and it still meets the other once nudged NUDGE away
    from it; each moved from as laid by its motion ({name: 4 x 4 in the stage's frame}, none: as laid), on the meshes
    of snap.read_place(`laid`). A touch or a thin crossing is no pair inside each other: quarters' lockers touching
    and habitat's beds on their 1.7 cm rugs read as ten and sixteen broken drops the triage found nothing on
    (checkout 83, 2026-11-10). The drop's own overlaps are its poses', which the layer never writes for one it keeps
    as laid."""
    import collide
    import numpy as np
    scene = collide.Scene()
    meshes = {}
    for name in {name for pair in pairs for name in pair}:
        motion = motions.get(name, np.eye(4))
        scene.add(name, name, laid["objects"][name].vertices, laid["objects"][name].faces, motion)
        meshes[name] = laid["objects"][name].copy().apply_transform(motion)
    return [pair for pair in pairs
            if scene.intersection_test(*pair) and inside_past_the_triage(pair, meshes, scene, beds)]


def inside_past_the_triage(pair, meshes, scene, beds):
    """Whether one of a crossing pair lies inside the other as the resting triage counts an overlap: deeper than
    TOLERANCE plus its bedding allowance, and still meeting the other after the NUDGE away from it."""
    import resting
    first, second = pair
    depth = max(resting.overlap_depth(meshes[first], meshes[second]),
                resting.overlap_depth(meshes[second], meshes[first]))
    return any(depth > triage.TOLERANCE + beds.get(name, 0.0)
               and scene.intersection_test(name, other, triage.nudge_way({"mesh": meshes[name]}, meshes[other])
                                           * triage.NUDGE)
               for name, other in ((first, second), (second, first)))


def beds(stage, place, inputs):
    """{object: how deep its class may bed into what it lies on} (triage.bedding) of each object laid on the stage,
    by its inventory row (`inputs`' inventory) and the declared resting rules."""
    import resting
    data = triage.rules(inputs["resting rules"])
    rows = triage.inventory_rows(place, None, inputs["inventory"])
    return {path.removeprefix(f"/{place}/Objects/"): triage.bedding(rows.get(prim.GetAttribute("score:row").Get(), {}),
                                                                    data)[0]
            for path, prim in resting.objects_of(stage, place).items()}


def laid_inside_each_other(poses, pairs):
    """The poses with both objects of each pair that already crosses as laid (`pairs`: the drop's loose-to-loose
    collision is off, so the plan's crossing sandbags stay crossed) kept as laid, said "laid inside <other>", as one
    laid inside a static is (settle.rest_poses): the layout's fault, which the assembly's resting gate judges, not a
    broken drop (settle@airlock, 2026-10-30). One already left as laid keeps its own word."""
    import numpy as np
    others = {}
    for first, second in pairs:
        others.setdefault(first, []).append(second)
        others.setdefault(second, []).append(first)
    return {name: ({**pose, "after": pose["before"], "rested": False,
                    "said": f"laid inside {', '.join(sorted(others[name]))}; left as laid"}
                   if name in others and (pose["rested"] or not np.allclose(pose["after"], pose["before"]))
                   else pose)
            for name, pose in poses.items()}


def kept_with_their_supports(poses, under):
    """The poses with each object stacked on a loose support (`under`, settle.stacked_under) kept as laid where the
    layer leaves that support unrested (as laid, or stood up for the paint): the stacked one's rest was found on the
    support where the drop left it, so over the support as the layer lays it, it crosses it (settle@airlock's
    sandbags_18 rested 52 cm down ramp_1, which the drop let sink 7 cm into the deck and the layer keeps as laid inside
    it, 2026-10-30). Down a stack: what is kept keeps what is stacked on it. One already left as laid keeps its word."""
    import numpy as np
    poses = dict(poses)
    changed = True
    while changed:
        changed = False
        for name, supports in under.items():
            pose = poses.get(name)
            kept = [support for support in supports if support in poses and not poses[support]["rested"]]
            if pose is None or not kept or not (pose["rested"] or not np.allclose(pose["after"], pose["before"])):
                continue
            poses[name] = {**pose, "after": pose["before"], "rested": False,
                           "said": f"stacked on {', '.join(kept)}, which is left as laid; left as laid"}
            changed = True
    return poses


def motions(poses):
    """{name: how the layer moves it from as laid} of each pose."""
    import numpy as np
    return {name: pose["after"] @ np.linalg.inv(pose["before"]) for name, pose in poses.items()}


def judged(root, inputs):
    """The resting triage of the stage at `root` on the declared rules, kit and inventory."""
    return triage.triage(root, None, rules_file=inputs["resting rules"], kit_file=inputs["kit"],
                         inventory_file=inputs["inventory"])


def faulty(found, place):
    """The top-level objects a triage finds a real fault on, by name (the free check before a drop is bought, and
    after one what it made worse)."""
    names = {fault["object"].removeprefix(f"/{place}/Objects/") for fault in found["faults"] if fault["real"]}
    return {name.split("/")[0] for name in names}


def fallen_back(poses, worse):
    """Each object stood flush on the slope (settle.flush_on_slope) that rests worse so, put back at the drop's own
    rest (its `fallback`), not kept as laid: the wreck's probe lander lost its 1 degree, 2 cm rest when its flush pose
    rested worse (2026-10-15). (the poses, the names put back)."""
    back = {name for name in worse if "fallback" in poses.get(name, {})}
    return {name: (dict(pose["fallback"], said=f"{pose['said']} rested worse; the drop's rest: "
                                               f"{pose['fallback']['said']}") if name in back else pose)
            for name, pose in poses.items()}, back


def kept_where_worse(poses, worse, inventory, resting_on):
    """Each object that rests worse than as laid (`worse`: names with a real fault now and none before: a model with
    a sloping base the drop tips over the triage's lean, a mouse snapped onto a desk's edge), and what is held on it,
    kept as laid: the layer never makes an object rest worse. Held on it is held on that very object
    (`resting_on(name)`: the objects it rests on, supports_of), not on any of its row: one pallet resting worse kept
    every case on all four of the campgrounds' pallets as laid, 5 degrees over on theirs (2026-10-15)."""
    held_on = {row["id"]: row.get("anchor", "").removeprefix("on:") for row in inventory["rows"]}
    rows = {name.rsplit("_", 1)[0] for name in worse}
    kept = {name for name in poses if name in worse
            or (held_on.get(name.rsplit("_", 1)[0]) in rows and resting_on(name) & worse)}
    return {name: (dict(pose, after=pose["before"], rested=False,
                        said=f"kept as laid: {pose['said']} made it, or what lies on it, rest worse") if name in kept
                   else pose)
            for name, pose in poses.items()}


def supports_of(stage, place, names):
    """The objects each named one may rest on as it lies: under its footprint (SUPPORT_REACH wider) with their top
    within SUPPORT_REACH of its bottom (the greenhouse's keyboard, kept as laid, ended a foot off when the cabinet
    beside the console it lies on was settled 6 cm: the cabinet is kept as laid too)."""
    import numpy as np
    from pxr import Usd, UsdGeom
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    boxes = {}
    for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if not box.IsEmpty():
            boxes[prim.GetName()] = (np.asarray(box.GetMin()), np.asarray(box.GetMax()))
    found = set()
    for name in names & set(boxes):
        low, high = boxes[name]
        found |= {other for other, (other_low, other_high) in boxes.items() if other != name
                  and abs(other_high[1] - low[1]) <= SUPPORT_REACH
                  and np.all(other_low[[0, 2]] <= high[[0, 2]] + SUPPORT_REACH)
                  and np.all(other_high[[0, 2]] >= low[[0, 2]] - SUPPORT_REACH)}
    return found


def still(loose, folder):
    """A drop's record in which every loose object rests as laid (no drop was needed), written as a drop's is."""
    import numpy as np
    folder.mkdir(parents=True, exist_ok=True)
    found = {"objects": {name: {"motion": np.eye(4).tolist(), "moving": 0.0, "inside": []} for name in sorted(loose)},
             "overlaps": [], "dropped": False}
    (folder / "settled.json").write_text(json.dumps(found, indent=1))
    return found


def moved(poses):
    """{name: its rest} of each pose that moves its object."""
    import numpy as np
    return {name: pose["after"] for name, pose in poses.items() if not np.allclose(pose["after"], pose["before"])}


def merged(poses, found, seed, place):
    """A later step's poses over the earlier ones, each from the seed's laid matrix; one the later step left as laid
    keeps where the earlier put it."""
    for name, pose in found.items():
        earlier = poses.get(name, {}).get("after")
        kept = pose["after"] is pose["before"] and earlier is not None
        poses[name] = {**pose, "before": settle.laid_matrix(seed, place, name),
                       "after": earlier if kept else pose["after"]}
    return poses


def laid_over(root, seed, place, poses, path):
    """The poses so far written as a layer at `path`, put over everything else the scratch root holds."""
    from pxr import Sdf
    write_layer(seed, place, moved(poses), path)
    layer = Sdf.Layer.FindOrOpen(str(root))
    layer.subLayerPaths = [str(path), *layer.subLayerPaths]
    layer.Save()


def held_phase(root, path, inputs, inventory, poses, seed):
    """Each held object at rest on its holders as they rest (held.held_rests; one the scene record lays on its
    holder's side left as laid), and its own glowing parts carried with it: {name: pose}."""
    from pxr import Usd
    import score.stages.assembly.record as laid_record  # this form: as grounded_seed reads it
    place = place_of(inputs)
    laid_over(root, seed, place, poses, path)
    record = pathlib.Path(root).parent / laid_record.RECORD  # the scene record grounded_seed wrote beside the stage
    held = snapped.held_rests(root, place, inventory, inputs["kit"],
                              json.loads(record.read_text()) if record.is_file() else None)
    rested = Usd.Stage.Open(str(root))
    entries = {name: {"before": pose["before"], "after": pose["after"],
                      "middle": settle.object_middle(rested, place, name)}
               for name, pose in held.items() if pose["rested"]}
    held.update({name: {**found, "rested": True, "said": "carried with what it lies on"}
                 for name, found in settle.carried_with(rested, place, inventory, entries).items()})
    return held


def leaning_phase(root, path, place, ways, poses, seed):
    """Each leaning object (`ways`, held.leaning) rested on its foot against its holder over the poses so far
    (held.leaning_rests): {name: pose}; none without one."""
    if not ways:
        return {}
    laid_over(root, seed, place, poses, path)
    return snapped.leaning_rests(root, place, ways)


def fixed_phase(root, found, place, supports=("fixed",)):
    """Each object of these supports the triage (`found`) finds floating, let down onto what is under it
    (held.fixed_let_down): {name: pose}. A fixed one as laid; after the drop a loose one too, which the drop rests on
    its convex hull: the wreck's aft section, a hull open at its end, lay 4.6 cm over the crater rim its hull met."""
    floating = sorted({fault["object"].removeprefix(f"/{place}/Objects/") for fault in found["faults"]
                       if fault["real"] and fault["kind"] == "floats" and fault["support"] in supports})
    return snapped.fixed_let_down(root, place, [name for name in floating if "/" not in name])


def write_layer(stage, place, matrices, path):
    """An over of each object's transform ({name: its matrix in the stage's frame}, written in its parent's frame)
    as an OpenUSD layer."""
    import numpy as np
    from pxr import Gf, Sdf, Usd, UsdGeom
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    for name, matrix in sorted(matrices.items()):
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        parent = UsdGeom.Xformable(prim.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        parent = np.asarray(parent).T
        local = np.linalg.inv(parent) @ np.asarray(matrix)
        spec = Sdf.CreatePrimInLayer(layer, prim.GetPath())
        spec.specifier = Sdf.SpecifierOver
        transform = Sdf.AttributeSpec(spec, "xformOp:transform", Sdf.ValueTypeNames.Matrix4d)
        transform.default = Gf.Matrix4d(local.T.tolist())
        order = Sdf.AttributeSpec(spec, "xformOpOrder", Sdf.ValueTypeNames.TokenArray,
                                  variability=Sdf.VariabilityUniform)
        order.default = ["xformOp:transform"]
    whole_layer.stamped(layer, place).Save()


def layer_faults(folder):
    """The settle layer and its record are there."""
    folder = pathlib.Path(folder)
    return [f"no {part}" for part in (LAYER, RECORD, f"{DROP}/settled.json") if not (folder / part).exists()]


# --- the gates ---------------------------------------------------------------------------------------------------

def judge_rested(output, inputs, evidence):
    """Fail when the drop broke: an object still moving at its end, or two at rest inside each other (a rest of at
    least one written); and when one is left as laid inside another or a static, or floating over what is under it
    (laid_wrong: its layout's fault, which no settle mends). One that would not rest as laid keeps its pose (its fault
    stays where it was, for its layout or its model; counted as `kept`, lower is better) and one stood upright on
    uneven feet waits on the paint (named, not counted): neither fails the row."""
    record = read_json(pathlib.Path(output) / RECORD)
    faults = [f"{name}: {entry['said']}" for name, entry in sorted(record["objects"].items())
              if "still moving" in entry["said"]]
    faults += [f"{first} and {second} came to rest inside each other" for first, second in record["overlaps"]
               if any(record["objects"].get(name, {}).get("rested") for name in (first, second))]  # not both kept
    faults += [f"{name}: {entry['said']} (its layout's fault: back to the assembly's parting)"
               for name, entry in sorted(record["objects"].items()) if laid_wrong(entry)]
    faults += leaning_wrong(output, inputs, record)
    unrested = [(name, entry) for name, entry in sorted(record["objects"].items())
                if not entry["rested"] and "still moving" not in entry["said"] and not laid_wrong(entry)]
    kept = [f"{name}: {entry['said']}" for name, entry in unrested if not for_the_paint(entry)]
    for_paint = [f"{name}: {entry['said']}" for name, entry in unrested if for_the_paint(entry)]
    reason = (f"{len(faults)} drops broke" if faults else f"all {len(record['objects'])} rests found") + \
        (f"; {len(kept)} kept as laid" if kept else "") + \
        (f"; {len(for_paint)} stood up for the paint" if for_paint else "")
    # `kept` counts only what stays as laid: one stood up for the paint is a rest put right, named, not scored (the
    # lab's chairs stood up off a raised caster read as 2 kept become 3, 2026-10-15)
    return checks.Verdict("rested", checks.FAIL if faults else checks.PASS, reason,
                          {"broken": len(faults), "kept": len(kept)}, {"broken": "lower", "kept": "lower"},
                          tuple(faults) + tuple(kept) + tuple(for_paint))


def leaning_wrong(output, inputs, record):
    """Each leaning object (the record's `leaning`, held.leaning) that falls or floats as the settle layer lays it
    over the seed on its made ground (held.leaning_faults, measured there, never read off the record's words): one
    that leans on nothing, lies past held.LEAN_FALLS, meets nothing toward its holder or stands its foot off the
    floor (#94)."""
    ways = record.get("leaning") or {}
    if not ways:
        return []
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH) as scratch:  # on disk: a seed copy is too big for /tmp
        root = rested_root(output, inputs, pathlib.Path(scratch))
        return snapped.leaning_faults(root, place_of(inputs), ways)


def laid_wrong(entry):
    """Whether an object is left as laid because its layout is wrong, not its rest: laid inside another object or a
    static (rest_poses, laid_inside_each_other: galley's chairs inside its dining table, its counters inside each
    other, settled and accepted on 2026-11-03), or floating over what is under it past what a let-down may move
    (held.fixed_let_down: the hangar's ship 72 cm up). The settle never mends either, and kept as laid it is no rest:
    the gate fails it, so the layout goes back to the assembly's parting or its maker, never on to be accepted."""
    said = entry["said"]
    return not entry["rested"] and said.endswith("left as laid") and (
        said.startswith("laid inside ") or (said.startswith("floats ") and "over what is under it" in said))


def for_the_paint(entry):
    """Whether an object's rest is a stand upright on uneven feet (settle.rest_poses), for the paint to finish."""
    return not entry["rested"] and entry["said"].endswith("stood upright on its lowest foot")


def judge_resting(output, inputs, evidence):
    """Fail when the settle layer makes any object rest worse: an object the resting triage finds a real fault on, on
    the seed with its made ground and the settle layer, that it found none on without the layer (the feet and lean of
    an object stood upright for the paint aside), and on every real overlap the triage finds with the layer, whether
    or not it was there as laid (one overlap gate over the final layout, held or not). What is left is named; the
    assembly's own drop and triage judge it on the baked models."""
    record = read_json(pathlib.Path(output) / RECORD)
    for_paint = {name for name, entry in record["objects"].items() if for_the_paint(entry)}
    found, contained = {}, {}
    for state, layered in (("before", False), ("after", True)):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as scratch:  # on disk: a seed copy is too big for /tmp
            root = rested_root(output, inputs, pathlib.Path(scratch), layered)
            laid = scene_record(root)
            contained = within_of(laid) if layered else contained
            rested = rested_inputs(inputs, root, as_they_rest(read_json(inputs["inventory"]), laid))
            found[state] = triage.triage(root, rules_file=inputs["resting rules"], kit_file=inputs["kit"],
                                         inventory_file=rested["inventory"])
    real = {state: [fault for fault in found[state]["faults"] if fault["real"]
                    and not (fault["object"].rsplit("/", 1)[-1] in for_paint and fault["kind"] in FOR_THE_PAINT)
                    and not planned_within(fault, contained)]
            for state in found}
    worse = worse_faults(real["before"], real["after"])
    objects = {state: len({fault["object"] for fault in real[state]}) for state in real}
    findings = tuple(f"{'worse' if fault in worse else 'left'}: {fault['object']}: {fault['kind']} {fault['measure']}: "
                     f"{fault['why']}" for fault in sorted(real["after"], key=lambda fault: fault not in worse))
    reason = (f"{objects['after']} of {found['after']['objects']} objects with real resting faults rested, "
              f"{objects['before']} as laid" + (f"; {len(worse)} faults new with the settle layer or overlapping"
                                                if worse else ""))
    return checks.Verdict("resting", checks.FAIL if worse else checks.PASS, reason,
                          {"objects with faults": objects["after"], "as laid": objects["before"], "worse": len(worse)},
                          {"objects with faults": "lower", "worse": "lower"}, findings)


def within_of(record):
    """{object: the objects its plan lays it within} of the scene record's objects (`on` how "within": plants in their
    planter bed, a suit in its locker); {} without a record."""
    return {entry["name"]: set((entry.get("on") or {}).get("holder") or []) for entry in (record or {}).get("objects")
            or [] if (entry.get("on") or {}).get("how") == "within"}


def planned_within(fault, contained):
    """Whether an overlap is one thing laid within the other by its plan: the plan's own placement, not a fault
    (2026-11-09: greenhouse's plants in their planter beds failed settle as ten overlaps). A thing on another, or two
    unrelated things, still fail inside each other, as worse_faults says."""
    if fault["kind"] != "overlaps" or not fault.get("partner"):
        return False
    one, other = fault["object"].rsplit("/", 1)[-1], str(fault["partner"]).rsplit("/", 1)[-1]
    return other in contained.get(one, ()) or one in contained.get(other, ())


def worse_faults(before, after):
    """The real faults `after` (the triage's with the settle layer) that fail the resting gate: each on an object with
    none `before` (as laid; an object at fault as laid is no worse for another kind), and every overlap, which being
    one as laid never excuses: two things inside each other fail, held or not, as laid or not (galley's chairs in its
    table, quarters' lockers in each other, accepted on 2026-11-03)."""
    was = {fault["object"] for fault in before}
    return [fault for fault in after if fault["object"] not in was or fault["kind"] == "overlaps"]


def rested_root(output, inputs, folder, layered=True):
    """The seed on its made ground, its kit pieces at their kit spots (grounded_seed), in `folder`, with the settle
    layer over it unless not `layered`: the stage the assembly lays, but for the bakes and the other layers."""
    from pxr import Sdf
    root = grounded_seed(inputs, folder)
    if layered:
        layer = Sdf.Layer.FindOrOpen(str(root))
        layer.subLayerPaths = [str(pathlib.Path(output) / LAYER), *layer.subLayerPaths]
        layer.Save()
    return root


SETTLE_LAYER = contracts.Contract("settle-layer", 1, layer_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("rested", judge_rested), checks.Check("resting", judge_resting))
