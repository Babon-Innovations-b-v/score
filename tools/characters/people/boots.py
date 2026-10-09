"""The work suit's boots, and the trouser legs gathered into them.

The boot is a lace-up work boot Hi3DGen (MIT) made from a drawing, straightened (toe along +z)
and thinned, kept as `WORK_BOOT` in the look. It is scaled to the foot's heel-to-toe length plus
room, turned to the foot's heading, stood on the floor and centred across the foot; the right
boot is the left one mirrored. A trouser leg that ends above the boot's top is drawn down into it
(`lengthened`); trouser points below the boot's top are drawn in until they sit just outside its
wall, blending back to the drape over a few centimetres above it.
"""
import numpy as np
import trimesh
from paths import WORK_BOOT
from scipy.spatial import cKDTree

ROOM_LENGTH = 0.035   # the boot is longer than the bare foot
HEEL_BEHIND = 0.018   # its heel sits behind the bare heel
SOLE_BELOW = 0.004    # its sole a touch below the bare sole, so the foot never shows
WIDER = 1.12          # the generated boot is narrow for a work boot and for this foot
OUTSIDE_WALL = 0.004  # gathered trousers sit at least this far outside the boot's wall
GATHER_SLACK = 0.014  # and no more than this
BLEND_ABOVE = 0.09    # over this height above the boot's top the tuck fades out
BINS = 48             # angles round the boot at which its wall is measured
SMOOTHING = 8         # rounds the tuck's moves are averaged, so no single point spikes the hem
# How the boot hangs: from the ToeBase joint forward the toe blends onto it (start, length, most
# share), and from the ankle up the shaft blends onto the shin.
TOE_BLEND = (0.0, 0.04, 0.7)
SHAFT_BLEND = (0.03, 0.12, 0.75)
# Trouser cloth over the boot's top takes the boot's weights, fading out this far above it.
HEM_FADE = 0.08
# A trouser leg reaches at least this far below the lowest point of its boot's top all round. A drape that ends
# higher (Blender's cloth ends a few centimetres above the Warp drapes', and the boots then stood apart from the
# trousers: owner, 2026-10-09) has its lower leg stretched down to it over STRETCH_OVER above its hem; a drape that
# already reaches is left as it is.
REACH_INTO = 0.03
STRETCH_OVER = 0.30
# The angles round a boot's shaft at which its top and a trouser leg's hem are read.
RIM_BINS = 16


def bare_foot(body, side):
    """The body's points hanging mostly from one foot."""
    owner = body.weights.argmax(axis=1)
    joints = [body.joint_names.index(side + name) for name in ("Foot", "ToeBase", "ToeEnd")]
    return body.points[np.isin(owner, joints)]


def fit(boot, body, side):
    """The boot's points fitted round one foot."""
    heading = body.joints[side + "ToeEnd"] - body.joints[side + "Foot"]
    yaw = np.arctan2(heading[0], heading[2])
    forward = np.array([np.sin(yaw), 0.0, np.cos(yaw)])
    across = np.array([np.cos(yaw), 0.0, -np.sin(yaw)])
    foot = bare_foot(body, side)
    along = foot @ forward
    length = along.max() - along.min()
    scale = (length + ROOM_LENGTH) / (boot[:, 2].max() - boot[:, 2].min())
    shaped = boot * scale * [WIDER, 1.0, 1.0]
    turn = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
    shaped = shaped @ turn.T
    shaped[:, 1] += foot[:, 1].min() - SOLE_BELOW - shaped[:, 1].min()
    heel_shift = (along.min() - HEEL_BEHIND) - (shaped @ forward).min()
    across_shift = (foot @ across).mean() - (shaped @ across).mean()
    shaped += forward * heel_shift + across * across_shift
    print(f"{side} boot: foot {length * 100:.1f} cm long, boot scale {scale:.3f}")
    return shaped


def fitted(body):
    """Both boots: the left's points, the right's (the left mirrored), and the left's faces."""
    source = np.load(WORK_BOOT)
    left = fit(source["points"], body, "Left")
    return left, left * [-1.0, 1.0, 1.0], source["faces"].astype(np.int64)


def outline_points(boot_mesh, height):
    """Points along the boot's cross-section at a height, a few millimetres apart: the thinned
    boot has large flat triangles, so its points alone miss most of the wall."""
    section = boot_mesh.section(plane_origin=[0, height, 0], plane_normal=[0, 1, 0])
    if section is None:
        return np.zeros((0, 2))
    points = []
    for line in section.discrete:
        for start, end in zip(line[:-1], line[1:]):
            steps = max(1, int(np.linalg.norm(end - start) / 0.003))
            for fraction in np.linspace(0, 1, steps, endpoint=False):
                points.append((start + (end - start) * fraction)[[0, 2]])
    return np.array(points)


