"""The physics stage (experimental, F11: the paper's "responsive"): a place's stage with its physics in OpenUSD's own
schema, and a trial in a physics engine that shows its objects react. The trial is made from the scene's design
(design.py: its loose rows' laid objects dropped back onto where they stand, under the gravity of the body its site
is on), never from a record written for the scene; only a scene whose inventory has a loose row has the rows.

    physics-layer  (free) the place's stage copied (its neighbours output where it shows other places, they standing
                   in it under places/, else its assembly), its trial record made from the design (record.json), with
                   tools/usd/physics.py's layers: every mesh colliding by its
                   triangles, every object's mass (its surface's area, its material's sheet and density) and physics
                   material (friction, restitution), the scene's pull; and the trial: its bodies colliding by their
                   convex hulls, its drops lifted over their targets, its hinge (a RevoluteJoint with limits and a
                   motor), its pushes (kinematic hands). physics.json says what was written.
       gates       laid      the record's trial stands: every body draws a mesh and has a mass, nothing but its
                             target stands under a drop
                   designed  every object the trial names is an object of a row of the scene's inventory, and it
                             drops at least one
    physics-trial  (paid) the trial run on Blender's Bullet from the stage's UsdPhysics
                   (inside/physics_trial.py) on a rented machine; its motion written back as
                   layers/physics_motion.usda; the record's views rendered at its moments (usd_views.py on the same
                   card); trial.json (every frame), measures.json, strip-<view>.png (the moments side by side)
       gates       reacted   each drop came to rest on its target, each hinge opened at least OPENED_LEAST, each
                             pushed object moved at least MOVED_LEAST
                   at rest   at the end every body is still (under STILL), lies inside no static, and no body ever
                             went under the floor (FLOOR_MOST)
                   hinge     every hinge stayed within its limits (to LIMIT_SLACK) every frame
                   energy    while nothing drives the trial (no hand moves, no motor is on), the bodies' energy never
                             rises over where it stood when the drive stopped (ENERGY_SLACK)
"""
import json
import pathlib
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

from score import checks, contracts
from score.adapters import engines
from score.stages import row_kinds

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import physics  # noqa: E402
from score.stages.physics import design  # noqa: E402

TRIAL_SCRIPT = "score/stages/physics/inside/physics_trial.py"
RENDER_SCRIPT = "tools/blender/inside/usd_views.py"
# The cheapest card that fits (the budget of 2026-10-12): a few minutes of Bullet on its processor, then sixteen looks.
CARDS = ("gpu-24gb",)
WHO = "score physics trial"
# About forty minutes of one 24 GB card with its start.
EUROS = 2.0
TRIAL_MINUTES = 20
MINUTES_A_VIEW = 3
STILL = 0.05
FLOOR_MOST = -0.02
OPENED_LEAST = 45.0
MOVED_LEAST = 0.2
LIMIT_SLACK = 1.0
# A drop rests on its target when its lowest point ends this close over the target's top (metres; the collision
# margins of the two bodies stand between them).
LANDED = (-0.01, 0.03)
# The energy may rise this share of itself, or this many joules, over where it stood: a contact solver's jitter.
ENERGY_SLACK = (0.01, 1.0)


LAYER_FILES = {**row_kinds.DESIGNED, "materials": "{data}/physics/materials.json",
               "physics": "{data}/physics/setting.json", "bodies": "{data}/physics/bodies.json",
               "within": "{data}/places/within.json"}


# What the trial reads besides the layer's output (its record there, the places it shows under places/): the Blender
# scripts it runs.
TRIAL_FILES = {"renderer": "{data}/../tools/blender/inside", "trial script": "{repo}/" + TRIAL_SCRIPT}


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def place_of(folder):
    return next(pathlib.Path(folder).glob("*.usda")).stem


# --- physics-layer -----------------------------------------------------------------------------------------------

def make_layer(inputs, out, seed, params):
    """The place's stage (its neighbours output where it has one, else its assembly) with the physics and trial
    layers, and what was written."""
    for child in pathlib.Path(inputs.get("neighbours") or inputs["assembly"]).iterdir():
        if child.name == "contract.json":
            continue
        (shutil.copytree if child.is_dir() else shutil.copy2)(child, out / child.name)
    subprocess.run(["chmod", "-R", "u+w", str(out)], check=True)
    record = designed_trial(inputs, out)
    (out / "record.json").write_text(json.dumps(record, indent=1))
    written = physics.write(out, record, read_json(inputs["materials"]))
    (out / "physics.json").write_text(json.dumps(written, indent=1))


