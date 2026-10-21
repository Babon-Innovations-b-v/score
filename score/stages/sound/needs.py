"""What a place needs to be heard, worked out free from its own records (#29), and what answers each need:

    bed     its room tone, or what the suit lets through outside where no air carries sound: worked out from its
            design (beds.py), never listed per place
    event   each thing that moves (data/motion/<place>.json motions and data/motion/rigid/<place>.json moving things with a move: a
            slide, swing, path, spin, climb or turn; a motion that only lights is none): its own `sounds`, else the
            sounds data/sound/moving.json gives its row kind's move (moving.sounds_for: the kind of its scene inventory
            row, inventory_of, by data/checks/row-kinds.json). Things moving exactly together (a hatch's wheel and window
            riding its leaf) are one event
    voice   the people of its cast (data/characters/<place>.json, counted off the concept): the people's voice
            (data/sound/voices.json), on the first of them

Each need is in one state: `library` (every sound named has a library file), `make` (a sound named has a brief with
prompts and no file: the sound row's batch makes it) or `none` (nothing named, or a name with neither file nor
brief): the gaps check (score/stages/complete/gaps) shows make and none as the place's sound gaps.
"""
import json
import pathlib
import sys

from score.stages.sound import beds
from score.stages.sound import moving

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/usd"))
import stage_inputs  # noqa: E402

LIBRARY, MAKE, NONE = "library", "make", "none"


def read(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text()) if path.exists() else {}


def events(motions, rigid, renamed):
    """Each thing that moves, as one event: [{"name", "prims", "entries"}], a thing moving exactly as one before it
    joining that one's event; its prims are its record's and the one the place renamed it to."""
    found, by_move = [], {}
    for entry in [*(dict(motion, table="motions") for motion in motions),
                  *(dict(move, table="moves") for move in rigid)]:
        moves = {key: entry[key] for key in moving.MOVES if key in entry}
        if not moves:
            continue
        key = json.dumps([moves, entry.get("start"), entry.get("length")], sort_keys=True)
        prims = [entry["prim"]] + ([renamed[entry["prim"]]] if entry["prim"] in renamed else [])
        if key not in by_move:
            by_move[key] = {"name": entry["name"], "prims": [], "entries": []}
            found.append(by_move[key])
        by_move[key]["prims"] += prims
        by_move[key]["entries"].append(entry)
    return found


def people(cast):
    """The names of the people a cast record stands in the place."""
    return [person["name"] for person in cast.get("people", [])]


def event_sounds(event, rows, kinds, table):
    """The sounds an event plays: each entry's own, else the moving sounds table's for its row kind and move."""
    named = []
    for entry in event["entries"]:
        own = entry.get("sounds") or (moving.sounds_for(entry, rows, kinds, table) or {}).get("sounds", [])
        named += [sound["name"] for sound in own]
    return list(dict.fromkeys(named))


def state_of(names, catalogue, sounds):
    """A need's state from the sounds named for it."""
    def has_file(name):
        return bool(sounds.get(name, {}).get("file") or catalogue.get(name, {}).get("file"))

    def briefed(name):
        return bool(sounds.get(name, {}).get("pick", {}).get("prompts"))
    if not names or any(not has_file(name) and not briefed(name) for name in names):
        return NONE
    return LIBRARY if all(has_file(name) for name in names) else MAKE


def inventory_of(place, data, design=beds.DESIGN):
    """The place's scene inventory: the creator's kept one (under `design`), else data/'s."""
    kept = design / "inventory" / f"{place}.json"
    return kept if kept.is_file() else pathlib.Path(data) / "inventory" / stage_inputs.inventory_path(place).name


def needs(place, data, design=beds.DESIGN):
    """Every sound need of the place: [{"kind", "item", "prim", "sounds", "state"}], the bed's with what its design
    does not give (`missing`)."""
    data = pathlib.Path(data)
    voice = read(data / "sound/voices.json").get("people")
    catalogue = read(data / "sound/catalogue.json").get("sounds", {})
    sounds = read(data / "sound/sounds.json").get("sounds", {})
    rigid_record = read(data / f"motion/rigid/{place}.json")
    rows = read(inventory_of(place, data, design)).get("rows", [])
    kinds, table = read(data / "checks/row-kinds.json").get("kinds", {}), read(data / "sound/moving.json")
    found = []
    bed = beds.of_place(place, beds.paths(place, data, design))
    found.append({"kind": "bed", "item": "room", "prim": f"/{place}", "sounds": bed["sounds"],
                  "missing": bed["facts"]["missing"]})
    for event in events(read(data / f"motion/{place}.json").get("motions", []), rigid_record.get("moves", []),
                        rigid_record.get("renamed", {})):
        found.append({"kind": "event", "item": event["name"], "prim": event["prims"][0],
                      "sounds": event_sounds(event, rows, kinds, table)})
    cast = people(read(data / f"characters/{place}.json"))
    if cast:
        found.append({"kind": "voice", "item": "people", "prim": f"/{place}/Characters/{cast[0]}",
                      "sounds": [voice] if voice else []})
    return [dict(need, state=state_of(need["sounds"], catalogue, sounds)) for need in found]


SENTENCES = {"bed": "no room tone", "event": "{item} moves without a sound", "voice": "people here, no voice"}
WORK = {"bed": "a library bed whose brief fits the place (`bed` in data/sound/sounds.json: how it is heard, and the "
               "shell, ground, shape, nouns or row kinds it asks), else a new brief there",
        "design": "its design: {missing}",
        "event": "give {item}'s inventory row a kind (data/checks/row-kinds.json) and that kind's move its sound in "
                 "data/sound/moving.json: a library sound first, else a brief in data/sound/sounds.json",
        "voice": "name the people's voice in data/sound/voices.json: a library sound first, else a brief in "
                 "data/sound/sounds.json"}


def gaps(place, data, design=beds.DESIGN):
    """The place's sound needs not answered from the library: [{"id", "prim", "sentence", "node", "work"}], one the
    sound row makes naming its node (`sound@<place>`), one with nothing to make naming its work (a bed its design does
    not decide names what the design lacks)."""
    found = []
    makes = place in beds.places(data, design)
    for need in needs(place, data, design):
        if need["state"] == LIBRARY:
            continue
        sentence = SENTENCES[need["kind"]].format(item=need["item"])
        made_here = need["state"] == MAKE and makes
        if need["state"] == MAKE:
            sentence += f" from the library: {', '.join(need['sounds'])} still to make"
        found.append({"id": f"sound:{need['kind']}:{need['item']}", "prim": need["prim"], "sentence": sentence,
                      "node": f"sound@{place}" if made_here else None,
                      "work": None if made_here else work_of(need)})
    return found


def work_of(need):
    """What answers a need with nothing to make: a bed its design does not decide names what the design lacks."""
    if need.get("missing"):
        return WORK["design"].format(missing="; ".join(need["missing"]))
    return WORK[need["kind"]].format(item=need["item"])
