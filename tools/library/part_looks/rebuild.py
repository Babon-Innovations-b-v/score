"""Runs inside Blender (part_looks.py starts it through tools/blender/session.py batch): each job's old code builder,
as it stood at the score commit the library models were made at, built again part by part, its size fitted to the
model's box, its triangles listed part by part in the order the old join laid them, each with the face it lies in
(part_looks.py checks the model's triangles against those faces).

    blender -b --python rebuild.py -- <old builders folder> <jobs.json> <answers.json>

A job is {"name", "kind" (the builder), "laid", "box" [[low], [high]] (the model's files together, kit frame)};
{"name", "kind", "laid", "size"} to list a builder's parts alone (the map's recovery); or {"name", "kind": "*"} for
every builder's name. Its answer is {"name", "size", "shift" (the build moved onto the model's box), "box", "parts":
[[part, surface], ...], "order": [part index per built triangle, in the order the old join laid them], "polygons":
[the serial of the face each lies in], "outlines": [each face's corners, by serial], "contents": [each face's
corners' `content` texture coordinates, or None, by serial]}, {"name", "builders"}, or {"name", "error"}. Nothing is
baked or written but the answers.
"""
import json
import sys
import traceback

import bpy

FOLDER, JOBS, ANSWERS = sys.argv[sys.argv.index("--") + 1:][:3]
sys.path.insert(0, FOLDER)
import pieces  # noqa: E402  (the old builders, at the commit the models were made at)

FITS = 20  # rounds of the size fit at most
FITTED = 1e-6  # metres every corner of the built box may lie off the model's when the fit stops


def kit_point(point):
    """A Blender point in the kit frame (shapes.to_blender undone): Blender (x, y, z) is kit (x, z, -y)."""
    return (point[0], point[2], -point[1])


def part_faces(parts):
    """{(part, surface): [kit-frame triangles]} of the built parts, in the order the old join laid them (the parts'
    own, each part's faces in turn): a part's name without Blender's .001 ending, its surface the material slot each
    face names; that order, one (part, surface, polygon) a triangle, the polygon its face's serial in the join; and
    each face's outline (its corners, kit frame) by serial, and its corners' `content` texture coordinates (a printed
    plate's picture across its front, shapes.content_plate) where its part has that map, else None. How a face of
    more than three corners is cut into triangles is Blender's choice at the time (the old export cut some n-gons
    otherwise), so a triangle is told by the face it lies in, not by its own corners."""
    found, order, outlines, contents = {}, [], [], []
    for part in parts:
        name = part.name.split(".")[0]
        slots = [slot.name.split(".")[0] for slot in part.data.materials]
        matrix = part.matrix_world
        first = len(outlines)
        outlines += [[kit_point(matrix @ part.data.vertices[index].co) for index in polygon.vertices]
                     for polygon in part.data.polygons]
        content = part.data.uv_layers.get("content")
        contents += [[list(content.data[loop].uv) for loop in polygon.loop_indices] if content else None
                     for polygon in part.data.polygons]
        part.data.calc_loop_triangles()
        for triangle in part.data.loop_triangles:
            corners = [kit_point(matrix @ part.data.vertices[index].co) for index in triangle.vertices]
            key = (name, slots[triangle.material_index])
            found.setdefault(key, []).append(corners)
            order.append((key, corners, first + triangle.polygon_index))
    return found, order, outlines, contents


def built(kind, size, laid):
    """The builder's parts at `size`, in an empty scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return pieces.BUILDERS[kind](tuple(size), laid)


def box_of(faces):
    corners = [corner for triangles in faces.values() for triangle in triangles for corner in triangle]
    return ([min(corner[axis] for corner in corners) for axis in range(3)],
            [max(corner[axis] for corner in corners) for axis in range(3)])


def shifted(faces, outlines, by):
    """The built faces and outlines moved by `by` (kit frame)."""
    move = lambda corner: tuple(value + step for value, step in zip(corner, by))  # noqa: E731
    return ({key: [[move(corner) for corner in triangle] for triangle in triangles]
             for key, triangles in faces.items()},
            [[move(corner) for corner in outline] for outline in outlines])


def fitted(job):
    """(size, faces, order, outlines, contents, shift) of the builder fitted to the model's box: each side scaled by
    the box's over the built one's until every side is within FITTED, or FITS rounds, then the whole build moved so
    its box's middle is the model's (a model laid off its builder's origin: a canopy hung from its mount, a box made
    at another room's size whose sides do not follow it)."""
    (low, high) = job["box"]
    size = [high[axis] - low[axis] for axis in range(3)]
    for _ in range(FITS):
        faces, order, outlines, contents = part_faces(built(job["kind"], size, job.get("laid", {})))
        built_low, built_high = box_of(faces)
        if max(abs((built_high[axis] - built_low[axis]) - (high[axis] - low[axis])) for axis in range(3)) <= FITTED:
            break
        size = [side * (high[axis] - low[axis]) / max(built_high[axis] - built_low[axis], 1e-9)
                for axis, side in enumerate(size)]
    shift = [(low[axis] + high[axis] - built_low[axis] - built_high[axis]) / 2 for axis in range(3)]
    faces, outlines = shifted(faces, outlines, shift)
    return size, faces, order, outlines, contents, shift


def answer(job):
    if job["kind"] == "*":
        return {"name": job["name"], "builders": sorted(pieces.BUILDERS)}
    if "box" not in job:
        faces, _, _, _ = part_faces(built(job["kind"], job["size"], job.get("laid", {})))
        return {"name": job["name"], "size": job["size"], "parts": [list(key) for key in faces]}
    size, faces, order, outlines, contents, shift = fitted(job)
    keys = list(faces)
    return {"name": job["name"], "size": size, "shift": shift, "box": box_of(faces),
            "parts": [list(key) for key in keys],
            "order": [keys.index(key) for key, _, _ in order], "polygons": [polygon for _, _, polygon in order],
            "outlines": outlines, "contents": contents}


answers = []
for job in json.load(open(JOBS)):
    try:
        answers.append(answer(job))
    except Exception as failure:  # one builder's failure is that job's answer, named, never the others'
        answers.append({"name": job["name"], "error": f"{type(failure).__name__}: {failure}",
                        "trace": traceback.format_exc()[-1500:]})
    print("REBUILT", job["name"], flush=True)
json.dump(answers, open(ANSWERS, "w"))
