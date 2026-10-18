"""A picture for every step whose output holds none of its own, made from that output's files on the store's machine
(the local source), never in a hosted process: a plan drawn from above with its items labelled, a settle's objects
at rest, the painted takes three-quarter, a surface check's library colours over its baked ones, the surfaces a list
names as swatches, a sound's waveforms, what a USD layer moves (its routes) or places over the place, whatever a JSON
output places, the models it names by hash, the pictures its records point at, else a tile per thing it names. The
drawer is picked from the files, never from the stage's name. Each picture is made once per output, one at a time,
light (one thread), and kept at <home>/previews/<VERSION>/<output>.png; it is served and exported under PREVIEW_NAME with an id made from the output.

    path = previews.picture(files, plan, known, home, output, words, elsewhere)   # files: [(listed name, path)]
"""
import hashlib
import json
import os
import pathlib
import threading

for _threads in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_threads, "1")

from score.dashboard.previews import checks, crops, maps, meshes, paint, sheets, swatches  # noqa: E402
from score.dashboard.state.files import packaged  # noqa: E402
from score.dashboard.state.versions import SHORT, code_version  # noqa: E402

PREVIEW_NAME = "preview.png"
# the drawers' code version: a change to any drawer makes every cached picture again
VERSION = f"5-{code_version([pathlib.Path(__file__).parent])[:SHORT]}"
LARGEST_JSON = 4 * 1024 * 1024
_one_at_a_time = threading.Lock()


def preview_id(output):
    """The 64-hex id a preview is served and exported under, made from its output."""
    return hashlib.sha256(f"score-dashboard-preview-{VERSION}:{output}".encode()).hexdigest()


def cached(home, output):
    return pathlib.Path(home) / "previews" / VERSION / f"{output}.png"


def documents(files):
    """{listed name: parsed JSON} of the output's JSON files (its contract and anything too large left out)."""
    found = {}
    for name, path in files:
        if not name.endswith(".json") or pathlib.PurePosixPath(name).name == "contract.json":
            continue
        if pathlib.Path(path).stat().st_size > LARGEST_JSON:
            continue
        try:
            found[name] = json.loads(pathlib.Path(path).read_text())
        except (OSError, ValueError):
            continue
    return found


def plan_document(parsed):
    return next((document for document in parsed.values()
                 if isinstance(document, dict) and "walls" in document and "items" in document), None)


def settle_document(parsed):
    return next((document for document in parsed.values() if isinstance(document, dict) and isinstance(
        document.get("objects"), dict) and any(isinstance(item, dict) and "matrix" in item and "rested" in item
                                               for item in document["objects"].values())), None)


def finish_documents(parsed):
    return [document for document in parsed.values() if isinstance(document, dict) and document.get("finishes")]


def own_files(files):
    return [(name, path) for name, path in files if not packaged(name)]


def layer_files(files):
    return [(name, path) for name, path in own_files(files)
            if pathlib.PurePosixPath(name).suffix in (".usda", ".usd", ".usdc")]


def about_the_place(document, plan):
    """True for a JSON document that says it is about the plan's place: only those are drawn over it."""
    return isinstance(document, dict) and bool(plan) and document.get("place") == plan.get("place")


def record_name(key, value):
    """A tile's name for a record: its key, said missing when the record says what it lacks."""
    return f"{key}: missing" if isinstance(value, dict) and value.get("missing") else key


def named_things(document):
    """The names a document holds things under: a dict's keys whose values are records (or those of its one value
    that holds records), else the names of its first list of records, else its keys; a list's items by their
    names."""
    if isinstance(document, list):
        return [maps.name_of(item, str(number)) if isinstance(item, dict) else str(item)
                for number, item in enumerate(document)]
    if not isinstance(document, dict):
        return []
    records = [key for key, value in document.items() if isinstance(value, dict)]
    if len(records) >= 2:
        return [record_name(key, document[key]) for key in records]
    if len(records) == 1 and len(named_things(document[records[0]])) >= 2:
        return named_things(document[records[0]])
    listed = next((value for value in document.values() if isinstance(value, list) and value
                   and isinstance(value[0], dict)), None)
    return named_things(listed) if listed else [f"{key}: {said(value)}" for key, value in document.items()]


