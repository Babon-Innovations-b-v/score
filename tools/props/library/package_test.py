"""Checks of the scene package (package.py) and the outdoor place route's own steps (place_route.py), on small
meshes made here: a copy's transform, a tilted piece landing on its spot, a sound package passing, and a missing
picture, a failed model and a wrong count of copies refused; a details.json turn read as its yaw, a take split in two.

    .venv/bin/python tools/props/library/package_test.py
"""
import json
import math
import pathlib
import shutil
import sys
import tempfile

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import package  # noqa: E402
import place_route  # noqa: E402

INVENTORY = {"rows": [{"id": "crate", "count": 2}, {"id": "cable_run", "count": 1}]}


def a_run(folder):
    """A finished route run of two models: a generated crate laid twice, a code cable laid once, front up."""
    made = folder / "work" / "made"
    made.mkdir(parents=True)
    for name, size in (("crate", (1.0, 1.0, 1.0)), ("cable_run_2", (2.0, 0.1, 0.06))):
        box = trimesh.creation.box(extents=size)
        box.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(box.vertices), 2)),
                                                   material=trimesh.visual.material.SimpleMaterial())
        files = box.export(file_type="gltf")
        gltf = json.loads(files.pop("model.gltf"))
        for index, buffer in enumerate(gltf["buffers"]):
            (made / f"{name}_{index}.bin").write_bytes(files[buffer["uri"]])
            buffer["uri"] = f"{name}_{index}.bin"
        (made / f"{name}.gltf").write_text(json.dumps(gltf))
    planned = {"scene": "yard", "take": "r1", "frame": "x across, z along, y up", "on_seat": [0.0, 0.0],
               "children": [],
               "models": {"crate": {"kind": "yard_crate", "route": "model", "size": [1.0, 1.0, 1.0]},
                          "cable_run_2": {"kind": "yard_cable_run", "route": "code", "size": [2.0, 0.1, 0.06],
                                          "tilt": 90.0}},
               "pieces": [{"model": "crate", "row": "crate", "spot": {"x": 1.0, "z": 2.0, "facing": 90}},
                          {"model": "crate", "row": "crate", "spot": {"x": -1.0, "z": 0.0, "scale": 0.5}},
                          {"model": "cable_run_2", "row": "cable_run", "spot": {"x": 0.0, "z": 0.0, "facing": 0}}]}
    work = folder / "work"
    (work / "plan-route.json").write_text(json.dumps(planned))
    (work / "checks.json").write_text(json.dumps({"crate": {"pass": True}, "cable_run_2": {"pass": True}}))
    (made / "report-chunky1.json").write_text(json.dumps({"crate": {"triangles": 12}}))
    return work


def test_a_facing_of_90_turns_the_front_to_plus_x():
    front = package.turned(90.0, 0.0, 1.0) @ np.array([0.0, 0.0, -1.0])
    assert np.allclose(front, [1.0, 0.0, 0.0]), front


def test_a_tilted_piece_lands_its_middle_on_its_spot():
    entry = {"size": [2.0, 0.1, 0.06], "tilt": 90.0}
    at = package.standing_at(entry, {"x": 0.0, "z": 0.0, "facing": 0.0})
    assert np.allclose(at, [0.0, 0.03, -0.05]), at


def test_a_sound_package_passes_and_matches_the_inventory():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        out = folder / "out"
        scene = package.write("yard", a_run(folder), out)
        assert package.problems(out, INVENTORY) == []
        assert len(scene["instances"]) == 3 and (out / "objects/crate.gltf").is_file()
        matrix = np.array(scene["instances"][0]["matrix"]).reshape(4, 4).T
        assert np.allclose(matrix[:3, 3], [1.0, 0.0, 2.0])


def test_a_missing_buffer_a_failed_model_and_a_wrong_count_are_refused():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        out = folder / "out"
        package.write("yard", a_run(folder), out)
        buffer = package.model_files(out / "objects/crate.gltf")[0]
        (out / "objects" / buffer).unlink()
        scene = json.loads((out / "scene.json").read_text())
        scene["objects"]["cable_run_2"]["check"]["pass"] = False
        (out / "scene.json").write_text(json.dumps(scene))
        found = package.problems(out, {"rows": [{"id": "crate", "count": 3}, {"id": "cable_run", "count": 1}]})
        assert any("crate" in line and "missing" in line for line in found), found
        assert any("failed its model check" in line for line in found), found
        assert any("row crate" in line for line in found), found


def test_a_run_with_a_failed_model_is_not_packaged():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        work = a_run(folder)
        (work / "checks.json").write_text(json.dumps({"crate": {"pass": False}, "cable_run_2": {"pass": True}}))
        try:
            package.write("yard", work, folder / "out")
        except SystemExit as refused:
            assert "crate" in str(refused)
        else:
            raise AssertionError("a failed model was packaged")


