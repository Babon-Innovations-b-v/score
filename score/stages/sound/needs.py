"""What a place needs to be heard, worked out free from its own records (#29), and what answers each need:

    bed     its room tone: data/sound/places.json `loops` (or what the suit lets through, `heard_through`)
    event   each thing that moves (data/motion/<place>.json motions and data/motion/rigid/<place>.json moving things with a move: a
            slide, swing, path, spin, climb or turn; a motion that only lights is none): its own `sounds`, else the
            sounds data/sound/moving.json gives its name. Things moving exactly together (a hatch's wheel and window
            riding its leaf) are one event
    voice   the people of its cast (data/characters/<place>.json, counted off the concept): a sound of the place's
            `voices` (data/sound/places.json, each on one of them)

Each need is in one state: `library` (every sound named has a library file), `make` (a sound named has a brief with
prompts and no file: the sound row's batch makes it) or `none` (nothing named, or a name with neither file nor
brief): the gaps check (score/stages/complete/gaps) shows make and none as the place's sound gaps.
"""
import json
import pathlib

from score.stages.sound import moving

MOVES = ("slide", "swing", "path", "spin", "climb", "turn")
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
        moves = {key: entry[key] for key in MOVES if key in entry}
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


def event_sounds(event, table):
    """The sounds an event plays: each entry's own, else the moving sounds table's for its name."""
    named = []
    for entry in event["entries"]:
        own = entry.get("sounds") or (moving.sounds_for(entry["name"], table.get(entry["table"], {})) or {}).get(
            "sounds", [])
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


def needs(place, data):
    """Every sound need of the place: [{"kind", "item", "prim", "sounds", "state"}]."""
    data = pathlib.Path(data)
    record = read(data / "sound/places.json").get("places", {}).get(place, {})
    catalogue = read(data / "sound/catalogue.json").get("sounds", {})
    sounds = read(data / "sound/sounds.json").get("sounds", {})
    rigid_record = read(data / f"motion/rigid/{place}.json")
    found = []
    bed = record.get("loops", []) + record.get("heard_through", [])
    found.append({"kind": "bed", "item": "room", "prim": f"/{place}", "sounds": bed})
    for event in events(read(data / f"motion/{place}.json").get("motions", []), rigid_record.get("moves", []),
                        rigid_record.get("renamed", {})):
        found.append({"kind": "event", "item": event["name"], "prim": event["prims"][0],
                      "sounds": event_sounds(event, read(data / "sound/moving.json"))})
    cast = people(read(data / f"characters/{place}.json"))
    if cast:
        found.append({"kind": "voice", "item": "people", "prim": f"/{place}/Characters/{cast[0]}",
                      "sounds": [voice["sound"] for voice in record.get("voices", []) if voice["on"] in cast]})
    return [dict(need, state=state_of(need["sounds"], catalogue, sounds)) for need in found]


SENTENCES = {"bed": "no room tone", "event": "{item} moves without a sound", "voice": "people here, no voice"}
WORK = {"bed": "name the place's room tone in data/sound/places.json loops: a library sound first, else a brief in "
                "data/sound/sounds.json",
        "event": "name {item}'s sound in data/sound/moving.json: a library sound first, else a brief in "
                 "data/sound/sounds.json",
        "voice": "name a voice on one of the place's people in data/sound/places.json voices: a library sound first, "
                 "else a brief in data/sound/sounds.json"}


def gaps(place, data):
    """The place's sound needs not answered from the library: [{"id", "prim", "sentence", "node", "work"}], one the
    sound row makes naming its node (`sound@<place>`), one with nothing to make naming its work."""
    found = []
    makes = place in read(pathlib.Path(data) / "sound/places.json").get("places", {})
    for need in needs(place, data):
        if need["state"] == LIBRARY:
            continue
        sentence = SENTENCES[need["kind"]].format(item=need["item"])
        made_here = need["state"] == MAKE and makes
        if need["state"] == MAKE:
            sentence += f" from the library: {', '.join(need['sounds'])} still to make"
        found.append({"id": f"sound:{need['kind']}:{need['item']}", "prim": need["prim"], "sentence": sentence,
                      "node": f"sound@{place}" if made_here else None,
                      "work": None if made_here else WORK[need["kind"]].format(item=need["item"])})
    return found
