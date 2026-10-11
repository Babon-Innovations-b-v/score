"""The turntable's cameras and what each of its views sees of the raw model: the close-up's own camera (view c) and
MAP_VIEWS round it, drawn by inside/turntable.py on a rented card (turntable_row.py) with the raw model's own texture
unlit and the face under every pixel. The finish-map method draws a finish map of each MAP_VIEW and lays every map on
the faces its view sees (finish_parts.py).
"""
import json

import numpy as np

# The views a finish map is drawn of besides the close-up: the two sides and the back, low (azimuth degrees, 0 the
# close-up's side, at ELEVATION).
ELEVATION = 15.0
MAP_TURNS = (90, 180, 270)
SIDE = 1024
# The camera stands far enough that the model's farthest point from the middle fits with this margin.
FIT_MARGIN = 1.08
FRONT, BACK = "c", "t15-180"


def view_name(turn):
    return f"t{int(ELEVATION):02d}-{turn:03d}"


MAP_VIEWS = tuple(view_name(turn) for turn in MAP_TURNS)


def views_of(take, mesh):
    """The close-up's camera (view c) and MAP_VIEWS, in the raw model's glTF frame: labels.seen_faces looks at the
    model turned half round (VIEW_TURN) from +z, so the close-up camera stands at -z looking +z."""
    from PIL import Image
    import labels
    camera = json.loads((labels.PIXAL / f"{take}.svviews" / "transforms.json").read_text())
    width, height = Image.open(labels.PIXAL / f"{take}.svviews" / "input.png").size
    distance = -camera["frames"][0]["transform_matrix"][1][3]
    fov = camera["camera_angle_x"]
    reach = float(np.linalg.norm(mesh.vertices, axis=1).max())
    orbit = max(distance, FIT_MARGIN * reach / np.sin(fov / 2))
    found = [{"name": FRONT, "position": [0.0, 0.0, -distance], "target": [0.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0],
              "fov_x": fov, "width": width, "height": height}]
    for turn in MAP_TURNS:
        azimuth, rise = np.radians(turn), np.radians(ELEVATION)
        direction = [np.sin(azimuth) * np.cos(rise), np.sin(rise), -np.cos(azimuth) * np.cos(rise)]
        found.append({"name": view_name(turn), "position": [float(orbit * value) for value in direction],
                      "target": [0.0, 0.0, 0.0], "up": [0.0, 1.0, 0.0], "fov_x": fov, "width": SIDE, "height": SIDE})
    return found


def cameras(folder, takes):
    """<folder>/multiview/job.json for inside/turntable.py."""
    import labels
    import split_compare
    (folder / "multiview").mkdir(parents=True, exist_ok=True)
    job = {"out": str(folder / "multiview" / "renders"), "takes": [
        {"take": take, "model": str(labels.PIXAL / f"{take}.glb"),
         "views": views_of(take, split_compare.raw_model(take))}
        for take in takes]}
    (folder / "multiview" / "job.json").write_text(json.dumps(job, indent=1))


def poly_faces(renders, mesh):
    """Each Blender polygon's welded face (the nearest face middle)."""
    from scipy.spatial import cKDTree
    middles = np.load(renders / "faces.npy")
    distance, found = cKDTree(mesh.triangles_center).query(middles)
    if np.median(distance) > 1e-4:
        raise RuntimeError(f"{renders.name}: Blender's polygons lie {np.median(distance):.5f} from the welded faces")
    return found


def face_map(renders, view, mesh):
    """Each pixel's welded face in a turntable view (the turntable row's <view>-id.npz), -1 off the model."""
    ids = np.load(renders / f"{view}-id.npz")["ids"]
    poly = poly_faces(renders, mesh)
    return np.where(ids >= 0, poly[np.maximum(ids, 0)], -1)


def camera_of(job, take, view):
    """A turntable view's camera as the job gave it to inside/turntable.py."""
    entry = next(entry for entry in job["takes"] if entry["take"] == take)
    return next(camera for camera in entry["views"] if camera["name"] == view)


def projected(mesh, camera):
    """Each face middle's pixel (row, column) and depth through a turntable camera (glTF frame, fov across the
    width)."""
    position, target, up = (np.array(camera[key], dtype=float) for key in ("position", "target", "up"))
    forward = (target - position) / np.linalg.norm(target - position)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    true_up = np.cross(right, forward)
    offset = mesh.triangles_center - position
    depth = offset @ forward
    scale = 0.5 * camera["width"] / np.tan(camera["fov_x"] / 2)
    column = np.clip((0.5 * camera["width"] + scale * (offset @ right) / depth).astype(int), 0, camera["width"] - 1)
    row = np.clip((0.5 * camera["height"] - scale * (offset @ true_up) / depth).astype(int), 0, camera["height"] - 1)
    return row, column, depth


def seen_in_view(renders, camera, mesh, faces):
    """Which faces a turntable view sees and the pixel each lands on: a face is seen when its middle lies no more than
    labels.DEPTH_SLACK behind the face Blender drew at that pixel (`faces`, the view's face map), so faces smaller
    than a pixel count too."""
    import labels
    row, column, depth = projected(mesh, camera)
    drawn = faces[row, column]
    front_depth = np.where(drawn >= 0, depth[np.maximum(drawn, 0)], -np.inf)
    seen = (drawn >= 0) & (depth > 0) & (depth <= front_depth + labels.DEPTH_SLACK)
    return seen, row, column
