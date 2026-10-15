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
import export_test  # noqa: E402
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


def legged_tank(ends):
    """A 1.4 m tank on four legs at its corners, each leg ending `ends` metres up (the greenhouse's water tank,
    2026-10-12, as it lay after its drop: three feet on the floor, the fourth 7 cm up)."""
    body = trimesh.creation.box(bounds=((-0.7, 0.3, -0.7), (0.7, 1.6, 0.7)))
    legs = [trimesh.creation.box(bounds=((across - 0.05, end, along - 0.05), (across + 0.05, 0.3, along + 0.05)))
            for (across, along), end in zip(((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)), ends)]
    return trimesh.util.concatenate([body, *legs])


def wedge(degrees):
    """A 1 m block whose base is cut at `degrees` across its depth: laid tilted by as much, its base lies flat."""
    rise = np.tan(np.radians(degrees))
    corners = [(across, (along + 0.5) * rise if low else 1.0, along) for across in (-0.5, 0.5)
               for along in (-0.5, 0.5) for low in (True, False)]
    return trimesh.convex.convex_hull(np.array(corners))


def a_foot_off_the_floor_and_a_lean_fail():
    """Both ways: a tank on three feet with the fourth 7 cm up fails by its foot (four contacts and its weight inside
    them passed it before), one on four level feet passes; a block whose own up leans 7.5 degrees from the floor it
    stands flat on fails unless its row says it leans."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        export_test.box_gltf(folder / "models", "tank", legged_tank((0.0, 0.0, 0.0, 0.07)))
        export_test.box_gltf(folder / "models", "level_tank", legged_tank((0.0, 0.0, 0.0, 0.0)))
        export_test.box_gltf(folder / "models", "wedge", wedge(7.5))
        stage = place_of(folder, [("tank", "tank", (0, 0, 0)), ("level", "level_tank", (4, 0, 0)),
                                  ("wedge", "wedge", (8, 0, 0)), ("leaning", "wedge", (11, 0, 0))],
                         [row("tank"), row("level"), row("wedge"), row("leaning", leans="a ramp, cut to lean")])
        kit = json.loads((folder / "kit.json").read_text())
        for piece in kit["pieces"][2:]:
            piece.update(tilt=7.5, at=[piece["at"][0], -0.5 * np.sin(np.radians(7.5)), 0.0])
        (folder / "kit.json").write_text(json.dumps(kit))
        stage = export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                              inventory_path=folder / "inventory.json")
        said = verdicts(triage.triage(stage))
        expected = {"tank_1": [("foot off", True)], "level_1": None, "wedge_1": [("leans", True)], "leaning_1": None}
        return [f"{name} reads {said.get(name)}, not {want}" for name, want in expected.items()
                if said.get(name) != want]


def a_block_tipped_onto_one_edge_of_its_sole_leans():
    """A foot is down when any of its sole touches, so a 1 m block tipped 6 degrees onto one edge of its flat base has
    its one foot down, and still fails: its up leans 6 degrees from the floor it touches along that edge."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        place_of(folder, [("tipped", "box", (0, 0, 0))], [row("tipped")])
        kit = json.loads((folder / "kit.json").read_text())
        kit["pieces"][0].update(tilt=6.0, at=[0.0, 0.5 * np.sin(np.radians(6.0)), 0.0])
        (folder / "kit.json").write_text(json.dumps(kit))
        stage = export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                              inventory_path=folder / "inventory.json")
        said = verdicts(triage.triage(stage)).get("tipped_1") or []
        problems = [] if ("leans", True) in said else [f"the tipped block reads {said}, not leaning"]
        return problems + ([f"its foot reads off: {said}"] if ("foot off", True) in said else [])


def on_slope(degrees, tilted, flat_ground=False):
    """The floor faults of a 2.6 m by 2.6 m block on ground sloping `degrees` along x (the campgrounds' reactor on its
    6.6 degree slope), its up `tilted` degrees the same way, its lowest point on the ground; level ground with
    `flat_ground`."""
    rise = 0.0 if flat_ground else np.tan(np.radians(degrees))
    mesh = trimesh.creation.box(bounds=((-1.3, 0.0, -1.3), (1.3, 1.5, 1.3)))
    matrix = trimesh.transformations.rotation_matrix(np.radians(tilted), (0, 0, 1))
    mesh.apply_transform(matrix)
    mesh.apply_translation((0.0, -float((mesh.vertices[:, 1] - rise * mesh.vertices[:, 0]).min()), 0.0))
    ground = lambda flat: rise * np.atleast_2d(flat)[:, 0]  # noqa: E731
    far = trimesh.creation.box(bounds=((-9, -51, -9), (9, -50, 9)))  # the rays need a surface: one far under it
    entry = {"name": "/slope/Objects/block_1", "row_id": "block", "model": "block", "support": "floor",
             "bed": (0.0, None), "row": {}, "mesh": mesh, "matrix": matrix}
    found = triage.standing(entry, ground, triage.Surfaces({"far": far}), set(), set())
    return sorted({item["kind"] for item in triage.held_up_faults(entry, found)}), found


