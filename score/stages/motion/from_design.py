"""A scene's rigid moves made from its design, never written by hand (the owner, 2026-10-21: "the modules are not
agnostic"): every object of a scene inventory row whose kind moves (score/stages/row_kinds.py) moves as its kind's
rule says (data/checks/row-kinds.json `motion`), at the speed its motion kind's cited range gives
(data/checks/motion.json), or stands with the rule's reason. The rules, each general:

    swing   a leaf turned about the upright line through a point on its own box (`hinge`: from the box's middle, each
            axis a share of its half size; a door's left edge, a crane's own middle) `angle` degrees open and shut
            again once a round, at the middle of its kind's cited turning speeds
    slide   shifted along its own box, at the middle of its kind's cited speeds and back: `along` "long" its own
            width along its longer level side (a sliding door), "up" its own height (a garage door rising), "short"
            across its span as far as half a round less two seconds carries it (a bridge crane on its runway)
    spin    turned steadily about its own middle at the whole number of turns a round nearest the middle of its
            kind's cited speeds, so the layer loops
    still   standing, with the rule's reason
    lying   a swing turns about an upright line, so only a thing standing upright swings: one whose own box is lower
            than it is wide both ways (a hatch in a floor, a crane spanning a hall on its rails) stands, with LYING
    needs   "passes": a rule that moves only for a walker of the scene's accepted cast whose route (the cast's path,
            else its walk the way it faces: scene_clips.legs_of) comes within NEAR of the object at rest, its moves
            timed off each crossing: open by when the walker comes that near, shut once it is that far past, played
            once (no loop), so a door opens for who walks through it and for nobody else; with no such walker (or no
            person in the design at all: served) it stands with `still_without`
    words   the row's own words choose its rule (rule_of): its kind's first `variants` entry whose words its name
            holds (a sliding door slides, a garage door rises, a double door splits), and one of `open_words` stands
            it open (posed: written open and still), never swung shut from a shut start
    unmade  a move no writer makes (a rocket's launch, a flag's cloth, a double door's two leaves): named in the
            record's `unmade`, which the motion row's `covered` fails, never written down as a still

    record(place, inventory, kinds, motion_kinds, stage, carried)   the rigid record tools/usd/motion_layer.py writes
    plan_gaps(plan)     the accepted plan's `placed` gaps as gaps a moving row with no object is left out by
    left_gaps(record)   the batch gap of each moving row a carried batch gap or a plan gap left with no object
"""
import math

import numpy as np

from score.stages import batch_gaps, row_kinds

# One round of the layer, seconds, and when in it a swinging thing opens and shuts again.
ROUND = 20.0
OPENS, SHUTS = 2.0, 10.0
MOTION_KINDS = "data/checks/motion.json"
# Where the source fix of a row the accepted plan places too few of waits (hangar's floor hatch, 2026-10-29).
PLAN_FIX = "parked on #36, https://github.com/Babon-Innovations-b-v/score/issues/36#issuecomment-6507732319"
# A walker passes through a door when its route comes this near the door's box at rest, metres (its doorway).
NEAR = 1.0
# What a rule's `needs` asks of the design before any cast is read (served): a walker needs a person.
NEEDS = {"passes": "acts"}
# How often a walker's route is read for its crossings, seconds.
READ_STEP = 0.1
LYING = ("it lies lower than it is wide both ways (its own box), so it would turn about a level line or travel on "
         "rails, never about the upright line a swing turns on: it stands as the plan lays it")


def middle_speed(rule, measure):
    """The middle of a motion kind's cited speed range (`angular` degrees or `linear` metres a second)."""
    low, high = rule[measure]
    return (float(low) + float(high)) / 2


def timed(rule, travel, spans):
    """(moves, length, loop, why) of a rule: for a walker's crossings (`spans`, needs "passes") each opened by its
    start and shut at its end, played once over a length of whole rounds; else open at OPENS and shut at SHUTS
    every round (a gantry: open from 0 and shut at half the round)."""
    if spans is None:
        times = [[0.0, "open"], [ROUND / 2, "shut"]] if rule.get("along") == "short" else \
            [[OPENS, "open"], [SHUTS, "shut"]]
        return times, ROUND, True, ""
    moves = passing_moves(spans, travel)
    length = ROUND * max(1, math.ceil((moves[-1][0] + travel) / ROUND - 1e-9))
    said = ", ".join(f"{enter:.1f} to {leave:.1f} s" for enter, leave in spans)
    return moves, length, False, f"; opened for who walks through it (within {NEAR:g} m of it at {said})"


