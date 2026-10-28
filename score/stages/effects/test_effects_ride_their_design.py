"""A scene's effects are made from its design, ride their objects at their measured spots, and pass every gate;
a row that emits with no object on the stage fails `designed` (effects/__init__.py, from_design.py). The stage is a
small kitchen made here; no record is written for the scene. How each effect is made is one rule by what it is made
of (effects.json `methods`): a drilling rig's cuttings are grains, a pile Newton makes (inside/newton_pile.py, in the
physics trial's own Python on a card) and drawn as one surface: here its run is stood in for by a cone surface of the
slope given, under the gravity of the body its site is on, its bore and amount the scene's one model call's answer
(stood in for here).

Breaks that turn it red (each applied once and seen red, then reverted):
- `from_design.spot_on`: `middle + at * half` read as `middle`  -> the first test (the kettle's spout at its box's
  middle, not its front).
- `from_design.record`: the `missing.append(...)` line left out  -> the second test (`designed` passes).
- `from_design.checks_of`: `emitters=[name]` read as `emitters=[]`  -> the first test (`footage` is no longer measured
  on each emitter, so it does not pass).
- `effects.flank`: the line through the rings' tops fitted over their inner edges with the heights' median (50, not
  FLANK_TOP)  -> the third test (the 32 degree pile reads under 30).
- `tools/usd/effects.write_clip`: `baked(emitter)` not read (the emitter baked as a Godot particle)  -> the third
  test (the pile is not the one Newton made, `footage` fails).
- `effects.poured`: the body's gravity left out of the emitter  -> the third test (no Mars pull on the emitter).
- `effects.poured`: the row's asked values left out of the pile (`**entry["asked"]["values"]` dropped)  -> the third
  test (the pile has no volume).
- `inside/newton_pile.column`: the column as wide as the bore alone (`max(bore, ...)` read as `bore`)  -> the fourth
  test (the Campgrounds rig's 0.4 m3 rises 3.3 m/s through its 8 cm bore: a jet that splashed its pile to 19.6
  degrees).
- `effects.files`: the "pile script" line left out  -> the fourth test (a change to the pile moves no key, so the
  failed row is never made again).
- `asked.read`: a line not answered let through  -> the fifth test (no ValueError).
- `effects.made`: the `newton-mpm` branch made `particles`  -> the third test (the pile is baked as particles, no
  surface).
- data/checks/effects.json: a kind's `matter` removed, or a matter's `made_by` removed  -> the sixth test.
"""
import importlib.util
import json
import math
import pathlib
import sys
import types

import numpy as np

from score import checks
from score.stages import effects
from score.stages.effects import asked

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACE = "toy"
# The toy kitchen's objects: (name, low corner, high corner of the model's own box, where it stands).
OBJECTS = (("stove_1", (-0.4, 0.0, -0.3), (0.4, 0.9, 0.3), (2.0, 0.0, 1.0)),
           ("kettle_1", (-0.1, 0.0, -0.08), (0.1, 0.25, 0.08), (-1.0, 0.9, 0.0)),
           ("chair_1", (-0.25, 0.0, -0.25), (0.25, 0.9, 0.25), (0.0, 0.0, 2.0)))
INVENTORY = {"rows": [{"id": "stove", "name": "stove", "noun": "stove"},
                      {"id": "kettle", "name": "kettle", "noun": "kettle"},
                      {"id": "chair", "name": "chair", "noun": "chair"},
                      {"id": "wall", "name": "back wall", "noun": "wall"}]}


def box_mesh(stage, path, low, high):
    """A closed box mesh between two corners."""
    from pxr import UsdGeom
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(corners)
    mesh.CreateFaceVertexCountsAttr([4] * len(faces))
    mesh.CreateFaceVertexIndicesAttr([index for face in faces for index in face])


