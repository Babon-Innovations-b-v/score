"""The people stage's checks on made-up records (no cloud, no models): the shared loop's hand-on of the looks and
their place in the table, the body gates, the dress's glTF round trip and the clips' clearance easing."""
import json
import pathlib
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/characters/maker"))

from score.stages import people_rows  # noqa: E402
from score.stages.people import dress, loop  # noqa: E402
from score.stages.people_bodies import bodies, clips, far  # noqa: E402
import clearance  # noqa: E402


def loop_ends(folder):
    """The shared loop's ends (made.ENDS) for two looks of the people line and one object: the player made and
    painted, Nev's take never baked."""
    import score.stages.props.pixal_row as pixal_row
    ends = {name: folder / name for name in ("props-inputs", "surfaces-bake", "surfaces-parts", "likeness", "pixal")}
    for path in ends.values():
        path.mkdir()
    for path in pixal_row.take_files("pp-player"):  # where pixal@people's batch brought the take
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix == ".svviews":
            path.mkdir(exist_ok=True)
            (path / "input.png").write_bytes(b"the close-up")
        else:
            path.write_bytes(path.name.encode())
    (ends["pixal"] / "takes.json").write_text(json.dumps({"player-work": {
        "take": "pp-player", **{path.name: pixal_row.file_hash(path) for path in pixal_row.take_files("pp-player")}}}))
    rows = [{"id": "player-work", "take": "pp-player", "layer": "people", "failures": {"take": "made before the loop"}},
            {"id": "nev-space", "take": "pp-nev", "layer": "people"}, {"id": "crate", "take": "crate-s1"}]
    (ends["props-inputs"] / "rows.json").write_text(json.dumps({"rows": [dict({"layer": "objects"}, **row)
                                                                         for row in rows]}))
    (ends["likeness"] / "likeness.json").write_text(json.dumps({"objects": {
        row["id"]: {"route": "prop"} for row in rows}}))
    (ends["surfaces-bake"] / "baked.json").write_text(json.dumps({"player-work": {"parts": "pp-player"}}))
    (ends["surfaces-bake"] / "labelled" / "pp-player").mkdir(parents=True)
    np.savez(ends["surfaces-bake"] / "labelled" / "pp-player" / "pp-player.npz", points=np.zeros((1, 3)),
             names=np.array(["navy_twill__navy_r080_m000_s7"]), surface=np.zeros(1, int))
    (ends["surfaces-bake"] / "specs.json").write_text(json.dumps({
        "navy_twill__navy_r080_m000_s7": {"library": "navy_twill", "metal": 0.0}, "steel": {"library": "steel"}}))
    (ends["surfaces-parts"] / "parts.json").write_text(json.dumps({"takes": {
        "pp-player": {"parts": [{"part": 0, "surface": "navy_twill"}]}}}))
    return ends


def test_the_loop_hands_each_look_on_and_names_its_gap():
    """#41: people-made@people hands on every look of the people layer the loop made, with its painted take, and
    names the rest by their gap; it fails only when none came through. A body's parts are refused on a gap."""
    from score import graph
    with tempfile.TemporaryDirectory() as held:
        ends, out = loop_ends(pathlib.Path(held)), pathlib.Path(held) / "out"
        out.mkdir()
        loop.make(ends, out, 0, {})
        found = json.loads((out / "made.json").read_text())
        assert sorted(found) == ["nev-space", "player-work"], found  # the object is not the people layer's
        assert found["player-work"]["finishes"] == [{"part": 0, "surface": "navy_twill"}], found
        assert (out / found["player-work"]["labelled"]).exists() and "no baked model" in found["nev-space"]["gap"]
        assert found["player-work"]["failures"] == {"take": "made before the loop"}, found  # named, never silent
        assert found["player-work"]["model"].endswith("made/player-work.gltf"), found
        # the surfaces with the list's settings the bake painted, resolved from its specs.json for the dress
        assert found["player-work"]["specs"] == {"navy_twill__navy_r080_m000_s7": {"library": "navy_twill",
                                                                                   "metal": 0.0}}, found
        stored = out / found["player-work"]["files"]  # the take's files kept in the store (#26)
        assert (stored / "pp-player.svviews" / "input.png").read_bytes() == b"the close-up", found
        laid = pathlib.Path(held) / "laid"
        bodies.laid_take(out, "player-work", laid)
        bodies.laid_take(out, "player-work", laid)  # laid again over itself: plain copies, never read-only
        assert sorted(path.name for path in laid.iterdir()) == ["pp-player-final.glb", "pp-player.glb",
                                                                "pp-player.svviews"]
        verdict = loop.judge_made(out, ends, {})
        assert verdict.answer == "pass" and verdict.measures["gaps"] == 1 and "nev-space" in verdict.findings[0]
        assert verdict.measures["named_failures"] == 1, verdict
        inputs = {f"{bodies.MADE}@{bodies.LINE}": out}
        assert dress.painted_take(inputs, "player-work") == out / "labelled" / "pp-player.npz"
        for look in ("nev-space", "guard-guard-uniform"):
            try:
                bodies.refused_on_gap(out, look)
                raise AssertionError(f"{look}: bought with no model from the loop")
            except graph.Blocked as blocked:
                assert "made no model" in str(blocked)