def passing_moves(spans, travel):
    """The open and shut moments of a crossing's spans [(enter, leave)]: open `travel` before each is entered (not
    before the last shut has ended, nor before 0), shut once it is left (not before it is all the way open)."""
    moves, free = [], 0.0
    for enter, leave in spans:
        opens = max(free, enter - travel)
        shuts = max(leave, opens + travel)
        moves += [[round(opens, 3), "open"], [round(shuts, 3), "shut"]]
        free = shuts + travel
    return moves


def merged(spans, travel):
    """Crossing spans joined where the thing could not shut and open again between them."""
    joined = []
    for enter, leave in sorted(spans):
        if joined and enter - travel < joined[-1][1] + travel:
            joined[-1] = (joined[-1][0], max(joined[-1][1], leave))
        else:
            joined.append((enter, leave))
    return joined


def swing(path, row, rule, motion_kind, stage=None, spans=None, posed=False):
    """A swing about the point `hinge` names on the object's own box: open at OPENS and shut again at SHUTS, or for
    each crossing (timed); posed, written open and still."""
    speed = middle_speed(motion_kind, "angular")
    angle = float(rule["angle"])
    moves, length, loop, why = timed(rule, angle / speed, spans) if not posed else ([], ROUND, False, "")
    return {"name": path.rsplit("/", 1)[-1], "prim": path, "row": row, "kind": rule["kind"], "on": "rail",
            "start": 0.0, "length": length, "loop": loop,
            "swing": {"about": {"side": rule["hinge"]}, "angle": angle, "speed": speed,
                      "starts": "open" if posed else "shut", "moves": moves},
            "from": f"{rule['why']}{why}; at {speed:g} degrees a second, the middle of the {rule['kind']} kind's "
                    f"cited range ({MOTION_KINDS})"}


def own_frame(stage, path):
    """(the object's own box size, its own axes in its parent's frame as rows) where the base stands it."""
    from pxr import Usd, UsdGeom
    prim = stage.GetPrimAtPath(path)
    found = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeUntransformedBound(
        prim).ComputeAlignedRange()
    size = np.zeros(3) if found.IsEmpty() else np.asarray(found.GetMax() - found.GetMin(), dtype=float)
    local = np.asarray(UsdGeom.Xformable(prim).GetLocalTransformation(Usd.TimeCode.Default()), dtype=float)
    return size, local[:3, :3]


def slide_by(rule, motion_kind, stage, path):
    """How far and which way a slide shifts the object, in its parent's frame (module docstring, slide)."""
    size, axes = own_frame(stage, path)
    if rule["along"] == "up":
        return axes[1] * size[1]
    longer = 0 if size[0] >= size[2] else 2
    level = longer if rule["along"] == "long" else 2 - longer
    scale = max(float(np.linalg.norm(axes[level])), 1e-12)
    reach = size[level] * scale if rule["along"] == "long" else \
        middle_speed(motion_kind, "linear") * (ROUND / 2 - 2.0)
    return axes[level] / scale * reach


def slide(path, row, rule, motion_kind, stage=None, spans=None, posed=False):
    """A slide along the object's own box (slide_by) and back, timed as a swing is."""
    speed = middle_speed(motion_kind, "linear")
    by = slide_by(rule, motion_kind, stage, path)
    moves, length, loop, why = timed(rule, float(np.linalg.norm(by)) / speed, spans) if not posed else \
        ([], ROUND, False, "")
    return {"name": path.rsplit("/", 1)[-1], "prim": path, "row": row, "kind": rule["kind"], "on": "rail",
            "start": 0.0, "length": length, "loop": loop,
            "slide": {"by": [round(float(value), 5) for value in by], "speed": speed,
                      "starts": "open" if posed else "shut", "moves": moves},
            "from": f"{rule['why']}{why}; at {speed:g} metres a second, the middle of the {rule['kind']} kind's "
                    f"cited range ({MOTION_KINDS})"}


