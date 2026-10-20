"""The people's dress rows: `people-dress-<look>` (free, world) lays the look's finish from the shared loop on its built
body (#41). Each surface of the body (a part of its outfit, as the build named it) takes the library surface the
loop's bake painted on the most of its points: its points at the bind laid back into the finished model's frame (the
rig's stand undone) and each read off the nearest painted sample of the take (its labelled take, handed on by the
people's after-step, people-made@people: loop.py). The glTF's material takes that surface's colour, roughness and
metalness from the library (data/library, the people place's tokens) and names it in `extras.library`; the face print
keeps its picture. The UsdSkel asset is written again from the dressed glTF (tools/characters/skel_usd.py). The
library recipe's own detail (bump, quilting) is not baked onto a person yet: the colour, roughness and metalness are
the library surface's, nothing else is a picture's. A look the loop made no model for is blocked with its gap.

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


def library_surfaces():
    """{library surface: its spec} the people place allows."""
    folder = str(REPO / "tools/props/library")
    if folder not in sys.path:
        sys.path.append(folder)
    import library
    return library.resolved(LINE)


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


def positions(document, rest, accessor_index):
    """An accessor's float32 VEC3 values from the binary chunk (rest: its chunk header included)."""
    blob = rest[8:8 + struct.unpack("<I", rest[:4])[0]]
    found = document["accessors"][accessor_index]
    view = document["bufferViews"][found["bufferView"]]
    start = view.get("byteOffset", 0) + found.get("byteOffset", 0)
    return np.frombuffer(blob, np.float32, found["count"] * 3, start).reshape(-1, 3).astype(np.float64)


def surface_of_points(points, painted_points, painted_names):
    """The library surface most of the points' nearest painted samples carry, and their median distance."""
    from scipy.spatial import cKDTree
    distance, nearest = cKDTree(painted_points).query(points)
    names, counts = np.unique(painted_names[nearest], return_counts=True)
    return str(names[counts.argmax()]), float(np.median(distance))


def painted_take(inputs, look):
    """The look's labelled take the loop's bake painted, as people-made@people handed it on; Blocked with the loop's
    gap when it made the look none."""
    handed = pathlib.Path(inputs[f"{bodies.MADE}@{bodies.LINE}"])
    bodies.refused_on_gap(handed, look)
    return handed / json.loads((handed / "made.json").read_text())[look]["labelled"]


def make_dress(inputs, out, seed, params):
    """The dressed body.glb, its usd/ and dress.json (each surface's library surface and its median distance). With
    `params["surface"]` (a coloured place's row, data/people/colours.json) every fabric surface of the outfit but a
    print wears that library surface instead of the paint's."""
    name, body = next((name, pathlib.Path(path)) for name, path in inputs.items() if name.startswith("people-body-"))
    look = json.loads((body / "look.json").read_text())
    rig = np.load(body / "rig.npz")
    turn, scale, shift = rig["turn"], float(rig["scale"]), rig["shift"]
    with np.load(painted_take(inputs, name.removeprefix("people-body-"))) as stored:
        painted = stored["low"] + stored["points"].astype(np.float64) / 65535 * (stored["high"] - stored["low"])
        painted_names = stored["names"][stored["surface"]]
    surfaces = library_surfaces()
    document, rest = read_glb(body / "body.glb")
    outfit = next(node for node in document["nodes"] if node.get("name") == look["outfit"] and "mesh" in node)
    record = {"take": look["take"], "outfit": look["outfit"], "surfaces": {}}
    for primitive in document["meshes"][outfit["mesh"]]["primitives"]:
        material = document["materials"][primitive["material"]]
        points = positions(document, rest, primitive["attributes"]["POSITION"])
        finished = ((points - shift) / scale) @ turn
        name, apart = surface_of_points(finished, painted, painted_names)
        role = material.get("extras", {}).get("role")
        if role == "hair":  # hair stays on its own route (owner, 2026-10-11): the build's colour, no library paint
            record["surfaces"][material["name"]] = {"library": None, "route": "hair", "role": role, "known": True,
                                                    "median_m": round(apart * scale, 4)}
            continue
        painted_name = name
        if params.get("surface") and surfaces.get(name, {}).get("family") == "fabric" and \
                not material.get("extras", {}).get("print"):
            name = params["surface"]
        spec = surfaces.get(name)
        record["surfaces"][material["name"]] = {"library": name, "median_m": round(apart * scale, 4), "role": role,
                                                "known": spec is not None, "painted": painted_name}
        if spec is None:
            continue
        material.setdefault("extras", {})["library"] = name
        shading = material.setdefault("pbrMetallicRoughness", {})
        if not material["extras"].get("print"):
            shading["baseColorFactor"] = [float(value) for value in spec["colour"][:3]] + [1.0]
        shading["roughnessFactor"] = float(spec.get("roughness", 0.85))
        shading["metallicFactor"] = float(spec.get("metallic", 0.0))
    write_glb(out / "body.glb", document, rest)
    done = subprocess.run([sys.executable, str(REPO / "tools/characters/skel_usd.py"), str(out / "body.glb"), "--out",
                           str(out / "usd")], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"skel_usd.py failed: {done.stderr[-2000:]}")
    shutil.copy2(body / "look.json", out / "look.json")
    (out / "dress.json").write_text(json.dumps(record, indent=1))


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