def test_a_take_whose_files_are_not_the_ones_pixal_made_is_a_gap():
    """#26: the hand-on keeps only the bytes pixal@people's takes.json names; another file in the work folder is a gap
    named, never handed to a body."""
    import score.stages.props.pixal_row as pixal_row
    with tempfile.TemporaryDirectory() as held:
        ends, out = loop_ends(pathlib.Path(held)), pathlib.Path(held) / "out"
        out.mkdir()
        pixal_row.take_files("pp-player")[1].write_bytes(b"another finish")
        loop.make(ends, out, 0, {})
        found = json.loads((out / "made.json").read_text())
        assert found["player-work"] == {"gap": "pp-player-final.glb not the bytes pixal made"}, found


def test_people_are_made_by_the_loop_on_a_line_no_place_owns():
    """#41: no side route of the people's own; the loop's rows and its after-step run on the line `people`, where no
    place's rows (assembly, complete, the library hand-over) apply, and the looks' parts and dress wait on it."""
    from score import stages
    from score.stages import shapes_first
    table = {row.name: row for row in stages.STAGES}
    assert not [name for name in table if name.startswith(("people-route", "people-parts", "people-paint"))]
    assert table[loop.ROW].applies(bodies.LINE) and not table[loop.ROW].applies("hub")
    for name in ("props-inputs", "closeup", "pixal", "finish-route-views", "surfaces-bake", "likeness"):
        assert table[name].applies is None or table[name].applies(bodies.LINE), name
    for name in ("assembly", "complete", "library"):
        assert not table[name].applies(bodies.LINE) and table[name].applies("hub"), name
    assert loop.ROW == bodies.MADE and shapes_first.no_place(bodies.LINE)
    look = next(iter(bodies.looks()))
    for row in (table[f"people-dress-{look}"], table[f"{bodies.PARTS}-{look}"], table[f"{bodies.BODY}-{look}"]):
        assert bodies.MADE in row.beside and row.neighbours(None) == [bodies.LINE], row.name
    for row in (table[f"{bodies.PARTS}-{look}"], table[f"{bodies.BODY}-{look}"]):  # #26: the take is the store's
        found = row.files(None) if callable(row.files) else row.files
        assert not [path for path in found.values() if "work/pixal" in str(path)], found


def write_checks(folder, deep, bind_deep, tuck_over=0):
    """A body's records with two clips: walking with the given counts, standing clean."""
    checks = folder / "checks"
    checks.mkdir(parents=True)
    (checks / "bodycloth.json").write_text(json.dumps({
        "margin_mm": 3.0, "bind": {"deep_by_part": {"boot_r": bind_deep}},
        "clips": {"walking": {"deep_by_part": {"boot_r": deep}, "deepest_mm": 9.0},
                  "standing": {"deep_by_part": {"boot_r": bind_deep}, "deepest_mm": 2.0}}}))
    clip = {"worst_tuck_out_mm": 2.0, "frames_tuck_over": 0, "rigid_stretch": 1.0, "most_crossings": 10}
    (checks / "pokes.json").write_text(json.dumps({"rest_crossings": 10, "clips": {
        "walking": dict(clip, worst_tuck_out_mm=2.0 + tuck_over, frames_tuck_over=tuck_over), "standing": clip}}))
    (checks / "pokes_shipped.json").write_text(json.dumps({"rest_crossings": 10, "clips": {
        "walking": {"most_crossings": 20}, "standing": {"most_crossings": 20}}}))


def test_a_body_is_judged_clip_by_clip():
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        write_checks(folder, deep=13, bind_deep=13)
        assert clips.usable(folder) == (["standing", "walking"], {})
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        write_checks(folder, deep=50, bind_deep=13, tuck_over=3)
        passing, failing = clips.usable(folder)
        assert passing == ["standing"] and len(failing["walking"]) == 2, failing
        verdict = bodies.judge_clips(folder, {}, {})
        assert verdict.answer == "pass" and verdict.measures["failing"] == 1 and "walking" in verdict.findings[0]


