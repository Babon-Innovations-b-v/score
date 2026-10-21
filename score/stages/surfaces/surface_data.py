"""The surface stage's world data and the world files each row declares (Stage.files, a function of the place).

data/surfaces/<place>.json: the models a place's line paints, each under its raw take (`takes`: its place, kind,
object words and the places whose library it may take surfaces from, as the library names them), the name the
library knows the place by (`library`), its bake (`bake`: the model each take is baked as, and the make_chunky entries
written out where the route's own would not do; the job is written in the bake from git, bake_job.py), and the models
it lays that another place claims (`elsewhere`: {model: {take, place}}, read from that place's bake); a place with nothing to paint lists
no takes and says why (`nothing`). Every model is painted, the owner's picks included (a pick chooses the model,
never its old paint: owner, 2026-10-12), and each take by one place only: a model is painted once world-wide. A
designed place's surface data is its approved design's instead (DESIGN, `{home}/design/surfaces/<place>.json`, written
by prepare with its hand-in: score/stages/complete/prepare/handin.py), so its line paints the takes the estimate prices.

Kept apart from the rows' code on purpose: a paid row's code version hashes this module, so it stays small.
"""
import json
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[3]
FOLDER = REPO / "data/surfaces"
DESIGN = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "design" / "surfaces"
PIXAL = "{home}/work/pixal"


def designed(place):
    return (DESIGN / f"{place}.json").exists()


def path(place):
    return DESIGN / f"{place}.json" if designed(place) else FOLDER / f"{place}.json"


def pattern(place):
    return ("{home}/design/surfaces/" if designed(place) else "{data}/surfaces/") + f"{place}.json"


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


def take_patterns(place):
    """{name: pattern} of every raw-model file the method reads per take: the model, its close-up's folder and the
    finished model the paint lays it on."""
    return {f"{name} {take}": f"{PIXAL}/{take}{suffix}" for take in takes(place)
            for name, suffix in (("model", ".glb"), ("close-up", ".svviews"), ("finished", "-final.glb"))}


def take_files(place):
    """take_patterns' files that are there. A take with none is no stop here: the views row names it, or leaves it
    out as a batch gap (score/stages/batch_gaps.py), and the rows after it work on the takes it cast."""
    home = DESIGN.parents[1]
    return {name: pattern for name, pattern in take_patterns(place).items()
            if (home / pattern.replace("{home}/", "")).exists()}


def shape_files(place):
    """The world files of a row that reads no library surface (inputs, maps): the place's data and its takes' files.
    A library change never re-keys it; the maps read the lists' answers, not the library."""
    return {"surfaces": pattern(place), **take_files(place)}


def line_files(place):
    """The world files of a row that reads the library (lists, names, parts, paint, check): shape_files and the
    method's library (a scene's surfaces, tokens and wear are its surface-library's and scene palette's, inputs,
    never place.json)."""
    return {**shape_files(place), "library": "{data}/library"}


def parts_files(place):
    """The parts row's world files: line_files and the code its kit surfaces are read from (kit_surfaces.py and the
    builders' modules), so a finish takes the room's own kit surface. The old kits (data/kit) were retired (owner,
    2026-10-21): no kit is read."""
    builders = {f"kit builders {name}": "{repo}/tools/props/library/inside/" + name
                for name in ("pieces.py", "pieces_earth.py", "pieces_ship.py", "shapes.py")}
    return {**line_files(place), **builders, "kit surfaces": "{repo}/tools/props/library/kit_surfaces.py"}


# What bake_job.py writes a place's bake job from besides its own code (which the bake's code version hashes, the
# routes' with it): the kinds' details and the composites' children. The table keys each on the entries the place's
# models read (library_reads.narrowed), so one kind's edit re-keys only the bakes that read it. Both retired with the
# old models (owner, 2026-10-21): declared only while there, so no bake waits on a retired file by name.
BAKE_JOB_FILES = {"details": "{data}/library/details.json", "composites": "{data}/library/composites.json"}


def job_files(place, bake):
    """The world files a place's bake job is written from (BAKE_JOB_FILES and the place's scene inventory where it
    has one: its design's, else data/inventory's, the people line's; the old kits and per-place inventories were
    retired, owner, 2026-10-21); a place whose data has no bake blocks here, before anything is cleared: a path that
    is never there, naming it. A model no entry can be written for blocks the same way, declared in the table
    (library_reads.narrowed)."""
    if not bake:
        return {"bake job": pattern(place) + " names no bake"}
    found = {name: path for name, path in BAKE_JOB_FILES.items()
             if (REPO / "data" / path[len("{data}/"):]).is_file()}
    if (DESIGN.parent / "inventory" / f"{place}.json").exists():
        found["inventory"] = "{home}/design/inventory/" + f"{place}.json"
    elif (REPO / "data/inventory" / f"{place}.json").exists():
        found["inventory"] = "{data}/inventory/" + f"{place}.json"
    return found


def bake_files(place):
    """The bake row's world files: the place's data, what its bake job is written from (job_files), the data of each
    place that claims a model it lays, the bake's code and the library."""
    jobs = job_files(place, record(place).get("bake"))
    claimed = {f"claimed {claim['place']}": pattern(claim["place"])
               for claim in record(place).get("elsewhere", {}).values()}
    return {"surfaces": pattern(place), **jobs, **claimed, "library bake": "{repo}/tools/props/cloud/library_bake.py",
            "bake scripts": "{repo}/tools/props/library/inside", "library": "{data}/library"}
