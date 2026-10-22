"""The crops stage's reading of a place's design and the world files each of its rows declares (Stage.files, a
function of the place).

A place's crops are its design's alone (owner, 2026-10-21: every stage builds from the creator's design; the old
per-place crop data, data/crops/<place>.json, was retired): every row of its kept scene inventory whose kind grows
standing on a bed (design_layers.row_layers: a row that grows on a row of a bed's noun, or on a row that grows itself,
a planter) is a crop kind, named by its row, asked of SAM 3 by its own words (`kind_nouns`); its bed row is the row it
stands on, and the beds are the plan items that row makes, in the place's frame (scene_record.plan.items_of), as tall
as the bed row's metres, standing on the plan level the bed row's anchor names (`beds_in`). The plot SAM 3 is asked
for on the concept is the bed rows' words. The view is the place's locked concept (`DESIGN_VIEW`).

    record_of(inventory)         {place, concept: {view, plot: {nouns}}, kinds: {row: {row, nouns, bed}}, beds: [row]}
    read(inputs)                 record_of the row's declared inventory
    beds_in(inputs, record)      [{name, row, centre, size}] metres, Y up, the place's frame, in the plan's order
    applies(place)               whether the place's design shows crops (design_layers.has_layer)

Kept apart from the rows' code on purpose: every crop row's code version hashes this module, so it stays small.
"""
import contextlib
import json
import pathlib
import sys

from score.stages import design_layers, row_kinds

REPO = pathlib.Path(__file__).resolve().parents[3]
# The SAM 3 runner and the script it copies up: imported inside the rows (tools()), so declared as files instead.
MASKS_TOOLS = {"masks": "{repo}/tools/props/scene/box_masks.py",
               "masks runner": "{repo}/tools/props/cloud/box_masks_cloud.py"}
# The view every crop row reads: the place's locked design concept ({home}/design/concepts/<place>.png).
DESIGN_VIEW = "design"


def design_files(place):
    """The design every crop row reads: the place's kept scene inventory and plan, and the row-kind rules."""
    return {"inventory": "{home}/design/inventory/" + f"{place}.json", "plan": "{home}/design/plans/" + f"{place}.json",
            "row kinds": "{data}/checks/row-kinds.json"}


@contextlib.contextmanager
def tools(*folders):
    """The prop tools' folders (under tools/) on the path while the block runs; the path as it was after. A folder
    left on the path at the table's import would add files to other stages' code versions (_code hashes a name's file
    in every folder on the path), so the rows import the tools inside it and declare the files they run instead."""
    kept = list(sys.path)
    sys.path[:0] = [str(REPO / "tools" / folder) for folder in folders]
    try:
        yield
    finally:
        sys.path[:] = kept


def applies(place):
    """Whether the place's design shows crops: a row that grows standing on a bed."""
    return design_layers.has_layer(place, "crops")


def nouns_of(rows):
    """The words SAM 3 is asked for rows by: each row's name, then its noun, once each, in order."""
    found = [row_kinds.words(row.get(field)) for row in rows for field in ("name", "noun")]
    return list(dict.fromkeys(word for word in found if word))


def record_of(inventory, kinds=None):
    """The crop kinds of a design's scene inventory (module docstring), by the row-kind rules `kinds` (the house's
    by default)."""
    kinds = row_kinds.table() if kinds is None else kinds
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    crops = [row for row in rows.values() if "crops" in design_layers.row_layers(row, rows, kinds)]
    beds = list(dict.fromkeys(design_layers.holder_of(row, rows)["id"] for row in crops))
    return {"place": inventory["place"],
            "concept": {"view": DESIGN_VIEW, "plot": {"nouns": nouns_of([rows[bed] for bed in beds])}},
            "kinds": {row["id"]: {"row": row["id"], "nouns": kind_nouns(row, crops),
                                  "bed": design_layers.holder_of(row, rows)["id"]} for row in crops},
            "beds": beds}