def outer_radius(boot_mesh, axis_point, heights):
    """How far the boot reaches from an axis, per height band (at its middle) and angle bin,
    gaps filled from the neighbouring bins."""
    table = np.full((len(heights) - 1, BINS), -np.inf)
    for row in range(len(heights) - 1):
        ring = outline_points(boot_mesh, (heights[row] + heights[row + 1]) / 2)
        if not len(ring):
            continue
        offset = ring - axis_point
        angle = np.arctan2(offset[:, 0], offset[:, 1])
        radius = np.hypot(offset[:, 0], offset[:, 1])
        columns = ((angle + np.pi) / (2 * np.pi) * BINS).astype(int) % BINS
        np.maximum.at(table[row], columns, radius)
    for _ in range(BINS):
        empty = ~np.isfinite(table)
        if not empty.any():
            break
        around = np.maximum(np.roll(table, 1, axis=1), np.roll(table, -1, axis=1))
        table[empty] = around[empty]
    return table


class Walls:
    """One boot's wall tables, measured once for each axis they are asked about."""

    def __init__(self, boot, faces):
        self.mesh = trimesh.Trimesh(boot, faces, process=False)
        self.cache = {}

    def table(self, axis_point, heights):
        key = tuple(np.round(axis_point, 3))
        if key not in self.cache:
            self.cache[key] = outer_radius(self.mesh, axis_point, heights)
        return self.cache[key]


def around(points, axis_point, bins=RIM_BINS):
    """Which of `bins` angles round an upright line through `axis_point` each point lies at."""
    offset = points[:, [0, 2]] - axis_point[[0, 2]]
    return ((np.arctan2(offset[:, 0], offset[:, 1]) + np.pi) / (2 * np.pi) * bins).astype(int) % bins


def lowest_top(boot):
    """The lowest point of the boot's top all round: over the angles round its shaft, the least of its highest point
    at each, and the shaft's middle at the top, where those angles are read from."""
    top = boot[:, 1].max()
    shaft = boot[boot[:, 1] > top - 0.03].mean(axis=0)
    angle = around(boot, shaft)
    tops = [boot[angle == bin_, 1].max() for bin_ in range(RIM_BINS) if (angle == bin_).any()]
    return min(tops), shaft


def lengthened(cloth_points, limbs, boot, side):
    """One trouser leg stretched down until its hem reaches REACH_INTO below its boot's top all round (the highest
    of its lowest points round the shaft); a leg that already reaches comes back unchanged."""
    leg = limbs == ("left_leg" if side == "Left" else "right_leg")
    low_top, shaft = lowest_top(boot)
    near = leg & (np.linalg.norm(cloth_points[:, [0, 2]] - shaft[[0, 2]], axis=1) < 0.14) \
        & (cloth_points[:, 1] < boot[:, 1].max() + STRETCH_OVER)
    if not near.any():
        return cloth_points
    angle = around(cloth_points[near], shaft)
    hem = max(cloth_points[near][angle == bin_, 1].min() for bin_ in range(RIM_BINS) if (angle == bin_).any())
    target = low_top - REACH_INTO
    if hem <= target:
        return cloth_points
    anchor = hem + STRETCH_OVER
    stretch = (anchor - target) / (anchor - hem)
    moved = cloth_points.copy()
    below = leg & (cloth_points[:, 1] < anchor)
    moved[below, 1] = anchor - (anchor - cloth_points[below, 1]) * stretch
    print(f"{side}: trouser hem at {hem * 100:.1f} cm drawn down to {target * 100:.1f} cm, "
          f"{REACH_INTO * 100:.0f} cm into the boot")
    return moved


