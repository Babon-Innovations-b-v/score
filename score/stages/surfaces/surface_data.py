"""The surface stage's world data and the world files each row declares (Stage.files, a function of the place).

data/surfaces/<place>.json: the models a place's line paints, each under its raw take (`takes`: its place, kind,
object words and the places whose library it may take surfaces from, as the library names them), the name the
library knows the place by (`library`), its bake (`bake`: the route's make_chunky job, the model each take is baked
as, and entries the job lacks: another job's path, or the entry written out), and the models it lays that another
place claims (`elsewhere`: {model: {take, place}}, read from that place's bake); a place with nothing to paint lists
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


def line_files(place):
    """A free row's world files: the place's data, its takes' files and the library."""
    return {"surfaces": pattern(place), **take_files(place), "library": "{data}/library",
            "places": "{data}/definitions/place.json", "tokens": "{repo}/design/tokens/tokens.json"}


def bake_files(place):
    """The bake row's world files: the place's data, its bake jobs (a place whose data names none blocks here, before
    anything is cleared), the data of each place that claims a model it lays, the bake's code and the library."""
    bake = record(place).get("bake")
    jobs = {"bake job": bake["job"]} if bake else {"bake job": pattern(place) + " names no bake job"}
    jobs.update({f"bake job {model}": entry for model, entry in (bake or {}).get("entries", {}).items()
                 if isinstance(entry, str)})
    claimed = {f"claimed {claim['place']}": pattern(claim["place"])
               for claim in record(place).get("elsewhere", {}).values()}
    return {"surfaces": pattern(place), **jobs, **claimed, "library bake": "{repo}/tools/props/cloud/library_bake.py",
            "bake scripts": "{repo}/tools/props/library/inside", "library": "{data}/library"}
