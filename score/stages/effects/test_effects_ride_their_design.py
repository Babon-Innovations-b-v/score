"""A scene's effects are made from its design, ride their objects at their measured spots, and pass every gate;
a row that emits with no object on the stage fails `designed`, steam written where the design gives none fails
`subject` (effects/__init__.py, from_design.py). Each world is a small kitchen with a drilling rig on Mars (its site
the Campgrounds') made here, a row of WORLDS; no record is written for the scene. How each effect is made is one rule
by what it is made of (effects.json `methods`): a drilling rig's cuttings are grains, a pile Newton makes
(inside/newton_pile.py, in the physics trial's own Python on a card) and drawn as one surface: here its run is stood
in for by a cone surface of the slope given, under the gravity of the body its site is on, its bore and amount the
scene's one model call's answer (stood in for here), and Newton's column is built from the very pile asked.

Breaks that turn it red (each applied once and seen red, then reverted):
- `from_design.spot_on`: `middle + at * half` read as `middle`  -> the sound world's spots (the kettle's spout at its
  box's middle, not its front).
- `from_design.record`: the `missing.append(...)` line left out  -> the faulty world (`designed` passes).
- `from_design.checks_of`: `emitters=[name]` read as `emitters=[]`  -> the sound world (`footage` is no longer
  measured on each emitter, so it does not pass).
- `from_design`: `if not held_on(row, rows, kinds):` -> `if False:`  -> the faulty world (the pot on the chair
  carries steam, it is not named quiet).
- `effects.__init__`: `elif subject.get("on") and under not in subject["on"]:` -> `elif False:`  -> the forged
  record (`subject` misses the pot standing on loose).
- `effects.__init__`: `if kind not in subject.get("kinds", ()):` -> `if False:`  -> the forged record (`subject`
  misses the steam on the bare hob).
- `effects.flank`: the line through the rings' tops fitted over their inner edges with the heights' median (50, not
  FLANK_TOP)  -> the sound world (the 32 degree pile reads under 30).
- `tools/usd/effects.write_clip`: `if emitter.get("drawn") == "surface":` -> `if False:` (the emitter baked as a
  Godot particle)  -> the sound world (the pile is not the one Newton made, `footage` fails).
- `effects.poured`: the body's gravity left out of the emitter  -> the sound world (no Mars pull on the emitter).
- `effects.poured`: the row's asked values left out of the pile (`**entry["asked"]["values"]` dropped)  -> the sound
  world (the pile has no volume).
- `inside/newton_pile.column`: the column as wide as the bore alone (`max(bore, ...)` read as `bore`)  -> the sound
  world (the Campgrounds rig's 0.4 m3 rises 3.3 m/s through its 8 cm bore: a jet that splashed its pile to 19.6
  degrees).
- `effects.files`: the "pile script" line left out  -> the pile script's key (a change to the pile moves no key, so
  the failed row is never made again).
- `asked.read`: a line not answered let through  -> the unanswered world (no ValueError).
- `effects.made`: the `newton-mpm` branch made `particles`  -> the sound world (the pile is baked as particles, no
  surface).
- data/checks/effects.json: a kind's `matter` removed, or a matter's `made_by` removed  -> the sound world (no
  effect is made), or a method's `why` emptied  -> the library's reasons.
"""
import importlib.util
import json
import math
import pathlib
import sys
import types

import numpy as np
import pytest

from score import checks
from score.stages import effects
from score.stages.effects import asked

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACE = "toy"


def box_mesh(stage, path, low, high):
    """A closed box mesh between two corners."""
    from pxr import UsdGeom
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(corners)
    mesh.CreateFaceVertexCountsAttr([4] * len(faces))
    mesh.CreateFaceVertexIndicesAttr([index for face in faces for index in face])


def toy_seed(folder, objects):
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




