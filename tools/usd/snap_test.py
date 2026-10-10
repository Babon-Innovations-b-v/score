"""Check the snap on places made here: a box lifted 0.3 m drops to rest on the floor within 1 cm, a box on another
drops onto its top, a box slid toward a wall stops touching it without going in and one laid into it backs out, a free spot is never inside another
box and stands on the floor, the same seed gives the same spot, and a snapped pose written into the layout is where
the exported stage lays the box.

Run: .venv/bin/python tools/usd/snap_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collide  # noqa: E402
import export  # noqa: E402
import export_test  # noqa: E402
import settle_test  # noqa: E402
import snap  # noqa: E402
import triage_test  # noqa: E402

PLACE = triage_test.PLACE


def made_models(folder):
    """A 1 m box and a wall 4 m long, 2 m high and 0.2 m thick, both standing on their foot."""
    (folder / "models").mkdir()
    export_test.box_gltf(folder / "models")
    export_test.box_gltf(folder / "models", "wall", trimesh.creation.box(bounds=((-0.1, 0.0, -2.0), (0.1, 2.0, 2.0))))


def laid(folder, pieces, rows):
    """A place of these pieces, exported, read as the snap reads it."""
    made_models(folder)
    return snap.read_place(triage_test.place_of(folder, pieces, rows))


def lowest_after(place, name, offset):
    return float(place["objects"][name].bounds[0][1] + offset[1])


def a_lifted_box_drops_onto_the_floor_and_onto_a_box():
    with tempfile.TemporaryDirectory() as temporary:
        place = laid(pathlib.Path(temporary), [("crate", "box", (0, 0.3, 0)), ("crate", "box", (3, 0, 0)),
                                               ("crate", "box", (3.2, 1.6, 0.1))], [triage_test.row("crate")])
        problems = []
        offset = snap.snap_down(place, "crate_1")
        if not 0.0 <= lowest_after(place, "crate_1", offset) <= 0.01 or np.abs(offset[[0, 2]]).max() > 0:
            problems.append(f"the box lifted 0.3 m moved by {offset}, not straight down onto the floor")
        offset = snap.snap_down(place, "crate_3")
        if not 1.0 <= lowest_after(place, "crate_3", offset) <= 1.01:
            problems.append(f"the box over another drops to {lowest_after(place, 'crate_3', offset):.3f}, not onto "
                            "its top at 1 m")
        return problems


def a_box_slid_toward_a_wall_stops_touching_it():
    with tempfile.TemporaryDirectory() as temporary:
        place = laid(pathlib.Path(temporary), [("crate", "box", (0, 0, 0.3)), ("wall", "wall", (3, 0, 0))],
                     [triage_test.row("crate"), triage_test.row("wall", fixed=True)])
        offset = snap.snap_to(place, "crate_1", [(1.0, 0.0)])
        scene = collide.Scene()
        for name in ("crate_1", "wall_1"):
            mesh = place["objects"][name]
            scene.add(name, name, mesh.vertices, mesh.faces, np.eye(4))
        problems = []
        if abs(offset[0] - (3 - 0.1 - 0.5 - snap.CLEARANCE)) > 1e-3 or np.abs(offset[1:]).max() > 0:
            problems.append(f"the box slid toward the wall moved by {offset}, not 2.4 m along x")
        if scene.intersection_test("crate_1", "wall_1", offset):
            problems.append("the slid box went into the wall")
        if not scene.intersection_test("crate_1", "wall_1", offset + [0.01, 0.0, 0.0]):
            problems.append("the slid box stopped more than 1 cm short of the wall")
        try:
            snap.snap_to(place, "crate_1", [(-1.0, 0.0)])
            problems.append("a slide with nothing in its way did not refuse")
        except ValueError:
            pass
        return problems


def a_box_laid_into_a_wall_is_slid_back_out():
    """A box laid 4 cm into a wall (furniture into a skirting), slid toward it, backs out to stop 2 mm short."""
    with tempfile.TemporaryDirectory() as temporary:
        place = laid(pathlib.Path(temporary), [("crate", "box", (2.44, 0, 0.3)), ("wall", "wall", (3, 0, 0))],
                     [triage_test.row("crate"), triage_test.row("wall", fixed=True)])
        offset = snap.snap_to(place, "crate_1", [(1.0, 0.0)])
        wanted = 3 - 0.1 - 0.5 - snap.CLEARANCE - 2.44
        return [] if abs(offset[0] - wanted) < 1e-3 and np.abs(offset[1:]).max() == 0 else [
            f"the box laid into the wall moved by {offset}, not {wanted:.3f} m back along x"]


def a_free_spot_is_free_and_stands():
    with tempfile.TemporaryDirectory() as temporary:
        crowded = [("crate", "box", (across, 0, along)) for across in (0, 1.6, 3.2) for along in (0, 1.6, 3.2)]
        place = laid(pathlib.Path(temporary), [("loose", "box", (8, 0.4, 8))] + crowded,
                     [triage_test.row("crate"), triage_test.row("loose")])
        scene = collide.Scene()
        for name, mesh in place["objects"].items():
            scene.add(name, name, mesh.vertices, mesh.faces, np.eye(4))
        problems, spots = [], []
        for seed in range(5):
            offset = snap.place_free(place, "loose_1", (-0.5, -0.5, 6.0, 6.0), seed=seed)
            spots.append(tuple(np.round(offset, 6)))
            inside = [other for other in place["objects"] if other != "loose_1"
                      and scene.intersection_test("loose_1", other, offset)]
            if inside:
                problems.append(f"seed {seed}: the free spot lies inside {inside}")
            if not 0.0 <= lowest_after(place, "loose_1", offset) <= 0.01:
                problems.append(f"seed {seed}: the free spot's box stands at {lowest_after(place, 'loose_1', offset)}")
        if len(set(spots)) < 2:
            problems.append("five seeds gave one spot")
        if tuple(np.round(snap.place_free(place, "loose_1", (-0.5, -0.5, 6.0, 6.0), seed=0), 6)) != spots[0]:
            problems.append("the same seed gave another spot")
        return problems


def a_written_pose_is_where_the_stage_lays_it():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        place = laid(folder, [("crate", "box", (2, 0.3, 1))], [triage_test.row("crate")])
        pose = snap.proposed_pose(place, "crate_1", snap.snap_down(place, "crate_1"), None)
        (folder / "inventory.json").write_text(json.dumps(
            {"scene": PLACE, "rows": [dict(triage_test.row("crate"), at=[{"x": 2, "z": 1, "y": 0.3, "facing": 0}])]}))
        snap.write_pose("crate_1", np.asarray(pose["matrix"]), None, folder / "inventory.json", folder / "kit.json")
        spot = json.loads((folder / "inventory.json").read_text())["rows"][0]["at"][0]
        (folder / "inventory.json").write_text(json.dumps({"scene": PLACE, "rows": [triage_test.row("crate")]}))
        again = export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                              inventory_path=folder / "inventory.json")
        problems = []
        if abs(spot["y"] - snap.CLEARANCE) > 1e-4:
            problems.append(f"the written spot is {spot}, not lifted {snap.CLEARANCE} m")
        off = np.abs(settle_test.stage_matrix(again, "crate_1") - np.asarray(pose["matrix"])).max()
        if off > 1e-4:
            problems.append(f"the exported box stands {off:.5f} off the snapped pose")
        return problems


CHECKS = (a_lifted_box_drops_onto_the_floor_and_onto_a_box, a_box_slid_toward_a_wall_stops_touching_it,
          a_box_laid_into_a_wall_is_slid_back_out,
          a_free_spot_is_free_and_stands, a_written_pose_is_where_the_stage_lays_it)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
