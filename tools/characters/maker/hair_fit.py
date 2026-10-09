"""A generated head with hair laid over the person's own head, and its hair kept as a clean shell over their scalp.

    /root/envs/motion/bin/python hair_fit.py <work folder> <generated.glb> <out.npz> [most=0.035] [middle_nose]
        [wide_sizes=0.9:1.7] [stretch=1.3]

1. Alignment. The generated head (Hi3DGen from the clay hair picture) is a redraw, not this head: it is matched by one
   scale, from the head's depth and width at the nose, and a rigid move found by trimmed ICP (only the closest 55% of
   point pairs count, so the hair, which the bald head lacks, and the generated bust are left out). Target: the
   person's skin below the hairline.
2. Thickness: along the shell grid's directions, the generated mesh's outermost hit less the scalp's radius, clipped
   at zero and at `most`.
3. The shell: the thickness smoothed, tapered to the hairline, and meshed (hair_shell.py).

Take C's numbers (the shell's centre, the face's lowest height) are moved with the person's eyes. The options are the
ones the first expedition's hair needed (#112): `middle_nose` looks for the nose only in the middle of the face (a curl
in front of the forehead is not the nose), `wide_sizes` searches bigger scales (hair as wide as the face), `stretch`
caps how far the cranium may stretch (thick curls at the sides). Moved here from round three's gen_hair.py and the
nev_mars job's hair_person.py.
"""
import json
import pathlib
import sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hair_shell as shell  # noqa: E402

KEEP = 0.55
TURNS = np.radians([-15.0, -5.0, 5.0, 15.0])
SIZES = (0.94, 0.97, 1.0, 1.03, 1.06)
ICP_STEPS = 40
# A finer grid than built hair, so the generated clumps survive (thinned afterwards).
ROWS, COLUMNS = 64, 200
SIDE_HAIR = 0.006
TAKE_C_EYES = np.array([0.0, 1.649, 0.060])
TAKE_C_EYE_X = 0.031
TAKE_C_TOP = 1.757
TAKE_C_FACE_LOWEST = 1.50


class Head:
    """The person's head as the fit needs it: the shell's centre and the face's lowest height, moved from take C's by
    the eyes, and the skin."""

    def __init__(self, work):
        joints = json.loads((work / "gc/body/joints.json").read_text())
        eyes = np.array([0.0, joints["LeftEye"][1], joints["LeftEye"][2]])
        scale = np.array([joints["LeftEye"][0] / TAKE_C_EYE_X,
                          (joints["HeadEnd"][1] - joints["LeftEye"][1]) / (TAKE_C_TOP - TAKE_C_EYES[1]),
                          joints["LeftEye"][0] / TAKE_C_EYE_X])
        self.centre = eyes + (shell.TAKE_C_CENTRE - TAKE_C_EYES) * scale
        self.lowest = eyes[1] + (TAKE_C_FACE_LOWEST - TAKE_C_EYES[1]) * scale[1]
        self.skin = np.load(work / "head/skin_head.npz")

    def face_points(self):
        """The skin below the hairline (face, ears, neck): what the bald redraw shares with this head."""
        points = self.skin["points"]
        offset = points - self.centre
        polar = np.degrees(np.arccos(np.clip(offset[:, 1] / np.linalg.norm(offset, axis=1), -1, 1)))
        azimuth = np.degrees(np.arctan2(offset[:, 0], offset[:, 2]))
        below = polar > np.degrees(shell.hairline(azimuth)) + 4
        return points[below & (points[:, 1] > self.lowest)]


def generated(path):
    scene = trimesh.load(path)
    mesh = scene.to_geometry() if isinstance(scene, trimesh.Scene) else scene
    return trimesh.Trimesh(mesh.vertices, mesh.faces, process=True)


def turn_y(angle):
    cosine, sine = np.cos(angle), np.sin(angle)
    return np.array([[cosine, 0, sine], [0, 1, 0], [-sine, 0, cosine]])


def rigid(source, target):
    """The rotation and move (no scale) taking source points onto target points."""
    source_mean, target_mean = source.mean(0), target.mean(0)
    left, _, right = np.linalg.svd((target - target_mean).T @ (source - source_mean))
    fix = np.eye(3)
    if np.linalg.det(left @ right) < 0:
        fix[2, 2] = -1
    rotation = left @ fix @ right
    return rotation, target_mean - rotation @ source_mean


def nose_measures(points, middle_only):
    """The nose tip and the head's depth and width in a band at its height. `middle_only` looks for the tip only in
    the middle of the face, across and up."""
    if middle_only:
        middle_x, width = np.median(points[:, 0]), np.ptp(points[:, 0])
        low, high = np.quantile(points[:, 1], [0.30, 0.70])
        candidates = points[(np.abs(points[:, 0] - middle_x) < 0.08 * width) & (points[:, 1] > low)
                            & (points[:, 1] < high)]
    else:
        candidates = points[points[:, 1] > np.quantile(points[:, 1], 0.35)]
    tip = candidates[np.argmax(candidates[:, 2])]
    band = points[np.abs(points[:, 1] - tip[1]) < 0.04 * np.ptp(points[:, 1])]
    band = band[np.abs(band[:, 0] - tip[0]) < 0.5 * np.ptp(band[:, 0])]
    return tip, tip[2] - band[:, 2].min(), np.ptp(band[:, 0])


