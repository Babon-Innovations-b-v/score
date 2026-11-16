"""Runs in the physics trial's own Python (score/stages/physics/inside/newton_env.sh: MuJoCo as pinned there, the one
sim body's walkers run in): each loose object of a place let go where it is laid, in MuJoCo, against what is near it.

    <env>/bin/python score/stages/place_build/ready/settle_mujoco.py <job.npz> <out.json>

job.npz: for each loose object `<n>`, `hull_<n>` (its points, metres, y up: MuJoCo collides it by their convex hull),
`statics_<n>` (the triangles, (count, 3, 3), of everything else near it: the ground, shells, walls and the other
objects) and `names` (the objects in order). Each object is its own small model built as an mjSpec (a free body of its
hull; each static triangle a thin plate of STATIC_SKIN, so an open shell or a terrain is a real surface, not its
hull), the models side by side in a process pool: one model an object, so a hollow cabinet's hull never meets the
suit stored inside it (what an object holds is left out of its statics by the caller). Each is stepped SECONDS under
gravity; out.json: {name: {"moved": metres its middle moved, "turned": degrees it turned, "depth": the deepest contact
at the start (metres, MuJoCo's contact dist: negative is inside), "contacts": contacts at the end}, "engine": ...}.
"""
import json
import multiprocessing
import pathlib
import sys

import mujoco
import numpy as np

SECONDS = 1.0
STEP = 0.002
GRAVITY = 9.81
FRICTION = 0.9
DENSITY = 400.0  # kg a cubic metre: a crate, a cabinet; the rest pose does not depend on it
# Each static triangle's plate is this thick (metres), half each side of its face: thicker than a fall moves in one
# step (6 m/s, a 2 m drop, is 12 mm a step), so nothing passes through a plate between two steps; a piece laid on a
# face starts 1 cm inside its plate and is pushed up that far, well under the check's few cm.
STATIC_SKIN = 0.02
SMALLEST = 1e-8  # a static triangle with less area (square metres) is no surface
# Each model's arena (bytes) for its contacts and constraints: MuJoCo's default sizes it from the model alone, and a
# hull resting on a dense made model's plates (a TRELLIS.2 desk, 2026-11-16: 10,935 contacts) ran past it with
# "mj_stackAlloc: out of memory"; 64 MB holds over 150,000 contacts, eight pool processes 0.5 GB.
ARENA = 64 * 1024 * 1024


def plates(triangles):
    """Each triangle as the six corners of a plate STATIC_SKIN thick across it; degenerate triangles left out."""
    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    areas = np.linalg.norm(normals, axis=1)
    kept = areas > 2 * SMALLEST
    unit = normals[kept] / areas[kept, None]
    offset = unit[:, None, :] * (STATIC_SKIN / 2)
    return np.concatenate([triangles[kept] + offset, triangles[kept] - offset], axis=1)


def model_of(hull, statics):
    """The mjSpec of one loose object (a free body, its hull's middle its origin) among its static plates, compiled;
    the hull's middle."""
    spec = mujoco.MjSpec()
    spec.option.gravity = [0.0, -GRAVITY, 0.0]
    spec.option.timestep = STEP
    spec.memory = ARENA
    middle = hull.mean(axis=0)
    spec.add_mesh(name="loose", uservert=(hull - middle).ravel().tolist())
    body = spec.worldbody.add_body(name="loose", pos=middle.tolist())
    body.add_freejoint()
    body.add_geom(type=mujoco.mjtGeom.mjGEOM_MESH, meshname="loose", density=DENSITY, contype=1, conaffinity=0,
                  friction=[FRICTION, 0.005, 0.0001])
    for number, corners in enumerate(plates(statics)):
        spec.add_mesh(name=f"plate{number}", uservert=corners.ravel().tolist(),
                      inertia=mujoco.mjtMeshInertia.mjMESH_INERTIA_SHELL)
        spec.worldbody.add_geom(type=mujoco.mjtGeom.mjGEOM_MESH, meshname=f"plate{number}", contype=0, conaffinity=1,
                                friction=[FRICTION, 0.005, 0.0001])
    return spec.compile()


def turned_degrees(start, end):
    """The angle (degrees) between two unit quaternions (w, x, y, z)."""
    return float(np.degrees(2 * np.arccos(min(1.0, abs(float(np.dot(start, end)))))))


def settled(item):
    """One object let go: how far it moved and turned, its deepest contact at the start, its contacts at the end."""
    name, hull, statics = item
    model = model_of(hull, statics)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    depth = float(min((data.contact[index].dist for index in range(data.ncon)), default=0.0))
    start_pos, start_turn = data.xpos[1].copy(), data.xquat[1].copy()
    for _ in range(int(SECONDS / STEP)):
        mujoco.mj_step(model, data)
    return name, {"moved": float(np.linalg.norm(data.xpos[1] - start_pos)),
                  "turned": turned_degrees(start_turn, data.xquat[1]), "depth": depth, "contacts": int(data.ncon)}


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    job = np.load(sys.argv[1])
    items = [(str(name), job[f"hull_{name}"], job[f"statics_{name}"]) for name in job["names"]]
    with multiprocessing.Pool(min(8, max(1, len(items)))) as pool:
        found = dict(pool.map(settled, items))
    pathlib.Path(sys.argv[2]).write_text(json.dumps({"objects": found, "engine": f"mujoco {mujoco.__version__}"}))


if __name__ == "__main__":
    main()
