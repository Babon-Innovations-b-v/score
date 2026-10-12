"""Check the physics trial's measures and gates on a run written here (no Blender): a run where the drops land, the
door opens within its limits and the energy only falls passes every gate; each gate is then broken once (a drop that
ends under its target, a door past its limit, a rise while nothing drives, a body still moving and inside a static).

Run: .venv/bin/python score/stages/physics/physics_test.py
"""
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from score import checks  # noqa: E402
from score.stages import physics  # noqa: E402

FRAMES = 6
RECORD = {"drops": [{"object": "crate", "onto": "table"}], "moved": ["stool"]}
LAID = {"tops": {"crate": 0.76}}


def motion(dx):
    return [[1, 0, 0, dx], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]


def body(lowest, speed, moved=0.0):
    return {"mass": 10.0, "lowest": lowest, "speed": speed, "motions": [motion(0.0)] * (FRAMES - 1) + [motion(moved)]}


def a_run(**changes):
    """A run of six frames: the crate falls onto the table, the stool is pushed 0.5 m, the leaf opens 90 degrees."""
    run = {"frames": FRAMES, "rate": 24.0, "gravity": 1.62, "statics": 3,
           "bodies": {"crate": body([1.2, 1.1, 0.9, 0.77, 0.765, 0.765], [0, 1, 1, 0.5, 0.01, 0.0]),
                      "stool": body([0.0] * FRAMES, [0, 0.5, 0.5, 0.3, 0.0, 0.0], moved=0.5),
                      "leaf": body([0.01] * FRAMES, [0, 1, 1, 1, 0.02, 0.0])},
           "energy": [100.0, 99.0, 120.0, 140.0, 139.0, 138.5], "driven": [False, False, True, True, False, False],
           "hinges": {"leaf": {"frame": "/p/Objects/frame", "lower": 0.0, "upper": 100.0,
                               "angles": [0.0, 0.0, 30.0, 60.0, 90.0, 90.0]}},
           "joined": [["/p/Objects/frame", "leaf"]],
           "inside at start": {}, "inside at end": {"leaf": ["/p/Objects/frame/geo"]}}
    for path, value in changes.items():
        holder = run
        *parents, last = path.split(".")
        for name in parents:
            holder = holder[name]
        holder[last] = value
    return run


def answers(run):
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        middles = {"crate": [0, 1, 0], "stool": [0, 0.2, 0], "leaf": [0, 1.3, 0]}
        (folder / "measures.json").write_text(json.dumps(physics.measured(run, RECORD, LAID, middles)))
        return {check.name: check.judge(folder, {}, None).answer for check in physics.TRIAL_CHECKS}


def a_good_run_passes():
    found = answers(a_run())
    assert all(answer == checks.PASS for answer in found.values()), found


def each_gate_breaks():
    assert answers(a_run(**{"bodies.crate.lowest": [1.2, 1.0, 0.5, 0.3, 0.3, 0.3]}))["reacted"] == checks.FAIL
    assert answers(a_run(**{"hinges.leaf.angles": [0.0, 0.0, 30.0, 60.0, 104.0, 99.0]}))["hinge"] == checks.FAIL
    assert answers(a_run(energy=[100.0, 99.0, 120.0, 140.0, 139.0, 145.0]))["energy"] == checks.FAIL
    assert answers(a_run(**{"bodies.leaf.speed": [0, 1, 1, 1, 0.5, 0.4]}))["at rest"] == checks.FAIL
    inside = {"leaf": ["/p/Objects/frame/geo"], "crate": ["/p/Objects/table/geo"]}
    assert answers(a_run(**{"inside at end": inside}))["at rest"] == checks.FAIL


def the_rises_are_per_undriven_stretch():
    assert physics.energy_rises([10.0, 10.5, 30.0, 20.0, 21.0], [False, False, True, False, False]) == \
        {0: (0.5, 10.0), 3: (1.0, 20.0)}


if __name__ == "__main__":
    a_good_run_passes()
    each_gate_breaks()
    the_rises_are_per_undriven_stretch()
    print("physics_test: ok")
