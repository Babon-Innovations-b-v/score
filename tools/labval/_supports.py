"""What a LabValidation trial's person rests on besides the lab's floor, as drawn ground the sim body's contact reads
(triangles, the person's frame, Y up, the seen floor at y = 0): the chair a sit-to-stand sits on and the box a drop
jump starts from. Each from what is known and what the clip shows, never fitted to the reference's angles:

- the chair's seat at SEAT_HIGH over the floor (Uhlrich et al. 2023, PLOS Comput Biol 19(10) e1011462, Methods: the
  joint moments "while rising from a 40 cm chair"), under the skin the clip sits on: the points the Hips carry most
  within RESTING of their lowest on each seated frame (the frames that skin is within SEATED of its lowest over the
  clip; with the thighs' skin too the seat reached under the feet, drawn back under the knees, on subject8_STS1),
  their convex hull across the floor grown by MARGIN;
- the box's top where the clip's feet stand before the drop (no height in the paper's text, SimTK's project and
  download pages or sessionMetadata.yaml, 2026-11-07; the dataset's README is inside its archive, not in the store's
  copy: the clip's own first support, `_soma.undrifted`'s level, which the MoGe-2 floor puts the floor under), under the foot skin within RESTING of that level, its hull grown by MARGIN.
  The lab's markers, the check only, put the box 0.33 to 0.36 m up on 9 drop jumps; the clips stand 0.07 to 0.30.

Neither reaches where the clip's feet stand on the floor: a skin point seen on a support within CLEAR across the floor
of a foot's skin on the floor (within RESTING of it) is left out of its footprint (subject3's drop jumps land where
GEM-X saw them start, 15 to 17% of their floor feet under the box otherwise), and a support with fewer than three
points left, or all on a line, is none.

A seat or a top is one flat convex polygon (a fan of triangles from its middle): its sides are upright and cross no
upright line, so the ground under a point is the top or the floor (`inside/ground`'s `standing`)."""
import numpy as np
from scipy.spatial import ConvexHull, cKDTree

from score.stages import sim_body
from tools.characters import played

SEAT_HIGH = 0.40  # m: LabValidation's chair (Uhlrich et al. 2023)
SEATED = 0.05  # m: a frame is seated when the seat skin's lowest point is within this of its lowest over the clip
RESTING = 0.03  # m: the skin within this of its lowest on a frame rests on its support
MARGIN = 0.02  # m: a support's footprint grown past the skin seen on it
# A support's footprint keeps CLEAR across the floor from the feet on the floor. Chosen on subjects 2 to 5's six drop
# jumps against their plates (#98, 2026-11-07): 0.05 m left subject4_DJ1's and subject3_DJAsym1's landed feet on the
# box's edge (right foot carried 0.57 and 0.29 of the plates' frames, 0.83 and 0.50 at 0.10); 0.15 no better.
CLEAR = 0.10  # m
BOX_LOW = 0.03  # m: a drop jump's first feet this far over the floor or more stand on its box (the stage's STANCE_HIGH)
SEAT_SEGMENTS = ("Hips",)
FEET = ("LeftFoot", "LeftToeBase", "LeftToeEnd", "RightFoot", "RightToeBase", "RightToeEnd")


def skin(rig, local):
    """The rig's skin on every frame of `local` (frames x points x 3)."""
    skinning = played.chained(np.asarray(local, dtype=float), rig["parents"]) @ np.linalg.inv(np.asarray(rig["bind"]))
    points = np.c_[np.asarray(rig["points"], dtype=float), np.ones(len(rig["points"]))]
    return np.einsum("pj,fjab,pb->fpa", np.asarray(rig["weights"], dtype=float), skinning[..., :3, :], points)


def carried_by(rig, segments):
    """The skin points the named joints carry most."""
    names = [str(name) for name in rig["names"]]
    return np.isin(np.asarray(rig["weights"]).argmax(axis=1), [names.index(name) for name in segments if name in names])


