"""The people's dress rows: `people-dress-<look>` (free, world) lays the look's finish from the shared loop on its built
body (#41). The body's points at the bind are laid back into the finished model's frame (the rig's stand undone) and
each reads the library surface the loop's bake painted on the take's outer surface there (its labelled take, handed
on by the people's after-step, people-made@people: loop.py): of the painted samples within OUTER_REACH_M, those within
OUTER_BAND_M of the outermost along the point's normal vote (`outer_labels`). The take keeps the inside faces
Pixal3D grew (71% of the astronaut's faces no view saw, each painted from its nearest seen face), and the nearest
sample alone read the boots' insides as the grey suit, 2026-10-22. A garment is split where its triangles' surfaces
change, its labels smoothed over its edges first (a material drawn in two surfaces took the one most of its points
carried, and the brown overalls' chest and hips showed the grey: astronaut, 2026-10-22); a hard part or a skin part
takes one surface, its points' most; the hair and a print (the face cut from the close-up) keep the build's own
finish. Each glTF material takes its surface's colour, roughness and metalness from the library (data/library, the
people place's tokens) and names it in `extras.library`. The UsdSkel asset is written again from the dressed glTF
(tools/characters/skel_usd.py). The library recipe's own detail (bump, quilting) is not baked onto a person yet: the
colour, roughness and metalness are the library surface's, nothing else is a picture's. A look the loop made no model
for is blocked with its gap.

Gates: `dressed` (every surface of the outfit took a library surface) and `aligned` (the body's points lie on the
painted take: the median distance to the nearest painted sample within ALIGNED_MOST).
"""
import json
import pathlib
import shutil
import struct
import subprocess
import sys

import numpy as np

from score.stages.people_bodies import bodies

REPO = pathlib.Path(__file__).resolve().parents[3]
ALIGNED_MOST = 0.01
LINE = "people"
# A body point reads the painted samples this near it, and of those the ones this near the outermost along its normal
# (outer_labels). UNMEASURED: picked (2026-10-22) on the astronaut, its boots' insides within 1.5 cm of their outsides.
OUTER_REACH_M = 0.015
OUTER_BAND_M = 0.004
SMOOTH_ROUNDS = 3
ONE_SURFACE = ("hard", "skin")  # roles drawn in one surface: a rigid part, bare skin
COMPONENTS = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def library_surfaces():
    """{library surface: its spec}, every variant in its own token (the people place's own list of materials in
    place.json was retired, 2026-10-21)."""
    folder = str(REPO / "tools/props/library")
    if folder not in sys.path:
        sys.path.append(folder)
    import library
    return library.by_library(LINE)


def read_glb(path):
    data = pathlib.Path(path).read_bytes()
    length = struct.unpack("<I", data[12:16])[0]
    return json.loads(data[20:20 + length]), data[20 + length:]


