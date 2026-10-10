"""A labelled model's parts kept in the repository (`data/parts`): what each part of a generated model is painted
with, small enough to commit, for whatever lays the model again later (the OpenUSD export's part subsets).

    ~/.farm-factory-props/env/bin/python tools/props/library/stored_parts.py <labelled folder> [<name>]

labels.py writes a labelled take as one .ply per library material, about a million faces and 35 MB a take: the bake's
input, kept under the work folder. Stored here is a sample of it: STORED_POINTS points spread over the surface by
area, each with the material of the face it lies on, in the labelled folder's own frame (the finished model's),
quantised to 16 bits over the model's box (a fifteen-thousandth of the box: under 0.2 mm on a 2.4 m take).
`data/parts/<take>.npz` holds `points` (uint16, n x 3), `low` and `high` (the box), `surface` (uint8 per point) and
`names` (the library material of each surface number). `data/parts/models.json` says which take each place's made
model was painted from ({place: {model: take}}).
Where a take's .ply files are gone, its parts were sampled the same way from an accepted stage's own subsets (the
street's water barriers, `*-b`, from usd-r2-final, 2026-10-10; export reproduces them within 1 to 2% per surface).
"""
import json
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from paths import REPO  # noqa: E402

STORED = REPO / "data/parts"
INDEX = "models.json"
STORED_POINTS = 40_000
LEVELS = 65535


def sampled(folder):
    """STORED_POINTS points over the labelled folder's materials by area; (points, surface number, names)."""
    meshes = {path.stem: trimesh.load(path, force="mesh", process=False) for path in sorted(folder.glob("*.ply"))}
    if not meshes:
        raise ValueError(f"{folder}: no labelled materials")
    total = sum(mesh.area for mesh in meshes.values())
    names = sorted(meshes)
    points, surfaces = [], []
    for number, name in enumerate(names):
        count = max(1, int(round(STORED_POINTS * meshes[name].area / total)))
        found, _ = trimesh.sample.sample_surface(meshes[name], count, seed=number)
        points.append(found)
        surfaces.append(np.full(len(found), number, dtype=np.uint8))
    return np.vstack(points), np.concatenate(surfaces), names


def write(folder, name, target=STORED):
    """The labelled folder stored as <target>/<name>.npz; its path."""
    points, surfaces, names = sampled(pathlib.Path(folder))
    low, high = points.min(axis=0), points.max(axis=0)
    quantised = np.round((points - low) / np.maximum(high - low, 1e-9) * LEVELS).astype(np.uint16)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{name}.npz"
    np.savez_compressed(path, points=quantised, low=low, high=high, surface=surfaces, names=np.array(names))
    return path


def read(path):
    """A stored take: (points in the labelled frame, the library material of each point)."""
    with np.load(path) as stored:
        points = stored["low"] + stored["points"].astype(np.float64) / LEVELS * (stored["high"] - stored["low"])
        return points, stored["names"][stored["surface"]]


def kit_frame(points, turn, size):
    """Points of a labelled take in the kit frame its made model stands in: turned by the kind's `turn` and fitted to
    its laid `size` on the middle of its foot, as the route's make_chunky does."""
    points = points @ np.asarray(turn).reshape(3, 3).T
    low, high = points.min(axis=0), points.max(axis=0)
    foot = np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])
    return (points - foot) * (np.asarray(size, dtype=np.float64) / (high - low))


def takes_of(place, target=STORED):
    """Each of a place's made models' stored take ({model: path of its .npz}), from the index."""
    index = target / INDEX
    named = json.loads(index.read_text()).get(place, {}) if index.exists() else {}
    return {model: target / f"{take}.npz" for model, take in named.items()}


if __name__ == "__main__":
    labelled = pathlib.Path(sys.argv[1])
    print(write(labelled, sys.argv[2] if len(sys.argv) > 2 else labelled.name))
