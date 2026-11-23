"""The benchmark's close-up frames each asset whole in the close-up style (turned and looking down, or straight above
when it lies flat), lays it on the grey backdrop while its RGBA keeps the true alpha, refuses a render whose box
slipped, gives both routes the material class its words or its kind name, and keeps every route step as a store object with its blobs in the bucket: a failing step is its branch's
gap, the steps after it are not run, and a run taken up again runs no kept step twice.

Breaks that turn this red (each applied once and seen red, then reverted):
- bench.view_of: MARGIN left out of `reach` -> the box's outermost corner lands on the frame's edge, not inside it
- bench.view_of: LOOK_DOWN_DEGREES for every row, not check.look_down -> the tray is not seen from straight above
- bench.on_backdrop: the alpha left out (the render's RGB alone) -> the backdrop comes out black, not BACKDROP
- bench.material_for: a CLASS_WORDS word matched whole only -> the wooden tray is given plastic, not wood
- bench.render_asset: the box check dropped -> the render Blender laid in centimetres is kept
- bench.Kept.keep: the bucket push dropped -> the step's blobs are not in the bucket
- bench.run_steps: the gap's `return` dropped -> the step after a failing one runs
- bench.run_steps: a kept step not skipped -> taking the run up again makes the raw model twice
"""
import json
import math

import numpy as np
import pytest
from PIL import Image

import bench
from score.store import Store
from score.store.offload import FolderBucket

# id, its set kind, the class the routes are given, true box (low, high) in metres Z up, lies flat, the scale
# Blender's box comes back at, the route step that fails
ROWS = [
    ("simready_crate_blue_a01", "crate", "plastic", ([-0.3, -0.2, 0.0], [0.3, 0.2, 0.25]), False, 1.0, None),
    ("simready_utensil_serving_tray_wooden_b01", "tray (flat)", "wood", ([-0.14, -0.22, 0.0], [0.14, 0.22, 0.06]),
     True, 1.0, "finished"),
    ("simready_storage_locker_double_bench_b01", "cabinet / locker", "steel", ([0.0, 0.0, 0.0], [0.5, 0.5, 1.9]),
     False, 1.0, "raw"),
    ("simready_box_cardboard_a02", "box", "paper", ([-0.3, -0.2, 0.0], [0.3, 0.2, 0.25]), False, 100.0, None),
]
PIXELS = 64


def projected(view, point):
    """Where `point` lands in the frame, -1 to 1 at its edges: a pinhole camera worked out here, apart from bench."""
    eye, aim = np.asarray(view["eye"]), np.asarray(view["aim"])
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(forward, view["up"])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    offset = np.asarray(point) - eye
    depth = offset @ forward
    half = math.tan(math.radians(view["fov"]) / 2)
    return offset @ right / depth / half, offset @ up / depth / half


