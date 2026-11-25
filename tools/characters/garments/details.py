"""A garment's construction marks laid on its cloth (#225, owner 2026-11-25: clothes with no seams, stitching, hems or
pockets "look from 1950"): each mark a score_lib decal surface (fabrics.py's) on a thin mesh that follows the cloth over
the clip, a hair's breadth outside it.

An outfit garment's `details` names them:
    "seam": a surface    the mark along each seam, on the side of the panel whose name sorts first
    "seam other side"    the mark on the other panel's side (the seam's own mark when not given)
    "plain seams": [[panel, panel], ...]  seams GarmentCode cuts that a real garment has none of (a tee's centre
                         front: GarmentCode halves its torso), left bare
    "edge": a surface    the mark along each open edge (a hem, a cuff, a waistband's top)
    "neck": a surface    the mark along a neckline's edge (its points labelled right_collar / left_collar)
    "patches": [{"mark": a surface, "panel": name, "anchor": "top-centre" | "top-side" | "top-middle",
                 "across_cm": cm, "down_cm": cm}]  a patch mark (a pocket, a fly's stitching, a loop, a rivet) at its
                         library size, its middle `across_cm` towards the panel's side seam and `down_cm` down from the
                         anchor, its u towards the side seam and its v up.

A strip mark's st runs along its line (u, a unit every strip period, fabrics.STRIP_PERIOD_MM) and across it (v, 0 at
the seam or edge, 1 at its width), each taken from the fetched library entry's surface.json (`size_m`, `form`).
Every point is found on its panel's flat triangles (barycentric) and carried by them frame by frame, pushed out along
the cloth's normal past its drawn thickness. Score venv (numpy).
"""
import json
import pathlib

import numpy as np

CLEAR_M = 0.0006  # off the cloth's outer face
STEP_CM = 0.5  # a strip's points along its line
PATCH_STEP_CM = 1.0  # a patch's grid
INSIDE_CM = 0.02  # a strip's seam side laid this far inside its panel


def surfaces(garment):
    """Every library surface the garment's marks wear."""
    chosen = garment.get("details", {})
    found = [chosen[key] for key in ("seam", "seam other side", "edge", "neck") if key in chosen]
    return found + [spec["mark"] for spec in chosen.get("patches", [])]


def mark_record(library, surface):
    """The fetched library entry's surface.json (its `form` and `size_m`)."""
    kind, rest = surface["address"].split("/", 1)
    name, version = rest.split("@")
    return json.loads((pathlib.Path(library) / kind / name / version / "surface.json").read_text())


def panel_edges(record):
    """Every panel's boundary edges (copy index pairs, in its triangles' winding) and the box points' pairs they
    join: {panel: [(copy a, copy b), ...]}."""
    faces = np.asarray(record["faces"])
    panel_of = np.asarray(record["panel"])
    found = {}
    for number in np.unique(panel_of):
        own = faces[panel_of[faces[:, 0]] == number]
        sides = np.concatenate([own[:, [0, 1]], own[:, [1, 2]], own[:, [2, 0]]])
        keys = np.sort(sides, axis=1)
        unique, counts = np.unique(keys, axis=0, return_counts=True)
        once = {tuple(key) for key in unique[counts == 1]}
        found[int(number)] = [tuple(side) for side in sides if tuple(sorted(side)) in once]
    return found


def classified(record, edges):
    """Each panel's boundary edges sorted: {panel: {"seam:<other panel>": [...], "edge": [...], "neck": [...]}}, a
    seam being an edge whose two box points another panel's boundary joins too."""
    box = np.asarray(record["box"])
    owners = {}
    for panel, sides in edges.items():
        for side in sides:
            owners.setdefault(tuple(sorted((box[side[0]], box[side[1]]))), set()).add(panel)
    collar = set()
    for label in ("right_collar", "left_collar"):
        if f"label/{label}" in record:
            collar |= {int(point) for point in record[f"label/{label}"]}
    found = {}
    for panel, sides in edges.items():
        sorted_sides = found.setdefault(panel, {})
        for side in sides:
            key = tuple(sorted((box[side[0]], box[side[1]])))
            others = owners[key] - {panel}
            if others:
                group = f"seam:{min(others)}"
            elif key[0] in collar and key[1] in collar:
                group = "neck"
            else:
                group = "edge"
            sorted_sides.setdefault(group, []).append(side)
    return found


def chained(sides):
    """Edges (a, b) joined into polylines of copy indices, each along the edges' own direction."""
    following = {side[0]: side[1] for side in sides}
    starts = set(following) - set(following.values())
    lines, seen = [], set()
    for start in list(starts) + list(following):
        if start in seen or start not in following:
            continue
        line = [start]
        seen.add(start)
        while line[-1] in following and following[line[-1]] not in seen:
            line.append(following[line[-1]])
            seen.add(line[-1])
        if line[-1] in following and following[line[-1]] == start:
            line.append(start)
        if len(line) > 1:
            lines.append(line)
    return lines