def test_a_far_only_look_is_judged_on_its_far_body():
    with tempfile.TemporaryDirectory() as held:
        checks = pathlib.Path(held) / "checks"
        checks.mkdir()
        (checks / "build.json").write_text(json.dumps({"levels": {"far": {"triangles": 1220},
                                                                  "coat": {"triangles": 34159}}}))
        (checks / "shell.json").write_text(json.dumps({"offset_most_m": 0.09}))
        assert far.judge_far_triangles(pathlib.Path(held), {}, {}).answer == "pass"
        recorded = far.judge_near_recorded(pathlib.Path(held), {}, {})
        assert recorded.answer == "pass" and recorded.measures == {"near_triangles": 34159, "shell_most_m": 0.09}


def test_a_cast_doing_a_failing_clip_fails():
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        (folder / "rows.json").write_text(json.dumps({"places": {"lab": {"concept": "a test", "rows": {
            "a": {"name": "person walking", "count": 1, "looks": ["bram-work"]},
            "b": {"name": "person", "where": "at a desk", "count": 1, "looks": ["bram-work"]}}}}, "new": {}}))
        (folder / "usable.json").write_text(json.dumps({"bram-work": {"usable": ["standing"],
                                                                     "failing": {"walking": ["tucks: 5.1 mm"]}}}))
        verdict = clips.judge_casts(folder, {"casts": folder / "rows.json"}, {})
        assert verdict.answer == "fail" and verdict.measures == {"failing": 1, "judged": 2}, verdict


def shell_verdict(soft_tail):
    """judge_shell on a look of 1,000 soft points, `soft_tail` of them 8 cm off, and a hand and a boot 12 cm off."""
    with tempfile.TemporaryDirectory() as held:
        checks = pathlib.Path(held) / "checks"
        checks.mkdir()
        near, far = [0] * 21, [0] * 81
        near[20], far[80] = 1000 - soft_tail, soft_tail
        rigid = [0] * 121
        rigid[120] = 50
        (checks / "shell.json").write_text(json.dumps({"scale": 1.0, "parts": {
            "1": {"most_m": 0.02, "offsets_mm": near}, "2": {"most_m": 0.08, "offsets_mm": far},
            "3": {"most_m": 0.12, "offsets_mm": rigid}, "4": {"most_m": 0.12, "offsets_mm": rigid}}}))
        (checks / "parts.json").write_text(json.dumps({"parts": [
            {"part": 1, "role": "garment", "name": "cloth"}, {"part": 2, "role": "garment", "name": "cloth"},
            {"part": 3, "role": "hard", "name": "boot"}, {"part": 4, "role": "skin", "name": "skin_hands"}]}))
        return bodies.judge_shell(pathlib.Path(held), {}, {})


def test_the_shell_holds_most_soft_points_and_leaves_rigid_parts_out():
    passing, failing = shell_verdict(9), shell_verdict(20)
    assert passing.answer == "pass" and passing.measures["offset_share_m"] == 0.02, passing
    assert passing.measures["offset_most_m"] == 0.08 and "part 2" in passing.reason, passing
    assert failing.answer == "fail" and failing.measures["offset_share_m"] == 0.08, failing


def test_a_belt_is_worn_as_cloth():
    assert not bodies.rigid_part({"role": "hard", "name": "black_leather_belt"})
    assert not bodies.rigid_part({"role": "hard", "name": "steel_buckle"})
    assert bodies.rigid_part({"role": "hard", "name": "boot"}) and bodies.rigid_part({"role": "skin", "name": "skin_hands"})


def test_missing_record_is_unknown():
    with tempfile.TemporaryDirectory() as held:
        joins = dict((check.name, check) for check in bodies.checks())["joins"]
        assert joins.judge(pathlib.Path(held), {}, {}).answer == "unknown"


def test_dress_keeps_the_binary_chunk():
    with tempfile.TemporaryDirectory() as held:
        path = pathlib.Path(held) / "a.glb"
        blob = np.arange(9, dtype=np.float32).tobytes()
        document = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(blob)}],
                    "bufferViews": [{"buffer": 0, "byteLength": len(blob)}],
                    "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}]}
        rest = len(blob).to_bytes(4, "little") + b"BIN\x00" + blob
        dress.write_glb(path, document, rest)
        read, kept = dress.read_glb(path)
        assert kept == rest and read["asset"] == document["asset"]
        assert np.allclose(dress.positions(read, kept, 0).ravel(), np.arange(9))


def test_dress_finds_the_routed_body_whatever_its_outfit_is_named():
    """The route names the body's node work while the look's outfit is made (2026-10-22): dress takes the one skinned
    node that is not the far body."""
    document = {"nodes": [{"name": "far", "mesh": 0, "skin": 0}, {"name": "work", "mesh": 1, "skin": 0},
                          {"name": "Hips"}]}
    assert dress.outfit_node(document)["name"] == "work"


