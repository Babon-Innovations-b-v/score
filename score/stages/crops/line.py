"""The crops' own line: the crop kinds made by the prop route (its close-up and Pixal3D rows) and painted by the
surface stage's finish-map method, paint, bake and check, all unchanged, on the crop data's own files, as place rows
crops-props-inputs ... crops-surfaces-check (each input handed over under its stage's own name, renamed.py).

A line of its own, not the place's: in data/props/<place>.json and data/surfaces/<place>.json the crops would join the
place's own surface line, whose every row would be made again for them, re-making the models the owner reviewed
(the greenhouse's eight, 2026-10-12). Its data: data/crops/<place>-props.json (the prop data's form, prop_data.py) and
data/crops/<place>-surfaces.json (the surface data's form, surface_data.py), beside the crop data.

Before the close-ups, crops-boxes (boxes.py) runs the box gate's own SAM 3 measure on the crop rows' boxes.
"""
import pathlib
import sys

SURFACES = pathlib.Path(__file__).resolve().parents[1] / "surfaces"
if str(SURFACES) not in sys.path:
    sys.path.append(str(SURFACES))  # the surface stage's modules import each other by name

from score import contracts, graph  # noqa: E402
import score.stages.crops.boxes as boxes  # noqa: E402
import score.stages.crops.crop_data as crop_data  # noqa: E402
import score.stages.crops.renamed as renamed  # noqa: E402
import score.stages.props.closeup_row as closeup_row  # noqa: E402
import score.stages.props.pixal_row as pixal_row  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402

import bake_check  # noqa: E402
import finish_parts  # noqa: E402
import finish_rows  # noqa: E402
import place_line  # noqa: E402
import segvigen_row  # noqa: E402
import turntable_row  # noqa: E402
from surface_gates import guarded  # noqa: E402

PIXAL = "{home}/work/pixal"


def props_pattern(place):
    return "{data}/crops/" + f"{place}-props.json"


def surfaces_pattern(place):
    return "{data}/crops/" + f"{place}-surfaces.json"


def line_record(place):
    path = crop_data.FOLDER / f"{place}-surfaces.json"
    return prop_data.record_at(path) if path.exists() else {"takes": {}}


def inventory_pattern(place):
    return "{data}/inventory/" + f"{place}.json"


def view_files(place):
    """The place's concept views, as the prop route's inputs row reads them."""
    return prop_data.view_files(place)


def boxes_files(place):
    return {"crops": crop_data.pattern(place), "inventory": inventory_pattern(place),
            "box check": "{repo}/tools/props/scene/box_check.py", **crop_data.MASKS_TOOLS}


def inputs_files(place):
    return {"props": props_pattern(place), "inventory": inventory_pattern(place), "inventories": "{data}/inventory",
            **view_files(place), **prop_data.INPUTS_TOOLS}


def closeup_files(place):
    return dict(prop_data.CLOSEUP_TOOLS)


def pixal_files(place):
    return {"props": (props_pattern(place), prop_data.prop_part), "inventory": inventory_pattern(place),
            "surfaces": surfaces_pattern(place), **prop_data.PIXAL_TOOLS}


def take_files(place):
    """Every raw-model file the method reads per take (surface_data.take_files on the crops' data)."""
    found = {}
    for take in line_record(place)["takes"]:
        found[f"model {take}"] = f"{PIXAL}/{take}.glb"
        found[f"close-up {take}"] = f"{PIXAL}/{take}.svviews"
        found[f"finished {take}"] = f"{PIXAL}/{take}-final.glb"
    return found


def shape_files(place):
    return {"surfaces": surfaces_pattern(place), **take_files(place)}


def naming_files(place):
    return {**shape_files(place), "library": "{data}/library", "places": "{data}/definitions/place.json",
            "tokens": "{repo}/design/tokens/tokens.json"}


def turntable_files(place):
    return {**turntable_row.FILES, **shape_files(place)}


def segvigen_files(place):
    return {**segvigen_row.FILES, **shape_files(place)}


def paint_files(place):
    """The paint's: the naming files, the place's inventory (whose rows say a crop is fixed, so its feet are left as
    made), the resting rules and the paint script it runs by path on the machine."""
    return {**naming_files(place), f"inventory {place}": inventory_pattern(place),
            "resting rules": "{data}/checks/resting.json",
            "paint script": "{repo}/score/stages/surfaces/inside/paint_take.py"}


def bake_files(place):
    bake = line_record(place).get("bake")
    jobs = {"bake job": bake["job"]} if bake else {"bake job": surfaces_pattern(place) + " names no bake job"}
    return {"surfaces": surfaces_pattern(place), **jobs, "library bake": "{repo}/tools/props/cloud/library_bake.py",
            "bake scripts": "{repo}/tools/props/library/inside", "library": "{data}/library",
            "places": "{data}/definitions/place.json", "tokens": "{repo}/design/tokens/tokens.json"}


