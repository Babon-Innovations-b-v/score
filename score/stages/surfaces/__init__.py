"""The surface stage (R4, the paper's core contribution: shape and surface apart, every part one surface of the shared
library) as rows of world 1's stage table: each place's own line, side by side with every other place's.

    from score.stages import surfaces
    surfaces.ROWS          # the rows, in the order a line runs them

A line runs the method, then the framework:
    method (the finish-map method: finish_parts.py, turntable_row.py, finish_rows.py, segvigen_row.py):
        surfaces-inputs, surfaces-turntable, surfaces-lists (Gemini 3.1 Pro), surfaces-maps (Nano Banana Pro),
        surfaces-segvigen, surfaces-parts
    framework (place_line.py): surfaces-paint (proposals into the finish registry, registry.py), surfaces-bake,
        surfaces-check

The method's interface is one contract, PARTS (per model its parts, each with the library surface the method named
for it, parts.json and <take>/parts.npy, <take>/colours.npy). Another method replaces the method's rows and writes
it; the framework's rows stay.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))  # the stage's modules import each other by name, as in the prop environment

from score import contracts, graph  # noqa: E402

import surface_data as data  # noqa: E402
import finish_parts  # noqa: E402
import finish_rows  # noqa: E402
import place_line  # noqa: E402
import segvigen_row  # noqa: E402
import turntable_row  # noqa: E402
from surface_gates import guarded  # noqa: E402

PARTS = contracts.Contract("surfaces-parts", 1, finish_parts.parts_faults)


def contract(schema, faults):
    return contracts.Contract(schema, 1, faults)


def reads(*rows):
    """`after` for rows of this stage, each at its contract's version 1."""
    return {row: (row, 1) for row in rows}


def row(name, make, faults, check, judge, files, after=(), **more):
    """One place row of the stage: its output's contract is named for the row."""
    return graph.Stage(name, "place", make, contract(name, faults), (guarded(check, judge),), files=files,
                       after=reads(*after), applies=data.paints, **more)


def turntable_files(place):
    return {**turntable_row.FILES, **data.take_files(place)}


def segvigen_files(place):
    return {**segvigen_row.FILES, **data.take_files(place)}


METHOD = (
    row("surfaces-inputs", finish_parts.make_inputs, finish_parts.inputs_faults, "inputs", finish_parts.judge_inputs,
        data.line_files),
    row("surfaces-turntable", turntable_row.make_turntable, turntable_row.turntable_faults, "turntable",
        turntable_row.judge_turntable, turntable_files, ("surfaces-inputs",), paid=True,
        euros=turntable_row.TURNTABLE_EUROS),
    row("surfaces-lists", finish_rows.make_lists, finish_rows.lists_faults, "listed", finish_rows.judge_lists,
        data.line_files, ("surfaces-inputs",), paid=True, euros=finish_rows.LIST_EUROS),
    row("surfaces-maps", finish_rows.make_maps, finish_rows.maps_faults, "maps checked", finish_rows.judge_maps,
        data.line_files, ("surfaces-inputs", "surfaces-turntable", "surfaces-lists"), paid=True,
        euros=finish_rows.MAP_EUROS),
    row("surfaces-segvigen", segvigen_row.make_segvigen, segvigen_row.segvigen_faults, "split back",
        segvigen_row.judge_segvigen, segvigen_files, ("surfaces-maps",), paid=True,
        euros=segvigen_row.SEGVIGEN_EUROS),
    graph.Stage("surfaces-parts", "place", finish_parts.make_parts, PARTS,
                (guarded("parts", finish_parts.judge_parts),), files=data.line_files,
                after=reads("surfaces-inputs", "surfaces-turntable", "surfaces-maps", "surfaces-segvigen"),
                applies=data.paints))
LINE = (
    graph.Stage("surfaces-paint", "place", place_line.make_paint, contract("surfaces-paint", place_line.paint_faults),
                (guarded("one surface a part", place_line.judge_one_surface),
                 guarded("colour against the close-up", place_line.judge_concept_colour)),
                files=data.line_files, after=reads("surfaces-parts"), applies=data.paints),
    row("surfaces-bake", place_line.make_bake, place_line.bake_faults, "baked", place_line.judge_baked,
        data.bake_files, ("surfaces-paint",), paid=True, euros=place_line.BAKE_EUROS),
    graph.Stage("surfaces-check", "place", place_line.make_check, contract("surfaces-check", place_line.check_faults),
                (guarded("baked matches its surfaces", place_line.judge_lit),
                 guarded("triangles within budget", place_line.judge_triangles)),
                files=data.line_files, after=reads("surfaces-bake", "surfaces-paint"), applies=data.paints))
ROWS = (*METHOD, *LINE)
