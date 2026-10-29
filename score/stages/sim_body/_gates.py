"""The sim body stage's measures and gates: a run's gate numbers (`measured`) and each gate's judge."""
import json
import pathlib

import numpy as np

from score import checks

LAYER = "layers/sim_bodies.usda"
RECORD = "sim_bodies.json"
# MyoFullBody's foot colliders meet a MuJoCo floor within their 1 mm margin, MuJoCo's default solref and solimp, as
# MyoSuite, MuscleMimic and KINESIS leave them: 75 kg on two such capsules rests 0.1 mm into it without the margin and
# 0.9 mm over it with it (measured, MuJoCo 3.x, 1 ms steps, 2026-10-28), so
# a body more than a few millimetres into its ground is sunk (owner, 2026-10-28: "ground contact is real"); the ground
# pushes a point only within the run's GAP (5 mm) over it, so a carrying foot further off is floating.
SUNK_MOST = 0.003  # metres
LANDED = 0.005  # metres
CONTACT = 0.05  # share of the weight a foot's push must reach to count as landed
CARRIED = 0.05  # share of the weight
FOLLOWED = 5.0  # degrees
# The residual's limits, the body's weight standing in for the net external force (none is measured here): the force
# at most 2% of it (owner, 2026-10-28, from 5%: AddBiomechanics' published residual forces are "smaller than 2% of peak
# external force", Werling et al. 2023, PLoS ONE 18:e0295152, doi:10.1371/journal.pone.0295152, taken as the
# benchmark only), the moment at most 1% of it times the centre of mass' height (Hicks, Uchida, Seth, Rajagopal and
# Delp 2015, "Is my model good enough?", J Biomech Eng 137(2):020905, section 3.1.3).
RESIDUAL_FORCE = 0.02
RESIDUAL_MOMENT = 0.01
# The residual reduction's cap (inside/sim_body.py `reduced`, OpenSim's RRA): on every frame, all rounds together, the
# pelvis at most MOVE_MOST and every segment's turn at most FOLLOWED off the fitted path (owner, 2026-10-28;
# `within_frames`, gated by `follows`), and the adjusted path kept within FOLLOWED of the clip on the mean (the owner,
# 2026-10-28: "never more"). MOVE_MOST is ours: no published limit names a pelvis move.
MOVE_MOST = 0.02  # metres


def angle_between(one, other):
    """The angle (degrees) between two rotations given as rotation vectors in degrees."""
    from scipy.spatial.transform import Rotation
    turn = Rotation.from_rotvec(np.radians(one)) * Rotation.from_rotvec(np.radians(other)).inv()
    return np.degrees(turn.magnitude())


def landings(frames, weight):
    """Each landed foot's height over its ground (metres), frame by frame: a foot the ground pushes up with at least
    CONTACT of the weight."""
    return [height for frame in frames for height, push in frame["feet"].values()
            if push >= CONTACT * weight and height is not None]


def measured(entry, gravity):
    """A run's gate numbers: its deepest point into its ground, each landed foot's height off it, the mean upward push
    over its weight, the mean and worst angle off the clip, the largest move RRA made off the fitted path on any frame
    (a segment's turn, the pelvis' place), the largest joint moment and reserve, the residual's
    largest force and moment against their limits, and the muscles' activations and forces."""
    frames, weight = entry["frames"], entry["kg"] * gravity
    off = np.array([angle_between(frame["angles"], frame["targets"]) for frame in frames])
    push = np.mean([frame["ground"][1] for frame in frames])
    landed = np.abs(landings(frames, weight))
    force = np.array([float(np.linalg.norm(frame["residual"][:3])) for frame in frames])
    moment = np.array([float(np.linalg.norm(frame["residual"][3:])) for frame in frames])
    limits = (RESIDUAL_FORCE * weight, RESIDUAL_MOMENT * entry["com height"] * weight)
    forces, activations = np.array([frame["forces"] for frame in frames]), np.array([frame["activations"]
                                                                                     for frame in frames])
    return {"deepest": round(-min(0.0, min(frame["lowest"] for frame in frames if frame["lowest"] is not None)), 4),
            "landings": len(landed), "mean foot off ground m": round(float(landed.mean()), 4) if len(landed) else None,
            "worst foot off ground m": round(float(landed.max()), 4) if len(landed) else None,
            "weight N": round(weight, 2), "mean push N": round(float(push), 2),
            "push over weight": round(float(push / weight), 4),
            "mean off clip deg": round(float(off.mean()), 3), "worst off clip deg": round(float(off.max()), 3),
            "largest adjusted turn deg": entry["adjusted"]["largest turn deg"],
            "largest pelvis move cm": entry["adjusted"]["pelvis cm"][1],
            "largest torque Nm": round(float(max(np.abs(frame["torques"]).max() for frame in frames)), 2),
            "largest reserve Nm": round(float(max(frame["reserve"] for frame in frames)), 2),
            "largest residual N": round(float(force.max()), 2), "mean residual N": round(float(force.mean()), 2),
            "median residual N": round(float(np.median(force)), 2), "residual force limit N": round(limits[0], 2),
            "largest residual Nm": round(float(moment.max()), 2), "mean residual Nm": round(float(moment.mean()), 2),
            "median residual Nm": round(float(np.median(moment)), 2), "residual moment limit Nm": round(limits[1], 2),
            "frames within residual limits": round(float(((force <= limits[0]) & (moment <= limits[1])).mean()), 3),
            "largest muscle force N": round(float(forces.max()), 1),
            "muscle force N, mean of each frame's largest": round(float(forces.max(axis=1).mean()), 1),
            "largest activation": round(float(activations.max()), 4),
            "mean activation": round(float(activations.mean()), 4)}


