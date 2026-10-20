"""The people's surface line: the surface stage's finish-map method and its paint, unchanged, on the takes of
data/people/surfaces.json (each look's Pixal3D take), as environment rows people-inputs ... people-paint. The owner's plan
of 2026-10-11 (#5): a person's clothing is painted through the same surface stage as the props. No bake or check
rows: a person is not baked into a place; the dress rows (bodies.py) lay the paint's library surfaces on the built
body.
"""
import json
import pathlib
import sys

SURFACES = pathlib.Path(__file__).resolve().parents[1] / "surfaces"
if str(SURFACES) not in sys.path:
    sys.path.append(str(SURFACES))  # the surface stage's modules import each other by name

from score import contracts, graph  # noqa: E402
from score.stages.people import hair, renamed  # noqa: E402

import finish_parts  # noqa: E402
import finish_rows  # noqa: E402
import place_line  # noqa: E402
import segvigen_row  # noqa: E402
import turntable_row  # noqa: E402
from surface_gates import guarded  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parents[3] / "data/people/surfaces.json"
PIXAL = "{home}/work/pixal"


def shape_files():
    """surface_data.shape_files' environment files for the people's data (not a place's: data/surfaces holds places only)."""
    found = {"surfaces": "{data}/people/surfaces.json"}
    for take in json.loads(DATA.read_text())["takes"]:
        found.update({f"model {take}": f"{PIXAL}/{take}.glb", f"close-up {take}": f"{PIXAL}/{take}.svviews",
                      f"finished {take}": f"{PIXAL}/{take}-final.glb"})
    return found


SHAPE = shape_files()
NAMING = {**SHAPE, "library": "{data}/library", "places": "{data}/definitions/place.json",
          "tokens": "{repo}/design/tokens/tokens.json"}
PAINT = {**NAMING, "resting rules": "{data}/checks/resting.json",
         "paint script": "{repo}/score/stages/surfaces/inside/paint_take.py"}


def row(name, make, faults, checks, files, after=(), **more):
    """One environment row of the line: the surface stage's make and judges, its inputs named as the surface stage's."""
    return graph.Stage(name, "world", renamed.make(make), contracts.Contract(name, 1, faults),
                       tuple(guarded(check, renamed.judge(judge)) for check, judge in checks), files=files,
                       after={earlier: (earlier, 1) for earlier in after}, **more)


ROWS = (
    row("people-inputs", finish_parts.make_inputs, finish_parts.inputs_faults,
        (("inputs", finish_parts.judge_inputs),), SHAPE),
    row("people-turntable", turntable_row.make_turntable, turntable_row.turntable_faults,
        (("turntable", turntable_row.judge_turntable),), {**turntable_row.FILES, **SHAPE}, ("people-inputs",),
        paid=True, euros=turntable_row.TURNTABLE_EUROS),
    row("people-lists", finish_rows.make_lists, finish_rows.lists_faults, (("listed", finish_rows.judge_lists),),
        NAMING, ("people-inputs",), paid=True, euros=finish_rows.LIST_EUROS),
    row("people-maps", finish_rows.make_maps, finish_rows.maps_faults, (("maps checked", finish_rows.judge_maps),),
        SHAPE, ("people-inputs", "people-turntable", "people-lists"), paid=True, euros=finish_rows.MAP_EUROS),
    row("people-names", finish_rows.make_names, finish_rows.names_faults, (("named", finish_rows.judge_names),),
        NAMING, ("people-inputs", "people-maps")),
    row("people-segvigen", segvigen_row.make_segvigen, segvigen_row.segvigen_faults,
        (("split back", segvigen_row.judge_segvigen),), {**segvigen_row.FILES, **SHAPE}, ("people-maps",),
        paid=True, euros=segvigen_row.SEGVIGEN_EUROS),
    row("people-parts", finish_parts.make_parts, finish_parts.parts_faults, (("parts", finish_parts.judge_parts),),
        NAMING, ("people-inputs", "people-turntable", "people-maps", "people-names", "people-segvigen")),
    row("people-paint", place_line.make_paint, place_line.paint_faults,
        (("one surface a part", place_line.judge_one_surface),
         ("colour against the close-up", hair.judge_colour)),
        PAINT, ("people-parts",), paid=True, euros=place_line.PAINT_EUROS),
)
