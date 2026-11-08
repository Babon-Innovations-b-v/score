"""A place's bake job written from git, inside the bake's make: no job file to keep or to lose (2026-10-19: the 30 job
files under the work folder went with the old disk, and every surface bake blocked on them).

    job_head(wear_dirt, specs)            the job's top-level fields: script, density, wear, dirt, seed, faces, specs
    entry_of(model, inline, labelled)     one model's make_chunky entry, laid within its row (laid_size)
    measured_turn(labelled, size)         a design entry's turn, measured over its labelled take
    refusal(model, inline)                why entry_of stops on it whatever its labelled take, or None

A model's entry is the one its surface data writes out: its design's (prepare's hand-in, compare.bake_entry: the row's
size, near density, faces and foot, written without a turn: measured_turn over its labelled take), the people line's
as written. A model the data writes no entry for fails the make, by name: a gap, never a guessed size. The routes
that wrote an entry from a kit room's laid size or an outside place's inventory row (and read the kinds' details and
the composites) went with the old kits and inventories (owner, 2026-10-21: every stage builds from the design alone).

Kept small and apart from place_line.py on purpose: the paid bake row's code version hashes it.
"""
import json
import math
import pathlib

import numpy as np

import library
import place_route
import route


# A design's take turned about up into the kit frame (measured_turn): 0 or 90 degrees, x toward -z.
TURNS = {0: [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0], 90: [0.0, 0.0, 1.0, 0.0, 1.0, 0.0, -1.0, 0.0, 0.0]}
PERSON_KIND = "person"  # a person's take in its surface data (the people line's looks)


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


def measured_turn(labelled, size, own=False):
    """The turn (rows of the rotation, glTF frame to the kit's) of a take whose entry its design writes without one:
    of 0 and 90 degrees about up, the one whose labelled model's footprint fits `size`'s (x wide, z deep) proportions
    best, |log(wide ratio) - log(deep ratio)| (shapes_first/align.py's rule); 0 on a tie. A box alone cannot tell 180
    from 0: the take is made from its front close-up, so 0 keeps the front the close-up drew. A take laid at its own
    proportions (`own`: laid_size's slender row or code build) that stands on its longest side while its row lies
    (`lies`) is laid by its row instead (tumble.square_turn: its oriented box's sides on the row's): a row's long side
    runs along the wall or floor it is on, never up, unless the row stands (hangar's wall pipes, 0.4 by 32 by 0.4 m
    run along their wall, built up their receding picture 22.7 m tall, stood from 10 to 32.7 m in a 15 m hangar; #36,
    2026-10-31)."""
    if own and lies(place_route.made_size(labelled, size, 0), size):
        import tumble
        turn = tumble.square_turn(take_points(labelled), size, keep_up=False)  # its up chosen by its row, laid down
        return [round(float(value), 6) for value in turn.reshape(-1)]

    def misfit(yaw):
        wide, _, deep = place_route.made_size(labelled, size, yaw)
        return abs(math.log(size[0] / wide) - math.log(size[2] / deep))
    return TURNS[min(TURNS, key=misfit)]


def lies(own, size):
    """Whether a take standing on its longest side (`own`: its kit size unturned, x wide, y tall, z deep) is for a row
    (`size`, kit) whose longest side is level: its row lies."""
    return own[1] >= max(own[0], own[2]) and size[1] < max(size[0], size[2])


def take_points(labelled):
    """The labelled take's vertices (its parts, in the finished model's glTF frame)."""
    import trimesh
    return np.vstack([trimesh.load(path, force="mesh", process=False).vertices
                      for path in sorted(pathlib.Path(labelled).glob("*.ply"))])


def turned_size(labelled, size, base):
    """The labelled take's size in the kit frame laid by `base` (nine numbers, rows), scaled as one so its longest side
    is `size`'s (place_route.made_size, whose quarter turns about up it gives exactly)."""
    found = np.ptp(take_points(labelled) @ np.array(base, float).reshape(3, 3).T, axis=0)
    scale = max(size) / max(found)
    return [round(float(side * scale), 3) for side in found]


