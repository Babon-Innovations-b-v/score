"""A drop onto its target at work in the habitat: each case lifted over its target's top
(`tools/usd/physics.lifted`, its fall checked clear by `faults`) and let fall; its lowest point's height frame by frame
as the trial recorded it under the Moon's pull. The slider sets the same fall under another body's pull
(each body of the environment concept's physics, score/review/setting.py), worked out as a free fall from where it starts to where it rests (no bounce)."""
import math

from score.review import setting as settings
from score.stages.library.demo import _trial

ALGORITHM = "drop"
EVERY = 2  # frames kept along a fall
STEPS = 24  # points along a worked-out fall
TONES = ("c1", "c2")


def fall(name, start, rest, pull, tone):
    """A free fall from `start` to `rest` metres under `pull`, as a path on the height chart."""
    lands = math.sqrt(2 * (start - rest) / pull)
    times = [lands * step / STEPS for step in range(STEPS + 1)]
    return {"kind": "path", "tone": tone, "id": f"fall-{name}", "label": f"{_trial.said(name)} lands at {lands:.2f} s",
            "points": [[round(time, 3), round(start - pull * time * time / 2, 3)] for time in times]}


def made(inputs):
    ran, the_record = _trial.trial(inputs), _trial.record(inputs)
    times = _trial.seconds(ran)
    drops = {drop["object"]: drop for drop in the_record["drops"]}
    lowest = {name: ran["bodies"][name]["lowest"] for name in drops}
    rest = {name: heights[-1] for name, heights in lowest.items()}
    settled = max(next(index for index, height in enumerate(heights) if abs(height - heights[-1]) < 0.002)
                  for heights in lowest.values())
    shown = times[min(len(times) - 1, settled + 12)]
    pulls = sorted(((body["body"], body["gravity"]) for body in settings.now()["bodies"]), key=lambda item: item[1])
    at = next(index for index, (body, _) in enumerate(pulls) if body == the_record["body"])
    top = max(heights[0] for heights in lowest.values())
    return {
        "example": f"the {_trial.PLACE}'s two dropped cases, under the Moon's gravity",
        "view": "side", "bounds": [0, -0.1, round(shown, 2), round(top + 0.2, 2)],
        "axes": {"x": "seconds", "y": "lowest point over the floor, m"},
        "steps": [
            {"label": "Each case lifted over its target",
             "shapes": [*[{"kind": "line", "tone": "ground", "points": [[0, round(rest[name], 2)],
                                                                        [round(shown, 2), round(rest[name], 2)]],
                           "label": f"{'the floor' if drop['onto'] == 'floor' else _trial.said(drop['onto'])}'s top"}
                          for name, drop in drops.items()],
                        *[{"kind": "dots", "points": [[0, round(lowest[name][0], 2)]], "r": 0.04, "tone": tone,
                           "label": f"{_trial.said(name)}, {drops[name]['over']:g} m over its target"}
                          for name, tone in zip(drops, TONES)]]},
            {"label": f"The trial: each falls and comes to rest by {times[settled]:.1f} s",
             "shapes": [{"kind": "path", "tone": tone, "label": f"{_trial.said(name)}, as the trial recorded it",
                         "points": [[round(times[index], 2), round(lowest[name][index], 3)]
                                    for index in range(0, settled + 1, EVERY)]}
                        for name, tone in zip(drops, TONES)]},
            {"label": f"The same fall worked out under the {the_record['body'].capitalize()}'s pull",
             "shapes": [fall(name, lowest[name][0], rest[name], ran["gravity"], "c3") for name in drops]}],
        "slider": {"label": "pull", "unit": "m/s²", "values": [pull for _, pull in pulls], "at": at,
                   "shapes": [[fall(name, lowest[name][0], rest[name], pull, "c3") for name in drops]
                              for _, pull in pulls]},
        "numbers": [
            {"label": "pull", "value": round(ran["gravity"], 2), "unit": "m/s²",
             "tip": f"the {the_record['body'].capitalize()}'s, the scene's gravity"},
            *[{"label": _trial.said(name).rstrip(" 0123456789"), "value": drops[name]["over"], "unit": "m",
               "tip": f"{_trial.said(name)} lifted this far over its target"} for name in drops]]}
