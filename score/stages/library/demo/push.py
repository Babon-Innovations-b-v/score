"""A push by an unseen hand at work in the habitat: a kinematic box (`tools/usd/physics.write_push`) moved in a straight
line between its seconds, and the stool it meets sliding across the floor as the trial recorded it, seen from above;
the slider runs through the trial's time."""
import numpy as np

from score.stages.library.demo import _trial

ALGORITHM = "push"
EVERY = 3  # frames kept along the stool's way
MOMENTS = 13  # the slider's moments
AROUND = 0.8  # metres framed round the hand's line and the stool's way


def hand_at(push, time):
    """Where the hand's middle is at a time: held at `from`, moved in a line, held at `to`."""
    share = min(1.0, max(0.0, (time - push["start"]) / (push["end"] - push["start"])))
    return np.asarray(push["from"]) + share * (np.asarray(push["to"]) - np.asarray(push["from"]))


def box(middle, size, tone, label, name):
    """The hand's footprint as an area shape."""
    half_x, half_z = size[0] / 2, size[2] / 2
    corners = ((-half_x, -half_z), (half_x, -half_z), (half_x, half_z), (-half_x, half_z))
    return {"kind": "area", "tone": tone, "label": label, "id": name,
            "points": [_trial.plan_point(middle[0] + x, middle[2] + z) for x, z in corners]}


def moment(push, stool, way, time, index):
    return [box(hand_at(push, time), push["size"], "accent", f"the hand at {time:.1f} s", "hand"),
            {"kind": "dots", "points": [_trial.plan_point(way[index][0], way[index][2])], "r": 0.3, "tone": "c2",
             "id": stool, "label": f"{_trial.said(stool)} at {time:.1f} s"}]


def made(inputs):
    ran, the_record, the_scene = _trial.trial(inputs), _trial.record(inputs), _trial.scene(inputs)
    push, stool = the_record["pushes"][0], the_record["moved"][0]
    way, times = _trial.track(ran["bodies"][stool]), _trial.seconds(ran)
    still = next(index for index in range(len(way)) if times[index] > push["end"]
                 and all(np.linalg.norm(way[later] - way[index]) < 0.005 for later in range(index, len(way))))
    pick = [round(index * min(len(times) - 1, still + 12) / (MOMENTS - 1)) for index in range(MOMENTS)]
    slid = float(np.linalg.norm((way[-1] - way[0])[[0, 2]]))
    speed = float(np.linalg.norm(np.asarray(push["to"]) - np.asarray(push["from"])) / (push["end"] - push["start"]))
    seen = np.array([_trial.plan_point(point[0], point[2]) for point in [*way, push["from"], push["to"]]])
    low, high = seen.min(axis=0) - AROUND, seen.max(axis=0) + AROUND
    return {
        "example": f"the {_trial.PLACE}'s stool pushed across the floor, under the Moon's gravity",
        "view": "plan", "bounds": [round(float(value), 2) for value in (*low, *high)],
        "steps": [
            {"label": "The hand, an unseen box, beside the stool",
             "shapes": [_trial.floor(the_scene), *moment(push, stool, way, 0.0, 0)]},
            {"label": f"The hand moves in a line from {push['start']:g} to {push['end']:g} s",
             "shapes": [{"kind": "line", "tone": "accent", "label": "the hand's line",
                         "points": [_trial.plan_point(push["from"][0], push["from"][2]),
                                    _trial.plan_point(push["to"][0], push["to"][2])]}]},
            {"label": f"The trial: the stool slides {slid:.2f} m and stops by {times[still]:.1f} s",
             "shapes": [{"kind": "path", "tone": "c2", "label": "the stool's way, as the trial recorded it",
                         "points": [_trial.plan_point(point[0], point[2]) for point in way[:still + 1:EVERY]]}]},
            {"label": "Both at one moment", "shapes": moment(push, stool, way, times[still], still)}],
        "slider": {"label": "time", "unit": "s", "values": [round(times[index], 1) for index in pick],
                   "at": MOMENTS - 1, "shapes": [moment(push, stool, way, times[index], index) for index in pick]},
        "numbers": [
            {"label": "hand speed", "value": round(speed, 2), "unit": "m/s", "tip": "its line over its seconds"},
            {"label": "pushed for", "value": round(push["end"] - push["start"], 2), "unit": "s",
             "tip": f"from {push['start']:g} to {push['end']:g} s"},
            {"label": "stool slid", "value": round(slid, 2), "unit": "m", "tip": "from where it stood to where it stopped"},
            {"label": "stool", "value": round(ran["bodies"][stool]["mass"], 1), "unit": "kg", "tip": "its mass"}]}
