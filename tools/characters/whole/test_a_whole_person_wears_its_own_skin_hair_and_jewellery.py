"""A whole person wears its own skin, hair and jewellery: the face's body laid on the clips rig's mean body comes back
on it point for point (scaled by height, moved along the floor, its limbs turned onto the mean's); hair grown over a
shell that stands off the scalp is brought down onto it with its layers kept, hair inside the skin is put out to its
clearance and hair outside left; a ring goes round the finger it is meant for (read off a toy hand's skin), a watch
round its wrist with its case on the back of the wrist, a chain round the neck on its skin and moving with it; and
`faults` names a piece pushed into the skin. Each row is one toy (no SOMA, Newton or Blender).

Breaks that turn it red (each applied once, seen red, reverted): the limbs' turns left out (`posed_like_mean`
returning its points: the toy arm 15 degrees off the mean's); the roots' gap left out of `hair_fitted` (the hair left
standing off the scalp); the hair pushed along the nearest point's way instead of the skin's outward normal (`away`
for `normals` in `pushed_out`: a point inside left inside); the ring sized off its finger's nearest skin rather than
its farthest (`.min()` for `.max()` of the radius in `ring`: the ring inside the finger); the fingers counted from the
thickest (`sizes[-1] < sizes[0]` turned: the ring on the middle finger); the watch's case on the wrist's front
(`-back`); `deepest` reading only the first frame (a ring pushed in on the last frame passes); `skin_carried` carrying
only the first frame (the chain left behind as the neck turns)."""
import numpy as np
import pytest
import trimesh

from tools.characters import whole
from tools.characters.whole import jewellery

NAMES = np.array(["Chest", "LeftArm"])


def toy_mean():
    """A torso box on the floor and an arm tube hanging from its left shoulder, each carried by one joint."""
    torso = trimesh.creation.box(extents=[0.3, 0.5, 0.2]).subdivide_to_size(0.05)
    torso.apply_translation([0.0, 1.25, 0.0])
    arm = trimesh.creation.cylinder(radius=0.04, height=0.5, sections=16).subdivide_to_size(0.05)
    arm.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2.0, [1, 0, 0]))
    arm.apply_translation([0.2, 1.2, 0.0])
    floor = trimesh.creation.box(extents=[0.1, 1.0, 0.1])
    floor.apply_translation([0.0, 0.5, 0.0])
    points = np.concatenate([torso.vertices, arm.vertices, floor.vertices])
    weights = np.zeros((len(points), 2))
    weights[:len(torso.vertices), 0] = 1.0
    weights[len(torso.vertices):len(torso.vertices) + len(arm.vertices), 1] = 1.0
    weights[len(torso.vertices) + len(arm.vertices):, 0] = 1.0
    return points, weights


def toy_hand():
    """A palm and four fingers along +x from a wrist at the origin, the little finger the thinnest, the fingers
    widest across (z): skin points, faces, and the finger the ring goes on (counted from the little one)."""
    palm = trimesh.creation.box(extents=[0.09, 0.025, 0.1]).subdivide_to_size(0.006)
    palm.apply_translation([0.045, 0.0, 0.0])
    pieces = [palm]
    for number, radius in enumerate((0.0065, 0.0075, 0.008, 0.0075)):
        finger = trimesh.creation.cylinder(radius=radius, segment=[[0.085, 0.0, 0.0], [0.17, 0.0, 0.0]],
                                           sections=32).subdivide_to_size(0.003)
        finger.apply_scale([1.0, 1.0, 1.25])
        finger.apply_translation([0.0, 0.0, -0.039 + 0.026 * number])
        pieces.append(finger)
    joined = trimesh.util.concatenate(pieces)
    return np.asarray(joined.vertices), np.asarray(joined.faces)


def tube_skin(radius, start, end, sections=48):
    """A dense tube's surface from `start` to `end` along x (points, faces)."""
    tube = trimesh.creation.cylinder(radius=radius, segment=[start, end], sections=sections)
    tube = tube.subdivide_to_size(0.002)
    return np.asarray(tube.vertices), np.asarray(tube.faces)


@pytest.mark.parametrize("case", ["laid on the mean", "hair brought onto the scalp", "hair kept out",
                                  "ring round its finger",
                                  "watch round its wrist", "chain round the neck", "ring pushed in",
                                  "chain carried by the skin"])