def a_kit_run(folder):
    """A finished kit room run: one plate model (its box off its origin, as a baked model's is) laid twice, once turned
    a quarter about up."""
    made = folder / "work" / "made"
    made.mkdir(parents=True)
    box = trimesh.creation.box(extents=(2.0, 1.0, 0.1))
    box.apply_translation((0.3, 0.5, 0.0))
    box.visual = trimesh.visual.TextureVisuals(uv=np.zeros((len(box.vertices), 2)),
                                               material=trimesh.visual.material.SimpleMaterial())
    files = box.export(file_type="gltf")
    gltf = json.loads(files.pop("model.gltf"))
    for index, buffer in enumerate(gltf["buffers"]):
        (made / f"plate_1_{index}.bin").write_bytes(files[buffer["uri"]])
        buffer["uri"] = f"plate_1_{index}.bin"
    (made / "plate_1.gltf").write_text(json.dumps(gltf))
    pieces = [{"kind": "bay_plate", "model": "plate_1", "at": [1.0, 0.0, 2.0], "x": [1, 0, 0], "y": [0, 1, 0],
               "z": [0, 0, 1], "size": [2.0, 1.0, 0.1], "layer": 1},
              {"kind": "bay_plate", "model": "plate_1", "at": [0.0, 0.0, 0.0], "x": [0, 0, -1], "y": [0, 1, 0],
               "z": [1, 0, 0], "size": [2.0, 1.0, 0.1], "layer": 1}]
    work = folder / "work"
    (work / "layout.json").write_text(json.dumps({"room": "bay", "frame": "the room's own", "counts": {"bay_plate": 2},
                                                  "kinds": {}, "models": {"plate_1": {"route": "code"}},
                                                  "pieces": pieces}))
    (work / "plan.json").write_text(json.dumps({"models": {"plate_1": {"route": "code"}}}))
    (work / "checks.json").write_text(json.dumps({"plate_1": {"pass": True}}))
    return work


def test_a_kit_piece_stands_its_model_s_foot_on_its_origin_in_its_frame():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        out = folder / "out"
        scene = package.write_kit("bay", a_kit_run(folder), out)
        assert package.problems(out) == [], package.problems(out)
        turned_copy = np.array(scene["instances"][1]["matrix"]).reshape(4, 4).T
        foot = turned_copy @ np.array([0.3, 0.0, 0.0, 1.0])
        end = turned_copy @ np.array([1.3, 0.0, 0.0, 1.0])
        assert np.allclose(foot[:3], [0.0, 0.0, 0.0]) and np.allclose(end[:3], [0.0, 0.0, -1.0]), (foot, end)
        assert scene["instances"][0]["row"] == "plate" and scene["instances"][0]["stretch"] == [1.0, 1.0, 1.0]


def test_a_stretched_kit_piece_and_a_wrong_count_of_a_kind_are_refused():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        work = a_kit_run(folder)
        layout = json.loads((work / "layout.json").read_text())
        layout["pieces"][0]["size"] = [2.4, 1.0, 0.1]
        layout["counts"]["bay_plate"] = 3
        (work / "layout.json").write_text(json.dumps(layout))
        out = folder / "out"
        package.write_kit("bay", work, out)
        found = package.problems(out)
        assert any("stretched" in line for line in found), found
        assert any("kind bay_plate" in line for line in found), found


def test_a_turn_is_read_as_its_yaw():
    for yaw in (0.0, 90.0, 115.0, 270.0):
        angle = math.radians(yaw)
        turn = [math.cos(angle), 0.0, math.sin(angle), 0.0, 1.0, 0.0, -math.sin(angle), 0.0, math.cos(angle)]
        assert abs(place_route.yaw_of(turn) - yaw) < 1e-6, yaw


def test_a_take_is_split_in_two_across_its_longest_side():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        source = folder / "leg"
        source.mkdir()
        trimesh.creation.box(extents=(0.2, 0.2, 2.4)).subdivide().subdivide().subdivide().export(source / "steel.ply")
        (source / "labels.json").write_text("{}")
        axis, middle = place_route.split(source, folder / "a", folder / "b")
        assert axis == 2 and abs(middle) < 1e-6
        for half in ("a", "b"):
            bounds = trimesh.load(folder / half / "steel.ply").bounds
            assert bounds[1][2] - bounds[0][2] < 1.3, half
        shutil.rmtree(source)


def test_a_report_no_current_job_names_is_not_read():
    with tempfile.TemporaryDirectory() as temporary:
        work = pathlib.Path(temporary)
        (work / "made").mkdir()
        (work / "job-kit-shell_1.json").write_text(json.dumps({"report": "report-shell_1.json"}))
        (work / "made/report-shell_1.json").write_text(json.dumps({"pieces": {"ring_3": {"bounds": [[-1.3], [1.3]]}}}))
        (work / "made/report-shell_3.json").write_text(json.dumps({"pieces": {"ring_3": {"bounds": [[-1.2], [1.2]]}}}))
        assert package.made_reports(work) == {"ring_3": {"bounds": [[-1.3], [1.3]]}}
        for job in work.glob("job-*.json"):
            job.unlink()
        assert set(package.made_reports(work)) == {"ring_3"}, "with no jobs, every report is read"


def test_the_camp_grounds_are_painted_as_the_camp_and_their_cables_are_code_lengths():
    assert place_route.styled_as("campgrounds") == "expedition_camp"
    assert place_route.styled_as("wreck") == "wreck"
    row = {"id": "ground_cable", "size": [2.0, 0.05, 0.05], "at": [{"x": 0.0, "z": 0.0, "facing": 30.0}] * 3}
    models, pieces = place_route.code_models(row, "campgrounds")
    assert list(models) == ["ground_cable_2"] and models["ground_cable_2"]["builder"] == "ground_cable"
    assert models["ground_cable_2"]["size"] == [2.0, 0.05, 0.05] and len(pieces) == 3


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