def spin(path, row, rule, motion_kind, stage=None, spans=None, posed=False):
    """A steady turn about the object's own middle, a whole number of turns a round."""
    turns = max(1, round(middle_speed(motion_kind, "angular") * ROUND / 360.0))
    speed = turns * 360.0 / ROUND
    return {"name": path.rsplit("/", 1)[-1], "prim": path, "row": row, "kind": rule["kind"], "on": "rail",
            "start": 0.0, "length": ROUND, "loop": True, "spin": {"speed": speed},
            "from": f"{rule['why']}; {turns} turns in the layer's {ROUND:g} s ({speed:g} degrees a second), the "
                    f"whole number nearest the middle of the {rule['kind']} kind's cited range ({MOTION_KINDS})"}


WRITERS = {"swing": swing, "spin": spin, "slide": slide}


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
    """Whether the scene's design holds what a rule moves for (`needs`, as NEEDS asks it of the design: a walker
    needs a person), before any cast is read; True for a rule needing nothing."""
    return "needs" not in rule or bool(row_kinds.rows_that(inventory, NEEDS.get(rule["needs"], rule["needs"]),
                                                           kinds))


def rule_of(row, kinds):
    """A row's motion rule as its own words choose it (module docstring, words): its kind's rule with the first
    variant whose words its name holds over it, and `rests` "open" where its name holds one of the rule's
    open words."""
    base = kinds[row["row_kind"]]["motion"]
    said = set(row_kinds.words(row.get("name") or row.get("id")).split())
    variant = next((entry["motion"] for entry in kinds[row["row_kind"]].get("variants", [])
                    if said & set(entry["words"])), {})
    rule = {**base, **variant}
    return dict(rule, rests="open") if said & set(base.get("open_words", ())) else rule


def routes(cast):
    """Each walker of an accepted cast record (cast.json) as (name, seconds, [x, z] points read every READ_STEP):
    its path, else its walk the way it faces (scene_clips.legs_of), walked from the start at its pace."""
    from score.stages import scene_clips
    found = []
    for single in (cast or {}).get("characters", []):
        if not single.get("path") and single.get("doing") != scene_clips.CLIP:
            continue
        points = np.asarray(scene_clips.legs_of(single), dtype=float)[:, [0, 2]]
        along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))])
        pace = float(single.get("pace", scene_clips.WALK_PACE))
        seconds = np.arange(0.0, along[-1] / pace + READ_STEP, READ_STEP)
        spots = np.column_stack([np.interp(seconds * pace, along, points[:, axis]) for axis in (0, 1)])
        found.append((single["name"], seconds, spots))
    return found


def footprint(stage, path):
    """(low, high) [x, z] of the object's world box at rest; its own spot for one that draws nothing yet."""
    from pxr import Usd, UsdGeom
    prim = stage.GetPrimAtPath(path)
    found = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(
        prim).ComputeAlignedRange()
    if found.IsEmpty():
        spot = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
                          .ExtractTranslation(), dtype=float)[[0, 2]]
        return spot, spot
    return np.asarray(found.GetMin(), dtype=float)[[0, 2]], np.asarray(found.GetMax(), dtype=float)[[0, 2]]


def near_spans(low, high, walked):
    """The spans [(enter, leave)] seconds a walker's spots stand within NEAR of a footprint."""
    seconds, spots = walked
    apart = np.linalg.norm(np.maximum(0.0, np.maximum(low - spots, spots - high)), axis=1)
    inside = apart <= NEAR
    spans, start = [], None
    for index, flag in enumerate(inside):
        if flag and start is None:
            start = index
        if start is not None and (not flag or index == len(inside) - 1):
            spans.append((float(seconds[start]), float(seconds[index if flag else index - 1])))
            start = None
    return spans


def crossings(stage, path, walkers):
    """Every span any walker stands within NEAR of the object at rest, in time order."""
    low, high = footprint(stage, path)
    return sorted(span for _, *walked in walkers for span in near_spans(low, high, walked))


def gaps_naming(row, carried):
    """The names of the carried batch gaps (score/stages/batch_gaps.py) naming a row: by its id or its take (the
    row's `thing`, "prop:<take>": the bake's gap names the take only)."""
    names = {row["id"], str(row.get("thing", "")).split(":", 1)[-1]}
    return [entry["name"] for entry in carried if names & set(entry["objects"])]


