"""Check the reach check on places made here: two rooms joined by a doorway, a row in each, are both reached; a crate
shut in a pen with no gap is not, and fails the place; a crate on a raised block 2.4 m high is not reached until a
stair of 0.2 m steps leads up to it; a row with no object is unknown, which blocks; a dropped row is not walked to;
and the gate runs it as the `reach` check.

Run: .venv/bin/python tools/usd/reach_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import camera_paths_test  # noqa: E402
import complete  # noqa: E402
import export_test  # noqa: E402
import reach  # noqa: E402
import resting_test  # noqa: E402
import triage_test  # noqa: E402

BLOCK_HIGH = 2.4
RISE, TREAD = 0.2, 0.3


def walls(boxes):
    """Wall boxes ((x, y, z) low, (x, y, z) high) as one mesh standing on its foot."""
    return trimesh.util.concatenate([trimesh.creation.box(bounds=bounds) for bounds in boxes])


def pen():
    """Four walls 1.5 m high round a floor 3 m square, with no gap."""
    return walls([((-1.7, 0.0, -1.7), (1.7, 1.5, -1.5)), ((-1.7, 0.0, 1.5), (1.7, 1.5, 1.7)),
                  ((-1.7, 0.0, -1.5), (-1.5, 1.5, 1.5)), ((1.5, 0.0, -1.5), (1.7, 1.5, 1.5))])


def block():
    """A raised floor 4 m square and BLOCK_HIGH high."""
    return walls([((-2.0, 0.0, -2.0), (2.0, BLOCK_HIGH, 2.0))])


def stair():
    """Steps of RISE and TREAD, 1.2 m wide, from the ground at z = 2 + the stair's length up to the block's top."""
    count = int(round(BLOCK_HIGH / RISE))
    return walls([((-0.6, 0.0, 2.0 + (count - 2 - step) * TREAD),
                   (0.6, (step + 1) * RISE, 2.0 + (count - 1 - step) * TREAD))
                  for step in range(count - 1)])


def with_models(folder, shapes):
    """The test's made models: the 1 m box and each named shape."""
    (folder / "models").mkdir()
    export_test.box_gltf(folder / "models")
    for name, shape in shapes.items():
        export_test.box_gltf(folder / "models", name, shape)


def verdicts(stage, inventory_path):
    """The reach check's result on a stage, and {row: result}."""
    overall, rows, _ = reach.check(stage, resting_test.PLACE, json.loads(inventory_path.read_text()))
    return overall, {row["row"]: row["result"] for row in rows}


def rooms_joined_by_a_doorway_are_both_reached():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        with_models(folder, {"rooms": camera_paths_test.two_rooms()})
        stage = triage_test.place_of(folder, [("rooms", "rooms", (0, 0, 0)), ("crate", "box", (-2.0, 0, 0)),
                                              ("lamp", "box", (2.5, 0, 1.5))],
                                     [triage_test.row("rooms", fixed=True), triage_test.row("crate"),
                                      triage_test.row("lamp")])
        overall, rows = verdicts(stage, folder / "inventory.json")
        return [] if overall == reach.PASS else [f"two rooms with a doorway read {overall}: {rows}"]


def a_crate_shut_in_a_pen_fails():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        with_models(folder, {"pen": pen()})
        stage = triage_test.place_of(folder, [("pen", "pen", (6.0, 0, 0)), ("shut", "box", (6.0, 0, 0)),
                                              ("crate", "box", (0.0, 0, 0))],
                                     [triage_test.row("pen", fixed=True), triage_test.row("shut"),
                                      triage_test.row("crate")])
        overall, rows = verdicts(stage, folder / "inventory.json")
        want = {"pen": reach.PASS, "shut": reach.FAIL, "crate": reach.PASS}
        return [] if overall == reach.FAIL and rows == want else [f"the pen reads {overall}: {rows}, not {want}"]


def a_raised_crate_is_reached_by_its_stair_only():
    problems = []
    for with_stair in (False, True):
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            with_models(folder, {"block": block(), "stair": stair()})
            pieces = [("block", "block", (0, 0, 0)), ("up", "box", (0, BLOCK_HIGH, 0)), ("crate", "box", (5.0, 0, 0))]
            rows = [triage_test.row("block", fixed=True), triage_test.row("up"), triage_test.row("crate")]
            if with_stair:
                pieces.append(("stair", "stair", (0, 0, 0)))
                rows.append(triage_test.row("stair", fixed=True))
            stage = triage_test.place_of(folder, pieces, rows)
            _, found = verdicts(stage, folder / "inventory.json")
            want = reach.PASS if with_stair else reach.FAIL
            if found["up"] != want:
                problems.append(f"the crate on the block {'with' if with_stair else 'without'} its stair reads "
                                f"{found['up']}, not {want}")
    return problems


def a_row_with_no_object_is_unknown_and_a_dropped_one_not_walked():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        with_models(folder, {})
        stage = triage_test.place_of(folder, [("crate", "box", (0, 0, 0))],
                                     [triage_test.row("crate"), triage_test.row("rocket"),
                                      triage_test.row("gone", dropped="test: the row is not in this place")])
        overall, rows = verdicts(stage, folder / "inventory.json")
        want = {"crate": reach.PASS, "rocket": reach.UNKNOWN}
        return [] if overall == reach.UNKNOWN and rows == want else [f"the rows read {overall}: {rows}, not {want}"]


def the_gate_runs_it():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        with_models(folder, {"pen": pen()})
        stage = triage_test.place_of(folder, [("pen", "pen", (6.0, 0, 0)), ("shut", "box", (6.0, 0, 0)),
                                              ("crate", "box", (0.0, 0, 0))],
                                     [triage_test.row("pen", fixed=True), triage_test.row("shut"),
                                      triage_test.row("crate")])
        complete.run_checks(resting_test.PLACE, stage, ["reach"])
        found = {requirement["name"]: requirement["result"]
                 for requirement in complete.requirements(resting_test.PLACE, stage)}
        said = found.get("reach")
        return [] if said == complete.FAIL else [f"the gate's reach requirement reads {said}"]


CHECKS = (rooms_joined_by_a_doorway_are_both_reached, a_crate_shut_in_a_pen_fails,
          a_raised_crate_is_reached_by_its_stair_only, a_row_with_no_object_is_unknown_and_a_dropped_one_not_walked,
          the_gate_runs_it)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as no_records:
        reach.SCENES = pathlib.Path(no_records)  # the test's places have no scene record: no room floor, no ceiling
        failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
