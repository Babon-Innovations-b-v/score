"""A made model's moving parts (#177, PRD #159; #161 rules 1 and 11): NVIDIA cuts a model by what moves (a door, a
drawer, a lid, a wheel, a knob), each joined to the body by a revolute or prismatic joint with limits, so a TRELLIS.2
model, made in one piece, is cut the same way here and written in the form score's own workflows read: each moving
part a node `<part>__<joint>_<axis>[n]` whose origin is its pivot (score/stages/props/moving_parts' interface, read by
the motion layer's `parts_of`, place_build's glTF conversion and the physics layer's `write_parted`).

    asked(words, size, picture, ask=None)                -> [{name, joint, box, hinge, opens, thick_m}], one ask
    cut(vertices, faces, listed, camera, size)           -> each face's part (-1 the still body), {name: why left out}
    jointed(vertices, faces, face_part, listed, camera, size) -> each cut part's joint {axis, sign, pivot, limits}
    record(listed, face_part, joints, left_out)          -> parts.json's record
    written(model, face_part, record, out)               -> the model split into its part nodes (a GLB)
    part_masses(face_part, face_group, group_kg, areas, count) -> each part's kg and the body's, from its finish
                                                            groups' masses by the area each part holds of them
    part_classes(face_part, face_class, areas, count)    -> each part's physics class and the body's: its faces'
                                                            class of most area (each keeps its finish groups' own)

1. **Which pieces move**: one ask (Claude, EUR 0, kept by its hash, as the finish list and the mass are asked), the
   close-up shown with the object's words and size: each moving piece's function word, its joint (hinge, slide,
   spin), its box in the picture, a hinge's side of that box, how far it opens and how thick it is.
2. **Its faces** (`cut`): the faces whose middles the close-up's camera (a fitted one for TRELLIS.2,
   surfaces/close_up_fit.py) sees inside the piece's box, from the piece's outer face (where the camera's rays meet
   the model inside the box) in by its thickness along the way it faces (its seen faces' mean normal, to the model's
   nearest axis): a door's slab, not the cabinet behind it. Smaller boxes are cut first (a knob before the door it
   sits on); pieces under CRUMB of what was cut are dropped (a stray rim of the body), and a part left with under
   LEAST_FACES faces or LEAST_SHARE of the model's area is left out by name.
3. **Its joint** (`jointed`): a hinge about the edge of the part's box on its said side (the edge whose middle the
   camera sees nearest that side of the picture's box), at the part's back, turning the way that swings it out; a
   slide along the way it faces, out, as far as it opens (at most the model's depth there); a spin about the way it
   faces, through its middle, free. The axis is one of the model's own (it is set square to its heading,
   fit.headed), as the node name says it.
The model's frame is glTF's (y up, metres, front +z), the made model's own.
"""
import base64
import json
import pathlib

import numpy as np

JOINTS = ("hinge", "slide", "spin")
SIDES = ("left", "right", "top", "bottom")
RAYS = 48  # the camera's rays across a piece's box's longer side, finding its outer face
FRONT = 90  # the percentile of the met points along the way a piece faces that is its outer face
CRUMB = 0.05  # a connected piece of a part under this share of its area is not the part's
LEAST_FACES = 4
LEAST_SHARE = 0.001  # of the model's area
WIDEST_HINGE = 180.0  # degrees a hinge may open