def footing_on_a_slope_is_read_over_the_ground():
    """Both ways on a 6.6 degree slope: a block flush on it (tilted with it) stands, its whole base touching (read
    straight up, only its downhill strip did, its weight 0.8 m outside); one standing straight up on it rests on its
    downhill edge and still fails. On level ground nothing is read over a plane."""
    problems = []
    flush, found = on_slope(6.6, 6.6)
    if flush or found["outside"] > 0.0 or found["contacts"] < triage.CONTACTS_NEEDED:
        problems.append(f"flush on the slope: {flush}, outside {found['outside']}, contacts {found['contacts']}")
    upright, _ = on_slope(6.6, 0.0)
    if not upright:
        problems.append("standing straight up on the slope passed")
    level = trimesh.creation.box(bounds=((-1.3, 0.0, -1.3), (1.3, 1.5, 1.3)))
    if triage.ground_plane(level, lambda flat: np.zeros(len(np.atleast_2d(flat)))) is not None:
        problems.append("level ground read as a plane")
    plain, _ = on_slope(0.0, 0.0, flat_ground=True)
    return problems + ([f"a block flat on level ground: {plain}"] if plain else [])



def a_case_on_a_pallet_is_no_surface_under_the_pallet():
    """Both ways: a case standing on an 8 cm pallet, its bottom within RAY_START over the pallet's low points, is no
    surface under them (the campgrounds' pallets, 2026-10-15: read 10 cm up, their plane tipped 3 to 4 degrees), while
    a point bedded 2 cm into a crate's top still finds that top."""
    pallet = trimesh.creation.box(bounds=((-0.5, 0.0, -0.5), (0.5, 0.08, 0.5)))
    case = trimesh.creation.box(bounds=((-0.3, 0.08, -0.3), (0.3, 0.5, 0.3)))
    crate = trimesh.creation.box(bounds=((2.0, 0.0, -0.5), (3.0, 0.5, 0.5)))
    surfaces = triage.Surfaces({"pallet": pallet, "case": case, "crate": crate})
    under_pallet = surfaces.gaps_below(np.array([[0.0, 0.0, 0.0], [0.1, 0.01, 0.1]]), {0})
    bedded = surfaces.gaps_below(np.array([[2.5, 0.48, 0.0]]), set())
    problems = []
    if np.isfinite(under_pallet).any():
        problems.append(f"the case read under the pallet's low points: {under_pallet}")
    if not np.isclose(bedded[0], -0.02, atol=1e-6):
        problems.append(f"a point bedded 2 cm into the crate read {bedded[0]}")
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


def the_data_read_is_the_data_given():
    """Fault (review of step 0, 2026-10-11): the triage read data/checks/resting.json, data/kit/<place>.json and the
    inventory through the repository whatever files a caller declared, so the assembly stage's key covered files its
    judge never read and missed the ones it did."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = place_of(folder, [("plate", "box", (6, -0.4, 0)), ("sign", "box", (12, 1.5, 0)),
                                  ("crate", "box", (0, 0.3, 0))],
                         [row("plate", group="kit: floor"), row("sign", anchor="wall"), row("crate")])
        rules = {**triage.rules(), "fixed_in_kit": []}
        (folder / "rules.json").write_text(json.dumps(rules))
        (folder / "rows.json").write_text(json.dumps({"rows": [row("plate", group="kit: floor"), row("sign"),
                                                               row("crate")]}))
        (folder / "kit_given.json").write_text(json.dumps({"kinds": {"test_crate": {"group": "floors"}}}))
        said = verdicts(triage.triage(stage, rules_file=folder / "rules.json", kit_file=folder / "kit_given.json",
                                      inventory_file=folder / "rows.json"))
        expected = {"plate_1": [("sunk", True)], "sign_1": [("floats", True)], "crate_1": [("floats", False)]}
        return [f"{name} reads {said.get(name)} on the data given, not {want}" for name, want in expected.items()
                if said.get(name) != want]


CHECKS = (supports_and_guards, a_case_on_a_pallet_is_no_surface_under_the_pallet, overlaps_and_nudge, a_long_drop_is_unstable_and_faults_group,
          a_foot_off_the_floor_and_a_lean_fail, a_block_tipped_onto_one_edge_of_its_sole_leans, the_collision_set,
          occlusion_boundaries, the_data_read_is_the_data_given, footing_on_a_slope_is_read_over_the_ground)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