def entry_of(model, inline, labelled, built=False, person=False):
    """One model's make_chunky entry: `inline` (the surface data's own), turned by measured_turn over `labelled` (its
    labelled take) when it says no turn (module docstring), a person's by person_turn (his raw take's pose), laid at
    laid_size; `built`: its take is a code build (code_built); `person`: its row is a person (drawn_person), whose
    width follows his take's own for his row's height (person_size)."""
    if isinstance(inline, str):
        raise NoEntry(f"no entry for {model}: the data names a job file ({inline}); write its entry out or drop it")
    if inline is None:
        raise NoEntry(f"no entry for {model}: the data writes none (a design's hand-in writes one for every model)")
    if "base" in inline:
        return dict(inline, name=model)
    if labelled is None:
        raise NoTake(f"no entry for {model}: no labelled take to measure its turn over")
    base = person_turn(labelled) if person else \
        measured_turn(labelled, inline["size"], built or slender(inline["size"]))
    size = person_size(inline["size"], own_ratio(labelled, inline["size"], base)) if person and not built \
        else inline["size"]
    return dict(inline, name=model, base=base, size=laid_size(labelled, size, base, built, person))


def own_ratio(labelled, size, base):
    """The labelled take's own width over its height, turned by `base` (place_route.made_size)."""
    wide, tall, _ = turned_size(labelled, size, base)
    return wide / tall


def person_turn(labelled):
    """A person's turn into the kit frame (rows): the finish's stand undone (labels.finish_turn of the take its
    labelled folder is named for), so he stands in his raw take's own pose, its front the close-up's. The stand set an
    A-pose body upright by its box, a few degrees leaned and a quarter turned off his front: the people line's pilot,
    so baked, outline 0.465 against his close-up; laid in his raw pose 0.917 (#36, 2026-10-31)."""
    import labels
    return [round(float(value), 6) for value in labels.finish_turn(labelled.name).T.reshape(-1)]


def person_size(size, own):
    """A person's kit size (x wide, y tall, z deep): his take's `own` width over height for his row's height and its
    depth, never squeezed to the row's width nor stretched to his SAM 3 box (a seated pilot's box holds his chair:
    widened 0.5 to 1.205 m, his 6 degree lean read 14; an A-pose officer, his arms out, squeezed into 0.5 m,
    2026-10-29)."""
    _, tall, deep = (float(side) for side in size)
    return [round(tall * own, 3), tall, deep]


def off(ratio, other):
    """How far one ratio is from another, the larger over the smaller less one (the model gate's spread)."""
    return max(ratio / other, other / ratio) - 1


def drawn_row(take, inventories):
    """(the row whose prop object is `take`, its hand-in's rows) from the hand-ins (`inventories`, prepare's: its rows
    and objects), or (None, [])."""
    for path in inventories:
        if not pathlib.Path(path).is_file():
            continue
        record = json.loads(pathlib.Path(path).read_text())
        rows = {row["id"]: row for row in record.get("rows", [])}
        for row, entry in record.get("objects", {}).items():
            if entry.get("take") == take and row in rows:
                return rows[row], list(rows.values())
    return None, []


def drawn_person(take, inventories, inputs):
    """Whether the take's row in the hand-ins (drawn_row) is a person (tumble.person), or its surface data makes the
    take one (person_take): what entry_of lays at person_size."""
    import tumble
    row, _ = drawn_row(take, inventories)
    return tumble.person(row or {}) or person_take(take, inputs)