def resampled(line_cm, step):
    """A polyline's points every `step` cm (its ends kept); and each point's distance along it."""
    line_cm = np.asarray(line_cm, float)
    lengths = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(line_cm, axis=0), axis=1))]
    along = np.linspace(0.0, lengths[-1], max(int(np.ceil(lengths[-1] / step)) + 1, 2))
    return np.stack([np.interp(along, lengths, line_cm[:, axis]) for axis in (0, 1)], axis=1), along


def located(record, panel, flat_points):
    """Each flat point (cm) on its panel's triangles: (triangle's box points, barycentric weights); a point off the
    panel takes its nearest triangle's weights, carried past its edge."""
    faces = np.asarray(record["faces"])
    faces = faces[np.asarray(record["panel"])[faces[:, 0]] == panel]
    flat = np.asarray(record["flat"], float)
    first, second, third = flat[faces[:, 0]], flat[faces[:, 1]], flat[faces[:, 2]]
    middles = (first + second + third) / 3.0
    span_b, span_c = second - first, third - first
    determinant = span_b[:, 0] * span_c[:, 1] - span_b[:, 1] * span_c[:, 0]
    corners, weights = [], []
    for point in np.asarray(flat_points, float):
        offset = point - first
        weight_b = (offset[:, 0] * span_c[:, 1] - offset[:, 1] * span_c[:, 0]) / determinant
        weight_c = (span_b[:, 0] * offset[:, 1] - span_b[:, 1] * offset[:, 0]) / determinant
        weight_a = 1.0 - weight_b - weight_c
        outside = -np.minimum(np.minimum(weight_a, weight_b), weight_c)
        inside = np.flatnonzero(outside <= 1e-9)
        best = inside[0] if len(inside) else int(np.argmin(np.linalg.norm(middles - point, axis=1)))
        corners.append(np.asarray(record["box"])[faces[best]])
        weights.append([weight_a[best], weight_b[best], weight_c[best]])
    return np.asarray(corners), np.asarray(weights)


def inward(record, panel, line_cm):
    """Each point's unit normal in the flat panel, turned to point into the panel (a probe off the line's middle)."""
    tangent = np.gradient(line_cm, axis=0)
    tangent /= np.maximum(np.linalg.norm(tangent, axis=1, keepdims=True), 1e-9)
    normal = np.stack([-tangent[:, 1], tangent[:, 0]], axis=1)
    middle = len(line_cm) // 2
    weights = located(record, panel, [line_cm[middle] + normal[middle] * 0.3])[1]
    return normal if weights.min() >= -1e-6 else -normal


def strip(record, panel, copies, size_m, period_m):
    """A strip mark along a line of copies: its flat points (two rows: on the line and its width in), quads and st."""
    flat = np.asarray(record["flat"], float)
    line, along = resampled(flat[copies], STEP_CM)
    normal = inward(record, panel, line)
    width_cm = size_m[1] * 100.0
    points = np.concatenate([line + normal * INSIDE_CM, line + normal * width_cm])
    count = len(line)
    quads = [[index, index + 1, count + index + 1, count + index] for index in range(count - 1)]
    st = np.concatenate([np.stack([along / (period_m * 100.0), np.zeros(count)], axis=1),
                         np.stack([along / (period_m * 100.0), np.ones(count)], axis=1)])
    return points, np.asarray(quads), st


def panel_axes(record, panel):
    """A panel's flat directions (unit, cm space) of up (the body's y) and towards its side (away from the body's
    middle in x), from its flat points and where they are laid round the body."""
    chosen = np.asarray(record["panel"]) == panel
    flat = np.asarray(record["flat"], float)[chosen]
    laid = np.asarray(record["copies"], float)[chosen]
    design = np.c_[flat, np.ones(len(flat))]
    solved = np.linalg.lstsq(design, laid, rcond=None)[0][:2]  # flat (x, y) -> world, per axis
    up = solved[:, 1] / np.linalg.norm(solved[:, 1])
    side_sign = np.sign(laid[:, 0].mean()) or 1.0
    side = solved[:, 0] * side_sign
    side = side - up * np.dot(side, up)
    return up, side / np.linalg.norm(side)


def anchor_point(record, panel, anchor, up, side):
    """The panel's anchor in its flat points: its top's inner corner, outer corner or middle."""
    flat = np.asarray(record["flat"], float)[np.asarray(record["panel"]) == panel]
    height, across = flat @ up, flat @ side
    if anchor == "top-middle":
        middle = (across.min() + across.max()) / 2.0
        near = np.abs(across - middle) < 2.0
        best = np.flatnonzero(near)[np.argmax(height[near])]
        return flat[best]
    weight = -1.0 if anchor == "top-centre" else 1.0
    return flat[np.argmax(height + weight * across)]


