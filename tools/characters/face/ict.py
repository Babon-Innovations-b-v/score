"""ICT-FaceKit's face model (#226), fetched at a pinned commit and kept as one packed file in a capped cache.

ICT-FaceKit (USC Institute for Creative Technologies, MIT licence, github.com/ICT-VGL/ICT-FaceKit at `COMMIT`): one
topology of 26,719 points (the face, head and neck, mouth and eye sockets, gums and tongue, teeth, eyeballs, lacrimal
fluid, eye blend and occlusion, eyelashes; `PIECES`), its 100 identity modes and 53 expressions named as ARKit's, each
an OBJ of the whole mesh. `pack` reads them once into `model.npz` (the neutral points, its polygons fanned into
triangles with their UV corners, the identity and expression offsets as float32) and removes the OBJs; the cache is
the packed file alone, under `cache_root()`, removed whole when its commit is no longer the pinned one.
"""
import json
import os
import pathlib
import shutil
import urllib.request

import numpy as np

COMMIT = "da5f95a607f5e6b37755b38d3385d7f2853732e5"
SOURCE = f"https://raw.githubusercontent.com/ICT-VGL/ICT-FaceKit/{COMMIT}/FaceXModel/"
IDENTITIES = 100
# The model's pieces by their first and last point (README's topology table, inclusive), in the model's order.
PIECES = {"face": (0, 9408), "head_and_neck": (9409, 11247), "mouth_socket": (11248, 13293),
          "eye_socket_left": (13294, 13677), "eye_socket_right": (13678, 14061), "gums_and_tongue": (14062, 17038),
          "teeth": (17039, 21450), "eyeball_left": (21451, 23020), "eyeball_right": (23021, 24590),
          "lacrimal_left": (24591, 24794), "lacrimal_right": (24795, 24998), "eye_blend_left": (24999, 25022),
          "eye_blend_right": (25023, 25046), "occlusion_left": (25047, 25198), "occlusion_right": (25199, 25350),
          "lashes_left": (25351, 26034), "lashes_right": (26035, 26718)}
NARROW_FACE = 6705  # the last point of the narrow face area (README's face area table)


def cache_root():
    """Where the packed model lives: SCORE_FACE_CACHE, else ~/.cache/score/ict-facekit."""
    return pathlib.Path(os.environ.get("SCORE_FACE_CACHE", pathlib.Path.home() / ".cache/score/ict-facekit"))


def read_obj(path):
    """An OBJ's points, its UVs and its polygons' point and UV corners fanned into triangles."""
    points, uvs, triangles, corners = [], [], [], []
    for line in pathlib.Path(path).read_text().splitlines():
        if line.startswith("v "):
            points.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("vt "):
            uvs.append([float(value) for value in line.split()[1:3]])
        elif line.startswith("f "):
            ends = [corner.split("/") for corner in line.split()[1:]]
            for index in range(1, len(ends) - 1):
                trio = (ends[0], ends[index], ends[index + 1])
                triangles.append([int(end[0]) - 1 for end in trio])
                corners.append([int(end[1]) - 1 if len(end) > 1 and end[1] else -1 for end in trio])
    return (np.array(points), np.array(uvs).reshape(-1, 2), np.array(triangles, dtype=np.int64),
            np.array(corners, dtype=np.int64))


def read_points(path):
    """An OBJ's points alone."""
    return np.array([[float(value) for value in line.split()[1:4]]
                     for line in pathlib.Path(path).read_text().splitlines() if line.startswith("v ")])


def fetch(name, folder):
    """One file of the model at the pinned commit into `folder`."""
    target = folder / name
    with urllib.request.urlopen(SOURCE + name, timeout=120) as answer, target.open("wb") as out:
        shutil.copyfileobj(answer, out)
    return target


def pack():
    """Fetch the pinned model, pack it into the cache's model.npz, drop its OBJs and any other commit's cache."""
    root = cache_root()
    for stale in root.glob("*"):
        if stale.name != COMMIT:
            shutil.rmtree(stale) if stale.is_dir() else stale.unlink()
    folder = root / COMMIT
    folder.mkdir(parents=True, exist_ok=True)
    names = json.loads(fetch("vertex_indices.json", folder).read_text())
    neutral, uvs, triangles, corners = read_obj(fetch("generic_neutral_mesh.obj", folder))
    offsets = {}
    for kind, names_of_kind in (("identity", [f"identity{index:03d}" for index in range(IDENTITIES)]),
                                ("expression", names["expressions"])):
        stacked = []
        for name in names_of_kind:
            obj = fetch(f"{name}.obj", folder)
            stacked.append((read_points(obj) - neutral).astype(np.float32))
            obj.unlink()
        offsets[kind] = np.stack(stacked)
    (folder / "generic_neutral_mesh.obj").unlink()
    np.savez_compressed(folder / "model.npz", neutral=neutral, uvs=uvs, triangles=triangles, corners=corners,
                        identities=offsets["identity"], expressions=offsets["expression"],
                        expression_names=np.array(names["expressions"]),
                        landmarks=np.array(names["idx_to_landmark_verts"]))
    (folder / "vertex_indices.json").unlink()
    return folder / "model.npz"


def load():
    """The packed model, packed first when the cache does not hold the pinned commit's."""
    packed = cache_root() / COMMIT / "model.npz"
    return dict(np.load(packed if packed.exists() else pack()))


if __name__ == "__main__":
    model = load()
    print(f"ICT-FaceKit {COMMIT[:8]}: {len(model['neutral'])} points, {len(model['identities'])} identities, "
          f"{len(model['expressions'])} expressions -> {cache_root() / COMMIT / 'model.npz'}")
