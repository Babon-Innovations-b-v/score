"""The people's dress rows: `people-dress-<look>` (paid, world) lays the look's finish from the shared loop on its built
body (#41) and bakes it there, as every model is finished. The body's points at the bind are laid back into the
finished model's frame (the rig's stand undone) and each reads the library surface the loop's bake painted on the
take's outer surface there (its labelled take, handed on by the people's after-step, people-made@people: loop.py): of
the painted samples within OUTER_REACH_M, those within OUTER_BAND_M of the outermost along the point's normal vote
(`outer_labels`). The take keeps the inside faces Pixal3D grew (71% of the astronaut's faces no view saw, each painted
from its nearest seen face), and the nearest sample alone read the boots' insides as the grey suit, 2026-10-22. A
garment is split where its triangles' surfaces change, its labels smoothed over its edges first (a material drawn in
two surfaces took the one most of its points carried, and the brown overalls' chest and hips showed the grey:
astronaut, 2026-10-22); a hard part, the skin, the hair and each far-body part take one surface, the one most of its
area wears (counted by points, the astronaut's helmet front, 53% of its area the visor, took the grey its dense rim
carried and the visor was 0.02% of the body, 2026-10-23): the face and hair wear the library surface the finish route
gave the take there, never a picture (the close-up's face print is gone, owner 2026-10-23: "this didnt use our prop
pipeline and materials"). Each glTF material names its
surface in `extras.library` (the bake's name, its settings in it) and `extras.surface` (the library variant). Then
the body is baked (baked_body.py: the library recipes with the people palette's wear and dirt on the bake's rented
card, their maps laid into body.glb, the build's own pictures dropped) and the bake checked as the surface stage
checks one (bake_check.py). The UsdSkel asset is written again from the baked glTF (tools/characters/skel_usd.py).
A look the loop made no model for is blocked with its gap.

Gates: `dressed` (every material of the body names a known library surface and reads the baked maps: a flat factor
fails), `aligned` (the body's points lie on the painted take: the median distance to the nearest painted sample
within ALIGNED_MOST; the far body, a coarse stand-in, is not measured) and `baked` (bake_check's faults of the
bake: off its library surface, off the close-up, blotches, one grey look, an order reversed).
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
ONE_SURFACE = ("hard", "skin", "hair", "far")  # roles drawn in one surface: a rigid part, skin, hair, a far part
UNMEASURED = ("far",)  # roles the aligned gate leaves out: the far body is a coarse stand-in, never on the take
EUROS = 0.5  # the bake's card job (baked_body.MINUTES on an L4 with its setup); no measured run yet
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


def surfaces_of(labels, faces, role, points):
    """Each triangle's painted surface: one for a hard or skin part (the one most of its area wears), else its own."""
    if role in ONE_SURFACE:
        per_triangle = triangle_labels(labels, faces)
        corners = points[faces]
        areas = np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=1)
        names, numbers = np.unique(per_triangle, return_inverse=True)
        return np.full(len(faces), names[np.bincount(numbers, weights=areas).argmax()])
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


def dressed_meshes(document):
    """The body's meshes the dress lays: its outfit's (outfit_node) and its far body's, when it has one."""
    far = [node["mesh"] for node in document["nodes"] if "mesh" in node and "skin" in node and node.get("name") == "far"]
    return [outfit_node(document)["mesh"], *far]


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


def worn_name(painted_name, surfaces, params):
    """The library surface a part painted `painted_name` wears: `params["surface"]` (a worn row, `-in-<surface>`:
    score/stages/people_clothes.py) on every fabric, else the paint's."""
    if params.get("surface") and surfaces.get(painted_name, {}).get("family") == "fabric":
        return params["surface"]
    return painted_name


def named(material, name, spec):
    """The material naming its library surface: `extras.library` the bake's name, `extras.surface` its variant; the
    build's own picture flag (a face print) dropped."""
    extras = material.setdefault("extras", {})
    extras.pop("print", None)
    extras["library"], extras["surface"] = name, spec.get("library", name)


def dressed_primitives(document, rest, primitives, painted, surfaces, params):
    """(the mesh's primitives split by the surface painted on their triangles, each on a material naming its library
    surface, the binary chunk with their index lists, {material key: its record entry})."""
    binary, originals = Binary(document, rest), [json.loads(json.dumps(found)) for found in document["materials"]]
    # a material's points are measured together: the route's under layer lies under its garment, off the take
    chosen, record, out, distances = {}, {}, [], {}
    for primitive in primitives:
        number = primitive["material"]
        role, attributes = originals[number].get("extras", {}).get("role"), primitive["attributes"]
        points = positions(document, rest, attributes["POSITION"])
        normals = positions(document, rest, attributes["NORMAL"]) if "NORMAL" in attributes else np.zeros_like(points)
        labels, apart = painted.labels(points, normals)
        faces = accessor(document, rest, primitive["indices"]).reshape(-1, 3).astype(np.int64)
        per_triangle = surfaces_of(labels, faces, role, points)
        kinds = np.unique(per_triangle)
        for painted_name in kinds:
            mine = faces[per_triangle == painted_name]
            name = worn_name(str(painted_name), surfaces, params)
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
                named(document["materials"][target], name, spec)
            out.append(dict(primitive, material=target, **(
                {"indices": binary.indices(mine)} if len(kinds) > 1 else {})))
    return out, binary.rest(), record


