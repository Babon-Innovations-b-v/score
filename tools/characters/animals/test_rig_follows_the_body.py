"""The body decides an animal's rig (spine.py, legs.py): a fish's spine runs from its thicker head end to its tail
along its level long axis, every point split between the two bones it lies between, smoothly, its fins following the
bone beside them; a four-legged body faces the end its head reaches up from, its legs are the four chains that end
lowest (a hanging tail is none), named front and back, left and right, and a skeleton without four is refused a walk;
a foot slides back evenly on the ground and swings forward in the air. The route runs its machine steps with the
runner python under the run's own PROPS_HOME (route.CLOUD_PYTHON).

Made-up bodies here (a fish cloud, a standing cloud, a dog's skeleton with and without a hanging tail or a fourth
leg) whose answers are set by how they are made; one test asks them all whether the rig follows the body.

Breaks that turn test_the_rig_follows_the_body red (each applied once and seen red, 2026-10-26; again after the fold,
2026-11-13):
- body_axes' `if back > front:` made `if back < front:` (the spine runs from the tail).
- spine_weights' `weights[rows, upper] += share` dropped (a point's weights no longer sum to one).
- spine_weights' `share = place - lower` made `share = np.round(place - lower)` (each point wholly on one bone: a
  crease where two meet along the spine).
- forward_axis' `>` made `<` (the standing body faces its tail).
- name_legs' side sort `-heads[chain[0]] @ ... side` made `+` (the left legs named right).
- leg_chains' `key=lambda joint: height[joint]` made `-height[joint]` (the highest ends first: the hanging tail's
  tip, 0.1 up, is taken before the feet at 0.02).
- name_legs' `if len(chains) != 4:` made `if False:` (the three-legged dog is not refused for its legs).
- foot_path's `stride * (0.5 - phase / duty)` made `stride * (0.5 - (phase / duty) ** 2)` (the standing foot slides
  back unevenly).
- route.py's `CLOUD_PYTHON = HOME / "env/bin/python"` made `pathlib.Path.home() / ".farm-factory-props/env/bin/python"`.
"""
import os
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import legs  # noqa: E402
import spine  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
# The made-up dog's legs: their hip's place ahead and to the side, and the joint they hang from (0 the hips, 1 the
# chest).
DOG_LEGS = {"fl": (0.3, 0.08, 1), "fr": (0.3, -0.08, 1), "bl": (0.0, 0.08, 0), "br": (0.0, -0.08, 0)}
# Each skeleton row: what it is, the legs it has, where its tail's tip (joint 5) hangs, and what its walk is: None when
# its four legs are named, else the words the refusal carries.
SKELETONS = [
    ("a dog", tuple(DOG_LEGS), [-0.25, 0, 0.45], None),
    ("a dog whose tail hangs to the ground", tuple(DOG_LEGS), [-0.3, 0, 0.1], None),
    ("a three-legged dog", ("fl", "bl", "br"), [-0.25, 0, 0.45], "four legs"),
]
TAIL_TIP = 5


def fish_points():
    """A made-up fish along +x with its head at +x: a thick ellipsoid body and a thin tall tail fin behind it."""
    generator = np.random.default_rng(3)
    body = generator.normal(size=(4000, 3)) * [0.08, 0.02, 0.05] + [0.02, 0, 0]
    fin = generator.uniform([-0.18, -0.002, -0.06], [-0.1, 0.002, 0.06], size=(800, 3))
    return np.vstack([body, fin])


def standing_points():
    """A made-up standing animal along +x, its head reaching up at +x and its tail held out level at -x."""
    generator = np.random.default_rng(5)
    body = generator.uniform([-0.4, -0.1, 0.4], [0.4, 0.1, 0.6], size=(3000, 3))
    head = generator.uniform([0.35, -0.06, 0.6], [0.55, 0.06, 0.85], size=(500, 3))
    tail = generator.uniform([-0.7, -0.02, 0.5], [-0.4, 0.02, 0.6], size=(200, 3))
    feet = generator.uniform([-0.35, -0.1, 0.0], [0.35, 0.1, 0.4], size=(800, 3))
    return np.vstack([body, head, tail, feet])


def dog_skeleton(kept, tail_tip):
    """A small dog's skeleton, z up, head at +x, left at +y: a spine with a neck and head, a tail (its tip joint 5 at
    `tail_tip`), and the `kept` legs of DOG_LEGS, three joints each ending on the ground."""
    heads, parents = [[0, 0, 0.5]], [-1]

    def add(position, parent):
        heads.append(position)
        parents.append(parent)
        return len(heads) - 1

    chest = add([0.3, 0, 0.55], 0)
    neck = add([0.4, 0, 0.7], chest)
    add([0.5, 0, 0.8], neck)
    tail = add([-0.1, 0, 0.55], 0)
    add(list(tail_tip), tail)
    for name in kept:
        x, y, parent = DOG_LEGS[name]
        hip = add([x, y, 0.45], [0, chest][parent])
        knee = add([x, y, 0.25], hip)
        add([x + 0.03, y, 0.02], knee)
    return np.array(heads), parents


