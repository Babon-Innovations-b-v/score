"""The shared loop (#41): its rows in the table in order, an adapter's after-steps held to its ends and its layer, the
rough model's registration to the plan, the parts split read against it, and what the loop hands an after-step.
No spend, no model made. Run: .venv/bin/python -m pytest score/stages/shapes_first
"""
import fnmatch
import json
import pathlib
import re
import struct
import tempfile

import pytest

from score import checks, contracts, graph, stages
from score.stages import shapes_first
import score.stages.props.closeup_row as closeup_row
import score.stages.props.prop_data as prop_data
import score.stages.shapes_first.align as align
import score.stages.shapes_first.made as made
from score.stages.surfaces import surface_data

# These tests hold the data/props and data/surfaces places; a designed place's hand-in (the home's design/, which
# the sandbox links) is prepare_test.py's, so none is read here.
import score.stages.surfaces  # noqa: E402
prop_data.DESIGN = surface_data.DESIGN = pathlib.Path(tempfile.mkdtemp()) / "no design"
score.stages.surfaces.data.DESIGN = surface_data.DESIGN  # the table's own import of it (bare `surface_data`)

REPO = pathlib.Path(__file__).resolve().parents[3]
LOOP = ("rough-model", "rough-align", "props-inputs", "closeup", "pixal", "finish-route-views", "likeness")


def glb(path, low, high, node=None):
    """A binary glTF of one box's corners as a triangle list's positions (its accessor's bounds are what is read)."""
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    data = b"".join(struct.pack("<3f", *corner) for corner in corners[:6])
    gltf = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(data)}],
            "bufferViews": [{"buffer": 0, "byteLength": len(data)}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": 6, "type": "VEC3", "min": list(low),
                           "max": list(high)}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}}]}],
            "nodes": [{"mesh": 0, **(node or {})}], "scenes": [{"nodes": [0]}], "scene": 0}
    text = json.dumps(gltf).encode()
    text += b" " * (-len(text) % 4)
    body = struct.pack("<II", len(text), 0x4E4F534A) + text + struct.pack("<II", len(data), 0x004E4942) + data
    path.write_bytes(b"glTF" + struct.pack("<II", 2, 12 + len(body)) + body)


def aligned(tmp_path, low, high, floor=((-4.0, -2.0), (4.0, 2.0)), node=None, walls=None):
    """The rough-align output of a box model onto a plan's floor."""
    rough, plan, out = tmp_path / "rough", tmp_path / "plan", tmp_path / "out"
    for folder in (rough, plan, out):
        folder.mkdir()
    glb(rough / "rough.glb", low, high, node)
    (rough / "rough.json").write_text(json.dumps({"take": "here-rough-0"}))
    (plan / "plan.json").write_text(json.dumps({"place": "here", "floor": [list(corner) for corner in floor],
                                                "floor_height": 0.5, "walls": walls or {"high": 3.0}}))
    inputs = {"rough-model": rough, "plan": plan}
    align.make(inputs, out, 0, {})
    return out, inputs


def corners_placed(record, low, high):
    """The model box's corners through the registration's matrix."""
    matrix = record["matrix"]
    return [[sum(matrix[row][column] * point[column] for column in range(3)) + matrix[row][3] for row in range(3)]
            for point in [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]]


def test_the_rough_model_is_scaled_to_the_plan_s_metres_and_stood_on_its_floor(tmp_path):
    low, high = (-1.0, -0.2, 0.0), (1.0, 2.8, 1.0)  # 2 wide, 3 high, 1 deep: the plan's 8 by 4 at four times
    out, _ = aligned(tmp_path, low, high)
    record = json.loads((out / "align.json").read_text())
    assert record["turn_degrees"] == 0 and record["scale"] == pytest.approx(4.0)
    placed = corners_placed(record, low, high)
    assert min(point[0] for point in placed) == pytest.approx(-4) and max(point[0] for point in placed) == pytest.approx(4)
    assert min(point[2] for point in placed) == pytest.approx(-2) and max(point[2] for point in placed) == pytest.approx(2)
    assert min(point[1] for point in placed) == pytest.approx(0.5)  # on the floor's height
    assert record["misfit"] == {"wide": 1.0, "deep": 1.0, "high": 4.0}
    gltf = align.glb_json(out / "aligned.glb")
    root = gltf["nodes"][gltf["scenes"][0]["nodes"][0]]
    assert root["children"] == [0] and root["matrix"][12:15] == [row[3] for row in record["matrix"][:3]]
    assert align.CHECKS[0].judge(out, {}, {}).answer == checks.PASS


def test_a_model_drawn_turned_is_turned_to_the_plan(tmp_path):
    low, high = (0.0, 0.0, 0.0), (1.0, 1.0, 2.0)  # 1 wide, 2 deep onto 8 wide, 4 deep: a quarter turn fits
    out, _ = aligned(tmp_path, low, high)
    record = json.loads((out / "align.json").read_text())
    assert record["turn_degrees"] == 90 and record["scale"] == pytest.approx(4.0)
    placed = corners_placed(record, low, high)
    assert max(point[0] for point in placed) - min(point[0] for point in placed) == pytest.approx(8)


