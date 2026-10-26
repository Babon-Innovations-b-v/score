"""A moving body's collision as convex parts, so a hollow (a crate, a tray, a bin, a shelf) stays hollow: one convex hull
spans it, and what is dropped into an open crate rests on its hull's top (0.62 m) instead of its floor. The settle
stage (score/stages/settling) writes a drop's hollow objects' parts beside the stage it drops (FILE), which the drop
(../blender/inside/settle_stage.py) reads; kept out of settle.py and colliders.py, which sit in many rows' code, so a
change here moves the settle row alone.

    hollow_parts(stage, place, loose, cache)
                                  ({name: parts} for the loose objects whose mesh is not as good as one hull,
                                  {name: why} for those CoACD failed on, which drop as their one hull)
    convex_parts(meshes, cache)   ({name: [part corners, ...]} for {name: (points, triangles)}, each part a convex
                                  hull's corners in the mesh's own frame: CoACD's parts, or the mesh's one hull when
                                  they are as good as it; worked out once per mesh and kept in `cache`; {name: why}
                                  for a mesh CoACD failed on or ran past DECOMPOSE_SECONDS for, given its one hull
                                  and kept nowhere, so the next run tries it again)

CoACD (Wei, Liu, Lin, Sun, Wang and Lin, "Approximate Convex Decomposition for 3D Meshes with Collision-Aware Concavity
and Tree Search", SIGGRAPH 2022; MIT, pip coacd) is called as SimFoundry's _coacd_runner calls it: each part a hull of
at most PART_CORNERS corners, in a process of its own (a crash or a hang of the solver ends that process, not the
caller), one hull when the parts hold ONE_HULL of the hull's volume. About 13 s of one core for an open crate.

    .venv/bin/python tools/usd/convex_parts.py decompose <mesh.npz> <parts.json>   (convex_parts runs it)
"""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
import trimesh
from pxr import UsdGeom

# Beside a stage the drop is given (its folder goes to the drop's machine whole): its hollow objects' parts, which
# ../blender/inside/settle_stage.py reads (PARTS_FILE there).
FILE = "convex-parts.json"
# CoACD's max_ch_vertex, which only its decimate step keeps, and its seed.
PART_CORNERS = 60
SEED = 0
DECOMPOSE_SECONDS = 900
# Parts holding this share of the mesh's one hull's volume are that hull (the mesh is as good as convex): one hull.
ONE_HULL = (0.95, 1.05)
# What a kept decomposition was made with: a change here is a new key, never a stale read.
METHOD = f"coacd 1.0.14 max_ch_vertex={PART_CORNERS} decimate seed={SEED} one_hull={ONE_HULL}"


def hollow_parts(stage, place, loose, cache):
    """{name: [part corners, ...]} for each loose object (names under /<place>/Objects) whose drawn mesh is not as good
    as one convex hull (a crate, a tray, a bin, a shelf): its convex parts in the mesh's own frame, which the drop
    glues to it as bodies of their own, so what drops into its hollow meets its floor, not its hull's top; and
    {name: why} for each one CoACD failed on, which drops as its one hull (as before parts)."""
    meshes = {}
    for name in loose:
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{place}/Objects/{name}/geo"))
        meshes[name] = (np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64),
                        np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64).reshape(-1, 3))
    found, unsplit = convex_parts(meshes, cache)
    return {name: parts for name, parts in sorted(found.items()) if len(parts) > 1}, unsplit


def mesh_key(points, triangles):
    """A mesh's identity for the decomposition kept of it: its corners, its triangles and the method."""
    digest = hashlib.sha256(METHOD.encode())
    digest.update(np.ascontiguousarray(points, dtype=np.float32).tobytes())
    digest.update(np.ascontiguousarray(triangles, dtype=np.int64).tobytes())
    return digest.hexdigest()


