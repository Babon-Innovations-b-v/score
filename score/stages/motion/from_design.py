"""A scene's rigid moves made from its design, never written by hand (the owner, 2026-10-21: "the modules are not
agnostic"): every object of a scene inventory row whose kind moves (score/stages/row_kinds.py) moves as its kind's
rule says (data/checks/row-kinds.json `motion`), at the speed its motion kind's cited range gives
(data/checks/motion.json), or stands with the rule's reason. The rules, each general:

    swing   a leaf turned about the upright line through a point on its own box (`hinge`: from the box's middle, each
            axis a share of its half size; a door's left edge, a crane's own middle) `angle` degrees open and shut
            again once a round, at the middle of its kind's cited turning speeds
    spin    turned steadily about its own middle at the whole number of turns a round nearest the middle of its
            kind's cited speeds, so the layer loops
    still   standing, with the rule's reason
    lying   a swing turns about an upright line, so only a thing standing upright swings: one whose own box is lower
            than it is wide both ways (a hatch in a floor, a crane spanning a hall on its rails) stands, with LYING
    needs   a rule that moves only when the scene holds what it serves (a door swings only where somebody passes
            through it: a row whose kind `does` the need), else it stands with `still_without`

    record(place, inventory, kinds, motion_kinds, stage)   the rigid record tools/usd/motion_layer.py writes
"""
from score.stages import row_kinds

# One round of the layer, seconds, and when in it a swinging thing opens and shuts again.
ROUND = 20.0
OPENS, SHUTS = 2.0, 10.0
MOTION_KINDS = "data/checks/motion.json"
LYING = ("it lies lower than it is wide both ways (its own box), so it would turn about a level line or travel on "
         "rails, never about the upright line a swing turns on: it stands as the plan lays it")


def middle_speed(rule, measure):
    """The middle of a motion kind's cited speed range (`angular` degrees or `linear` metres a second)."""
    low, high = rule[measure]
    return (float(low) + float(high)) / 2


def swing(path, row, rule, motion_kind):
    """A swing about the point `hinge` names on the object's own box, open at OPENS and shut again at SHUTS."""
    speed = middle_speed(motion_kind, "angular")
    return {"name": path.rsplit("/", 1)[-1], "prim": path, "row": row, "kind": rule["kind"], "on": "rail",
            "start": 0.0, "length": ROUND, "loop": True,
            "swing": {"about": {"side": rule["hinge"]}, "angle": float(rule["angle"]), "speed": speed,
                      "starts": "shut", "moves": [[OPENS, "open"], [SHUTS, "shut"]]},
            "from": f"{rule['why']}; at {speed:g} degrees a second, the middle of the {rule['kind']} kind's cited "
                    f"range ({MOTION_KINDS})"}


def spin(path, row, rule, motion_kind):
    """A steady turn about the object's own middle, a whole number of turns a round."""
    turns = max(1, round(middle_speed(motion_kind, "angular") * ROUND / 360.0))
    speed = turns * 360.0 / ROUND
    return {"name": path.rsplit("/", 1)[-1], "prim": path, "row": row, "kind": rule["kind"], "on": "rail",
            "start": 0.0, "length": ROUND, "loop": True, "spin": {"speed": speed},
            "from": f"{rule['why']}; {turns} turns in the layer's {ROUND:g} s ({speed:g} degrees a second), the "
                    f"whole number nearest the middle of the {rule['kind']} kind's cited range ({MOTION_KINDS})"}


WRITERS = {"swing": swing, "spin": spin}


def upright(stage, path):
    """Whether an object stands upright: its own box (untransformed, metres) at least as tall as its narrower side
    across; one with no box is not judged here (the gates judge its swing)."""
    from pxr import Usd, UsdGeom
    found = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeUntransformedBound(
        stage.GetPrimAtPath(path)).ComputeAlignedRange()
    if found.IsEmpty():
        return True
    size = found.GetMax() - found.GetMin()
    return size[1] >= min(size[0], size[2])


def served(rule, inventory, kinds):
    """Whether the scene holds what a rule moves for (`needs`: a row whose kind does it); True for a rule needing
    nothing."""
    return "needs" not in rule or bool(row_kinds.rows_that(inventory, rule["needs"], kinds))


def record(place, inventory, kinds, motion_kinds, stage):
    """The scene's rigid record from its design: {place, about, seconds, moves, still, missing}."""
    moves, still, missing = [], {}, []
    for row in row_kinds.rows_that(inventory, "moves", kinds):
        rule = kinds[row["row_kind"]]["motion"]
        paths = row_kinds.objects_of(stage, place, row["id"])
        if not paths:
            missing.append(f"{row['id']} moves ({rule['move']}), and no object of it stands on the stage")
        for path in paths:
            if rule["move"] == "still":
                still[path] = rule["why"]
            elif not served(rule, inventory, kinds):
                still[path] = rule["still_without"]
            elif rule["move"] == "swing" and not upright(stage, path):
                still[path] = LYING
            else:
                moves.append(WRITERS[rule["move"]](path, row["id"], rule, motion_kinds[rule["kind"]]))
    return {"place": place,
            "about": "Made from the scene's design (score/stages/motion/from_design.py): each object of a row whose "
                     "kind moves, moved or kept standing by its kind's rule (data/checks/row-kinds.json).",
            "seconds": ROUND, "moves": moves, "still": still, "missing": missing}
