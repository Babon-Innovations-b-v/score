"""Library first (#21 cut 1): a group whose model the creator's library already holds is reused, never bought. Read
only from the library's own model index (`<SCORE_LIB_ROOT>/index/model.json`) and each entry's record, through
`score.library` (ADR-0007); score never imports the library (score/stages/library's overlay).

A library model matches a group by object kind and size ratio (groups.model_key without the kit). The index names
no size, so a model's size is its source row's in the scene inventory it was made for (its record's `place` and
`source_name`, or that name's object kind); a model with no such row has no size and matches nothing. A scene
inventory reading measures no size, so its rows match a model with a size by object kind alone.

Reused only when made under today's route (owner, 2026-10-20, #21/#41): a model is reused when the owner locked it
(index state `locked`), or when its provenance names today's route (`route` == todays_route(): the hash of the
prop pipeline's and finish route's code and gates, worked out as the library rows' key works it out and stamped by
their handover) and the runner accepted it there, so today's gates passed. Any other match is remade:
one the pipeline made from a picture (tags `prop`, `machine`, `crop`) under an older route counts as `old`, a
code-built one (`piece`, or no tag) as `code`. A withdrawn model is out of the library and matches nothing.
"""
from score import graph, library, stages
from score.stages import library as library_rows
from score.stages.complete.prepare import groups

PIPELINE_TAGS = ("prop", "machine", "crop")
NO_MATCH = {"pipeline": [], "old": [], "code": []}


def todays_route():
    """Today's route: the stage table's route stages' code and gates, hashed as the library rows' key hashes them."""
    return library_rows.route(graph.stage_code, stages.STAGES)


def library_models(root, route):
    """[{address, id, place, source, tag, today}] of the library's models not withdrawn, from its index and each
    entry's record; `today` when reusable under `route`."""
    found = []
    for entry in library.index(root, "model")["entries"]:
        if entry.get("state") == "withdrawn":  # out of the library (owner, 2026-10-21: every old model withdrawn)
            continue
        name, _, version = entry["address"].partition("/")[2].partition("@")
        record = library.entry(root, "model", name, version)
        provenance = record.get("provenance") or {}
        found.append({"address": entry["address"], "id": name, "place": provenance.get("place"),
                      "source": provenance.get("source_name") or name,
                      "tag": ((entry.get("tags") or {}).get("model") or [None])[0],
                      "today": reusable(entry, provenance, route)})
    return found


def reusable(entry, provenance, route):
    """Whether a model may be reused: the owner locked it, or the runner took it under `route` (today's)."""
    return entry.get("state") == "locked" or (provenance.get("route") == route and bool(provenance.get("accept")))


def source_row(model, rows_by_place):
    """The scene inventory row a library model was made for: its source name's row at its place, else its object
    kind's, else None."""
    rows = rows_by_place.get(model["place"]) or {}
    return rows.get(model["source"]) or rows.get(groups.object_kind(model["source"]))


def index(models, inventories):
    """{(object kind, size ratio): {"pipeline": [address], "old": [address], "code": [address]}} of the library
    models with a size: `pipeline` the reusable ones (today's route, or locked), the others remade; each under
    (object kind, None) too: a row with no size (a reading's) matches by its kind alone."""
    rows_by_place = {place: {row["id"]: row for row in record.get("rows", [])}
                     for place, record in inventories.items()}
    found = {}
    for model in models:
        row = source_row(model, rows_by_place)
        ratio = groups.size_ratio(row.get("size")) if row else None
        if ratio is None:
            continue
        made = "pipeline" if model["today"] else "old" if model["tag"] in PIPELINE_TAGS else "code"
        for key in ((groups.object_kind(model["source"]), ratio), (groups.object_kind(model["source"]), None)):
            found.setdefault(key, {name: [] for name in NO_MATCH})[made].append(model["address"])
    return found


def match(group, library):
    """{"pipeline": [address], "old": [address], "code": [address]} of the library models matching a group (none
    matched: all empty)."""
    kind, ratio, _ = group["key"]
    return library.get((kind, tuple(ratio) if ratio is not None else None), NO_MATCH)