def toy_seed(folder, objects=OBJECTS):
    """A stage folder <folder>/toy/toy.usda: the place's objects, each a box under Objects."""
    from pxr import Gf, Usd, UsdGeom
    seed = pathlib.Path(folder) / PLACE
    seed.mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(seed / f"{PLACE}.usda"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{PLACE}").GetPrim())
    UsdGeom.Scope.Define(stage, f"/{PLACE}/Objects")
    for name, low, high, at in objects:
        holder = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
        holder.AddTranslateOp().Set(Gf.Vec3d(*at))
        box_mesh(stage, f"/{PLACE}/Objects/{name}/body", low, high)
    stage.GetRootLayer().Save()
    return seed


def toy_inputs(folder, inventory=INVENTORY, objects=OBJECTS):
    folder = pathlib.Path(folder)
    (folder / "inventory.json").write_text(json.dumps(inventory))
    return {"design": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
            "effect kinds": REPO / "data/checks/effects.json", "seed": toy_seed(folder / "seeds", objects)}


def cone(asked, baked, slope):
    """Stands in for Newton's run: the pile `asked` (its samples a second over its seconds) as a cone surface of
    `slope` degrees on the collar, grown to its whole volume as it pours, at rest once poured."""
    pile = json.loads(pathlib.Path(asked).read_text())
    samples = int(round(float(pile["seconds"]) * float(pile["samples"]))) + 1
    tall = (3.0 * float(pile["volume"]) * math.tan(math.radians(slope)) ** 2 / math.pi) ** (1.0 / 3.0)
    rings, around = np.linspace(0.0, 1.0, 201), np.linspace(0.0, 2 * math.pi, 64, endpoint=False)
    out_by = np.repeat(rings, len(around)) * tall / math.tan(math.radians(slope))
    turn = np.tile(around, len(rings))
    shape = np.stack([out_by * np.cos(turn), tall * (1.0 - np.repeat(rings, len(around))), out_by * np.sin(turn)], 1)
    ring, step = np.meshgrid(np.arange(len(rings) - 1), np.arange(len(around)), indexing="ij")
    first, beside = ring * len(around) + step, ring * len(around) + (step + 1) % len(around)
    faces = np.stack([first, beside, first + len(around), beside, beside + len(around), first + len(around)], -1)
    vertices, indices = [], []
    for sample in range(samples):
        poured = min(sample / float(pile["samples"]) / float(pile["pour"]), 1.0)
        vertices.append(shape * poured ** (1.0 / 3.0) if poured else np.zeros((0, 3)))
        indices.append(faces.ravel() if poured else np.zeros(0, int))
    np.savez(baked, vertices=np.concatenate(vertices).astype(np.float32),
             vertex_starts=np.cumsum([0] + [len(part) for part in vertices]),
             indices=np.concatenate(indices).astype(np.int32),
             index_starts=np.cumsum([0] + [len(part) for part in indices]), grains=123)


def answered(volume):
    """Stands in for the scene's one model call: every line asked answered (the bore 0.1 m, the volume given)."""
    def asked(bodies, caller):
        wants = json.loads(next(iter(bodies.values()))["contents"][0]["parts"][1]["text"].split("\n", 1)[1])
        return {key: json.dumps({"answers": [dict(want, value=volume if want["parameter"] == "volume" else 0.1,
                                                  why="stood in") for want in wants]}) for key in bodies}
    return asked


def drill_inputs(folder, monkeypatch, slope):
    """The toy place with a drilling rig on Mars (its site the Campgrounds'), Newton's run a cone of `slope`."""
    pathlib.Path(folder).mkdir()
    rig = (("drilling_rig_1", (-1.0, 0.0, -1.0), (1.0, 8.0, 1.0), (0.0, 0.0, 0.0)),)
    inventory = {"rows": [{"id": "drilling_rig", "name": "drilling rig", "noun": "drill", "size": [2.0, 2.0, 8.0]}]}
    inputs = toy_inputs(folder, inventory, rig)
    (pathlib.Path(folder) / "within.json").write_text(json.dumps({"within": {PLACE: {"within": "campgrounds"}}}))
    (pathlib.Path(folder) / "concept.png").write_bytes(b"a picture")
    monkeypatch.setattr(effects, "newton_pile", lambda asked, baked: cone(asked, baked, slope))
    monkeypatch.setattr(asked.claude_code, "asked", answered(0.12))
    return dict(inputs, physics=REPO / "data/physics/setting.json", within=pathlib.Path(folder) / "within.json",
                concept=pathlib.Path(folder) / "concept.png")


def answers(inputs, folder):
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    effects.make(inputs, out, 0, {})
    assert effects.layer_faults(out) == []
    return out, {check.name: check.judge(out, inputs, None) for check in effects.CHECKS}


def test_the_stove_and_the_kettle_carry_their_steam_at_their_spots_and_pass(tmp_path):
    from pxr import Usd, UsdGeom
    out, found = answers(toy_inputs(tmp_path), tmp_path)
    record = json.loads((out / "record.json").read_text())
    stage = Usd.Stage.Open(str(tmp_path / "seeds" / PLACE / f"{PLACE}.usda"))
    stage.GetRootLayer().subLayerPaths.append(str(out / "layers/effects.usda"))
    where = {name: UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Objects/{name.split('_')[0]}_1/{name}"))
             .ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
             for name in ("stove_1_steam_rise", "kettle_1_steam_jet")}
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items()}
    assert {entry["name"]: entry["row"] for entry in record["effects"]} == {"stove_1_steam_rise": "stove",
                                                                            "kettle_1_steam_jet": "kettle"}
    # the stove's steam on the middle of its top: (2.0, 0.0 + 0.9, 1.0); the kettle's spout at the front of its box,
    # six tenths of the way up from its middle: (-1.0, 0.9 + 0.125 + 0.6 * 0.125, 0.0 + 0.08)
    assert max(abs(a - b) for a, b in zip(where["stove_1_steam_rise"], (2.0, 0.9, 1.0))) < 1e-6, where
    assert max(abs(a - b) for a, b in zip(where["kettle_1_steam_jet"], (-1.0, 1.1, 0.08))) < 1e-6, where
    # every footage check is measured on its own emitter
    assert {check["anchor"] for check in record["footage"]["checks"]} == set(where), record["footage"]["checks"]


