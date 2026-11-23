"""The moving parts and their joints of a made model against NVIDIA's (#177, #161 rules 1 and 11): how many pieces
move, which faces each one holds, and each joint's type, axis, pivot and limits.

The truth's moving parts are the bodies its revolute and prismatic joints move (of a joint's two bodies the one with
less drawn area: NVIDIA's door, not its cabinet), its fixed joints glue and are no moving part. A made face is given
its nearest truth triangle's body (`_finish.carried`), so a made part and a truth part are compared on the made
surface: their faces' area in common over their area together. Truth parts and made parts are paired one to one,
the best overlap first.
"""
import numpy as np

from . import _mesh

MOVING = {"PhysicsRevoluteJoint": "revolute", "PhysicsPrismaticJoint": "prismatic"}


def moving_bodies(truth):
    """[(joint, the body it moves, its type)] of the truth's revolute and prismatic joints."""
    areas = _mesh.areas(truth["vertices"], truth["faces"])
    body_area = np.bincount(np.asarray(truth["face_body"]) + 1, weights=areas,
                            minlength=len(truth.get("bodies") or []) + 1)
    found = []
    for joint in truth.get("joints") or []:
        if joint["type"] not in MOVING:
            continue
        ends = [end for end in (joint["body0"], joint["body1"]) if end >= 0]
        if ends:
            found.append((joint, min(ends, key=lambda end: body_area[end + 1]), MOVING[joint["type"]]))
    return found


def line_angle(one, other):
    """Degrees between two axes as lines (a hinge about -y is a hinge about +y)."""
    one, other = (np.asarray(way, dtype=float) / np.linalg.norm(way) for way in (one, other))
    return float(np.degrees(np.arccos(np.clip(abs(one @ other), 0.0, 1.0))))


def off_line(point, through, way):
    """Metres from `point` to the line through `through` along `way`."""
    way = np.asarray(way, dtype=float) / np.linalg.norm(way)
    apart = np.asarray(point, dtype=float) - np.asarray(through, dtype=float)
    return float(np.linalg.norm(apart - (apart @ way) * way))


def span(limits):
    return None if limits is None else float(limits[1] - limits[0])


def range_gap(made, truth):
    """How far the made joint's open span is off the truth's, a share of the truth's; 0 when neither is limited (a
    wheel), 1 when only one is."""
    made_span, true_span = span(made), span(truth)
    if made_span is None and true_span is None:
        return 0.0
    if made_span is None or true_span is None or true_span <= 0:
        return 1.0
    return abs(made_span - true_span) / true_span


def overlaps(truth, made, nearest, areas, moving):
    """(truth part x made part) area in common over area together on the made surface."""
    carried = np.asarray(truth["face_body"])[nearest]
    parts = np.asarray(made["face_part"])
    table = np.zeros((len(moving), len(made["joints"])))
    for row, (_, body, _) in enumerate(moving):
        held = carried == body
        for column in range(len(made["joints"])):
            mine = parts == column
            together = areas[held | mine].sum()
            table[row, column] = areas[held & mine].sum() / together if together > 0 else 0.0
    return table


def paired(table):
    """[(truth part, made part)] one to one, the best overlap first, overlaps above none only."""
    pairs, used_rows, used_columns = [], set(), set()
    for flat in np.argsort(-table, axis=None):
        row, column = np.unravel_index(flat, table.shape)
        if table[row, column] <= 0:
            break
        if row in used_rows or column in used_columns:
            continue
        pairs.append((int(row), int(column)))
        used_rows.add(row)
        used_columns.add(column)
    return pairs


def joints(truth, placed, made, nearest, matrix):
    """{"count_gap", and where the truth has moving parts "faces_least", "type_held", "axis_most", "pivot_most",
    "range_most", "joints" (each truth joint's pairing)}: `placed` the made vertices on the truth (`matrix`, the
    alignment), `made["face_part"]` each made face's moving part (an index into `made["joints"]`, -1 the still
    body), `made["joints"]` [{type revolute or prismatic, axis, pivot, limits (degrees or metres, None: free)}] in
    the made model's own frame, `nearest` each made face's truth triangle."""
    moving = moving_bodies(truth)
    found = {"count_gap": abs(len(made["joints"]) - len(moving)), "truth_moving": len(moving),
             "made_moving": len(made["joints"])}
    if not moving:
        return found
    areas = _mesh.areas(placed, np.asarray(made["faces"]))
    table = overlaps(truth, made, nearest, areas, moving)
    diagonal = _mesh.diagonal(np.asarray(truth["vertices"], dtype=float))
    rows = [{"truth": joint["prim"], "type": kind, "made": None, "faces": 0.0} for joint, _, kind in moving]
    for row, column in paired(table):
        joint, own = moving[row][0], made["joints"][column]
        axis = matrix[:3, :3] @ np.asarray(own["axis"], dtype=float)
        pivot = _mesh.moved(np.asarray(own["pivot"], dtype=float)[None], matrix)[0]
        rows[row].update(made=column, faces=round(float(table[row, column]), 4), made_type=own["type"],
                         axis=round(line_angle(axis, joint["axis"]), 3),
                         pivot=round(off_line(pivot, joint["pivot"], joint["axis"]) / diagonal, 4)
                         if rows[row]["type"] == "revolute" else 0.0,
                         range=round(range_gap(own.get("limits"), joint.get("limits")), 4))
    held = [row for row in rows if row["made"] is not None]
    found.update(joints=rows, faces_least=min(row["faces"] for row in rows),
                 type_held=round(sum(row.get("made_type") == row["type"] for row in rows) / len(rows), 4))
    if held:
        found.update(axis_most=max(row["axis"] for row in held), pivot_most=max(row["pivot"] for row in held),
                     range_most=max(row["range"] for row in held))
    return found
