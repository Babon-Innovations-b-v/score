"""Strand hair grown on a kept person's scalp, in Blender (#227, PRD #223): the first hair slice.

    blender -b --python groom.py -- --body <kept dressed body.glb> --dress <its dress.json> \
        --style data/people/hair/<look>.json --library <the people line's surface specs json> --out <folder> \
        [--clip walking --frames 0,7,14,21]

- **The scalp is the made hair.** The kept body (score_lib's dressed person) is one mesh whose head is the hair the
  look was made with, a shell: its hair part's surfaces not painted skin (`hair_materials`, read off the dress record),
  the piece of them joined to the top of the head (`shell_faces`).
- **Guides are combed over that shell** (`guides`): roots on its upper part, each strand stepped down the shell from
  the style's parting (`data/people/hair/<look>.json`, read from the look's close-up), drawn towards gravity as it
  falls, a front strand swept to the fringe's side, ending where the shell ends; each lies a few millimetres off it
  in layers, with the style's wave.
- **Geometry Nodes grow the rest and bind them** (`grown`): children distributed on the scalp at its rest shape,
  shaped by Interpolate Curves from their nearest guides, every strand carrying its root's place in the body's UV
  (`surface_uv_coordinate`), then Deform Curves on Surface, which moves each strand with its root's triangle through
  the armature and the corrective shapes, and a radius tapered from root to tip.
- **The finish is the library's** (`finished`): Cycles' Principled Hair BSDF in direct colouring, its colour the
  library surface the style names (the people line's `hair_brown` family); the shell under the strands wears that
  surface's own colour and roughness. score_lib holds no hair recipe yet, so the BSDF's own roughness and
  coat are Blender's defaults (a gap, #227).
- **Out**: `<out>/frames/<frame>.npz` (each curve's point count, its points in metres, Z up, its radius, its root UV and
  whether it is a guide) at the bind and at each clip frame, written to USD BasisCurves by `basis_curves.py`;
  pictures `front.png`, `three.png`, `clip_<frame>.png`; `measures.json`: strands, points, roots off the
  surface and points inside the body, per frame.
"""
import argparse
import json
import math
import pathlib
import random
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector, geometry
from mathutils.bvhtree import BVHTree

GUIDES = 1400  # guide strands combed by hand-written rules; the rest are grown from them
CHILDREN = 32000  # strands grown by Interpolate Curves between the guides
POINTS = 32  # points a combed strand: its chords a centimetre or less, so they follow the shell's bumps
DRAWN_POINTS = 64  # points a drawn strand: kept off the surface once more at this, its chords half a centimetre
STEP = 0.004  # metres a combing step
ROOT_ABOVE = 0.045  # a root lies at least this far above the Head joint: the scalp, not the hair's fall
OFF_SHELL = 0.012  # a step whose nearest shell point is further than this left the shell's edge
OVERHANG = 0.01  # metres a strand carries on past the shell's edge
LIP = -0.7  # a shell normal pointing further down than this is the bob's underside, where the strand ends
LAYER = (0.0015, 0.0075)  # how far off the shell a strand lies, in metres, its layer drawn at random
ROOT_RISE = 0.008  # metres over which a strand rises from its root to its layer
FALL = 0.07  # metres below the top of the head over which a strand turns from the parting to gravity
FRONT = 0.05  # a root further forward than this from the Head joint is the fringe's
RADIUS = (0.00012, 0.00003)  # a strand's radius at its root and its tip, metres
SEED = 227
WELD = 5  # decimals of a metre two glb points must share to be one place (10 micrometres)
SIZE = 900  # the head pictures' pixels across
CLIP_SIZE = 720  # a clip frame's
SAMPLES = 128
OFF_ROOT = 0.001  # metres: a root this far from the body's surface has left its place
BEHIND = 0.02  # metres: a strand point further behind the surface than this is not pushed out
PAST = 0.00005  # metres past a segment's start it is asked from


def arguments():
    parser = argparse.ArgumentParser()
    for name in ("--body", "--dress", "--style", "--library", "--out"):
        parser.add_argument(name, required=True)
    parser.add_argument("--clip", default="walking")
    parser.add_argument("--frames", default="0,7,14,21")
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:])