def test_a_wrist_with_no_hand_piece_is_no_join_and_one_with_a_hand_not_measured_fails():
    """An astronaut's gloves are its suit's cloth (2026-10-22): joins.py measures no wrist, and the body draws no hand
    piece, so there is no wrist join to open; a body that draws a hand but has no wrist measured still fails."""
    import struct
    with tempfile.TemporaryDirectory() as held:
        output = pathlib.Path(held)
        (output / "checks").mkdir()
        (output / "checks" / "joins.json").write_text(json.dumps({"verdict": {
            "wrist": None, "ankle": {"pass": True}, "stance": {"pass": True}}}))
        for hand, answer in (("cloth", "pass"), ("skin_hands", "fail")):
            document = {"nodes": [{"name": "work", "mesh": 0, "skin": 0}], "materials": [{"name": "cloth"},
                        {"name": hand}], "meshes": [{"primitives": [{"material": 0}, {"material": 1}]}]}
            text = json.dumps(document).encode()
            text += b" " * (-len(text) % 4)
            (output / "body.glb").write_bytes(b"glTF" + struct.pack("<II", 2, 28 + len(text)) + struct.pack(
                "<I", len(text)) + b"JSON" + text + struct.pack("<I", 0) + b"BIN\x00")
            judged = bodies.judge_joins(output, {}, {})
            assert judged.answer == answer, (hand, judged)


def test_a_point_reads_the_take_s_outer_surface_not_a_face_inside_it():
    """The take keeps faces Pixal3D grew inside (2026-10-22): the nearest sample read the boots' insides as the suit's
    grey. The outermost samples along the point's normal vote."""
    painted = np.array([[0.0, 0, 0.0], [0.001, 0, 0.0], [0.0, 0, -0.006], [0.001, 0, -0.006], [0.0, 0.001, -0.006]])
    names = np.array(["boot", "boot", "suit", "suit", "suit"])
    point, up = np.array([[0.0, 0, -0.002]]), np.array([[0.0, 0, 1.0]])
    assert dress.outer_labels(point, up, painted, names, 0.015, 0.004).tolist() == ["boot"]
    assert dress.outer_labels(np.array([[5.0, 0, 0]]), up, painted, names, 0.015, 0.004).tolist() == ["boot"]


def test_a_garment_splits_where_its_paint_changes_and_a_hard_part_takes_one_surface():
    """The astronaut's overalls and jacket were one material: it took the brown most of its points carried and its grey
    bib showed as patches (2026-10-22). A lone point's label follows its neighbours first."""
    faces = np.array([[0, 1, 2], [1, 3, 2], [2, 3, 4], [3, 5, 4], [4, 5, 6], [5, 7, 6]])
    labels = np.array(["brown", "brown", "brown", "brown", "grey", "grey", "grey", "grey"])
    strip = np.array([[number // 2, number % 2, 0.0] for number in range(8)])
    assert dress.surfaces_of(labels, faces, "garment", strip).tolist() == ["brown"] * 3 + ["grey"] * 3
    lone = np.array(["brown", "brown", "brown", "grey", "brown", "brown", "brown", "brown"])
    assert set(dress.surfaces_of(lone, faces, "garment", strip)) == {"brown"}
    assert set(dress.surfaces_of(np.array(["boot"] * 5 + ["suit"] * 3), faces, "hard", strip)) == {"boot"}


def test_a_one_surface_part_wears_what_most_of_its_area_wears_not_most_of_its_points():
    """The astronaut's helmet front: the visor on 53% of its area, the grey on more of its points (the rim's dense
    ring), so by points the visor was lost (0.02% of the body, 2026-10-23)."""
    points = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0], [1.1, 1, 0], [1.2, 1, 0], [1.1, 1.1, 0]])
    faces = np.array([[0, 1, 2], [1, 3, 2], [3, 4, 6], [4, 5, 6]])
    labels = np.array(["visor", "visor", "visor", "rim", "rim", "rim", "rim"])
    assert set(dress.surfaces_of(labels, faces, "skin", points)) == {"visor"}


def grid_cloth(size=20):
    """A flat square of cloth, size by size cells of two triangles: (corners per triangle, faces over them)."""
    cells = [(column, row) for row in range(size) for column in range(size)]
    triangles = []
    for column, row in cells:
        low, right, up, both = (column, row), (column + 1, row), (column, row + 1), (column + 1, row + 1)
        triangles += [[low, right, up], [right, both, up]]
    corners = np.array(triangles, dtype=float).reshape(-1, 2)
    return np.column_stack([corners, np.zeros(len(corners))]), np.arange(len(corners)).reshape(-1, 3)


