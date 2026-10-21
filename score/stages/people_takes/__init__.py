"""The people's take rows (#5; experimental): `people-take-<look>` (paid, world), a new look's close-ups and its
Pixal3D take, made by the prop route (tools/characters/maker/prop_person.py's closeup and mesh: klein's close-ups in
SOMA-X's bind pose on a characters machine, each checked for arms apart; Pixal3D on every close-up that passed,
finished here, each take checked for limbs apart, the first that passes kept). A look is an entry of
data/people/takes.json: its spec and outfit. Its own package, so a new take re-keys none of the people line's or the
bodies' rows (the people package is hashed into every body row's code version).

Once a take row is accepted, its take joins data/surfaces/people.json and the people line's hand-in to the shared loop
(data/props/people.json, data/inventory/people.json; the loop finishes it, #41) and a body row
(data/people/bodies.json) like every look.

Gates (unknown blocks): `close-ups` (at least one close-up with its arms apart), `take` (a kept take whose finished
Pixal3D model is in the output: its three files, `take/`, kept in the store, #26).
"""
import json
import pathlib
import shutil
import sys

from score import checks, contracts, graph

REPO = pathlib.Path(__file__).resolve().parents[3]
MAKER = REPO / "tools/characters/maker"
TAKES = REPO / "data/people/takes.json"
PIXAL = pathlib.Path.home() / ".farm-factory-props/work/pixal"
# A take's files as the Pixal3D batch brings them (score/stages/props/pixal_row.SUFFIXES), kept in the output's
# TAKE_FILES folder.
SUFFIXES = (".glb", "-final.glb", ".svviews")
TAKE_FILES = "take"
# Two klein close-ups on an L4 with its set-up (about 30 minutes at EUR 0.79 an hour) and two Pixal3D runs.
EUROS = 1.5
ROW = "people-take"


def make_take(inputs, out, seed, params):
    """The close-ups, their checks and the kept take (take.json) into the output."""
    sys.path.insert(0, str(MAKER))
    import prop_person
    import spec as specs
    spec = specs.read(pathlib.Path(inputs["spec"]))
    outfit, who = params["outfit"], f"{ROW}-{spec['name']}-{params['outfit']}"
    prop_person.closeup(spec, outfit, who, None, False)
    kept = prop_person.mesh(spec, outfit, who, None, False)
    folder = prop_person.folder_of(spec, outfit)
    shutil.copytree(folder / "closeup", out / "closeup")
    shutil.copy2(folder / "mesh" / "takes.json", out / "takes.json")
    stored(kept["kept"], out / TAKE_FILES)
    (out / "take.json").write_text(json.dumps({"take": kept["kept"], "spec": params["spec"], "outfit": outfit,
                                               "finished": f"{TAKE_FILES}/{kept['kept']}-final.glb"}, indent=1))


def stored(take, target):
    """The kept take's Pixal3D files (its raw model, its finished model and its close-up with its camera) copied out of
    the work folder the batch brought them to into the row's output, so the store keeps them (#26: the work folder
    was lost on 2026-10-19 with every take in it)."""
    target.mkdir(parents=True)
    for suffix in SUFFIXES:
        source = PIXAL / f"{take}{suffix}"
        (shutil.copytree if source.is_dir() else shutil.copy2)(source, target / source.name)


def take_faults(folder):
    return [] if (folder / "take.json").exists() else ["no take.json"]


def judge_closeups(output, inputs, evidence):
    found = json.loads((output / "closeup" / "checks.json").read_text())
    passing = [take for take, entry in found.items() if entry["pass"]]
    return checks.Verdict("close-ups", checks.PASS if passing else checks.FAIL,
                          f"{len(passing)} of {len(found)} close-ups with the arms apart",
                          {"passing": len(passing), "made": len(found)})


def judge_take(output, inputs, evidence):
    found = json.loads((output / "take.json").read_text())
    there = (output / found["finished"]).exists()
    return checks.Verdict("take", checks.PASS if there else checks.FAIL,
                          f"{found['take']} kept, its finished model {'in the output' if there else 'missing'}")


def guarded(name, judge):
    """A judge whose missing record answers unknown, never passes."""
    def judged(output, inputs, evidence):
        try:
            return judge(output, inputs, evidence)
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as missing:
            return checks.Verdict(name, checks.UNKNOWN, f"cannot tell: {type(missing).__name__}: {missing}")
    return checks.Check(name, judged)


TAKE = contracts.Contract(ROW, 1, take_faults)


def rows():
    """One paid world row a look of data/people/takes.json."""
    looks = json.loads(TAKES.read_text())["looks"]
    return tuple(graph.Stage(f"{ROW}-{look}", "world", make_take, TAKE,
                             (guarded("close-ups", judge_closeups), guarded("take", judge_take)),
                             files={"spec": "{repo}/" + entry["spec"], "maker": "{repo}/tools/characters/maker"},
                             params=entry, paid=True, euros=EUROS)
                 for look, entry in looks.items())


ROWS = rows()
