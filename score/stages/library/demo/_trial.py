"""What the physics setups' demos share (not a demo: `demos.modules` skips a module whose name starts with _): the
habitat's physics trial (physics-trial@habitat, recorded in the library's physics layer entry), its scene, and the
plan drawing of them. Its trial record is retired (record names why, so a demo reading it shows none)."""
import json

import numpy as np

PLACE = "habitat"
ENTRY = f"layer/physics.{PLACE}@1"


def trial(inputs):
    """The trial as it ran: {rate, frames, gravity, bodies {name: {mass, world, motions, lowest, ...}}, hinges}."""
    return inputs.json(ENTRY, "physics-trial/trial.json")


def record(inputs):
    """The trial record: body, material, drops, hinges, pushes, moved. None is kept: the habitat's hand-written trial
    record (data/physics/habitat.json) was the old concept's and is retired (owner, 2026-10-21: all old stuff is
    retired), and a design's trial is made from its design (score/stages/physics/design.py), not written down."""
    from score.stages.library import demos
    raise demos.NoExample(f"the {PLACE}'s trial record was the old concept's and is retired (2026-10-21); a demo "
                          "waits on a physics trial made from a design")


def scene(inputs, place=PLACE):
    """The place's scene record its demo is drawn on; NoExample while it has none (data/scene was retired with the old
    concepts, 2026-10-21: the scene-record row writes it again from the place's design)."""
    from score.stages.library.demos import NoExample
    path = inputs.repo / "data/scene" / f"{place}.json"
    if not path.exists():
        raise NoExample(f"no scene record of the {place} to draw it on: the old records were retired (2026-10-21) and "
                        "the scene-record row writes it from the design")
    return json.loads(path.read_text())


def seconds(ran):
    """[the time of each frame] of the trial."""
    return [frame / ran["rate"] for frame in range(ran["frames"])]


def plan_point(east, south):
    return [round(float(east), 2), round(float(-south), 2)]


def track(body):
    """[(x, y, z)] of the body's middle frame by frame: its motions (column vectors) applied to where it starts."""
    start = np.append(np.asarray(body["world"])[3, :3], 1.0)
    return [(np.asarray(motion) @ start)[:3] for motion in body["motions"]]


def floor(the_scene):
    """The room's floor as an area shape."""
    (low_x, low_z), (high_x, high_z) = the_scene["floor"]
    return {"kind": "area", "tone": "ground", "label": "the floor",
            "points": [plan_point(x, z) for x, z in ((low_x, low_z), (high_x, low_z), (high_x, high_z),
                                                      (low_x, high_z))]}


def plan_bounds(the_scene):
    (low_x, low_z), (high_x, high_z) = the_scene["floor"]
    return [*plan_point(low_x, high_z), *plan_point(high_x, low_z)]


def said(name):
    return name.replace("_", " ")
