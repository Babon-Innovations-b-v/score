"""The prop route's world data, the world files each of its rows declares (Stage.files, a function of the place) and
the way its rows reach the prop tools.

data/props/<place>.json: the objects a place makes by the prop route first (the owner's decision of 2026-10-12: every
object goes the prop route first, and only one whose measured checks fail is built in code and checked again):

    {"place": "hub", "order": "prop-first" | "code-first",
     "objects": {<inventory row>: {"route": "prop", "take": <raw model's name>, "closeup": <picture, optional>}
                                  | {"route": "code", "code_model": <the code build's .gltf>, "closeup": <...>}},
     "fallback": {<row>: <the code build's .gltf> | null}}

`closeup` names a close-up already drawn (a pattern, as the files below); without one the close-up row draws it from
the row's box in its concept view. `fallback` holds the prop objects that failed their checks, each with its code
build (null: no builder yet, an agent must write one); the paid rows read only the prop objects' part of the file, so
moving an object there re-makes no paid row. A place with no file has no prop-route rows (`applies`): no world 1 place
has one yet. FOLDER is the repository's; the comparison (compare.py) points it, and the surface stage's, at its own
copy of the data.

The rows import the prop tools inside their functions, under `tools()`, which puts the tools' folders on the path
and takes them off again: a folder left on the path at the table's import adds files to other stages' code versions
(_code hashes a name's file in every folder on the path), and moves their keys. So their code versions miss the
tools, and each row declares the tool files it runs as world files instead (`*_TOOLS`), as the surface bake does.

Kept apart from the rows' code on purpose: every row's code version hashes this module, so it stays small.
"""
import contextlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
FOLDER = REPO / "data/props"
INPUTS_TOOLS = {"close-up stage": "{repo}/tools/props/closeup", "box check": "{repo}/tools/props/scene/box_check.py"}
CLOSEUP_TOOLS = {"close-up stage": "{repo}/tools/props/closeup", "google spend": "{repo}/tools/props/cloud/google_spend.py"}
PIXAL_TOOLS = {"batch": "{repo}/tools/props/cloud/batch.py", "pixal": "{repo}/tools/props/pixal.py"}
LIKENESS_TOOLS = {"compare": "{repo}/tools/usd/compare.py", "glb file": "{repo}/tools/props/glb_file.py",
                  "model gate": "{repo}/tools/props/gates/model.py", "sorter": "{repo}/tools/props/library/sorter.py",
                  "straight": "{repo}/tools/props/library/straight.py", "fittings": "{data}/library/fittings.json",
                  "similar": "{repo}/tools/props/cloud/similar.py"}


@contextlib.contextmanager
def tools(*folders):
    """The prop tools' folders (under tools/) on the path while the block runs; the path as it was after."""
    kept = list(sys.path)
    sys.path[:0] = [str(REPO / "tools" / folder) for folder in folders]
    try:
        yield
    finally:
        sys.path[:] = kept


def pattern(place):
    return "{data}/props/" + f"{place}.json"


def record_at(path):
    return json.loads(pathlib.Path(path).read_text())


def applies(place):
    """Whether the place makes objects by the prop route (it has a file)."""
    return (FOLDER / f"{place}.json").exists()


def objects(place):
    """{row: entry} of the place's file; none without one."""
    return record_at(FOLDER / f"{place}.json")["objects"] if applies(place) else {}


def prop_objects(record):
    """{row: entry} of the objects a record sends the prop route."""
    return {row: entry for row, entry in record["objects"].items() if entry["route"] == "prop"}


def prop_part(path):
    """The part of a place's file the Pixal3D row reads: its prop objects' takes, so a change to the code objects or
    the fallback moves no paid row's key."""
    return json.dumps({row: entry["take"] for row, entry in prop_objects(record_at(path)).items()}, sort_keys=True)


def closeup_files(place):
    """{name: pattern} of every close-up the place's file names."""
    return {f"close-up {row}": entry["closeup"] for row, entry in objects(place).items() if entry.get("closeup")}


def view_files(place):
    """{name: pattern} of the place's concept views (WORK/ is the seeds' work folder)."""
    inventory = FOLDER.parent / "inventory" / f"{place}.json"
    views = record_at(inventory)["plan"]["views"] if inventory.exists() else []
    return {f"view {view['id']}": view["picture"].replace("WORK/", "{seeds}/") for view in views}


def inputs_files(place):
    """The inputs row's files: the place's file, its inventory and concept views, every close-up named, the inventory
    folder (the box gate reads the scene's inventory) and its tools."""
    return {"props": pattern(place), "inventory": "{data}/inventory/" + f"{place}.json",
            "inventories": "{data}/inventory", **view_files(place), **closeup_files(place), **INPUTS_TOOLS}


def closeup_row_files(place):
    """The close-up row's files: its tools (what it draws is in the inputs row's output)."""
    return dict(CLOSEUP_TOOLS)


def pixal_files(place):
    """The Pixal3D row's: the prop objects' takes, the place's inventory (the batch builds only its rows), the place's
    surface data, which must list every take it makes, and its tools."""
    return {"props": (pattern(place), prop_part), "inventory": "{data}/inventory/" + f"{place}.json",
            "surfaces": "{data}/surfaces/" + f"{place}.json", **PIXAL_TOOLS}


def likeness_files(place):
    """The likeness row's: the place's whole file, its inventory, every code build it names, the kinds' details
    (which kinds must stand square) and its tools."""
    record = record_at(FOLDER / f"{place}.json") if applies(place) else {"objects": {}, "fallback": {}}
    builds = {row: entry["code_model"] for row, entry in record["objects"].items() if entry["route"] == "code"}
    builds.update({row: model for row, model in record.get("fallback", {}).items() if model})
    return {"props": pattern(place), "inventory": "{data}/inventory/" + f"{place}.json",
            "details": "{data}/library/details.json", **LIKENESS_TOOLS,
            **{f"code build {row}": model for row, model in builds.items()},
            **{f"code build {row} buffer": model.removesuffix(".gltf") + ".bin" for row, model in builds.items()}}