def record(place, inventory, kinds, motion_kinds, stage, carried=(), cast=None):
    """The scene's rigid record from its design and its accepted cast (cast.json, None for a scene with no people):
    {place, about, seconds, moves, posed, still, unmade, missing, left_out}; a moving row with no object is missing,
    and left out ({row: [gap names]}) where a carried batch gap names it."""
    moves, posed, still, unmade, missing, left_out = [], [], {}, [], [], {}
    walkers = routes(cast)
    for row in row_kinds.rows_that(inventory, "moves", kinds):
        rule = rule_of(row, kinds)
        paths = row_kinds.objects_of(stage, place, row["id"])
        if not paths:
            missing.append(f"{row['id']}: moves ({rule['move']}), and no object of it stands on the stage")
            if gaps_naming(row, carried):
                left_out[row["id"]] = gaps_naming(row, carried)
        for path in paths:
            made = WRITERS.get(rule["move"])
            spans = crossings(stage, path, walkers) if rule.get("needs") == "passes" else None
            if rule["move"] == "still":
                still[path] = rule["why"]
            elif rule["move"] == "swing" and not upright(stage, path):
                still[path] = LYING
            elif rule.get("rests") == "open" and made:
                posed.append(made(path, row["id"], rule, motion_kinds[rule["kind"]], stage, posed=True))
                still[path] = f"it stands open, as its row's words say (\"{row.get('name')}\")"
            elif not served(rule, inventory, kinds) or spans == []:
                still[path] = rule["still_without"]
            elif made is None:
                unmade.append(f"{path}: {rule['move']}, which no writer makes: {rule['why']}")
            else:
                moves.append(made(path, row["id"], rule, motion_kinds[rule["kind"]], stage,
                                  spans=None if spans is None else merged_for(rule, motion_kinds, stage, path, spans)))
    return {"place": place,
            "about": "Made from the scene's design (score/stages/motion/from_design.py): each object of a row whose "
                     "kind moves, moved or kept standing by its kind's rule as the row's words choose it "
                     "(data/checks/row-kinds.json), a door opened only for a walker of the cast passing through.",
            "seconds": max([ROUND, *(float(move["length"]) for move in moves)]), "moves": moves, "posed": posed,
            "still": still, "unmade": unmade, "missing": missing, "left_out": left_out}


def merged_for(rule, motion_kinds, stage, path, spans):
    """A thing's crossing spans joined where its own travel could not shut and open it again between them."""
    kind = motion_kinds[rule["kind"]]
    travel = float(rule["angle"]) / middle_speed(kind, "angular") if rule["move"] == "swing" else \
        float(np.linalg.norm(slide_by(rule, kind, stage, path))) / middle_speed(kind, "linear")
    return merged(spans, travel)


def plan_gaps(plan):
    """The accepted plan's `placed` gaps (a row it places another number of times than the concept shows) as the
    carried gaps `record` reads: a moving row with no object that one names is left out by it, by name, never failed
    as a model that is not there (hangar's floor hatch: "1 in the concept, 0 on the plan", its row read with no box,
    2026-10-29). The gap names where its source fix waits, never the answer."""
    return [{"name": f"{gap['row']}: the accepted plan's gap \"{gap['words']}\" (its source fix: {PLAN_FIX})",
             "objects": [gap["row"]]} for gap in plan.get("gaps", []) if gap.get("kind") == "placed" and gap.get("row")]


def left_gaps(record):
    """The batch gap of each moving row left out: a paid step of its take failed in the batch, or the accepted plan
    places none of it (plan_gaps), so nothing of it moves; named by the row, so the table moves `designed`'s fault on
    it (stages.BATCH_GATES)."""
    return [batch_gaps.gap(f"{row}: no object, so it does not move", "motion", "designed", (row,),
                           [f"{row}: no object of it stands on the stage ({'; '.join(names)})"],
                           "a gap its fault names left it with no object (its take left out inside the batch, or "
                           "none of it on the accepted plan), so nothing of it moves")
            for row, names in sorted(record["left_out"].items())]
