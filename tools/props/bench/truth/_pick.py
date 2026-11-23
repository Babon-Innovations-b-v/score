"""The benchmark's set (#162's rule): which adopted NVIDIA SimReady models the prop pipeline is scored against.

A kind takes an adopted model (`model/simready_*`, in force) when the first of its Wikidata classes is one of the kind's
classes and its id holds one of the kind's words at a word start (`(^|_)<word>`). Within a kind the ids are sorted by
`sha256("r162:" + id)`, the overlap targets left out, and the first `PER_KIND` taken, skipping an id whose stem (the
id without its trailing `_<letter><two digits>`) an earlier pick or an overlap target already holds. The first
`TUNE` picks are tune, the rest held out. The overlap targets are the adopted models a withdrawn model's replacement
chain ends at (#155, #157): each is tune and carries its withdrawn models.
"""
import hashlib
import re

from score import library

SALT = "r162:"
PER_KIND = 5
TUNE = 3
PREFIX = "simready_"
STEM = re.compile(r"_[a-z]\d\d$")
# kind: (Wikidata classes its first class must be one of, words its id must hold at a word start). #162's table.
KINDS = {
    "box": (("cardboard box", "box", "carton"), ("box",)),
    "crate": (("crate",), ("crate",)),
    "shelf / rack": (("rack with shelves", "shelf"), ("rack", "shelf", "shelving")),
    "cabinet / locker": (("cabinet", "kitchen cabinet", "storage cabinets & locker", "tool cabinets & chest",
                          "Tool cabinet"), ("cabinet", "locker")),
    "desk / table / bench": (("table", "workbench", "coffee table", "desk"), ("table", "workbench", "desk", "bench")),
    "chair / stool": (("chair", "office chair", "stool"), ("chair", "stool")),
    "monitor / keyboard": (("computer monitor", "computer terminal", "computer keyboard"),
                           ("monitor", "keyboard", "terminal")),
    "lamp body": (("lamp", "LED lamp", "task lighting", "light fixture"), ("lamp", "light")),
    "bin": (("waste container", "recycling bin"), ("bin", "trash", "recycle", "waste")),
    "ladder": (("ladder",), ("ladder",)),
    "sign (flat)": (("signage", "safety sign", "wet floor sign"), ("sign",)),
    "toolbox / tool cart": (("toolbox", "tool cart"), ("toolbox", "tool", "cart")),
    "fridge / stove / sink": (("refrigerator", "gas stove", "sink"), ("fridge", "refrigerator", "stove", "sink")),
    "hose / pipe (slender)": (("hose", "plastic pipe", "pipe"), ("hose", "pipe")),
    "tray (flat)": (("tray", "serving tray"), ("tray",)),
}
RULE = ("A kind takes an adopted model (model/simready_*, in force, its newest version) when the first of its Wikidata "
        "classes is one of the kind's classes and its id holds one of the kind's words at a word start ((^|_)word). "
        "Within a kind the ids are sorted by sha256('r162:' + id), the overlap targets left out, and the first 5 "
        "taken, skipping an id whose stem (the id without its trailing _<letter><two digits>) an earlier pick or an "
        "overlap target already holds; the first 3 are tune, the rest held out. The overlap targets are the adopted "
        "models a withdrawn model's replacement chain ends at (#155, #157), all tune, each with its withdrawn models.")


def stem(entry_id):
    """The id without its trailing variant (`_<letter><two digits>`)."""
    return STEM.sub("", entry_id)


def newest(records):
    """{id: its newest version's record} of the given entry records."""
    found = {}
    for record in records:
        if record["id"] not in found or record["version"] > found[record["id"]]["version"]:
            found[record["id"]] = record
    return found


def adopted(records):
    """{id: record} of the adopted NVIDIA models in force, each at its newest version."""
    models = newest(record for record in records if record["kind"] == "model" and record["id"].startswith(PREFIX))
    return {entry_id: record for entry_id, record in models.items() if record.get("state") != "withdrawn"}


def overlaps(root, records):
    """{target address: [withdrawn model addresses]} for each adopted model a withdrawn model's chain ends at."""
    found = {}
    for record in records:
        if record["kind"] != "model" or library.replacement(record) is None:
            continue
        end = library.replaced_end(root, record["address"])
        if end.split("/", 1)[1].startswith(PREFIX):
            found.setdefault(end, []).append(record["address"])
    return {target: sorted(found[target]) for target in sorted(found)}


def matches(record, classes, words):
    """Whether the record's first Wikidata class is one of `classes` and its id holds one of `words` at a word start."""
    named = (record.get("tags") or {}).get("wikidata_class") or []
    return bool(named) and named[0] in classes and any(re.search(r"(^|_)" + word, record["id"]) for word in words)


def kind_picks(models, classes, words, taken_stems):
    """(matching ids, the picks) of one kind: its ids in salted-hash order, a stem already taken skipped."""
    ids = sorted((entry_id for entry_id, record in models.items() if matches(record, classes, words)),
                 key=lambda entry_id: hashlib.sha256((SALT + entry_id).encode()).hexdigest())
    stems, picks = set(taken_stems), []
    for entry_id in ids:
        if stem(entry_id) in stems:
            continue
        stems.add(stem(entry_id))
        picks.append(entry_id)
        if len(picks) == PER_KIND:
            break
    return ids, picks


def picked(root, commit):
    """The set the rule gives on the library at `root` (its checkout at `commit`): {rule, score_lib_commit, kinds,
    objects}, each object {address, kind, split, withdrawn}."""
    records = library.entries(root)
    models = adopted(records)
    targets = overlaps(root, records)
    target_ids = {address.split("/", 1)[1].split("@")[0] for address in targets}
    pool = {entry_id: record for entry_id, record in models.items() if entry_id not in target_ids}
    target_stems = {stem(entry_id) for entry_id in target_ids}
    objects, kinds = [], {}
    for kind, (classes, words) in KINDS.items():
        ids, picks = kind_picks(pool, classes, words, target_stems)
        kinds[kind] = {"classes": list(classes), "words": list(words), "matching": len(ids)}
        objects += [{"address": models[entry_id]["address"], "kind": kind,
                     "split": "tune" if rank < TUNE else "held-out", "withdrawn": []}
                    for rank, entry_id in enumerate(picks)]
    objects += [{"address": target, "kind": "overlap", "split": "tune", "withdrawn": withdrawn}
                for target, withdrawn in targets.items()]
    return {"rule": RULE, "score_lib_commit": commit, "kinds": kinds, "objects": objects}
