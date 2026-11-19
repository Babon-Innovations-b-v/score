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
- a second, smaller visor piece apart from the visor (a dark seam round the helmet's rim) stays visor, or the largest
  piece is not kept whole (`one_visor`);
- the sphere's sight lines are not spread over both halves of every axis (`directions`);
- a box painted red on its left side and blue elsewhere, stood (halved and lifted) and laid on a new map, reads
  back at each face's middle a colour other than its own (`own_maps` not taking the point back into the still's frame
  with `taken_back`, or reading the wrong texture place: the seams and panels of the still's own paint lost), the
  unwrap changes a face, or a texel outside every chart stays black (`bled`).
- a person's still (`parts_of(..., person=True)`) has a helmet, visor or backpack face (a dark face read as a visor
  and held rigid), or its head's faces are not all its head, or its head is held rigid (eased over hair resting on the
  shoulders, it hung the stairwell woman's sleeves from her head).
- a person's flat shoes 3 cm longer than the body's feet and 1 cm aside (`feet_fitted`) are not laid heel to toe on
  the body's foot skin, centred on it and pitched onto its rising sole, or a point above the ankle's blend moves (the stairwell woman's shoes stood
  2 cm in every tread and 18 cm under the next step).
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
    visor, helmet = still_rig.PARTS.index("visor"), still_rig.PARTS.index("helmet")
    two = np.where(part_of == still_rig.PARTS.index("suit"), part_of, helmet)
    two[-40:-10], two[-60:-56] = visor, visor
    one = still_rig.one_visor(mesh, two)
    assert (one[-40:-10] == visor).all() and (one[-60:-56] == helmet).all()

    sights = still_rig.directions(still_rig.SIGHTS)
    assert np.allclose(np.linalg.norm(sights, axis=1), 1.0)
    assert (sights.max(0) > 0.9).all() and (sights.min(0) < -0.9).all()

    painted = trimesh.creation.box()
    painted.vertices[:, 1] *= 2.0
    left = painted.face_normals[:, 0] < -0.5
    picture = np.zeros((8, 8, 3), np.uint8)
    picture[:, :4] = [200, 40, 40]
    picture[:, 4:] = [40, 40, 200]
    from PIL import Image
    places = np.where(left[:, None, None], [0.25, 0.5], [0.75, 0.5]) * np.ones((1, 3, 1))
    split = trimesh.Trimesh(painted.vertices[painted.faces].reshape(-1, 3), np.arange(36).reshape(-1, 3),
                            process=False)
    split.visual = trimesh.visual.TextureVisuals(uv=places.reshape(-1, 2), image=Image.fromarray(picture))
    split.visual.material = trimesh.visual.material.PBRMaterial(baseColorTexture=Image.fromarray(picture))
    source = still_rig.Source(split, split.faces)
    stood = painted.vertices * 0.5 + [0.0, 1.0, 0.0]
    mapping, faces_on, laid = still_rig.unwrapped(stood, painted.faces, painted.vertex_normals, size=64)
    assert np.allclose(stood[mapping][faces_on], stood[painted.faces])
    maps, report = still_rig.own_maps(stood[mapping], faces_on, laid, still_rig.taken_back(painted.vertices, stood),
                                      source, {"red": "#c83030", "blue": "#3030c8"}, size=64)
    texture = maps["base_color"].astype(float)
    for side, colour in ((left, (200, 40, 40)), (~left, (40, 40, 200))):
        middle = laid[faces_on[side]].mean(1)
        read = still_rig.bilinear(texture / 255.0, middle) * 255.0
        assert np.abs(read - colour).max() < 20
    assert (maps["base_color"].reshape(-1, 3).sum(1) > 0).all() and len(report) == 2

    person = trimesh.creation.icosphere(subdivisions=3, radius=0.1)
    person.vertices += [0.0, 1.65, 0.0]
    person = trimesh.util.concatenate([person, trimesh.creation.box((0.4, 0.6, 0.2), trimesh.transformations
                                                                    .translation_matrix([0.0, 1.1, 0.0]))])
    joints = ["Hips", "Chest", "Neck1", "Head", "HeadEnd"]
    bind = np.repeat(np.eye(4)[None], len(joints), axis=0)
    bind[:, 1, 3] = [1.0, 1.3, 1.5, 1.6, 1.75]
    dark = np.full((len(person.vertices), 3), 0.8)
    dark[person.vertices[:, 2] > 0.05] = 0.1  # the face's front as dark as a visor
    found = still_rig.parts_of(person, dark, None, joints, bind, person=True)
    on_head = person.triangles_center[:, 1] > 1.52
    assert (found[on_head] == still_rig.PARTS.index("head")).all()
    assert set(found[~on_head]) == {still_rig.PARTS.index("suit")} and "head" not in still_rig.RIGID

    feet = {}
    for side, x in (("Left", 0.1), ("Right", -0.1)):
        skin = np.array([[x, y + 0.1 * (z + 0.08), z] for z in np.linspace(-0.08, 0.18, 14)
                         for y in (0.0, 0.04, 0.08)])  # the sole rises 2.6 cm heel to toe, as SOMA's
        feet[side] = (skin, float(skin[skin[:, 2] < 0.08, 1].max()))
    shoe = np.array([[side * 0.1 + 0.012, y, z] for side in (1, -1) for z in np.linspace(-0.065, 0.213, 15)
                     for y in (0.0, 0.05)] + [[side * 0.1, y, 0.0] for side in (1, -1) for y in (0.3, 0.45)])
    laid = still_rig.feet_fitted(trimesh.Trimesh(shoe, np.zeros((0, 3), int), process=False), feet).vertices
    for side in (1, -1):
        sole = laid[(np.sign(laid[:, 0]) == side) & (shoe[:, 1] == 0.0)]
        assert np.allclose([sole[:, 2].min(), sole[:, 2].max()], [-0.08, 0.18], atol=1e-6)
        assert np.allclose(sole[:, 0].mean(), side * 0.1, atol=1e-6)
        assert np.allclose(sole[:, 1], 0.1 * (sole[:, 2] + 0.08), atol=1e-3)
    above = shoe[:, 1] > feet["Left"][1] + still_rig.ANKLE_BLEND
    assert np.allclose(laid[above], shoe[above])
