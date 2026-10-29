"""tools/usd/convex_parts.py, a moving body's convex parts, on shapes made here: an open crate is split round its
hollow, a box is its one hull, both are read back from the cache without CoACD, a laid crate gets its parts in its
own frame, a mesh CoACD fails on drops as its one hull, and the drop of an open crate laid far from the origin in
Newton (score/stages/settling/inside/settle_drop.py, through tools/usd/drop.py in the physics trial's Python) keeps it
where it is laid with a box on its floor, and a body of 100 parts drops with room for their contacts. With no built
trial Python under PROPS_HOME (bash score/stages/physics/inside/newton_env.sh $PROPS_HOME/envs/newton_env), as in
`make tests`' sandbox home, those two drop checks print `skipped` and pass nothing.

Breaks that turn each test red (each applied once and seen red):
- a_hollow_keeps_its_hollow_and_a_box_is_one_hull (2026-10-27): convex_parts.decomposed's `chosen = [whole.vertices]
  if ONE_HULL[0] <= share <= ONE_HULL[1] else parts` made `chosen = [whole.vertices]`.
- a_laid_hollow_object_gets_its_parts_in_its_own_frame (2026-10-27): convex_parts.hollow_parts's `if len(parts) > 1`
  made `>= 1` (a box given its one hull as parts).
- a_mesh_coacd_fails_on_drops_as_its_one_hull_and_is_tried_again (2026-10-27): convex_parts.convex_parts's `if why is
  None:` made `if True:` (a failed mesh's hull kept, never tried again).
- a_crate_laid_far_from_the_origin_stays_and_holds_a_box_on_its_floor (2026-10-27, with the trial's Python under a
  real PROPS_HOME, on this PC's card: 42 s fixed, 46 s and red broken): settle_drop's `hull(piece - middle)` made
  `hull(piece)` (each part laid on the body at its place in the world, 36 m from the body's middle).
- a_body_of_many_parts_drops_with_room_for_their_contacts (2026-10-29, on this PC's card, 64 s for the file fixed):
  settle_drop's `self.room = CONTACTS * shapes` made `self.room = 64 * len(self.bodies)` (the room by bodies: "the
  drop met 64 contacts").

Run: .venv/bin/python tools/usd/test_a_hollow_body_keeps_its_hollow.py   (make tests runs it)
"""
import json
import math
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
    import test_floating_sunk_and_tipping_objects_are_told_apart as resting_test
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
    next run tries it again; the other meshes keep their parts."""
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


# Where the dropped crate is laid (stage frame, y up): far from the origin, where a part weighed at the origin is thrown.
FAR = (30.0, 0.0, 20.0)
# The crate may settle this much as it beds onto the ground (metres, degrees); thrown, it moved 298 m and 164 degrees.
CRATE_DRIFT, CRATE_TURN = 0.05, 1.0
# The box's middle at rest over the ground (metres): on the crate's floor (4 cm) it is 0.14; on the hull's top, 0.72.
BOX_MIDDLE_MOST = 0.2
# Speed at the end (metres a second).
STILL = 0.01


def small_box():
    """A 0.2 m box standing on its foot."""
    box = trimesh.creation.box(extents=(0.2, 0.2, 0.2))
    box.apply_translation((0.0, 0.1, 0.0))
    return box


def dropped(folder):
    """The open crate laid FAR, a box laid at its rim and stacked on it, their parts written beside the stage, dropped:
    the drop's record, the laid stage and who got parts."""
    import test_floating_sunk_and_tipping_objects_are_told_apart as resting_test
    import drop
    from pxr import Usd
    resting_test.made_models(folder)
    resting_test.export_test.box_gltf(folder / "models", "crate", open_crate())
    resting_test.export_test.box_gltf(folder / "models", "small", small_box())
    path = resting_test.laid_place(folder, [("crate", "crate", FAR), ("block", "small", (FAR[0], 0.62, FAR[2]))],
                                   [("crate", "floor"), ("block", "floor")])
    stage = Usd.Stage.Open(str(path))
    hollow, _ = convex_parts.hollow_parts(stage, resting_test.PLACE, ["crate_1", "block_1"], folder / "cache")
    (path.parent / convex_parts.FILE).write_text(json.dumps(hollow))
    found = drop.simulate(path, {"crate_1": 0.0, "block_1": 0.0}, folder / "drop", under={"block_1": ["crate_1"]})
    return found, stage, sorted(hollow)


