"""The surface stage's world data and the world files each row declares (Stage.files, a function of the place).

data/surfaces/<place>.json: the models a place's line splits and paints, each under its raw take (`takes`: its
place, kind, object words and the places whose library it may take surfaces from, as the library names them), the
name the library knows the place by (`library`), and its bake (`bake`: the route's make_chunky job, the model each
take is baked as, and entries the job lacks: another job's path, or the entry written out). A take is split by one
place's line only. data/surfaces/finish-seed.json: the owner's picked models that seed the finish registry.

Kept apart from the rows' code on purpose: a paid row's code version hashes this module, so it stays small.
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
FOLDER = REPO / "data/surfaces"
SEED = "finish-seed"
PIXAL = "{home}/work/pixal"
SPLIT_SCRIPTS = {"turntable": {"turntable script": "{repo}/score/stages/surfaces/inside/turntable.py",
                               "blender runner": "{repo}/tools/props/cloud/blender_cloud.py"},
                 "unlit": {"delight worker": "{repo}/tools/props/cloud/delight_worker.py",
                           "delight setup": "{repo}/tools/props/cloud/delight_setup.sh"}}


def path(place):
    """A place's surface data file (the seed's for the seed rows, place None)."""
    return FOLDER / f"{place or SEED}.json"


def pattern(place):
    return "{data}/surfaces/" + (f"{place}.json" if place else f"{SEED}.json")


def takes(place):
    """{take: entry} a place's data lists; none when it has no data (its rows then block on the missing file)."""
    found = path(place)
    return json.loads(found.read_text())["takes"] if found.exists() else {}


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
    return {"surfaces": pattern(place), **take_files(place), "library": "{data}/library"}


def turntable_files(place):
    return {**SPLIT_SCRIPTS["turntable"], **take_files(place)}


def unlit_files(place):
    return {**SPLIT_SCRIPTS["unlit"], **take_files(place)}


def seed_files(place):
    """The seed rows' world files: the seed's data, each picked take's raw files and its stored paint."""
    return {**line_files(None), **{f"parts {take}": "{data}/parts/" + f"{take}.npz" for take in takes(None)}}


def bake_files(place):
    """The bake row's world files: the place's data, its bake jobs (a place whose data names none blocks here, before
    anything is cleared), the bake's code and the library."""
    found = path(place)
    bake = json.loads(found.read_text()).get("bake") if found.exists() else None
    jobs = {"bake job": bake["job"]} if bake else {"bake job": pattern(place) + " names no bake job"}
    jobs.update({f"bake job {model}": entry for model, entry in (bake or {}).get("entries", {}).items()
                 if isinstance(entry, str)})
    return {"surfaces": pattern(place), **jobs, "library bake": "{repo}/tools/props/cloud/library_bake.py",
            "bake scripts": "{repo}/tools/props/library/inside", "library": "{data}/library"}
