"""Every model goes through the shared loop (#41): its rows stand in the table in order, every model layer reaches its
models only through the loop's ends and every paid row outside it makes no model but a named exception, an adapter's
after-steps are held to those ends and its layer; the rough model is registered to the plan (scaled, turned and
stood on its floor, worked out by hand from the boxes below), the parts split is read against it, and an after-step
gets the made models or their gaps. No spend, no model made.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
score/stages/shapes_first/test_every_model_goes_through_the_loop.py
"""
import fnmatch
import json
import pathlib
import re
import struct

import pytest

from score import checks, contracts, graph, stages
from score.stages import shapes_first
import score.stages.props.closeup_row as closeup_row
import score.stages.props.prop_data as prop_data
import score.stages.shapes_first.align as align
import score.stages.shapes_first.floor_fit as floor_fit
import score.stages.shapes_first.made as made
from score.stages.surfaces import surface_data

import score.stages.surfaces  # noqa: E402


@pytest.fixture(autouse=True)
def no_design(tmp_path, monkeypatch):
    """No designed place's hand-in is read unless a test writes one (the home's design/, which the sandbox links)."""
    nowhere = tmp_path / "no design"
    monkeypatch.setattr(prop_data, "DESIGN", nowhere)
    monkeypatch.setattr(surface_data, "DESIGN", nowhere)
    monkeypatch.setattr(score.stages.surfaces.data, "DESIGN", nowhere)  # the table's own import of it

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
    """A box 2 wide, 3 high, 1 deep onto the plan's 8 by 4 floor: four times, unturned, spanning -4 to 4 and -2 to 2,
    its foot on the floor's 0.5 m.
    Break: score/stages/shapes_first/align.py: `floor - scale * least[1],` -> `floor,`"""
    low, high = (-1.0, -0.2, 0.0), (1.0, 2.8, 1.0)  # 2 wide, 3 high, 1 deep: the plan's 8 by 4 at four times
    out, _ = aligned(tmp_path, low, high)
    record = json.loads((out / "align.json").read_text())
    assert record["turn_degrees"] == 0 and record["scale"] == pytest.approx(4.0)
    placed = corners_placed(record, low, high)
    across, deep = [point[0] for point in placed], [point[2] for point in placed]
    assert (min(across), max(across)) == (pytest.approx(-4), pytest.approx(4))
    assert (min(deep), max(deep)) == (pytest.approx(-2), pytest.approx(2))
    assert min(point[1] for point in placed) == pytest.approx(0.5)  # on the floor's height
    assert record["misfit"] == {"wide": 1.0, "deep": 1.0, "high": 4.0}
    gltf = align.glb_json(out / "aligned.glb")
    root = gltf["nodes"][gltf["scenes"][0]["nodes"][0]]
    assert root["children"] == [0] and root["matrix"][12:15] == [row[3] for row in record["matrix"][:3]]
    assert align.CHECKS[0].judge(out, {}, {}).answer == checks.PASS


def test_a_model_drawn_turned_is_turned_to_the_plan(tmp_path):
    """1 wide and 2 deep onto 8 wide and 4 deep: a quarter turn fits, four times, 8 across.
    Break: score/stages/shapes_first/align.py: `return min(TURNS, key=misfit)` -> `return 0`"""
    low, high = (0.0, 0.0, 0.0), (1.0, 1.0, 2.0)  # 1 wide, 2 deep onto 8 wide, 4 deep: a quarter turn fits
    out, _ = aligned(tmp_path, low, high)
    record = json.loads((out / "align.json").read_text())
    assert record["turn_degrees"] == 90 and record["scale"] == pytest.approx(4.0)
    placed = corners_placed(record, low, high)
    assert max(point[0] for point in placed) - min(point[0] for point in placed) == pytest.approx(8)


