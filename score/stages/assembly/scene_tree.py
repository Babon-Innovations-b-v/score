"""The scene tree (CONTEXT.md "parent scene", "child scene"): a scene's accepted assembly with each child scene its
plan lays out referenced at its spot, so opening a parent scene opens the whole tree below it, each child scene still
its own layer stack, made, checked and changed apart. Free, local, no machine.

    make     copies the scene's accepted assembly, then each child scene's own tree (read beside, as the runner reads
             `after`: versioned and waited on; a child that holds scenes brings its own) into scenes/<child>/, and
             writes one layer of its own, layers/scenes.usda, the root's strongest sublayer: /<scene>/Scenes/<child>,
             an Xform referencing the child's root file with the transform that lays the child's plan outline on its
             hold of the scene's plan (its room outline in metres, x east and y south from the plan's north-west corner,
             each plan's frame in its own scene from scene_record.plan.frame_of), its middle on the hold's middle and
             its floor on the scene's floor. A scene that holds none is its assembly alone.
    gate     child scenes  every child the plan lays out, and every child read beside, stands under /<scene>/Scenes,
                           its reference resolves, it has children, its plan is the hold's size and its outline's
                           corners land on the hold's

The plan read is the one the scene's plan stage reads (stages.creator_plan): the creator's kept plan, else the data's.
"""
import json
import pathlib
import shutil

import numpy as np

from score import checks
from score.stages.assembly import stage_file
from score.stages.assembly.neighbours import reference_faults
from score.stages.scene_record.plan import frame_of, placed
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
KEPT = PROPS_HOME / "design" / "plans"  # the creator's kept plans (score/review/plans.KEPT)
SCENES = "Scenes"  # /<scene>/Scenes/<child>
FOLDER = "scenes"  # scenes/<child>/: each child's tree, copied whole
LAYER = "layers/scenes.usda"
TREE = "scene-tree"  # the stage's name: a child's tree is read beside as scene-tree@<child>
PLACED = 0.01  # metres a child's outline corner may land off its hold's
SIZED = 0.05  # metres a child's plan may differ from its hold in width or depth


def plan_path(place):
    """The plan the place's plan stage reads: the creator's kept plan, else data/plans; None with neither."""
    for path in (KEPT / f"{place}.json", REPO / "data/plans" / f"{place}.json"):
        if path.is_file():
            return path
    return None


def plan_pattern(place):
    """`plan_path` as a declared file's pattern, None with no plan."""
    path = plan_path(place)
    if path is None:
        return None
    return "{home}/design/plans/" + path.name if path.parent == KEPT else "{data}/plans/" + path.name


def holds(plan):
    """{child: hold} of the child scenes a plan lays out (its `holds`: place, row, x, y, w, d)."""
    return {hold["place"]: hold for hold in (plan or {}).get("holds", [])}


def read_plan(path):
    return json.loads(pathlib.Path(path).read_text()) if path else None


def held(place):
    """The child scenes the place's plan lays out, refused when one is the place itself or a scene above it (the
    tree's beside reads go down only: graph.Stage.downward)."""
    children = sorted(holds(read_plan(plan_path(place))))
    above = below(children, {place})
    if above:
        raise ValueError(f"{place}'s plan lays out {', '.join(sorted(above))}, which holds {place}: a scene "
                         "cannot hold itself")
    return children


def below(children, seen):
    """The scenes of `seen` found again walking down from `children` through their plans' holds."""
    found = set()
    for child in children:
        if child in seen:
            found.add(child)
            continue
        found |= below(sorted(holds(read_plan(plan_path(child)))), seen | {child})
    return found


def files(place):
    """The place's plan and each child scene's plan (its frame), where each has one."""
    named = {"plan": plan_pattern(place)}
    named.update({f"plan {child}": plan_pattern(child) for child in held(place)})
    return {name: pattern for name, pattern in named.items() if pattern}


def child_matrix(plan, hold, child_plan):
    """The 4x4 row-vector transform (OpenUSD's) taking a point of the child scene's frame to the parent's: the
    child's plan's north-west corner, east and south onto its hold's, its middle on the hold's middle."""
    corner, east, south = frame_of(plan)
    child_corner, child_east, child_south = frame_of(child_plan)
    up = np.array([0.0, 1.0, 0.0])
    turn = np.outer(east, child_east) + np.outer(south, child_south) + np.outer(up, up)  # p' = turn @ p
    across = hold["x"] + (hold["w"] - child_plan["w"]) / 2
    along = hold["y"] + (hold["d"] - child_plan["d"]) / 2
    shift = corner + east * across + south * along - turn @ child_corner
    matrix = np.identity(4)
    matrix[:3, :3] = turn.T
    matrix[3, :3] = shift
    return matrix