def bake_head(inputs, specs):
    """The bake job's head (surfaces/bake_job.job_head: the route's near density, its seed) at the people palette's
    wear and dirt (finish-route-palette@people with its surface library, palette_library.wear)."""
    from score.stages.people import baked_body  # noqa: F401  (puts the surface stage's modules on the path)
    import bake_job
    import palette_library
    palette = palette_library.read({"finish-route-palette": inputs[f"finish-route-palette@{LINE}"],
                                    palette_library.ROW: inputs[f"{palette_library.ROW}@{LINE}"]})
    return bake_job.job_head(palette_library.wear(palette), specs)


def make_dress(inputs, out, seed, params):
    """The dressed and baked body.glb, its usd/, bake.log and dress.json (each surface's library surface and its
    median distance, and the bake's check). With `params["surface"]` (a worn row, `-in-<surface>`:
    score/stages/people_clothes.py) every fabric surface of the outfit wears that library surface instead of the
    paint's."""
    from score.stages.people import baked_body
    name, body = next((name, pathlib.Path(path)) for name, path in inputs.items() if name.startswith("people-body-"))
    look = json.loads((body / "look.json").read_text())
    look_name = name.removeprefix("people-body-")
    painted = Painted(painted_take(inputs, look_name), np.load(body / "rig.npz"))
    surfaces = {**library_surfaces(), **handed_on(inputs, look_name)[1]["specs"]}
    document, rest = read_glb(body / "body.glb")
    found = {}
    for number in dressed_meshes(document):
        mesh = document["meshes"][number]
        mesh["primitives"], rest, laid = dressed_primitives(document, rest, mesh["primitives"], painted, surfaces,
                                                            params)
        found.update(laid)
    write_glb(out / "body.glb", document, rest)
    work = out / ".bake"
    labelled = pathlib.Path(inputs[f"surfaces-bake@{LINE}"]) / "labelled" / look["take"]
    checked = baked_body.bake(out / "body.glb", surfaces, bake_head(inputs, {}), labelled, work)
    shutil.copy2(work / "bake.log", out / "bake.log")
    shutil.rmtree(work)
    done = subprocess.run([sys.executable, str(REPO / "tools/characters/skel_usd.py"), str(out / "body.glb"), "--out",
                           str(out / "usd")], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"skel_usd.py failed: {done.stderr[-2000:]}")
    shutil.copy2(body / "look.json", out / "look.json")
    (out / "dress.json").write_text(json.dumps({"take": look["take"], "outfit": look["outfit"], "surfaces": found,
                                                "bake": checked}, indent=1))


def dress_faults(folder):
    missing = [name for name in ("body.glb", "dress.json", "look.json") if not (folder / name).exists()]
    return [f"missing {', '.join(missing)}"] if missing else []


def flat_materials(document):
    """The materials the body's meshes are drawn in that read no baked maps (base colour, metal and roughness,
    normal) or name no library surface, by name and number."""
    used = sorted({primitive["material"] for mesh in document["meshes"] for primitive in mesh["primitives"]})
    found = []
    for number in used:
        material = document["materials"][number]
        shading = material.get("pbrMetallicRoughness", {})
        maps = ("baseColorTexture" in shading, "metallicRoughnessTexture" in shading, "normalTexture" in material)
        if not all(maps) or not material.get("extras", {}).get("library"):
            found.append(f"{material.get('name')}#{number}")
    return found


def judge_dressed(output, inputs, evidence):
    """Every surface of the body a known library surface, and every material it is drawn in reading the baked
    library maps: a flat factor with no maps fails."""
    from score.checks import FAIL, PASS, Verdict
    found = json.loads((output / "dress.json").read_text())["surfaces"]
    failing = [f"{name}: {entry['library']} is no people library surface" for name, entry in found.items()
               if not entry["known"]]
    failing += [f"{name}: flat factors, no baked library maps"
                for name in flat_materials(read_glb(output / "body.glb")[0])]
    return Verdict("dressed", FAIL if failing else PASS, "; ".join(failing) or
                   f"all {len(found)} surfaces dressed and baked", {"failing": len(failing)}, {"failing": "lower"},
                   tuple(failing))


def judge_baked(output, inputs, evidence):
    """The bake's faults as the surface stage's check finds them (baked_body.checked, bake_check.surface_faults)."""
    from score.checks import FAIL, PASS, Verdict
    checked = json.loads((output / "dress.json").read_text())["bake"]
    worst = max(entry["delta_e"] for entry in checked["surfaces"].values())
    return Verdict("baked", FAIL if checked["faults"] else PASS, "; ".join(checked["faults"]) or
                   f"{len(checked['surfaces'])} surfaces baked on their library colour, worst dE {worst}",
                   {"failing": len(checked["faults"]), "worst_delta_e": worst}, {"failing": "lower"},
                   tuple(checked["faults"]))


def judge_aligned(output, inputs, evidence):
    from score.checks import FAIL, PASS, Verdict
    found = {name: entry for name, entry in json.loads((output / "dress.json").read_text())["surfaces"].items()
             if entry["role"] not in UNMEASURED}
    failing = [f"{name}: {entry['median_m']} m from the painted take" for name, entry in found.items()
               if entry["median_m"] > ALIGNED_MOST]
    worst = max(entry["median_m"] for entry in found.values())
    return Verdict("aligned", FAIL if failing else PASS, "; ".join(failing) or f"worst median {worst} m",
                   {"failing": len(failing), "worst_m": worst}, {"failing": "lower"}, tuple(failing))
