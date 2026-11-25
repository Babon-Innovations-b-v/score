"""A made model's moving parts run in Newton (#177, PRD #159): each part the parts step cut (place_build/maker/parts.py,
its node `<part>__<joint>_<axis>[n]` at its pivot) laid in a place of its own, joined by the physics layer
(tools/usd/physics.write_parted: a revolute joint for a hinge or a spin, a prismatic for a slide, its limits, its kg),
driven toward its far limit for the trial's seconds (its force by its kg), and stepped by the physics trial (score/stages/physics/inside/
physics_trial.py: Newton with MuJoCo's solver, in its own Python). Measured per part: how much of its range it
travelled and how far past its limit it went; a spin how far it turned.

    staged(model, record, folder)       the one-object place: the parted GLB laid as `model` over nothing, its stage
    trial_record(record)                the physics layer's record: no drop, each part driven (DRIVE_SECONDS)
    measured(out, record)               {node: {joint, range, travelled, reached, past, passes}} of the trial's out.json
    trialled(model, record, folder, env=LOCAL_ENV, lock=None)   all three, the trial run (holding `lock`, the card's)

    python -m tools.props.bench.joints <parted.glb> <parts.json> <folder>      prints one line; joints.json in folder

The object is the joints' still frame (a hinge's frame is static, write_parted), so only the parts move. A part
passes when it travels at least REACHED of its range and never more than PAST_SLACK or PAST_SHARE of its range
(the larger) past its limit; a spin when it turns at least SPIN_DEGREES and at most SPIN_FASTEST times its drive's
sweep.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tools/usd"))
import physics  # noqa: E402
from drop import LOCAL_ENV, TRIAL  # noqa: E402

PLACE = "bench_joints"
SECONDS = 4.0
DRIVE_SECONDS = (0.2, 3.5)  # the drive's start and end: it opens its part in about two seconds, then holds
REACHED = 0.9  # of its range a hinge or slide travels
# How far past its limit a part may go: the larger of an absolute slack (degrees, metres) and a share of its range, so
# a drill's 8 mm lever is held to 0.8 mm, not to a door's slack (r16: it went 3.6 mm past and passed at 1 cm).
PAST_SLACK = {"hinge": 2.0, "slide": 0.0005}
PAST_SHARE = 0.1
SPIN_DEGREES = 90.0
SPIN_FASTEST = 2.0  # times its drive's own sweep a spin may turn: past it the solve ran away (r16: a dial 48,574 degrees)
TORQUE_PER_KG = 20.0  # N m (a hinge or spin) or N (a slide) a kg of its part, at least LEAST_TORQUE
LEAST_TORQUE = 0.05  # (r16: a 5 N m floor on a 44 g dial ran its solve away)
MATERIALS = json.loads((REPO / "data/physics/materials.json").read_text())


def staged(model, record, folder):
    """The one-object place in `folder`: `model` (the parted GLB) copied in, converted (place_build/gltf.py keeps
    each part node its own Xform) and laid as /PLACE/Objects/model; the folder."""
    from pxr import Sdf, Usd, UsdGeom
    from score.stages.place_build import gltf
    folder = pathlib.Path(folder)
    (folder / "layers").mkdir(parents=True, exist_ok=True)
    laid = shutil.copyfile(model, folder / "model.glb")
    usd = gltf.converted(laid)
    Sdf.Layer.CreateNew(str(folder / "layers/edit.usda")).Save()
    stage = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{PLACE}").GetPrim())
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    holder = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/model")
    holder.GetPrim().GetReferences().AddReference(str(pathlib.Path(os.path.relpath(usd, folder / "layers"))))
    stage.Save()
    root = Sdf.Layer.CreateNew(str(folder / f"{PLACE}.usda"))
    root.subLayerPaths[:] = ["./layers/edit.usda", "./layers/base.usda"]
    root.defaultPrim, root.timeCodesPerSecond = PLACE, 24
    root.pseudoRoot.SetInfo("upAxis", "Y")
    root.pseudoRoot.SetInfo("metersPerUnit", 1.0)
    root.Save()
    return folder


def driven(part):
    """A part's drive toward its far limit (a spin: round), its speed covering its range in about two seconds."""
    span = (180.0 if part["joint"] == "spin" else float(part["limits"][1]))
    return {"speed": span / 2.0, "torque": max(LEAST_TORQUE, TORQUE_PER_KG * float(part["kg"])),
            "start": DRIVE_SECONDS[0], "end": DRIVE_SECONDS[1]}