def test_a_model_whose_nodes_carry_a_transform_is_not_registered_and_says_why(tmp_path):
    """A node scaled twice: its extent in the mesh frame is not its size, so no registration, said by name.
    Break: score/stages/shapes_first/align.py:
        `for index, node in enumerate(gltf.get("nodes", [])) for key in NODE_TRANSFORMS if key in node]`
        -> `for index, node in enumerate(gltf.get("nodes", [])) for key in NODE_TRANSFORMS if False]`"""
    out, _ = aligned(tmp_path, (0, 0, 0), (1, 1, 1), node={"scale": [2, 2, 2]})
    assert not (out / "aligned.glb").exists()
    verdict = align.CHECKS[0].judge(out, {}, {})
    assert verdict.answer == checks.FAIL and "carries its own scale" in verdict.findings[0]


def test_the_parts_split_is_held_to_the_registered_floor(tmp_path):
    """On the 8 by 4 floor a 9 m beam fits no way, a crate does; a terrain detail area round the floor is counted,
    not held; without a registration unknown; a line no place owns is held to no plan.
    Break: score/stages/shapes_first/align.py: `rows = [row for row in split if row.get("layer") not in ROUND]`
        -> `rows = split`"""
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


def test_the_plan_s_structure_and_what_stands_beyond_it_are_counted_not_held_to_its_floor(tmp_path):
    """The kept plan's structure (its floor) and beyond (the rocket) are counted, never held to the floor; a rug as
    wide as the floor, rounded, fits; with no kept plan all three oversized rows fail.
    Break: score/stages/shapes_first/floor_fit.py: `wide, deep = wide + ROUNDING, deep + ROUNDING` -> `pass`
    Break: score/stages/shapes_first/floor_fit.py:
        `**{f"rows of the plan's {name}": ids for name, ids in off_floor(inputs).items()}}` -> `}`"""
    out, _ = aligned(tmp_path, (-1.0, 0.0, 0.0), (1.0, 3.0, 1.0))
    split = tmp_path / "split"
    split.mkdir()
    rows = [{"id": "floor", "size": [9.0, 5.0, 0.1]}, {"id": "rocket", "size": [10.0, 10.0, 60.0]},
            {"id": "beam", "size": [9.0, 0.3, 0.3]}, {"id": "rug", "size": [8.0005, 4.0, 0.01]}]
    (split / "rows.json").write_text(json.dumps({"rows": rows}))
    kept = tmp_path / "kept.json"
    kept.write_text(json.dumps({"structure": ["floor", "rocket"], "beyond": ["rocket"]}))
    found = floor_fit.judge_rows_fit(split, {"rough-align": out, floor_fit.KEPT_PLAN: kept}, {})
    assert found.answer == checks.FAIL and found.findings == (
        "beam: 9.0 by 0.3 m fits no way on the 8.00 by 4.00 m floor",)  # a rug as wide as the floor, rounded, fits
    assert found.measures["rows of the plan's structure"] == 2 and found.measures["rows of the plan's beyond"] == 0
    assert floor_fit.judge_rows_fit(split, {"rough-align": out}, {}).measures["failing"] == 3  # no kept plan: all held


