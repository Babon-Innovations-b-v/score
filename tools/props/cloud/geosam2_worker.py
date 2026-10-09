"""Runs on a rented machine: GeoSAM2 (VAST-AI-Research/GeoSAM2 at a pinned commit, code and weights Apache-2.0) over
our own Pixal3D models, seeded with the clean close-up's finish regions (job parts-test, 2026-10-09).

    cd /root/gs/GeoSAM2 && /root/gs/venv/bin/python geosam2_worker.py <in folder> <out folder> <blender>

Each <in>/<take>/ holds mesh.glb (the raw model cut to 150,000 faces, its box centred, its longest side 1, turned so
its close-up side faces GeoSAM2's first view: ../library/split_compare.py) and seed_points.npz (the full model's face
centres in that frame and each face's close-up region + 1, 0 where the close-up does not see it). Per take: GeoSAM2's own Blender script renders its twelve views (EEVEE under a virtual
display), the seed is laid on the first view (each pixel's surface point from its depth, the region of the nearest
face), GeoSAM2's inference propagates it round the views and lifts it to faces (its defaults: the opposite view
segmented automatically, labels completed with PA 0.02). <out>/<take>/geosam2.npz: `middles` (the face centres of the
model as GeoSAM2 loads it) and `labels` (each face's part, 0 unlabelled), and geosam2_timing.json.
"""
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

sys.path.insert(0, str(pathlib.Path.cwd()))
from utils.inference_utils import gen_pcd, load_mesh_with_faces  # noqa: E402

# Samples per view in EEVEE: the views only feed GeoSAM2 their depth and normals.
RENDER_SAMPLES = "16"
# Blender's frame from a glTF's: x stays, y is the glTF's -z, z its y.
FROM_GLTF = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]])
# How far (of the model's longest side, 1) a seed pixel's surface point may lie from the nearest face centre.
SEED_GAP = 0.01


def render(blender, mesh, folder):
    """GeoSAM2's twelve views of the model (geosam2_render.py, as its README runs it), under a virtual display."""
    environment = dict(os.environ, RENDER_SAMPLES=RENDER_SAMPLES)
    done = subprocess.run(["xvfb-run", "-a", "-s", "-screen 0 1280x1024x24", blender, "-b", "-P", "geosam2_render.py",
                           str(mesh), "glb", str(folder)], env=environment, capture_output=True, text=True)
    if not (folder / "meta.json").exists():
        raise SystemExit(f"render failed:\n{done.stdout[-3000:]}\n{done.stderr[-3000:]}")


def seed(folder, middles, region_of_face):
    """The seed label map on the first view: each object pixel takes the region of the full model's face whose centre
    (`middles`) is nearest its surface point; the median gap, checked against SEED_GAP."""
    meta = json.loads((folder / "meta.json").read_text())
    depth = cv2.imread(str(folder / "depth_0000.exr"), cv2.IMREAD_UNCHANGED)[..., 0]
    points = gen_pcd(depth, np.array(meta["transforms"][0]), meta["camera_angle_x"])
    valid = depth < 65500.0
    in_model = ((points[valid] - np.array(meta["translation"])) / meta["scaling_factor"]) @ FROM_GLTF
    gap, nearest = cKDTree(middles).query(in_model)
    if np.median(gap) > SEED_GAP:
        raise SystemExit(f"the first view's points miss the model: median gap {np.median(gap):.4f}")
    found = np.zeros(depth.shape, dtype=np.int32)
    found[valid] = region_of_face[nearest]
    return found, float(np.median(gap))


def segment(folder, seed_path, out):
    """GeoSAM2's inference with the seed on view 0, its defaults otherwise; the final labels file."""
    done = subprocess.run([sys.executable, "inference.py", "--data-root", str(folder), "--mask-path", str(seed_path),
                           "--mask-view", "0", "--output-dir", str(out)], capture_output=True, text=True)
    (out / "inference.log").write_text(done.stdout[-20000:] + "\n" + done.stderr[-20000:])
    found = sorted(out.rglob("segmentation_postprocessed_*.npy"), key=lambda path: path.stat().st_mtime)
    if done.returncode or not found:
        raise SystemExit(f"inference failed ({done.returncode}): {done.stderr[-3000:]}")
    return np.load(found[-1]).reshape(-1)


def one_take(blender, take_in, take_out):
    """Render, seed, segment one take; the seconds each step took and the seed's gap."""
    take_out.mkdir(parents=True, exist_ok=True)
    views, seconds = take_out / "views", {}
    began = time.time()
    render(blender, take_in / "mesh.glb", views)
    seconds["render"] = round(time.time() - began, 1)
    began = time.time()
    points = np.load(take_in / "seed_points.npz")
    seed_map, seconds["seed_gap"] = seed(views, points["middles"], points["regions"])
    np.save(take_out / "seed.npy", seed_map)
    labels = segment(views, take_out / "seed.npy", take_out / "result")
    middles = load_mesh_with_faces(str(take_in / "mesh.glb"))[0].triangles_center
    if len(middles) != len(labels):
        raise SystemExit(f"{len(labels)} labels for {len(middles)} faces")
    np.savez_compressed(take_out / "geosam2.npz", middles=middles.astype(np.float32), labels=labels.astype(np.int32))
    seconds["segment"] = round(time.time() - began, 1)
    return seconds


def main():
    source, out, blender = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
    failed = []
    for take_in in sorted(path for path in source.iterdir() if (path / "mesh.glb").exists()):
        try:
            seconds = one_take(blender, take_in, out / take_in.name)
        except (Exception, SystemExit):  # noqa: BLE001 - written down and reported below; the other takes still run
            (out / take_in.name).mkdir(parents=True, exist_ok=True)
            (out / take_in.name / "geosam2_error.txt").write_text(traceback.format_exc())
            failed.append(take_in.name)
            continue
        (out / take_in.name / "geosam2_timing.json").write_text(json.dumps(seconds))
        print(take_in.name, json.dumps(seconds), flush=True)
    if failed:
        raise SystemExit(f"GeoSAM2 failed on {', '.join(failed)}")


if __name__ == "__main__":
    main()