def said(value):
    """A field's value in a few words: a count for a list or a record, a hash shortened, else the value itself."""
    if isinstance(value, (list, dict)):
        return str(len(value))
    return f"{value[:8]}..." if isinstance(value, str) and meshes.SHA.match(value) else str(value)


def tile_names(parsed, files):
    """What a tile sheet names: the things of the JSON document that names the most by name (not by number), else
    the output's files."""
    named = [[name for name in named_things(document) if not str(name).isdigit()] for document in parsed.values()]
    named = [names for names in named if names]
    if named:
        return max(named, key=len)
    return [pathlib.PurePosixPath(name).name for name, _ in files if pathlib.PurePosixPath(name).name != "contract.json"]


def draw(files, plan, known, destination, words, elsewhere=()):
    """The first drawer the files call for; the path written. `elsewhere` are the folders where the store's machine
    keeps the models an output names by hash."""
    parsed = documents(files)
    found = plan_document(parsed)
    if found:
        return maps.plan_picture(found, destination)
    found = settle_document(parsed)
    if found:
        return maps.settle_picture(found, plan, destination)
    made = paint.picture(files, known, destination)
    if made:
        return made
    found = [model for document in parsed.values() for model in checks.checked(document)]
    if found:
        return checks.picture(found, destination)
    found = finish_documents(parsed)
    if found:
        return swatches.picture(swatches.named_surfaces(found), known, destination)
    made = sheets.waveforms(own_files(files), destination)
    if made:
        return made
    return drawn_over_the_place(files, parsed, plan, words, destination) or drawn_from_records(
        files, parsed, words, destination, elsewhere)


def stage_root(files):
    """True when the output holds a whole OpenUSD stage: a top-level .usda that sublayers others."""
    for name, path in own_files(files):
        if "/" not in name and name.endswith(".usda") and pathlib.Path(path).stat().st_size < LARGEST_JSON:
            if "subLayers" in pathlib.Path(path).read_text(errors="replace"):
                return True
    return False


def drawn_over_the_place(files, parsed, plan, words, destination):
    """What a layer places and moves (each route), else what the output places, over the place (a whole stage
    large, over the plan's labelled items); the path, or None when it moves nothing and places fewer than two things
    there."""
    routes = [route for name, path in layer_files(files) for route in maps.layer_paths(name, path)]
    moving = {name for name, _ in routes}
    placed = [spot for name, path in layer_files(files) for spot in maps.layer_positions(name, path)
              if spot[0] not in moving]
    placed = placed or [spot for document in parsed.values() if about_the_place(document, plan)
                        for spot in maps.positions(document)]
    placed = maps.inside(placed, plan)
    if not routes and len(placed) < 2:
        return None
    if stage_root(files):
        return maps.stage_picture(placed, routes, plan, words, destination)
    return maps.positions_picture(placed, routes, plan, words, destination)


def drawn_from_records(files, parsed, words, destination, elsewhere):
    """The models the output names by hash, else the pictures its records point at, else a tile per thing it
    names; the path."""
    for document in parsed.values():
        made = meshes.picture(document, elsewhere, destination)
        if made:
            return made
    found = [pointed for document in parsed.values() for pointed in crops.pointed(document)]
    if found:
        return crops.picture(found, destination)
    return sheets.tiles(tile_names(parsed, files), words, destination)


def picture(files, plan, known, home, output, words, elsewhere=()):
    """The output's preview, made once and kept; its path."""
    path = cached(home, output)
    if path.is_file():
        return path
    with _one_at_a_time:
        if not path.is_file():
            partial = path.with_name(path.stem + ".partial.png")
            draw(files, plan, known, partial, words, elsewhere)
            partial.replace(path)
    return path