def test_a_model_whose_nodes_carry_a_transform_is_not_registered_and_says_why(tmp_path):
    out, _ = aligned(tmp_path, (0, 0, 0), (1, 1, 1), node={"scale": [2, 2, 2]})
    assert not (out / "aligned.glb").exists()
    verdict = align.CHECKS[0].judge(out, {}, {})
    assert verdict.answer == checks.FAIL and "carries its own scale" in verdict.findings[0]


def test_the_parts_split_is_held_to_the_registered_floor(tmp_path):
    out, inputs = aligned(tmp_path, (-1.0, 0.0, 0.0), (1.0, 3.0, 1.0))
    split = tmp_path / "split"
    split.mkdir()
    (split / "rows.json").write_text(json.dumps({"rows": [{"id": "crate", "size": [1.0, 3.9, 1.0]},
                                                          {"id": "beam", "size": [9.0, 0.3, 0.3]},
                                                          {"id": "ground_crater", "size": [30.0, 30.0, 2.0],
                                                           "layer": "terrain"}]}))
    found = align.judge_rows_fit(split, {"rough-align": out}, {})
    assert found.answer == checks.FAIL and found.findings == (
        "beam: 9.0 by 0.3 m fits no way on the 8.00 by 4.00 m floor",)
    assert found.measures["rows past the rough model"] == 1
    assert found.measures["rows round the floor"] == 1  # a detail area of the ground round the place
    assert align.judge_rows_fit(split, {}, {}).answer == checks.UNKNOWN
    person = {"id": "player-work", "size": None, "layer": "people"}  # a line no place owns: held to no plan
    (split / "rows.json").write_text(json.dumps({"rows": [person]}))
    assert align.judge_rows_fit(split, {}, {}).answer == checks.PASS


def test_an_after_step_gets_the_made_models_with_their_finishes_or_the_gaps(tmp_path):
    split, likeness, bake, parts = (tmp_path / name for name in ("split", "likeness", "bake", "parts"))
    for folder in (split, likeness, bake, parts):
        folder.mkdir()
    rows = [{"id": "seat", "take": "seat-s1", "layer": "objects"}, {"id": "lamp", "take": "lamp-s1", "layer": "objects"},
            {"id": "rock", "take": None, "layer": "objects"}, {"id": "path", "take": "path-t1", "layer": "terrain"}]
    (split / "rows.json").write_text(json.dumps({"rows": rows}))
    (likeness / "likeness.json").write_text(json.dumps({"objects": {
        "seat": {"route": "prop", "model": "elsewhere.gltf"}, "lamp": {"route": "prop", "model": None,
                                                                       "missing": "no close-up"},
        "rock": {"route": "code", "model": "/data/rock.gltf"}}}))
    (bake / "baked.json").write_text(json.dumps({"seat_1": {"parts": "seat-s1"}}))
    (parts / "parts.json").write_text(json.dumps({"takes": {"seat-s1": {"parts": [{"surface": "steel"}]}}}))
    inputs = {"props-inputs": split, "likeness": likeness, "surfaces-bake": bake, "surfaces-parts": parts}
    assert made.made(inputs, "objects") == {
        "seat": {"route": "prop", "model": str(bake / "made/seat_1.gltf"), "take": "seat-s1",
                 "finishes": [{"surface": "steel"}], "failures": {}},
        "lamp": {"gap": "no close-up"}, "rock": {"route": "code", "model": "/data/rock.gltf", "finishes": []}}
    assert made.made(inputs, "terrain") == {"path": {"gap": "no likeness record: the loop never reached its model"}}


def row(name, after):
    return graph.Stage(name, "place", lambda *arguments: None, contracts.Contract(name, 1, lambda folder: []),
                       after=after)


def test_an_after_step_must_read_the_loop_s_ends_and_runs_only_where_its_layer_handed_rows():
    with pytest.raises(ValueError, match="lacks"):
        shapes_first.rows((shapes_first.OBJECTS, shapes_first.Adapter("terrain", (row("join", {"terrain": ("g", 1)}),))))
    with pytest.raises(ValueError, match="share a layer"):
        shapes_first.rows((shapes_first.OBJECTS, shapes_first.Adapter("objects")))
    found = shapes_first.rows((shapes_first.Adapter("terrain", (row("join", dict(made.ENDS)),)),))
    join = found[-1]
    kept, prop_data.DESIGN = prop_data.DESIGN, pathlib.Path(tempfile.mkdtemp())  # a hand-in of the test's own
    (prop_data.DESIGN / "campgrounds.json").write_text(json.dumps({"objects": {"cairn": {"route": "prop",
                                                                                         "take": "cairn-p1"}}}))
    try:
        assert join.name == "join" and not join.applies("campgrounds")  # its rows are all on the objects layer
        objects = shapes_first.rows((shapes_first.Adapter("objects", (row("lay", dict(made.ENDS)),)),))[-1]
        assert objects.applies("campgrounds") and not objects.applies("hub")
    finally:
        prop_data.DESIGN = kept


