"""The surface stage's world data and the world files each row declares (Stage.files, a function of the place).

data/surfaces/<place>.json: the models a place's line paints, each under its raw take (`takes`: its place, kind,
object words and the places whose library it may take surfaces from, as the library names them), the name the
library knows the place by (`library`), its bake (`bake`: the model each take is baked as, and the make_chunky entries
written out where the route's own would not do; the job is written in the bake from git, bake_job.py), and the models
it lays that another place claims (`elsewhere`: {model: {take, place}}, read from that place's bake); a place with nothing to paint lists
no takes and says why (`nothing`). Every model is painted, the owner's picks included (a pick chooses the model,
never its old paint: owner, 2026-10-12), and each take by one place only: a model is painted once world-wide.

Kept apart from the rows' code on purpose: a paid row's code version hashes this module, so it stays small.
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
FOLDER = REPO / "data/surfaces"
PIXAL = "{home}/work/pixal"


def path(place):
    return FOLDER / f"{place}.json"


def pattern(place):
    return "{data}/surfaces/" + f"{place}.json"


def record(place):
    found = path(place)
    return json.loads(found.read_text()) if found.exists() else {}


def takes(place):
    """{take: entry} a place's data lists; none when it has no data (its rows then block on the missing file)."""
    return record(place).get("takes", {})


def paints(place):
    """False for a place whose data lists no takes (its file says why: every model is claimed by another place, or
    none is generated): its line has no surface rows. A place with no file paints, and blocks."""
    return not path(place).exists() or bool(takes(place))


def take_files(place):
    """{name: pattern} of every raw-model file the method reads per take: the model, its close-up's folder and the
    finished model the paint lays it on."""
    found = {}
    for take in takes(place):
        found[f"model {take}"] = f"{PIXAL}/{take}.glb"
        found[f"close-up {take}"] = f"{PIXAL}/{take}.svviews"
        found[f"finished {take}"] = f"{PIXAL}/{take}-final.glb"
    return found


def shape_files(place):
    """The world files of a row that reads no library surface (inputs, maps): the place's data and its takes' files.
    A library change never re-keys it; the maps read the lists' answers, not the library."""
    return {"surfaces": pattern(place), **take_files(place)}


def line_files(place):
    """The world files of a row that reads the library (lists, names, parts, paint, check): shape_files and the
    library, the places' surfaces and the palette."""
    return {**shape_files(place), "library": "{data}/library", "places": "{data}/definitions/place.json",
            "tokens": "{repo}/design/tokens/tokens.json"}


def parts_files(place):
    """The parts row's world files: line_files, the place's kit (where it has one) and the code its kit surfaces are
    read from (kit_surfaces.py and the builders' modules), so a finish takes the room's own kit surface."""
    kit = {"kit": "{data}/kit/" + place + ".json"} if (REPO / "data/kit" / f"{place}.json").exists() else {}
    builders = {f"kit builders {name}": "{repo}/tools/props/library/inside/" + name
                for name in ("pieces.py", "pieces_earth.py", "pieces_ship.py", "shapes.py")}
    return {**line_files(place), **kit, **builders, "kit surfaces": "{repo}/tools/props/library/kit_surfaces.py"}


# What bake_job.py writes a place's bake job from: the routes' code, the kinds' details and the composites' children.
BAKE_JOB_FILES = {"place route": "{repo}/tools/props/library/place_route.py",
                  "kit route": "{repo}/tools/props/library/route.py", "details": "{data}/library/details.json",
                  "composites": "{data}/library/composites.json"}


def read_data(folder, place):
    found = REPO / "data" / folder / f"{place}.json"
    return json.loads(found.read_text()) if found.exists() else {}


def unentered(place, bake):
    """The models a place bakes whose entry nothing in git gives (bake_job.entry_of would stop the bake on each): no
    entry written out, not laid in its kit (a piece, or a furniture or composite child model with its size) and, in
    an outside place (its kit says `on_seat`), no inventory row of its name."""
    kit, inventory = read_data("kit", place), read_data("inventory", place)
    laid = {piece.get("model") for piece in kit.get("pieces", [])}
    sized = {model for model, entry in kit.get("models", {}).items() if entry.get("size")}
    rows = {row["id"] for row in inventory.get("rows", [])} if "on_seat" in kit else set()
    return sorted(model for model in bake.get("models", {})
                  if not isinstance(bake.get("entries", {}).get(model), dict) and model not in laid | sized | rows)


def job_files(place, bake):
    """The world files a place's bake job is written from (BAKE_JOB_FILES, the place's kit and inventory where it has
    them); a place whose data has no bake, or a model no entry can be written for (unentered), blocks here, before
    anything is cleared: a path that is never there, naming it."""
    if not bake:
        return {"bake job": pattern(place) + " names no bake"}
    found = dict(BAKE_JOB_FILES)
    for folder in ("kit", "inventory"):
        if (REPO / "data" / folder / f"{place}.json").exists():
            found[folder] = "{data}/" + f"{folder}/{place}.json"
    found.update({f"bake entry {model}": pattern(place) + f" writes no entry for {model} and its kit lays none"
                  for model in unentered(place, bake)})
    return found


def bake_files(place):
    """The bake row's world files: the place's data, what its bake job is written from (job_files), the data of each
    place that claims a model it lays, the bake's code and the library."""
    jobs = job_files(place, record(place).get("bake"))
    claimed = {f"claimed {claim['place']}": pattern(claim["place"])
               for claim in record(place).get("elsewhere", {}).values()}
    return {"surfaces": pattern(place), **jobs, **claimed, "library bake": "{repo}/tools/props/cloud/library_bake.py",
            "bake scripts": "{repo}/tools/props/library/inside", "library": "{data}/library",
            "places": "{data}/definitions/place.json", "tokens": "{repo}/design/tokens/tokens.json"}
