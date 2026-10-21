"""ground-fit@<place>: the place's own stage judged standing on its made ground (free, local, pxr and ray casts). It
reads the place's neighbours output where it has one (its shown places stand there), else its assembly, which takes
the terrain output's places/<place>.usdc over its old ground, and its scene record (its box, doorways and views), so
it needs no seed, kit or old record of its own.

    make     measures.json: under, floating, continuous and openings, measured on that stage
    gates    under       every object standing on the ground has it under its whole footprint, no rougher there than
                         ROUGHER (the ground's height under its nine footprint spots)
             floating    no object standing on the ground hangs over it: its lowest point more than FEET over the
                         highest ground under its footprint, but within STANDING_BAND of it
             continuous  no hole in the ground: a ray straight down from over the place hits a surface at every
                         CONTINUOUS_STEP metres over its own box grown by CONTINUOUS_REACH
             openings    no doorway onto nothing and no view from inside running out below the horizon into nothing
                         (gates.measure_openings, sight.py)

A row of every place the design stands on a ground (terrain design.on_ground: a top scene at its site, or a scene its
plan holds), in any environment.
"""
import json
import pathlib

import numpy as np

from score import checks, contracts
from score.stages.terrain import design, gates, sight

MEASURES = "measures.json"
# The ground is judged continuous out to this many metres past the place's own box, a ray every this many metres.
CONTINUOUS_REACH = 20.0
CONTINUOUS_STEP = 2.0
# An object stands on the ground when its lowest point is within this of the highest ground under its footprint; it
# floats when more than FEET over it; the ground under a standing one varies at most ROUGHER (metres).
STANDING_BAND = 0.3
FEET = 0.05
ROUGHER = 0.10


def applies(place):
    return place is not None and design.on_ground(place)


def files(place):
    """Nothing beyond its reads: the made ground, its scene record and its stage are other rows' outputs."""
    return {}


def judged_stage(inputs, place):
    """The place's stage it is judged on: its neighbours output's root where it has one, else its assembly's."""
    from pxr import Usd
    folder = pathlib.Path(inputs.get("neighbours") or inputs["assembly"])
    return Usd.Stage.Open(str(folder / f"{place}.usda"))


def record_of(inputs):
    """(place, its scene record) from the scene-record output."""
    path = next(pathlib.Path(inputs["scene-record"]).glob("record/*.json"))
    return path.stem, json.loads(path.read_text())


def ground_of(inputs, place):
    """The made ground the place stands on, from the terrain output."""
    for path in sorted(pathlib.Path(inputs["terrain"]).glob("*/ground.json")):
        ground = json.loads(path.read_text())
        if place in ground["places"]:
            return ground
    raise ValueError(f"{place}: the terrain row made no ground it stands on")


def measure_standing(boxes, ground_under):
    """Every object standing on the ground (its lowest point within STANDING_BAND of the highest ground under its
    footprint, `ground_under(low, high)` the heights there): {"standing", "floating": [...], "rough": [...]}."""
    floating, rough, standing = [], [], 0
    for name, (low, high) in boxes.items():
        under = ground_under(low, high)
        gap = float(low[1]) - float(np.max(under))
        if abs(gap) > STANDING_BAND:
            continue
        standing += 1
        if gap > FEET:
            floating.append(f"{name}: hangs {gap:.2f} m over the ground under it")
        if np.ptp(under) > ROUGHER:
            rough.append(f"{name}: the ground under it varies {np.ptp(under):.2f} m")
    return {"standing": standing, "floating": floating, "rough": rough}


def measure_continuous(rays, record, top, up=(0.0, 1.0, 0.0)):
    """Rays straight down from `top` over the place's own box grown by CONTINUOUS_REACH, one every CONTINUOUS_STEP:
    {"rays", "holes", "first": the first few spots that hit nothing}."""
    low, high = gates.footprint(record)
    across = np.arange(low[0] - CONTINUOUS_REACH, high[0] + CONTINUOUS_REACH + 1e-9, CONTINUOUS_STEP)
    along = np.arange(low[1] - CONTINUOUS_REACH, high[1] + CONTINUOUS_REACH + 1e-9, CONTINUOUS_STEP)
    spots = np.array([[x, top, z] for x in across for z in along])
    missed = spots[~np.isfinite(gates.drops(rays, spots, -np.asarray(up, dtype=float)))]
    return {"rays": len(spots), "holes": len(missed),
            "first": [[round(float(x), 1), round(float(z), 1)] for x, _, z in missed[:5]]}


