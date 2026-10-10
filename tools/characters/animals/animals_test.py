"""Checks for the animal route's plain-Python pieces: the fish's spine rig, the walk's legs and the runner's Python the
route calls, without Blender."""
import os
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import legs  # noqa: E402
import spine  # noqa: E402


def fish_points():
    """A made-up fish along +x with its head at +x: a thick ellipsoid body and a thin tall tail fin behind it."""
    generator = np.random.default_rng(3)
    body = generator.normal(size=(4000, 3)) * [0.08, 0.02, 0.05] + [0.02, 0, 0]
    fin = generator.uniform([-0.18, -0.002, -0.06], [-0.1, 0.002, 0.06], size=(800, 3))
    return np.vstack([body, fin])


def test_the_spine_runs_from_the_head_along_the_body():
    points = fish_points()
    axes = spine.body_axes(points)
    assert axes["along"][0] > 0.99, axes["along"]
    assert axes["up"][2] == 1.0
    joints = spine.spine_joints(points, axes, 6)
    assert len(joints) == 7
    assert joints[0][0] > joints[-1][0]
    assert np.isclose(joints[0][0], points[:, 0].max(), atol=0.01)
    assert np.isclose(joints[-1][0], points[:, 0].min(), atol=0.01)


def test_spine_weights_sum_to_one_and_follow_the_bone_beside_a_point():
    points = fish_points()
    joints = spine.spine_joints(points, spine.body_axes(points), 6)
    weights = spine.spine_weights(points, joints)
    assert weights.shape == (len(points), 6)
    assert np.allclose(weights.sum(axis=1), 1.0)
    assert (weights >= 0).all()
    middles = (joints[:-1] + joints[1:]) / 2
    for bone, middle in enumerate(middles):
        assert np.argmax(spine.spine_weights(middle[None], joints)[0]) == bone
    tail_tip = spine.spine_weights(joints[-1][None], joints)[0]
    assert tail_tip[-1] == 1.0
    fin_point = np.array([[-0.17, 0.0, 0.05]])
    assert np.isclose(spine.spine_weights(fin_point, joints)[0].sum(), 1.0)
    assert spine.spine_weights(fin_point, joints)[0][-1] > 0.5


def test_weights_change_smoothly_along_the_spine():
    joints = np.array([[float(step), 0, 0] for step in range(5, -1, -1)])
    line = np.array([[position, 0, 0] for position in np.linspace(5, 0, 200)])
    weights = spine.spine_weights(line, joints)
    assert np.abs(np.diff(weights, axis=0)).max() < 0.05


def dog_skeleton():
    """A small dog's skeleton, z up, head at +x, left at +y: a spine with a neck and head, a tail, four legs of three
    joints each ending on the ground."""
    heads, parents = [[0, 0, 0.5]], [-1]

    def add(position, parent):
        heads.append(position)
        parents.append(parent)
        return len(heads) - 1

    chest = add([0.3, 0, 0.55], 0)
    neck = add([0.4, 0, 0.7], chest)
    add([0.5, 0, 0.8], neck)
    tail = add([-0.1, 0, 0.55], 0)
    add([-0.25, 0, 0.45], tail)
    for name, (x, y, parent) in {"fl": (0.3, 0.08, chest), "fr": (0.3, -0.08, chest),
                                 "bl": (0.0, 0.08, 0), "br": (0.0, -0.08, 0)}.items():
        hip = add([x, y, 0.45], parent)
        knee = add([x, y, 0.25], hip)
        add([x + 0.03, y, 0.02], knee)
    return np.array(heads), parents


def test_a_standing_body_faces_the_end_its_head_reaches_up_from():
    generator = np.random.default_rng(5)
    body = generator.uniform([-0.4, -0.1, 0.4], [0.4, 0.1, 0.6], size=(3000, 3))
    head = generator.uniform([0.35, -0.06, 0.6], [0.55, 0.06, 0.85], size=(500, 3))
    tail = generator.uniform([-0.7, -0.02, 0.5], [-0.4, 0.02, 0.6], size=(200, 3))
    feet = generator.uniform([-0.35, -0.1, 0.0], [0.35, 0.1, 0.4], size=(800, 3))
    forward = legs.forward_axis(np.vstack([body, head, tail, feet]))
    assert forward[0] > 0.98, forward
    forward = legs.forward_axis(np.vstack([body, head, tail, feet]) * [-1, 1, 1])
    assert forward[0] < -0.98, forward


def test_the_legs_are_the_four_chains_that_end_lowest():
    heads, parents = dog_skeleton()
    chains = legs.leg_chains(heads, parents)
    assert len(chains) == 4
    assert all(len(chain) == 3 for chain in chains)
    assert all(heads[chain[-1]][2] < 0.05 for chain in chains)
    named = legs.name_legs(chains, heads, forward=(1, 0, 0), side=(0, 1, 0))
    assert heads[named["front_left"][0]][0] > 0.2 and heads[named["front_left"][0]][1] > 0
    assert heads[named["back_right"][0]][0] < 0.1 and heads[named["back_right"][0]][1] < 0


def test_a_hanging_tail_is_not_a_leg():
    heads, parents = dog_skeleton()
    heads = heads.copy()
    heads[5] = [-0.3, 0, 0.1]
    chains = legs.leg_chains(heads, parents)
    assert len(chains) == 4 and all(5 not in chain for chain in chains), chains


def test_a_skeleton_without_four_legs_is_refused_for_a_walk():
    heads, parents = dog_skeleton()
    chains = legs.leg_chains(heads, parents)[:3]
    try:
        legs.name_legs(chains, heads, (1, 0, 0), (0, 1, 0))
    except ValueError as refused:
        assert "four legs" in str(refused)
    else:
        raise AssertionError("a three-legged walk was named")


def test_a_foot_slides_back_evenly_on_the_ground_and_swings_forward_in_the_air():
    stride, lift = 0.4, 0.06
    standing = [legs.foot_path(phase, stride, lift) for phase in np.linspace(0, legs.DUTY, 8, endpoint=False)]
    assert all(height == 0 for _, height in standing)
    steps = np.diff([ahead for ahead, _ in standing])
    assert np.allclose(steps, steps[0]) and steps[0] < 0
    assert np.isclose(legs.foot_path(0.0, stride, lift)[0], stride / 2)
    assert np.isclose(legs.foot_path(legs.DUTY, stride, lift)[0], -stride / 2)
    middle = legs.foot_path(legs.DUTY + (1 - legs.DUTY) / 2, stride, lift)
    assert np.isclose(middle[1], lift) and abs(middle[0]) < 1e-9
    assert np.isclose(legs.foot_path(0.9999, stride, lift)[0], stride / 2, atol=1e-3)
    assert sorted(legs.PHASES.values()) == [0.0, 0.25, 0.5, 0.75]


def routes_runner_python(props_home):
    """route.CLOUD_PYTHON as a fresh import sees it with PROPS_HOME at `props_home`."""
    environment = {**os.environ, "PROPS_HOME": str(props_home)}
    line = "import route; print(route.CLOUD_PYTHON)"
    return subprocess.run([sys.executable, "-c", line], cwd=pathlib.Path(__file__).resolve().parent, env=environment,
                          capture_output=True, text=True, check=True).stdout.strip()


def test_the_route_calls_the_runner_python_under_props_home():
    with tempfile.TemporaryDirectory() as temporary:
        assert routes_runner_python(temporary) == f"{temporary}/env/bin/python"


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("animals_test: ok")
