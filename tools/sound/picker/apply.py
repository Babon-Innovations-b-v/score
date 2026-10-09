"""Each sound's take into the world: the chosen one (choose.py), or the owner's swap where the page's store holds one.
Its files go into the world's files under sound/generated/ (the local copy of the world's release,
tools/assets/world.py; the recordings before stay where they are, so a swap back is possible), its
credit onto the licence list (data/sound/licences.json) (a generated take's prompt, seed and model; a recording's source and author), and its
entry into data/sound/sounds.json: the file, and a level that plays it as loud as the brief says, or as loud as the
take it replaces played. A swap back to the recording before takes the data's file and level off again.

The swaps are the page's store, read back as JSON: {need: {"take": key, ...}} or the store's list of documents.
"""
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "loudness"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import loudness  # noqa: E402
import needs  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "assets"))
import world as world_assets  # noqa: E402

## Where a chosen take goes, under sound/generated/ in the world's files, by its category.
FOLDERS = {"steps": "footsteps", "shot": "doors", "loop": "machines", "room": "places"}
## The level a take is played at in the game when the brief names none and it replaces nothing, in LUFS.
LEVELS = {"steps": -55.0, "shot": -43.0, "loop": -52.0, "room": -47.0}


def documents(raw):
    """The store's documents as {need: body}, from its list or a plain map."""
    if isinstance(raw, list):
        return {document.get("id") or document.get("doc_id"): document.get("data", document) for document in raw}
    return raw


def picks_from(raw):
    """The swaps as {need: take key}."""
    return {name: body["take"] for name, body in documents(raw).items() if body and body.get("take")}


def chosen_with_swaps(record, swaps):
    """Every need's take to put in: the owner's swap where there is one, else the one chosen for it."""
    picks = {need["name"]: need["chosen"] for need in record["needs"] if need.get("chosen")}
    known = {need["name"]: {take["key"] for take in need["takes"]} | {f"game:{need['name']}"}
             for need in record["needs"]}
    picks.update({name: key for name, key in swaps.items() if key in known.get(name, set())})
    return picks


def generated_folder(world, need):
    """The folder a need's generated files go in."""
    return world / "sound" / "generated" / FOLDERS[need["category"]]


def world_files_for(need, take):
    """Where a take's files go in the world's files, as (page file, name) pairs: several steps, or one file."""
    folder = f"sound/generated/{FOLDERS[need['category']]}"
    if len(take["files"]) == 1:
        return [(take["files"][0], f"{folder}/{need['name']}{pathlib.Path(take['files'][0]).suffix}")]
    return [(page_file, f"{folder}/{need['name']}_{index + 1}{pathlib.Path(page_file).suffix}")
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
    """A sound's volume_db as the catalogue writes it, else the catalogue's default."""
    catalogue = needs.read_json(needs.CATALOGUE)
    return float(catalogue["sounds"].get(name, {}).get("volume_db", catalogue["defaults"]["volume_db"]))


def credit(take, name):
    """A take's line on the licence list: a generated take's model, prompt and seed; a recording's source."""
    source = take["page"]
    if take.get("prompt"):
        source = f"{take['page']}; prompt: {take['prompt']}; seed {take['seed']}"
    return {"file": name, "source": source, "author": take["author"], "licence": take["licence"]}


def apply(page_folder, picks, sounds_path=needs.SOUNDS, licences_path=needs.LICENCES, world=None, swapped=()):
    """Puts every pick on a page into the game, and notes on each entry which take it is and who chose it (the
    owner for the names in `swapped`, else the scoring); gives back the names changed. `world` is the folder of the
    world's files (the local copy of its release when not given)."""
    world = pathlib.Path(world) if world else world_assets.local_folder(world_assets.manifest())
    record = json.loads((page_folder / "candidates.json").read_text())
    document = json.loads(sounds_path.read_text())
    sounds = document["sounds"]
    listed = json.loads(licences_path.read_text())
    manifest = json.loads(loudness.MANIFEST.read_text()) if loudness.MANIFEST.exists() else {}
    changed = []
    for need in record["needs"]:
        key = picks.get(need["name"])
        take = next((candidate for candidate in need["takes"] if candidate["key"] == key), None)
        if take is None and key == f"game:{need['name']}":
            take = {"key": key, "source": "game"}
        if take is None:
            continue
        entry = sounds.setdefault(need["name"], {})
        already = entry.get("pick", {}).get("chosen", {}).get("take") == key and in_place(entry, world)
        entry.setdefault("pick", {})["chosen"] = {"take": key, "by": "owner" if need["name"] in swapped else "scoring"}
        if take["source"] == "game":
            remove_generated(need, listed, world)
            back_to_the_recording(entry, need)
            changed.append(need["name"])
            continue
        if already:
            continue
        level = played_level(need["name"], sounds, manifest, entry.get("pick", {}), need["category"])
        placed = place_files(page_folder, need, take, listed, world)
        loudest = max(take["measures"][page_file]["lufs"] for page_file in take["files"])
        entry["file"] = placed if len(placed) > 1 else placed[0]
        entry["volume_db"] = round(min(level - loudest, 0.0), 1)
        changed.append(need["name"])
    sounds_path.write_text(json.dumps(document, indent="\t", ensure_ascii=False) + "\n")
    licences_path.write_text(json.dumps(listed, indent="\t", ensure_ascii=False) + "\n")
    return changed


def back_to_the_recording(entry, need):
    """A sound back on the recording it had before: its own in the catalogue's script (the data's file and level
    come off), or, for a sound the layers added, the recording its brief names as its `before` (that sound's files
    and level)."""
    before = need.get("before", need["name"])
    if before == need["name"]:
        entry.pop("file", None)
        entry.pop("volume_db", None)
        return
    files = need.get("before_files") or needs.written_files().get(before, [])
    entry["file"] = files if len(files) > 1 else files[0]
    entry["volume_db"] = written_volume(before)


def in_place(entry, world):
    """Whether every file an entry names is on disk: a take already put in is left as it is (an Ogg file comes out
    with new bytes each time it is written, so writing it again would only churn the repository)."""
    named = entry.get("file") or []
    files = [named] if isinstance(named, str) else named
    return bool(files) and all((world / path).exists() for path in files)


def remove_generated(need, listed, world):
    """Takes a need's generated files out of the game and off the licence list."""
    folder = generated_folder(world, need)
    olds = [path for path in folder.glob(f"{need['name']}*") if path.suffix in (".ogg", ".wav")
            and (path.stem == need["name"] or path.stem.removeprefix(need["name"] + "_").isdigit())]
    for old in olds:
        name = old.relative_to(world).as_posix()
        listed[:] = [listing for listing in listed if listing["file"] != name]
        old.unlink()


def place_files(page_folder, need, take, listed, world):
    """Copies a take's files into the game and puts each on the licence list, in place of the need's files there
    before (a walk of eight steps replaced by one of six leaves no seventh)."""
    remove_generated(need, listed, world)
    placed = []
    for page_file, name in world_files_for(need, take):
        target = world / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(page_folder / page_file, target)
        listed[:] = [listing for listing in listed if listing["file"] != name]
        listed.append(credit(take, name))
        placed.append(name)
    return placed
