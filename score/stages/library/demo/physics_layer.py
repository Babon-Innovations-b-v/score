"""The physics layer at work in the habitat: its trial (physics-trial@habitat, recorded in the library's physics layer
entry) as seen from above: the hatch driven open on its hinge, the stool pushed across the floor, two cases dropped
onto the table and the floor; each body's path is its recorded motion, frame by frame."""
import json

import numpy as np

ALGORITHM = "physics_layer"
PLACE = "habitat"
ENTRY = f"layer/physics.{PLACE}@1"
EVERY = 3  # frames kept along a path


def plan_point(east, south):
    return [round(float(east), 2), round(float(-south), 2)]


def track(body):
    """[(x, y, z)] of the body's middle frame by frame: its motions (column vectors) applied to where it starts."""
    start = np.append(np.asarray(body["world"])[3, :3], 1.0)
    return [(np.asarray(motion) @ start)[:3] for motion in body["motions"]]


def floor_outline(scene):
    (low_x, low_z), (high_x, high_z) = scene["floor"]
    return [plan_point(x, z) for x, z in ((low_x, low_z), (high_x, low_z), (high_x, high_z), (low_x, high_z))]


def dot(name, point, tone, label):
    return {"kind": "dots", "points": [plan_point(point[0], point[2])], "r": 0.35, "tone": tone, "id": name,
            "label": label}


def path(points, tone, label):
    return {"kind": "path", "points": [plan_point(point[0], point[2]) for point in points[::EVERY] + points[-1:]],
            "tone": tone, "label": label}


def made(inputs):
    trial = inputs.json(ENTRY, "physics-trial/trial.json")
    record = json.loads((inputs.repo / "data/physics" / f"{PLACE}.json").read_text())
    scene = json.loads((inputs.repo / "data/scene" / f"{PLACE}.json").read_text())
    tracks = {name: track(body) for name, body in trial["bodies"].items()}
    hinge = record["hinges"][0]
    swung = trial["hinges"][hinge["leaf"]]["angles"][-1]
    pushed = record["moved"][0]
    drops = [drop["object"] for drop in record["drops"]]
    seconds = trial["frames"] / trial["rate"]
    carried = [hinge["leaf"], *hinge["carries"]]
    fell = {name: tracks[name][0][1] - tracks[name][-1][1] for name in drops}
    return {
        "example": f"the {PLACE}'s trial: {seconds:.0f} seconds under the Moon's gravity",
        "view": "plan", "bounds": [*plan_point(scene["floor"][0][0], scene["floor"][1][1]),
                                   *plan_point(scene["floor"][1][0], scene["floor"][0][1])],
        "steps": [
            {"label": "The room and the things that can move, where they start",
             "shapes": [{"kind": "area", "points": floor_outline(scene), "tone": "ground", "label": "the floor"},
                        *[dot(name, points[0], "base", f"{name.replace('_', ' ')}, "
                              f"{trial['bodies'][name]['mass']:.0f} kg") for name, points in tracks.items()]]},
            {"label": f"The hatch is driven open on its hinge, {swung:.0f} degrees, carrying its wheel and window",
             "shapes": [*[path(tracks[name], "c1", f"{name.replace('_', ' ')}'s way") for name in carried],
                        *[dot(name, tracks[name][-1], "c1", name.replace("_", " ")) for name in carried]]},
            {"label": "The stool is pushed and slides across the floor",
             "shapes": [path(tracks[pushed], "c2", "the stool's way"),
                        dot(pushed, tracks[pushed][-1], "c2", "the stool where it stops")]},
            {"label": "Two cases are dropped and come to rest",
             "shapes": [*[dot(name, tracks[name][-1], "c3", f"{name.replace('_', ' ')} fell {fell[name]:.2f} m")
                          for name in drops],
                        *[{"kind": "text", "points": [plan_point(tracks[name][-1][0], tracks[name][-1][2] - 0.5)],
                           "tone": "c3", "label": f"fell {fell[name]:.2f} m"} for name in drops]]}],
        "numbers": [{"label": "moving bodies", "value": len(tracks), "unit": "", "tip": "bodies the trial moves"},
                    {"label": "hatch opens", "value": round(swung), "unit": "°", "tip": "the hinge's angle at the end"},
                    {"label": "trial", "value": round(seconds, 1), "unit": "s", "tip": "how long the trial runs"}]}
