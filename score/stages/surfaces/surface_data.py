"""The surface stage's world data and the world files each row declares (Stage.files, a function of the place).

data/surfaces/<place>.json: the models a place's line paints, each under its raw take (`takes`: its place, kind,
object words and the places whose library it may take surfaces from, as the library names them), the name the
library knows the place by (`library`), its bake (`bake`: the model each take is baked as, and each model's
make_chunky entry written out; the job is written in the bake, bake_job.py), and the models
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


def job_files(place, bake):
    """A place whose data has no bake blocks here, before anything is cleared: a path that is never there, naming
    it. Its bake job is written from its data's entries alone (bake_job.py: a design's hand-in writes one for every
    model; the kit rooms' and outside places' entries, read from the old kits, inventories, kinds' details and
    composites, went with them, owner, 2026-10-21); a model with none blocks the same way, declared in the table
    (library_reads.narrowed)."""
    return {} if bake else {"bake job": pattern(place) + " names no bake"}


def bake_files(place):
    """The bake row's world files: the place's data, what its bake job is written from (job_files), the data of each
    place that claims a model it lays, the bake's code and the library."""
    jobs = job_files(place, record(place).get("bake"))
    claimed = {f"claimed {claim['place']}": pattern(claim["place"])
               for claim in record(place).get("elsewhere", {}).values()}
    return {"surfaces": pattern(place), **jobs, **claimed, "library bake": "{repo}/tools/props/cloud/library_bake.py",
            "bake scripts": "{repo}/tools/props/library/inside", "library": "{data}/library"}