def row(name, make, schema, faults, checks, files, after=(), **more):
    """One place row of the line: its stage's make and judges, its inputs named as that stage's."""
    return graph.Stage(name, "place", renamed.make(make), contracts.Contract(schema, 1, faults),
                       tuple(guarded(check, renamed.judge(judge)) for check, judge in checks), files=files,
                       after={earlier: (schema_of[earlier], 1) for earlier in after}, applies=crop_data.applies,
                       **more)


schema_of = {"crops-boxes": "crops-boxes", "crops-props-inputs": "props-inputs", "crops-closeup": "props-closeups",
             "crops-pixal": "props-pixal", **{f"crops-surfaces-{step}": f"surfaces-{step}" for step in (
                 "inputs", "turntable", "lists", "maps", "names", "segvigen", "parts", "paint", "bake", "check")}}

BOXES = graph.Stage("crops-boxes", "place", boxes.make_boxes, contracts.Contract("crops-boxes", 1, boxes.boxes_faults),
                    boxes.CHECKS, files=boxes_files, paid=True, euros=boxes.EUROS, applies=crop_data.applies)
ROWS = (
    BOXES,
    row("crops-props-inputs", closeup_row.make_inputs, "props-inputs", closeup_row.inputs_faults,
        (("boxed or drawn", closeup_row.judge_inputs),), inputs_files, ("crops-boxes",)),
    row("crops-closeup", closeup_row.make_closeups, "props-closeups", closeup_row.closeups_faults,
        (("close-up", closeup_row.judge_closeups),), closeup_files, ("crops-props-inputs",), paid=True,
        euros=round(4 * 2 * closeup_row.DOLLARS_A_PICTURE, 2)),
    row("crops-pixal", pixal_row.make_pixal, "props-pixal", pixal_row.pixal_faults,
        (("takes", pixal_row.judge_takes),), pixal_files, ("crops-closeup",), paid=True, euros=2.0),
    row("crops-surfaces-inputs", finish_parts.make_inputs, "surfaces-inputs", finish_parts.inputs_faults,
        (("inputs", finish_parts.judge_inputs),), shape_files, ("crops-pixal",)),
    row("crops-surfaces-turntable", turntable_row.make_turntable, "surfaces-turntable", turntable_row.turntable_faults,
        (("turntable", turntable_row.judge_turntable),), turntable_files, ("crops-surfaces-inputs",), paid=True,
        euros=turntable_row.TURNTABLE_EUROS),
    row("crops-surfaces-lists", finish_rows.make_lists, "surfaces-lists", finish_rows.lists_faults,
        (("listed", finish_rows.judge_lists),), naming_files, ("crops-surfaces-inputs",), paid=True,
        euros=finish_rows.LIST_EUROS),
    row("crops-surfaces-maps", finish_rows.make_maps, "surfaces-maps", finish_rows.maps_faults,
        (("maps checked", finish_rows.judge_maps),), shape_files,
        ("crops-surfaces-inputs", "crops-surfaces-turntable", "crops-surfaces-lists"), paid=True,
        euros=finish_rows.MAP_EUROS),
    row("crops-surfaces-names", finish_rows.make_names, "surfaces-names", finish_rows.names_faults,
        (("named", finish_rows.judge_names),), naming_files, ("crops-surfaces-inputs", "crops-surfaces-maps"),
        paid=True, euros=finish_rows.LIST_EUROS),
    row("crops-surfaces-segvigen", segvigen_row.make_segvigen, "surfaces-segvigen", segvigen_row.segvigen_faults,
        (("split back", segvigen_row.judge_segvigen),), segvigen_files, ("crops-surfaces-maps",), paid=True,
        euros=segvigen_row.SEGVIGEN_EUROS),
    row("crops-surfaces-parts", finish_parts.make_parts, "surfaces-parts", finish_parts.parts_faults,
        (("parts", finish_parts.judge_parts),), naming_files,
        ("crops-surfaces-inputs", "crops-surfaces-turntable", "crops-surfaces-maps", "crops-surfaces-names",
         "crops-surfaces-segvigen")),
    row("crops-surfaces-paint", place_line.make_paint, "surfaces-paint", place_line.paint_faults,
        (("one surface a part", place_line.judge_one_surface),
         ("colour against the close-up", place_line.judge_concept_colour),
         ("feet in one plane", place_line.judge_feet)),
        paint_files, ("crops-surfaces-parts",), paid=True, euros=place_line.PAINT_EUROS),
    row("crops-surfaces-bake", place_line.make_bake, "surfaces-bake", place_line.bake_faults,
        (("baked", place_line.judge_baked),), bake_files, ("crops-surfaces-paint",), paid=True,
        euros=place_line.BAKE_EUROS),
    row("crops-surfaces-check", bake_check.make_check, "surfaces-check", bake_check.check_faults,
        (("baked matches its surfaces", bake_check.judge_lit), ("triangles within budget", bake_check.judge_triangles)),
        naming_files, ("crops-surfaces-bake", "crops-surfaces-paint")),
)