def test_a_building_the_plan_lays_against_its_edge_and_a_far_row_are_counted_not_held_to_its_floor(tmp_path):
    """Fault 2026-10-26 (props-inputs@square): the square's buildings stand on the ground round its 29.86 m floor, the
    plan laying only their faces at its edges, and failed as floor objects at their read 30 by 30 m. Read without
    their anchors (no inventory) the fault's measures come back; with them the buildings are counted past the edge,
    and the far rocket (also the plan's structure) is counted once. A beam on the ground in the middle and a stall on
    the plaza at the edge stay held.
    Break: score/stages/shapes_first/floor_fit.py:
        `return min(x, y) <= ROUNDING or x + across >= wide - ROUNDING or y + along >= deep - ROUNDING` -> `return True`
    Break: score/stages/shapes_first/floor_fit.py: `"rows past the plan's edge": past_edge(plan, inventory)}` -> `}`"""
    out, _ = aligned(tmp_path, (-1.0, 0.0, -1.0), (1.0, 3.0, 1.0), floor=((-14.93, -14.93), (14.93, 14.93)))
    split = tmp_path / "split"
    split.mkdir()
    buildings = {"left_building": [30.0, 30.0, 24.0], "right_building": [30.0, 30.0, 20.0],
                 "foreground_building": [40.0, 20.0, 15.0]}
    rows = [{"id": name, "size": size} for name, size in buildings.items()] + [
        {"id": "rocket", "size": [15.8, 4.2, 60.0], "far": {"pieces": 1, "length": 15.8}},
        {"id": "city_skyline", "size": [100.0, 30.0, 100.0], "far": {"pieces": 10, "length": 1000.0}},
        *({"id": f"thing_{number}", "size": [1.0, 1.0, 1.0]} for number in range(9))]
    (split / "rows.json").write_text(json.dumps({"rows": rows}))
    kept = tmp_path / "kept.json"
    items = [["LEFT BUILDING 1", 0.0, 15.77, 2.145, 6.609, "E", "item"],
             ["RIGHT BUILDING 1", 26.38, 4.464, 2.609, 17.799, "W", "item"],
             ["FOREGROUND BUILDING 1", 10.784, 23.423, 7.421, 5.566, "N", "item"]]
    kept.write_text(json.dumps({"w": 28.989, "d": 28.989, "items": items, "beyond": [],
                                "rows": {item[0]: [item[0].lower().replace(" 1", "").replace(" ", "_")] for item in items},
                                "structure": ["sky", "sea", "city_skyline", "rocket", "planet", "plaza"]}))
    inputs = {"rough-align": out, floor_fit.KEPT_PLAN: kept}
    found = floor_fit.judge_rows_fit(split, inputs, {})
    assert found.answer == checks.FAIL and len(found.findings) == 3
    assert found.findings[0] == "left_building: 30.0 by 30.0 m fits no way on the 29.86 by 29.86 m floor"
    assert {key: found.measures[key] for key in ("failing", "rows of the plan's beyond", "rows of the plan's structure",
                                                 "rows past the rough model", "rows round the floor")} == {
        "failing": 3, "rows of the plan's beyond": 0, "rows of the plan's structure": 2, "rows past the rough model": 3,
        "rows round the floor": 0}
    inventory = tmp_path / "inventory.json"
    anchors = {"rows": [{"id": name, "anchor": "ground"} for name in buildings]}
    inventory.write_text(json.dumps(anchors))
    found = floor_fit.judge_rows_fit(split, {**inputs, "inventory": inventory}, {})
    assert found.answer == checks.PASS and found.measures["rows past the plan's edge"] == 3
    assert found.measures["rows of the plan's structure"] == 2 and found.measures["rows laid far off"] == 0
    middle = [["BEAM 1", 10.0, 10.0, 9.0, 0.3, None, "item"], ["STALL 1", 0.0, 2.0, 2.0, 2.0, None, "item"]]
    kept.write_text(json.dumps({"w": 28.989, "d": 28.989, "items": items + middle, "structure": [],
                                "rows": {**{item[0]: [item[0].lower().replace(" 1", "").replace(" ", "_")]
                                            for item in items}, "BEAM 1": ["beam"], "STALL 1": ["stall"]}}))
    rows += [{"id": "beam", "size": [31.0, 0.3, 0.3]}, {"id": "stall", "size": [31.0, 2.0, 3.0]}]
    (split / "rows.json").write_text(json.dumps({"rows": rows}))
    inventory.write_text(json.dumps({"rows": [*anchors["rows"], {"id": "beam", "anchor": "ground"},
                                              {"id": "stall", "anchor": "on:plaza"}]}))
    found = floor_fit.judge_rows_fit(split, {**inputs, "inventory": inventory}, {})
    assert [finding.split(":")[0] for finding in found.findings] == ["beam", "stall"]
    assert found.measures["rows laid far off"] == 2  # no longer the plan's structure: counted as laid far off


def test_the_table_s_split_reads_the_kept_plan_with_floor_fit_s_gate():
    """Fault 2026-10-24 (eight places' shells failed the floor): the table's parts split gates on floor_fit's judge,
    which reads the kept plan, not align's.
    Break: score/stages/__init__.py: `checks=tuple(fit if check.name == fit.name else check for check in row.checks))`
        -> `checks=row.checks)`"""
    split = {stage.name: stage for stage in stages.STAGES}["props-inputs"]
    fit = next(check for check in split.checks if check.name == "fits the plan")
    assert fit.judge.__wrapped__ is floor_fit.judge_rows_fit


