"""The stage table: every stage the runner knows, in the paper's order, and world 1 as the runner reads it.

    from score import stages
    runner = stages.runner()        # world 1, the framework's store on this machine
    runner.status(["hangar", "hdoor"])
    runner.drive(stages.places(runner.world))   # every line of the world to its end (python -m score run world1)

Step 0 holds the worked example: assembly (P5) on world 1's round-three stages as unverified seeds, and complete
(P11). Terrain (the paper's Methods, "Terrain") makes every ground of the world from its plan, one world node, paid
(pictures and depth in the cloud, cleared by the runner). The surface stage (step 1, its overlay) is each place's
own line of rows, split to checked bake, beside the world's seed of the finish registry. Effects (experimental) makes
the proof place's effects layer from its record, which its assembly takes; effects-look renders it before and after. Each stage joins the table
when it is built in its step (docs/bible.md, architecture/components).
"""
import pathlib

from score import contracts, graph
from score.stages import assembly, complete, effects, surfaces, terrain
from score.stages.effects import look as effects_look
from score.stages.terrain import look
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[2]
WORLD1 = REPO / "data/definitions/world.json"

TERRAIN = graph.Stage("terrain", "world", terrain.make, terrain.GROUNDS, terrain.CHECKS, files=terrain.FILES,
                      paid=True, euros=terrain.EUROS)
# Experimental (PRD #6) until the owner reviews it: the proof place's effects layer, which its assembly takes.
EFFECTS = graph.Stage("effects", "place", effects.make, effects.LAYER, effects.CHECKS, files=effects.files,
                      applies=lambda place: place in effects.STAGED)
ASSEMBLY = graph.Stage("assembly", "place", assembly.make_from_seed, contracts.OPENUSD_STAGE, assembly.CHECKS,
                       files=assembly.FILES, gatherers=assembly.GATHERERS,
                       after={"terrain": ("grounds", 1), "effects": ("effects-layer", 1)})
COMPLETE = graph.Stage("complete", "place", complete.make_manifest, contracts.PLACE_MANIFEST, complete.CHECKS,
                       after={"assembly": ("openusd-stage", 1)})
# Experimental (PRD #6) until the owner reviews it: the proof place's before and after its made ground, rendered.
TERRAIN_LOOK = graph.Stage("terrain-look", "place", look.make, look.LOOK, look.CHECKS, files=look.files,
                           after={"assembly": ("openusd-stage", 1)}, paid=True, euros=look.EUROS,
                           applies=lambda place: place in look.LOOKED)
EFFECTS_LOOK = graph.Stage("effects-look", "place", effects_look.make, effects_look.LOOK, effects_look.CHECKS,
                           files=effects_look.files, after={"assembly": ("openusd-stage", 1)}, paid=True,
                           euros=effects_look.EUROS, applies=lambda place: place in effects_look.LOOKED)
STAGES = (TERRAIN, EFFECTS, ASSEMBLY, COMPLETE, TERRAIN_LOOK, EFFECTS_LOOK, *surfaces.ROWS)


def world1():
    """World 1: its record, its data in the repository, its old outputs in the work folder, the prop tools' home (the
    raw models, the routes' bake jobs) and the repository (the code a stage hands to a rented machine)."""
    return graph.World.from_file(WORLD1, data=str(REPO / "data"), seeds=str(PROPS_HOME / "work"),
                                 home=str(PROPS_HOME), repo=str(REPO))


def places(world):
    """A world's places: one kit each in its data."""
    return sorted(path.stem for path in (pathlib.Path(world.roots["data"]) / "kit").glob("*.json"))


WORLDS = {"world1": world1}


def runner(store=None, world=None):
    """The runner over the stage table, on world 1 and the framework's store unless told otherwise."""
    return graph.Runner(STAGES, world or world1(), store or Store.default())