def gather(cloth_points, limbs, boot, walls, side):
    """One trouser leg gathered over its boot's top: below the top each point is held between
    just outside the boot's wall and GATHER_SLACK beyond it; the hold fades out BLEND_ABOVE up."""
    top = boot[:, 1].max()
    leg = limbs == ("left_leg" if side == "Left" else "right_leg")
    heights = np.linspace(0.0, top, 41)
    moved = cloth_points.copy()
    count = 0
    for index in np.where(leg & (cloth_points[:, 1] < top + BLEND_ABOVE))[0]:
        point = cloth_points[index]
        # A hem lying on the floor can dip just below it (#112): read the wall from the floor up.
        height = min(max(point[1], 0.0), top - 1e-4)
        # The shaft's own centre at this height is the axis, so every angle sees its wall.
        slab = np.abs(boot[:, 1] - min(height, top - 0.012)) < 0.012
        axis = np.array([boot[slab, 0].mean(), 0.0, boot[slab, 2].mean()])
        offset = point[[0, 2]] - axis[[0, 2]]
        radius = np.hypot(*offset)
        row = min(np.digitize(height, heights) - 1, len(heights) - 2)
        table = walls.table(axis[[0, 2]], heights)
        column = int((np.arctan2(offset[0], offset[1]) + np.pi) / (2 * np.pi) * BINS) % BINS
        # The wall over nearby bands too (and the whole rim near the top), so the rim never
        # pokes out.
        low_row = max(0, row - 2) if height < top - 0.02 else min(row, len(heights) - 6)
        wall = table[low_row:row + 3, column].max()
        wanted = np.clip(radius, wall + OUTSIDE_WALL, wall + GATHER_SLACK)
        if abs(wanted - radius) < 1e-5:
            continue
        blend = 1.0 if point[1] <= top else 0.5 * (1 + np.cos(np.pi * (point[1] - top) / BLEND_ABOVE))
        moved[index, [0, 2]] = axis[[0, 2]] + offset * (radius + (wanted - radius) * blend) / radius
        count += 1
    print(f"{side}: {count} trouser points gathered over the {top * 100:.1f} cm boot top")
    return moved


def smoothed_moves(before, after, faces):
    """The tuck's moves averaged over neighbouring points, so single points drawn in leave no
    spikes in the hem; a moved point keeps at least its own move, so it stays outside the boot."""
    delta = after - before
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    moved = np.linalg.norm(delta, axis=1) > 0
    region = moved.copy()
    for _ in range(3):
        grown = region.copy()
        grown[edges[region[edges[:, 0]], 1]] = True
        region = grown
    for _ in range(SMOOTHING):
        total = delta.copy()
        count = np.ones(len(before))
        np.add.at(total, edges[:, 0], delta[edges[:, 1]])
        np.add.at(count, edges[:, 0], 1)
        averaged = total / count[:, None]
        stronger = np.linalg.norm(averaged, axis=1) > np.linalg.norm(delta, axis=1)
        keep_own = moved & ~stronger
        delta = np.where((region & ~keep_own)[:, None], averaged, delta)
    return before + delta


def tucked(cloth_points, faces, limbs, boots_by_side, left_faces, body):
    """The cloth with both trouser legs drawn down into their boots where they end short, and gathered there."""
    faces = np.asarray(faces)
    points = cloth_points
    for side, boot in boots_by_side.items():
        boot_faces = left_faces if side == "Left" else left_faces[:, ::-1]
        points = lengthened(points, limbs, boot, side)
        points = gather(points, limbs, boot, Walls(boot, boot_faces), side)
    return smoothed_moves(cloth_points, points, faces)


def weights(points, side, body):
    """A boot's weights: the foot, the toe blending onto ToeBase ahead of the ball and the shaft
    onto the shin above the ankle."""
    names = body.joint_names
    foot, toe = body.joints[side + "Foot"], body.joints[side + "ToeBase"]
    forward = np.array([toe[0] - foot[0], 0.0, toe[2] - foot[2]])
    forward /= np.linalg.norm(forward)
    ahead = (points - toe) @ forward
    toe_share = np.clip((ahead - TOE_BLEND[0]) / TOE_BLEND[1], 0, 1) * TOE_BLEND[2]
    shin_share = np.clip((points[:, 1] - foot[1] - SHAFT_BLEND[0]) / SHAFT_BLEND[1], 0, 1) * SHAFT_BLEND[2]
    shares = np.zeros((len(points), len(names)))
    shares[:, names.index(side + "ToeBase")] = toe_share
    shares[:, names.index(side + "Shin")] = shin_share
    shares[:, names.index(side + "Foot")] = 1.0 - toe_share - shin_share
    return shares


def hem_follows_boot(points, cloth_weights, boot, boot_weights):
    """Trouser cloth over the boot's top takes the boot's weights (fading out HEM_FADE above the
    top), so the gathered hem rides with the boot instead of sliding into it."""
    top = boot[:, 1].max()
    near = np.linalg.norm(points[:, [0, 2]] - boot[:, [0, 2]].mean(axis=0), axis=1) < 0.14
    share = np.clip((top + HEM_FADE - points[:, 1]) / HEM_FADE, 0, 1) * near
    _, nearest = cKDTree(boot).query(points)
    blended = cloth_weights * (1 - share[:, None]) + boot_weights[nearest] * share[:, None]
    return blended / blended.sum(axis=1, keepdims=True)