def asking_body(words, size, picture=None):
    """The ask (a Gemini generateContent body, as claude_code reads one): the close-up (a PNG's bytes), the object's
    words and box, answered as its moving pieces."""
    text = (f"You find the pieces of an object that move against its body, for a physics simulator, as NVIDIA's "
            f"SimReady models are cut. The object: {words}. Its bounding box is "
            f"{' x '.join(f'{side:.3f}' for side in size)} m (wide, deep, tall). List each piece you see in the "
            "picture that moves on its own as a real one does: a door or lid on its hinge, a drawer or tray on its "
            "slide, a wheel, knob or dial that turns, a trigger or button pressed in. Leave out what does not move "
            "against the body (a handle fixed on a door moves with the door and is no piece of its own; a label, a "
            "foot, a seam). For each piece: `name` one function word (door, drawer, lid, flap, wheel, knob, dial, "
            "trigger, button, lever); `joint` hinge (turns about one of its edges), slide (moves straight in and "
            "out) or spin (turns about its own middle); `box` where it lies in the picture, [left, top, right, "
            "bottom], each a share 0 to 1 of the picture's width or height, counted from its top left; `hinge` for "
            "a hinge the side of its box its hinge runs along as seen in the picture (left, right, top or bottom), "
            "else none; `opens` how far a real one opens (degrees for a hinge, metres for a slide, 0 for a spin); "
            "`thick_m` how thick the moving piece is from its outer face inward, in metres. An object with no "
            "moving piece answers an empty list.")
    schema = {"type": "OBJECT", "properties": {
        "reason": {"type": "STRING"},
        "parts": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "name": {"type": "STRING"}, "joint": {"type": "STRING", "enum": list(JOINTS)},
            "box": {"type": "ARRAY", "items": {"type": "NUMBER"}},
            "hinge": {"type": "STRING", "enum": [*SIDES, "none"]}, "opens": {"type": "NUMBER"},
            "thick_m": {"type": "NUMBER"}}, "required": ["name", "joint", "box", "hinge", "opens", "thick_m"]}}},
        "required": ["reason", "parts"]}
    shown = [{"inline_data": {"mime_type": "image/png", "data": base64.b64encode(picture).decode()}},
             {"text": "The object as it was made from:"}] if picture else []
    return {"contents": [{"role": "user", "parts": [*shown, {"text": text}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}}


def claude_ask(body):
    """The ask sent to Claude on the subscription (EUR 0), its answer's JSON text."""
    from score.adapters.models import claude_code
    answer = claude_code.asked({"parts": body}, caller="make-parts")["parts"]
    if isinstance(answer, Exception):
        raise ValueError(f"no moving parts answer: {answer}")
    return answer


def checked(piece):
    """One answered piece, its name a part name (letters, digits and _); ValueError for one that is not a piece."""
    name = "".join(letter if letter.isalnum() else "_" for letter in str(piece["name"]).lower()).strip("_")
    box = [float(value) for value in piece["box"]]
    if not name or piece["joint"] not in JOINTS:
        raise ValueError(f"not a moving piece: {piece}")
    if len(box) != 4 or not (0.0 <= box[0] < box[2] <= 1.0 and 0.0 <= box[1] < box[3] <= 1.0):
        raise ValueError(f"{name}: its box {box} is not [left, top, right, bottom] inside the picture")
    if piece["joint"] == "hinge" and piece["hinge"] not in SIDES:
        raise ValueError(f"{name}: a hinge on no side of its box ({piece['hinge']})")
    if float(piece["thick_m"]) <= 0 or float(piece["opens"]) < 0:
        raise ValueError(f"{name}: thickness {piece['thick_m']} m, opening {piece['opens']}")
    return {"name": name, "joint": piece["joint"], "box": box, "hinge": piece["hinge"],
            "opens": float(piece["opens"]), "thick_m": float(piece["thick_m"])}


def asked(words, size, picture=None, ask=None):
    """The moving pieces seen in `picture` (a PNG's path), each checked; `ask` takes the body and gives the answer's
    JSON text (a test's), else Claude's."""
    shown = pathlib.Path(picture).read_bytes() if picture else None
    answer = json.loads((ask or claude_ask)(asking_body(words, size, shown)))
    return [checked(piece) for piece in answer["parts"]]


def projected(points, camera, size):
    """The picture places ([column, row]) of `points` seen by `camera` (route_cast.close_up_camera: eye, right, up,
    horizontal field), the inverse of route_cast.pixel_ways."""
    eye, right, up, field = camera
    width, height = size
    focal = width / 2 / np.tan(field / 2)
    relative = np.asarray(points, dtype=float) - eye
    depth = np.maximum(relative @ np.cross(up, right), 1e-9)
    return np.c_[width / 2 + focal * (relative @ right) / depth, height / 2 - focal * (relative @ up) / depth]


def met(mesh, camera, size, box):
    """(the faces the camera's rays meet inside a picture box (shares), where they meet them)."""
    import score.stages.surfaces  # noqa: F401  (the stage first: its modules import one another through it)
    import route_cast
    width, height = size
    left, top, right, bottom = box[0] * width, box[1] * height, box[2] * width, box[3] * height
    step = max(right - left, bottom - top) / RAYS
    columns, rows = np.meshgrid(np.arange(left + step / 2, right, step), np.arange(top + step / 2, bottom, step))
    ways = route_cast.pixel_ways(camera, size, np.c_[columns.ravel(), rows.ravel()])
    faces, _, points = mesh.ray.intersects_id(np.repeat(np.asarray(camera[0], float)[None], len(ways), axis=0),
                                                 ways, multiple_hits=False, return_locations=True)
    return np.asarray(faces), np.asarray(points)


def facing(normals, areas, faces):
    """(axis, sign) of the model's axis nearest the met faces' area-weighted mean normal."""
    mean = (normals[faces] * areas[faces, None]).sum(0)
    axis = int(np.argmax(np.abs(mean)))
    return axis, 1 if mean[axis] >= 0 else -1


def welded_pieces(vertices, faces, members):
    """Each member face's connected piece (faces sharing a corner where the corners lie, UV seams welded)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    _, corner = np.unique(np.round(vertices, 6), axis=0, return_inverse=True)
    corners = corner.reshape(-1)[faces[members]]
    rows = np.repeat(np.arange(len(members)), 3)
    graph = coo_matrix((np.ones(rows.size), (rows, corners.ravel() + len(members))),
                       shape=(len(members) + corner.max() + 1,) * 2)
    _, label = connected_components(graph, directed=False)
    return label[:len(members)]


def cut(vertices, faces, listed, camera, size):
    """(each face's part, an index into `listed`, -1 the still body; {name: why it was left out}) (module docstring,
    step 2). `camera` is route_cast.close_up_camera's, `size` the close-up's (width, height) pixels."""
    import trimesh
    vertices, faces = np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int64)
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    normals, areas, middles = mesh.face_normals, mesh.area_faces, mesh.triangles_center
    seen = projected(middles, camera, size) / np.asarray(size, dtype=float)
    face_part, left_out = np.full(len(faces), -1), {}
    order = sorted(range(len(listed)), key=lambda index: (listed[index]["box"][2] - listed[index]["box"][0])
                   * (listed[index]["box"][3] - listed[index]["box"][1]))
    for index in order:
        piece = listed[index]
        hit, points = met(mesh, camera, size, piece["box"])
        if not len(hit):
            left_out[piece["name"]] = "the camera meets nothing of the model inside its box"
            continue
        axis, sign = facing(normals, areas, hit)
        front = np.percentile(sign * points[:, axis], FRONT)
        left, top, right, bottom = piece["box"]
        inside = ((seen[:, 0] >= left) & (seen[:, 0] <= right) & (seen[:, 1] >= top) & (seen[:, 1] <= bottom)
                  & (sign * middles[:, axis] >= front - piece["thick_m"]) & (face_part < 0))
        members = np.nonzero(inside)[0]
        if len(members):
            label = welded_pieces(vertices, faces, members)
            held = np.bincount(label, weights=areas[members])
            members = members[held[label] >= CRUMB * held.sum()]
        if len(members) < LEAST_FACES or areas[members].sum() < LEAST_SHARE * areas.sum():
            left_out[piece["name"]] = f"{len(members)} faces cut, under {LEAST_FACES} or {LEAST_SHARE:.1%} of its area"
            continue
        face_part[members] = index
    return face_part, left_out


def hinge_line(low, high, axis, sign, piece, camera, size):
    """(the hinge's axis, its pivot): of the edges of the part's box at its back running across the way it faces,
    the one whose middle the camera sees nearest the said side of the piece's picture box."""
    left, top, right, bottom = (share * size[index % 2] for index, share in enumerate(piece["box"]))
    target = {"left": (left, (top + bottom) / 2), "right": (right, (top + bottom) / 2),
              "top": ((left + right) / 2, top), "bottom": ((left + right) / 2, bottom)}[piece["hinge"]]
    middle = (low + high) / 2
    back = low[axis] if sign > 0 else high[axis]
    edges = []
    for along in (index for index in range(3) if index != axis):
        other = 3 - axis - along
        for end in (low[other], high[other]):
            point = middle.copy()
            point[other], point[axis] = end, back
            edges.append((along, point))
    places = projected(np.array([point for _, point in edges]), camera, size)
    return edges[int(np.argmin(np.linalg.norm(places - target, axis=1)))]


def jointed(vertices, faces, face_part, listed, camera, size):
    """{part index: {"axis" x, y or z, "sign", "pivot", "limits"}} of each cut part (module docstring, step 3):
    limits degrees for a hinge, metres for a slide, None for a free spin."""
    import trimesh
    vertices, faces = np.asarray(vertices, dtype=float), np.asarray(faces, dtype=np.int64)
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    whole = vertices[faces].reshape(-1, 3)
    found = {}
    for index in sorted(set(np.asarray(face_part).tolist()) - {-1}):
        piece, members = listed[index], np.nonzero(np.asarray(face_part) == index)[0]
        corners = vertices[faces[members]].reshape(-1, 3)
        low, high = corners.min(0), corners.max(0)
        axis, sign = facing(mesh.face_normals, mesh.area_faces, members)
        middle = (low + high) / 2
        if piece["joint"] == "hinge":
            along, pivot = hinge_line(low, high, axis, sign, piece, camera, size)
            way = np.cross(np.eye(3)[along], middle - pivot)[axis] * sign
            joint = {"axis": along, "sign": 1 if way >= 0 else -1, "pivot": pivot,
                     "limits": [0.0, min(piece["opens"], WIDEST_HINGE)]}
        elif piece["joint"] == "slide":
            depth = float(np.ptp(whole[:, axis]))
            joint = {"axis": axis, "sign": sign, "pivot": middle,
                     "limits": [0.0, round(min(piece["opens"], depth), 5)]}
        else:
            joint = {"axis": axis, "sign": 1, "pivot": middle, "limits": None}
        found[index] = {**joint, "axis": "xyz"[joint["axis"]],
                        "pivot": [round(float(value), 5) for value in joint["pivot"]]}
    return found


def node_name(name, joint, axis, sign):
    """moving_parts.joint_name's `<part>__<joint>_<axis>[n]`."""
    from score.stages.props import moving_parts
    return moving_parts.joint_name(name, joint, axis, sign)


def record(listed, face_part, joints, left_out):
    """parts.json's record: each cut part {name (its function word and number), node, joint, axis, sign, pivot,
    limits, faces, box, thick_m}, the body's faces, and what was left out and why."""
    face_part = np.asarray(face_part)
    parts, numbers = [], {}
    for index in sorted(joints):
        piece, joint = listed[index], joints[index]
        numbers[piece["name"]] = numbers.get(piece["name"], 0) + 1
        name = f"{piece['name']}_{numbers[piece['name']]:02d}"
        parts.append({"name": name, "index": index, "node": node_name(name, piece["joint"], joint["axis"],
                                                                      joint["sign"]),
                      "joint": piece["joint"], "axis": joint["axis"], "sign": joint["sign"], "pivot": joint["pivot"],
                      "limits": joint["limits"], "faces": int((face_part == index).sum()), "box": piece["box"],
                      "thick_m": piece["thick_m"]})
    return {"parts": parts, "body": {"node": "body", "faces": int((face_part < 0).sum())}, "left_out": left_out,
            "frame": "the made model's own: glTF's y up, metres, front +z",
            "from": "score/stages/place_build/maker/parts.py (#177): the pieces Claude saw move in the close-up, "
                    "cut by the camera's view of their boxes and their thickness, each joint on its edge or axis"}


def written(model, face_part, parts_record, out):
    """The model (a GLB, its faces in scene.dump's order, as face_part counts them) split into its parts: the still
    body's pieces as nodes `body_<n>`, each moving part a node named its `node` at its pivot holding its pieces
    (`<name>_<n>`, laid from the pivot), every piece keeping its own material and texture coordinates; written to
    `out` as a GLB."""
    import trimesh
    scene = trimesh.load(str(model), force="scene")
    face_part = np.asarray(face_part)
    by_index = {part["index"]: part for part in parts_record["parts"]}
    parted, start = trimesh.Scene(), 0
    for part in parts_record["parts"]:
        parted.graph.update(frame_to=part["node"], frame_from=parted.graph.base_frame,
                            matrix=trimesh.transformations.translation_matrix(part["pivot"]))
    for number, mesh in enumerate(scene.dump(concatenate=False)):
        labels = face_part[start:start + len(mesh.faces)]
        start += len(mesh.faces)
        for label in np.unique(labels).tolist():
            piece = mesh.submesh([np.nonzero(labels == label)[0]], append=True)
            if label < 0 or label not in by_index:
                parted.add_geometry(piece, node_name=f"body_{number}", geom_name=f"body_{number}")
                continue
            part = by_index[label]
            piece.apply_translation(-np.asarray(part["pivot"], dtype=float))
            parted.add_geometry(piece, node_name=f"{part['name']}_{number}", geom_name=f"{part['name']}_{number}",
                                parent_node_name=part["node"])
    if start != len(face_part):
        raise ValueError(f"{model}: {start} faces, the parts name {len(face_part)}")
    parted.export(str(out))
    return out


def part_masses(face_part, face_group, group_kg, areas, count):
    """(each part's kg, an index below `count`; the still body's kg): each finish group's mass (`group_kg`, by the
    group `face_group` gives each face) shared out by the area of it each part holds."""
    face_part, face_group, areas = np.asarray(face_part), np.asarray(face_group), np.asarray(areas, dtype=float)
    group_area = np.bincount(face_group, weights=areas, minlength=len(group_kg))
    face_kg = np.asarray(group_kg, dtype=float)[face_group] * areas / np.maximum(group_area[face_group], 1e-12)
    held = np.bincount(face_part + 1, weights=face_kg, minlength=count + 1)
    return [float(value) for value in held[1:]], float(held[0])


def part_classes(face_part, face_class, areas, count):
    """(each part's class, an index below `count`; the still body's): the class (its finish group's, sim.py's) of most
    of its faces' area, None for a part with no face."""
    face_part, face_class, areas = np.asarray(face_part), np.asarray(face_class, dtype=object), np.asarray(areas)
    found = []
    for index in [*range(count), -1]:
        held = {}
        for name, area in zip(face_class[face_part == index], areas[face_part == index]):
            held[name] = held.get(name, 0.0) + float(area)
        found.append(max(held, key=held.get) if held else None)
    return found[:-1], found[-1]
