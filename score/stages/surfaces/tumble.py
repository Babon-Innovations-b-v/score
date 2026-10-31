"""Whether a take stands square in its model frame (#36, 2026-10-29: 154 of env1's 406 baked models stood tumbled, base's
square module rolled 32 degrees, camp's bunk bed 44), and the turn that stands it square. Free, numpy and trimesh, in
the prop environment: the bake stands a take square before it is laid (route_bake.stood_square) and surfaces-check's
`stands square` fails one that still is not (bake_check.judge_square). Its own module, so the two rows that read it
hash only this.

    measure(points)                 (degrees off, looseness): its oriented box's axes against the frame's
    rules_of(inputs)                the pose rules a row's kept pose is read by (stance.json, resting.json)
    keeps_pose(row, rules, rows, built)  why a row keeps the pose it was made in, or None: the one guard list
    square_turn(points, size, keep_up)  the turn standing a tumbled take square, its box's proportions the row's

A take is tumbled when its oriented box (of its convex hull) is turned more than DEGREES off the frame (the axis
nearest up off up, or its long plan axis off the frame's, mod 90, for one not round in plan) and its frame-aligned
box is more than LOOSE times its own: a round or irregular thing whose box turns freely is never called tumbled.
The one guard list (keeps_pose), read by the bake's stand-square (route_bake.stood_square), its SAM-box width rule
(bake_job.boxed, likeness_row.drawn_size) and surfaces-check's `stands square`, decided by row kind, anchor and words,
never by an object's name: a person (a row of the people route: its pose and its width are its take's own; cockpit
pilot_1, seated, its picture box holding the chair, was widened 0.5 to 1.205 m, 2026-10-29), a row whose design lays
it leaning (`leans`) or lying (stance.json's lying classes: torn wreckage, a thing on its side), a hanging row (the
resting rules' hanging words in its id or name, or its anchor the ceiling: garage's ceiling lamp, `on:ceiling_beam`,
was turned 50 degrees) and a row with no up (the resting rules' ground debris and cable: rocks, rubble, a pile, a limp
cable, which rest as they were made; hangar's floor cables were turned 31 degrees), and a code build (its take's
code.json route "code", bake_job.code_built: the thin straight route makes it in its own pose and leans it by the
close-up's look-down, thin_straight.facing; the bake turned quarters' string lights 34 degrees off that lean, outline
0.544 to 0.101, #36 2026-10-30).
"""
import itertools
import json
import math
import pathlib
import re

import numpy as np

DEGREES = 10.0
LOOSE = 1.25
ROUND_PLAN = 0.92  # a plan this near square (its oriented box's two plan sides) is round: its yaw is not read
NO_UP = ("ground debris", "cable")  # the resting rules' classes with no up: rubble and limp cable rest as made
PEOPLE = "people"  # the route of a designed person's row
PERSON = "a person: its pose and its width for its height are its take's own"
CODE_BUILD = "a code build: it stands as its code made it"
CEILING, CEILING_GROUP = "ceiling", "kit: ceiling"  # an anchor at the ceiling: the word, or a holder of that group


def oriented(points):
    """(axes as columns, extents) of the oriented box of the points' convex hull."""
    import trimesh
    hull = trimesh.PointCloud(np.asarray(points, float)).convex_hull
    box = hull.bounding_box_oriented
    return box.primitive.transform[:3, :3], np.asarray(box.primitive.extents, float), hull


def measure(points):
    """(degrees its oriented box stands off the frame, its frame-aligned box's volume over its oriented box's)."""
    axes, extents, hull = oriented(points)
    up = int(np.argmax(np.abs(axes[1, :])))
    tilt = math.degrees(math.acos(min(1.0, abs(float(axes[1, up])))))
    plan = [axis for axis in range(3) if axis != up]
    yaw = 0.0
    if min(extents[plan]) / max(extents[plan]) <= ROUND_PLAN:
        way = axes[[0, 2], plan[int(np.argmax(extents[plan]))]]
        yaw = math.degrees(math.atan2(way[1], way[0])) % 90
        yaw = min(yaw, 90 - yaw)
    loose = float(np.prod(hull.extents)) / max(float(np.prod(extents)), 1e-12)
    return round(max(tilt, yaw), 2), round(loose, 3)


def tumbled(points):
    degrees, loose = measure(points)
    return degrees > DEGREES and loose > LOOSE


def words_of(row):
    return set(re.findall(r"[a-z]+", f"{row.get('id', '')} {row.get('name', '')}".replace("_", " ").lower()))