def convex_parts(meshes, cache):
    """({name: [part corners, ...]}, {name: why}) for {name: (points, triangles)}, each part a convex hull's corners
    in the mesh's own frame: the mesh's one hull when CoACD's parts are as good as it (ONE_HULL), else the parts. A
    mesh's parts are read from `cache` (a folder, by mesh_key) once worked out; the meshes not yet kept are worked out
    side by side, one process each and at most one a core, and the same mesh (a library model laid many times) once.
    A mesh CoACD fails on or runs past DECOMPOSE_SECONDS for gets its one hull, kept nowhere, and its why: one model
    never fails the drop (a convex 82k-triangle sphere took 335 s of one core, 2026-10-26)."""
    cache = pathlib.Path(cache)
    keys = {name: mesh_key(points, triangles) for name, (points, triangles) in meshes.items()}
    missing = {key: meshes[name] for name, key in keys.items() if not (cache / f"{key}.json").exists()}
    failed = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(len(missing), os.cpu_count() or 1))) as pool:
        for key, (parts, why) in zip(missing, pool.map(lambda mesh: tried(*mesh), missing.values())):
            if why is None:
                kept(cache / f"{key}.json", parts)
            else:
                failed[key] = (parts, why)
    found = {name: failed[key][0] if key in failed else json.loads((cache / f"{key}.json").read_text())
             for name, key in keys.items()}
    return found, {name: failed[key][1] for name, key in keys.items() if key in failed}


def tried(points, triangles):
    """(the mesh's parts, None), or (its one hull, why) when CoACD failed on it or ran past DECOMPOSE_SECONDS."""
    try:
        return decomposed(points, triangles), None
    except subprocess.TimeoutExpired:
        why = f"CoACD ran past {DECOMPOSE_SECONDS} s"
    except subprocess.CalledProcessError as error:
        why = f"CoACD failed (exit {error.returncode})"
    return [one_hull(points)], f"{why}: dropped as its one hull"


def one_hull(points):
    """The corners of the mesh's one convex hull, rounded as kept parts are."""
    corners = trimesh.convex.convex_hull(np.asarray(points, dtype=np.float64)).vertices
    return np.round(np.asarray(corners, dtype=np.float64), 6).tolist()


def kept(path, parts):
    """Write the parts whole or not at all (a reader never meets half a file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_suffix(".writing")
    scratch.write_text(json.dumps(parts))
    scratch.replace(path)


def decomposed(points, triangles):
    """The mesh's convex parts (CoACD in its own process), or its one hull when they are as good as it."""
    with tempfile.TemporaryDirectory() as temporary:
        given, found = pathlib.Path(temporary) / "mesh.npz", pathlib.Path(temporary) / "parts.json"
        np.savez(given, points=np.asarray(points, dtype=np.float64), triangles=np.asarray(triangles, dtype=np.int64))
        subprocess.run([sys.executable, "-I", __file__, "decompose", str(given), str(found)], check=True,
                       timeout=DECOMPOSE_SECONDS, stdout=subprocess.DEVNULL)
        parts = [np.asarray(part, dtype=np.float64) for part in json.loads(found.read_text())]
    whole = trimesh.convex.convex_hull(np.asarray(points, dtype=np.float64))
    share = sum(trimesh.convex.convex_hull(part).volume for part in parts) / whole.volume
    chosen = [whole.vertices] if ONE_HULL[0] <= share <= ONE_HULL[1] else parts
    return [np.round(np.asarray(part, dtype=np.float64), 6).tolist() for part in chosen]


def coacd_parts(given, found):
    """Inside its own process (decomposed): CoACD's parts of the mesh in `given` (npz), as corners, into `found`."""
    import coacd
    coacd.set_log_level("error")
    data = np.load(given)
    welded = trimesh.Trimesh(data["points"], data["triangles"].reshape(-1, 3), process=True)
    parts = coacd.run_coacd(coacd.Mesh(np.asarray(welded.vertices), np.asarray(welded.faces)),
                            max_ch_vertex=PART_CORNERS, decimate=True, seed=SEED)
    pathlib.Path(found).write_text(json.dumps([np.asarray(corners).tolist() for corners, _ in parts]))


if __name__ == "__main__":
    if sys.argv[1:2] != ["decompose"] or len(sys.argv) != 4:
        raise SystemExit(__doc__)
    coacd_parts(sys.argv[2], sys.argv[3])
