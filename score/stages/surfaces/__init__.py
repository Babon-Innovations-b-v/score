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

The finish route (route_*.py, beside the method until its test passes): finish-route-views, -split, -list (Gemini 3.1
Pro), -fill, -recheck (Gemini 3.1 Pro and the free colour check).

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
import route_data  # noqa: E402
import route_fill  # noqa: E402
import route_list  # noqa: E402
import route_recheck  # noqa: E402
import route_split  # noqa: E402
import route_views  # noqa: E402
import row_files  # noqa: E402
import segvigen_row  # noqa: E402
import turntable_row  # noqa: E402
from surface_gates import guarded  # noqa: E402

PARTS = contracts.Contract("surfaces-parts", 1, finish_parts.parts_faults)


def contract(schema, faults):
    return contracts.Contract(schema, 1, faults)


def reads(*rows):
    """`after` for rows of this stage, each at its contract's version 1."""
    return {row: (row, 1) for row in rows}


def row(name, make, faults, check, judge, files, after=(), applies=data.paints, **more):
    """One place row of the stage: its output's contract is named for the row."""
    return graph.Stage(name, "place", make, contract(name, faults), (guarded(check, judge),), files=files,
                       after=reads(*after), applies=applies, **more)


METHOD = (
    row("surfaces-inputs", finish_parts.make_inputs, finish_parts.inputs_faults, "inputs", finish_parts.judge_inputs,
        data.shape_files),
    row("surfaces-turntable", turntable_row.make_turntable, turntable_row.turntable_faults, "turntable",
        turntable_row.judge_turntable, row_files.turntable_files, ("surfaces-inputs",), paid=True,
        euros=turntable_row.TURNTABLE_EUROS),
    row("surfaces-lists", finish_rows.make_lists, finish_rows.lists_faults, "listed", finish_rows.judge_lists,
        data.line_files, ("surfaces-inputs",), paid=True, euros=finish_rows.LIST_EUROS),
    row("surfaces-maps", finish_rows.make_maps, finish_rows.maps_faults, "maps checked", finish_rows.judge_maps,
        data.shape_files, ("surfaces-inputs", "surfaces-turntable", "surfaces-lists"), paid=True,
        euros=finish_rows.MAP_EUROS),
    row("surfaces-names", finish_rows.make_names, finish_rows.names_faults, "named", finish_rows.judge_names,
        data.line_files, ("surfaces-inputs", "surfaces-maps"), paid=True, euros=finish_rows.LIST_EUROS),
    row("surfaces-segvigen", segvigen_row.make_segvigen, segvigen_row.segvigen_faults, "split back",
        segvigen_row.judge_segvigen, row_files.segvigen_files, ("surfaces-maps",), paid=True,
        euros=segvigen_row.SEGVIGEN_EUROS),
    graph.Stage("surfaces-parts", "place", finish_parts.make_parts, PARTS,
                (guarded("parts", finish_parts.judge_parts),), files=data.parts_files,
                after=reads("surfaces-inputs", "surfaces-turntable", "surfaces-maps", "surfaces-names",
                            "surfaces-segvigen"),
                applies=data.paints))
LINE = (
    graph.Stage("surfaces-paint", "place", place_line.make_paint, contract("surfaces-paint", place_line.paint_faults),
                (guarded("one surface a part", place_line.judge_one_surface),
                 guarded("colour against the close-up", place_line.judge_concept_colour)),
                files=data.line_files, after=reads("surfaces-parts"), applies=data.paints, paid=True,
                euros=place_line.PAINT_EUROS),
    row("surfaces-bake", place_line.make_bake, place_line.bake_faults, "baked", place_line.judge_baked,
        data.bake_files, ("surfaces-paint",), paid=True, euros=place_line.BAKE_EUROS),
    graph.Stage("surfaces-check", "place", place_line.make_check, contract("surfaces-check", place_line.check_faults),
                (guarded("baked matches its surfaces", place_line.judge_lit),
                 guarded("triangles within budget", place_line.judge_triangles)),
                files=data.line_files, after=reads("surfaces-bake", "surfaces-paint"), applies=data.paints))
# Experimental (2026-10-20): the finish route (owner; #18), beside METHOD until its test passes and the owner moves
# the line onto it. Library first: the views cast here, Gemini's finish list matched to library surfaces with
# settings, the free colour labels voted into parts, each part filled, and a recheck with up to three tweaks, else the
# named fault "no library surface fits". Off by default: its rows have a node only when a command asks for one of
# them by name (`--stage finish-route-*`, graph.asked_for), so no line, plan, hole or price has them otherwise; each
# takes the runner's object filter (`--object`), and its paid rows refuse to run without one (route_cap.py: the
# trial's EUR 5 in total, held against the Google ledger before each ask).
ROUTE_NAMES = ("finish-route-views", "finish-route-split", "finish-route-list", "finish-route-fill",
               "finish-route-recheck")


def route_applies(place):
    """A finish route row's node: only when this command asks for a route row by name, for a place that paints."""
    return graph.asked_for(ROUTE_NAMES) and data.paints(place)


ROUTE = (
    row("finish-route-views", route_views.make_views, route_views.views_faults, "views cast", route_views.judge_views,
        route_data.shape_files, selects=True, applies=route_applies),
    row("finish-route-split", route_split.make_split, route_split.split_faults, "parts voted",
        route_split.judge_split, route_data.shape_files, ("finish-route-views",), selects=True, applies=route_applies),
    row("finish-route-list", route_list.make_list, route_list.list_faults, "library first", route_list.judge_list,
        route_data.library_files, ("finish-route-views", "finish-route-split"), paid=True,
        euros=route_list.LIST_EUROS, selects=True, applies=route_applies),
    row("finish-route-fill", route_fill.make_fill, route_fill.fill_faults, "every part filled", route_fill.judge_fill,
        route_data.library_files, ("finish-route-views", "finish-route-split", "finish-route-list"), selects=True,
        applies=route_applies),
    row("finish-route-recheck", route_recheck.make_recheck, route_recheck.recheck_faults, "library surface fits",
        route_recheck.judge_recheck, route_data.library_files, ("finish-route-views", "finish-route-fill"),
        paid=True, euros=route_recheck.RECHECK_EUROS, selects=True, applies=route_applies))
ROWS = (*METHOD, *LINE, *ROUTE)
