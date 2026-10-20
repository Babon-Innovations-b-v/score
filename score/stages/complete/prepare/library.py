"""Library first (#21 cut 1): a group whose model the creator's library already holds is reused, never bought. Read
only from the library's own model index (`<SCORE_LIB_ROOT>/index/model.json`) and each entry's record, through
`score.library` (ADR-0007); score never imports the library (score/stages/library's overlay).

A library model matches a group by object kind and size ratio (groups.model_key without the kit). The index names
no size, so a model's size is its source row's in the scene inventory it was made for (its record's `place` and
`source_name`, or that name's object kind); a model with no such row has no size and matches nothing. A model the
pipeline made from a picture (tags `prop`, `machine`, `crop`) is reusable; a code-built one (`piece`, or no tag) is
counted apart, since #19 sends code-built objects through the pipeline.
"""
from score import library
from score.stages.complete.prepare import groups

PIPELINE_TAGS = ("prop", "machine", "crop")


def library_models(root):
    """[{address, id, place, source, tag}] of the library's models, from its index and each entry's record."""
    found = []
    for entry in library.index(root, "model")["entries"]:
        name, _, version = entry["address"].partition("/")[2].partition("@")
        record = library.entry(root, "model", name, version)
        provenance = record.get("provenance") or {}
        found.append({"address": entry["address"], "id": name, "place": provenance.get("place"),
                      "source": provenance.get("source_name") or name,
                      "tag": ((entry.get("tags") or {}).get("model") or [None])[0]})
    return found


def source_row(model, rows_by_place):
    """The scene inventory row a library model was made for: its source name's row at its place, else its object
    kind's, else None."""
    rows = rows_by_place.get(model["place"]) or {}
    return rows.get(model["source"]) or rows.get(groups.object_kind(model["source"]))


def index(models, inventories):
    """{(object kind, size ratio): {"pipeline": [address], "code": [address]}} of the library models with a size."""
    rows_by_place = {place: {row["id"]: row for row in record.get("rows", [])}
                     for place, record in inventories.items()}
    found = {}
    for model in models:
        row = source_row(model, rows_by_place)
        ratio = groups.size_ratio(row.get("size")) if row else None
        if ratio is None:
            continue
        made = "pipeline" if model["tag"] in PIPELINE_TAGS else "code"
        key = (groups.object_kind(model["source"]), ratio)
        found.setdefault(key, {"pipeline": [], "code": []})[made].append(model["address"])
    return found


def match(group, library):
    """{"pipeline": [address], "code": [address]} of the library models matching a group (none matched: both
    empty)."""
    kind, ratio, _ = group["key"]
    return library.get((kind, tuple(ratio) if ratio is not None else None), {"pipeline": [], "code": []})