def rules_of(inputs):
    """{"lying": stance.json's lying words (phrases too), "hanging": the resting rules' hanging words, "no_up": the
    resting rules' words of a class with no up (NO_UP)}, from a row's inputs "stance rules" and "resting rules"
    (paths), each empty where its file is not an input."""
    stance = json.loads(pathlib.Path(inputs["stance rules"]).read_text()) if "stance rules" in inputs else {}
    resting = json.loads(pathlib.Path(inputs["resting rules"]).read_text()) if "resting rules" in inputs else {}
    return {"lying": [word for kind in stance.get("lies", []) for word in kind["words"]],
            "hanging": list(resting.get("hanging", [])),
            "no_up": [word for bedding in resting.get("may_bed", []) if bedding["class"] in NO_UP
                      for word in bedding["words"]]}


def take_row(take, model, rows):
    """The hand-in row the take makes (its `thing` "prop:<take>"), else the row its model is named for, else {}: the
    row the guard list reads for a baked model, in the bake and in its check alike."""
    return next((row for row in rows if row.get("thing") == f"prop:{take}"),
                next((row for row in rows if row.get("id") == model.removesuffix("_1")), {}))


def person(row):
    """Whether a row is a person: its route the people line's."""
    return row.get("route") == PEOPLE


def hangs(row, hanging, rows=()):
    """What a row hangs by, or None: the resting rules' `hanging` words in its id or name, or its anchor at the
    ceiling (CEILING a word of it, or the row it is `on:` of group CEILING_GROUP among `rows`)."""
    said = sorted(words_of(row) & set(hanging))
    if said:
        return ", ".join(said)
    anchor = str(row.get("anchor") or "")
    holder = {found.get("id"): found for found in rows}.get(anchor.removeprefix("on:"), {})
    if CEILING in re.findall(r"[a-z]+", anchor.replace("_", " ").lower()) or holder.get("group") == CEILING_GROUP:
        return f"anchored {anchor}"
    return None


def keeps_pose(row, rules, rows=(), built=False):
    """Why the row keeps the pose it was made in, or None (the module docstring's guard list): a person, its take a
    code build (`built`), its design laying it leaning or lying, hanging, or with no up. `rules`: rules_of's; `rows`:
    its inventory's, naming what an `on:` anchor holds it to."""
    text = f"{row.get('id', '')} {row.get('name', '')}".replace("_", " ").lower()
    if person(row):
        return PERSON
    if built:
        return CODE_BUILD
    if row.get("leans"):
        return "its design lays it leaning"
    said = next((word for word in rules["lying"] if (" " in word and word in text) or word in words_of(row)), None)
    if said:
        return f"its design lays it lying ({said})"
    hung = hangs(row, rules["hanging"], rows)
    if hung:
        return f"it hangs ({hung}): it hangs as it was made"
    natural = sorted(words_of(row) & set(rules["no_up"]))
    if natural:
        return f"no up ({', '.join(natural)}): it rests as it was made"
    return None


def square_turn(points, size, keep_up=True):
    """The turn (rows, the frame's) that stands points square: their oriented box's axis nearest up set up (the take
    stands as the finish stood it, only its tilt taken off), and of the two ways to set the other two on the frame's
    plan axes, the one whose box best keeps the row's `size` proportions (x wide, y tall, z deep: |log| misfits, as
    bake_job.measured_turn weighs a footprint), the least turn on a tie. The row's proportions never choose its up:
    a row drawn flatter than its take laid it on its back (workshop's desk_front_right, its row 1.5 x 1.0 x 0.8 for an
    L desk 0.71 x 0.42 x 0.61, #36 2026-10-30). With `keep_up` False the proportions choose its up too, of every way to
    set the box's axes on the frame's: a standing take laid down along its lying row (bake_job.measured_turn)."""
    axes, extents, _ = oriented(points)
    wide, tall, deep = (max(float(side), 1e-6) for side in size)
    up = int(np.argmax(np.abs(axes[1, :])))
    best = None
    for order in (order for order in itertools.permutations(range(3)) if order[1] == up or not keep_up):
        rows = []
        for frame_axis, box_axis in enumerate(order):
            way = axes[:, box_axis]
            rows.append(way if way[frame_axis] >= 0 else -way)  # each box axis the way its frame axis points
        turn = np.array(rows)
        if np.linalg.det(turn) < 0:
            turn[2] = -turn[2]
        ex, ey, ez = (extents[box_axis] for box_axis in order)
        misfit = abs(math.log(ex / ey) - math.log(wide / tall)) + abs(math.log(ez / ey) - math.log(deep / tall))
        angle = math.degrees(math.acos(max(-1.0, min(1.0, (float(np.trace(turn)) - 1) / 2))))
        score = (round(misfit, 6), angle)
        if best is None or score < best[0]:
            best = (score, turn)
    return best[1]
