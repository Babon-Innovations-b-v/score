"""The late-bake stage: a code-built kit's pieces laid after its run (route.py late-plan), baked with the material
library on rented cards (tools/props/cloud/library_bake.py), run by the runner as a paid node `late_bake@<room>`.

    .venv/bin/python -m score.stages.late_bake run <room> [<room> ...]
    .venv/bin/python -m score.stages.late_bake status <room> [<room> ...]

A room's kit script (KITS) writes its layout; route.py's late-plan sorts the pieces that name a `model` not made yet
(those in the room's made folder are made) into make_kit.py jobs, and library_bake.py runs them; the made models,
the layout, the plan and make_kit's reports are the output. The route's own `late-lay` puts the output's pieces into
the room's kit (data/kit/<room>.json) afterwards.

The gates read make_kit's reports: `made` (every planned model has its model and a report with triangles) and
`surfaces` (every slot of every made model is a library variant, data/library/materials.json, or one of its printed
pictures, data/library/pictures: each part takes exactly one surface from the shared library).
"""
import json
import os
import pathlib
import shutil
import subprocess

from score import checks, contracts, graph
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
# Each room's kit script (writes the layout) and the folder of its late models made before; the stage's files name the
# camp's, the one room it bakes for now.
KITS = {"camp": {"script": "{repo}/tools/props/scene/camp_kit.py", "made": "{seeds}/place/camp-late1/made"}}
# One card at most an hour for a few make_kit jobs (a late bake of three models took 2 minutes, 2026-10-09).
EUROS = 2.0


def make_late(inputs, out, seed, params):
    """Write the room's layout, plan its late pieces and bake them on rented cards; the models into out/made."""
    layout = out / "layout.json"
    subprocess.run([str(PROPS_PYTHON), str(inputs["script"]), str(layout)], check=True)
    route = REPO / "tools/props/library/route.py"
    subprocess.run([str(PROPS_PYTHON), str(route), "late-plan", str(layout), str(out), str(inputs["made"])], check=True)
    jobs = sorted(out.glob("job-*.json"))
    for job in jobs:
        spec = json.loads(job.read_text())
        spec["out"] = str(out / "made")
        job.write_text(json.dumps(spec, indent=1))
    if jobs:
        subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/library_bake.py"), *map(str, jobs), "--who",
                        f"score late_bake stage (seed {seed})"], check=True, env=dict(os.environ))
    (out / "made").mkdir(exist_ok=True)


def late_faults(folder):
    """Why a folder is not a late bake, or [] when it is."""
    return [f"no {name}" for name in ("layout.json", "plan.json", "made") if not (folder / name).exists()]


LATE_MODELS = contracts.Contract("late-models", 1, late_faults, {"length": "metre", "up axis": "Y"})


def reports(output):
    """{model: make_kit's report entry} from every report in the made folder."""
    found = {}
    for path in sorted((output / "made").glob("report*.json")):
        found.update(json.loads(path.read_text()).get("pieces", {}))
    return found


def judge_made(output, inputs, evidence):
    """Every planned model has its model file and a report with triangles."""
    planned = sorted(json.loads((output / "plan.json").read_text())["models"])
    found = reports(output)
    missing = [name for name in planned if not (output / "made" / f"{name}.gltf").exists()
               or not found.get(name, {}).get("triangles")]
    answer = checks.FAIL if missing else checks.PASS
    reason = f"{len(planned) - len(missing)} of {len(planned)} planned models made" + (
        f"; missing {', '.join(missing)}" if missing else "")
    return checks.Verdict("made", answer, reason, {"planned": len(planned), "missing": len(missing)},
                          {"missing": "lower"}, tuple(missing))


def library_names():
    """Every library variant and printed picture by name."""
    library = json.loads((REPO / "data/library/materials.json").read_text())
    names = {variant for family in library["families"].values() for variant in family.get("variants", {})}
    return names | {path.stem for path in (REPO / "data/library/pictures").glob("*.png")}


def judge_surfaces(output, inputs, evidence):
    """Every slot of every made model is one of the shared library's surfaces."""
    names = library_names()
    foreign = sorted({f"{model}: {slot}" for model, entry in reports(output).items()
                      for slot in entry.get("slots", []) if slot not in names})
    answer = checks.FAIL if foreign else checks.PASS
    reason = "every slot a library surface" if not foreign else f"{len(foreign)} slots off the library: " + ", ".join(
        foreign[:8])
    return checks.Verdict("surfaces", answer, reason, {"foreign": len(foreign)}, {"foreign": "lower"}, tuple(foreign))


STAGE = graph.Stage("late_bake", "place", make_late, LATE_MODELS,
                    (checks.Check("made", judge_made), checks.Check("surfaces", judge_surfaces)),
                    files={"script": KITS["camp"]["script"], "made": KITS["camp"]["made"],
                           "library": "{repo}/data/library/materials.json", "pictures": "{repo}/data/library/pictures",
                           "route": "{repo}/tools/props/library/route.py",
                           "make_kit": "{repo}/tools/props/library/inside/make_kit.py",
                           "pieces": "{repo}/tools/props/library/inside/pieces.py"},
                    paid=True, euros=EUROS)


def runner(store=None):
    """The runner over this stage alone, on world 1 with the repository as a root."""
    from score.stages import world1
    world = world1()
    world = graph.World(world.name, world.seed, dict(world.roots, repo=str(REPO)))
    return graph.Runner((STAGE,), world, store or Store.default())
