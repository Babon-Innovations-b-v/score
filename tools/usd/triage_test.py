"""Check the resting triage, the collision queries and the annotate step's arithmetic on places made here: a box on
the floor rests and a lifted one floats for real; a kit piece out of the ground is a false alarm; a cable sunk a few
centimetres may bed in; two boxes deep inside each other overlap for real while two only touching clear the nudge; a
wall piece touching nothing hangs free; a drop that moves an object 0.5 m is SAGE-unstable; the real faults group by
cause; the collision set finds the pairs that meet; and the occlusion boundary lies where a near object hides a far one.

Run: .venv/bin/python tools/usd/triage_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import annotate  # noqa: E402
import collide  # noqa: E402
import export  # noqa: E402
import resting_test  # noqa: E402
import triage  # noqa: E402

PLACE = resting_test.PLACE


def place_of(folder, pieces, rows):
    """A place of these pieces (row, model, at) and these inventory rows (dicts), exported; its stage."""
    if not (folder / "models").exists():
        resting_test.made_models(folder)
    kit = {"place": PLACE, "lamps": [], "children": [],
           "pieces": [{"prop": f"test_{row}", "kind": f"test_{row}", "model": model, "row": row,
                       "size": [1.0, 1.0, 1.0], "at": list(at), "facing": 0.0} for row, model, at in pieces]}
    (folder / "kit.json").write_text(json.dumps(kit))
    (folder / "inventory.json").write_text(json.dumps({"scene": PLACE, "rows": rows}))
    return export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                         inventory_path=folder / "inventory.json")


def row(identity, anchor="floor", **more):
    """An inventory row of this id, its name the id unless given."""
    return {"id": identity, "name": identity, "anchor": anchor, "thing": f"prop:test_{identity}", **more}


def verdicts(found):
    """{object name: [(kind, real)]} of a triage."""
    said = {}
    for fault in found["faults"]:
        said.setdefault(fault["object"].rsplit("/", 1)[-1], []).append((fault["kind"], fault["real"]))
    return said


def supports_and_guards():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = place_of(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (3, 0.3, 0)),
                                  ("plate", "box", (6, -0.4, 0)), ("cable", "box", (9, -0.06, 0)),
                                  ("sign", "box", (12, 1.5, 0))],
                         [row("crate"), row("plate", group="kit: floor"), row("cable", name="floor cable"),
                          row("sign", anchor="wall")])
        said = verdicts(triage.triage(stage))
        expected = {"crate_1": None, "crate_2": [("floats", True)], "plate_1": [("sunk", False)],
                    "cable_1": [("sunk", False)], "sign_1": [("hangs free", True)]}
        return [f"{name} reads {said.get(name)}, not {want}" for name, want in expected.items()
                if said.get(name) != want]


def overlaps_and_nudge():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = place_of(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (0.6, 0, 0)),
                                  ("crate", "box", (3, 0, 0)), ("crate", "box", (4.0, 0, 0))], [row("crate")])
        said = verdicts(triage.triage(stage))
        problems = []
        if ("overlaps", True) not in said.get("crate_1", []):
            problems.append(f"two boxes 40 cm inside each other read {said.get('crate_1')}")
        if any(kind == "overlaps" and real for kind, real in said.get("crate_3", [])):
            problems.append(f"two boxes only touching read {said.get('crate_3')}")
        return problems


def a_long_drop_is_unstable_and_faults_group():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = place_of(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (3, 0.3, 0)),
                                  ("crate", "box", (6, 0.4, 0))], [row("crate")])
        moved = np.eye(4)
        moved[0, 3] = 0.5
        found = triage.triage(stage, {"objects": {"crate_1": {"motion": moved.tolist(), "moving": 0.0}}})
        problems = []
        if ("unstable", True) not in verdicts(found).get("crate_1", []):
            problems.append(f"a box that moves 0.5 m when dropped reads {verdicts(found).get('crate_1')}")
        floats = [group for group in found["groups"] if group["kind"] == "floats"]
        if len(floats) != 1 or floats[0]["count"] != 2 or floats[0]["worst"]["object"].endswith("crate_2"):
            problems.append(f"the two floating boxes do not form one group, worst the higher: {floats}")
        return problems


def the_collision_set():
    box = trimesh.creation.box((1.0, 1.0, 1.0))
    scene = collide.Scene()
    for name, across in (("a", 0.0), ("b", 0.5), ("c", 5.0), ("d", 5.99)):
        matrix = np.eye(4)
        matrix[0, 3] = across
        scene.add(name, "box", box.vertices, box.faces, matrix)
    problems = []
    if scene.collision_set() != {("a", "b"), ("c", "d")}:
        problems.append(f"the collision set is {scene.collision_set()}")
    if scene.intersection_test("a", "b", (-0.6, 0.0, 0.0)):
        problems.append("a box moved clear still meets the other")
    if not scene.touches("c", 0.03) or scene.touches("a", 0.03) is False:
        problems.append("a box 1 cm from another does not touch it within 3 cm")
    distances, names = scene.raycast([[0.0, 5.0, 0.0]], [[0.0, -1.0, 0.0]])
    if names != ["a"] or abs(distances[0] - 4.5) > 1e-6:
        problems.append(f"a ray down onto box a reads {distances}, {names}")
    return problems


def occlusion_boundaries():
    ids = np.zeros((4, 6), dtype=np.int32)
    depth = np.full((4, 6), 10.0)
    ids[:, 3:] = 1
    depth[:, 3:] = 2.0
    found = annotate.occlusion_boundaries({"ids": ids, "depth": depth})
    expected = np.zeros((4, 6), dtype=bool)
    expected[:, 3] = True
    return [] if np.array_equal(found, expected) else [f"the boundary is\n{found.astype(int)}"]


CHECKS = (supports_and_guards, overlaps_and_nudge, a_long_drop_is_unstable_and_faults_group, the_collision_set,
          occlusion_boundaries)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
