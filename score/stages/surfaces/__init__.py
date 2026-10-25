"""The surface stage (R4, the paper's core contribution: shape and surface apart, every part one surface of the shared
library) as rows of world 1's stage table: each place's own line, side by side with every other place's.

    from score.stages import surfaces
    surfaces.ROWS          # the rows, in the order a line runs them

A line runs the finish route (owner, 2026-10-20, #18; route_*.py), then the framework:
    route: finish-route-palette (Gemini 3.1 Pro, one ask a scene: its palette tokens, colours and wear read from its
        locked concept, scene_palette.py), surface-library (Gemini 3.1 Pro, one ask a scene: its surfaces made fresh
        from today's recipes in its palette, scene_library.py; owner, 2026-10-21: every old material retired, the
        library starts empty; every row after it takes this library through palette_library.py, never place.json),
        finish-route-views (free: renders of the raw model from every angle the coverage check needs, and its
        colour regions), finish-route-list (Gemini 3.1 Pro, one batch: the finish list matched library first, a label
        for each region in each view), finish-route-split (free: the labels voted across views, every face one
        finish or its take a gap), surfaces-parts (free: each part its checked library surface)
    framework: surfaces-bake (paid: each take painted with its parts' library surfaces, the list's settings on
        them, and baked, one job a take on the rented card, route_bake.py; proposals into the finish registry,
        registry.py), surfaces-paint (free: the bake's painted takes and the paint's gates, route_paint.py),
        finish-route-recheck (Gemini 3.1 Pro, one batch, and the free colour check: pass or a gap),
        surfaces-check (route_check.py: bake_check.py's against the bake's specs)

The method's interface is one contract, PARTS (per model its parts, each with the library surface the method named
for it, parts.json and <take>/parts.npy, <take>/colours.npy). The people's line runs the same route rows
(../people/line.py); the crops are the places' own takes. The finish-map method (its turntable, maps, names and
SegviGen rows) was deleted on 2026-10-20 (#26), when the crops and people left it.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))  # the stage's modules import each other by name, as in the prop environment

from score import contracts, graph  # noqa: E402

import surface_data as data  # noqa: E402
import finish_parts  # noqa: E402
import place_line  # noqa: E402
import route_data  # noqa: E402
import route_bake  # noqa: E402
import route_list  # noqa: E402
import route_paint  # noqa: E402
import route_parts  # noqa: E402
import route_recheck  # noqa: E402
import route_split  # noqa: E402
import route_views  # noqa: E402
import scene_library  # noqa: E402
import scene_palette  # noqa: E402
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


ROUTE = (
    row("finish-route-palette", scene_palette.make_palette, scene_palette.palette_faults, "palette from the design",
        scene_palette.judge_palette, scene_palette.palette_files, paid=True, euros=scene_palette.PALETTE_EUROS),
    row(scene_library.ROW, scene_library.make_library, scene_library.library_faults, "surfaces from the design",
        scene_library.judge_library, scene_library.files, ("finish-route-palette",), paid=True,
        euros=scene_library.LIBRARY_EUROS),
    row("finish-route-views", route_views.make_views, route_views.views_faults, "views cast", route_views.judge_views,
        route_data.shape_files, selects=True),
    row("finish-route-list", route_list.make_list, route_list.list_faults, "library first", route_list.judge_list,
        route_data.library_files, ("finish-route-palette", scene_library.ROW, "finish-route-views"), paid=True,
        euros=route_list.LIST_EUROS, selects=True),
    row("finish-route-split", route_split.make_split, route_split.split_faults, "one finish a face",
        route_split.judge_split, route_data.shape_files, ("finish-route-views", "finish-route-list"), selects=True),
    graph.Stage("surfaces-parts", "place", route_parts.make_parts, PARTS, (guarded("parts", route_parts.judge_parts),),
                files=route_data.parts_files, after=reads("finish-route-palette", scene_library.ROW, "finish-route-views",
                                                          "finish-route-list", "finish-route-split"),
                applies=data.paints, selects=True))
LINE = (
    row("surfaces-bake", route_bake.make_bake, route_bake.bake_faults, "baked", route_bake.judge_baked,
        data.bake_files, ("finish-route-palette", scene_library.ROW, "surfaces-parts"), paid=True, euros=place_line.BAKE_EUROS,
        selects=True),  # it bakes the parts row's takes, the filter's alone; selecting prices it for those
    graph.Stage("surfaces-paint", "place", route_paint.make_paint, contract("surfaces-paint", place_line.paint_faults),
                (guarded("one surface a part", place_line.judge_one_surface),
                 guarded("colour against the close-up", place_line.judge_concept_colour)),
                files=data.line_files, after=reads("surfaces-bake"), applies=data.paints),
    row("finish-route-recheck", route_recheck.make_recheck, route_recheck.recheck_faults, "library surface fits",
        route_recheck.judge_recheck, route_data.library_files,
        ("finish-route-palette", scene_library.ROW, "finish-route-views", "surfaces-parts"), paid=True,
        euros=route_recheck.RECHECK_EUROS,
        selects=True),
    graph.Stage("surfaces-check", "place", place_line.make_check, contract("surfaces-check", place_line.check_faults),
                (guarded("baked matches its surfaces", place_line.judge_lit),
                 guarded("triangles within budget", place_line.judge_triangles)),
                files=data.line_files, after=reads("finish-route-palette", scene_library.ROW, "surfaces-bake", "surfaces-paint",
                                  "finish-route-recheck"),
                applies=data.paints))
ROWS = (*ROUTE, *LINE)