def patch(record, panel_names, spec, size_m):
    """A patch mark's flat points, quads and st, and its panel's number."""
    panel = [str(name) for name in panel_names].index(spec["panel"])
    up, side = panel_axes(record, panel)
    centre = (anchor_point(record, panel, spec["anchor"], up, side) + side * spec["across_cm"]
              - up * spec["down_cm"])
    width, height = size_m[0] * 100.0, size_m[1] * 100.0
    columns = max(int(np.ceil(width / PATCH_STEP_CM)) + 1, 2)
    rows = max(int(np.ceil(height / PATCH_STEP_CM)) + 1, 2)
    u_values, v_values = np.meshgrid(np.linspace(0.0, 1.0, columns), np.linspace(0.0, 1.0, rows), indexing="xy")
    st = np.stack([u_values.ravel(), v_values.ravel()], axis=1)
    points = centre + np.outer(st[:, 0] - 0.5, side * width) + np.outer(st[:, 1] - 0.5, up * height)
    quads = [[row * columns + column, row * columns + column + 1, (row + 1) * columns + column + 1,
              (row + 1) * columns + column] for row in range(rows - 1) for column in range(columns - 1)]
    return panel, points, np.asarray(quads), st


def vertex_normals(points, faces):
    """Area-weighted unit normals of a mesh's points (frames x points x 3)."""
    corners = points[:, faces]
    face_normals = np.cross(corners[:, :, 1] - corners[:, :, 0], corners[:, :, 2] - corners[:, :, 0])
    normals = np.zeros_like(points)
    for corner in range(3):
        np.add.at(normals, (slice(None), faces[:, corner]), face_normals)
    return normals / np.maximum(np.linalg.norm(normals, axis=-1, keepdims=True), 1e-12)


def outward_sign(points, normals, body_points):
    """+1 when the cloth's normals point away from the body (most points), else -1."""
    from scipy.spatial import cKDTree
    nearest = cKDTree(body_points).query(points)[1]
    return 1.0 if np.mean(np.einsum("ij,ij->i", normals, points - body_points[nearest]) > 0.0) > 0.5 else -1.0


def pieces(record, garment, library):
    """Every mark of the garment: [(surface, panel, flat points, quads, st)]."""
    details = garment.get("details", {})
    if not details:
        return []
    names = [str(name) for name in record["panel_names"]]
    plain = {tuple(sorted((names.index(first), names.index(second))))
             for first, second in details.get("plain seams", [])}
    found = []
    for panel, groups in classified(record, panel_edges(record)).items():
        for group, sides in groups.items():
            if group.startswith("seam:"):
                other = int(group.split(":")[1])
                if tuple(sorted((panel, other))) in plain:
                    continue
                first = min(names[panel], names[other]) == names[panel]
                surface = details["seam"] if first else details.get("seam other side", details["seam"])
            elif group in details:
                surface = details[group]
            else:
                continue
            mark = mark_record(library, surface)
            for line in chained(sides):
                found.append((surface, panel, *strip(record, panel, line, mark["size_m"],
                                                       mark["size_m"][0])))
    for spec in details.get("patches", []):
        mark = mark_record(library, spec["mark"])
        panel, points, quads, st = patch(record, names, spec, mark["size_m"])
        found.append((spec["mark"], panel, points, quads, st))
    return found


def laid(record, garment, library, frames, body_points, thickness_m):
    """The garment's marks as one mesh over its frames: (points per frame, triangles, st per corner, each triangle's
    surface index, the surfaces); None when it has none."""
    made = pieces(record, garment, library)
    if not made:
        return None
    faces = np.asarray(record["box"])[np.asarray(record["faces"])]
    frames = np.asarray(frames, float)
    normals = vertex_normals(frames, faces)
    sign = outward_sign(frames[0], normals[0], np.asarray(body_points, float))
    lift = CLEAR_M + (thickness_m if sign > 0 else 0.0)  # a solidified cloth grows along its normals
    surfaces, triangles, corners_st, finish, all_points = [], [], [], [], []
    offset = 0
    for surface, panel, flat_points, quads, st in made:
        if surface["name"] not in [known["name"] for known in surfaces]:
            surfaces.append(surface)
        index = [known["name"] for known in surfaces].index(surface["name"])
        box_points, weights = located(record, panel, flat_points)
        carried = np.einsum("fpcx,pc->fpx", frames[:, box_points], weights)
        normal = np.einsum("fpcx,pc->fpx", normals[:, box_points], weights)
        normal /= np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-12)
        all_points.append(carried + normal * sign * lift)
        for quad in quads:
            for triangle in ((quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])):
                triangles.append([offset + corner for corner in triangle])
                corners_st.append(st[list(triangle)])
                finish.append(index)
        offset += len(flat_points)
    return (np.concatenate(all_points, axis=1), np.asarray(triangles), np.asarray(corners_st), np.asarray(finish),
            surfaces)