def test_a_stray_blotch_takes_the_surface_round_it_and_a_one_surface_part_is_kept():
    """The take's unseen paint left the astronaut's collar, wrists and lower back in jagged blotches of the joints'
    dark (2026-10-23): an island under the props' STRAY_ISLAND joins the surface round it; a large one and a
    one-surface part stay, and the strays gate's measure sees the blotch before and none after."""
    points, faces = grid_cloth()
    labels = np.array(["grey"] * len(faces), dtype=object)
    labels[:400] = "brown"  # half the cloth: a panel, kept
    labels[[500, 501]] = "dark"  # one cell, 0.25%: a stray
    kept = np.zeros(len(faces), dtype=bool)
    kept[[700, 701]] = True
    labels[[700, 701]] = "visor"  # a one-surface part's, as small: kept
    assert round(dress.stray_share(points, faces, labels, kept), 6) == 0.0025
    merged = dress.without_strays(points, faces, labels, kept)
    assert merged[500] == merged[501] == "grey" and set(merged[:400]) == {"brown"} and merged[700] == "visor"
    assert dress.stray_share(points, faces, merged, kept) == 0.0


def test_dress_appends_index_lists_to_the_binary_chunk():
    blob = np.arange(9, dtype=np.float32).tobytes()
    rest = len(blob).to_bytes(4, "little") + b"BIN\x00" + blob
    document = {"buffers": [{"byteLength": len(blob)}], "bufferViews": [{"buffer": 0, "byteLength": len(blob)}],
                "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"}]}
    binary = dress.Binary(document, rest)
    number = binary.indices(np.array([[0, 1, 2]]))
    kept = binary.rest()
    assert np.allclose(dress.positions(document, kept, 0).ravel(), np.arange(9))
    assert dress.accessor(document, kept, number).ravel().tolist() == [0, 1, 2]
    assert document["buffers"][0]["byteLength"] == len(kept) - 8


def test_the_face_and_hair_wear_the_paint_and_lose_the_print():
    """Owner, 2026-10-23: the face was a cutout of the close-up. Skin and hair take one library surface from the
    paint, like a hard part, and the material forgets its print."""
    faces = np.array([[0, 1, 2], [1, 3, 2]])
    for role in ("skin", "hair"):
        assert set(dress.surfaces_of(np.array(["visor", "visor", "visor", "shell"]), faces, role,
                                     np.array([[0.0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]]))) == {"visor"}
    material = {"extras": {"role": "skin", "print": True}}
    dress.named(material, "visor__black_r005", {"library": "helmet_visor"})
    assert material["extras"] == {"role": "skin", "library": "visor__black_r005", "surface": "helmet_visor"}


def baked_document():
    """A two-triangle skinned primitive with a morph target, in glb_file's form (document, views)."""
    from score.stages.people import baked_body  # noqa: F401  (puts tools/props on the path)
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=np.float32)
    arrays = [points, np.tile(np.array([[0, 0, 1]], np.float32), (4, 1)), np.arange(16, dtype=np.uint8).reshape(4, 4),
              points * 0.5, np.array([0, 1, 2, 1, 3, 2], dtype=np.uint32)]
    kinds = [(5126, "VEC3"), (5126, "VEC3"), (5121, "VEC4"), (5126, "VEC3"), (5125, "SCALAR")]
    document = {"bufferViews": [{"buffer": 0, "byteLength": array.nbytes} for array in arrays],
                "accessors": [{"bufferView": number, "componentType": kind, "count": len(array), "type": shape}
                              for number, (array, (kind, shape)) in enumerate(zip(arrays, kinds))],
                "materials": [{"name": "cloth", "extras": {"library": "suit"}}],
                "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "JOINTS_0": 2},
                                            "targets": [{"POSITION": 3}], "indices": 4, "material": 0}]}]}
    return document, [array.tobytes() for array in arrays]


def test_the_bake_s_coordinates_split_a_vertex_and_carry_its_weights_and_targets():
    """A vertex whose corners the bake laid at two coordinates becomes two vertices, each carrying its joints and its
    corrective's offset, and the triangles keep their corners."""
    from score.stages.people import baked_body
    import glb_file
    document, views = baked_document()
    lists, points, _, triangles, owners = baked_body.triangles_of(document, views)
    assert owners == [(0, 0), (0, 0)] and triangles.tolist() == [[0, 1, 2], [1, 3, 2]]
    uvs = np.array([[[0, 0], [0.5, 0], [0, 0.5]], [[0.9, 0.9], [0.6, 0.6], [0, 0.5]]])  # vertex 1 lies twice
    baked_body.laid_coordinates(document, views, lists, uvs)
    primitive = document["meshes"][0]["primitives"][0]
    laid = glb_file.accessor_array(document, views, primitive["attributes"]["POSITION"])
    assert len(laid) == 5
    corners = glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3)
    assert np.allclose(laid[corners], points[triangles])
    coordinates = glb_file.accessor_array(document, views, primitive["attributes"]["TEXCOORD_0"])
    assert np.allclose(coordinates[corners], uvs)
    joints = glb_file.accessor_array(document, views, primitive["attributes"]["JOINTS_0"])
    assert np.array_equal(joints[corners], np.arange(16).reshape(4, 4)[triangles])
    target = glb_file.accessor_array(document, views, primitive["targets"][0]["POSITION"])
    assert np.allclose(target[corners], points[triangles] * 0.5)


