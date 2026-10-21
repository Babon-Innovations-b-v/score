"""The light stage's second paid row, light-haze (a place whose kit lays a lamp with a shaft, `shafted_kinds`: today
the square's floodlight towers and the launch's pad floodlights): the same render as light-passes with the shafts' haze left out, so the light row can tell what the haze lays
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
SKY = passes.REPO / "data/definitions/sky.json"


def shafted_kinds(place):
    """The kit kinds the place lays whose lamps light a shaft of haze (its floodlights): each lamp row the sky record
    gives a shaft (data/definitions/sky.json `lamps`, laid as `<room>_<row>`, as the scene-record row lights them:
    scene_record/kit_shell.lamp_spots)."""
    path = passes.REPO / f"data/kit/{place}.json"
    if not path.is_file():
        return set()
    kit = json.loads(path.read_text())
    sky = json.loads(SKY.read_text())
    rows = {row for body in sky.values() if isinstance(body, dict)
            for row, lamp in (body.get("lamps") or {}).items() if lamp.get("shaft")}
    kinds = {f"{kit.get('room', place)}_{row}" for row in rows}
    return kinds & {laid["kind"] for laid in kit["pieces"]}


def applies(place):
    """A place whose kit lays a lamp with a shaft (the table adds: and whose design is lit)."""
    return place is not None and bool(shafted_kinds(place))


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
