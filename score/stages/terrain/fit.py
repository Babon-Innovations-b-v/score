"""ground-fit@<place>: the place's own stage judged standing on its made ground (free, local, pxr and ray casts). It
reads the place's neighbours output where it has one (its shown places stand there), else its assembly, which takes
the terrain output's places/<place>.usdc over its old ground, so it needs no seed of its own and no work folder.

    make     measures.json: under, floating, continuous and openings, measured on that stage
    gates    under       every object that stood on the old ground has the made ground under its whole footprint, at
                         its feet (a flat world) or no rougher than before (a ball), and none over water
                         (gates.measure_under)
             floating    no object standing on the ground hangs over it: its lowest point more than gates.FEET over
                         the highest ground under its footprint, but within gates.STANDING_BAND of it
             continuous  no hole in the ground: a ray straight down from over the place hits a surface at every
                         CONTINUOUS_STEP metres over its own box grown by CONTINUOUS_REACH
             openings    no doorway onto nothing and no view from inside running out below the horizon into nothing,
                         the doors open (gates.measure_openings, sight.py)

A row of every place a ground plan seats (data/ground/plan/*.json `seats`), in any environment.
"""
import json
import pathlib

import numpy as np

from score import checks, contracts
from score.stages.terrain import gates, outside, record, sight

REPO = pathlib.Path(__file__).resolve().parents[3]
PLANS = REPO / "data/ground/plan"
MEASURES = "measures.json"
# The ground is judged continuous out to this many metres past the place's own box, a ray every this many metres
# (the near ground is laid out to outside.NEAR_MARGIN past it, finer than a step).
CONTINUOUS_REACH = 20.0
CONTINUOUS_STEP = 2.0


def seated(place):
    """The ground plan's name that seats the place, or None."""
    for path in sorted(PLANS.glob("*.json")):
        if place in json.loads(path.read_text()).get("seats", {}):
            return path.stem
    return None


def applies(place):
    return place is not None and seated(place) is not None


def files(place):
    """The ground plans and copied grounds (the old ground `under` reads), and the place's own records: its scene
    record and its kit (its door leaves)."""
    return {"grounds": "{data}/ground", "scene": "{data}/scene/{place}.json", "kit": "{data}/kit/{place}.json"}


def read_optional(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.is_file() else None


def judged_stage(inputs, place):
    """The place's stage it is judged on: its neighbours output's root where it has one, else its assembly's."""
    from pxr import Usd
    folder = pathlib.Path(inputs.get("neighbours") or inputs["assembly"])
    return Usd.Stage.Open(str(folder / f"{place}.usda"))


def measure_floating(boxes, ground_under):
    """Every object standing on the ground (its lowest point within gates.STANDING_BAND of the highest ground under
    its footprint, `ground_under(low, high)` the heights there) that hangs more than gates.FEET over it:
    {"standing": count, "faults": [...]}."""
    faults, standing = [], 0
    for name, (low, high) in boxes.items():
        ground = float(np.max(ground_under(low, high)))
        gap = float(low[1]) - ground
        if gap > gates.STANDING_BAND or gap < -gates.STANDING_BAND:
            continue
        standing += 1
        if gap > gates.FEET:
            faults.append(f"{name}: hangs {gap:.2f} m over the ground under it")
    return {"standing": standing, "faults": faults}


def measure_continuous(rays, scene, kit, top, up=(0.0, 1.0, 0.0)):
    """Rays straight down from `top` over the place's own box grown by CONTINUOUS_REACH, one every CONTINUOUS_STEP:
    {"rays", "holes", "first": the first few spots that hit nothing}."""
    low, high = gates.footprint(scene, kit)
    across = np.arange(low[0] - CONTINUOUS_REACH, high[0] + CONTINUOUS_REACH + 1e-9, CONTINUOUS_STEP)
    along = np.arange(low[1] - CONTINUOUS_REACH, high[1] + CONTINUOUS_REACH + 1e-9, CONTINUOUS_STEP)
    spots = np.array([[x, top, z] for x in across for z in along])
    missed = spots[~np.isfinite(gates.drops(rays, spots, -np.asarray(up, dtype=float)))]
    return {"rays": len(spots), "holes": len(missed),
            "first": [[round(float(x), 1), round(float(z), 1)] for x, _, z in missed[:5]]}


def make(inputs, out, seed, params):
    """The place's stage measured standing on its made ground: measures.json."""
    place = pathlib.Path(inputs["scene"]).stem
    ground = seated(place)
    plan_record = json.loads((pathlib.Path(inputs["grounds"]) / "plan" / f"{ground}.json").read_text())
    made = record.read(pathlib.Path(inputs["terrain"]) / ground)
    scene, kit = (read_optional(inputs[name]) if name in inputs else None for name in ("scene", "kit"))
    scene = scene or {}
    on_seat = (kit or {}).get("on_seat", [0.0, 0.0])
    laid = outside.placed_ground(made, made["places"][place], on_seat)
    stage = judged_stage(inputs, place)
    boxes = gates.object_boxes(stage, place)
    water = made["water"]["level"] - laid.drop if made.get("water") else None
    seen = sight.gathered(stage, gates.leaves(stage, place, kit))
    found = {"place": place, "ground": ground,
             "under": gates.measure_under(boxes, gates.old_ground(inputs["grounds"], plan_record, place, on_seat),
                                          laid, water),
             "floating": measure_floating(boxes, lambda low, high: gates.heights_under(
                 laid, gates.footprint_spots(low, high))),
             "continuous": measure_continuous(gates.caster(seen), scene, kit, float(seen.bounds[1][1]) + 1.0),
             "openings": gates.measure_openings(stage, place, (scene, kit), gates.ball_of(laid))}
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
    """Fail on any object that stood on the old ground and has no made ground under its whole footprint."""
    return faults_verdict("under", measured(output)["under"], "ground under all {standing} objects that stand on it")


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
