"""What the motion layer needs at a place, worked out free from its records (CONTEXT.md "gap"; the gaps check's layer
source, score/stages/complete/gaps/layers.py): every scene inventory row of a moving kind (data/checks/motion.json:
a row named for a kind's prims) that no game motion or rigid move moves and no `still` reason keeps standing, and
every motion need of the place (data/checks/contents.json `motion`: a word some motion's name must hold) that no record
names. Each is code work in words (a move or a reason written in the place's rigid record), never a guessed node:
nothing is made until the record says how the thing moves. Generic for any environment: kinds, rows and needs are
all environment data."""
import json
import pathlib
import re


def read(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else {}


def of_kind(name, prefix):
    """A prim or row named for a kind: the kind's prim name itself, or a row's object `<row>_<n>`."""
    return re.fullmatch(rf"{re.escape(prefix)}(_\d+)?", name) is not None


def moved_names(place, data):
    """(the last names of every prim the place's records move or keep still with a reason; the names a need is met
    by: every motion's name and every still prim's, as the completion gate's contents check reads them)."""
    data = pathlib.Path(data)
    rigid = read(data / f"motion/rigid/{place}.json")
    game = read(data / f"motion/{place}.json").get("motions", [])
    renamed = rigid.get("renamed", {})
    entries = [*game, *rigid.get("moves", [])]
    prims = [renamed.get(entry["prim"], entry["prim"]) for entry in entries if "prim" in entry]
    still = [name.rsplit("/", 1)[-1] for name, why in rigid.get("still", {}).items() if str(why).strip()]
    return ({path.rsplit("/", 1)[-1] for path in prims} | set(still),
            [entry.get("name", "") for entry in entries] + still)


def needs(place, data):
    """The place's motion needs no record answers: [{"kind": "move" | "need", "item", "about"}]."""
    data = pathlib.Path(data)
    kinds = read(data / "checks/motion.json").get("kinds", {})
    names, motions = moved_names(place, data)
    found = []
    for row in read(data / f"inventory/{place}.json").get("rows", []):
        kind = next((kind for kind, rule in kinds.items() if row["id"] in rule.get("prims", [])), None)
        if kind and not any(of_kind(name, row["id"]) or name == row["id"] for name in names):
            found.append({"kind": "move", "item": row["id"], "about": kind})
    for word in read(data / "checks/contents.json").get("places", {}).get(place, {}).get("motion", []):
        if not any(word in name for name in motions):
            found.append({"kind": "need", "item": word, "about": "data/checks/contents.json"})
    return found + old_records(place)


def old_records(place):
    """A designed place's motion records written for its old concept, whose rows therefore do not apply (the old
    concept's pictures and takes went with the old disk, 2026-10-19): [{"kind": "record", "item", "about"}]."""
    import score.stages.crops.crop_data as crop_data
    import score.stages.motion.models as models
    found = [{"kind": "record", "item": f"models:{take}", "about": f"data/motion/models/{place}.json names take {take}"}
             for take in models.old_takes(place)]
    if crop_data.old_concept(place):
        view = crop_data.record(place)["concept"]["view"]
        found.append({"kind": "record", "item": "crops", "about": f"data/crops/{place}.json reads concept view {view}"})
    return found


SENTENCES = {"move": "{item} is a {about} that nothing moves and no reason keeps still",
             "need": "the place must show {item} moving, and no motion of its records is {item}",
             "record": "{about}, of the place's old concept, not its approved design: its rows do not run"}
WORK = {"move": "a move for {item} in data/motion/rigid/{place}.json (a path, swing, spin or slide with its `from`), "
                "or its `still` reason",
        "need": "a motion named for {item} in data/motion/rigid/{place}.json, or the need dropped in "
                "data/checks/contents.json with the concept's reason",
        "record": "the record written again from the picked design: its rows and takes the design's hand-in "
                  "({{home}}/design/props/{place}.json), a crop data's view `design`"}


def gaps(place, data):
    """The place's motion gaps: [{"id", "prim", "sentence", "node", "work"}], each code work in words."""
    return [{"id": f"motion:{need['kind']}:{need['item']}", "prim": f"/{place}",
             "sentence": SENTENCES[need["kind"]].format(**need), "node": None,
             "work": WORK[need["kind"]].format(place=place, **need)} for need in needs(place, data)]
