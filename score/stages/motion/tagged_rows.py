"""A moving row's objects found by the row their own prims name (`score:row`), on the place's stage with its made ground
laid (motion@square, 2026-11-10: the terrain lays the sea as one water sheet, /square/Outside/water, tagged
score:row "sea"; the motion stage found a row's objects only by their names, `<row>` or `<row>_<n>`, and its build
laid no made ground, so the sea's row stood with no object and `designed` failed it). Kept apart from the motion
package, which other makers' code versions hash: only the table's motion row reads this file.

    grounded(inputs)                  the build the motion row's make and gates stand on (motion.built), with the
                                      terrain row's made ground laid in it as the assembly lays it (take_ground)
    objects(stage, place, row)        the prims of the place naming the row in their `score:row`, outermost first
"""
import contextlib
import pathlib
import tempfile

from score.stages import layer_base, row_kinds
from score.stages.assembly import record
from score.stages import motion

TAG = "score:row"
# The scopes a place holds other places in: a shown place's prims are that place's objects, never this one's.
SHOWN = "Places"


@contextlib.contextmanager
def grounded(inputs):
    """The place's built stage folder (motion.built) with the terrain row's made ground (its `terrain` output's
    places/<place>.usdc) held just over its base, for the length of a `with`; the build alone where the place reads no
    terrain row or the terrain made it no ground."""
    with motion.built(inputs) as source:
        source = pathlib.Path(source)
        if "terrain" not in inputs:
            yield source
        elif source != pathlib.Path(inputs["seed"]):
            record.take_ground(inputs["terrain"], source.name, source / f"{source.name}.usda")
            yield source
        else:
            with over_seed(source) as held:
                record.take_ground(inputs["terrain"], held.name, held / f"{held.name}.usda")
                yield held


@contextlib.contextmanager
def over_seed(seed):
    """A stage folder of the seed's name whose root holds the seed's root, for the length of a `with`: a place with no
    scene record builds on its seed itself, which is never written to."""
    from pxr import Sdf
    layer_base.SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"tagged-{seed.name}-", dir=layer_base.SCRATCH) as holder:
        folder = pathlib.Path(holder) / seed.name
        (folder / "layers").mkdir(parents=True)
        root = Sdf.Layer.CreateNew(str(folder / f"{seed.name}.usda"))
        root.subLayerPaths.append(str(seed / f"{seed.name}.usda"))
        root.Save()
        yield folder


def objects(stage, place, row):
    """The paths of the prims under /<place> whose `score:row` names the row, in path order: outside the layers' own
    scopes (row_kinds.NOT_OBJECTS) and the places it shows, and never inside another prim it names."""
    from pxr import Usd
    root = stage.GetPrimAtPath(f"/{place}")
    if not root:
        return []
    found = []
    walk = iter(Usd.PrimRange(root))
    for prim in walk:
        if prim.GetParent() == root and prim.GetName() in (*row_kinds.NOT_OBJECTS, SHOWN):
            walk.PruneChildren()
            continue
        tag = prim.GetAttribute(TAG)
        if tag and tag.HasAuthoredValue() and tag.Get() == row:
            found.append(prim.GetPath().pathString)
            walk.PruneChildren()
    return found
