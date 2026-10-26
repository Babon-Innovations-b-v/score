"""The settle's drop of a hollow piece (tools/blender/inside/settle_stage.py with tools/usd/convex_parts.py's parts) in
Blender 5.0.1, laid 36 m from the world's origin: an open crate stays where it is laid, and a box laid at its rim comes
to rest on its floor, not on its hull's top. Its parts weighed at the world's origin once threw such a crate 276 m
(2026-10-26); laid at the origin it moved 1 cm, which is why the crate here is laid far from it.

It runs Blender through tools/blender/session.py's batch (the machine's lock, a private screen): 17 s with the fix,
71 s and a failure without it (2026-10-26). With no Blender 5.0.1 set up under PROPS_HOME or no Xvfb (bash
tools/blender/setup.sh) it says so and passes nothing: it prints `skipped` and ends 0.

Run: .venv/bin/python tools/usd/test_a_hollow_piece_drops_as_its_parts_far_from_the_origin.py
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
sys.path.insert(0, str(HERE.parent / "blender"))
import convex_parts  # noqa: E402
import convex_parts_test  # noqa: E402
import resting_test  # noqa: E402
import session  # noqa: E402
import settle  # noqa: E402

# Where the crate is laid (stage frame, y up): far from the origin, where a part weighed at the origin is thrown.
FAR = (30.0, 0.0, 20.0)
# The crate may settle this much as it beds onto the ground (metres, degrees); thrown, it moved 276 m and 165 degrees.
CRATE_DRIFT, CRATE_TURN = 0.05, 1.0
# The box's middle at rest over the ground (metres): on the crate's floor (4 cm) it is 0.14; on the hull's top, 0.72.
BOX_MIDDLE_MOST = 0.2
# Speed at the end (metres a second): settle.py's own still test.
STILL = 0.01


def small_box():
    """A 0.2 m box standing on its foot."""
    box = trimesh.creation.box(extents=(0.2, 0.2, 0.2))
    box.apply_translation((0.0, 0.1, 0.0))
    return box


def dropped(folder):
    """The open crate laid FAR, a box laid at its rim and stacked on it, their parts written beside the stage, dropped:
    the drop's record and the laid stage's path."""
    from pxr import Usd
    resting_test.made_models(folder)
    resting_test.export_test.box_gltf(folder / "models", "crate", convex_parts_test.open_crate())
    resting_test.export_test.box_gltf(folder / "models", "small", small_box())
    rim = (FAR[0], 0.62, FAR[2])
    path = resting_test.laid_place(folder, [("crate", "crate", FAR), ("block", "small", rim)],
                                   [("crate", "floor"), ("block", "floor")])
    stage = Usd.Stage.Open(str(path))
    hollow, _ = convex_parts.hollow_parts(stage, resting_test.PLACE, ["crate_1", "block_1"], folder / "cache")
    (path.parent / convex_parts.FILE).write_text(json.dumps(hollow))
    found = settle.simulate(path, {"crate_1": 0.0, "block_1": 0.0}, folder / "drop", under={"block_1": ["crate_1"]})
    return found, path, sorted(hollow)


def rest_of(found, path, name):
    """An object's middle as laid and at rest (stage frame) and how far it turned (degrees)."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(path))
    laid = settle_matrix(stage, name)
    motion = np.asarray(found["objects"][name]["motion"])
    middle = np.append(settle.object_middle(stage, resting_test.PLACE, name), 1.0)
    turn = motion[:3, :3]
    turned = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(turn) - 1.0) / 2.0))))
    return (laid @ middle)[:3], (motion @ laid @ middle)[:3], turned


def settle_matrix(stage, name):
    from pxr import Usd, UsdGeom
    prim = stage.GetPrimAtPath(f"/{resting_test.PLACE}/Objects/{name}")
    return np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T


def a_crate_laid_far_from_the_origin_stays_and_holds_a_box_on_its_floor():
    """Break: weigh each part at the world's origin (convex_pieces' meshes in world corners, no matrix_world) and
    the crate is thrown; put a joint's pivot at the origin and it tilts and sinks; drop it as one hull and the box
    rests on the hull's top at 0.72."""
    with tempfile.TemporaryDirectory() as temporary:
        found, path, hollow = dropped(pathlib.Path(temporary))
        problems = [] if hollow == ["crate_1"] else [f"parts were given to {hollow}, not the crate alone"]
        laid, rest, turned = rest_of(found, path, "crate_1")
        drift = float(np.linalg.norm(rest - laid))
        if drift > CRATE_DRIFT or turned > CRATE_TURN:
            problems.append(f"the crate moved {drift:.3f} m and turned {turned:.2f} degrees from where it was laid")
        _, box, _ = rest_of(found, path, "block_1")
        if box[1] > BOX_MIDDLE_MOST or abs(box[0] - FAR[0]) > 0.5 or abs(box[2] - FAR[2]) > 0.5:
            problems.append(f"the box rests with its middle at {box.round(3).tolist()}, not on the crate's floor")
        moving = {name: item["moving"] for name, item in found["objects"].items() if item["moving"] > STILL}
        if moving:
            problems.append(f"still moving at the end: {moving}")
        return problems


CHECKS = (a_crate_laid_far_from_the_origin_stays_and_holds_a_box_on_its_floor,)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    import shutil
    if not (session.RUNTIME / f"blender-{session.DEFAULT_VERSION}" / "blender").exists() or not shutil.which("Xvfb"):
        print(f"skipped: no Blender {session.DEFAULT_VERSION} under {session.RUNTIME}, or no Xvfb "
              "(bash tools/blender/setup.sh)")
        sys.exit(0)
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