def trial_record(record):
    """The physics layer's record for the staged place: earth's pull, no drop, the model's parts each driven."""
    parts = [{**{key: part[key] for key in ("node", "joint", "axis", "sign", "limits", "kg")},
              "drive": driven(part)} for part in record["parts"]]
    return {"place": PLACE, "body": "earth", "gravity": 9.81, "material": "steel", "seconds": SECONDS, "drops": [],
            "hinges": [], "slides": [], "pushes": [], "moved": [], "parted": [{"object": "model", "parts": parts}]}


def measured(out, record):
    """{node: {joint, range, travelled, reached, past, passes}} of the trial's out.json (`out`, parsed): a hinge's
    angles and a slide's metres read as the way its drive opens it (its sign), a spin's turn in degrees."""
    found = {}
    tracks = {**{name: ("hinge", entry["angles"]) for name, entry in out.get("hinges", {}).items()},
              **{name: ("slide", entry["metres"]) for name, entry in out.get("slides", {}).items()}}
    for part in record["parts"]:
        name = next((name for name in tracks if name.endswith(part["node"])), None)
        if name is None:
            found[part["node"]] = {"joint": part["joint"], "passes": False, "why": "the trial measured no such joint"}
            continue
        _, track = tracks[name]
        way = [value * (1 if part["sign"] > 0 else -1) for value in track]
        travelled = max(way)
        if part["joint"] == "spin":
            sweep = driven(part)["speed"] * (DRIVE_SECONDS[1] - DRIVE_SECONDS[0])
            found[part["node"]] = {"joint": "spin", "travelled": round(travelled, 3), "sweep": round(sweep, 3),
                                   "passes": SPIN_DEGREES <= travelled <= SPIN_FASTEST * sweep}
            continue
        span = float(part["limits"][1])
        past, slack = travelled - span, max(PAST_SLACK[part["joint"]], PAST_SHARE * span)
        found[part["node"]] = {"joint": part["joint"], "range": span, "travelled": round(travelled, 4),
                               "reached": round(travelled / span, 3) if span else None, "past": round(past, 4),
                               "slack": round(slack, 4), "passes": travelled >= REACHED * span and past <= slack}
    return found


def ran(stage, out, env, lock):
    """The physics trial on `stage` in `env`'s Python, holding `lock` (a file) while it runs when given."""
    command = [str(pathlib.Path(env) / "bin/python"), str(TRIAL), str(stage), str(out)]
    done = subprocess.run((["flock", str(lock)] if lock else []) + command, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"the physics trial failed: {done.stderr[-1500:]}")
    return json.loads(pathlib.Path(out).read_text())


def trialled(model, record, folder, env=LOCAL_ENV, lock=None):
    """The model's parts staged, joined, driven and run: measured(...), written as joints.json in `folder` too."""
    folder = staged(model, record, folder)
    written = physics.write(folder, trial_record(record), MATERIALS)
    if written.get("faults"):
        raise ValueError(f"the physics layer refused the parts: {written['faults']}")
    found = measured(ran(folder / f"{PLACE}.usda", folder / "out.json", env, lock), record)
    (folder / "joints.json").write_text(json.dumps(found, indent=1))
    return found


if __name__ == "__main__":
    given_model, given_record, given_folder = sys.argv[1:4]
    result = trialled(given_model, json.loads(pathlib.Path(given_record).read_text()), given_folder,
                      lock=os.environ.get("SCORE_CARD_LOCK"))
    print(f"joints: {sum(entry['passes'] for entry in result.values())}/{len(result)} parts pass, "
          f"{pathlib.Path(given_folder) / 'joints.json'}")
