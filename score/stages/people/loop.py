"""The people's after-step on the shared loop (#41; score/stages/shapes_first): `people-made@people` (free), on the
line `people`, which no place owns (shapes_first/align.NO_PLACE). Every look is a row the people layer handed the loop
(data/props/people.json), made like every model: its close-up, its Pixal3D take, the finish route and its bake, the
likeness gate; a step made outside the loop is a named failure in the row's record (`failures`), handed on with it.
This row reads the loop's ends (made.ENDS) and hands each look on: made.json, {look: {"take", "model" (the loop's
baked model), "finishes" (its surfaces-parts part rows), "labelled" (its painted samples, labelled/<take>.npz),
"failures"} or {"gap": <why>}}, and each labelled take the bake painted, so the dress rows (dress.py) lay its library
surfaces on the look's body.

Gate `made` (unknown blocks): every look the loop handed on, each gap named and the looks with named failures
counted; it fails only when no look came through, so one look's gap stops its own dress row (dress.py names it),
never the others'.
"""
import json
import pathlib
import shutil

import score.stages.shapes_first.made as made
from score import contracts
from score.checks import FAIL, PASS, Verdict

LAYER = "people"
ROW = "people-made"


def handed(found, bake, out):
    """One look's hand-on: its take, finishes and its labelled take copied into the output, or its gap."""
    if "gap" in found:
        return found
    if found["route"] != "prop":
        return {"gap": f"on the {found['route']} route: no painted take to dress from"}
    take = found["take"]
    labelled = pathlib.Path(bake) / "labelled" / take / f"{take}.npz"
    if not labelled.exists():
        return {"gap": f"the bake painted no labelled take {take}"}
    (out / "labelled").mkdir(exist_ok=True)
    shutil.copyfile(labelled, out / "labelled" / f"{take}.npz")
    return {"take": take, "model": found["model"], "finishes": found["finishes"], "labelled": f"labelled/{take}.npz",
            "failures": found["failures"]}


def make(inputs, out, seed, params):
    """made.json and labelled/<take>.npz of every look the loop made."""
    found = {look: handed(entry, inputs["surfaces-bake"], out) for look, entry in made.made(inputs, LAYER).items()}
    (out / "made.json").write_text(json.dumps(found, indent=1))


def faults(folder):
    return [] if (folder / "made.json").exists() else ["no made.json"]


CONTRACT = contracts.Contract(ROW, 1, faults)


def judge_made(output, inputs, evidence):
    """Every look handed on, its gaps named: fails only when none came through."""
    found = json.loads((output / "made.json").read_text())
    gaps = [f"{look}: {entry['gap']}" for look, entry in sorted(found.items()) if "gap" in entry]
    through = len(found) - len(gaps)
    failed = sum(1 for entry in found.values() if entry.get("failures"))
    return Verdict("made", PASS if through else FAIL,
                   f"{through} of {len(found)} looks made by the loop, {failed} with steps named made outside it",
                   {"gaps": len(gaps), "made": through, "named_failures": failed}, {"gaps": "lower"}, tuple(gaps[:40]))
