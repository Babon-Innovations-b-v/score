"""Every model goes through the shared loop (#41): its rows stand in the table in order, every model layer reaches its
models only through the loop's ends and every paid row outside it makes no model but a named exception, an adapter's
after-steps are held to those ends and its layer; the rough model is registered to the plan (scaled, turned and
stood on its floor, worked out by hand from the boxes below), the parts split is read against it, and an after-step
gets the made models or their gaps. No spend, no model made. One test: the registrations, the fits, the made models,
the adapters and the table are its case tables.

Each break below turns the test red (`Break: <file>: `old` -> `new``); each was applied once and seen red.
Break: score/stages/shapes_first/align.py: `floor - scale * least[1],` -> `floor,`
Break: score/stages/shapes_first/align.py: `return min(TURNS, key=misfit)` -> `return 0`
Break: score/stages/shapes_first/align.py:
    `for index, node in enumerate(gltf.get("nodes", [])) for key in NODE_TRANSFORMS if key in node]`
    -> `for index, node in enumerate(gltf.get("nodes", [])) for key in NODE_TRANSFORMS if False]`
Break: score/stages/shapes_first/align.py: `rows = [row for row in split if row.get("layer") not in ROUND]`
    -> `rows = split`
Break: score/stages/shapes_first/floor_fit.py: `wide, deep = wide + ROUNDING, deep + ROUNDING` -> `pass`
Break: score/stages/shapes_first/floor_fit.py:
    `**{f"rows of the plan's {name}": ids for name, ids in off_floor(plan).items()},` -> ``
Break: score/stages/shapes_first/floor_fit.py:
    `return min(x, y) <= ROUNDING or x + across >= wide - ROUNDING or y + along >= deep - ROUNDING` -> `return True`
Break: score/stages/shapes_first/floor_fit.py: `"rows past the plan's edge": past_edge(plan, inventory)}` -> `}`
Break: score/stages/__init__.py: `checks=tuple(fit if check.name == fit.name else check for check in row.checks))`
    -> `checks=row.checks)`
Break: score/stages/shapes_first/made.py: `found.setdefault(entry["parts"], pathlib.Path(bake) / "made" /
    f"{model}.gltf")`
    -> `found.setdefault(model, pathlib.Path(bake) / "made" / f"{model}.gltf")`
Break: score/stages/shapes_first/made.py: `    if "missing" in entry:` -> `    if False:`
Break: score/stages/shapes_first/__init__.py: `if step.grain != "place" or missing:` -> `if step.grain != "place":`
Break: score/stages/shapes_first/__init__.py: `if len(set(layers)) != len(layers):` -> `if False:`
Break: score/stages/shapes_first/__init__.py: `return handed(place, layer) and (applies is None or applies(place))`
    -> `return applies is None or applies(place)`
Break: score/stages/shapes_first/__init__.py:
    `SPLIT = dataclasses.replace(props.INPUTS, after={**props.INPUTS.after, "rough-align": ("rough-align", 1)},`
    -> `SPLIT = dataclasses.replace(props.INPUTS, after={**props.INPUTS.after},`
Break: score/stages/__init__.py: `row.name in ("assembly", "settle")` -> `row.name == "assembly"`
Break: score/stages/__init__.py: `models=(sound.moss_takes.KIND,), after={"motion": ("motion-layer", 2)},`
    -> `models=(sound.moss_takes.KIND,), after={"motion": ("motion-layer", 2), "pixal": ("props-pixal", 1)},`
Break: score/stages/__init__.py: `beside={"scene-tree": ("openusd-stage", 1)}, downward=True,
    neighbours=held_scenes)`
    -> `beside={"scene-tree": ("openusd-stage", 1)}, downward=True, neighbours=held_scenes, paid=True,
    euros=1.0)`
Break: score/stages/props/closeup_row.py: `return entry.get("layer", "objects")` -> `return entry.get("layer",
    "objects") + "-x"`

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
    """No designed place's hand-in is read unless the test writes one (the home's design/, which the sandbox links)."""
    nowhere = tmp_path / "no design"
    monkeypatch.setattr(prop_data, "DESIGN", nowhere)
    monkeypatch.setattr(surface_data, "DESIGN", nowhere)
    monkeypatch.setattr(score.stages.surfaces.data, "DESIGN", nowhere)  # the table's own import of it


REPO = pathlib.Path(__file__).resolve().parents[3]
FLOOR = ((-4.0, -2.0), (4.0, 2.0))  # the plan's 8 by 4 floor
SQUARE = ((-14.93, -14.93), (14.93, 14.93))  # the square's 29.86 m floor
EXACT = ("turn", "misfit")  # measures compared exactly; the rest to float rounding

# The rough models registered to their plan's floor: (box low, box high, floor, the root node's own transform, what
# the registration measures, or the reason it is refused). The upright box is 2 wide, 3 high, 1 deep: the plan's 8 by
# 4 at four times, unturned, spanning -4 to 4 and -2 to 2, its foot on the floor's 0.5 m. The turned box is 1 wide and
# 2 deep: a quarter turn fits, four times, 8 across. A node scaled twice: its extent in the mesh frame is not its size.
REGISTRATIONS = {
    "upright": ((-1.0, -0.2, 0.0), (1.0, 2.8, 1.0), FLOOR, None,
                {"turn": 0, "scale": 4.0, "across": (-4, 4), "deep": (-2, 2), "foot": 0.5, "width": 8,
                 "misfit": {"wide": 1.0, "deep": 1.0, "high": 4.0}}),
    "turned": ((0.0, 0.0, 0.0), (1.0, 1.0, 2.0), FLOOR, None, {"turn": 90, "scale": 4.0, "width": 8}),
    "square": ((-1.0, 0.0, -1.0), (1.0, 3.0, 1.0), SQUARE, None, {"width": 29.86}),
    "scaled node": ((0, 0, 0), (1, 1, 1), FLOOR, {"scale": [2, 2, 2]}, {"refused": "carries its own scale"}),
}

BEAM = {"id": "beam", "size": [9.0, 0.3, 0.3]}
BEAM_FITS_NO_WAY = "beam: 9.0 by 0.3 m fits no way on the 8.00 by 4.00 m floor"
# On the 8 by 4 floor a 9 m beam fits no way, a crate does; a terrain detail area round the floor is counted, not held.
CRATER = [{"id": "crate", "size": [1.0, 3.9, 1.0]}, BEAM,
          {"id": "ground_crater", "size": [30.0, 30.0, 2.0], "layer": "terrain"}]
# The kept plan's structure (its floor) and beyond (the rocket) are counted, never held to the floor; a rug as wide as
# the floor, rounded, fits; with no kept plan all three oversized rows fail.
STRUCTURE = [{"id": "floor", "size": [9.0, 5.0, 0.1]}, {"id": "rocket", "size": [10.0, 10.0, 60.0]}, BEAM,
             {"id": "rug", "size": [8.0005, 4.0, 0.01]}]
KEPT = {"structure": ["floor", "rocket"], "beyond": ["rocket"]}
# Fault 2026-10-26 (props-inputs@square): the square's buildings stand on the ground round its 29.86 m floor, the plan
# laying only their faces at its edges, and failed as floor objects at their read 30 by 30 m. Read without their
# anchors (no inventory) the fault's measures come back; with them the buildings are counted past the edge, and the
# far rocket (also the plan's structure) is counted once. A beam on the ground in the middle and a stall on the plaza
# at the edge stay held.
BUILDINGS = {"left_building": [30.0, 30.0, 24.0], "right_building": [30.0, 30.0, 20.0],
             "foreground_building": [40.0, 20.0, 15.0]}
SQUARE_ROWS = [{"id": name, "size": size} for name, size in BUILDINGS.items()] + [
    {"id": "rocket", "size": [15.8, 4.2, 60.0], "far": {"pieces": 1, "length": 15.8}},
    {"id": "city_skyline", "size": [100.0, 30.0, 100.0], "far": {"pieces": 10, "length": 1000.0}},
    *({"id": f"thing_{number}", "size": [1.0, 1.0, 1.0]} for number in range(9))]
ITEMS = [["LEFT BUILDING 1", 0.0, 15.77, 2.145, 6.609, "E", "item"],
         ["RIGHT BUILDING 1", 26.38, 4.464, 2.609, 17.799, "W", "item"],
         ["FOREGROUND BUILDING 1", 10.784, 23.423, 7.421, 5.566, "N", "item"]]
ITEM_ROWS = {item[0]: [item[0].lower().replace(" 1", "").replace(" ", "_")] for item in ITEMS}
SQUARE_KEPT = {"w": 28.989, "d": 28.989, "items": ITEMS, "beyond": [], "rows": ITEM_ROWS,
               "structure": ["sky", "sea", "city_skyline", "rocket", "planet", "plaza"]}
MIDDLE_KEPT = {"w": 28.989, "d": 28.989, "structure": [],
               "items": ITEMS + [["BEAM 1", 10.0, 10.0, 9.0, 0.3, None, "item"],
                                 ["STALL 1", 0.0, 2.0, 2.0, 2.0, None, "item"]],
               "rows": {**ITEM_ROWS, "BEAM 1": ["beam"], "STALL 1": ["stall"]}}
ANCHORS = [{"id": name, "anchor": "ground"} for name in BUILDINGS]
MIDDLE_ROWS = SQUARE_ROWS + [{"id": "beam", "size": [31.0, 0.3, 0.3]}, {"id": "stall", "size": [31.0, 2.0, 3.0]}]
MIDDLE_ANCHORS = ANCHORS + [{"id": "beam", "anchor": "ground"}, {"id": "stall", "anchor": "on:plaza"}]

# The parts split read against the registration: (judge, registration, split rows, kept plan, inventory anchors,
# expected answer, findings (exact) or the names they start with, measures).
FITS = {
    "a beam past the floor, a crater round it": (align.judge_rows_fit, "upright", CRATER, None, None, checks.FAIL,
                                                 (BEAM_FITS_NO_WAY,),
                                                 {"rows past the rough model": 1, "rows round the floor": 1}),
    "no registration": (align.judge_rows_fit, None, CRATER, None, None, checks.UNKNOWN, None, {}),
    "a line no place owns": (align.judge_rows_fit, None, [{"id": "player-work", "size": None, "layer": "people"}],
                             None, None, checks.PASS, None, {}),
    "the kept plan's structure and beyond": (floor_fit.judge_rows_fit, "upright", STRUCTURE, KEPT, None, checks.FAIL,
                                             (BEAM_FITS_NO_WAY,),
                                             {"rows of the plan's structure": 2, "rows of the plan's beyond": 0}),
    "no kept plan": (floor_fit.judge_rows_fit, "upright", STRUCTURE, None, None, checks.FAIL, None, {"failing": 3}),
    "the square's buildings unanchored": (
        floor_fit.judge_rows_fit, "square", SQUARE_ROWS, SQUARE_KEPT, None, checks.FAIL,
        ("left_building: 30.0 by 30.0 m fits no way on the 29.86 by 29.86 m floor",
         "right_building", "foreground_building"),
        {"failing": 3, "rows of the plan's beyond": 0, "rows of the plan's structure": 2,
         "rows past the rough model": 3, "rows round the floor": 0}),
    "the square's buildings anchored": (floor_fit.judge_rows_fit, "square", SQUARE_ROWS, SQUARE_KEPT, ANCHORS,
                                        checks.PASS, None,
                                        {"rows past the plan's edge": 3, "rows of the plan's structure": 2,
                                         "rows laid far off": 0}),
    "a beam in the middle, a stall on the plaza": (floor_fit.judge_rows_fit, "square", MIDDLE_ROWS, MIDDLE_KEPT,
                                                   MIDDLE_ANCHORS, checks.FAIL, ("beam", "stall"),
                                                   {"rows laid far off": 2}),  # no longer the plan's structure
}

# Which row reads which in the table: the loop in its order (the likeness reads the bake), and the assembly and the
# settle read the terrain's ground-join (2026-10-30: the settle dropped camp's joined rocks the assembly no longer lays).
READS_BEFORE = {"rough-align": "rough-model", "props-inputs": "rough-align", "closeup": "props-inputs",
                "pixal": "closeup", "finish-route-views": "pixal", "likeness": "surfaces-bake",
                "assembly": "ground-join", "settle": "ground-join"}
# Where an after-step of each layer applies: the campgrounds hand in only objects (the cairn), the hub hands in none.
APPLIES = [("terrain", "campgrounds", False), ("objects", "campgrounds", True), ("objects", "hub", False)]


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


def aligned(folder, low, high, floor, node):
    """The rough-align output of a box model onto a plan's floor."""
    rough, plan, out = folder / "rough", folder / "plan", folder / "out"
    for each in (rough, plan, out):
        each.mkdir(parents=True)
    glb(rough / "rough.glb", low, high, node)
    (rough / "rough.json").write_text(json.dumps({"take": "here-rough-0"}))
    (plan / "plan.json").write_text(json.dumps({"place": "here", "floor": [list(corner) for corner in floor],
                                                "floor_height": 0.5, "walls": {"high": 3.0}}))
    align.make({"rough-model": rough, "plan": plan}, out, 0, {})
    return out


