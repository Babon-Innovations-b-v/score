"""The stage table: every stage the runner knows, in the paper's order, and world 1 as the runner reads it.

    from score import stages
    runner = stages.runner()        # world 1, the framework's store on this machine
    runner.status(["hangar", "hdoor"])
    runner.drive(stages.places(runner.world))   # every line of the world to its end (python -m score run world1)

Step 0 holds the worked example: assembly (P5) on world 1's round-three stages as unverified seeds, and complete
(P11). Terrain (the paper's Methods, "Terrain") makes every ground of the world from its plan, one world node, paid
(pictures and depth in the cloud, cleared by the runner). The surface stage (step 1, its overlay) is each place's
own line of rows, split to checked bake, beside the world's seed of the finish registry. Effects (experimental) makes
each staged place's effects layer from its record, which its assembly takes; effects-look renders it before and
after. Neighbours (experimental) stands the places a place's scene record shows in its assembly, each read as its
own accepted assembly. Each stage joins the table when it is built in its step (docs/bible.md, architecture/components).
"""
import dataclasses
import pathlib

from score import contracts, graph
from score.stages import assembly, complete, effects, images, surfaces, terrain
from score.stages.surfaces import bake_check
from score.stages.surfaces.surface_gates import guarded
from score.stages.assembly import neighbours
from score.stages.effects import look as effects_look
from score.stages.terrain import look
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[2]
WORLD1 = REPO / "data/definitions/world.json"

TERRAIN = graph.Stage("terrain", "world", terrain.make, terrain.GROUNDS, terrain.CHECKS, files=terrain.FILES,
                      paid=True, euros=terrain.EUROS)
# Experimental (PRD #6) until the owner reviews it: each staged place's effects layer (effects.STAGED), which its
# assembly takes.
EFFECTS = graph.Stage("effects-layer", "place", effects.make, effects.LAYER, effects.CHECKS, files=effects.files,
                      applies=lambda place: place in effects.STAGED)
ASSEMBLY = graph.Stage("assembly", "place", assembly.make_from_seed, contracts.OPENUSD_STAGE, assembly.CHECKS,
                       files=assembly.FILES, gatherers=assembly.GATHERERS,
                       after={"terrain": ("grounds", 1), "effects-layer": ("effects-layer", 1),
                              "surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                       beside={"surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                       neighbours=assembly.claiming_places)
# Experimental (PRD #6) until the owner reviews it: each place's assembly with the places its scene record shows,
# each read beside as its own accepted assembly. Complete does not read it yet: a neighbour whose assembly fails (the
# hub's) would stop every place that shows it.
NEIGHBOURS = graph.Stage("neighbours", "place", neighbours.make, contracts.OPENUSD_STAGE, neighbours.CHECKS,
                         files=neighbours.files, after={"assembly": ("openusd-stage", 1)},
                         beside={"assembly": ("openusd-stage", 1)}, neighbours=neighbours.neighbours,
                         applies=neighbours.applies)
COMPLETE = graph.Stage("complete", "place", complete.make_manifest, contracts.PLACE_MANIFEST, complete.CHECKS,
                       after={"assembly": ("openusd-stage", 1)})
# Experimental (PRD #6) until the owner reviews it: the proof place's before and after its made ground, rendered.
TERRAIN_LOOK = graph.Stage("terrain-look", "place", look.make, look.LOOK, look.CHECKS, files=look.files,
                           after={"assembly": ("openusd-stage", 1)}, paid=True, euros=look.EUROS,
                           applies=lambda place: place in look.LOOKED)
EFFECTS_LOOK = graph.Stage("effects-look", "place", effects_look.make, effects_look.LOOK, effects_look.CHECKS,
                           files=effects_look.files, after={"assembly": ("openusd-stage", 1)}, paid=True,
                           euros=effects_look.EUROS, applies=lambda place: place in effects_look.LOOKED)



def bake_checked(row):
    """surfaces-check on bake_check.py, the check's own module (a border triangle a blotch only when off every surface
    within its reach). Set here, in the table, not in surfaces/__init__.py, which is in the turntable's and SegviGen's
    code version: an edit there re-buys them. Moves into surfaces/__init__.py, and the old check leaves place_line.py,
    once their fan-out of 2026-10-12 is done."""
    if row.name != "surfaces-check":
        return row
    return dataclasses.replace(row, make=bake_check.make_check,
                               contract=contracts.Contract("surfaces-check", 1, bake_check.check_faults),
                               checks=(guarded("baked matches its surfaces", bake_check.judge_lit),
                                       guarded("triangles within budget", bake_check.judge_triangles)))


def feet_checked(row):
    """surfaces-paint with the gate "feet in one plane" beside its own (place_line.judge_feet: a take's short legs are
    stretched down before its bake, a missing leg fails by name). Set here, as bake_checked is, so the turntable's and
    SegviGen's code version does not move."""
    if row.name != "surfaces-paint":
        return row
    return dataclasses.replace(row, checks=(*row.checks, guarded("feet in one plane", surfaces.place_line.judge_feet)),
                               files=paint_files)


def paint_files(place):
    """The paint's world files: the line's, and the inventory of each place a take is made for with the resting rules,
    which it reads to tell a take laid loose on the floor or held, whose feet it levels (place_line.stands_on_feet)."""
    import stage_inputs  # tools/usd, on the path by the assembly stage's import: a place's inventory, or its kit's
    inventories = {f"inventory {entry['place']}": "{data}/inventory/" + stage_inputs.inventory_path(entry["place"]).name
                   for entry in surfaces.data.takes(place).values()}
    return {**surfaces.data.line_files(place), **inventories, "resting rules": "{data}/checks/resting.json"}


STAGES = (TERRAIN, EFFECTS, ASSEMBLY, NEIGHBOURS, COMPLETE, TERRAIN_LOOK, EFFECTS_LOOK,
          *map(feet_checked, map(bake_checked, surfaces.ROWS)))


def world1():
    """World 1: its record, its data in the repository, its old outputs in the work folder, the prop tools' home (the
    raw models, the routes' bake jobs) and the repository (the code a stage hands to a rented machine)."""
    return graph.World.from_file(WORLD1, data=str(REPO / "data"), seeds=str(PROPS_HOME / "work"),
                                 home=str(PROPS_HOME), repo=str(REPO))


def places(world):
    """A world's places: one kit each in its data (none for a world without data, the images world)."""
    if "data" not in world.roots:
        return []
    return sorted(path.stem for path in (pathlib.Path(world.roots["data"]) / "kit").glob("*.json"))


WORLDS = {"world1": world1, "images": images.image_world}
# A world whose stages are not world 1's: the images world (each job image rebuilt and proved, score/stages/images).
TABLES = {"images": images.STAGES}


def runner(store=None, world=None):
    """The runner over the stage table, on world 1 and the framework's store unless told otherwise."""
    world = world or world1()
    return graph.Runner(TABLES.get(world.name, STAGES), world, store or Store.default())
