"""A place's bake job written from git, inside the bake's make: no job file to keep or to lose (2026-10-19: the 30 job
files under the work folder went with the old disk, and every surface bake blocked on them).

    job_head(wear_dirt, specs)            the job's top-level fields: script, density, wear, dirt, seed, faces, specs
    entry_of(model, inline, labelled)     one model's make_chunky entry
    measured_turn(labelled, size)         a design entry's turn, measured over its labelled take
    refusal(model, inline)                why entry_of stops on it whatever its labelled take, or None

A model's entry is the one its surface data writes out: its design's (prepare's hand-in, compare.bake_entry: the row's
size, near density, faces and foot, written without a turn: measured_turn over its labelled take), the people line's
as written. A model the data writes no entry for fails the make, by name: a gap, never a guessed size. The routes
that wrote an entry from a kit room's laid size or an outside place's inventory row (and read the kinds' details and
the composites) went with the old kits and inventories (owner, 2026-10-21: every stage builds from the design alone).

Kept small and apart from place_line.py on purpose: the paid bake row's code version hashes it.
"""
import math

import library
import place_route
import route


# A design's take turned about up into the kit frame (measured_turn): 0 or 90 degrees, x toward -z.
TURNS = {0: [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0], 90: [0.0, 0.0, 1.0, 0.0, 1.0, 0.0, -1.0, 0.0, 0.0]}


class NoEntry(RuntimeError):
    """A model the place bakes whose entry its data does not write."""


class NoTake(NoEntry):
    """A model whose entry has no turn and no labelled take to measure one over."""


def specs_of(library_name):
    """Every library surface the people line's bake bakes with: each variant by its own name and the place's own
    names (library.by_library, library.resolved)."""
    return dict(library.by_library(library_name), **library.resolved(library_name))


def job_head(wear_dirt, specs):
    """The job's top-level fields at the scene's (wear, dirt) with its specs, at a near model's density and triangle
    budget (route.NEAR, route.CHUNKY_FACES); its out and report are the bake's own."""
    wear, dirt = wear_dirt
    return {"script": "make_chunky.py", "density": route.NEAR, "wear": wear, "dirt": dirt, "seed": 3,
            "faces": route.CHUNKY_FACES, "specs": specs}


def measured_turn(labelled, size):
    """The turn (rows of the rotation, glTF frame to the kit's) of a take whose entry its design writes without one:
    of 0 and 90 degrees about up, the one whose labelled model's footprint fits `size`'s (x wide, z deep) proportions
    best, |log(wide ratio) - log(deep ratio)| (shapes_first/align.py's rule); 0 on a tie. A box alone cannot tell 180
    from 0: the take is made from its front close-up, so 0 keeps the front the close-up drew."""
    def misfit(yaw):
        wide, _, deep = place_route.made_size(labelled, size, yaw)
        return abs(math.log(size[0] / wide) - math.log(size[2] / deep))
    return TURNS[min(TURNS, key=misfit)]


def entry_of(model, inline, labelled):
    """One model's make_chunky entry: `inline` (the surface data's own), turned by measured_turn over `labelled` (its
    labelled take) when it says no turn (module docstring)."""
    if isinstance(inline, str):
        raise NoEntry(f"no entry for {model}: the data names a job file ({inline}); write its entry out or drop it")
    if inline is None:
        raise NoEntry(f"no entry for {model}: the data writes none (a design's hand-in writes one for every model)")
    if "base" in inline:
        return dict(inline, name=model)
    if labelled is None:
        raise NoTake(f"no entry for {model}: no labelled take to measure its turn over")
    return dict(inline, name=model, base=measured_turn(labelled, inline["size"]))


def refusal(model, inline):
    """Why entry_of stops on a model whatever its labelled take, or None: entry_of's own checks, run without the take
    (a turn is measured over it in the bake, so its absence here is no refusal)."""
    try:
        entry_of(model, inline, None)
    except NoTake:
        return None
    except NoEntry as refused:
        return str(refused)
    return None