def designed_trial(inputs, folder):
    """The trial record made from the scene's design over the stage in `folder` (design.py)."""
    stage, root = physics.opened(folder)
    place = root.stem
    within = {name: entry["within"] for name, entry in read_json(inputs["within"]).get("within", {}).items()}
    under = design.ground(place, within, read_json(inputs["physics"]))
    return design.trial(place, stage, read_json(inputs["design"]), row_kinds.table(inputs["row kinds"]), under)


def judge_designed(output, inputs, evidence):
    """Pass when every object the trial names is an object of a row of the scene's inventory and it drops one."""
    record = read_json(pathlib.Path(output) / "record.json")
    names = physics.bodies_of(record)
    strangers = row_kinds.strangers(names, read_json(inputs["design"]))
    faults = [f"{name} is no object of the scene's inventory" for name in strangers]
    if not names:
        faults.append("no loose object of the design stands clear to drop" +
                      (f" ({'; '.join(record['left out'])})" if record.get("left out") else
                       " (none of its loose rows is laid on the stage)"))
    return checks.Verdict("designed", checks.FAIL if faults else checks.PASS,
                          f"{len(faults)} faults" if faults else
                          f"{len(names)} bodies, each an object of a loose row of the scene's inventory",
                          {"bodies": len(names)}, {}, tuple(faults) or tuple(record.get("left out", [])))


def judge_laid(output, inputs, evidence):
    """Pass when the trial was written: no fault stopped it and every body has a mass."""
    written = read_json(pathlib.Path(output) / "physics.json")
    faults = list(written["faults"])
    faults += [f"{name} has no mass" for name, mass in written.get("bodies", {}).items() if not mass > 0]
    return checks.Verdict("laid", checks.FAIL if faults else checks.PASS,
                          f"{len(faults)} faults stop the trial" if faults
                          else f"{len(written['bodies'])} bodies laid over {written['meshes']} colliding meshes",
                          {"bodies": len(written.get("bodies", {}))}, {}, tuple(faults))


def layer_faults(folder):
    folder = pathlib.Path(folder)
    found = contracts.openusd_stage_faults(folder)
    return found + [f"no {name}" for name in ("physics.json", "record.json") if not (folder / name).exists()]


LAYER = contracts.Contract("physics-layer", 1, layer_faults, {"length": "metre", "up axis": "Y"})
LAYER_CHECKS = (checks.Check("laid", judge_laid), checks.Check("designed", judge_designed))


# --- physics-trial -----------------------------------------------------------------------------------------------

def moment_views(record, rate):
    """Each of the record's views at each of its moments: a look at that frame of the stage."""
    return [dict(view, name=f"{view['name']}-t{moment:04.1f}", frame=int(round(moment * rate)), look_only=True,
                 moment=moment) for view in record["views"] for moment in record["moments"]]


def render(machine, folder, place, views, size, out):
    """Every view rendered in one Blender run on the held machine, into out/frames."""
    out.mkdir(parents=True, exist_ok=True)
    spec = out / "views.json"
    spec.write_text(json.dumps({"size": size, "views": views}))
    machine.run(REPO / RENDER_SCRIPT, [folder / place / f"{place}.usda", spec, out / "frames"],
                [*folder.iterdir(), spec], [out / "frames"], MINUTES_A_VIEW * len(views))


def strips(out, record):
    """strip-<view>.png: the view's moments side by side, in order."""
    for view in record["views"]:
        pictures = [Image.open(out / "frames" / f"{view['name']}-t{moment:04.1f}-look.png")
                    for moment in record["moments"]]
        wide, tall = pictures[0].size
        strip = Image.new("RGB", (wide * len(pictures), tall))
        for index, picture in enumerate(pictures):
            strip.paste(picture.convert("RGB"), (index * wide, 0))
        strip.save(out / f"strip-{view['name']}.png")


def starts(folder, place, names):
    """Each body's bounds' middle where the trial starts it (the stage's frame)."""
    stage, _ = physics.opened(folder / place)
    boxes = {name: physics.world_box(physics.object_prim(stage, name)) for name in names}
    return {name: ((low + high) / 2).tolist() for name, (low, high) in boxes.items()}


def trial_folder(out, place, layer):
    """out/stages/trial holding a writable copy of the layer's stage (the places it shows under places/ with it) as
    <place>/, less its contract."""
    folder = out / "stages" / "trial"
    shutil.copytree(layer, folder / place, ignore=shutil.ignore_patterns("contract.json"))
    subprocess.run(["chmod", "-R", "u+w", str(folder / place)], check=True)
    return folder