def world_inputs(folder, inventory, objects):
    """The toy place on Mars (its site the Campgrounds') from its design inventory and its objects."""
    folder = pathlib.Path(folder)
    folder.mkdir()
    (folder / "inventory.json").write_text(json.dumps(inventory))
    (folder / "within.json").write_text(json.dumps({"within": {PLACE: {"within": "campgrounds"}}}))
    (folder / "concept.png").write_bytes(b"a picture")
    return {"design": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
            "effect kinds": REPO / "data/checks/effects.json", "seed": toy_seed(folder / "seeds", objects),
            "physics": REPO / "data/physics/setting.json", "within": folder / "within.json",
            "concept": folder / "concept.png"}


def cone(asked, baked, slope, piles):
    """Stands in for Newton's run: the pile `asked` (its samples a second over its seconds), kept in `piles`, as a
    cone surface of `slope` degrees on the collar, grown to its whole volume as it pours, at rest once poured."""
    pile = json.loads(pathlib.Path(asked).read_text())
    piles.append(pile)
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


def answered(values):
    """Stands in for the scene's one model call: each line asked whose parameter `values` holds answered with it."""
    def asked(bodies, caller):
        wants = json.loads(next(iter(bodies.values()))["contents"][0]["parts"][1]["text"].split("\n", 1)[1])
        return {key: json.dumps({"answers": [dict(want, value=values[want["parameter"]], why="stood in")
                                             for want in wants if want["parameter"] in values]}) for key in bodies}
    return asked


def newton_pile_script(monkeypatch):
    """inside/newton_pile.py loaded here: it runs in Newton's Python, and its column() needs neither warp nor newton."""
    for name in ("warp", "newton", "newton.solvers"):
        monkeypatch.setitem(sys.modules, name, types.SimpleNamespace(SolverImplicitMPM=None))
    loader = importlib.util.spec_from_file_location("newton_pile", REPO / "score/stages/effects/inside/newton_pile.py")
    script = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(script)
    return script