def bodies_of(output):
    return json.loads((pathlib.Path(output) / RECORD).read_text())["bodies"]


def verdict(name, faults, passed, measures, findings=()):
    return checks.Verdict(name, checks.FAIL if faults else checks.PASS, "; ".join(faults[:3]) if faults else passed,
                          measures, {}, tuple(faults) or tuple(findings))


def judge_on_floor(output, inputs, evidence):
    """Fail a body that went into its ground by more than SUNK_MOST in any frame."""
    bodies = bodies_of(output)
    faults = [f"{name} went {body['measures']['deepest']:.3f} m into its ground" for name, body in bodies.items()
              if body["measures"]["deepest"] > SUNK_MOST]
    return verdict("on floor", faults, f"{len(bodies)} bodies, none into its ground by over {SUNK_MOST} m",
                   {"bodies": len(bodies)})


def judge_lands(output, inputs, evidence):
    """Fail a body a landed foot of which stood more than LANDED off its ground, or none of whose feet ever landed."""
    bodies = bodies_of(output)
    faults = [f"{name}: no foot landed on its ground" if not body["measures"]["landings"] else
              f"{name}: a landed foot {body['measures']['worst foot off ground m']:.3f} m off its ground"
              for name, body in bodies.items() if not body["measures"]["landings"]
              or body["measures"]["worst foot off ground m"] > LANDED]
    return verdict("lands", faults, f"{len(bodies)} bodies, each landed foot within {LANDED} m of its ground",
                   {"bodies": len(bodies)})


def judge_carries(output, inputs, evidence):
    """Fail a body whose ground's mean push is off its weight by more than CARRIED of it."""
    bodies = bodies_of(output)
    faults = [f"{name}: the ground pushes {body['measures']['push over weight']:.3f} of its weight"
              for name, body in bodies.items() if abs(body["measures"]["push over weight"] - 1.0) > CARRIED]
    return verdict("carries", faults, f"{len(bodies)} bodies, the ground carries each one's weight within "
                   f"{CARRIED:.0%}", {"bodies": len(bodies)})


def judge_follows(output, inputs, evidence):
    """Fail a body whose joints are off its clip's by more than FOLLOWED degrees on the mean, or that RRA moved off its
    fitted path by more than FOLLOWED degrees on a segment or MOVE_MOST at the pelvis on any frame."""
    bodies, faults = bodies_of(output), []
    for name, body in bodies.items():
        found = body["measures"]
        if found["mean off clip deg"] > FOLLOWED:
            faults.append(f"{name}: {found['mean off clip deg']:.2f} degrees off its clip on the mean")
        if found["largest adjusted turn deg"] > FOLLOWED:
            faults.append(f"{name}: a segment turned {found['largest adjusted turn deg']:.1f} degrees off its fitted "
                          f"path in a frame")
        if found["largest pelvis move cm"] > 100 * MOVE_MOST:
            faults.append(f"{name}: the pelvis moved {found['largest pelvis move cm']:.1f} cm off its fitted path in "
                          f"a frame")
    return verdict("follows", faults, f"{len(bodies)} bodies, each within {FOLLOWED} degrees of its clip on the mean "
                   f"and RRA's move within {FOLLOWED} degrees and {100 * MOVE_MOST:.0f} cm on every frame",
                   {"bodies": len(bodies)})


def judge_residual(output, inputs, evidence):
    """Fail a body whose pelvis residual passes its force or moment limit in any frame."""
    bodies = bodies_of(output)
    faults = []
    for name, body in bodies.items():
        found = body["measures"]
        if found["largest residual N"] > found["residual force limit N"]:
            faults.append(f"{name}: a residual of {found['largest residual N']:.0f} N, over its "
                          f"{found['residual force limit N']:.0f} N")
        if found["largest residual Nm"] > found["residual moment limit Nm"]:
            faults.append(f"{name}: a residual moment of {found['largest residual Nm']:.0f} N m, over its "
                          f"{found['residual moment limit Nm']:.0f} N m")
    return verdict("residual", faults, f"{len(bodies)} bodies, each residual within {RESIDUAL_FORCE:.0%} of its weight "
                   f"and {RESIDUAL_MOMENT:.0%} of its weight times its centre's height", {"bodies": len(bodies)})


def output_faults(folder):
    folder = pathlib.Path(folder)
    found = [f"no {name}" for name in (RECORD, LAYER) if not (folder / name).exists()]
    if not found and not bodies_of(folder):
        found.append("no sim body: the cast names no character whose clip the rig holds")
    return found
