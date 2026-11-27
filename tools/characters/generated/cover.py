"""How well the regrown strands fill the generated hair's shell (`coverage`): the share of its outer surface, and of its
volume, within REACH_M of a strand. Round 1 left the shell's outer half and its ends empty (the dark neck showed from
behind, a bob lost its line, 2026-11-26); a regrown head is kept only at LEAST_OUTER or more.

The strands are read as points STEP_M apart along them (in chunks of CHUNK strands, so a head's 250 000 strands stay
under a gigabyte), snapped to a VOXEL_M grid; each surface sample's and voxel's nearest such point is looked up. The
outer surface is the hair triangles' samples with air OUT_M further out along the ray from the head's middle (the
side the shell is seen from; its inner side lies on the scalp or hangs facing the neck and cheeks)."""
import numpy as np
from scipy.spatial import cKDTree

from tools.characters.generated import volume

REACH_M = 0.003
STEP_M = 0.0005
VOXEL_M = 0.001
CHUNK = 20000
OUT_M = 0.004
LEAST_OUTER = 0.95


def strand_cells(strands):
    """The VOXEL_M cells the strands (strands x points x 3) pass through, as their middles."""
    cells = []
    for first in range(0, len(strands), CHUNK):
        chunk = strands[first:first + CHUNK]
        starts, ends = chunk[:, :-1].reshape(-1, 3), chunk[:, 1:].reshape(-1, 3)
        pieces = np.maximum(np.ceil(np.linalg.norm(ends - starts, axis=1) / STEP_M).astype(int), 1)
        segment = np.repeat(np.arange(len(starts)), pieces)
        offset = np.arange(len(segment)) - np.repeat(np.cumsum(pieces) - pieces, pieces)
        share = (offset / pieces[segment])[:, None]
        places = starts[segment] + (ends[segment] - starts[segment]) * share
        cells.append(np.unique(np.round(places / VOXEL_M).astype(np.int64), axis=0))
    return np.unique(np.vstack(cells), axis=0) * VOXEL_M


def covered(places, tree):
    """Whether each place lies within REACH_M of a strand cell."""
    return np.isfinite(tree.query(places, distance_upper_bound=REACH_M, workers=-1)[0])


def coverage(strands, points, faces, hair_faces, space, start, rng):
    """{outer, surface, volume}: the shares of the shell's outer surface, its whole surface and its volume's voxels
    within REACH_M of a strand; `start` is the head's middle."""
    tree = cKDTree(strand_cells(strands))
    samples, _ = volume.surface_samples(points, faces[hair_faces], rng)
    away = samples - start
    away /= np.maximum(np.linalg.norm(away, axis=1, keepdims=True), 1e-9)
    outer = volume.read(space, "filled", samples + away * OUT_M) < 0.5
    on_surface = covered(samples, tree)
    voxels = space["low"] + np.argwhere(space["filled"] > 0.5) * volume.VOXEL_M
    return {"outer": round(float(on_surface[outer].mean()), 4), "surface": round(float(on_surface.mean()), 4),
            "volume": round(float(covered(voxels, tree).mean()), 4)}
