"""Check a moving body's convex parts (tools/usd/convex_parts.py) on shapes made here: an open crate is split round its
hollow, a box is its one hull, both are read back from the cache without CoACD, and a laid crate gets its parts in its
own frame.

Run: .venv/bin/python tools/usd/convex_parts_test.py   (make tests runs it with the framework's environment)
"""
import pathlib
import sys
import tempfile

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import convex_parts  # noqa: E402


def open_crate():
    """A 1 m crate with no lid: a floor and four walls 0.6 m high, 4 cm thick."""
    move = trimesh.transformations.translation_matrix
    sides = [trimesh.creation.box(extents=(1.0, 0.04, 0.8), transform=move((0, 0.02, 0)))]
    sides += [trimesh.creation.box(extents=(0.04, 0.6, 0.8), transform=move((x, 0.3, 0))) for x in (-0.48, 0.48)]
    sides += [trimesh.creation.box(extents=(1.0, 0.6, 0.04), transform=move((0, 0.3, z))) for z in (-0.38, 0.38)]
    return trimesh.util.concatenate(sides)


def a_hollow_keeps_its_hollow_and_a_box_is_one_hull():
    """An open crate is split into convex parts, none filling its hollow (none holds the point over its floor's
    middle, halfway up); a box is its one hull, its 8 corners; and both are read back from the cache without CoACD."""
    crate, box = open_crate(), trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    meshes = {"crate": (crate.vertices, crate.faces), "box": (box.vertices, box.faces)}
    with tempfile.TemporaryDirectory() as temporary:
        found, unsplit = convex_parts.convex_parts(meshes, temporary)
        real = convex_parts.decomposed
        convex_parts.decomposed = lambda *mesh: (_ for _ in ()).throw(AssertionError("CoACD ran for a kept mesh"))
        try:
            again, _ = convex_parts.convex_parts(meshes, temporary)
        finally:
            convex_parts.decomposed = real
    problems = [] if again == found else ["the kept parts read back differently"]
    problems += [f"CoACD failed: {unsplit}"] if unsplit else []
    if len(found["box"]) != 1 or len(found["box"][0]) != 8:
        problems.append(f"the box is {len(found['box'])} parts, not its one hull of 8 corners")
    if len(found["crate"]) < 5:
        problems.append(f"the open crate is {len(found['crate'])} parts, not split round its hollow")
    middle = np.array([[0.0, 0.3, 0.0]])
    filling = [number for number, part in enumerate(found["crate"])
               if trimesh.convex.convex_hull(np.asarray(part)).contains(middle)[0]]
    return problems + ([f"crate parts {filling} fill its hollow"] if filling else [])


def a_laid_hollow_object_gets_its_parts_in_its_own_frame():
    """On an exported place, an open crate laid loose gets its convex parts, in its drawn mesh's own frame (inside
    the crate's own box, wherever it is laid); a laid box, as good as its one hull, gets none (it drops as before)."""
    import resting_test
    from pxr import Usd
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        resting_test.export_test.box_gltf(folder / "models", "crate", open_crate())
        path = resting_test.laid_place(folder, [("crate", "crate", (2, 0, 1)), ("block", "box", (5, 0, 0))],
                                       [("crate", "floor"), ("block", "floor")])
        stage = Usd.Stage.Open(str(path))
        found, _ = convex_parts.hollow_parts(stage, resting_test.PLACE, ["crate_1", "block_1"], folder / "cache")
    problems = [] if set(found) == {"crate_1"} else [f"parts were given to {sorted(found)}, not the crate alone"]
    corners = np.concatenate([np.asarray(part) for part in found.get("crate_1", [[[0, 0, 0]]])])
    if np.any(corners.min(axis=0) < [-0.51, -0.01, -0.41]) or np.any(corners.max(axis=0) > [0.51, 0.61, 0.41]):
        problems.append(f"the crate's parts reach {corners.min(axis=0)} to {corners.max(axis=0)}, past its own frame")
    return problems


def a_mesh_coacd_fails_on_drops_as_its_one_hull_and_is_tried_again():
    """A mesh CoACD runs past its time for (or fails on) gets its one hull and its why, and nothing is kept, so the
    next run tries it again; the other meshes keep their parts. Break: let the timeout raise (the whole settle row
    failed on one slow model) or keep the one hull in the cache (never tried again)."""
    import subprocess
    crate, box = open_crate(), trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    meshes = {"crate": (crate.vertices, crate.faces), "box": (box.vertices, box.faces)}
    real = convex_parts.decomposed

    def slow(points, triangles):
        if len(points) == len(crate.vertices):
            raise subprocess.TimeoutExpired("coacd", convex_parts.DECOMPOSE_SECONDS)
        return real(points, triangles)

    with tempfile.TemporaryDirectory() as temporary:
        convex_parts.decomposed = slow
        try:
            found, unsplit = convex_parts.convex_parts(meshes, temporary)
        finally:
            convex_parts.decomposed = real
        kept = sorted(path.name for path in pathlib.Path(temporary).iterdir())
    problems = [] if set(unsplit) == {"crate"} and "one hull" in unsplit["crate"] else [f"told: {unsplit}"]
    hull = trimesh.convex.convex_hull(crate.vertices).vertices
    if len(found["crate"]) != 1 or len(found["crate"][0]) != len(hull):
        problems.append(f"the crate is {len(found['crate'])} parts, not its one hull")
    if len(kept) != 1:
        problems.append(f"kept {kept}: the box's parts alone, never the failed crate's hull")
    return problems


CHECKS = (a_hollow_keeps_its_hollow_and_a_box_is_one_hull, a_laid_hollow_object_gets_its_parts_in_its_own_frame,
          a_mesh_coacd_fails_on_drops_as_its_one_hull_and_is_tried_again)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