def corners_placed(record, low, high):
    """The model box's corners through the registration's matrix."""
    matrix = record["matrix"]
    return [[sum(matrix[row][column] * point[column] for column in range(3)) + matrix[row][3] for row in range(3)]
            for point in [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]]


def measured(record, low, high):
    """What a registration did to the box: its turn, scale and misfit, and where its corners land on the floor."""
    placed = corners_placed(record, low, high)
    across, deep = [point[0] for point in placed], [point[2] for point in placed]
    return {"turn": record["turn_degrees"], "scale": record["scale"], "misfit": record["misfit"],
            "across": (min(across), max(across)), "deep": (min(deep), max(deep)), "width": max(across) - min(across),
            "foot": min(point[1] for point in placed)}


def judged(folder, case, registered):
    """A fit case's verdict: its split rows, kept plan and anchors written, judged against its registration."""
    judge, registration, rows, kept, anchors = case[:5]
    folder.mkdir()
    (folder / "rows.json").write_text(json.dumps({"rows": rows}))
    inputs = {"rough-align": registered[registration]} if registration else {}
    if kept is not None:
        (folder / "kept.json").write_text(json.dumps(kept))
        inputs[floor_fit.KEPT_PLAN] = folder / "kept.json"
    if anchors is not None:
        (folder / "inventory.json").write_text(json.dumps({"rows": anchors}))
        inputs["inventory"] = folder / "inventory.json"
    return judge(folder, inputs, {})


