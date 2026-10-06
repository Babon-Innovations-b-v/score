"""The sounds a picking page asks the owner for, made from the world's data in three layers, plus what the game
already plays:

1. **Surfaces** (data/sound/surfaces.json): every surface's footstep, impact and scrape.
2. **Rooms**: a room's tone (its place's ambience); its echo is worked out, not picked (game/sound/echo/).
3. **Things** (data/inventory/<room>.json): every row's `sound`, the hum, buzz or whir its things make.

A sound's brief is its `pick` in data/sound/sounds.json: the page it is on (`game`: every sound the game needs), its
category (which sets the loudness its takes are brought to), where it plays, the prompts MOSS is given with their
seeds and length, and the searches the optional CC0 sources are asked. Every sound the layers and the catalogue name
has a brief, but the warning tone and the low-oxygen beep, which the game makes itself to an exact shape
(tools/sound/made.py); `needs` lists any that has none.
"""
import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[3]
SOUNDS = REPO / "data" / "sound" / "sounds.json"
SURFACES = REPO / "data" / "sound" / "surfaces.json"
INVENTORIES = REPO / "data" / "inventory"
CATALOGUE = REPO / "game" / "sound" / "catalogue" / "sound_catalogue.gd"
LICENCES = REPO / "game" / "sound" / "licences" / "licences.json"
FOLDERS = {"RECORDINGS": "res://game/sound/recordings/", "MADE": "res://game/sound/made/"}


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def layer_names(surfaces=SURFACES, inventories=INVENTORIES):
    """Every sound name the three layers' data names, by layer."""
    named = {"surface": [], "thing": []}
    for sounds in read_json(surfaces)["surfaces"].values():
        for happening in ("footstep", "impact", "scrape"):
            if sounds.get(happening) and sounds[happening] not in named["surface"]:
                named["surface"].append(sounds[happening])
    for path in sorted(pathlib.Path(inventories).glob("*.json")):
        for row in read_json(path).get("rows", []):
            if row.get("sound") and row["sound"] not in named["thing"]:
                named["thing"].append(row["sound"])
    return named


def written_files(catalogue=CATALOGUE):
    """The file each sound written in the catalogue's script plays, by name (the first take of several)."""
    text = pathlib.Path(catalogue).read_text()
    found = {}
    for name, folder, relative in re.findall(r'"(\w+)": \{\s*FILE: \[?\s*(RECORDINGS|MADE) \+ "([^"]+)"', text):
        found[name] = [FOLDERS[folder] + relative]
    return found


def current_files(name, sounds=None, catalogue=CATALOGUE):
    """The files a sound plays today: the data's pick when there is one, else the catalogue's own."""
    entry = (sounds or read_json(SOUNDS)["sounds"]).get(name, {})
    if "file" in entry:
        return [entry["file"]] if isinstance(entry["file"], str) and entry["file"] else list(entry["file"])
    return written_files(catalogue).get(name, [])


def needs_for(page, sounds_path=SOUNDS):
    """The needs on one picking page, in the data's order: each sound's name and its brief."""
    sounds = read_json(sounds_path)["sounds"]
    before = written_files()
    found = []
    for name, entry in sounds.items():
        brief = entry.get("pick", {})
        if brief.get("page") != page:
            continue
        found.append({"name": name, "category": brief["category"], "where": brief["where"],
                      "search": brief.get("search", []), "loop": bool(brief.get("loop")),
                      "level": brief.get("level"), "seconds": float(brief.get("seconds", 8)),
                      "now": before.get(name, [])})
    return found


## The sounds the game makes itself to an exact shape, and never generates.
MADE_ONLY = ("warning_tone", "oxygen_low")


def unbriefed(sounds_path=SOUNDS):
    """The sounds the layers and the catalogue name that have no prompts yet, by where they are named."""
    sounds = read_json(sounds_path)["sounds"]
    named = dict(layer_names())
    named["catalogue"] = [name for name in catalogue_names() if name not in MADE_ONLY]
    return {where: [name for name in names if "prompts" not in sounds.get(name, {}).get("pick", {})]
            for where, names in named.items()}


def catalogue_names(catalogue=CATALOGUE):
    """Every sound the catalogue's script names."""
    return re.findall(r'^\t"(\w+)": ', pathlib.Path(catalogue).read_text(), re.M)


def licences_by_file(path=LICENCES):
    return {listing["file"]: listing for listing in read_json(path)}
