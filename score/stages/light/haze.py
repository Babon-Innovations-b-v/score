"""The light stage's second paid row, light-haze (a place whose kit lays a lamp with a shaft, `shafted_kinds`: a
glowing row its plan aims, the library's aimed lamp): the same render as light-passes with the shafts' haze left out, so the light row can tell what the haze lays
over the place (the veil) from what the floodlights light on its floor, which one render cannot (the captain,
2026-10-12, after the square's veil read 0.097 with its floodlights' floor light in it). Its own module, so
light-passes keeps its key.
"""
import json
import pathlib
import shutil

import score.stages.light.passes as passes  # this form: the code version then leaves __init__ out

# Four to eight views on one rented card, as light-passes.
EUROS = 2.0
LAMPS = passes.REPO / "data/library/lamps.json"


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def glowing(inventory_path):
    """The ids of an inventory's rows whose row kind glows (score/stages/row_kinds.py): its lamps."""
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # score/stages, never a test's repo
    import row_kinds
    return {row["id"] for row in row_kinds.rows_that(read(inventory_path), "glows", row_kinds.table())}


def shafted_rows(place):
    """The rows of the place whose lamps light a shaft of haze (its floodlights): each inventory row whose row kind
    glows that the place's plan aims (`aims`), the library's aimed lamp, when that lamp has a shaft
    (data/library/lamps.json), as the scene-record row lights them (scene_record/kit_shell)."""
    plan = passes.plan_of(place)
    inventory = passes.KEPT / "inventory" / f"{place}.json"  # the design's scene inventory
    if not plan or not plan.get("aims") or not inventory.is_file() or not read(LAMPS)["aimed"].get("shaft"):
        return set()
    return glowing(inventory) & set(plan["aims"])


def shafted_kinds(place, kit):
    """The kit kinds `kit` lays (the place's design kit, earth_seed's kit.json) of its shafted rows, each laid as
    `<room>_<row>`."""
    kinds = {f"{kit.get('room', place)}_{row}" for row in shafted_rows(place)}
    return kinds & {laid["kind"] for laid in kit["pieces"]}


def design_kit(place):
    """The place's kit as its design lays it (earth_seed's kit.json): no piece. The old kits (data/kit) were retired
    with the old concepts, 2026-10-21."""
    return {"room": place, "pieces": []}


def applies(place):
    """A place whose kit lays a lamp with a shaft (the table adds: and whose design is lit): none while a design lays
    no kit piece (design_kit)."""
    return place is not None and bool(shafted_kinds(place, design_kit(place)))


def without_shafts(folder, place):
    """The place's copy of its light layer with its shafts made inactive."""
    from pxr import Sdf
    held = Sdf.Layer.FindOrOpen(str(folder / passes.layer.LAYER))
    spec = Sdf.CreatePrimInLayer(held, f"/{place}/Shafts")
    spec.active = False
    held.Save()


def make_haze(inputs, out, seed, params):
    """Render the place with its light layer and no shafts on its views, every lamp in its own light group."""
    place = passes.place_of(inputs)
    layer_folder = pathlib.Path(inputs["light-layer"])
    lamps = [lamp["path"] for lamp in json.loads((layer_folder / "lamps.json").read_text())["lamps"]]
    tree = out / "stages"
    tree.mkdir(parents=True)
    root = passes.lit_tree(place, layer_folder, tree, inputs)
    without_shafts(tree / place, place)
    passes.render(passes.pass_jobs(root, tree, place, lamps, out, layer_folder), out)
    shutil.rmtree(tree)