def test_an_after_step_gets_the_made_models_with_their_finishes_or_the_gaps(tmp_path):
    """The seat's take baked as seat_1 hands its baked model and its parts' finishes; the lamp's missing close-up is
    its gap; the code rock its own model; a layer whose rows never reached the likeness is a gap each.
    Break: score/stages/shapes_first/made.py: `found.setdefault(entry["parts"], pathlib.Path(bake) / "made" /
        f"{model}.gltf")`
        -> `found.setdefault(model, pathlib.Path(bake) / "made" / f"{model}.gltf")`
    Break: score/stages/shapes_first/made.py: `    if "missing" in entry:` -> `    if False:`"""
    split, likeness, bake, parts = (tmp_path / name for name in ("split", "likeness", "bake", "parts"))
    for folder in (split, likeness, bake, parts):
        folder.mkdir()
    rows = [{"id": "seat", "take": "seat-s1", "layer": "objects"},
            {"id": "lamp", "take": "lamp-s1", "layer": "objects"},
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


def test_an_after_step_must_read_the_loop_s_ends_and_runs_only_where_its_layer_handed_rows(tmp_path, monkeypatch):
    """An after-step lacking the ends is refused, two adapters on one layer are refused, and an after-step applies
    only where the place handed rows of its layer (the campgrounds' cairn is on the objects layer, the hub hands none).
    Break: score/stages/shapes_first/__init__.py: `if step.grain != "place" or missing:` -> `if step.grain != "place":`
    Break: score/stages/shapes_first/__init__.py: `if len(set(layers)) != len(layers):` -> `if False:`
    Break: score/stages/shapes_first/__init__.py: `return handed(place, layer) and (applies is None or applies(place))`
        -> `return applies is None or applies(place)`"""
    with pytest.raises(ValueError, match="lacks"):
        lacking = shapes_first.Adapter("terrain", (row("join", {"terrain": ("g", 1)}),))
        shapes_first.rows((shapes_first.OBJECTS, lacking))
    with pytest.raises(ValueError, match="share a layer"):
        shapes_first.rows((shapes_first.OBJECTS, shapes_first.Adapter("objects")))
    found = shapes_first.rows((shapes_first.Adapter("terrain", (row("join", dict(made.ENDS)),)),))
    join = found[-1]
    monkeypatch.setattr(prop_data, "DESIGN", tmp_path / "design")  # a hand-in of the test's own
    prop_data.DESIGN.mkdir()
    (prop_data.DESIGN / "campgrounds.json").write_text(json.dumps({"objects": {"cairn": {"route": "prop",
                                                                                         "take": "cairn-p1"}}}))
    assert join.name == "join" and not join.applies("campgrounds")  # its rows are all on the objects layer
    objects = shapes_first.rows((shapes_first.Adapter("objects", (row("lay", dict(made.ENDS)),)),))[-1]
    assert objects.applies("campgrounds") and not objects.applies("hub")


def test_the_table_runs_the_loop_in_its_order():
    """Each loop row reads the one before it (the likeness reads the bake), and the split gates on the plan.
    Break: score/stages/shapes_first/__init__.py:
        `SPLIT = dataclasses.replace(props.INPUTS, after={**props.INPUTS.after, "rough-align": ("rough-align", 1)},`
        -> `SPLIT = dataclasses.replace(props.INPUTS, after={**props.INPUTS.after},`"""
    table = {stage.name: stage for stage in stages.STAGES}
    assert [stage.name for stage in stages.STAGES].count("rough-model") == 1
    for earlier, later in zip(LOOP, LOOP[1:]):
        if later == "likeness":
            earlier = "surfaces-bake"
        assert earlier in table[later].after, (earlier, later)
    assert "fits the plan" in {check.name for check in table["props-inputs"].checks}


def test_the_terrain_adapter_only_joins_its_rows_into_the_ground_after_the_model():
    """ground-join is the terrain layer's one after-step, reads the loop's ends, the assembly reads it, and it runs
    nowhere a place handed no terrain rows (the wreck).
    Break: score/stages/shapes_first/__init__.py: `return handed(place, layer) and (applies is None or applies(place))`
        -> `return applies is None or applies(place)`"""
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
    "scene-record": "the scene's record: its shell and stairs named with surfaces from its surface library, lays no "
                    "model",
    "surface-tiles": "tile pictures of the scene's library surfaces for its shell, lays no model",
    "settle": "the motion layer's physics: not on an adapter yet (#41's motion track)",
    "crops-layer": "the motion layer's growth: not on an adapter yet (#41's motion track)",
    "motion": "the moving objects' baked models laid as the settle lays them: not on an adapter yet (#41's motion "
              "track)",
    "effects-layer": "the emitting objects' baked models laid as the settle lays them: not on an adapter yet (#41)",
}
# Every paid row outside the loop and what it makes: none a model, but the named exceptions MADE_OUTSIDE holds.
MAKES_NO_MODEL = {
    "settle": "rest poses of the made models", "sound": "sounds", "demo-film*": "films",
    "physics-trial": "a physics trial",
    "light-passes": "renders", "surface-tiles": "surface tile pictures",
    "crops-concept": "a concept picture", "crops-boxes": "measured boxes", "crops-look": "renders",
    "straight-masks": "SAM 3 masks of the thin straight rows, read by prepare's prediction alone",
    "body-face-*": "a body's face palette and recipe variant", "people-clips-made": "Kimodo clips and the mean rig",
    "people-look-*": "renders of a made body (its review page)",
    "people-dress-*": "the loop's library surfaces baked onto a made body's own model, every variant (c3a5a275)",
}
# Paid rows that make a model outside the loop: each a named exception its own record names.
MADE_OUTSIDE = {
    "people-look-parts-*": "data/props/people.json `failures`: the garments' second split",
    "people-body-*": "data/props/people.json `failures`: the body built from the raw take",
}


