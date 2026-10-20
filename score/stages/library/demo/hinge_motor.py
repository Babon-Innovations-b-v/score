"""A hinge with its limits and motor at work in the habitat: the north hatch's leaf on its revolute joint
(`tools/usd/physics.write_hinge`), its limits, the time its motor (`write_drive`: an angular velocity drive, its
torque capped) is on, and the angle the trial recorded frame by frame; the slider runs through the trial's time."""
from score.stages.library.demo import _trial

ALGORITHM = "hinge_motor"
EVERY = 2  # frames kept along the recorded angle
MOMENTS = 17  # the slider's moments over the trial


def at_moment(time, angle, leaf):
    return {"kind": "dots", "points": [[round(time, 2), round(angle, 1)]], "r": 0.12, "tone": "accent", "id": "leaf",
            "label": f"{_trial.said(leaf)}, {angle:.0f}° at {time:.1f} s"}


def made(inputs):
    ran, the_record = _trial.trial(inputs), _trial.record(inputs)
    hinge = the_record["hinges"][0]
    drive, (lower, upper) = hinge["drive"], hinge["opens"]
    angles, times = ran["hinges"][hinge["leaf"]]["angles"], _trial.seconds(ran)
    end = times[-1]
    pick = [round(index * (len(times) - 1) / (MOMENTS - 1)) for index in range(MOMENTS)]
    first = next(index for index, angle in enumerate(angles) if angle >= upper - 0.5)
    return {
        "example": f"the {_trial.PLACE}'s {_trial.said(hinge['leaf']).replace(' 1', '')}, under the Moon's gravity",
        "view": "side", "bounds": [0, lower - 15, round(end, 2), upper + 15],
        "axes": {"x": "seconds", "y": "how far open, degrees"},
        "steps": [
            {"label": f"Its limits: {lower:g} to {upper:g} degrees",
             "shapes": [{"kind": "line", "points": [[0, value], [round(end, 2), value]], "tone": "warn",
                         "label": f"limit, {value:g}°"} for value in (lower, upper)]},
            {"label": f"Its motor drives {drive['speed']:g}°/s with up to {drive['torque']:g} N m, "
                      f"from {drive['start']:g} to {drive['end']:g} s",
             "shapes": [{"kind": "area", "tone": "ghost", "label": "motor on",
                         "points": [[drive["start"], lower - 10], [drive["end"], lower - 10],
                                    [drive["end"], upper + 10], [drive["start"], upper + 10]]}]},
            {"label": f"The trial: the leaf swings open and stops at its limit at {times[first]:.1f} s",
             "shapes": [{"kind": "path", "tone": "c1", "label": "the angle the trial recorded",
                         "points": [[round(times[index], 2), round(angles[index], 1)]
                                    for index in range(0, len(angles), EVERY)]}]},
            {"label": "The leaf at one moment", "shapes": [at_moment(times[first], angles[first], hinge["leaf"])]}],
        "slider": {"label": "time", "unit": "s", "values": [round(times[index], 1) for index in pick],
                   "at": min(range(MOMENTS), key=lambda rank: abs(pick[rank] - first)),
                   "shapes": [[at_moment(times[index], angles[index], hinge["leaf"])] for index in pick]},
        "numbers": [
            {"label": "opens", "value": upper - lower, "unit": "°", "tip": f"its limits, {lower:g} to {upper:g}"},
            {"label": "motor", "value": drive["speed"], "unit": "°/s", "tip": "the drive's target speed"},
            {"label": "torque", "value": drive["torque"], "unit": "N m", "tip": "the most the motor pushes with"},
            {"label": "carries", "value": len(hinge["carries"]), "unit": "",
             "tip": ", ".join(_trial.said(name) for name in hinge["carries"]) + ": held to the leaf by fixed joints"}]}