def person_take(take, inputs):
    """Whether the surface data among `inputs` makes `take` a person (its `kind`, as the people line writes each
    look's take: score/stages/people_rows.py), whose rows carry no route and no hand-in objects (drawn_row finds none:
    the people line's looks were squeezed to their rows' 0.5 m, their arms out, #36 2026-10-31)."""
    surfaces = inputs.get("surfaces")
    return bool(surfaces) and json.loads(pathlib.Path(surfaces).read_text()).get("takes", {}).get(
        take, {}).get("kind") == PERSON_KIND


def code_built(take, home):
    """Whether `take` in the props `home`'s work/pixal is a code build: its mark (thin_straight's and flat_sheet's
    code.json) names route "code"."""
    mark = code_mark(take, home)
    return mark.exists() and json.loads(mark.read_text()).get("route") == "code"


def code_mark(take, home):
    """The code build mark of `take` under the props `home` (there or not)."""
    return pathlib.Path(home) / "work" / "pixal" / f"{take}.svviews" / "code.json"


def slender(size):
    """The model gate's slender rule on a kit size (tools/props/gates/model.py shape_class: its middle side under
    SLENDER_SHARE of its longest)."""
    smallest, middle, largest = sorted(float(side) for side in size)
    return largest > 0 and middle / largest < model_gate().SLENDER_SHARE


def model_gate():
    """tools/props/gates/model.py, loaded by its path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("model_gate", place_route.HERE.parent / "gates" / "model.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    return gate


def laid_size(labelled, size, base, built=False, person=False):
    """A design entry's size in the kit frame (2026-11-08, #10: the plan wins on space, the model on shape): a
    Pixal3D take at its labelled take's own proportions turned by `base`, scaled as one to the largest that fits
    within its row's `size` (fitted_size), never stretched side by side to it: the bake stretched 264 of 386 takes more
    than 20% off their own shape so, old_station's connecting tunnel (3 by 0.86 by 1.59 m) to its 3 by 1.5 by 1.5 m
    row, its outline 0.70 as made and 0.466 stretched. A slender row or a code build (`built`) keeps its take's own
    proportions with its longest side the row's (turned_size): a thin run's box is its thickness on its two short
    sides, so fitting a sagging string side by side to its 8 by 0.01 by 0.01 crushed its sag flat (2026-10-26), and a
    code build's section is its picture's where its box's cannot show it (airlock's locker lamp, built 0.046 m across,
    fitted to its 0.4 by 0.1 by 0.1 row: outline 0.813 built, 0.409 baked, 2026-10-29). A `person` keeps `size`
    (person_size: his own width for his row's height)."""
    if built or slender(size):
        return turned_size(labelled, size, base)
    if person:
        return size
    return fitted_size(labelled, size, base)


def fitted_size(labelled, size, base):
    """The labelled take's size in the kit frame laid by `base` (nine numbers, rows), scaled as one to the largest
    that fits within `size` (fit_within)."""
    return fit_within(np.ptp(take_points(labelled) @ np.array(base, float).reshape(3, 3).T, axis=0), size)


def fit_within(found, size):
    """`found` (a model's sides) scaled as one to the largest that fits within `size`, side for side."""
    found = np.maximum(np.asarray(found, float), 1e-9)
    scale = float(np.min(np.asarray(size, float) / found))
    return [round(float(side * scale), 3) for side in found]


def refitted(entries, written, labelled, built=False, person=False):
    """`entries` with each Pixal3D model the bake's stand measured (its `stood`: route_bake.stood_square and
    squared_again turn a tumbled take square) laid again within its row (its `written` entry's size) at its turn's
    own proportions (fitted_size), so a take turned square is never stretched to the size its tumbled pose fitted; a
    code build's (`built`), a person's (`person`), a slender row's and an entry written with its turn keep theirs."""
    if built or person:
        return entries
    found = {}
    for model, entry in entries.items():
        row = written.get(model) if isinstance(written.get(model), dict) else {}
        fits = "stood" in entry and "base" not in row and row.get("size") and not slender(row["size"])
        found[model] = dict(entry, size=fitted_size(labelled, row["size"], entry["base"])) if fits else entry
    return found


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
