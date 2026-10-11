"""The stage table: every stage the runner knows, in the paper's order, and world 1 as the runner reads it.

    from score import stages
    runner = stages.runner()        # world 1, the framework's store on this machine
    runner.status(["hangar", "hdoor"])
    runner.drive(stages.places(runner.world))   # every line of the world to its end (python -m score run world1)

Step 0 holds the worked example: assembly (P5) on world 1's round-three stages as unverified seeds, and complete
(P11). Terrain (the paper's Methods, "Terrain") makes every ground of the world from its plan, one world node, paid
(pictures and depth in the cloud, cleared by the runner). Each stage joins the table when it is built in its step
(docs/bible.md, architecture/components).
"""
import pathlib

from score import contracts, graph
from score.stages import assembly, complete, terrain
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[2]
WORLD1 = REPO / "data/definitions/world.json"

TERRAIN = graph.Stage("terrain", "world", terrain.make, terrain.GROUNDS, terrain.CHECKS, files=terrain.FILES,
                      paid=True, euros=terrain.EUROS)
ASSEMBLY = graph.Stage("assembly", "place", assembly.make_from_seed, contracts.OPENUSD_STAGE, assembly.CHECKS,
                       files=assembly.FILES, gatherers=assembly.GATHERERS)
COMPLETE = graph.Stage("complete", "place", complete.make_manifest, contracts.PLACE_MANIFEST, complete.CHECKS,
                       after={"assembly": ("openusd-stage", 1)})
STAGES = (TERRAIN, ASSEMBLY, COMPLETE)


def world1():
    """World 1: its record, its data in the repository and its old outputs in the work folder."""
    return graph.World.from_file(WORLD1, data=str(REPO / "data"), seeds=str(PROPS_HOME / "work"))


def places(world):
    """A world's places: one kit each in its data."""
    return sorted(path.stem for path in (pathlib.Path(world.roots["data"]) / "kit").glob("*.json"))


WORLDS = {"world1": world1}


def runner(store=None, world=None):
    """The runner over the stage table, on world 1 and the framework's store unless told otherwise."""
    return graph.Runner(STAGES, world or world1(), store or Store.default())