def make(inputs, out, seed, params):
    """The scene's assembly with each child scene's tree copied in and referenced at its hold."""
    from pxr import Gf, Sdf, Usd, UsdGeom
    shutil.copytree(inputs["assembly"], out, dirs_exist_ok=True, copy_function=shutil.copyfile)
    root = stage_file(out)
    scene = root.stem
    plan = read_plan(inputs.get("plan"))
    children = {name.partition("@")[2]: pathlib.Path(path) for name, path in inputs.items()
                if name.startswith(f"{TREE}@")}
    laid = holds(plan)
    standing = sorted(child for child in children if child in laid)
    if not standing:
        return
    layer_path = out / LAYER
    layer_path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(layer_path))
    stage.OverridePrim(f"/{scene}")
    UsdGeom.Scope.Define(stage, f"/{scene}/{SCENES}")
    for child in standing:
        shutil.copytree(children[child], out / FOLDER / child, copy_function=shutil.copyfile)
        child_root = stage_file(out / FOLDER / child)
        prim = UsdGeom.Xform.Define(stage, f"/{scene}/{SCENES}/{child}")
        prim.GetPrim().GetReferences().AddReference(f"../{FOLDER}/{child}/{child_root.name}")
        matrix = child_matrix(plan, laid[child], read_plan(inputs[f"plan {child}"]))
        prim.AddTransformOp().Set(Gf.Matrix4d(*matrix.flatten().tolist()))
    stage.GetRootLayer().Save()
    top = Sdf.Layer.FindOrOpen(str(root))
    top.subLayerPaths.insert(0, f"./{LAYER}")
    top.Save()


def corners(plan):
    """A plan's outline corners in its scene's frame: north-west, north-east, south-east, south-west."""
    return [placed(plan, x, y) for x, y in ((0.0, 0.0), (plan["w"], 0.0), (plan["w"], plan["d"]), (0.0, plan["d"]))]


def hold_corners(plan, hold, child_plan):
    """Where the child's outline corners belong on the parent's plan: on its hold, its middle on the hold's."""
    across = hold["x"] + (hold["w"] - child_plan["w"]) / 2
    along = hold["y"] + (hold["d"] - child_plan["d"]) / 2
    return [placed(plan, across + x, along + y)
            for x, y in ((0.0, 0.0), (child_plan["w"], 0.0), (child_plan["w"], child_plan["d"]),
                         (0.0, child_plan["d"]))]


def placement_faults(prim, scene_prim, plan, hold, child_plan):
    """Each way the composed child stands off its hold: its plan another size than the hold, a corner elsewhere."""
    from pxr import Gf, UsdGeom
    faults = []
    path = prim.GetPath()
    if abs(child_plan["w"] - hold["w"]) > SIZED or abs(child_plan["d"] - hold["d"]) > SIZED:
        faults.append(f"{path}: its plan is {child_plan['w']} x {child_plan['d']} m, its hold "
                      f"{hold['w']} x {hold['d']} m")
    cache = UsdGeom.XformCache()
    relative = cache.GetLocalToWorldTransform(prim) * cache.GetLocalToWorldTransform(scene_prim).GetInverse()
    for name, own, wanted in zip(("north-west", "north-east", "south-east", "south-west"), corners(child_plan),
                                 hold_corners(plan, hold, child_plan)):
        landed = np.array(relative.Transform(Gf.Vec3d(*own.tolist())))
        if np.linalg.norm(landed - wanted) > PLACED:
            faults.append(f"{path}: its {name} corner lands at {np.round(landed, 3).tolist()}, its hold's at "
                          f"{np.round(wanted, 3).tolist()}")
    return faults


def child_faults(stage, scene, plan, child, inputs):
    """Each fault of one child scene the plan lays out or the row read."""
    hold = holds(plan).get(child)
    prim = stage.GetPrimAtPath(f"/{scene}/{SCENES}/{child}")
    if hold is None:
        return [f"/{scene}/{SCENES}/{child}: read as a child scene, laid out nowhere on {scene}'s plan"]
    if not prim:
        why = "" if f"{TREE}@{child}" in inputs else " (no scene of the batch: its design is not done)"
        return [f"/{scene}/{SCENES}/{child}: laid out on {scene}'s plan, not in the stage{why}"]
    faults = reference_faults(prim)
    if not prim.GetChildren():
        faults.append(f"{prim.GetPath()}: no children, the child scene is empty")
    child_plan = read_plan(inputs.get(f"plan {child}"))
    if child_plan is None:
        return [*faults, f"{prim.GetPath()}: no plan of {child} read, its spot cannot be judged"]
    return faults + placement_faults(prim, stage.GetPrimAtPath(f"/{scene}"), plan, hold, child_plan)


def judge_children(output, inputs, evidence):
    """Fail when a child scene the plan lays out does not stand at its hold, resolve and hold something, or a child
    stands that the plan lays out nowhere; unknown with no plan read, since what the scene holds cannot be told (a
    parent scene whose plan is not kept yet would otherwise pass holding nothing)."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_file(pathlib.Path(output))))
    scene = stage.GetDefaultPrim().GetName()
    plan = read_plan(inputs.get("plan"))
    if plan is None:
        return checks.Verdict("child scenes", checks.UNKNOWN,
                              f"no plan of {scene} read: which child scenes it holds cannot be told")
    scope = stage.GetPrimAtPath(f"/{scene}/{SCENES}")
    standing = {prim.GetName() for prim in (scope.GetChildren() if scope else [])}
    read = {name.partition("@")[2] for name in inputs if name.startswith(f"{TREE}@")}
    children = sorted(set(holds(plan)) | read | standing)
    faults = [fault for child in children for fault in child_faults(stage, scene, plan, child, inputs)]
    reason = (f"{len(faults)} faults in {len(children)} child scenes" if faults
              else f"{len(children)} child scenes stand at their holds: {', '.join(children)}" if children
              else "its plan lays out no child scene")
    return checks.Verdict("child scenes", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "children": len(children)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("child scenes", judge_children),)
