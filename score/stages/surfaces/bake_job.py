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
import json
import math
import pathlib

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


def entry_of(model, inline, labelled, built=False, box=None, kept=None, person=False):
    """One model's make_chunky entry: `inline` (the surface data's own), turned by measured_turn over `labelled` (its
    labelled take) when it says no turn (module docstring); `built`: its take is a code build (code_built); `box`: its
    row's SAM 3 box on its concept (drawn_row), which a Pixal3D take's width against its height follows (boxed);
    `kept`, `person`: the guard list's word on its row (tumble.keeps_pose, tumble.person), which boxed follows."""
    if isinstance(inline, str):
        raise NoEntry(f"no entry for {model}: the data names a job file ({inline}); write its entry out or drop it")
    if inline is None:
        raise NoEntry(f"no entry for {model}: the data writes none (a design's hand-in writes one for every model)")
    if "base" in inline:
        return dict(inline, name=model)
    if labelled is None:
        raise NoTake(f"no entry for {model}: no labelled take to measure its turn over")
    base = measured_turn(labelled, inline["size"])
    size = inline["size"] if built else boxed(inline["size"], box, own_ratio(labelled, inline["size"], base), kept,
                                              person)
    return dict(inline, name=model, base=base, size=laid_size(labelled, size, base, built))


def own_ratio(labelled, size, base):
    """The labelled take's own width over its height, turned by `base` (place_route.made_size)."""
    wide, tall, _ = place_route.made_size(labelled, size, 90 if base == TURNS[90] else 0)
    return wide / tall


def boxed(size, box, own, kept=None, person=False):
    """A Pixal3D take's kit size (x wide, y tall, z deep): where its row's SAM 3 `box` ([left, top, right, bottom]
    pixels) disagrees with the row's width over height by more than the model gate's SPREAD_LIMIT and its take's `own`
    width over height agrees with the box within it (the picture and the model both against the row), its width at
    the take's own ratio to its height; its height and depth, which a picture seen from above cannot show, as the row
    says. A size wider than tall or deepest, no box, or one source alone against the row, as it is (owner, 2026-10-29,
    "Yes, land the rule"). Of the 61 rows it changed with the height moving too, 22 were wrong against their pictures,
    each a height grown from a top seen from above (galley's stove top 0.05 to 0.32 m, the hangar's crane 2 to 6 m,
    old_station's modules taller than round); with only the width moving, 34 change, 5 of them wrong (3 doors widened
    by their frames, base's square module, camp's computer tower), 2026-10-29. A row the guard list keeps (`kept`,
    tumble.keeps_pose: hanging, lying, leaning, cable, ground debris) is left out, as it is; a person (`person`) keeps
    its take's own width for the row's height, never squeezed to the row's width nor stretched to its box (a seated
    pilot's box holds his chair: widened 0.5 to 1.205 m, his 6 degree lean read 14; an A-pose officer, his arms out,
    squeezed into 0.5 m, 2026-10-29)."""
    wide, tall, deep = (float(side) for side in size)
    if person and own:
        return [round(tall * own, 3), tall, deep]
    if kept or not box or not own or box[2] <= box[0] or box[3] <= box[1]:
        return size
    drawn, said, limit = (box[2] - box[0]) / (box[3] - box[1]), wide / tall, model_gate().SPREAD_LIMIT
    if deep > max(wide, tall) or wide > tall or off(drawn, said) <= limit or off(own, drawn) > limit:
        return size
    return [round(tall * own, 3), tall, deep]


def off(ratio, other):
    """How far one ratio is from another, the larger over the smaller less one (the model gate's spread)."""
    return max(ratio / other, other / ratio) - 1


def drawn_row(take, inventories):
    """(the row whose prop object is `take`, its hand-in's rows) from the hand-ins (`inventories`, prepare's: its rows
    and objects; the row holds its SAM 3 `box`), or (None, [])."""
    for path in inventories:
        if not pathlib.Path(path).is_file():
            continue
        record = json.loads(pathlib.Path(path).read_text())
        rows = {row["id"]: row for row in record.get("rows", [])}
        for row, entry in record.get("objects", {}).items():
            if entry.get("take") == take and row in rows:
                return rows[row], list(rows.values())
    return None, []


def drawn_guard(take, inventories, inputs):
    """(its row's SAM 3 box, the guard list's word on its row, whether it is a person) for the take's row in the
    hand-ins (drawn_row; tumble.keeps_pose and tumble.person over the pose rules among `inputs`): what boxed reads."""
    import tumble
    row, rows = drawn_row(take, inventories)
    if row is None:
        return None, None, False
    return row.get("box"), tumble.keeps_pose(row, tumble.rules_of(inputs), rows), tumble.person(row)


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


def laid_size(labelled, size, base, built=False):
    """A design entry's size in the kit frame: its row's, or for a slender row or a code build (`built`) its labelled
    take's own proportions turned by `base`, scaled as one so its longest side is the row's (place_route.made_size): a
    thin run's box is its thickness on its two short sides, so fitting a sagging string side by side to its 8 by 0.01
    by 0.01 crushed its sag flat (2026-10-26); a code build's section is its picture's where its box's cannot show it,
    so fitting airlock's locker lamp, built 0.046 m across, to its 0.4 by 0.1 by 0.1 row undid it (outline 0.813 built,
    0.409 baked, 2026-10-29)."""
    if built or slender(size):
        return place_route.made_size(labelled, size, 90 if base == TURNS[90] else 0)
    return size


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
