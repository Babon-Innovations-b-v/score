"""The owner's picks into the game: for each need picked on a page, its take's files into game/sound/recordings/,
its credit on the licence list, its entry in data/sound/sounds.json (the file, and a level that plays it as loud
as the brief says, or as loud as the take it replaces played), and every sound file measured again for the
loudness manifest the game's test holds. A pick of the take in the game now changes nothing.

The picks are the page's store, read back as JSON: {need: {"take": key, ...}} or the store's list of documents.
"""
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "loudness"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import loudness  # noqa: E402
import needs  # noqa: E402

REPO = needs.REPO
## Where a picked take goes, by its category.
FOLDERS = {"steps": "footsteps", "shot": "doors", "loop": "machines", "room": "places"}
## The level a take is played at in the game when the brief names none and it replaces nothing, in LUFS.
LEVELS = {"steps": -55.0, "shot": -43.0, "loop": -52.0, "room": -47.0}


def picks_from(raw):
    """The picks as {need: take key}, from the store's documents or a plain map."""
    if isinstance(raw, list):
        raw = {document.get("id") or document.get("doc_id"): document.get("data", document) for document in raw}
    return {name: body["take"] for name, body in raw.items() if body and body.get("take")}


def game_files_for(need, take):
    """Where a take's files go in the game, as (page file, res:// path) pairs: several steps, or one file."""
    folder = FOLDERS[need["category"]]
    if len(take["files"]) == 1:
        return [(take["files"][0], f"res://game/sound/recordings/{folder}/{need['name']}.ogg")]
    return [(page_file, f"res://game/sound/recordings/{folder}/{need['name']}_{index + 1}.ogg")
            for index, page_file in enumerate(take["files"])]


def played_level(name, sounds, manifest, brief, category):
    """The loudness a sound should play at in the game: its brief's level, else the level of the take it replaces,
    else its category's."""
    if brief.get("level") is not None:
        return float(brief["level"])
    now = needs.current_files(name, sounds)
    if now and now[0] in manifest:
        volume = float(sounds.get(name, {}).get("volume_db", written_volume(name)))
        return float(manifest[now[0]]["lufs"]) + volume
    return LEVELS[category]


def written_volume(name):
    """A sound's volume_db as the catalogue's script writes it."""
    text = needs.CATALOGUE.read_text()
    found = re.search(rf'"{name}": \{{.*?VOLUME_DB: (-?[\d.]+)', text, re.S)
    return float(found.group(1)) if found else -12.0


def credit(take, res_path):
    """A take's line on the licence list."""
    return {"file": res_path, "source": take["page"], "author": take["author"], "licence": take["licence"]}


def apply(page_folder, picks, sounds_path=needs.SOUNDS, licences_path=needs.LICENCES, repo=REPO):
    """Puts every pick on a page into the game; gives back the names changed."""
    record = json.loads((page_folder / "candidates.json").read_text())
    document = json.loads(sounds_path.read_text())
    sounds = document["sounds"]
    listed = json.loads(licences_path.read_text())
    manifest = json.loads(loudness.MANIFEST.read_text()) if loudness.MANIFEST.exists() else {}
    changed = []
    for need in record["needs"]:
        key = picks.get(need["name"])
        take = next((candidate for candidate in need["takes"] if candidate["key"] == key), None)
        if take is None or take["source"] == "game":
            continue
        entry = sounds.setdefault(need["name"], {})
        level = played_level(need["name"], sounds, manifest, entry.get("pick", {}), need["category"])
        placed = place_files(page_folder, need, take, listed, repo)
        loudest = max(take["measures"][page_file]["lufs"] for page_file in take["files"])
        entry["file"] = placed if len(placed) > 1 else placed[0]
        entry["volume_db"] = round(min(level - loudest, 0.0), 1)
        changed.append(need["name"])
    sounds_path.write_text(json.dumps(document, indent="\t", ensure_ascii=False) + "\n")
    licences_path.write_text(json.dumps(listed, indent="\t", ensure_ascii=False) + "\n")
    return changed


def place_files(page_folder, need, take, listed, repo):
    """Copies a take's files into the game and puts each on the licence list in place of what was there."""
    placed = []
    for page_file, res_path in game_files_for(need, take):
        target = repo / res_path.removeprefix("res://")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(page_folder / page_file, target)
        listed[:] = [listing for listing in listed if listing["file"] != res_path]
        listed.append(credit(take, res_path))
        placed.append(res_path)
    return placed
