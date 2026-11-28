"""The strands laid on and over the clothes each drawn frame (#223): the hair rides the Head joint rigidly and the
cloth moves on its own, so a strand that hangs into a garment is stopped at it and lies along it. Round 14
(2026-11-28, owner's close-ups): the stairwell woman's hair passed through her puffer's high collar standing and as
she walked; it never lay on it (from whole9, af909fbfd keeping the body's own high collar, the hair ran into it).

Each strand is followed from its root (which lies on the scalp, outside every garment) to its tip, each step taken as
the strand's own (its rest shape carried along), never from the cloth's normal alone: a generated garment is a thin
two-sided shell wound either way, so the side a strand belongs on is the side it reaches the cloth from. A step whose
segment meets the cloth (or ends within its clearance) is slid along the cloth's plane there, CLEAR_M off it on the
strand's side, its length kept; TRIES times at a curved spot, then left on the plane. Only strands that come within a
voxel of the cloth at all are followed (`near`): the rest are unchanged.

Inside Blender `blender_person.hair_over_cloth` casts the rays on the garments' BVH as they stand at the frame.
"""
import numpy as np

CLEAR_M = 0.002  # a strand point lies this far (metres) off the cloth on its side
TRIES = 3  # a step slid again at most this often where the cloth curves under it
SLACK_M = 0.005  # added to the voxel past the longest step and cloth edge


def voxel_size(steps, edges):
    """The voxel (m) in whose neighbourhood a step that meets the cloth must start or end: the longest step, the
    longest cloth edge (a point of the cloth is that near a sample of it) and SLACK_M."""
    return float(np.max(steps, initial=0.0) + np.max(edges, initial=0.0) + SLACK_M)


def keys_of(cells):
    """Integer voxel cells (k x 3) as one int64 key each."""
    cells = cells.astype(np.int64) + (1 << 20)
    return (cells[:, 0] << 42) | (cells[:, 1] << 21) | cells[:, 2]


def cloth_keys(points, triangles, size):
    """The sorted keys of the voxels within one voxel of the cloth's corners and triangle middles."""
    samples = np.vstack([points, points[triangles].mean(axis=1)])
    cells = np.unique(np.floor(samples / size).astype(np.int64), axis=0)
    around = np.stack(np.meshgrid(*[np.arange(-1, 2)] * 3, indexing="ij"), axis=-1).reshape(-1, 3)
    return np.unique(keys_of((cells[:, None, :] + around[None]).reshape(-1, 3)))


def near(points, keys, size):
    """Whether each point (k x 3) lies in a voxel next to the cloth."""
    return np.isin(keys_of(np.floor(points / size)), keys, assume_unique=False)


def slid(start, end, location, normal, keep_length):
    """`end` slid onto the plane through `location` CLEAR_M off it on `start`'s side; with `keep_length`, the point
    on that plane at its old distance from `start`, the way it slid."""
    side = np.sign(np.einsum("ki,ki->k", start - location, normal))
    side[side == 0.0] = 1.0
    way = normal * side[:, None]
    moved = end - (np.einsum("ki,ki->k", end - location, way) - CLEAR_M)[:, None] * way
    if not keep_length:
        return moved
    length = np.linalg.norm(end - start, axis=1)
    height = np.einsum("ki,ki->k", start - location, way) - CLEAR_M
    foot = start - height[:, None] * way
    along = moved - foot
    span = np.linalg.norm(along, axis=1)
    held = span > 1e-9
    reach = np.sqrt(np.maximum(length ** 2 - height ** 2, 0.0))
    moved[held] = foot[held] + along[held] * (reach[held] / span[held])[:, None]
    return moved


def step_laid(start, end, cast):
    """Each step `start` -> `end` (k x 3) stopped at the cloth and slid along it (`slid`): the ends."""
    end = end.copy()
    chosen = np.arange(len(start))
    for attempt in range(TRIES + 1):
        if not len(chosen):
            break
        reach = end[chosen] - start[chosen]
        length = np.linalg.norm(reach, axis=1)
        live = length > 1e-9
        chosen, reach, length = chosen[live], reach[live], length[live]
        hit, location, normal = cast(start[chosen], reach / length[:, None], length + CLEAR_M)
        chosen, location, normal = chosen[hit], location[hit], normal[hit]
        end[chosen] = slid(start[chosen], end[chosen], location, normal, attempt < TRIES)
    return end


def laid_over(strands, cast, keys, size):
    """The strands (strands x points x 3, roots first) laid on and over the cloth: `cast(origins, ways, reaches)`
    gives (hit, location, normal) of the first cloth met along each ray; `keys` and `size` its voxels
    (`cloth_keys`). (the strands, how many moved)."""
    laid = strands.copy()
    chosen = np.flatnonzero(near(strands.reshape(-1, 3), keys, size).reshape(strands.shape[:2]).any(axis=1))
    if not len(chosen):
        return laid, 0
    rest = strands[chosen]
    steps = np.diff(rest, axis=1)
    done = rest.copy()
    for number in range(1, rest.shape[1]):
        start = done[:, number - 1]
        end = start + steps[:, number - 1]
        shifted = np.any(start != rest[:, number - 1], axis=1)
        looked = np.flatnonzero(shifted | near(start, keys, size) | near(end, keys, size))
        end[looked] = step_laid(start[looked], end[looked], cast)
        done[:, number] = end
    laid[chosen] = done
    return laid, int(np.any(done != rest, axis=(1, 2)).sum())