def matched(name, patterns):
    return next((pattern for pattern in patterns if fnmatch.fnmatch(name, pattern)), None)


def test_every_model_layer_reaches_its_models_only_through_the_loop():
    """#41: a row outside the loop reading a loop row is an after-step reading its ends, or named with its reason.
    Break: score/stages/__init__.py: `models=(sound.moss_takes.KIND,), after={"motion": ("motion-layer", 2)},`
        -> `models=(sound.moss_takes.KIND,), after={"motion": ("motion-layer", 2), "pixal": ("props-pixal", 1)},`"""
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
    """Every paid row outside the loop says what it makes (no model) or is a named exception its record names.
    Break: score/stages/__init__.py: `beside={"scene-tree": ("openusd-stage", 1)}, downward=True,
        neighbours=held_scenes)`
        -> `beside={"scene-tree": ("openusd-stage", 1)}, downward=True, neighbours=held_scenes, paid=True,
        euros=1.0)`"""
    loop = {row.name for row in shapes_first.rows(())}
    records = json.loads((prop_data.FOLDER / "people.json").read_text())["objects"].values()
    named = {row for entry in records for text in (entry.get("failures") or {}).values()
             for row in re.findall(r"people-[a-z0-9_-]*[a-z0-9]", text)}
    unsaid, unnamed = [], []
    for row in stages.STAGES:
        exception = matched(row.name, MADE_OUTSIDE)  # first: people-look-parts-* is no people-look-* page
        if not row.paid or row.name in loop or (exception is None and matched(row.name, MAKES_NO_MODEL)):
            continue
        if exception is None:
            unsaid.append(row.name)
        elif exception.startswith("people-") and row.name not in named:
            unnamed.append(row.name)
    assert not unsaid, f"paid rows outside the loop that say neither what they make nor their exception: {unsaid}"
    assert not unnamed, f"people rows their record's `failures` does not name: {unnamed}"


def test_every_layer_the_hand_in_names_is_an_adapter_s():
    """Every layer a prop data file hands the loop has an adapter.
    Break: score/stages/props/closeup_row.py: `return entry.get("layer", "objects")` -> `return entry.get("layer",
        "objects") + "-x"`"""
    registered = {adapter.layer for adapter in shapes_first.ADAPTERS}
    for path in sorted(prop_data.FOLDER.glob("*.json")):
        layers = {closeup_row.layer_of(entry) for entry in json.loads(path.read_text())["objects"].values()}
        assert layers <= registered, (path.name, layers - registered)