def make_trial(inputs, out, seed, params):
    """Run the trial on a rented machine, play its motion back in the stage, render its moments, measure it."""
    layer = pathlib.Path(inputs["physics-layer"])
    place = place_of(layer)
    record = read_json(layer / "record.json")
    folder = trial_folder(out, place, layer)
    root = folder / place / f"{place}.usda"
    # One card held for both steps: one machine's start, not two.
    with engines.machine_runner().Machine(CARDS, WHO) as machine:
        machine.run(REPO / TRIAL_SCRIPT, [root, out / "trial.json"], list(folder.iterdir()), [out / "trial.json"],
                    TRIAL_MINUTES)
        trial = read_json(out / "trial.json")
        physics.write_motion(folder / place, {name: body["motions"] for name, body in trial["bodies"].items()})
        middles = starts(folder, place, trial["bodies"])
        render(machine, folder, place, moment_views(record, trial["rate"]), record["size"], out)
    strips(out, record)
    (out / "measures.json").write_text(json.dumps(measured(trial, record, read_json(layer / "physics.json"), middles),
                                                  indent=1))
    shutil.copy2(folder / place / "layers/physics_motion.usda", out / "physics_motion.usda")
    shutil.copy2(layer / "record.json", out / "record.json")
    shutil.rmtree(out / "stages")


def moved_by(motion, middle):
    """How far a point of the body moved under its motion (column vectors, the stage's frame)."""
    point = np.append(np.asarray(middle, dtype=float), 1.0)
    return float(np.linalg.norm((np.asarray(motion) @ point)[:3] - point[:3]))


def energy_rises(energy, driven):
    """Each undriven stretch's worst rise over where its energy stood when it began (joules), by its first frame."""
    rises, begun = {}, None
    for frame, (value, pushed) in enumerate(zip(energy, driven)):
        if pushed:
            begun = None
            continue
        if begun is None:
            begun = frame
        rises[begun] = max(rises.get(begun, 0.0), value - energy[begun])
    return {begun: (round(rise, 4), round(energy[begun], 4)) for begun, rise in rises.items()}


def measured(trial, record, laid, middles):
    """The trial's measures: each body's end, each drop's landing, each hinge's swing, the energy's rises."""
    joined = {frozenset(pair) for pair in trial["joined"]}
    bodies = {}
    for name, body in trial["bodies"].items():
        # A body lies against what its joint holds it to (a leaf in its frame): only other statics count.
        inside = [path for path in trial["inside at end"].get(name, [])
                  if frozenset((name, path.removesuffix("/geo"))) not in joined]
        bodies[name] = {"mass": body["mass"], "end speed": body["speed"][-1], "lowest ever": min(body["lowest"]),
                        "lowest at end": body["lowest"][-1],
                        "moved": round(moved_by(body["motions"][-1], middles[name]), 4), "inside at end": inside}
    drops = {drop["object"]: {"onto": drop.get("onto", "where it stood"), "top": laid["tops"][drop["object"]],
                              "over top at end": round(bodies[drop["object"]]["lowest at end"]
                                                       - laid["tops"][drop["object"]], 4)}
             for drop in record["drops"]}
    hinges = {leaf: {"lower": hinge["lower"], "upper": hinge["upper"], "least": min(hinge["angles"]),
                     "most": max(hinge["angles"]), "end": hinge["angles"][-1]}
              for leaf, hinge in trial["hinges"].items()}
    return {"frames": trial["frames"], "rate": trial["rate"], "gravity": trial["gravity"], "statics": trial["statics"],
            "bodies": bodies, "drops": drops, "hinges": hinges, "moved": record.get("moved", []),
            "energy rises": energy_rises(trial["energy"], trial["driven"]),
            "energy": {"start": trial["energy"][0], "most": max(trial["energy"]), "end": trial["energy"][-1]}}


def measures(output):
    return read_json(pathlib.Path(output) / "measures.json")