def rest_of(found, stage, name):
    """An object's middle as laid and at rest (stage frame) and how far it turned (degrees)."""
    import test_floating_sunk_and_tipping_objects_are_told_apart as resting_test
    import settle
    from pxr import Usd, UsdGeom
    laid = np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(f"/{resting_test.PLACE}/Objects/{name}"))
                      .ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T
    motion = np.asarray(found["objects"][name]["motion"])
    middle = np.append(settle.object_middle(stage, resting_test.PLACE, name), 1.0)
    turned = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(motion[:3, :3]) - 1.0) / 2.0))))
    return (laid @ middle)[:3], (motion @ laid @ middle)[:3], turned


def newton_missing():
    """Why the drop cannot run here (no trial Python built under PROPS_HOME: building it fetches its wheels), or
    None."""
    import drop
    if not list(drop.LOCAL_ENV.glob(".built-*")):
        return f"no trial Python built at {drop.LOCAL_ENV} (score/stages/physics/inside/newton_env.sh)"
    return None


def a_crate_laid_far_from_the_origin_stays_and_holds_a_box_on_its_floor():
    """In Newton, an open crate laid 36 m from the origin stays where it is laid, and a box laid at its rim rests on
    its floor, both still at the end (its break is in the file's docstring)."""
    missing = newton_missing()
    if missing:
        print(f"skipped: {a_crate_laid_far_from_the_origin_stays_and_holds_a_box_on_its_floor.__name__}: {missing}")
        return []
    with tempfile.TemporaryDirectory() as temporary:
        found, stage, hollow = dropped(pathlib.Path(temporary))
        problems = [] if hollow == ["crate_1"] else [f"parts were given to {hollow}, not the crate alone"]
        laid, rest, turned = rest_of(found, stage, "crate_1")
        drift = float(np.linalg.norm(rest - laid))
        if drift > CRATE_DRIFT or turned > CRATE_TURN:
            problems.append(f"the crate moved {drift:.3f} m and turned {turned:.2f} degrees from where it was laid")
        _, box, _ = rest_of(found, stage, "block_1")
        if box[1] > BOX_MIDDLE_MOST or abs(box[0] - FAR[0]) > 0.5 or abs(box[2] - FAR[2]) > 0.5:
            problems.append(f"the box rests with its middle at {box.round(3).tolist()}, not on the crate's floor")
        moving = {name: item["moving"] for name, item in found["objects"].items() if item["moving"] > STILL}
        return problems + ([f"still moving at the end: {moving}"] if moving else [])


def tiles(count=10, side=1.0, high=0.04):
    """A slab `side` square and `high` thick standing on y = 0, and its convex parts: count x count tiles."""
    step = side / count
    corners = [[[x0 + dx, y, z0 + dz] for dx in (0.0, step) for y in (0.0, high) for dz in (0.0, step)]
               for x0 in np.arange(count) * step - side / 2 for z0 in np.arange(count) * step - side / 2]
    slab = trimesh.creation.box(extents=(side, high, side))
    slab.apply_translation((0.0, high / 2, 0.0))
    return slab, corners


def a_body_of_many_parts_drops_with_room_for_their_contacts():
    """settle@garage and settle@airlock (2026-10-29): bodies of 50 to 157 convex parts met more contacts than a room
    sized by bodies held, and the drop failed. A slab dropped as its 100 tiles rests where it is laid."""
    missing = newton_missing()
    if missing:
        print(f"skipped: {a_body_of_many_parts_drops_with_room_for_their_contacts.__name__}: {missing}")
        return []
    import test_floating_sunk_and_tipping_objects_are_told_apart as resting_test
    import drop
    from pxr import Usd
    slab, parts = tiles()
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        resting_test.export_test.box_gltf(folder / "models", "slab", slab)
        path = resting_test.laid_place(folder, [("slab", "slab", (0.0, 0.0, 0.0))], [("slab", "floor")])
        (path.parent / convex_parts.FILE).write_text(json.dumps({"slab_1": parts}))
        try:
            found = drop.simulate(path, {"slab_1": 0.0}, folder / "drop")
        except RuntimeError as error:
            return [f"the drop failed: {error}"]
        laid, rest, turned = rest_of(found, Usd.Stage.Open(str(path)), "slab_1")
    drift = float(np.linalg.norm(rest - laid))
    return [] if drift <= CRATE_DRIFT and turned <= CRATE_TURN else [f"the slab moved {drift:.3f} m, {turned:.1f} deg"]


CHECKS = (a_hollow_keeps_its_hollow_and_a_box_is_one_hull, a_laid_hollow_object_gets_its_parts_in_its_own_frame,
          a_mesh_coacd_fails_on_drops_as_its_one_hull_and_is_tried_again,
          a_crate_laid_far_from_the_origin_stays_and_holds_a_box_on_its_floor,
          a_body_of_many_parts_drops_with_room_for_their_contacts)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