def icp(gen_points, target_points, tree, scale, rotation, move):
    """Trimmed rigid ICP at a fixed scale: (trimmed mean gap, (scale, rotation, move))."""
    for _ in range(ICP_STEPS):
        distance, nearest = tree.query(scale * gen_points @ rotation.T + move)
        keep = distance <= np.quantile(distance, KEEP)
        rotation, move = rigid(scale * gen_points[keep], target_points[nearest[keep]])
    distance, _ = tree.query(scale * gen_points @ rotation.T + move)
    return np.sort(distance)[: int(KEEP * len(distance))].mean(), (scale, rotation, move)


def fit(gen_points, target_points, head_points, options):
    """A scale from the depth and width at the nose, noses lined up, then trimmed ICP from a few turns and scales
    round it; the best."""
    tree = cKDTree(target_points)
    middle = "middle_nose" in options
    our_tip, our_depth, our_width = nose_measures(head_points, middle)
    gen_tip, gen_depth, gen_width = nose_measures(gen_points, middle)
    first = (our_depth / gen_depth + our_width / gen_width) / 2
    sizes = SIZES
    if "wide_sizes" in options:
        low, high = (float(value) for value in options["wide_sizes"].split(":"))
        sizes = tuple(np.linspace(low, high, 9))
    best = (np.inf, None)
    for size in first * np.array(sizes):
        for turn in TURNS:
            rotation = turn_y(turn)
            result = icp(gen_points, target_points, tree, size, rotation, our_tip - size * rotation @ gen_tip)
            if result[0] < best[0]:
                best = result
    return best


def outer_radius(mesh, dirs, centre):
    """The distance from the centre to the mesh's outermost hit per direction."""
    flat = dirs.reshape(-1, 3)
    locations, ray, _ = mesh.ray.intersects_location(np.tile(centre, (len(flat), 1)), flat, multiple_hits=True)
    radius = np.zeros(len(flat))
    np.maximum.at(radius, ray, np.linalg.norm(locations - centre, axis=1))
    return radius.reshape(dirs.shape[:2])


def fit_cranium(placed, dirs, scalp, centre, cap):
    """The placed head stretched about the centre, per axis, so its sides and back sit SIDE_HAIR over the scalp (the
    redraw's cranium is small for its face), fitted on the sides and back by least squares, at most `cap` times."""
    radius = outer_radius(placed, dirs, centre)
    polar = np.degrees(np.arccos(dirs[..., 1]))
    azimuth = np.degrees(np.arctan2(dirs[..., 0], dirs[..., 2]))
    edge = np.degrees(shell.hairline(azimuth))
    use = (np.abs(azimuth) > 50) & (polar > 50) & (polar < edge - 5) & (radius > 0)
    wanted = (scalp[use] + SIDE_HAIR) / radius[use]
    squares, *_ = np.linalg.lstsq(dirs[use] ** 2, wanted ** 2, rcond=None)
    stretch = np.sqrt(np.clip(squares, 1.0 / cap ** 2, cap ** 2))
    print(f"cranium stretch x {stretch[0]:.3f} y {stretch[1]:.3f} z {stretch[2]:.3f}", flush=True)
    return trimesh.Trimesh(centre + (np.asarray(placed.vertices) - centre) * stretch, placed.faces, process=False)


def hair_from(placed, head, most, cap):
    """The hair shell: the placed head's thickness over the scalp, smoothed, tapered and meshed."""
    skin = trimesh.Trimesh(head.skin["points"], head.skin["faces"], process=False)
    dirs = shell.directions(ROWS, COLUMNS)
    scalp = shell.scalp_radius(skin, dirs, head.centre)
    placed = fit_cranium(placed, dirs, scalp, head.centre, cap)
    field = np.clip(outer_radius(placed, dirs, head.centre) - scalp, 0.0, most)
    field = shell.smooth_grid(field, 1)
    field = np.maximum(shell.taper(field, dirs, 0.9), 0.0015)
    grid = head.centre + dirs * (scalp + field)[..., None]
    tuck = head.centre + dirs[-1] * (scalp[-1] - shell.TUCK)[:, None]
    points, faces = shell.mesh(grid, tuck)
    hair = trimesh.Trimesh(points, faces, process=False)
    trimesh.repair.fix_normals(hair)
    return hair, field, placed


def main():
    work, source, out = pathlib.Path(sys.argv[1]), sys.argv[2], pathlib.Path(sys.argv[3])
    options = dict(argument.split("=") if "=" in argument else (argument, "") for argument in sys.argv[4:])
    head = Head(work)
    mesh = generated(source)
    error, (scale, rotation, move) = fit(mesh.sample(6000), head.face_points(), head.skin["points"], options)
    print(f"aligned: trimmed mean gap {error * 1000:.1f} mm, scale {scale:.4f}", flush=True)
    placed = trimesh.Trimesh(scale * mesh.vertices @ rotation.T + move, mesh.faces, process=False)
    hair, field, placed = hair_from(placed, head, float(options.get("most", 0.035)),
                                    float(options.get("stretch", 2.0)))
    np.savez(str(out).replace(".npz", "_aligned.npz"), points=np.asarray(placed.vertices),
             faces=np.asarray(placed.faces))
    np.savez(out, points=np.asarray(hair.vertices), faces=np.asarray(hair.faces), uv=np.zeros((len(hair.vertices), 2)))
    print(f"{out.name}: {len(hair.vertices)} points; thickness {field.min() * 1000:.1f}..{field.max() * 1000:.1f} mm "
          f"(median {np.median(field) * 1000:.1f})", flush=True)


if __name__ == "__main__":
    main()
