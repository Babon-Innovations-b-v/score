"""The people's after-step on the shared loop (#41; score/stages/shapes_first): `people-made@people` (free), on the
line `people`, which no place owns (shapes_first/align.NO_PLACE). Every look is a row the people layer handed the loop
(data/props/people.json), made like every model: its close-up, its Pixal3D take, the finish route and its bake, the
likeness gate; a step made outside the loop is a named failure in the row's record (`failures`), handed on with it.
This row reads the loop's ends (made.ENDS) and pixal@people, and hands each look on: made.json, {look: {"take",
"model" (the loop's baked model), "finishes" (its surfaces-parts part rows), "labelled" (its painted samples,
labelled/<take>.npz), "specs" (each library surface the bake painted on it, with its settings, as the bake's
specs.json holds it), "files" (takes/<take>/: its raw and finished Pixal3D model and its close-up, the bytes
pixal@people's takes.json names), "failures"} or {"gap": <why>}}, and each labelled take the bake painted, so the dress
rows (dress.py) lay its library surfaces on the look's body and the body rows build from the take the store keeps,
never the work folder (#26: it was lost on 2026-10-19).

Gate `made` (unknown blocks): every look the loop handed on, each gap named and the looks with named failures
counted; it fails only when no look came through, so one look's gap stops its own dress row (dress.py names it),
never the others'.
"""
import json
import pathlib
import shutil

import numpy as np

import score.stages.props.pixal_row as pixal_row
import score.stages.shapes_first.made as made
from score import contracts
from score.checks import FAIL, PASS, Verdict

LAYER = "people"
ROW = "people-made"
TAKES = "takes"  # each look's Pixal3D files (raw, finished, close-up) as pixal@people made them, kept in the store
# The loop's ends this after-step reads, and the Pixal3D row whose takes.json names the bytes it hands on.
AFTER = {**made.ENDS, "pixal": ("props-pixal", 1)}


def handed(found, bake, made_takes, out):
    """One look's hand-on: its take, finishes, its labelled take and its Pixal3D files copied into the output, or its
    gap."""
    if "gap" in found:
        return found
    if found["route"] != "prop":
        return {"gap": f"on the {found['route']} route: no painted take to dress from"}
    take = found["take"]
    labelled = pathlib.Path(bake) / "labelled" / take / f"{take}.npz"
    if not labelled.exists():
        return {"gap": f"the bake painted no labelled take {take}"}
    unlike = take_faults(take, made_takes)
    if unlike:
        return {"gap": "; ".join(unlike)}
    (out / "labelled").mkdir(exist_ok=True)
    shutil.copyfile(labelled, out / "labelled" / f"{take}.npz")
    files = out / TAKES / take
    files.mkdir(parents=True)
    for path in pixal_row.take_files(take):
        (shutil.copytree if path.is_dir() else shutil.copyfile)(path, files / path.name)
    return {"take": take, "model": found["model"], "finishes": found["finishes"], "labelled": f"labelled/{take}.npz",
            "specs": painted_specs(bake, labelled), "files": f"{TAKES}/{take}", "failures": found["failures"]}


def painted_specs(bake, labelled):
    """{library surface: its spec} of every surface the bake painted on the labelled take: a surface with the list's
    settings is named for them (route_settings.settings_name), so only the bake's specs.json resolves it."""
    specs = json.loads((pathlib.Path(bake) / "specs.json").read_text())
    with np.load(labelled) as stored:
        return {str(name): specs[str(name)] for name in stored["names"]}


def take_faults(take, made_takes):
    """Why the take's Pixal3D files in the work folder are not the ones pixal@people made (its takes.json's hashes):
    a file missing, or other bytes."""
    recorded = next((entry for entry in made_takes.values() if entry["take"] == take), None)
    if recorded is None:
        return [f"pixal@{LAYER} made no take {take}"]
    return [f"{path.name} {'missing from the work folder' if not path.exists() else 'not the bytes pixal made'}"
            for path in pixal_row.take_files(take)
            if not path.exists() or pixal_row.file_hash(path) != recorded.get(path.name)]


def make(inputs, out, seed, params):
    """made.json, labelled/<take>.npz and takes/<take>/ of every look the loop made."""
    made_takes = json.loads((pathlib.Path(inputs["pixal"]) / "takes.json").read_text())
    found = {look: handed(entry, inputs["surfaces-bake"], made_takes, out)
             for look, entry in made.made(inputs, LAYER).items()}
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