def test_a_body_in_flat_factors_is_not_dressed():
    """A material with the library's colour as a flat factor and no baked maps fails `dressed`; the baked one passes."""
    document = {"materials": [{"name": "cloth", "extras": {"library": "suit"},
                               "pbrMetallicRoughness": {"baseColorFactor": [0.5, 0.5, 0.5, 1.0]}}],
                "meshes": [{"primitives": [{"material": 0}]}]}
    assert dress.flat_materials(document) == ["cloth#0"]
    document["materials"][0]["pbrMetallicRoughness"] = {"baseColorTexture": {"index": 0},
                                                        "metallicRoughnessTexture": {"index": 1}}
    document["materials"][0]["normalTexture"] = {"index": 2}
    assert dress.flat_materials(document) == []
    del document["materials"][0]["extras"]["library"]
    assert dress.flat_materials(document) == ["cloth#0"]


def test_a_bake_on_its_library_colour_passes_the_surface_stage_s_check_and_one_off_it_fails():
    """The body's bake is checked by bake_check's own measures: a picture in the surface's colour lies on it, a
    picture far off it is named."""
    from PIL import Image
    from score.stages.people import baked_body
    import labels
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
    spec = {"colour": [0.2, 0.3, 0.6], "family": "fabric"}
    uvs = np.array([[[0.1, 0.1], [0.9, 0.1], [0.1, 0.9]]])
    with tempfile.TemporaryDirectory() as held:
        picture = pathlib.Path(held) / "base_color.png"
        for colour, faults in ((labels.srgb(np.array(spec["colour"])), 0), (np.array([1.0, 1.0, 0.0]), 1)):
            Image.new("RGB", (8, 8), tuple(int(round(value * 255)) for value in colour)).save(picture)
            found = baked_body.checked(points, np.array([[0, 1, 2]]), np.array([0]), ["suit"], uvs, picture,
                                       {"suit": spec}, {}, (0.0, 0.0))
            assert len(found["faults"]) == faults, found
    assert found["surfaces"]["suit"]["delta_e"] > 20


def test_a_dress_row_bakes_on_a_card_and_reads_the_palette_and_the_bake():
    import score.stages.people as people
    for look in bodies.looks():
        row = people.dress_row(look)
        assert row.paid and row.euros == dress.EUROS
        assert set(row.beside) == {bodies.MADE, "finish-route-palette", "surface-library", "surfaces-bake"}
        assert "baked" in {check.name for check in row.checks}


def test_each_person_of_a_look_wears_a_variant_of_its_own():
    """Owner, 2026-10-25: "Each one looks different": variant n of a body wears, for every part but a rigid one, the
    n-th of its surface's family by colour nearness (itself first); a library too small to tell two apart is a gap."""
    surfaces = {"skin_a": {"family": "skin", "colour": [0.5, 0.4, 0.3]},
                "skin_b": {"family": "skin", "colour": [0.4, 0.3, 0.2]},
                "skin_c": {"family": "skin", "colour": [0.1, 0.1, 0.1]},
                "suit_white": {"family": "fabric", "colour": [0.9, 0.9, 0.9]},
                "suit_grey": {"family": "fabric", "colour": [0.6, 0.6, 0.6]},
                "visor": {"family": "glass", "colour": [0.1, 0.1, 0.1]}}
    assert [dress.worn_name("skin_a", surfaces, {"variant": number}, "skin") for number in range(4)] == [
        "skin_a", "skin_b", "skin_c", "skin_a"]
    assert dress.worn_name("visor", surfaces, {"variant": 1}, "hard") == "visor"
    assert dress.worn_name("suit_white", surfaces, {"surface": "suit_grey", "variant": 1}, "cloth") == "suit_white"
    record = {"skin#0": {"painted": "skin_a", "role": "skin"}, "suit#1": {"painted": "suit_white", "role": "cloth"},
              "visor#2": {"painted": "visor", "role": "hard"}}
    assert [dress.variant_gap(record, surfaces, {"variant": number}) for number in range(6)] == [None] * 6
    gap = dress.variant_gap(record, surfaces, {"variant": 6})
    assert gap and "variant 0" in gap and "fabric, skin" in gap, gap
    import score.stages.people as people
    row = people.dress_row("astronaut-made", "suit_grey", 3)
    assert (row.name, row.params) == ("people-dress-astronaut-made-in-suit_grey-v3",
                                      {"surface": "suit_grey", "variant": 3})


