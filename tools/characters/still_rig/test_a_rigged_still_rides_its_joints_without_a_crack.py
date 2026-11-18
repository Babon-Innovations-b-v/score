"""A rigged still's hard parts ride their joints and the cloth between them bends instead of cracking.

The fixture is a strip of points 1 cm apart up a body's back: suit cloth, a backpack on the chest, a helmet on the head
above it touching the backpack, and a stray backpack face inside the cloth. Each break below turns it red:

- a hard part's point far from any other hard part does not ride its joint wholly (`rigid`), or a weight row stops
  summing to one;
- the cloth next to a hard part keeps its own joint up to the rim, so neighbouring points 1 cm apart differ by more
  than a third of their weight (the cliff prop_build's eased_to_hard left on one surface: edges 8 times their length);
- the helmet and the backpack meet as two rigid parts on different joints (no `seamed` sharing), so a 10 degree nod
  stretches an edge at their seam more than 1.5 times its length;
- a loose strip of cloth 2 cm beside the backpack, joined to it by no face, is eased onto the chest (the ease measured
  straight across the gap, not over the surface: the upper arm beside the backpack torn at every swing);
- the cloth's weights jump from the hips to the chest between two points and `eased_cliffs` leaves a step of more than
  a fifth between neighbours, moves a fixed point, or lets a row stop summing to one;
- a cube with one side cut away is not closed by `closed` (an open edge left, or a fan face turned against the face
  it borders, so the patch shows its back: the black tears at the shoulders and boots);
- a lone face of another part inside a part is kept as that other part (`kept_pieces`);
- the sphere's sight lines are not spread over both halves of every axis (`directions`).
"""
import pathlib
import sys

import numpy as np
import trimesh
from scipy.spatial.transform import Rotation

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import still_rig  # noqa: E402

NAMES = ["Root", "Hips", "Chest", "Head"]


def strip():
    """Two columns of points 1 cm apart from 0.8 m to 1.9 m, faces between them, each face's part by its height:
    suit under 1.3 m, backpack to 1.6 m, helmet over it; and every point's own weights on the hips."""
    heights = np.round(np.arange(0.8, 1.9001, 0.01), 3)
    points = np.array([[side, height, -0.15] for height in heights for side in (0.0, 0.01)])
    faces = []
    for row in range(len(heights) - 1):
        low, high = 2 * row, 2 * row + 2
        faces += [[low, low + 1, high + 1], [low, high + 1, high]]
    faces = np.array(faces)
    middles = points[faces].mean(1)[:, 1]
    part_of = np.where(middles < 1.3, 0, np.where(middles < 1.6, 3, 1))
    weights = np.zeros((len(points), len(NAMES)))
    weights[:, NAMES.index("Hips")] = 1.0
    return points, faces, part_of, weights, heights


def test_a_rigged_still_rides_its_joints_without_a_crack():
    points, faces, part_of, weights, heights = strip()
    out = still_rig.rigid(points, faces, part_of, weights, NAMES)
    assert np.allclose(out.sum(1), 1.0)
    height = points[:, 1]
    head, chest = out[:, NAMES.index("Head")], out[:, NAMES.index("Chest")]
    assert np.allclose(head[height > 1.6 + still_rig.SEAM + 0.01], 1.0)
    assert np.allclose(chest[(height > 1.3 + 0.01) & (height < 1.6 - still_rig.SEAM - 0.01)], 1.0)
    seam = np.argmin(np.abs(height - 1.6))
    assert 0.3 < head[seam] < 0.7 and 0.3 < chest[seam] < 0.7
    column = out[0::2]
    assert np.abs(np.diff(column, axis=0)).max() < 1 / 3
    assert chest[np.argmin(np.abs(height - 1.29))] > 0.9 and chest[height < 1.3 - still_rig.EASE_REACH].max() == 0.0

    nod = np.repeat(np.eye(4)[None, None], len(NAMES), axis=1)
    pivot = np.array([0.0, 1.6, 0.0])
    nod[0, NAMES.index("Head"), :3, :3] = Rotation.from_euler("x", 10, degrees=True).as_matrix()
    nod[0, NAMES.index("Head"), :3, 3] = pivot - nod[0, NAMES.index("Head"), :3, :3] @ pivot
    order, kept = still_rig.strongest(out)
    most, _, _ = still_rig.stretch(points, faces, order, kept, nod)
    assert max(most) < 1.5
    cracked = weights.copy()
    cracked[height > 1.6] = np.eye(len(NAMES))[NAMES.index("Head")]
    cracked[(height >= 1.3) & (height <= 1.6)] = np.eye(len(NAMES))[NAMES.index("Chest")]
    order, kept = still_rig.strongest(cracked)
    assert max(still_rig.stretch(points, faces, order, kept, nod)[0]) > 1.5

    beside = points[(height > 1.35) & (height < 1.55)] + [0.0, 0.0, 0.02]
    loose = np.r_[points, beside]
    start = len(points)
    loose_faces = [faces] + [[[start + 2 * row, start + 2 * row + 1, start + 2 * row + 3],
                              [start + 2 * row, start + 2 * row + 3, start + 2 * row + 2]]
                             for row in range(len(beside) // 2 - 1)]
    loose_faces = np.concatenate([np.asarray(rows).reshape(-1, 3) for rows in loose_faces])
    loose_weights = np.r_[weights, weights[:len(beside)]]
    eased = still_rig.rigid(loose, loose_faces, np.r_[part_of, np.zeros(len(loose_faces) - len(faces), int)],
                            loose_weights, NAMES)
    assert np.allclose(eased[start:, NAMES.index("Hips")], 1.0)

    stepped = weights.copy()
    stepped[height >= 1.0] = np.eye(len(NAMES))[NAMES.index("Chest")]
    fixed = height > 1.5
    smooth = still_rig.eased_cliffs(points, faces, stepped, fixed)
    assert np.allclose(smooth.sum(1), 1.0) and np.allclose(smooth[fixed], stepped[fixed])
    assert np.abs(np.diff(smooth[0::2], axis=0)).max() < 0.2

    box = trimesh.creation.box()
    cut = trimesh.Trimesh(box.vertices, box.faces[2:], process=False)
    shut = still_rig.closed(cut)
    assert still_rig.open_edges(cut) > 0 and still_rig.open_edges(shut) == 0 and shut.is_winding_consistent

    mesh = trimesh.Trimesh(points, faces, process=False)
    stray = part_of.copy()
    stray[10] = still_rig.PARTS.index("backpack")
    assert still_rig.kept_pieces(mesh, stray)[10] == part_of[10]

    sights = still_rig.directions(still_rig.SIGHTS)
    assert np.allclose(np.linalg.norm(sights, axis=1), 1.0)
    assert (sights.max(0) > 0.9).all() and (sights.min(0) < -0.9).all()