def write_glb(path, document, rest):
    """The glTF with its JSON chunk replaced and its binary chunk as it was."""
    text = json.dumps(document, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<I", len(text)) + b"JSON" + text + rest
    pathlib.Path(path).write_bytes(b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body)


def accessor(document, rest, accessor_index):
    """An accessor's values from the binary chunk (rest: its chunk header included), one row a value."""
    blob = rest[8:8 + struct.unpack("<I", rest[:4])[0]]
    found = document["accessors"][accessor_index]
    view = document["bufferViews"][found["bufferView"]]
    start = view.get("byteOffset", 0) + found.get("byteOffset", 0)
    width = WIDTHS[found["type"]]
    return np.frombuffer(blob, COMPONENTS[found["componentType"]], found["count"] * width, start).reshape(-1, width)


def positions(document, rest, accessor_index):
    """An accessor's float32 VEC3 values from the binary chunk (rest: its chunk header included)."""
    return accessor(document, rest, accessor_index).astype(np.float64)


def outer_labels(points, normals, painted_points, painted_names, reach, band):
    """Each point's surface on the take's outer skin: the most common among the painted samples within `reach` that
    lie within `band` of the outermost along the point's normal; the nearest sample's where none is that near."""
    from scipy.spatial import cKDTree
    tree = cKDTree(painted_points)
    labels = painted_names[tree.query(points)[1]]
    for number, near in enumerate(tree.query_ball_point(points, reach)):
        if not near:
            continue
        near = np.asarray(near)
        along = (painted_points[near] - points[number]) @ normals[number]
        names, counts = np.unique(painted_names[near[along >= along.max() - band]], return_counts=True)
        labels[number] = names[counts.argmax()]
    return labels


def smoothed_labels(labels, faces, rounds=SMOOTH_ROUNDS):
    """Each point's label replaced by the most common among itself and its neighbours along `faces`, `rounds` times."""
    kinds, numbers = np.unique(labels, return_inverse=True)
    edges = faces[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2)
    for _ in range(rounds):
        votes = np.zeros((len(labels), len(kinds)))
        np.add.at(votes, (np.arange(len(labels)), numbers), 1.0)
        np.add.at(votes, (edges[:, 0], numbers[edges[:, 1]]), 1.0)
        np.add.at(votes, (edges[:, 1], numbers[edges[:, 0]]), 1.0)
        numbers = votes.argmax(1)
    return kinds[numbers]


def triangle_labels(labels, faces):
    """Each triangle's label: the most common of its corners'."""
    kinds, numbers = np.unique(labels, return_inverse=True)
    votes = np.zeros((len(faces), len(kinds)))
    for corner in range(3):
        np.add.at(votes, (np.arange(len(faces)), numbers[faces[:, corner]]), 1.0)
    return kinds[votes.argmax(1)]


def surfaces_of(labels, faces, role):
    """Each triangle's painted surface: one for a hard or skin part (its points' most), else its own."""
    if role in ONE_SURFACE:
        names, counts = np.unique(labels[np.unique(faces)], return_counts=True)
        return np.full(len(faces), names[counts.argmax()])
    return triangle_labels(smoothed_labels(labels, faces), faces)


class Binary:
    """The glTF's binary chunk, with index lists appended as new accessors."""

    def __init__(self, document, rest):
        self.document = document
        self.length = struct.unpack("<I", rest[:4])[0]
        self.blob = bytearray(rest[8:8 + self.length])
        self.after = rest[8 + self.length:]

    def indices(self, faces):
        """A new accessor holding `faces` as unsigned ints: its number."""
        self.blob += b"\x00" * (-len(self.blob) % 4)
        data = faces.astype(np.uint32).ravel()
        self.document["bufferViews"].append({"buffer": 0, "byteOffset": len(self.blob), "byteLength": data.nbytes,
                                             "target": 34963})
        self.blob += data.tobytes()
        self.document["accessors"].append({"bufferView": len(self.document["bufferViews"]) - 1,
                                           "componentType": 5125, "count": len(data), "type": "SCALAR",
                                           "max": [int(data.max())], "min": [int(data.min())]})
        return len(self.document["accessors"]) - 1

    def rest(self):
        """The binary chunk with its header, as read_glb hands it."""
        self.blob += b"\x00" * (-len(self.blob) % 4)
        self.document["buffers"][0]["byteLength"] = len(self.blob)
        return struct.pack("<I", len(self.blob)) + b"BIN\x00" + bytes(self.blob) + self.after


def handed_on(inputs, look):
    """The look's folder and entry as people-made@people handed it on; Blocked with the loop's gap when it made the
    look none."""
    handed = pathlib.Path(inputs[f"{bodies.MADE}@{bodies.LINE}"])
    bodies.refused_on_gap(handed, look)
    return handed, json.loads((handed / "made.json").read_text())[look]


def painted_take(inputs, look):
    """The look's labelled take the loop's bake painted."""
    handed, entry = handed_on(inputs, look)
    return handed / entry["labelled"]


def outfit_node(document):
    """The body's own skinned mesh node, not its far body's: the route names it `work` whatever the look's outfit
    (tools/characters/maker/route_build.py NODE), a far-only build names it for its outfit."""
    found = [node for node in document["nodes"] if "mesh" in node and "skin" in node and node.get("name") != "far"]
    if len(found) != 1:
        raise RuntimeError(f"the body has {len(found)} skinned outfit nodes, not one")
    return found[0]


def shaded(material, spec):
    """The material in the library surface's colour (a print keeps its picture), roughness and metalness."""
    shading = material.setdefault("pbrMetallicRoughness", {})
    if not material.get("extras", {}).get("print"):
        shading["baseColorFactor"] = [float(value) for value in spec["colour"][:3]] + [1.0]
    shading["roughnessFactor"] = float(spec.get("roughness", 0.85))
    shading["metallicFactor"] = float(spec.get("metal", 0.0))


class Painted:
    """The look's painted take in the finished model's frame and the rig that lays the body's bind points into it."""

    def __init__(self, take, rig):
        with np.load(take) as stored:
            self.points = stored["low"] + stored["points"].astype(np.float64) / 65535 * (
                stored["high"] - stored["low"])
            self.names = stored["names"][stored["surface"]]
        self.turn, self.scale, self.shift = rig["turn"], float(rig["scale"]), rig["shift"]

    def finished(self, points):
        return ((points - self.shift) / self.scale) @ self.turn

    def labels(self, points, normals):
        """The points' (at the bind) outer surfaces (outer_labels) and their distances to the take in metres."""
        from scipy.spatial import cKDTree
        turned = normals @ self.turn
        turned /= np.maximum(np.linalg.norm(turned, axis=1, keepdims=True), 1e-12)
        finished = self.finished(points)
        labels = outer_labels(finished, turned, self.points, self.names, OUTER_REACH_M / self.scale,
                              OUTER_BAND_M / self.scale)
        return labels, cKDTree(self.points).query(finished)[0] * self.scale


def worn_name(painted_name, material, surfaces, params):
    """The library surface a part painted `painted_name` wears: `params["surface"]` (a worn row, `-in-<surface>`:
    score/stages/people_clothes.py) on every fabric but a print, else the paint's."""
    if params.get("surface") and surfaces.get(painted_name, {}).get("family") == "fabric" and \
            not material.get("extras", {}).get("print"):
        return params["surface"]
    return painted_name


def dressed_primitives(document, rest, primitives, painted, surfaces, params):
    """(the outfit's primitives split by the surface painted on their triangles, each on a material in its library
    surface, the binary chunk with their index lists, {material key: its record entry})."""
    binary, originals = Binary(document, rest), [json.loads(json.dumps(found)) for found in document["materials"]]
    # a material's points are measured together: the route's under layer lies under its garment, off the take
    chosen, record, out, distances = {}, {}, [], {}
    for primitive in primitives:
        number = primitive["material"]
        extras = originals[number].get("extras", {})
        role, attributes = extras.get("role"), primitive["attributes"]
        points = positions(document, rest, attributes["POSITION"])
        normals = positions(document, rest, attributes["NORMAL"]) if "NORMAL" in attributes else np.zeros_like(points)
        labels, apart = painted.labels(points, normals)
        if role == "hair" or extras.get("print"):  # the hair's own route (owner, 2026-10-11); the face's picture
            record[f"{originals[number]['name']}#{number}"] = {
                "library": None, "route": "hair" if role == "hair" else "print", "role": role, "known": True,
                "median_m": round(float(np.median(apart)), 4)}
            out.append(primitive)
            continue
        faces = accessor(document, rest, primitive["indices"]).reshape(-1, 3).astype(np.int64)
        per_triangle = surfaces_of(labels, faces, role)
        kinds = np.unique(per_triangle)
        for painted_name in kinds:
            mine = faces[per_triangle == painted_name]
            name = worn_name(str(painted_name), originals[number], surfaces, params)
            if (number, name) not in chosen:
                taken = any(material == number for material, _ in chosen)
                if taken:
                    document["materials"].append(json.loads(json.dumps(originals[number])))
                chosen[(number, name)] = len(document["materials"]) - 1 if taken else number
            target = chosen[(number, name)]
            spec = surfaces.get(name)
            key = f"{originals[number]['name']}#{target}"
            distances[key] = np.concatenate([distances.get(key, np.zeros(0)), apart[np.unique(mine)]])
            record[key] = {"library": name, "median_m": round(float(np.median(distances[key])), 4), "role": role,
                           "known": spec is not None, "painted": str(painted_name)}
            if spec is not None:
                document["materials"][target].setdefault("extras", {})["library"] = name
                shaded(document["materials"][target], spec)
            out.append(dict(primitive, material=target, **(
                {"indices": binary.indices(mine)} if len(kinds) > 1 else {})))
    return out, binary.rest(), record


def make_dress(inputs, out, seed, params):
    """The dressed body.glb, its usd/ and dress.json (each surface's library surface and its median distance). With
    `params["surface"]` (a worn row, `-in-<surface>`: score/stages/people_clothes.py) every fabric surface of the outfit
    but a print wears that library surface instead of the paint's."""
    name, body = next((name, pathlib.Path(path)) for name, path in inputs.items() if name.startswith("people-body-"))
    look = json.loads((body / "look.json").read_text())
    look_name = name.removeprefix("people-body-")
    painted = Painted(painted_take(inputs, look_name), np.load(body / "rig.npz"))
    surfaces = {**library_surfaces(), **handed_on(inputs, look_name)[1]["specs"]}
    document, rest = read_glb(body / "body.glb")
    mesh = document["meshes"][outfit_node(document)["mesh"]]
    mesh["primitives"], rest, found = dressed_primitives(document, rest, mesh["primitives"], painted, surfaces,
                                                         params)
    write_glb(out / "body.glb", document, rest)
    done = subprocess.run([sys.executable, str(REPO / "tools/characters/skel_usd.py"), str(out / "body.glb"), "--out",
                           str(out / "usd")], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"skel_usd.py failed: {done.stderr[-2000:]}")
    shutil.copy2(body / "look.json", out / "look.json")
    (out / "dress.json").write_text(json.dumps({"take": look["take"], "outfit": look["outfit"], "surfaces": found},
                                               indent=1))


def dress_faults(folder):
    missing = [name for name in ("body.glb", "dress.json", "look.json") if not (folder / name).exists()]
    return [f"missing {', '.join(missing)}"] if missing else []


def judge_dressed(output, inputs, evidence):
    from score.checks import FAIL, PASS, Verdict
    found = json.loads((output / "dress.json").read_text())["surfaces"]
    failing = [f"{name}: {entry['library']} is no people library surface" for name, entry in found.items()
               if not entry["known"]]
    return Verdict("dressed", FAIL if failing else PASS, "; ".join(failing) or f"all {len(found)} surfaces dressed",
                   {"failing": len(failing)}, {"failing": "lower"}, tuple(failing))


def judge_aligned(output, inputs, evidence):
    from score.checks import FAIL, PASS, Verdict
    found = json.loads((output / "dress.json").read_text())["surfaces"]
    failing = [f"{name}: {entry['median_m']} m from the painted take" for name, entry in found.items()
               if entry["median_m"] > ALIGNED_MOST]
    worst = max(entry["median_m"] for entry in found.values())
    return Verdict("aligned", FAIL if failing else PASS, "; ".join(failing) or f"worst median {worst} m",
                   {"failing": len(failing), "worst_m": worst}, {"failing": "lower"}, tuple(failing))
