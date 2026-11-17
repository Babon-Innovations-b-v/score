"""The walkers of a place_build scene, from their spots to the scene-clips output sim body and the cast read:

    python -m score.stages.walker_route plan <scene folder> <walkers.json> <place> <run folder>
    (Kimodo: tools/characters/clips/walker_route.py <tree> <run folder>/make)
    python -m score.stages.walker_route assemble <scene folder> <run folder>

walkers.json: {place: {"walkers": [{name, character, look, variant?, tread?, seconds?, through: [[x, y, z], ...]}]}}
(`seconds`: the clip lasts at least that long, the walker going on round its spots; walker_route.filled). `plan` writes
<run>/make/walkers.json (each walker's route, frames, feet ground and pieces); `assemble` writes <run>/cast/cast.json
(each walker a cast single at its route's start, turned to its first heading), <run>/scene-clips/scene_clips.json
(its placement, per-frame route and footfalls; rig.npz and motions/ come from the Kimodo program's rig step) and
prints each walker's measures (walker_route.measures) on one line.
"""
import json
import math
import pathlib
import shutil
import sys

import numpy as np

from score.stages import walker_route


def ground_reader(found):
    """A reader of the ground under scene points (n x 3), looked for from a knee over each point's height."""
    from score.stages.cast import measure

    def ground_at(spots):
        under = measure.ground_under([list(map(float, spot)) for spot in spots], found)
        return [spot[1] - stand["gap"] if stand["gap"] is not None else spot[1] for spot, stand in zip(spots, under)]
    return ground_at


def plan(scene, spec_path, place, run):
    """Each walker's route on the walkers' floor, walked frame by frame and cut into pieces: the make folder's plan."""
    from score.stages.place_build import ready
    spec = json.loads(pathlib.Path(spec_path).read_text())[place]
    found = ready.solids(scene)
    walkers = []
    for walker in spec["walkers"]:
        through, points, metres, roots, headings = walker_route.filled(scene, walker["through"], walker.get("seconds"),
                                                                       walker.get("tread"))
        feet = walker_route.feet_ground(roots, headings, ground_reader(found))
        found_pieces = walker_route.pieces(roots)
        walkers.append({**walker, "through": through, "clip": f"scene_{walker['name']}", "route": points,
                        "metres": metres,
                        "roots": np.round(roots, 5).tolist(), "headings": np.round(headings, 6).tolist(),
                        "feet": np.round(feet, 4).tolist(), "pieces": found_pieces})
        print(walker["name"], f"{metres} m", f"{len(roots)} frames", [(piece["kind"], piece["end"] - piece["start"])
                                                                      for piece in found_pieces], flush=True)
    make = pathlib.Path(run) / "make"
    shutil.rmtree(make, ignore_errors=True)
    make.mkdir(parents=True)
    walker_route.write_plan(make, place, walkers)


def single_of(walker, roots, headings):
    """A walker as a cast single (tools/characters/cast.py's keys) standing at its route's start: placed at its
    scene clip's placement, its turn the placement's less 180 (cast.py's front is -z, Kimodo's +Z)."""
    stairs = None
    kinds = {piece["kind"] for piece in walker["pieces"]} - {"walk"}
    if kinds:
        stairs = {"way": sorted(kinds)[0], "flight": walker.get("flight", "stairs"),
                  "run": walker.get("tread", 0.28), "to": list(map(float, roots[-1]))}
    return {"name": walker["name"], "character": walker["character"], "doing": "walking", "start": 0.0,
            "worn": None, "pace": walker_route.PACE, "held": False, "variant": walker.get("variant", 0),
            "look": walker["look"], "surface": None, "stairs": stairs, "path": walker["route"],
            "at": list(map(float, roots[0])), "turn": math.degrees(float(headings[0])) - 180.0}


def footfalls_of(motion, roots, headings, feet):
    """The made motion's stance middles as scene_clips' footfalls (frame, side, hips, heading, ground)."""
    falls = []
    for channel, start, end in walker_route.stances(np.asarray(motion["foot_contacts"]) > 0.5):
        if channel not in (2, 5):  # the toe end's runs alone, one a stance
            continue
        frame = (start + end - 1) // 2
        if frame >= len(roots):
            continue
        side = "left" if channel == 2 else "right"
        falls.append({"frame": int(frame), "side": side, "hips": [float(roots[frame, 0]), float(roots[frame, 2])],
                      "heading": float(headings[frame]), "ground": float(feet[frame, 0 if side == "left" else 1])})
    return sorted(falls, key=lambda fall: fall["frame"])


def assemble(scene, run):
    """The cast and the scene-clips record from the plan and the made motions; each walker's measures printed."""
    from score.stages.place_build import ready
    run = pathlib.Path(run)
    made = run / "make"
    plan = json.loads(walker_route.plan_file(made).read_text())
    triangles = np.concatenate(list(ready.solids(scene).values()))
    characters, clips, measured = [], [], {}
    for walker in plan["walkers"]:
        roots, headings = np.asarray(walker["roots"]), np.asarray(walker["headings"])
        feet = np.asarray(walker["feet"])
        motion = dict(np.load(made / "joined" / f"{walker['clip']}.npz"))
        single = single_of(walker, roots, headings)
        characters.append(single)
        climbs = single["stairs"] is not None
        clips.append({"name": walker["name"], "clip": walker["clip"], "pace": walker_route.PACE,
                      "sentence": walker_route.WALKING, "stairs": single["stairs"], "frames": len(roots), "cut": None,
                      "seconds": round(walker_route.seconds_of(len(roots)), 4),
                      "placement": {"origin": np.round(roots[0], 5).tolist(),
                                    "turn": round(math.degrees(float(headings[0])), 4)},
                      "route": np.round(roots, 4).tolist(),
                      "footfalls": footfalls_of(motion, roots, headings, feet) if climbs else [],
                      "relief": round(float(roots[:, 1].max() - roots[:, 1].min()), 4), "postprocess": not climbs,
                      "lift": 0.0, "pieces": walker["pieces"]})
        measured[walker["name"]] = walker_route.measures(motion, roots, triangles)
        print("MEASURES", walker["name"], json.dumps(measured[walker["name"]]), flush=True)
    (run / "cast").mkdir(exist_ok=True)
    (run / "cast" / "cast.json").write_text(json.dumps({"place": plan["place"], "characters": characters}, indent=1))
    out = run / "scene-clips"
    out.mkdir(exist_ok=True)
    (out / "scene_clips.json").write_text(json.dumps({"place": plan["place"], "clips": clips, "left out": []}, indent=1))
    (run / "measures.json").write_text(json.dumps(measured, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "plan":
        plan(*sys.argv[2:6])
    elif sys.argv[1] == "assemble":
        assemble(*sys.argv[2:4])
    else:
        raise SystemExit(__doc__)