def test_a_whole_person_wears_its_own_skin_hair_and_jewellery(case):
    if case == "laid on the mean":
        mean, weights = toy_mean()
        arm = weights[:, 1] > 0.5
        low = mean.copy()
        turn = trimesh.transformations.rotation_matrix(np.radians(15.0), [0, 0, 1], point=[0.2, 1.45, 0.0])
        low[arm] = trimesh.transform_points(low[arm], turn)
        low = low * 0.95 + [0.0, 0.0, 0.05]
        scale, shift = whole.laid(low, mean, weights[:, 0] > 0.5)
        assert scale == pytest.approx(1.0 / 0.95)
        turns = whole.limb_turns(low * scale + shift, mean, weights, NAMES)
        back = whole.posed_like_mean(low * scale + shift, weights, turns)
        assert np.abs(back - mean).max() < 1e-6
    if case == "hair kept out":
        sphere = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
        points = np.array([[0.0, 0.09, 0.0], [0.105, 0.0, 0.0], [0.0, 0.0, 0.1005]])
        moved, short = whole.pushed_out(points, np.asarray(sphere.vertices), np.asarray(sphere.faces),
                                        np.full(3, 0.002))
        radii = np.linalg.norm(moved, axis=1)
        assert radii[0] > 0.1015 and radii[2] > 0.1015
        assert moved[1] == pytest.approx(points[1])
        assert short == pytest.approx(0.012, abs=0.001)
    if case in ("ring round its finger", "ring pushed in"):
        skin, faces = toy_hand()
        points, _, _ = jewellery.ring(skin, faces, skin, np.zeros(3), 1)
        centre = points.mean(axis=0)
        assert centre[2] == pytest.approx(-0.013, abs=0.002)  # the ring finger, next to the little one
        assert 0.1 < centre[0] < 0.13  # on the finger, not round the palm
        inner = np.hypot(points[:, 1] - centre[1], points[:, 2] - centre[2]).min()
        assert inner >= 0.0075 * 1.25 + jewellery.RING["clear"] - 2e-4
        frames = np.repeat(points[None], 3, axis=0)
        if case == "ring pushed in":
            frames[-1] = centre + (frames[-1] - centre) * np.array([1.0, 0.6, 0.6])
        into = jewellery.deepest(frames, np.repeat(skin[None], 3, axis=0), faces)
        found = {"into the skin mm": {"left_ring": round(into * 1000.0, 2)}}
        assert bool(jewellery.faults(found)) == (case == "ring pushed in"), found
    if case == "watch round its wrist":
        skin, _ = tube_skin(0.03, [0.0, 0.0, 0.0], [0.0, -0.25, 0.0])
        made = jewellery.watch(skin, np.array([0.0, 0.0, 0.0]), np.array([0.0, -0.25, 0.0]),
                               np.array([1.0, 0.0, 0.0]))
        strap = made["strap"][0]
        assert np.hypot(strap[:, 0], strap[:, 2]).min() >= 0.03 + jewellery.WATCH["clear"] - 1e-4
        assert made["case"][0][:, 0].min() > 0.03  # on the back of the wrist (+x), outside the strap
    if case == "chain round the neck":
        neck, faces = tube_skin(0.05, [0.0, 1.3, 0.0], [0.0, 1.7, 0.0])
        points, _, _ = jewellery.necklace(neck, faces, np.array([0.0, 1.5, 0.0]), np.array([0.0, 1.25, 0.0]))
        radii = np.hypot(points[:, 0], points[:, 2])
        assert radii.min() >= 0.05 + jewellery.CHAIN["clear"] - 2e-4  # the tube's own facets
        assert radii.max() < 0.05 + jewellery.CHAIN["clear"] + 2.0 * jewellery.CHAIN["wire"] + 1e-3
        assert points[:, 1].min() < points[:, 1].max() - 0.04  # it falls at the front
    if case == "chain carried by the skin":
        neck, faces = tube_skin(0.05, [0.0, 1.3, 0.0], [0.0, 1.7, 0.0])
        points, _, _ = jewellery.necklace(neck, faces, np.array([0.0, 1.5, 0.0]), np.array([0.0, 1.25, 0.0]))
        turn = trimesh.transformations.rotation_matrix(np.radians(20.0), [1, 0, 0], point=[0.0, 1.3, 0.0])
        frames = np.stack([neck, trimesh.transform_points(neck, turn)])
        carried = whole.skin_carried(whole.skin_bound(points, neck, faces), frames, faces)
        assert len(carried) == 2
        assert np.abs(carried[1] - trimesh.transform_points(points, turn)).max() < 1e-3
    if case == "hair brought onto the scalp":
        sphere = trimesh.creation.icosphere(subdivisions=4, radius=0.1)
        directions = np.array([[0.0, 1.0, 0.0], [0.6, 0.8, 0.0], [-0.6, 0.8, 0.0]])
        strands = np.concatenate([directions * radius for radius in (0.115, 0.12, 0.125)])  # root, then layers out
        order = np.array([0, 3, 6, 1, 4, 7, 2, 5, 8])
        fitted = whole.hair_fitted(np.array([3, 3, 3]), strands[order], np.asarray(sphere.vertices),
                                   np.asarray(sphere.faces))
        radii = np.linalg.norm(fitted, axis=1).reshape(3, 3)
        assert radii[:, 0] == pytest.approx(0.1 + whole.HAIR_OFF_M, abs=5e-4)
        assert radii[:, 2] == pytest.approx(0.1 + whole.HAIR_OFF_M + 0.01, abs=5e-4)