def kind_nouns(row, crops):
    """A crop kind's words for SAM 3: its row's name, then its noun when no other crop row shares it (a plant two
    kinds' words find is the earlier kind's, so a shared noun would give every plant to the first)."""
    noun = row_kinds.words(row.get("noun"))
    shared = any(row_kinds.words(other.get("noun")) == noun for other in crops if other is not row)
    return [word for word in dict.fromkeys([row_kinds.words(row.get("name")), "" if shared else noun]) if word]


def read(inputs):
    """record_of the inventory a crop row declares (design_files), by the row-kind rules it declares."""
    return record_of(json.loads(pathlib.Path(inputs["inventory"]).read_text()), row_kinds.table(inputs["row kinds"]))


def level_of(plan, row):
    """The height a row stands at in the place's frame: the plan level its anchor names (`on:<level>`, its words the
    level's name), else the plan's floor."""
    from score.stages.scene_record import plan as plan_frame
    floor = float(plan_frame.frame_of(plan)[0][1])
    named = row_kinds.words(str(row.get("anchor") or "").removeprefix("on:"))
    level = next((level for level in plan.get("levels") or [] if row_kinds.words(level.get("name")) == named), None)
    return floor + (float(level["height"]) if level else 0.0)


def beds_of(plan, inventory, record):
    """Every plan item a bed row makes: {name, row, centre, size} in the place's frame (x east, y up, z south),
    metres, as tall as its row's size (wide, deep, tall) says, standing on its row's level; the plan's order."""
    from score.stages.scene_record import plan as plan_frame
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    found = []
    for item in plan_frame.items_of(plan):
        bed = next((row for row in record["beds"] if row in (item["rows"] or [])), None)
        if bed is None:
            continue
        low_x, low_z, high_x, high_z = item["box"]
        tall, floor = float(rows[bed]["size"][2]), level_of(plan, rows[bed])
        found.append({"name": item["name"], "row": bed,
                      "centre": [round((low_x + high_x) / 2, 4), round(floor + tall / 2, 4), round((low_z + high_z) / 2, 4)],
                      "size": [round(high_x - low_x, 4), tall, round(high_z - low_z, 4)]})
    return found


def beds_in(inputs, record):
    """beds_of the plan and inventory a crop row declares."""
    return beds_of(json.loads(pathlib.Path(inputs["plan"]).read_text()),
                   json.loads(pathlib.Path(inputs["inventory"]).read_text()), record)


def concept_picture(place):
    """The pattern of the place's locked design concept, the view every crop row reads (`design`)."""
    return "{home}/design/concepts/" + f"{place}.png"


def concept_files(place):
    """The concept row's files: the design, its concept view and the SAM 3 script that runs on the rented card (not
    in the row's code version: it is copied up, not imported)."""
    return {**design_files(place), "concept": concept_picture(place), **MASKS_TOOLS}


def boxes_files(place):
    """crops-boxes' files: the design (its reading's boxes in the kept inventory), the locked concept those boxes are
    on, the box check and the SAM 3 runner."""
    return {**design_files(place), "concept": concept_picture(place),
            "box check": "{repo}/tools/props/scene/box_check.py", **MASKS_TOOLS}


def layer_files(place):
    """The layer row's files: the design (the crop rows and their beds), the library and its theme (the baked
    models' surfaces) and the asset writer."""
    return {**design_files(place), "library": "{data}/library", "places": "{data}/definitions/place.json",
            "tokens": "{repo}/design/tokens/tokens.json", "sounds": "{data}/sound/surfaces.json",
            "export": "{repo}/tools/usd"}


def look_files(place):
    """The look row's files: the design (the beds it stands the crops on), the SAM 3 tools and the renderer."""
    return {**design_files(place), **MASKS_TOOLS, "renderer": "{repo}/tools/blender/inside",
            "blender runner": "{repo}/tools/props/cloud/blender_cloud.py"}
