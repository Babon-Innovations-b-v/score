"""The people's surface line: people are models like every other (the owner, 2026-10-11 and 2026-10-20), so their
clothing goes through the one finish route the places' lines run, its rows' makes and judges unchanged, on the takes
of data/people/surfaces.json (each look's Pixal3D take, made by people-take-<look>, the prop route's close-up and
Pixal3D), as environment rows:

    people-route-views   free   the route's renders of each raw take and its colour regions (route_views.py)
    people-route-list    paid   one Gemini batch answer a take: the finish list, library first (route_list.py)
    people-route-split   free   the labels voted across views, every face one finish (route_split.py)
    people-parts         free   each part its checked library surface: the method's interface (route_parts.py)
    people-paint         paid   the framework's paint on a rented machine (place_line.make_paint), the parts laid on
                                each finished take; the dress rows read its labelled samples

No bake or check rows: a person is not baked into a place; the dress rows (dress.py) lay the paint's library surfaces
on the built body. Until 2026-10-20 the line ran the finish-map method (turntable, lists, maps, names, SegviGen).
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
import place_line  # noqa: E402
import route_data  # noqa: E402
import route_list  # noqa: E402
import route_parts  # noqa: E402
import route_split  # noqa: E402
import route_views  # noqa: E402
from surface_gates import guarded  # noqa: E402

DATA = pathlib.Path(__file__).resolve().parents[3] / "data/people/surfaces.json"
PIXAL = "{home}/work/pixal"
SURFACES_FILE = "{data}/people/surfaces.json"
LIBRARY = {"library": "{data}/library", "places": "{data}/definitions/place.json",
           "tokens": "{repo}/design/tokens/tokens.json"}


def takes():
    return list(json.loads(DATA.read_text())["takes"])


def route_shape(place=None):
    """The route's views and split files on the people's data: each take's raw model and own close-up that is here
    (route_data.model_files' rule: a take with none is named by the views gate before anything is asked)."""
    found = {"surfaces": SURFACES_FILE}
    for take in takes():
        if route_data.model_path(take) is not None:
            found[f"model {take}"] = f"{PIXAL}/{take}.glb"
        if route_data.close_up_path(take) is not None:
            found[f"close-up {take}"] = f"{PIXAL}/{take}.svviews/input.png"
    return found


def route_library(place=None):
    """The route's list and parts files: route_shape, the library, the places and the palette."""
    return {**route_shape(place), **LIBRARY}


def paint_files(place=None):
    """The paint's: every take's raw, close-up and finished model, the library, the resting rules and the script."""
    found = {"surfaces": SURFACES_FILE, **LIBRARY, "resting rules": "{data}/checks/resting.json",
             "paint script": "{repo}/score/stages/surfaces/inside/paint_take.py"}
    for take in takes():
        found.update({f"model {take}": f"{PIXAL}/{take}.glb", f"close-up {take}": f"{PIXAL}/{take}.svviews",
                      f"finished {take}": f"{PIXAL}/{take}-final.glb"})
    return found


def row(name, make, faults, checks, files, after=(), **more):
    """One environment row of the line: the surface stage's make and judges, its inputs named as the surface stage's."""
    return graph.Stage(name, "world", renamed.make(make), contracts.Contract(name, 1, faults),
                       tuple(guarded(check, renamed.judge(judge)) for check, judge in checks), files=files,
                       after={earlier: (earlier, 1) for earlier in after}, **more)


ROWS = (
    row("people-route-views", route_views.make_views, route_views.views_faults,
        (("views cast", route_views.judge_views),), route_shape, selects=True),
    row("people-route-list", route_list.make_list, route_list.list_faults, (("library first", route_list.judge_list),),
        route_library, ("people-route-views",), paid=True, euros=route_list.LIST_EUROS, selects=True),
    row("people-route-split", route_split.make_split, route_split.split_faults,
        (("one finish a face", route_split.judge_split),), route_shape, ("people-route-views", "people-route-list"),
        selects=True),
    row("people-parts", route_parts.make_parts, finish_parts.parts_faults, (("parts", route_parts.judge_parts),),
        route_library, ("people-route-views", "people-route-list", "people-route-split"), selects=True),
    row("people-paint", place_line.make_paint, place_line.paint_faults,
        (("one surface a part", place_line.judge_one_surface),
         ("colour against the close-up", hair.judge_colour)),
        paint_files, ("people-parts",), paid=True, euros=place_line.PAINT_EUROS),
)