def emitter_spots(seed, out, names):
    """Where each emitter stands in the world, the effects layer over the seed."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(seed / f"{PLACE}.usda"))
    stage.GetRootLayer().subLayerPaths.append(str(out / "layers/effects.usda"))
    return {name: tuple(UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Objects/{name.rsplit('_', 2)[0]}/{name}"))
                        .ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation())
            for name in names}


KITCHEN = (("stove_1", (-0.4, 0.0, -0.3), (0.4, 0.9, 0.3), (2.0, 0.0, 1.0)),
           ("pot_1", (-0.1, 0.0, -0.1), (0.1, 0.15, 0.1), (2.0, 0.9, 1.0)),
           ("hob_1", (-0.3, 0.0, -0.3), (0.3, 0.9, 0.3), (-3.0, 0.0, 1.0)),
           ("kettle_1", (-0.1, 0.0, -0.08), (0.1, 0.25, 0.08), (-1.0, 0.9, 0.0)),
           ("chair_1", (-0.25, 0.0, -0.25), (0.25, 0.9, 0.25), (0.0, 0.0, 2.0)),
           ("drilling_rig_1", (-1.0, 0.0, -1.0), (1.0, 8.0, 1.0), (8.0, 0.0, -6.0)))
HUMIDIFIER = (("humidifier_1", (-0.15, 0.0, -0.15), (0.15, 0.4, 0.15), (4.0, 0.0, -1.0)),)
ROWS = [{"id": "stove", "name": "stove", "noun": "stove"},
        {"id": "pot", "name": "cooking pot", "noun": "pot", "anchor": "on:stove"},
        {"id": "hob", "name": "bare hob", "noun": "hob"},
        {"id": "kettle", "name": "kettle", "noun": "kettle"},
        {"id": "chair", "name": "chair", "noun": "chair"},
        {"id": "wall", "name": "back wall", "noun": "wall"},
        {"id": "humidifier", "name": "humidifier", "noun": "humidifier"},
        {"id": "drilling_rig", "name": "drilling rig", "noun": "drill", "size": [2.0, 2.0, 8.0]}]
SHELVED = [dict(row, anchor="on:chair") if row["id"] == "pot" else row for row in ROWS]
RIG = "drilling_rig_1_drill_cuttings"
# Each world: its objects, its rows, the slope Newton's run (stood in) settles to, the scene's one model call's answers,
# and what the design makes of it: the ValueError it stops on, or the checks that fail (each with its findings), the
# rows named quiet, the emitters and their rows, where the pot's and the kettle's steam stand, the drill's flank slope
# range, and whether its column is let out wider than its bore.
WORLDS = (
    # the pot's steam on the middle of its top: (2.0, 0.9 + 0.15, 1.0); the kettle's spout at the front of its box,
    # six tenths of the way up from its middle: (-1.0, 0.9 + 0.125 + 0.6 * 0.125, 0.0 + 0.08); the Campgrounds rig's
    # asked 0.4 m3 through its 8 cm bore spills off a collar wider than its bore
    {"id": "sound", "objects": KITCHEN + HUMIDIFIER, "rows": ROWS, "slope": 32.0,
     "answers": {"bore": 0.08, "volume": 0.4}, "fails": {}, "quiet": [],
     "emitters": {"pot_1_steam_rise": "pot", "kettle_1_steam_jet": "kettle",
                  "humidifier_1_humidifier_mist": "humidifier", RIG: "drilling_rig"},
     "spots": {"pot_1_steam_rise": (2.0, 1.05, 1.0), "kettle_1_steam_jet": (-1.0, 1.1, 0.08)},
     "flank": (30.0, 33.0), "wide": True},
    # the pot on a chair is quiet, the humidifier has no object on the stage, the pile settles flat under the slip
    # faces measured on Mars, and a bore's own handful stays inside its bore
    {"id": "faulty", "objects": KITCHEN, "rows": SHELVED, "slope": 22.0,
     "answers": {"bore": 0.08, "volume": 0.002},
     "fails": {"designed": ("humidifier emits humidifier_mist, and no object of it stands on the stage",),
               "footage": (f"{RIG}: drill cuttings' flank slope: 21.950 (footage 30.0 to 34.0)",)},
     "quiet": ["pot"], "emitters": {"kettle_1_steam_jet": "kettle", RIG: "drilling_rig"},
     "spots": {"kettle_1_steam_jet": (-1.0, 1.1, 0.08)}, "flank": (0.0, 30.0), "wide": False},
    # a parameter the scene was asked and not answered stops the row
    {"id": "unanswered", "objects": KITCHEN, "rows": ROWS, "slope": 32.0, "answers": {"bore": 0.08},
     "stops": "drilling_rig drill_cuttings volume"},
)


def test_effects_ride_their_design(tmp_path, monkeypatch):
    """Each world's effects are made from its design over its stage and judged by every gate: who carries what, where
    it stands, how it is made and what each gate answers are the world's row; then steam written where the design
    gives none fails `subject`."""
    from pxr import Usd
    script = newton_pile_script(monkeypatch)
    # run apart, the pile script keys the row as a file: a change to it makes the pile again
    assert effects.files(PLACE)["pile script"] == "{repo}/score/stages/effects/inside/newton_pile.py"
    library = json.loads((REPO / "data/checks/effects.json").read_text())
    assert all(method["why"] for name, method in library["methods"].items() if name != "about")
    made, records, kept = {}, {}, {}
    for world in WORLDS:
        piles = []
        monkeypatch.setattr(effects, "newton_pile", lambda asked, baked: cone(asked, baked, world["slope"], piles))
        monkeypatch.setattr(asked.claude_code, "asked", answered(world["answers"]))
        inputs = world_inputs(tmp_path / world["id"], {"rows": world["rows"]}, world["objects"])
        out = tmp_path / world["id"] / "out"
        out.mkdir()
        if "stops" in world:
            with pytest.raises(ValueError, match=world["stops"]):
                effects.make(inputs, out, 0, {})
            continue
        effects.make(inputs, out, 0, {})
        assert effects.layer_faults(out) == [], world["id"]
        found = {check.name: check.judge(out, inputs, None) for check in effects.CHECKS}
        record = json.loads((out / "record.json").read_text())
        records[world["id"]], kept[world["id"]] = record, (out, inputs)
        assert {name for name, verdict in found.items() if verdict.answer != checks.PASS} == set(world["fails"]), (
            world["id"], {name: (verdict.reason, verdict.findings) for name, verdict in found.items()})
        for name, findings in world["fails"].items():
            assert found[name].answer == checks.FAIL, (world["id"], name, found[name].reason)
            assert found[name].findings == findings, (world["id"], found[name].findings)
        assert {entry["name"]: entry["row"] for entry in record["effects"]} == world["emitters"], world["id"]
        assert [line.split(":")[0] for line in record["quiet"]] == world["quiet"], (world["id"], record["quiet"])
        where = emitter_spots(inputs["seed"], out, world["emitters"])
        for name, spot in world["spots"].items():
            assert max(abs(a - b) for a, b in zip(where[name], spot)) < 1e-6, (world["id"], name, where[name])
        # every footage check is measured on its own emitter
        anchors = {check["anchor"] for check in record["footage"]["checks"]}
        assert anchors == set(where), (world["id"], record["footage"]["checks"])
        flank = found["footage"].measures[f"{RIG}: drill cuttings' flank slope"]
        assert world["flank"][0] < flank < world["flank"][1], (world["id"], flank)
        stage = Usd.Stage.Open(str(out / "layers/effects.usda"))
        emitter = stage.GetPrimAtPath(f"/{PLACE}/Objects/drilling_rig_1/{RIG}")
        assert abs(emitter.GetAttribute("score:effect:gravity").Get()[1] + 3.71) < 0.02, world["id"]  # Mars's
        assert stage.GetPrimAtPath(f"{emitter.GetPath()}/{RIG}_surface").GetTypeName() == "Mesh", world["id"]
        drill = next(entry for entry in record["effects"] if entry["name"] == RIG)
        assert drill["asked"]["values"] == world["answers"], (world["id"], drill["asked"])
        made.update({entry["kind"]: entry["made_by"] for entry in record["effects"]})
        # Newton's column of the very pile asked (on a coarser grid): let out no faster than SPILL over the pour, all
        # its volume, and wider than the bore only where the volume needs it
        (pile,) = piles
        spots, spacing = script.column(dict(pile, voxel=0.04))
        across, tall = float(np.hypot(spots[:, 0], spots[:, 1]).max()), float(spots[:, 2].max())
        assert tall / pile["pour"] <= script.SPILL * 1.05, (world["id"], tall)
        assert abs(len(spots) * spacing ** 3 / pile["volume"] - 1.0) < 0.1, (world["id"], len(spots))
        assert (across > 0.1) == world["wide"], (world["id"], across)
    # every effect kind is made by the one rule for its matter
    assert made == {"steam_jet": "particles", "steam_rise": "particles", "humidifier_mist": "particles",
                    "drill_cuttings": "newton-mpm"}, made
    # the sound world's pot steam written into the world where the pot stands on a chair, and onto its bare hob
    out, inputs = kept["faulty"]
    steam = next(entry for entry in records["sound"]["effects"] if entry["row"] == "pot")
    forged = dict(records["faulty"], effects=[*records["faulty"]["effects"], steam,
                                              dict(steam, row="hob", name="hob_1_steam_rise")])
    (out / "record.json").write_text(json.dumps(forged))
    verdict = next(check for check in effects.CHECKS if check.name == "subject").judge(out, inputs, None)
    assert verdict.answer == checks.FAIL and verdict.findings == (
        "pot_1_steam_rise: steam_rise was measured on a pot standing on a cooker, and pot stands on loose",
        "hob_1_steam_rise: steam_rise was measured on a pot, and it rides a cooker (hob)"), verdict.findings