def test_clearance_eases_out_and_back():
    angles = np.zeros(20)
    angles[10] = 0.3
    eased = clearance.spread(angles)
    assert eased[10] >= 0.3 and eased[8] > 0 and eased[0] == 0 and eased[19] == 0, eased


def test_each_full_look_has_its_own_page_row_reading_its_body_and_dress_alone():
    """#26: one look runs without the others: its page `people-look-<look>` reads its own body and dress only, at one
    look's estimate; and the line's hand-in is approved by its picks, so its likeness is measured, not blocked."""
    import score.stages.people as people
    from score.stages.people import look
    pages = {row.name: row for row in people.LOOKS}
    assert set(pages) == {f"{look.ROW}-{name}" for name in people.FULL}
    for name in people.FULL:
        page = pages[f"{look.ROW}-{name}"]
        assert set(page.after) == {f"people-dress-{name}", f"{bodies.BODY}-{name}"} and page.euros == look.EUROS
    assert json.loads((REPO / "data/props/people.json").read_text()).get("approved")


def test_a_looks_parts_are_their_own_priced_row_the_body_reads():
    """#21: the parts are never bought inside the body row: each look has a `people-look-parts-<look>` row, priced on
    its own and keyed on its take and outfit (not the clips), and its body row reads it."""
    built = {row.name: row for row in bodies.rows()}
    for look in bodies.looks():
        parts, body = built[f"{bodies.PARTS}-{look}"], built[f"{bodies.BODY}-{look}"]
        assert parts.paid and parts.euros == bodies.PARTS_EUROS and "clips" not in parts.files, parts
        assert body.after[parts.name] == (bodies.PARTS, 1) and body.euros < 3.0, body


def test_every_body_plays_the_clips_its_own_row_made_with_the_route():
    """#26: the clips and the rig are made inside the batch by people-clips-made (fixed seed), never read from the lost
    work folder; every body row reads them, and a full body is built and then put through the people route, no
    settle."""
    from score.stages.people_bodies import made_clips
    built = {row.name: row for row in bodies.rows()}
    assert made_clips.ROW_STAGE.paid and set(made_clips.CLIPS) >= {"standing", "walking", "bench"}
    assert {person["doing"] for place in json.loads((REPO / "data/people/rows.json").read_text())["places"]
            for person in people_rows.persons(place)} <= \
        set(made_clips.CLIPS), "a cast does a clip no body has"
    for look in bodies.looks():
        body = built[f"{bodies.BODY}-{look}"]
        assert body.after[made_clips.ROW] == (made_clips.ROW, 1) and "clips" not in body.files, body
    source = (REPO / "score/stages/people_bodies/bodies.py").read_text()
    assert '("build", "route")' in source and "settle\")" not in source


def test_the_clips_row_passes_only_with_every_clip_in_the_rig_and_its_seed():
    from score.stages.people_bodies import made_clips
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        (folder / "motions").mkdir()
        np.savez(folder / "rig.npz", **{f"clip_{clip}": np.zeros(1) for clip in made_clips.CLIPS})
        for clip in made_clips.CLIPS:
            (folder / "motions" / f"{clip}.record.json").write_text(json.dumps({"clip": clip, "seed": 1}))
        assert made_clips.judged(folder, {}, {}).answer == "pass"
        (folder / "motions" / "bench.record.json").write_text(json.dumps({"clip": "bench"}))
        assert made_clips.judged(folder, {}, {}).answer == "fail"
        (folder / "rig.npz").unlink()
        assert made_clips.judged(folder, {}, {}).answer == "unknown"


def test_the_triangles_are_counted_on_the_route_body_as_drawn():
    """The route adds the under layer and the closings: the gate counts the body glTF's near nodes, never the far."""
    import struct
    document = {"accessors": [{"count": 30}, {"count": 12}, {"count": 3000}],
                "meshes": [{"primitives": [{"indices": 0}, {"indices": 1}]}, {"primitives": [{"indices": 2}]}],
                "nodes": [{"name": "work", "mesh": 0}, {"name": "far", "mesh": 1}, {"name": "Hips"}]}
    text = json.dumps(document).encode()
    text += b" " * (-len(text) % 4)
    with tempfile.TemporaryDirectory() as held:
        folder = pathlib.Path(held)
        (folder / "checks").mkdir()
        (folder / "body.glb").write_bytes(struct.pack("<III", 0x46546C67, 2, 20 + len(text))
                                          + struct.pack("<II", len(text), 0x4E4F534A) + text)
        (folder / "checks" / "route.json").write_text("{}")
        found = bodies.judge_triangles(folder, {}, {})
        assert found.answer == "pass" and found.measures["triangles"] == 14, found