def top(across, height, floor_feet):
    """A flat convex top at `height` over the points `across` (n x 2, x and z) farther than CLEAR from every point of
    `floor_feet` (m x 2), grown by MARGIN: triangles x 3 x 3; none (0 x 3 x 3) when such points span no area."""
    if len(floor_feet):
        across = across[cKDTree(floor_feet).query(across, distance_upper_bound=CLEAR)[0] > CLEAR]
    if len(across) < 3 or np.linalg.matrix_rank(across - across.mean(axis=0), tol=1e-6) < 2:
        return np.zeros((0, 3, 3))
    hull = across[ConvexHull(across).vertices]
    middle = hull.mean(axis=0)
    outward = hull - middle
    hull = hull + MARGIN * outward / np.linalg.norm(outward, axis=1, keepdims=True)
    corners = np.c_[hull[:, 0], np.full(len(hull), height), hull[:, 1]]
    centre = np.array([middle[0], height, middle[1]])
    return np.array([[centre, corners[index], corners[(index + 1) % len(corners)]] for index in range(len(corners))])


def resting(placed, on):
    """The x and z of the points of `placed` (frames x points x 3) within RESTING of each frame's lowest, over the
    frames `on`."""
    chosen = placed[on]
    near = chosen[..., 1] <= chosen[..., 1].min(axis=1, keepdims=True) + RESTING
    return chosen[near][:, [0, 2]]


def on_floor(feet_skin):
    """The x and z of the feet's skin within RESTING of the floor on any frame (points x 2)."""
    return feet_skin[feet_skin[..., 1] <= RESTING][:, [0, 2]]


def seat(rig, local):
    """The chair's seat under a sit-to-stand (`local` stood) and its record."""
    placed = skin(rig, local)
    sitting = placed[:, carried_by(rig, SEAT_SEGMENTS)]
    lowest = sitting[..., 1].min(axis=1)
    seated = lowest <= lowest.min() + SEATED
    found = top(resting(sitting, seated), SEAT_HIGH, on_floor(placed[:, carried_by(rig, FEET)]))
    return found, {"kind": "chair seat", "top m": SEAT_HIGH, "seated frames": int(seated.sum()),
                   "seen seat skin m": round(float(np.median(lowest[seated])), 4),
                   "footprint m2": round(area(found), 4)}


def box(rig, local):
    """The box under a drop jump's start (`local` stood) and its record; none when its first feet stand under
    BOX_LOW (the clip starts on its floor)."""
    feet_skin = skin(rig, local)[:, carried_by(rig, FEET)]
    heights = sim_body.soles(rig, local)[0].min(axis=1)
    first = float(np.median(heights[:5]))
    if first < BOX_LOW:
        return np.zeros((0, 3, 3)), {"kind": "box", "none": f"the clip's first feet stand {first:.3f} m up"}
    left = np.flatnonzero(heights < first / 2.0)
    on = np.arange(len(heights)) < (left[0] if len(left) else len(heights))
    level = float(np.median(heights[on]))
    on &= np.abs(heights - level) <= RESTING
    found = top(resting(feet_skin, on), level, on_floor(feet_skin))
    return found, {"kind": "box", "top m": round(level, 4), "frames on it": int(on.sum()),
                   "footprint m2": round(area(found), 4)}


def area(triangles):
    """The area across the floor of a fan of flat triangles (m2)."""
    first, second = triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    return float(np.abs(first[:, 0] * second[:, 2] - first[:, 2] * second[:, 0]).sum() / 2.0)


def under(rig, local, activity):
    """What the clip `local` (stood, on `rig`) of a trial of `activity` rests on besides the floor: (triangles x 3 x
    3, its record or None)."""
    if activity == "sit-to-stand":
        return seat(rig, local)
    if activity == "drop jump":
        return box(rig, local)
    return np.zeros((0, 3, 3)), None
