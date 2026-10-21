"""The stage a layer stage writes its layer over and judges it on (the effects and motion stages): the place's seed
with its accepted scene record written over the seed's record prims as the assembly writes it
(assembly/record.py's take_record), or the seed alone where the place has none. The design's objects stand on it by
their names (`<row>_<n>`), which the layers find by the row-kind classification (score/stages/row_kinds.py). It
imports the assembly's record module alone, so the assembly's own edits move no layer's key."""
import contextlib
import pathlib
import shutil
import tempfile

import score.stages.assembly.record as record
from score.store import PROPS_HOME

# Where a place's stage is built for a make and each gate: on disk beside the work folder's stages (/tmp on this
# machine is a tmpfs in memory, filled to its 22 GB by leftover builds on 2026-10-12), removed when the call ends.
SCRATCH = PROPS_HOME / "work/motion-scratch"
# The seed's own parts copied beside its root (as the assembly's SEED_PARTS).
SEED_PARTS = ("layers", "assets", "inputs.json")


def files(place):
    """The place's kit: the record is written over it (take_record lays the kit first). The old kits (data/kit) were
    retired (owner, 2026-10-21) and the design lays none yet, so a layer over a scene record names it missing rather
    than failing in its make."""
    return {"kit": "{data}/kit/{place}.json"}


@contextlib.contextmanager
def built(inputs):
    """The stage folder a layer is written over, for the length of a `with`: the seed, or for a place with an
    accepted scene record a copy of the seed with it written in as the assembly writes it (beside links to the
    seed's sibling places it references). The copy is removed when the `with` ends, failed or not."""
    seed = pathlib.Path(inputs["seed"])
    if "scene-record" not in inputs:
        yield seed
        return
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"layer-{seed.name}-", dir=SCRATCH) as holder:
        holder = pathlib.Path(holder)
        for other in seed.parent.iterdir():  # the places it shows, referenced as its seed's siblings
            if other.is_dir() and other.name != seed.name:
                (holder / other.name).symlink_to(other)
        folder = holder / seed.name
        folder.mkdir()
        shutil.copy2(seed / f"{seed.name}.usda", folder / f"{seed.name}.usda")
        for part in SEED_PARTS:
            if (seed / part).is_dir():
                shutil.copytree(seed / part, folder / part)
            elif (seed / part).exists():
                shutil.copy2(seed / part, folder / part)
        record.take_record(inputs, folder, seed.name)
        yield folder


def opened(folder):
    """The place's stage in a built folder, opened."""
    from pxr import Usd
    folder = pathlib.Path(folder)
    return Usd.Stage.Open(str(folder / f"{folder.name}.usda"))