def row(name, after):
    return graph.Stage(name, "place", lambda *arguments: None, contracts.Contract(name, 1, lambda folder: []),
                       after=after)


def matched(name, patterns):
    return next((pattern for pattern in patterns if fnmatch.fnmatch(name, pattern)), None)


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
    "cast": "its people measured on the stage with the bakes laid as for motion (a seat carries a seated person), "
            "lays no model",
    "sim-body": "its cast's sim bodies on the scene's ground with the bakes laid as the cast's, lays no model",
    "light-layer": "the place's lights measured on it as the assembly lays it (light/passes.py LAID), lays no model",
    "light-passes": "renders of the place as the assembly lays it (light/passes.py LAID), lays no model",
    "light": "the place's light judged on it as the assembly lays it (light/passes.py LAID), lays no model",
    "screens": "each screen row's picture over its bake and its finishes (#88), lays no model",
    "finish-route-picks": "the recheck's picks for the loop's parts row, made from it in the table and read by it "
                          "alone (stages.picks_applied, #118), lays no model",
}
# Every paid row outside the loop and what it makes: none a model, but the named exceptions MADE_OUTSIDE holds.
MAKES_NO_MODEL = {
    "settle": "rest poses of the made models", "sound": "sounds", "demo-film*": "films",
    "physics-trial": "a physics trial",
    "light-passes": "renders", "surface-tiles": "surface tile pictures",
    "crops-concept": "a concept picture", "crops-boxes": "measured boxes", "crops-look": "renders",
    "straight-masks": "SAM 3 masks of the thin straight rows, read by prepare's prediction alone",
    "body-face-*": "a body's face palette and recipe variant", "people-clips-made": "Kimodo clips and the mean rig",
    "scene-clips": "Kimodo clips of each walker walked along its own route on the scene's ground",
    "people-look-*": "renders of a made body (its review page)",
    "people-dress-*": "the loop's library surfaces baked onto a made body's own model, every variant (c3a5a275)",
    "sim-body": "a cast's musculoskeletal bodies' physics: forces, moments, activations (#65)",
    "body-peel": "a film's layer peel, rendered", "place-peel": "a film's place peel, rendered",
}
# Paid rows that make a model outside the loop: each a named exception its own record names.
MADE_OUTSIDE = {
    "people-look-parts-*": "data/props/people.json `failures`: the garments' second split",
    "people-body-*": "data/props/people.json `failures`: the body built from the raw take",
}