def make(inputs, out, seed, params):
    """The place's stage measured standing on its made ground: measures.json."""
    place, record = record_of(inputs)
    ground = ground_of(inputs, place)
    shaped = design.reliefs(ground)
    stage = judged_stage(inputs, place)
    boxes = gates.object_boxes(stage, place)
    standing = measure_standing(boxes, lambda low, high: design.ground_points(
        ground, place, gates.footprint_spots(low, high), shaped)[:, 1])
    seen = sight.gathered(stage)
    found = {"place": place, "ground": ground["on"],
             "under": {"standing": standing["standing"], "faults": standing["rough"]},
             "floating": {"standing": standing["standing"], "faults": standing["floating"]},
             "continuous": measure_continuous(gates.caster(seen), record, float(seen.bounds[1][1]) + 1.0),
             "openings": gates.measure_openings(stage, place, record, design.ball_of(ground, place))}
    (out / MEASURES).write_text(json.dumps(found, indent=1))


def measured(output):
    return json.loads((pathlib.Path(output) / MEASURES).read_text())


def faults_verdict(check, found, sentence):
    """A verdict on one measure's faults list: fail on any, else pass with `sentence`."""
    faults = found["faults"]
    return checks.Verdict(check, checks.FAIL if faults else checks.PASS,
                          f"{len(faults)} of {found['standing']} objects on the ground: {faults[0]}" if faults
                          else sentence.format(**found), {"faults": len(faults), "standing": found["standing"]},
                          {"faults": "lower"}, tuple(faults))


def judge_under(output, inputs, evidence):
    """Fail on any object standing on the ground whose footprint the ground under it does not hold level."""
    return faults_verdict("under", measured(output)["under"],
                          "ground under all {standing} objects that stand on it, level enough for each")


def judge_floating(output, inputs, evidence):
    """Fail on any object standing on the ground that hangs over it."""
    return faults_verdict("floating", measured(output)["floating"],
                          "none of the {standing} objects on the ground hangs over it")


def judge_continuous(output, inputs, evidence):
    """Fail on any ray straight down over the place that hits nothing: a hole in the ground."""
    found = measured(output)["continuous"]
    holes = [f"no ground under ({x}, {z})" for x, z in found["first"]]
    return checks.Verdict("continuous", checks.FAIL if found["holes"] else checks.PASS,
                          f"{found['holes']} of {found['rays']} rays down hit nothing" + (f", first {holes[0]}"
                                                                                         if holes else ""),
                          {"holes": found["holes"], "rays": found["rays"]}, {"holes": "lower"}, tuple(holes))


def judge_openings(output, inputs, evidence):
    """Fail on any doorway that opens onto nothing or any view that runs out below the horizon into nothing."""
    found = measured(output)["openings"]
    findings = [f"{door['door']} opens onto nothing (floor {door['drops']} m under the sill)"
                for door in found["doors"] if door["open_onto_nothing"]]
    if found["void_rays"]:
        findings.append(f"{found['void_rays']} of {found['rays']} view rays run out below the horizon into nothing "
                        f"(worst from {found['worst_probe']['at']})")
    return checks.Verdict("openings", checks.FAIL if findings else checks.PASS,
                          "; ".join(findings) or f"all {len(found['doors'])} doorways open onto a floor, no view "
                                                 "runs out into nothing",
                          {"doors onto nothing": found["doors_onto_nothing"], "void rays": found["void_rays"]},
                          {"doors onto nothing": "lower", "void rays": "lower"}, tuple(findings))


def fit_faults(folder):
    return [] if (pathlib.Path(folder) / MEASURES).is_file() else [f"no {MEASURES}"]


FIT = contracts.Contract("ground-fit", 1, fit_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("under", judge_under), checks.Check("floating", judge_floating),
          checks.Check("continuous", judge_continuous), checks.Check("openings", judge_openings))