def judge_reacted(output, inputs, evidence):
    """Pass when each drop rests on its target, each hinge opened, each pushed object moved."""
    found = measures(output)
    faults = [f"{name} ended {drop['over top at end']:+.3f} m from the top of {drop['onto']}"
              for name, drop in found["drops"].items() if not LANDED[0] <= drop["over top at end"] <= LANDED[1]]
    faults += [f"{leaf} opened only {hinge['most']:.1f} degrees" for leaf, hinge in found["hinges"].items()
               if hinge["most"] - hinge["lower"] < OPENED_LEAST]
    faults += [f"{name} moved only {found['bodies'][name]['moved']:.3f} m" for name in found["moved"]
               if found["bodies"][name]["moved"] < MOVED_LEAST]
    return checks.Verdict("reacted", checks.FAIL if faults else checks.PASS,
                          f"{len(faults)} objects did not react as the trial asks" if faults else
                          f"{len(found['drops'])} drops landed, {len(found['hinges'])} hinges opened, "
                          f"{len(found['moved'])} pushed objects moved",
                          {"opened": max((hinge["most"] for hinge in found["hinges"].values()), default=0.0)},
                          {}, tuple(faults))


def judge_rest(output, inputs, evidence):
    """Pass when every body ends still, inside no static, and never went under the floor."""
    found = measures(output)
    faults = []
    for name, body in found["bodies"].items():
        if body["end speed"] > STILL:
            faults.append(f"{name} still moves at {body['end speed']:.3f} m/s")
        if body["inside at end"]:
            faults.append(f"{name} ends inside {', '.join(body['inside at end'])}")
        if body["lowest ever"] < FLOOR_MOST:
            faults.append(f"{name} went {-body['lowest ever']:.3f} m under the floor")
    fastest = max(body["end speed"] for body in found["bodies"].values())
    return checks.Verdict("at rest", checks.FAIL if faults else checks.PASS,
                          f"{len(faults)} faults at the end" if faults
                          else f"all {len(found['bodies'])} bodies at rest, through nothing",
                          {"fastest at end": fastest}, {"fastest at end": "lower"}, tuple(faults))


def judge_hinge(output, inputs, evidence):
    """Pass when every hinge stayed within its limits every frame."""
    found = measures(output)
    faults = [f"{leaf} swung {hinge['least']:.1f} to {hinge['most']:.1f} degrees, limits {hinge['lower']:.0f} to "
              f"{hinge['upper']:.0f}" for leaf, hinge in found["hinges"].items()
              if hinge["least"] < hinge["lower"] - LIMIT_SLACK or hinge["most"] > hinge["upper"] + LIMIT_SLACK]
    if not found["hinges"]:
        said = read_json(pathlib.Path(output) / "record.json").get("no_hinges")
        return checks.Verdict("hinge", checks.PASS if said else checks.UNKNOWN,
                              f"the trial hangs no hinge: {said}" if said else
                              "the trial has no hinge and its record does not say why (`no_hinges`)")
    return checks.Verdict("hinge", checks.FAIL if faults else checks.PASS,
                          f"{len(faults)} hinges left their limits" if faults else
                          "every hinge within its limits: " + ", ".join(
                              f"{leaf} {hinge['least']:.1f} to {hinge['most']:.1f}" for leaf, hinge in
                              found["hinges"].items()),
                          {}, {}, tuple(faults))


def judge_energy(output, inputs, evidence):
    """Pass when the energy never rises while nothing drives the trial."""
    found = measures(output)
    faults = [f"from frame {begun}: rose {rise:.2f} J over {start:.2f} J"
              for begun, (rise, start) in found["energy rises"].items()
              if rise > max(ENERGY_SLACK[0] * abs(start), ENERGY_SLACK[1])]
    worst = max((rise for rise, _ in found["energy rises"].values()), default=0.0)
    return checks.Verdict("energy", checks.FAIL if faults else checks.PASS,
                          f"the energy rose undriven in {len(faults)} stretches" if faults
                          else f"no undriven rise over the slack (worst {worst:.3f} J)",
                          {"worst rise": worst}, {"worst rise": "lower"}, tuple(faults))


def trial_faults(folder):
    """Every trial output: its run, its measures, a strip a view."""
    folder = pathlib.Path(folder)
    missing = [name for name in ("trial.json", "measures.json", "physics_motion.usda", "record.json")
               if not (folder / name).exists()]
    return [f"no {name}" for name in missing] + ([] if list(folder.glob("strip-*.png")) else ["no strip"])


TRIAL = contracts.Contract("physics-trial", 1, trial_faults, {"length": "metre", "time": "second"})
TRIAL_CHECKS = (checks.Check("reacted", judge_reacted), checks.Check("at rest", judge_rest),
                checks.Check("hinge", judge_hinge), checks.Check("energy", judge_energy))