def test_the_table_runs_the_loop_in_its_order():
    table = {stage.name: stage for stage in stages.STAGES}
    assert [stage.name for stage in stages.STAGES].count("rough-model") == 1
    for earlier, later in zip(LOOP, LOOP[1:]):
        if later == "likeness":
            earlier = "surfaces-bake"
        assert earlier in table[later].after, (earlier, later)
    assert "fits the plan" in {check.name for check in table["props-inputs"].checks}


def test_the_terrain_adapter_only_joins_its_rows_into_the_ground_after_the_model():
    table = {stage.name: stage for stage in stages.STAGES}
    assert [stage.name for stage in stages.STAGES].count("ground-join") == 1
    assert made.ENDS.keys() <= table["ground-join"].after.keys() and "ground-join" in table["assembly"].after
    assert [step.name for step in shapes_first.TERRAIN.after] == ["ground-join"]
    assert not table["ground-join"].applies("wreck")  # no terrain rows handed in until its rough model is registered


# The rows outside the loop that read a loop row, each with why. A model layer takes its models through the loop's ends
# (an adapter's after-step: made.ENDS through made.made); a row joins here only with its reason (#41).
READS_THE_LOOP = {
    "complete": "the completion gate: judges likeness and surfaces-check, lays no model",
    "library": "the hand-over: every accepted output of the line to the creator's library, lays no model",
    "assembly": "the object layer laid (OBJECTS: nothing after the model), its baked models and their paint",
    "earth-seed": "the scene's base: its shell from its locked plan painted from its surface library, lays no model",
    "scene-record": "the scene's record: its shell and stairs named with surfaces from its surface library, lays no model",
    "settle": "the motion layer's physics: not on an adapter yet (#41's motion track)",
    "crops-layer": "the motion layer's growth: not on an adapter yet (#41's motion track)",
}
# Every paid row outside the loop and what it makes: none a model, but the named exceptions MADE_OUTSIDE holds.
MAKES_NO_MODEL = {
    "settle": "rest poses of the made models", "sound": "sounds", "demo-film*": "films",
    "physics-trial": "a physics trial",
    "light-passes": "renders",
    "crops-concept": "a concept picture", "crops-boxes": "measured boxes", "crops-look": "renders",
    "library-clips*": "preview clips (renders)",
    "people-clips-made": "Kimodo clips and the mean rig", "people-look": "renders of the made bodies (its review page)",
}
# Paid rows that make a model outside the loop: each a named exception its own record names.
MADE_OUTSIDE = {
    "people-look-parts-*": "data/props/people.json `failures`: the garments' second split",
    "people-body-*": "data/props/people.json `failures`: the body built from the raw take",
}


def matched(name, patterns):
    return next((pattern for pattern in patterns if fnmatch.fnmatch(name, pattern)), None)


def test_every_model_layer_reaches_its_models_only_through_the_loop():
    loop = {row.name for row in shapes_first.rows(())}
    after_steps = {step.name for adapter in shapes_first.ADAPTERS for step in adapter.after}
    around, reading = [], set()
    for row in stages.STAGES:
        if row.name in loop or not loop & row.after.keys():
            continue
        reading.add(row.name)
        through = row.name in after_steps and made.ENDS.keys() <= row.after.keys()
        if not through and row.name not in READS_THE_LOOP:
            around.append(f"{row.name} reads {sorted(loop & row.after.keys())}")
    assert not around, f"rows reaching the loop's models around its ends (made.ENDS): {around}"
    assert READS_THE_LOOP.keys() <= reading, f"no longer read the loop: {sorted(READS_THE_LOOP.keys() - reading)}"


def test_a_paid_row_outside_the_loop_makes_no_model_but_a_named_exception():
    loop = {row.name for row in shapes_first.rows(())}
    records = json.loads((prop_data.FOLDER / "people.json").read_text())["objects"].values()
    named = {row for entry in records for text in (entry.get("failures") or {}).values()
             for row in re.findall(r"people-[a-z0-9_-]*[a-z0-9]", text)}
    unsaid, unnamed = [], []
    for row in stages.STAGES:
        if not row.paid or row.name in loop or matched(row.name, MAKES_NO_MODEL):
            continue
        exception = matched(row.name, MADE_OUTSIDE)
        if exception is None:
            unsaid.append(row.name)
        elif exception.startswith("people-") and row.name not in named:
            unnamed.append(row.name)
    assert not unsaid, f"paid rows outside the loop that say neither what they make nor their exception: {unsaid}"
    assert not unnamed, f"people rows their record's `failures` does not name: {unnamed}"


def test_every_layer_the_hand_in_names_is_an_adapter_s():
    registered = {adapter.layer for adapter in shapes_first.ADAPTERS}
    for path in sorted(prop_data.FOLDER.glob("*.json")):
        layers = {closeup_row.layer_of(entry) for entry in json.loads(path.read_text())["objects"].values()}
        assert layers <= registered, (path.name, layers - registered)