def usd_box(path, low, high):
    """A Z-up stage in metres holding one box mesh from `low` to `high`."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    mesh = UsdGeom.Mesh.Define(stage, "/box")
    mesh.CreatePointsAttr([(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    mesh.CreateFaceVertexCountsAttr([4] * 6)
    mesh.CreateFaceVertexIndicesAttr([0, 1, 3, 2, 4, 6, 7, 5, 0, 4, 5, 1, 2, 3, 7, 6, 0, 2, 6, 4, 1, 5, 7, 3])
    stage.Save()


def drawer(scale):
    """A stand-in for Blender: the object a red square with its true alpha; its shadow a half-dark band below it."""
    def draw(_job_name, arguments, log):
        root, job, out = arguments
        job = json.loads(open(job).read())
        from pathlib import Path
        out = Path(out)
        out.mkdir(parents=True)
        rgba = np.zeros((PIXELS, PIXELS, 4), np.uint8)
        rgba[16:40, 16:48] = (200, 0, 0, 255)
        Image.fromarray(rgba, "RGBA").save(out / "rgba.png")
        shadow = rgba.copy()
        shadow[40:48, 16:48] = (0, 0, 0, 128)
        Image.fromarray(shadow, "RGBA").save(out / "shadow.png")
        low, high, _ = bench.true_box(root)
        (out / "report.json").write_text(json.dumps({"box": [[side * scale for side in low],
                                                             [side * scale for side in high]], "job": job}))
        Path(log).write_text("drawn\n")
        return 0
    return draw


@pytest.mark.parametrize("name, kind, material, box, flat, scale, failing", ROWS)
def test_every_asset_is_framed_whole_and_every_step_kept(tmp_path, monkeypatch, name, kind, material, box, flat, scale,
                                                         failing):
    set_file = tmp_path / "set.json"
    set_file.write_text(json.dumps({"objects": [{"address": f"model/{name}@1", "kind": kind, "split": "tune"}]}))
    [row] = bench.read_set(set_file)
    assert (row["id"], bench.material_for(row)) == (name, material)
    low, high = box
    usd_box(tmp_path / f"{name}.usda", low, high)
    monkeypatch.setattr(bench, "fetched", lambda address, values, into: (
        {"title": name, "tags": {"description": ["a thing"]}}, tmp_path / f"{name}.usda"))
    monkeypatch.setattr(bench, "SIZE", PIXELS)
    bucket = FolderBucket(tmp_path / "bucket")
    kept = bench.Kept(Store.in_folder(tmp_path / "store"), bucket, tmp_path / "index.json")
    bench.render_all([row], {}, kept, "trial", drawer(scale))

    found = kept.entry(name, "input", "render")
    if scale != 1.0:
        assert "gap" in found and "off" in found["gap"], found
        return
    folder = kept.store.checkout(found["output"])
    for sha in set(kept.store.listing(found["output"]).values()):
        assert (tmp_path / "bucket" / f"blobs/{sha}").is_file(), sha
    given = json.loads((folder / "row.json").read_text())
    assert given["lies_flat"] is flat and given["words"] == f"{name} a thing"
    assert np.allclose(given["size"], np.subtract(high, low), atol=1e-4)
    view = given["camera"]
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    seen = np.abs([projected(view, corner) for corner in corners])
    assert seen.max() == pytest.approx(1 - bench.MARGIN, abs=1e-6), seen.max()  # whole, and as near as it can be
    looking = np.subtract(view["eye"], view["aim"])
    rise = math.degrees(math.asin(looking[2] / np.linalg.norm(looking)))
    turn = math.degrees(math.atan2(looking[0], -looking[1]))
    assert (rise, turn if not flat else 0.0) == pytest.approx((90.0, 0.0) if flat else (15.0, 35.0), abs=1e-6)

    laid = np.asarray(Image.open(folder / "closeup.png"))
    assert laid.shape[2] == 3 and tuple(laid[2, 2]) == bench.BACKDROP and tuple(laid[20, 20]) == (200, 0, 0)
    assert laid[44, 30].sum() < sum(bench.BACKDROP)  # its shadow darker than the backdrop
    alpha = np.asarray(Image.open(folder / "rgba.png"))[..., 3]
    assert alpha[20, 20] == 255 and alpha[44, 30] == 0  # the true alpha holds no shadow

    made = []

    def step(label):
        def make(out):
            made.append(label)
            if label == failing:
                raise bench.StepFailed(f"{label} made nothing")
            (out / f"{label}.txt").write_text(label)
        return make
    steps = [(label, step(label)) for label in ("raw", "finished", "straight")]
    for _ in range(2):  # the run, then the run taken up again
        bench.run_steps(kept, name, "A", steps, tmp_path / "scratch")
    order = ["raw", "finished", "straight"]
    expected = order[:order.index(failing) + 1] if failing else order
    assert made == expected
    for label in order:
        entry = kept.entry(name, "A", label)
        if failing and order.index(label) > order.index(failing):
            assert entry is None
        elif label == failing:
            assert "made nothing" in entry["gap"]
        else:
            assert (kept.store.checkout(entry["output"]) / f"{label}.txt").read_text() == label