def routes_runner_python(props_home):
    """route.CLOUD_PYTHON as a fresh import sees it with PROPS_HOME at `props_home`."""
    environment = {**os.environ, "PROPS_HOME": str(props_home)}
    line = "import route; print(route.CLOUD_PYTHON)"
    return subprocess.run([sys.executable, "-c", line], cwd=HERE, env=environment, capture_output=True, text=True,
                          check=True).stdout.strip()


def test_the_rig_follows_the_body(tmp_path):
    # A fish's spine: its level long axis, head end first, every point split smoothly between two bones.
    fish = fish_points()
    axes = spine.body_axes(fish)
    assert axes["along"][0] > 0.99, axes["along"]
    assert axes["up"][2] == 1.0
    joints = spine.spine_joints(fish, axes, 6)
    assert len(joints) == 7
    assert joints[0][0] > joints[-1][0]
    assert np.isclose(joints[0][0], fish[:, 0].max(), atol=0.01)
    assert np.isclose(joints[-1][0], fish[:, 0].min(), atol=0.01)
    weights = spine.spine_weights(fish, joints)
    assert weights.shape == (len(fish), 6)
    assert np.allclose(weights.sum(axis=1), 1.0)
    assert (weights >= 0).all()
    middles = (joints[:-1] + joints[1:]) / 2
    # Each probe: what it is, where it lies, the bone it follows and the least share of it it holds.
    probes = [(f"the middle of bone {bone}", middle, bone, 1.0 - 1e-9) for bone, middle in enumerate(middles)]
    probes += [("the tail's tip", joints[-1], 5, 1.0), ("the tail fin", [-0.17, 0.0, 0.05], 5, np.nextafter(0.5, 1))]
    for name, point, bone, least in probes:
        share = spine.spine_weights(np.asarray(point, np.float64)[None], joints)[0]
        assert np.isclose(share.sum(), 1.0), (name, share)
        assert np.argmax(share) == bone and least <= share[bone] <= 1.0, (name, share)
    along_the_spine = joints[0] + np.linspace(0, 1, 200)[:, None] * (joints[-1] - joints[0])
    assert np.abs(np.diff(spine.spine_weights(along_the_spine, joints), axis=0)).max() < 0.05

    # A standing body faces the end its head reaches up from, mirrored or not.
    for mirror in (1, -1):
        forward = legs.forward_axis(standing_points() * [mirror, 1, 1])
        assert forward[0] * mirror > 0.98, (mirror, forward)

    # A skeleton's legs are the four chains that end lowest, named by where they stand; without four, no walk.
    for name, kept, tail_tip, refusal in SKELETONS:
        heads, parents = dog_skeleton(kept, tail_tip)
        chains = legs.leg_chains(heads, parents)
        assert all(len(chain) == 3 and heads[chain[-1]][2] < 0.05 for chain in chains), (name, chains)
        assert all(TAIL_TIP not in chain for chain in chains), (name, chains)
        assert len(chains) == len(kept), (name, chains)
        try:
            named = legs.name_legs(chains, heads, forward=(1, 0, 0), side=(0, 1, 0))
        except ValueError as refused:
            assert refusal is not None and refusal in str(refused), (name, refused)
            continue
        assert refusal is None, f"{name}: a walk was named"
        for leg, chain in named.items():
            hip = heads[chain[0]]
            assert (hip[0] > 0.2) if leg.startswith("front") else (hip[0] < 0.1), (name, leg, hip)
            assert (hip[1] > 0) if leg.endswith("left") else (hip[1] < 0), (name, leg, hip)

    # A foot slides back evenly on the ground, half a stride ahead to half behind, and swings forward in the air.
    stride, lift = 0.4, 0.06
    standing = [legs.foot_path(phase, stride, lift) for phase in np.linspace(0, legs.DUTY, 8, endpoint=False)]
    assert all(height == 0 for _, height in standing)
    steps = np.diff([ahead for ahead, _ in standing])
    assert np.allclose(steps, steps[0]) and steps[0] < 0
    # Each point of the cycle: its phase, how far ahead and how high the foot is there, and how near it must be.
    for phase, ahead, height, near in [(0.0, stride / 2, 0.0, 1e-8), (legs.DUTY, -stride / 2, 0.0, 1e-8),
                                       (legs.DUTY + (1 - legs.DUTY) / 2, 0.0, lift, 1e-9),
                                       (0.9999, stride / 2, None, 1e-3)]:
        place = legs.foot_path(phase, stride, lift)
        assert abs(place[0] - ahead) <= near and (height is None or np.isclose(place[1], height)), (phase, place)

    # The route runs its machine steps with the runner python under the run's own PROPS_HOME.
    assert routes_runner_python(tmp_path) == f"{tmp_path}/env/bin/python"