def test_every_model_goes_through_the_loop(tmp_path, monkeypatch):
    """Every rough model is registered to its plan or refused by name, every parts split is read against that
    registration, an after-step gets the made models or their gaps and is held to the loop's ends and its layer, and
    the table runs the loop in its order with every row outside it reaching models only through its ends."""
    registered = {}
    for name, (low, high, floor, node, expected) in REGISTRATIONS.items():
        out = aligned(tmp_path / "registered" / name, low, high, floor, node)
        verdict = align.CHECKS[0].judge(out, {}, {})
        if "refused" in expected:
            assert not (out / "aligned.glb").exists(), name
            assert verdict.answer == checks.FAIL and expected["refused"] in verdict.findings[0], (name, verdict)
            continue
        assert verdict.answer == checks.PASS, (name, verdict)
        record = json.loads((out / "align.json").read_text())
        found = measured(record, low, high)
        for key, value in expected.items():
            assert found[key] == (value if key in EXACT else pytest.approx(value)), (name, key, found[key])
        gltf = align.glb_json(out / "aligned.glb")
        root = gltf["nodes"][gltf["scenes"][0]["nodes"][0]]
        assert root["children"] == [0] and root["matrix"][12:15] == [line[3] for line in record["matrix"][:3]], name
        registered[name] = out

    (tmp_path / "fits").mkdir()
    for number, (name, case) in enumerate(FITS.items()):
        answer, findings, measures = case[5:]
        verdict = judged(tmp_path / "fits" / str(number), case, registered)
        assert verdict.answer == answer, (name, verdict)
        if findings is not None:
            assert len(verdict.findings) == len(findings) and all(
                text == want or text.split(":")[0] == want for text, want in zip(verdict.findings, findings)), (
                name, verdict.findings)
        assert {key: verdict.measures[key] for key in measures} == measures, (name, verdict.measures)

    split, likeness, bake, parts = (tmp_path / name for name in ("split", "likeness", "bake", "parts"))
    for folder in (split, likeness, bake, parts):
        folder.mkdir()
    # The seat's take baked as seat_1 hands its baked model and its parts' finishes; the lamp's missing close-up is its
    # gap; the code rock its own model; a layer whose rows never reached the likeness is a gap each.
    (split / "rows.json").write_text(json.dumps({"rows": [
        {"id": "seat", "take": "seat-s1", "layer": "objects"}, {"id": "lamp", "take": "lamp-s1", "layer": "objects"},
        {"id": "rock", "take": None, "layer": "objects"}, {"id": "path", "take": "path-t1", "layer": "terrain"}]}))
    (likeness / "likeness.json").write_text(json.dumps({"objects": {
        "seat": {"route": "prop", "model": "elsewhere.gltf"},
        "lamp": {"route": "prop", "model": None, "missing": "no close-up"},
        "rock": {"route": "code", "model": "/data/rock.gltf"}}}))
    (bake / "baked.json").write_text(json.dumps({"seat_1": {"parts": "seat-s1"}}))
    (parts / "parts.json").write_text(json.dumps({"takes": {"seat-s1": {"parts": [{"surface": "steel"}]}}}))
    inputs = {"props-inputs": split, "likeness": likeness, "surfaces-bake": bake, "surfaces-parts": parts}
    for layer, expected in {
            "objects": {"seat": {"route": "prop", "model": str(bake / "made/seat_1.gltf"), "take": "seat-s1",
                                 "finishes": [{"surface": "steel"}], "failures": {}},
                        "lamp": {"gap": "no close-up"}, "rock": {"route": "code", "model": "/data/rock.gltf",
                                                                 "finishes": []}},
            "terrain": {"path": {"gap": "no likeness record: the loop never reached its model"}}}.items():
        assert made.made(inputs, layer) == expected, layer

    # An after-step lacking the loop's ends is refused, and so are two adapters on one layer.
    for adapters, refusal in (
            ((shapes_first.OBJECTS, shapes_first.Adapter("terrain", (row("join", {"terrain": ("g", 1)}),))), "lacks"),
            ((shapes_first.OBJECTS, shapes_first.Adapter("objects")), "share a layer")):
        with pytest.raises(ValueError, match=refusal):
            shapes_first.rows(adapters)
    table = {stage.name: stage for stage in stages.STAGES}
    names = [stage.name for stage in stages.STAGES]
    assert names.count("rough-model") == 1 and names.count("ground-join") == 1
    for later, earlier in READS_BEFORE.items():
        assert earlier in table[later].after, (earlier, later)
    # ground-join is the terrain layer's one after-step, reads the loop's ends, and runs nowhere a place handed no
    # terrain rows (the wreck, until its rough model is registered).
    assert [step.name for step in shapes_first.TERRAIN.after] == ["ground-join"]
    assert made.ENDS.keys() <= table["ground-join"].after.keys() and not table["ground-join"].applies("wreck")
    # Fault 2026-10-24 (eight places' shells failed the floor): the table's parts split gates on floor_fit's judge,
    # which reads the kept plan, not align's.
    fit = next(check for check in table["props-inputs"].checks if check.name == "fits the plan")
    assert fit.judge.__wrapped__ is floor_fit.judge_rows_fit

    # #41: a row outside the loop reading a loop row is an after-step reading its ends, or named with its reason; a
    # paid row outside it says what it makes (no model) or is a named exception its record names.
    loop = {stage.name for stage in shapes_first.rows(())}
    after_steps = {step.name for adapter in shapes_first.ADAPTERS for step in adapter.after}
    records = json.loads((prop_data.FOLDER / "people.json").read_text())["objects"].values()
    named = {line for entry in records for text in (entry.get("failures") or {}).values()
             for line in re.findall(r"people-[a-z0-9_-]*[a-z0-9]", text)}
    around, reading, unsaid, unnamed = [], set(), [], []
    for stage in stages.STAGES:
        if stage.name in loop:
            continue
        if loop & stage.after.keys():
            reading.add(stage.name)
            through = stage.name in after_steps and made.ENDS.keys() <= stage.after.keys()
            if not through and stage.name not in READS_THE_LOOP:
                around.append(f"{stage.name} reads {sorted(loop & stage.after.keys())}")
        exception = matched(stage.name, MADE_OUTSIDE)
        if not stage.paid or (exception is None and matched(stage.name, MAKES_NO_MODEL)):
            continue
        if exception is None:
            unsaid.append(stage.name)
        elif exception.startswith("people-") and stage.name not in named:
            unnamed.append(stage.name)
    assert not around, f"rows reaching the loop's models around its ends (made.ENDS): {around}"
    assert READS_THE_LOOP.keys() <= reading, f"no longer read the loop: {sorted(READS_THE_LOOP.keys() - reading)}"
    assert not unsaid, f"paid rows outside the loop that say neither what they make nor their exception: {unsaid}"
    assert not unnamed, f"people rows their record's `failures` does not name: {unnamed}"

    # Every layer a prop data file hands the loop has an adapter, and an after-step applies only where the place
    # handed rows of its layer (the campgrounds' cairn is on the objects layer, the hub hands none).
    layers = {adapter.layer for adapter in shapes_first.ADAPTERS}
    for path in sorted(prop_data.FOLDER.glob("*.json")):
        handed = {closeup_row.layer_of(entry) for entry in json.loads(path.read_text())["objects"].values()}
        assert handed <= layers, (path.name, handed - layers)
    monkeypatch.setattr(prop_data, "DESIGN", tmp_path / "design")  # a hand-in of the test's own
    prop_data.DESIGN.mkdir()
    (prop_data.DESIGN / "campgrounds.json").write_text(json.dumps({"objects": {"cairn": {"route": "prop",
                                                                                         "take": "cairn-p1"}}}))
    for layer, place, applies in APPLIES:
        step = shapes_first.rows((shapes_first.Adapter(layer, (row(f"{layer}-step", dict(made.ENDS)),)),))[-1]
        assert step.name == f"{layer}-step" and step.applies(place) == applies, (layer, place)
