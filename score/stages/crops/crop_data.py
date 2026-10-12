"""The crops stage's world data and the world files each of its rows declares (Stage.files, a function of the place).

data/crops/<place>.json: the crop kinds a place's concept shows on its beds, each with its inventory row and the
nouns SAM 3 is asked for it by; the concept view and the plot's nouns and plan item (its size in metres); `beds`, the
prefix of the scene record's bed boxes the crops are laid on; `state`, what the beds show and whose decision that is.
A place with no file has no crop rows (`applies`).

Kept apart from the rows' code on purpose: every crop row's code version hashes this module, so it stays small.
"""
import contextlib
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
FOLDER = REPO / "data/crops"
# The SAM 3 runner and the script it copies up: imported inside the rows (tools()), so declared as files instead.
MASKS_TOOLS = {"masks": "{repo}/tools/props/scene/box_masks.py",
               "masks runner": "{repo}/tools/props/cloud/box_masks_cloud.py"}


@contextlib.contextmanager
def tools(*folders):
    """The prop tools' folders (under tools/) on the path while the block runs; the path as it was after. A folder
    left on the path at the table's import would add files to other stages' code versions (_code hashes a name's file
    in every folder on the path), so the rows import the tools inside it and declare the files they run instead."""
    kept = list(sys.path)
    sys.path[:0] = [str(REPO / "tools" / folder) for folder in folders]
    try:
        yield
    finally:
        sys.path[:] = kept


def pattern(place):
    return "{data}/crops/" + f"{place}.json"


def applies(place):
    """Whether the place's concept shows crops (it has a file)."""
    return (FOLDER / f"{place}.json").exists()


def record(place):
    return json.loads((FOLDER / f"{place}.json").read_text())


def concept_picture(place):
    """The pattern of the place's concept view the crop data names (WORK/ is the seeds' work folder)."""
    inventory = json.loads((REPO / "data/inventory" / f"{place}.json").read_text())
    wanted = record(place)["concept"]["view"]
    view = next(view for view in inventory["plan"]["views"] if view["id"] == wanted)
    return view["picture"].replace("WORK/", "{seeds}/")


def concept_files(place):
    """The concept row's files: the crop data, the concept view, the plan (the plot's size) and the SAM 3 script that
    runs on the rented card (not in the row's code version: it is copied up, not imported)."""
    if not applies(place):
        return {}
    return {"crops": pattern(place), "concept": concept_picture(place), "plan": "{data}/plans/" + f"{place}.json",
            **MASKS_TOOLS}


def layer_files(place):
    """The layer row's files: the crop data, the scene record (the beds), the inventory (the crop rows), the library
    and its theme (the baked models' surfaces) and the asset writer."""
    if not applies(place):
        return {}
    return {"crops": pattern(place), "scene": "{data}/scene/" + f"{place}.json",
            "inventory": "{data}/inventory/" + f"{place}.json", "library": "{data}/library",
            "places": "{data}/definitions/place.json", "tokens": "{repo}/design/tokens/tokens.json",
            "sounds": "{data}/sound/surfaces.json", "export": "{repo}/tools/usd"}


def look_files(place):
    """The look row's files: the crop data, the scene record (the beds it stands the crops on), the SAM 3 tools and
    the renderer."""
    if not applies(place):
        return {}
    return {"crops": pattern(place), "scene": "{data}/scene/" + f"{place}.json", **MASKS_TOOLS,
            "renderer": "{repo}/tools/blender/inside", "blender runner": "{repo}/tools/props/cloud/blender_cloud.py"}
