"""A picture for every step whose output holds none of its own, made from that output's files on the store's machine
(the local source), never in a hosted process: a plan drawn from above with its items labelled, a settle's objects
at rest, the surfaces a list names as swatches, the painted takes three-quarter, a USD layer's prims over the place,
a sound's waveforms, whatever a JSON output places, else a tile per thing it names. The drawer is picked from the
files, never from the stage's name. Each picture is made once per output, one at a time, light (one thread), and
kept at <home>/previews/<output>.png; it is served and exported under PREVIEW_NAME with an id made from the output.

    path = previews.picture(files, plan, known, home, output, words)   # files: [(listed name, path)]
"""
import hashlib
import json
import os
import pathlib
import threading

for _threads in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_threads, "1")

from score.dashboard.previews import maps, paint, sheets, swatches  # noqa: E402

PREVIEW_NAME = "preview.png"
VERSION = "1"  # raise it when a drawer changes, so every cached picture is made again
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


def layer_files(files):
    return [(name, path) for name, path in files
            if pathlib.PurePosixPath(name).suffix in (".usda", ".usd", ".usdc")
            and not pathlib.PurePosixPath(name).parts[0] == "assets"]


def about_the_place(document, plan):
    """True for a JSON document that says it is about the plan's place: only those are drawn over it."""
    return isinstance(document, dict) and bool(plan) and document.get("place") == plan.get("place")


def named_things(document):
    """The names a document holds things under: a dict's keys whose values are records, else the names of its
    first list of records, else its keys; a list's items by their names."""
    if isinstance(document, list):
        return [maps.name_of(item, str(number)) if isinstance(item, dict) else str(item)
                for number, item in enumerate(document)]
    if not isinstance(document, dict):
        return []
    records = [key for key, value in document.items() if isinstance(value, dict)]
    if len(records) >= 2:
        return records
    listed = next((value for value in document.values() if isinstance(value, list) and value
                   and isinstance(value[0], dict)), None)
    return named_things(listed) if listed else list(document)


def tile_names(parsed, files):
    """What a tile sheet names: the things the largest JSON document holds, else the output's files."""
    if parsed:
        return named_things(max(parsed.values(), key=lambda document: len(json.dumps(document))))
    return [pathlib.PurePosixPath(name).name for name, _ in files if pathlib.PurePosixPath(name).name != "contract.json"]


def draw(files, plan, known, destination, words):
    """The first drawer the files call for; the path written."""
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
    found = finish_documents(parsed)
    if found:
        return swatches.picture(swatches.named_surfaces(found), known, destination)
    made = sheets.waveforms(files, destination)
    if made:
        return made
    placed = [spot for name, path in layer_files(files) for spot in maps.layer_positions(name, path)]
    placed = placed or [spot for document in parsed.values() if about_the_place(document, plan)
                        for spot in maps.positions(document)]
    placed = maps.inside(placed, plan)
    if len(placed) >= 2:
        return maps.positions_picture(placed, plan, words, destination)
    return sheets.tiles(tile_names(parsed, files), words, destination)


def picture(files, plan, known, home, output, words):
    """The output's preview, made once and kept; its path."""
    path = cached(home, output)
    if path.is_file():
        return path
    with _one_at_a_time:
        if not path.is_file():
            partial = path.with_name(path.stem + ".partial.png")
            draw(files, plan, known, partial, words)
            partial.replace(path)
    return path