def test_a_row_that_emits_with_no_object_on_the_stage_fails_designed(tmp_path):
    rows = INVENTORY["rows"] + [{"id": "humidifier", "name": "humidifier", "noun": "humidifier"}]
    _, found = answers(toy_inputs(tmp_path, inventory={"rows": rows}), tmp_path)
    assert found["designed"].answer == checks.FAIL, found["designed"].reason
    assert found["designed"].findings == ("humidifier emits humidifier_mist, and no object of it stands on the stage",)



def test_a_drilling_rig_lays_its_newton_pile_on_mars_and_is_held_to_the_slip_faces_measured_there(tmp_path,
                                                                                                    monkeypatch):
    from pxr import Usd
    out, found = answers(drill_inputs(tmp_path / "steep", monkeypatch, 32.0), tmp_path / "steep")
    assert all(verdict.answer == checks.PASS for verdict in found.values()), {
        name: (verdict.reason, verdict.findings) for name, verdict in found.items()}
    assert 30.0 < found["footage"].measures["drilling_rig_1_drill_cuttings: drill cuttings' flank slope"] < 33.0
    stage = Usd.Stage.Open(str(out / "layers/effects.usda"))
    emitter = stage.GetPrimAtPath(f"/{PLACE}/Objects/drilling_rig_1/drilling_rig_1_drill_cuttings")
    assert abs(emitter.GetAttribute("score:effect:gravity").Get()[1] + 3.71) < 0.02  # Mars's, its site's body
    assert stage.GetPrimAtPath(f"{emitter.GetPath()}/drilling_rig_1_drill_cuttings_surface").GetTypeName() == "Mesh"
    entry = json.loads((out / "record.json").read_text())["effects"][0]
    assert (entry["made_by"], entry["asked"]["values"]) == ("newton-mpm", {"bore": 0.1, "volume": 0.12}), entry
    _, flat = answers(drill_inputs(tmp_path / "flat", monkeypatch, 22.0), tmp_path / "flat")
    assert flat["footage"].answer == checks.FAIL, flat["footage"].reason


def test_a_large_pile_of_cuttings_spills_off_its_collar_and_never_jets(monkeypatch):
    for name in ("warp", "newton", "newton.solvers"):  # the script runs in Newton's Python; column() needs neither
        monkeypatch.setitem(sys.modules, name, types.SimpleNamespace(SolverImplicitMPM=None))
    script = REPO / "score/stages/effects/inside/newton_pile.py"
    loader = importlib.util.spec_from_file_location("newton_pile", script)
    newton_pile = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(newton_pile)
    # run apart, it keys the row as a file: a change to it makes the pile again
    assert effects.files(PLACE)["pile script"] == "{repo}/" + str(script.relative_to(REPO))
    for volume, wide in ((0.4, True), (0.002, False)):  # the Campgrounds rig's asked 0.4 m3; a bore's own handful
        pile = {"voxel": 0.04, "bore": 0.08, "volume": volume, "pour": 6.0, "seed": 7}
        spots, spacing = newton_pile.column(pile)
        across, tall = float(np.hypot(spots[:, 0], spots[:, 1]).max()), float(spots[:, 2].max())
        assert tall / pile["pour"] <= newton_pile.SPILL * 1.05, (volume, tall)  # its slices fall at tall / pour
        assert abs(len(spots) * spacing ** 3 / volume - 1.0) < 0.1, (volume, len(spots))
        assert (across > 0.1) == wide, (volume, across)


def test_a_parameter_the_scene_was_asked_and_not_answered_stops_the_row():
    wants = asked.wanted([({"id": "drilling_rig", "name": "drilling rig", "size": [2.0, 2.0, 8.0]}, "drill_cuttings")],
                         json.loads((REPO / "data/checks/effects.json").read_text()))
    assert {want["parameter"] for want in wants} == {"bore", "volume"}
    answer = json.dumps({"answers": [dict(wants[0], value=0.1, why="read off the picture")]})
    try:
        asked.read(answer, wants)
    except ValueError as error:
        assert "volume" in str(error) or "bore" in str(error), error
    else:
        raise AssertionError("an unanswered parameter was let through")


def test_every_effect_kind_is_made_by_the_one_rule_for_its_matter():
    library = json.loads((REPO / "data/checks/effects.json").read_text())
    made = {name: library["methods"][kind["matter"]]["made_by"] for name, kind in library["kinds"].items()}
    assert made == {"steam_jet": "particles", "steam_rise": "particles", "humidifier_mist": "particles",
                    "drill_cuttings": "newton-mpm"}, made
    assert all(method["why"] for name, method in library["methods"].items() if name != "about")
