"""RRA's caps (owner, 2026-10-28): each frame's cap linearised
as balls (`cap_rows`), the adjusted path held within the clip's `follows` limit (`within_follows`) and within the
per-frame cap as measured (`within_frames`), and the measures they read (`turned_off`, `off_clip`)."""
import numpy as np
from scipy.ndimage import minimum_filter1d
from scipy.spatial.transform import Rotation

from model import posed_path
from rra._linear import adjusted_leads, moved
from solvers import CUTOFF, smoothed

CAP_STEP = 1e-3  # metres or radians: `cap_rows`' difference step
FRAME_ROUNDS = 20  # `within_frames`' rounds of lowering the frames over their cap
FRAME_MARGIN = 0.95  # a frame over its cap lowered this much further than its excess, so the rounds end


def turns_off(model, path, fitted, riders):
    """Each segment's turn of `path` off the fitted poses, as world rotation vectors (frames x segments x 3, rad)."""
    posed = posed_path(model, path, *riders[:3])[..., :3, :3]
    relative = posed @ np.swapaxes(fitted[..., :3, :3], -1, -2)
    return Rotation.from_matrix(relative.reshape(-1, 3, 3)).as_rotvec().reshape(*relative.shape[:2], 3)


def cap_rows(physics, path, total, land, fitted, riders, most):
    """The per-frame cap linearised at the path moved by `total` (frames x adjusted): each frame's balls, every
    segment's turn off the fitted poses (`most[1]`), the lumbar leaders' own turn (`most[1]`: RRA's per-coordinate
    bound, so a trunk turned one way and a pelvis the other cannot bend the lumbar twice the cap) and the pelvis'
    place off the fitted path (`most[0]`), as rows on that frame's move scaled to radius one (frames x balls x 3 x
    adjusted) and their values now (frames x balls x 3); balls that are another's or never move left out (every
    segment riding the chest turns as it does; the held feet do not). A segment's change with the move is measured
    through `land` (the legs follow the feet), by forward differences."""
    model, adjusted = physics.model, adjusted_leads(physics)
    count, width = total.shape
    now = turns_off(model, land(moved(physics, path, total, adjusted)), fitted, riders)
    turning = np.zeros((count, now.shape[1], 3, width))
    for column in range(width):
        nudge = np.zeros(width)
        nudge[column] = CAP_STEP
        ahead = turns_off(model, land(moved(physics, path, total + nudge, adjusted)), fitted, riders)
        turning[..., column] = (ahead - now) / (CAP_STEP * most[1])
    kept = []
    for ball in range(now.shape[1]):
        mine = np.concatenate([turning[:, ball].reshape(count, -1), now[:, ball] / most[1]], axis=1)
        if np.abs(mine).max() > CAP_STEP and not any(np.allclose(mine, other, atol=CAP_STEP) for other in kept):
            kept.append(mine)
    pelvis, lumbar = np.zeros((count, 1, 3, width)), np.zeros((count, 1, 3, width))
    pelvis[:, 0, :, :3] = np.eye(3) / most[0]
    lumbar[:, 0, :, 6:9] = np.eye(3) / most[1]
    rows = np.concatenate([np.stack([mine[:, :3 * width].reshape(count, 3, width) for mine in kept], axis=1), pelvis,
                           lumbar], axis=1)
    values = np.concatenate([np.stack([mine[:, 3 * width:] for mine in kept], axis=1), total[:, None, :3] / most[0],
                             total[:, None, 6:9] / most[1]], axis=1)
    return rows, values


def turned_off(before, after):
    """Each segment's turn between two posed paths (frames x segments x 4 x 4), degrees (frames x segments)."""
    return np.degrees(Rotation.from_matrix((np.swapaxes(after[..., :3, :3], -1, -2) @ before[..., :3, :3])
                                           .reshape(-1, 3, 3)).magnitude()).reshape(before.shape[:2])


def off_clip(model, path, worlds, segments, bodies, riding, parents):
    """The `follows` gate's measure on a path: the mean angle (degrees) between each segment's turn against its parent
    (riding its bone) and the clip's, over segments and frames."""
    found = []
    for posed, world in zip(posed_path(model, path, segments, bodies, riding), worlds):
        found += [np.degrees(Rotation.from_matrix((world[parent][:3, :3].T @ world[index][:3, :3])
                                                   @ (posed[index][:3, :3].T @ posed[parent][:3, :3])).magnitude())
                  for index, parent in enumerate(parents) if parent >= 0]
    return float(np.mean(found))


def within_follows(physics, path, adjusted, moves, land, worlds, riders, follows):
    """The adjusted path kept within the clip's `follows` limit (the owner's cap: never further off the clip than the
    `follows` gate allows, degrees on the mean): the whole move, else the largest of its quarters that is, else none;
    and the share kept."""
    model = physics.model
    for share in (1.0, 0.75, 0.5, 0.25):
        found = adjusted if share == 1.0 else land(moved(physics, path, share * moves, adjusted_leads(physics)))
        if off_clip(model, found, worlds, *riders) <= follows:
            return found, share
    return path, 0.0


def _frame_excess(model, path, found, fitted, riders, most):
    """Each frame's largest move of `found` off the fitted `path` over its cap: its segments' turns (riding their bones,
    against `fitted`'s poses) over `most[1]` and the pelvis' place over `most[0]`, the larger."""
    turned = turned_off(fitted, posed_path(model, found, *riders[:3]))
    shift = np.linalg.norm(found[:, :3] - path[:, :3], axis=1)
    return np.maximum(turned.max(axis=1) / np.degrees(most[1]), shift / most[0])


def within_frames(physics, path, moves, land, fitted, riders, most, rate):
    """The adjusted path held within `most` of the fitted path on every frame, all rounds together (owner, 2026-10-28:
    each segment's turn at most 5 degrees and the pelvis at most 2 cm off the fitted motion): each frame's share of the
    move (`moves`, frames x adjusted) lowered by how far it is over (`_frame_excess`), the shares eroded and low-passed
    over a CUTOFF period so the move stays smooth, its feet kept (`land`), until no frame is over; the path and the
    shares."""
    adjusted, share = adjusted_leads(physics), np.ones(len(path))
    window = int(rate // CUTOFF) + 1
    for _ in range(FRAME_ROUNDS):
        found = land(moved(physics, path, share[:, None] * moves, adjusted))
        over = _frame_excess(physics.model, path, found, fitted, riders, most)
        if over.max() <= 1.0:
            return found, share
        lowered = np.where(over > 1.0, share * FRAME_MARGIN / over, share)
        share = np.clip(np.minimum(lowered, smoothed(minimum_filter1d(lowered, window), rate)), 0.0, None)
    raise ValueError(f"the adjusted path is still {over.max():.2f} times its per-frame cap after {FRAME_ROUNDS} rounds")
