"""The sounds a picking page asks the owner for, made from the world's data in three layers, plus what the game
already plays:

1. **Surfaces** (data/sound/surfaces.json): every surface's footstep, impact and scrape.
2. **Rooms**: a room's tone (its place's ambience); its echo is worked out, not picked (game/sound/echo/).
3. **Things** (data/inventory/<room>.json): every row's `sound`, the hum, buzz or whir its things make.

A sound's brief for the page is its `pick` in data/sound/sounds.json: the page it is on, its category (which sets
the loudness its takes are brought to), where it plays in the game, and the searches the sources are asked. A
sound the layers name with no brief yet is listed by `--all`, so nothing the world names is forgotten.
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
    found = []
    for name, entry in sounds.items():
        brief = entry.get("pick", {})
        if brief.get("page") != page:
            continue
        found.append({"name": name, "category": brief["category"], "where": brief["where"],
                      "search": brief["search"], "loop": bool(brief.get("loop")), "level": brief.get("level"),
                      "now": current_files(name, sounds)})
    return found


def unbriefed(sounds_path=SOUNDS):
    """The sounds the layers name that no page asks for yet."""
    sounds = read_json(sounds_path)["sounds"]
    return {layer: [name for name in names if "pick" not in sounds.get(name, {})]
            for layer, names in layer_names().items()}


def licences_by_file(path=LICENCES):
    return {listing["file"]: listing for listing in read_json(path)}