def test_parts_pass_only_when_every_part_is_named():
    with tempfile.TemporaryDirectory() as held:
        found = [{"name": "coat", "role": "garment", "material": "FABRIC"}, {"name": "boot_r", "role": "hard"}]
        (pathlib.Path(held) / "parts.json").write_text(json.dumps({"parts": found}))
        assert bodies.judge_parts(pathlib.Path(held), {}, {}).answer == "fail"
        found[1]["material"] = "LEATHER"
        (pathlib.Path(held) / "parts.json").write_text(json.dumps({"parts": found}))
        assert bodies.judge_parts(pathlib.Path(held), {}, {}).answer == "pass"


def test_a_failed_tucks_record_refuses_the_body_before_any_machine():
    """#21: a look whose settled tucks failed in every clip on the same inputs is Blocked, a predicted gap, never
    rented for."""
    from score import graph
    bodies.refused_on_record(None, "people-body-x")
    try:
        bodies.refused_on_record({"worst_tuck_out_mm": 9.32, "clips": 4}, "people-body-x")
        raise AssertionError("a failed tucks record was bought again")
    except graph.Blocked as blocked:
        assert "predicted gap" in str(blocked) and "9.32" in str(blocked)


def test_full_or_far_follows_the_design():
    """Which looks get a full body is the design's (full.py): a person filling a quarter of its concept's frame height
    is full, one filling a twentieth is far, one with no share measured is full, and a crowd's look is far; the share
    is the tallest of the row's boxes over the picture's height."""
    from score.stages.people_bodies import full
    design = {"places": {"a": {"rows": {"near": {"looks": ["near-work"], "share": 0.25},
                                        "far": {"looks": ["far-work"], "share": 0.05},
                                        "unmeasured": {"looks": ["plain-work"], "share": None},
                                        "crowd": {"crowd": "crowd-coat", "share": 0.4}}}}}
    assert full.full_looks(design) == {"near-work", "plain-work"}, full.full_looks(design)
    row = {"boxes": [[0, 100, 50, 484], [0, 0, 10, 100]], "box": [0, 0, 10, 100]}
    assert people_rows.concept_share(row, [2752, 1536]) == 0.25
    assert people_rows.concept_share({"box": [0, 0, 10, 153.6]}, [2752, 1536]) == 0.1
    assert people_rows.concept_share({}, [2752, 1536]) is None and people_rows.concept_share(row, None) is None


def test_todays_design_makes_the_tube_player_full_and_the_crowd_far():
    """On today's data/people/rows.json: the tube's person on the right (a quarter of the concept's height) gets a
    full body; the square's crowd look stays far; every rule shares one FAR_SHARE."""
    sys.path.insert(0, str(REPO / "tools/usd"))
    import contents
    from score.stages.cast import spread
    from score.stages.people_bodies import full
    looks = bodies.looks()
    assert not looks["person_uniform-made"].get("far_only") and looks["crowd-made"]["far_only"], looks
    assert full.FAR_SHARE == spread.FAR_SHARE == contents.FAR_SHARE


def test_the_body_rows_follow_the_design_s_share():
    """The body rows read the design, nothing else: today's rows.json with the tube's person shrunk under FAR_SHARE
    makes its look far, and the same rows with the crowd's look given to a near person make it full."""
    design = json.loads(bodies.DESIGN.read_text())
    tube = design["places"]["tube"]["rows"]["person_right"]
    assert tube["looks"] == ["person_uniform-made"], tube
    held = bodies.DESIGN
    with tempfile.TemporaryDirectory() as folder:
        bodies.DESIGN = pathlib.Path(folder) / "rows.json"
        try:
            bodies.DESIGN.write_text(json.dumps({**design, "places": {**design["places"], "tube": {
                **design["places"]["tube"], "rows": {"person_right": {**tube, "share": 0.05}}}}}))
            assert bodies.looks()["person_uniform-made"].get("far_only"), "a far person kept a full body"
            bodies.DESIGN.write_text(json.dumps({"places": {"p": {"rows": {
                "near": {"looks": ["crowd-made"], "share": 0.3}}}}}))
            made = bodies.looks()
            assert not made["crowd-made"].get("far_only") and made["person_uniform-made"].get("far_only"), made
        finally:
            bodies.DESIGN = held


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("people stage checks pass")