def imported(path):
    """The glb's objects, the far body and the importer's stray sphere left out: (armature, body mesh object)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [ob for ob in bpy.data.objects if ob not in before]
    for ob in new:
        if ob.name.startswith(("far", "Icosphere")):
            bpy.data.objects.remove(ob)
    armature = next(ob for ob in bpy.data.objects if ob.type == "ARMATURE" and ob in new)
    meshes = [ob for ob in bpy.data.objects if ob.type == "MESH" and ob in new and ob.name in bpy.data.objects]
    return armature, max(meshes, key=lambda ob: len(ob.data.vertices))


def hair_materials(body, dress):
    """Indices of the body's materials that are its hair part's surfaces painted other than skin. The dress record
    (dress.json) names each surface `<part>#<n>` with its role and painted surface; the glb names the materials of one
    part `<part>`, `<part>.001`, ... in the order of n. The made head is one part: its face is painted skin
    (woman_stair: hair#7 skin_light, hair#8 the hair and the shoulders)."""
    record = json.loads(pathlib.Path(dress).read_text())
    families = {name: entry["family"] for name, entry in record["bake"]["surfaces"].items()}
    hair = sorted((key for key, entry in record["surfaces"].items() if entry["role"] == "hair"),
                  key=lambda key: int(key.split("#")[1]))
    names = [material.name for material in body.data.materials]
    chosen = set()
    for order, key in enumerate(hair):
        name = key.split("#")[0] + (f".{order:03d}" if order else "")
        if families.get(record["surfaces"][key]["painted"]) != "skin":
            chosen.add(names.index(name))
    return chosen


def welded_edges(mesh, index):
    """The face's edges as pairs of rounded point places: the glb splits its points at every UV seam, so faces that
    touch share places, not point indices."""
    places = [tuple(round(component, WELD) for component in mesh.vertices[vertex].co)
              for vertex in mesh.polygons[index].vertices]
    return [tuple(sorted((places[corner], places[(corner + 1) % len(places)]))) for corner in range(len(places))]


def shell_faces(body, materials, floor):
    """The scalp shell: the faces of `materials` above `floor` (world height: the neck's base, under which the parts
    judge gave the same part the shoulders) joined by edges to the topmost of them."""
    mesh = body.data
    world = body.matrix_world
    candidates = {polygon.index for polygon in mesh.polygons
                  if polygon.material_index in materials and (world @ polygon.center).z > floor}
    by_edge = {}
    for index in candidates:
        for key in welded_edges(mesh, index):
            by_edge.setdefault(key, []).append(index)
    top = max(candidates, key=lambda index: mesh.polygons[index].center.z)
    found, waiting = {top}, [top]
    while waiting:
        index = waiting.pop()
        for key in welded_edges(mesh, index):
            for other in by_edge[key]:
                if other not in found:
                    found.add(other)
                    waiting.append(other)
    return sorted(found)


def rest_world(body):
    """The body's rest points in world metres (its original mesh, before the armature)."""
    world = body.matrix_world
    return [world @ vertex.co for vertex in body.data.vertices]


def shell_tree(body, faces, points):
    """A BVH of the shell faces at rest, in world space."""
    polygons = [list(body.data.polygons[index].vertices) for index in faces]
    return BVHTree.FromPolygons(points, polygons)


def parting(points, faces, body, head, style):
    """The parting as a segment over the head, (front end, back end), on the style's side of the head's middle.
    The body faces +Y and its left is -X."""
    side = -1.0 if style["parting_side"] == "left" else 1.0
    x_part = head.x + side * style["parting_m"]
    used = {vertex for index in faces for vertex in body.data.polygons[index].vertices}
    top = max(points[vertex].z for vertex in used)
    near = [points[vertex] for vertex in used if abs(points[vertex].x - x_part) < 0.012 and points[vertex].z > top - 0.05]
    front = max(near, key=lambda point: point.y)
    back = min(near, key=lambda point: abs(point.y - (head.y - 0.05)) - point.z)
    return Vector((x_part, front.y, front.z)), Vector((x_part, back.y, back.z)), top


def on_segment(point, ends):
    start, end = ends
    along = end - start
    share = max(0.0, min(1.0, (point - start).dot(along) / along.length_squared))
    return start + along * share


def tangent(vector, normal):
    flat = vector - normal * vector.dot(normal)
    return flat.normalized() if flat.length > 1e-9 else flat


def comb(point, normal, ends, top, sweep):
    """The direction a strand runs at `point`: away from the parting, turning to gravity as it falls, a fringe strand
    swept to its side."""
    away = tangent(point - on_segment(point, ends), normal)
    down = tangent(Vector((0.0, 0.0, -1.0)), normal)
    fall = max(0.0, min(1.0, (top - point.z) / FALL))
    direction = away * (1.0 - fall) + (away * 0.35 + down) * fall + tangent(sweep, normal)
    return direction.normalized() if direction.length > 1e-9 else down


def traced(root, tree, ends, top, sweep, longest):
    """A strand's path down the shell from its root, [(point, normal)], ending where the shell turns under (the made
    bob's lower lip folds in towards the neck: a strand that followed it ran up inside the hair) or, carried on OVERHANG past it, where the shell's edge ends (the made
    hairline is a saw of triangles; a strand lying just over it hides the saw, as hair does)."""
    location, normal, _, _ = tree.find_nearest(root)
    path = [(location, normal)]
    direction = Vector()
    for _ in range(int(longest / STEP)):
        direction = comb(location, normal, ends, top, sweep)
        found = tree.find_nearest(location + direction * STEP)
        if found[0] is None or found[1].z < LIP:
            return path
        if found[3] > OFF_SHELL * 0.5:
            break
        location, normal = found[0], found[1]
        path.append((location, normal))
    for _ in range(int(OVERHANG / STEP)):
        location = location + direction * STEP
        path.append((location, normal))
    return path


def laid(path, layer, phase, style):
    """The strand's points off the shell: risen to its layer from the root, waved across its run, POINTS of them
    evenly along its length."""
    length = [0.0]
    for (one, _), (two, _) in zip(path, path[1:]):
        length.append(length[-1] + (two - one).length)
    points = []
    for index, (location, normal) in enumerate(path):
        run = path[min(index + 1, len(path) - 1)][0] - path[max(index - 1, 0)][0]
        across = normal.cross(run).normalized() if run.length > 1e-9 else Vector()
        rise = min(1.0, length[index] / ROOT_RISE)
        wave = style["wave_m"] * math.sin(2 * math.pi * length[index] / style["wave_period_m"] + phase)
        points.append(location + normal * layer * rise + across * wave * rise)
    return resampled(points, length)


def resampled(points, length):
    total = length[-1]
    out, segment = [], 0
    for index in range(POINTS):
        at = total * index / (POINTS - 1)
        while segment < len(points) - 2 and length[segment + 1] < at:
            segment += 1
        span = max(length[segment + 1] - length[segment], 1e-12)
        share = min(1.0, max(0.0, (at - length[segment]) / span))
        out.append(points[segment].lerp(points[segment + 1], share))
    return out


def roots(body, faces, points, head, count, rng):
    """`count` root places on the shell's faces above the scalp line, area-weighted: [(point, body face index)]."""
    scalp = [index for index in faces if points[body.data.polygons[index].vertices[0]].z > head.z + ROOT_ABOVE]
    triangles, areas = [], []
    for index in scalp:
        corners = [points[vertex] for vertex in body.data.polygons[index].vertices]
        for second in range(1, len(corners) - 1):
            triangles.append((index, corners[0], corners[second], corners[second + 1]))
            areas.append(geometry.area_tri(corners[0], corners[second], corners[second + 1]))
    picked = rng.choices(range(len(triangles)), weights=areas, k=count)
    out = []
    for choice in picked:
        index, one, two, three = triangles[choice]
        first, second = rng.random(), rng.random()
        if first + second > 1:
            first, second = 1 - first, 1 - second
        out.append((one + (two - one) * first + (three - one) * second, index))
    return out, scalp, sum(areas)


def root_uv(body, face, point, points):
    """The root's place in the body's UV map, from its triangle of `face` (barycentric)."""
    polygon = body.data.polygons[face]
    loops = list(polygon.loop_indices)
    uv = body.data.uv_layers["UVMap"].data
    for second in range(1, len(loops) - 1):
        corners = [loops[0], loops[second], loops[second + 1]]
        triangle = [points[body.data.loops[loop].vertex_index] for loop in corners]
        if geometry.intersect_point_tri(point, *triangle) or second == len(loops) - 2:
            flat = [Vector((uv[loop].uv.x, uv[loop].uv.y, 0.0)) for loop in corners]
            place = geometry.barycentric_transform(point, *triangle, *flat)
            return place.x, place.y
    raise ValueError(f"face {face} has no triangle")


def guides(body, faces, points, head, style, rng):
    """The guide strands: [(points world, root uv, root normal)], their scalp faces and the scalp's area."""
    tree = shell_tree(body, faces, points)
    ends = parting(points, faces, body, head, style)
    top = ends[2]
    fringe = Vector((1.0 if style["fringe_side"] == "right" else -1.0, 0.0, 0.0))
    places, scalp, area = roots(body, faces, points, head, GUIDES, rng)
    made = []
    for root, face in places:
        sweep = fringe * 0.8 if root.y > head.y + FRONT else Vector()
        path = traced(root, tree, ends[:2], top, sweep, style["length_m"])
        if len(path) < 4:
            continue
        strand = laid(path, rng.uniform(*LAYER), rng.uniform(0, 2 * math.pi), style)
        made.append((strand, root_uv(body, face, root, points), path[0][1]))
    return made, scalp, area


def curves_object(body, made):
    """The guides as a hair Curves object bound to the body: points in the body's own space, each curve's root UV
    and up (its root's normal), flagged as guides."""
    to_body = body.matrix_world.inverted()
    curves = bpy.data.hair_curves.new("hair")
    curves.add_curves([POINTS] * len(made))
    flat = [component for strand, _, _ in made for point in strand for component in to_body @ point]
    curves.attributes["position"].data.foreach_set("vector", flat)
    uv = curves.attributes.new("surface_uv_coordinate", "FLOAT2", "CURVE")
    uv.data.foreach_set("vector", [component for _, place, _ in made for component in place])
    turn = to_body.to_3x3()
    up = curves.attributes.new("up", "FLOAT_VECTOR", "CURVE")
    up.data.foreach_set("vector", [component for _, _, normal in made for component in (turn @ normal).normalized()])
    guide = curves.attributes.new("groom_guide", "INT", "CURVE")
    guide.data.foreach_set("value", [1] * len(made))
    curves.surface = body
    curves.surface_uv_map = "UVMap"
    ob = bpy.data.objects.new("hair", curves)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = body
    ob.matrix_parent_inverse = Matrix.Identity(4)
    return ob


def scalp_attribute(body, scalp):
    """The body's face attribute `hair_scalp`: true on the faces children are grown from."""
    attribute = body.data.attributes.new("hair_scalp", "BOOLEAN", "FACE")
    chosen = set(scalp)
    attribute.data.foreach_set("value", [polygon.index in chosen for polygon in body.data.polygons])
    body.add_rest_position_attribute = True


def node(tree, kind, location, **settings):
    made = tree.nodes.new(kind)
    made.location = location
    for name, value in settings.items():
        setattr(made, name, value)
    return made


def attribute_node(tree, name, data_type, location):
    reading = node(tree, "GeometryNodeInputNamedAttribute", location, data_type=data_type)
    reading.inputs["Name"].default_value = name
    return reading


def math_node(tree, operation, location, kind="ShaderNodeMath"):
    return node(tree, kind, location, operation=operation)


def rest_surface(tree, body):
    """The body as drawn, laid back at its rest shape (its rest_position): the surface strands are grown and kept off
    at, so the same strands grow at every frame."""
    surface = node(tree, "GeometryNodeObjectInfo", (-1800, -300), transform_space="RELATIVE")
    surface.inputs["Object"].default_value = body
    rest = node(tree, "GeometryNodeSetPosition", (-1600, -300))
    tree.links.new(surface.outputs["Geometry"], rest.inputs["Geometry"])
    tree.links.new(attribute_node(tree, "rest_position", "FLOAT_VECTOR", (-1800, -500)).outputs["Attribute"],
                   rest.inputs["Position"])
    return rest.outputs["Geometry"]


def children_grown(tree, guides, rest, area):
    """Children on the scalp faces at rest, shaped by Interpolate Curves from the guides, each carrying its root's
    UV as `surface_uv_coordinate` and flagged as no guide (Interpolate Curves hands them the guides' attributes);
    joined with the guides."""
    link = tree.links.new
    spread = node(tree, "GeometryNodeDistributePointsOnFaces", (-1400, -300))
    spread.inputs["Density"].default_value = CHILDREN / area
    spread.inputs["Seed"].default_value = SEED
    link(rest, spread.inputs["Mesh"])
    link(attribute_node(tree, "hair_scalp", "BOOLEAN", (-1600, -600)).outputs["Attribute"],
         spread.inputs["Selection"])
    children = node(tree, "GeometryNodeInterpolateCurves", (-1200, -100))
    link(guides, children.inputs["Guide Curves"])
    link(attribute_node(tree, "up", "FLOAT_VECTOR", (-1400, 0)).outputs["Attribute"], children.inputs["Guide Up"])
    link(spread.outputs["Points"], children.inputs["Points"])
    link(spread.outputs["Normal"], children.inputs["Point Up"])
    grown_only = node(tree, "GeometryNodeStoreNamedAttribute", (-1100, -100), data_type="INT", domain="CURVE")
    grown_only.inputs["Name"].default_value = "groom_guide"
    grown_only.inputs["Value"].default_value = 0
    link(children.outputs["Curves"], grown_only.inputs["Geometry"])
    bound = node(tree, "GeometryNodeStoreNamedAttribute", (-1000, -100), data_type="FLOAT2", domain="CURVE")
    bound.inputs["Name"].default_value = "surface_uv_coordinate"
    link(grown_only.outputs["Geometry"], bound.inputs["Geometry"])
    link(attribute_node(tree, "UVMap", "FLOAT_VECTOR", (-1200, -400)).outputs["Attribute"], bound.inputs["Value"])
    joined = node(tree, "GeometryNodeJoinGeometry", (-800, 0))
    link(bound.outputs["Geometry"], joined.inputs["Geometry"])
    link(guides, joined.inputs["Geometry"])
    return joined.outputs["Geometry"]


def nearest_on(tree, rest, field, location):
    """The rest surface's `field` (a vector) at its point nearest each strand point."""
    sample = node(tree, "GeometryNodeSampleNearestSurface", location, data_type="FLOAT_VECTOR")
    tree.links.new(rest, sample.inputs["Mesh"])
    tree.links.new(field, sample.inputs["Value"])
    return sample.outputs["Value"]


def kept_off(tree, curves, rest):
    """Every strand point at least LAYER[0] off the rest surface in front of it (rising from 0 at the root over
    ROOT_RISE, as the guides do), pushed out along that surface's normal: a child shaped by a guide a few millimetres
    away, or a guide between two combing steps, otherwise dips into a bump of the shell or the face beside it.
    Points further behind the surface than BEHIND are left (none is that deep: it would be inside the head)."""
    link = tree.links.new
    near = nearest_on(tree, rest, node(tree, "GeometryNodeInputPosition", (-1000, -700)).outputs["Position"],
                      (-800, -700))
    normal = nearest_on(tree, rest, node(tree, "GeometryNodeInputNormal", (-1000, -900)).outputs["Normal"],
                        (-800, -900))
    position = node(tree, "GeometryNodeInputPosition", (-800, -500)).outputs["Position"]
    offset = math_node(tree, "SUBTRACT", (-600, -600), "ShaderNodeVectorMath")
    link(position, offset.inputs[0])
    link(near, offset.inputs[1])
    height = math_node(tree, "DOT_PRODUCT", (-400, -600), "ShaderNodeVectorMath")
    link(offset.outputs["Vector"], height.inputs[0])
    link(normal, height.inputs[1])
    along = node(tree, "GeometryNodeSplineParameter", (-600, -900))
    rise = node(tree, "ShaderNodeMapRange", (-400, -900))
    rise.inputs["From Max"].default_value = ROOT_RISE
    rise.inputs["To Max"].default_value = LAYER[0]
    link(along.outputs["Length"], rise.inputs["Value"])
    short = math_node(tree, "SUBTRACT", (-200, -700))
    link(rise.outputs["Result"], short.inputs[0])
    link(height.outputs["Value"], short.inputs[1])
    push = math_node(tree, "MAXIMUM", (0, -700))
    link(short.outputs["Value"], push.inputs[0])
    push.inputs[1].default_value = 0.0
    shallow = math_node(tree, "GREATER_THAN", (-200, -900))
    link(height.outputs["Value"], shallow.inputs[0])
    shallow.inputs[1].default_value = -BEHIND
    gated = math_node(tree, "MULTIPLY", (200, -800))
    link(push.outputs["Value"], gated.inputs[0])
    link(shallow.outputs["Value"], gated.inputs[1])
    moved = math_node(tree, "SCALE", (400, -800), "ShaderNodeVectorMath")
    link(normal, moved.inputs[0])
    link(gated.outputs["Value"], moved.inputs["Scale"])
    pushed = node(tree, "GeometryNodeSetPosition", (600, -400))
    link(curves, pushed.inputs["Geometry"])
    link(moved.outputs["Vector"], pushed.inputs["Offset"])
    return pushed.outputs["Geometry"]


def untorn(tree, curves, rest):
    """The strands whose root UV finds their root again on the rest surface (Sample UV Surface within OFF_ROOT):
    a UV that lies on two islands of the body's map, or on none, would carry its strand to the wrong triangle."""
    link = tree.links.new
    found = node(tree, "GeometryNodeSampleUVSurface", (800, -600), data_type="FLOAT_VECTOR")
    link(rest, found.inputs["Mesh"])
    link(node(tree, "GeometryNodeInputPosition", (600, -700)).outputs["Position"], found.inputs["Value"])
    link(attribute_node(tree, "UVMap", "FLOAT_VECTOR", (600, -800)).outputs["Attribute"],
         found.inputs["Source UV Map"])
    link(attribute_node(tree, "surface_uv_coordinate", "FLOAT_VECTOR", (600, -900)).outputs["Attribute"],
         found.inputs["Sample UV"])
    first = node(tree, "GeometryNodePointsOfCurve", (600, -1000))
    root = node(tree, "GeometryNodeSampleIndex", (800, -900), data_type="FLOAT_VECTOR", domain="POINT")
    link(curves, root.inputs["Geometry"])
    link(node(tree, "GeometryNodeInputPosition", (600, -1100)).outputs["Position"], root.inputs["Value"])
    link(first.outputs["Point Index"], root.inputs["Index"])
    apart = math_node(tree, "DISTANCE", (1000, -700), "ShaderNodeVectorMath")
    link(found.outputs["Value"], apart.inputs[0])
    link(root.outputs["Value"], apart.inputs[1])
    far = math_node(tree, "GREATER_THAN", (1200, -700))
    link(apart.outputs["Value"], far.inputs[0])
    far.inputs[1].default_value = OFF_ROOT
    lost = node(tree, "FunctionNodeBooleanMath", (1200, -900), operation="NOT")
    link(found.outputs["Is Valid"], lost.inputs[0])
    either = node(tree, "FunctionNodeBooleanMath", (1400, -800), operation="OR")
    link(far.outputs["Value"], either.inputs[0])
    link(lost.outputs["Boolean"], either.inputs[1])
    kept = node(tree, "GeometryNodeDeleteGeometry", (1600, -400), domain="CURVE")
    link(curves, kept.inputs["Geometry"])
    link(either.outputs["Boolean"], kept.inputs["Selection"])
    return kept.outputs["Geometry"]


def uncrossed(tree, curves, rest):
    """The strands none of whose segments crosses the rest surface (GN's Raycast from each point to the next, from
    PAST along it): the few a fold of the made shell still catches after the pushes are left out whole, never drawn
    through the head."""
    link = tree.links.new
    position = node(tree, "GeometryNodeInputPosition", (1800, -900)).outputs["Position"]
    following = node(tree, "GeometryNodeOffsetPointInCurve", (1800, -1100))
    following.inputs["Offset"].default_value = 1
    ahead = node(tree, "GeometryNodeSampleIndex", (2000, -1000), data_type="FLOAT_VECTOR", domain="POINT")
    link(curves, ahead.inputs["Geometry"])
    link(position, ahead.inputs["Value"])
    link(following.outputs["Point Index"], ahead.inputs["Index"])
    run = math_node(tree, "SUBTRACT", (2200, -1000), "ShaderNodeVectorMath")
    link(ahead.outputs["Value"], run.inputs[0])
    link(position, run.inputs[1])
    unit = math_node(tree, "NORMALIZE", (2400, -1100), "ShaderNodeVectorMath")
    link(run.outputs["Vector"], unit.inputs[0])
    step = math_node(tree, "SCALE", (2600, -1100), "ShaderNodeVectorMath")
    link(unit.outputs["Vector"], step.inputs[0])
    step.inputs["Scale"].default_value = PAST
    start = math_node(tree, "ADD", (2800, -1000), "ShaderNodeVectorMath")
    link(position, start.inputs[0])
    link(step.outputs["Vector"], start.inputs[1])
    length = math_node(tree, "LENGTH", (2400, -900), "ShaderNodeVectorMath")
    link(run.outputs["Vector"], length.inputs[0])
    reach = math_node(tree, "SUBTRACT", (2600, -900))
    link(length.outputs["Value"], reach.inputs[0])
    reach.inputs[1].default_value = PAST
    ray = node(tree, "GeometryNodeRaycast", (3000, -900))
    link(rest, ray.inputs["Target Geometry"])
    link(start.outputs["Vector"], ray.inputs["Source Position"])
    link(unit.outputs["Vector"], ray.inputs["Ray Direction"])
    link(reach.outputs["Value"], ray.inputs["Ray Length"])
    counted = node(tree, "FunctionNodeBooleanMath", (3200, -900), operation="AND")
    link(ray.outputs["Is Hit"], counted.inputs[0])
    link(following.outputs["Is Valid Offset"], counted.inputs[1])
    marked = node(tree, "GeometryNodeStoreNamedAttribute", (3400, -400), data_type="FLOAT", domain="POINT")
    marked.inputs["Name"].default_value = "crossing"
    link(curves, marked.inputs["Geometry"])
    link(counted.outputs["Boolean"], marked.inputs["Value"])
    any_point = math_node(tree, "GREATER_THAN", (3600, -700))
    link(attribute_node(tree, "crossing", "FLOAT", (3400, -700)).outputs["Attribute"], any_point.inputs[0])
    any_point.inputs[1].default_value = 0.0
    kept = node(tree, "GeometryNodeDeleteGeometry", (3800, -400), domain="CURVE")
    link(marked.outputs["Geometry"], kept.inputs["Geometry"])
    link(any_point.outputs["Value"], kept.inputs["Selection"])
    dropped = node(tree, "GeometryNodeRemoveAttribute", (4000, -400))
    dropped.inputs["Name"].default_value = "crossing"
    link(kept.outputs["Geometry"], dropped.inputs["Geometry"])
    return dropped.outputs["Geometry"]


def grown(hair, body, area, material):
    """The Geometry Nodes modifier on the guides: children grown on the scalp at rest, every strand kept off the
    surface, resampled finer and kept off again (a chord between two kept points still cut the shell's sharper
    bumps), a strand still crossing it left out, bound by its root UV, deformed with the body, tapered, in the hair material."""
    tree = bpy.data.node_groups.new("hair_grown", "GeometryNodeTree")
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    link = tree.links.new
    rest = rest_surface(tree, body)
    curves = children_grown(tree, node(tree, "NodeGroupInput", (-1800, 0)).outputs["Geometry"], rest, area)
    finer = node(tree, "GeometryNodeResampleCurve", (700, -200))
    finer.inputs["Count"].default_value = DRAWN_POINTS
    link(kept_off(tree, curves, rest), finer.inputs["Curve"])
    curves = uncrossed(tree, untorn(tree, kept_off(tree, finer.outputs["Curve"], rest), rest), rest)
    deformed = node(tree, "GeometryNodeDeformCurvesOnSurface", (1800, 0))
    link(curves, deformed.inputs["Curves"])
    tapered = node(tree, "GeometryNodeSetCurveRadius", (2000, 0))
    link(deformed.outputs["Curves"], tapered.inputs["Curve"])
    taper = node(tree, "ShaderNodeMapRange", (1800, -250))
    taper.inputs["To Min"].default_value, taper.inputs["To Max"].default_value = RADIUS
    link(node(tree, "GeometryNodeSplineParameter", (1600, -250)).outputs["Factor"], taper.inputs["Value"])
    link(taper.outputs["Result"], tapered.inputs["Radius"])
    dressed = node(tree, "GeometryNodeSetMaterial", (2200, 0))
    dressed.inputs["Material"].default_value = material
    link(tapered.outputs["Curve"], dressed.inputs["Geometry"])
    link(dressed.outputs["Geometry"], node(tree, "NodeGroupOutput", (2400, 0)).inputs["Geometry"])
    modifier = hair.modifiers.new("hair_grown", "NODES")
    modifier.node_group = tree
    hair.data.materials.append(material)


def library_surface(library, name):
    """The named variant of the people line's surface library: its linear colour and roughness."""
    spec = json.loads(pathlib.Path(library).read_text())[name]
    return spec["colour"], spec["roughness"]


def finished(body, faces, colour, roughness):
    """The hair material (Principled Hair BSDF in the surface's colour), and the shell (`faces`) under the strands in
    the surface itself: the dress left it painted skin and the tee (#227)."""
    hair = bpy.data.materials.new("hair_strands")
    hair.use_nodes = True
    nodes = hair.node_tree.nodes
    nodes.remove(nodes["Principled BSDF"])
    bsdf = nodes.new("ShaderNodeBsdfHairPrincipled")
    bsdf.parametrization = "COLOR"
    bsdf.inputs["Color"].default_value = (*colour, 1.0)
    hair.node_tree.links.new(bsdf.outputs[0], nodes["Material Output"].inputs["Surface"])
    under = bpy.data.materials.new("hair_under")
    under.use_nodes = True
    principled = under.node_tree.nodes["Principled BSDF"]
    principled.inputs["Base Color"].default_value = (*colour, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    body.data.materials.append(under)
    slot = len(body.data.materials) - 1
    for index in faces:
        body.data.polygons[index].material_index = slot
    return hair


def lit(scene):
    """A grey ground light and three area lights (key, fill, rim) that travel with the camera."""
    world = bpy.data.worlds.new("ground")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.56, 0.58, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    scene.world = world
    camera = bpy.data.objects.new("camera", bpy.data.cameras.new("camera"))
    camera.data.lens = 85
    scene.collection.objects.link(camera)
    scene.camera = camera
    for name, place, power in (("key", (0.9, -0.5, 0.7), 32.0), ("fill", (-1.0, -0.2, 0.1), 10.0),
                               ("rim", (-0.2, 1.2, 0.8), 40.0)):
        light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        light.data.energy, light.data.size = power, 0.6
        light.location = place
        light.parent = camera
        light.rotation_euler = (Vector((0, 0, 0)) - Vector(place)).to_track_quat("-Z", "Y").to_euler()
        scene.collection.objects.link(light)
    return camera


def rendering(scene):
    scene.render.engine = "CYCLES"
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = "CUDA"
    preferences.get_devices()
    for device in preferences.devices:
        device.use = True
    scene.cycles.device = "GPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles_curves.shape = "THICK"
    scene.view_settings.view_transform = "AgX"


def shot(scene, camera, aim, turn, distance, size, path):
    """A still from `turn` degrees round the face (0: in front, the body faces +Y) at `distance` from `aim`."""
    angle = math.radians(turn)
    camera.location = aim + Vector((math.sin(angle), math.cos(angle), 0.04)).normalized() * distance
    camera.rotation_euler = (aim - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x = scene.render.resolution_y = size
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def evaluated_strands(hair):
    """The strands as drawn now: (point counts, points in world metres, radii, root uvs, guide flags)."""
    graph = bpy.context.evaluated_depsgraph_get()
    drawn = hair.evaluated_get(graph)
    data = drawn.data
    count = len(data.points)
    points = np.empty(count * 3)
    data.attributes["position"].data.foreach_get("vector", points)
    points = points.reshape(-1, 3) @ np.array(drawn.matrix_world.to_3x3()).T + np.array(drawn.matrix_world.translation)
    radius = np.empty(count)
    data.attributes["radius"].data.foreach_get("value", radius)
    offsets = np.empty(len(data.curves) + 1, dtype=np.int32)
    data.curve_offset_data.foreach_get("value", offsets)
    uv = np.empty(len(data.curves) * 2)
    data.attributes["surface_uv_coordinate"].data.foreach_get("vector", uv)
    guide = np.empty(len(data.curves), dtype=np.int32)
    data.attributes["groom_guide"].data.foreach_get("value", guide)
    return np.diff(offsets), points, radius, uv.reshape(-1, 2), guide


def body_tree(body):
    """The body as drawn now, as a BVH in world space."""
    graph = bpy.context.evaluated_depsgraph_get()
    drawn = body.evaluated_get(graph)
    mesh = drawn.to_mesh()
    world = drawn.matrix_world
    points = [world @ vertex.co for vertex in mesh.vertices]
    polygons = [list(polygon.vertices) for polygon in mesh.polygons]
    tree = BVHTree.FromPolygons(points, polygons)
    drawn.to_mesh_clear()
    return tree


def measured(strands, body):
    """Roots off the body's surface (the binding's error: OFF_ROOT or more is a strand torn from its place) and strand
    segments that cross the body's surface, the shell included (a strand through the head, the face or the
    shoulders), each segment asked from just past its start so a root on the surface is not its own crossing."""
    counts, points, _, _, _ = strands
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    off = np.array([body.find_nearest(Vector(points[start]))[3] for start in starts])
    ends = np.ones(len(points), dtype=bool)
    ends[np.cumsum(counts) - 1] = False
    crossing = 0
    for index in np.nonzero(ends)[0]:
        start, end = Vector(points[index]), Vector(points[index + 1])
        run = end - start
        if run.length > 2 * PAST and body.ray_cast(start + run.normalized() * PAST, run, run.length - PAST)[0]:
            crossing += 1
    return {"strands": int(len(counts)), "points": int(len(points)),
            "roots_off_mm_max": round(1000 * float(off.max()), 3), "roots_off": int((off >= OFF_ROOT).sum()),
            "segments": int(ends.sum()), "segments_through_body": crossing}


def kept(hair, body, path):
    """The strands as drawn now saved at `path`, and their measures."""
    strands = evaluated_strands(hair)
    saved(strands, path)
    return measured(strands, body_tree(body))


def saved(strands, path):
    counts, points, radius, uv, guide = strands
    np.savez_compressed(path, counts=counts, points=points, radius=radius, root_uv=uv, guide=guide)


def main():
    given = arguments()
    out = pathlib.Path(given.out)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    style = json.loads(pathlib.Path(given.style).read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    armature, body = imported(given.body)
    head = armature.matrix_world @ armature.data.bones["Head"].head_local
    floor = (armature.matrix_world @ armature.data.bones["Neck1"].head_local).z
    faces = shell_faces(body, hair_materials(body, given.dress), floor)
    points = rest_world(body)
    made, scalp, area = guides(body, faces, points, head, style, random.Random(SEED))
    colour, roughness = library_surface(given.library, style["surface"])
    material = finished(body, faces, colour, roughness)
    scalp_attribute(body, scalp)
    hair = curves_object(body, made)
    grown(hair, body, area, material)
    scene = bpy.context.scene
    rendering(scene)
    camera = lit(scene)
    measures = {"guides": len(made), "scalp_faces": len(scalp), "scalp_m2": area, "shell_faces": len(faces),
                "surface": style["surface"], "colour_linear": colour, "frames": {}}
    armature.data.pose_position = "REST"
    measures["frames"]["bind"] = kept(hair, body, out / "frames" / "bind.npz")
    aim = head + Vector((0, 0, 0.08))
    for name, turn in (("front", 0), ("three", 40), ("back", 180)):
        shot(scene, camera, aim, turn, 1.0, SIZE, out / f"{name}.png")
    armature.data.pose_position = "POSE"
    armature.animation_data.action = bpy.data.actions[given.clip]
    for frame in [int(frame) for frame in given.frames.split(",")]:
        scene.frame_set(frame)
        measures["frames"][frame] = kept(hair, body, out / "frames" / f"{frame:03d}.npz")
        aim = armature.matrix_world @ armature.pose.bones["Head"].head + Vector((0, 0, 0.03))
        shot(scene, camera, aim, 35, 1.25, CLIP_SIZE, out / f"clip_{frame:03d}.png")
    (out / "measures.json").write_text(json.dumps(measures, indent=1))
    print("GROOM", json.dumps(measures))


if __name__ == "__main__":
    main()
