"""The remake's hand-in to the shared loop (CONTEXT.md "layer adapter", "prop pipeline"; score/stages/shapes_first):
each designed place's takes, exactly as prepare priced them, written where the prop route's rows read a place's
hand-in (prop_data.DESIGN) and the finish route its surface data (surface_data.DESIGN), so the runner runs and prices
the takes the estimate prices. Free and local; nothing in the stage table imports it.

A designed place is one whose plan is kept where the plan stage reads it (score/review/plans.KEPT: its pick, its
scene inventory read from it, its plan). Its hand-in (`{home}/design/props/<place>.json`) is both the loop's hand-in
record (prop_data's form) and the scene inventory the Pixal3D batch builds from (approved by the creator's pick, the
owner 2026-10-21, which tools/props/cloud/batch.py built_from takes as it stands):

    {"place" (its style's id: library_of), "scene" (the place), "order": "prop-first",
     "approved": {"by": "the creator's pick", "concept": <sha256>}, "migrated": false, "room",
     "plan": {"views": [{"id": "v1", "picture": "{home}/design/concepts/<place>.png"}]},
     "rows": [the reading's rows, each sized as prepare sizes it; a handed row's `kind` generate, `was` its own;
              a row with a box `grounded`: SAM 3's, else Gemini's region, said which (BOXED); the box gate passes
              it],
     "objects": {<a take's first row>: {"route": "prop", "take", "layer", "rows"}},   (bought and made model takes)
     "takes": {<take>: {"place", "rows", "route", "shell", "status", "stages"}},       (every take prepare listed)
     "fallback": {}}

`stages` are the paid layers the take runs once each (estimate.take_stages: [] when it is not bought); the runner
counts a node's units from them (gaps/price.design_units), so its plan lists and prices the same takes. The surface
data (`{home}/design/surfaces/<place>.json`, surface_data's form) lists the takes the finish route paints (every
model take, a shell piece's too: CONTEXT.md "prop pipeline") and bakes each model take (compare.bake_entry: its entry
and faces, which Pixal3D's finish reads). A file is written only when its bytes change, so a key moves only with what the design says; a place no
longer designed has its files taken out.
"""
import json
import pathlib

from score.stages.complete.prepare import estimate, groups

ROOT = pathlib.Path(__file__).resolve().parents[4]
APPROVED_BY = "the creator's pick"  # what the Pixal3D batch takes as a design's approval (batch.py DESIGNED)
GROUNDED = "SAM 3's box in the reading of the picked concept"  # the box gate passes it (box_check.row_verdict)
# A row SAM 3 found none of is framed by Gemini's region round it in the same reading (groups.boxed_by), said so.
BOXED = {"SAM 3": GROUNDED, "Gemini": "Gemini's region in the reading of the picked concept (SAM 3 found none)"}
LAYERS = {"people": "people"}  # a route's layer at the loop's seam (shapes_first.ADAPTERS); a terrain row's is terrain


def layer_of(row):
    """The model layer that hands a row to the loop: the terrain adapter's for a terrain row, else its route's."""
    return "terrain" if row.get("terrain") else LAYERS.get(row.get("route"), "objects")


def handed(take):
    """Whether the loop makes the take's model: a model route's take, bought or already made."""
    return take["route"] in groups.MODEL_ROUTES and take["status"] in ("bought", "made")


def library_of(place):
    """The name the library and data/definitions/place.json know the place by (its data/surfaces file's `library`,
    the street's prologue_street), else its own."""
    old = ROOT / "data/surfaces" / f"{place}.json"
    return json.loads(old.read_text()).get("library", place) if old.is_file() else place


def hand_in(place, inventory, takes, route):
    """The place's hand-in record (module docstring) of its takes, `inventory` its sized scene inventory."""
    first = {take["rows"][0]: take for take in takes if handed(take)}
    rows = [{**row, **({"kind": "generate", "was": row["kind"]} if row["id"] in first else {}),
             **({"grounded": BOXED[row["boxed_by"]]} if row.get("boxed_by") else {})} for row in inventory["rows"]]
    return {"place": library_of(place), "scene": place, "order": "prop-first",
            "approved": {"by": APPROVED_BY, "concept": inventory["concept_pick"]["sha256"]},
            "migrated": False, "room": inventory.get("room", {}),
            "plan": {"views": [{"id": "v1", "picture": "{home}/design/concepts/" + f"{place}.png"}]}, "rows": rows,
            "objects": {row: {"route": "prop", "take": take["take"], "layer": layer_of(take_row(rows, row)),
                              "rows": take["rows"]} for row, take in first.items()},
            "takes": {take["take"]: {"place": place, "rows": take["rows"], "route": take["route"],
                                     "shell": take["shell"], "status": take["status"],
                                     "stages": estimate.take_stages(route, take) if take["status"] == "bought" else []}
                      for take in takes},
            "fallback": {}}


def take_row(rows, row_id):
    return next(row for row in rows if row["id"] == row_id)


def surface_record(place, record, details):
    """The place's surface data (surface_data's form) of its hand-in: every model take painted by the finish route (a
    shell piece's too, so the bake that bakes the listed takes bakes it) and baked as <row>_1 with its entry where its
    row has a size."""
    from score.stages.props import compare
    by_id = {row["id"]: row for row in record["rows"]}
    sized = {row: entry for row, entry in record["objects"].items() if groups.sides(by_id[row].get("size"))}
    return {"place": place, "library": record["place"],
            "takes": {entry["take"]: {"places": [place], "library_places": [record["place"]], "place": place,
                                      "kind": f"{place}_{row}", "object": by_id[row]["name"]}
                      for row, entry in record["objects"].items()},
            "bake": {"models": {f"{row}_1": entry["take"] for row, entry in sized.items()},
                     "entries": {f"{row}_1": compare.bake_entry(place, by_id[row], details) for row in sized}},
            "elsewhere": {}}


def written(path, record):
    """`record` at `path` when its bytes change; whether it was written."""
    text = json.dumps(record, indent=1) + "\n"
    if path.is_file() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return True


def kept(store, record, route, designed):
    """Every `designed` place's hand-in and surface data written from prepare's `record` (route: its prop route's
    stages), the rest taken out; ([places kept], [places whose files changed])."""
    from score.review import plans
    from score.stages.props import prop_data
    from score.stages.surfaces import surface_data
    inventories, _ = groups.current(store, designed)
    details = json.loads((ROOT / "data/library/details.json").read_text())
    changed = []
    for place in sorted(inventories):
        inventory = {"room": plans.filed_inventory(place).get("room", {}), **inventories[place]}
        record_in = hand_in(place, inventory, [take for take in record["takes"] if take["place"] == place], route)
        moved = written(prop_data.DESIGN / f"{place}.json", record_in)
        moved |= written(surface_data.DESIGN / f"{place}.json", surface_record(place, record_in, details))
        if moved:
            changed.append(place)
    for folder in (prop_data.DESIGN, surface_data.DESIGN):
        for path in folder.glob("*.json") if folder.is_dir() else []:
            if path.stem not in inventories:
                path.unlink()
                changed.append(path.stem)
    return sorted(inventories), sorted(set(changed))
