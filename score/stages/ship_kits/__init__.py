"""The ship-kit stage: a ship place's shell kit (its code-built pieces: wall bands, deck and ceiling plates, light
strips, door leaves, grates, frame ribs, windows), baked with the material library on rented cards
(tools/props/cloud/library_bake.py), run by the runner as a paid node `ship_kit@<place>` of its own table.

    .venv/bin/python -m score.stages.ship_kits run <place> [<place> ...]
    .venv/bin/python -m score.stages.ship_kits status <place> [<place> ...]

tools/props/scene/ship_kit.py writes the place's whole layout from its plan and inventory; the stage keeps its code
pieces only (a row the inventory makes by the prop route comes from its own take, and route.py plan refuses it as
"generated kinds with no labelled parts"); route.py plan sorts them into make_kit.py jobs; library_bake.py runs them.
The layout, the plan and the made models with make_kit's reports are the output. route.py's `layout` and `install`
then put the kit in place (data/kit/<place>.json), in one push for every ship place.

The gates are the late-bake stage's: `made` (every planned model has its model and a report with triangles) and
`surfaces` (every slot of every made model is a library variant or one of its printed pictures).
"""
import json
import os
import pathlib
import subprocess

from score import checks, contracts, graph
from score.stages import late_bake
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
# The ledger's kit bakes: 0.09 to 0.14 a place's jobs on one card, rounded up.
EUROS = 0.3


def code_only(layout, inventory):
    """The layout less every piece of a row the inventory makes by the prop route (kind `generate`)."""
    made = {f"{layout['room']}_{row['id']}" for row in inventory["rows"] if row["kind"] == "generate"}
    return dict(layout, pieces=[piece for piece in layout["pieces"] if piece["kind"] not in made],
                kinds={kind: entry for kind, entry in layout["kinds"].items() if kind not in made},
                counts={kind: count for kind, count in layout["counts"].items() if kind not in made})


def make_kit(inputs, out, seed, params):
    """Lay the place's shell, plan its code models and bake them on rented cards; the models into out/made."""
    room = json.loads(pathlib.Path(inputs["inventory"]).read_text())["place"]
    full = out / "layout-full.json"
    subprocess.run([str(PROPS_PYTHON), str(inputs["ship kit"]), room, str(full), str(inputs["plan"]),
                    str(inputs["inventory"])], check=True)
    layout = code_only(json.loads(full.read_text()), json.loads(pathlib.Path(inputs["inventory"]).read_text()))
    (out / "layout.json").write_text(json.dumps(layout, indent=1))
    subprocess.run([str(PROPS_PYTHON), str(inputs["route"]), "plan", str(out / "layout.json"), str(out)], check=True)
    jobs = sorted(out.glob("job-kit-*.json"))
    for job in jobs:
        spec = json.loads(job.read_text())
        spec["out"] = str(out / "made")
        job.write_text(json.dumps(spec, indent=1))
    if jobs:
        subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/library_bake.py"), *map(str, jobs), "--who",
                        f"score ship_kit stage ({room}, seed {seed})"], check=True, env=dict(os.environ))
    (out / "made").mkdir(exist_ok=True)


SHIP_KIT = contracts.Contract("ship-kit", 1, late_bake.late_faults, {"length": "metre", "up axis": "Y"})


def files(place):
    """The place's plan and inventory, the kit layout script and the route's and library's files."""
    return {"plan": "{data}/plans/" + f"{place}.json", "inventory": "{data}/inventory/" + f"{place}.json",
            "ship kit": "{repo}/tools/props/scene/ship_kit.py", "room kit": "{repo}/tools/props/scene/room_kit.py",
            "library": "{repo}/data/library/materials.json", "pictures": "{repo}/data/library/pictures",
            "route": "{repo}/tools/props/library/route.py", "sorter": "{repo}/tools/props/library/sorter.py",
            "pipeline failures": "{repo}/data/library/pipeline_failures.json",
            "make_kit": "{repo}/tools/props/library/inside/make_kit.py",
            "pieces": "{repo}/tools/props/library/inside/pieces.py",
            "ship pieces": "{repo}/tools/props/library/inside/pieces_ship.py"}


STAGE = graph.Stage("ship_kit", "place", make_kit, SHIP_KIT,
                    (checks.Check("made", late_bake.judge_made), checks.Check("surfaces", late_bake.judge_surfaces)),
                    files=files, paid=True, euros=EUROS)


def runner(store=None):
    """The runner over this stage alone, on environment 1 with the repository as a root."""
    from score.stages import world1
    world = world1()
    world = graph.Environment(world.name, world.seed, dict(world.roots, repo=str(REPO)))
    return graph.Runner((STAGE,), world, store or Store.default())
