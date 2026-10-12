"""The light stage's second paid row, light-haze (a place whose floodlights have shafts: the square and the launch
view): the same render as light-passes with the shafts' haze left out, so the light row can tell what the haze lays
over the place (the veil) from what the floodlights light on its floor, which one render cannot (the captain,
2026-10-12, after the square's veil read 0.097 with its floodlights' floor light in it). Its own module, so
light-passes keeps its key.
"""
import json
import pathlib
import shutil

import score.stages.light.passes as passes  # this form: the code version then leaves __init__ out

# The places whose floodlights have shafts (score/stages/light LAMP_KINDS' owners).
HAZED = ("square", "launch")
# Four to eight views on one rented card, as light-passes.
EUROS = 2.0


def without_shafts(folder, place):
    """The place's copy of its light layer with its shafts made inactive."""
    from pxr import Sdf
    held = Sdf.Layer.FindOrOpen(str(folder / passes.layer.LAYER))
    spec = Sdf.CreatePrimInLayer(held, f"/{place}/Shafts")
    spec.active = False
    held.Save()


def make_haze(inputs, out, seed, params):
    """Render the place with its light layer and no shafts on its views, every lamp in its own light group."""
    place = json.loads(pathlib.Path(inputs["scene"]).read_text())["place"]
    layer_folder = pathlib.Path(inputs["light-layer"])
    lamps = [lamp["path"] for lamp in json.loads((layer_folder / "lamps.json").read_text())["lamps"]]
    tree = out / "stages"
    tree.mkdir(parents=True)
    root = passes.lit_tree(place, layer_folder, tree, inputs)
    without_shafts(tree / place, place)
    passes.render(passes.pass_jobs(root, tree, place, lamps, out), out)
    shutil.rmtree(tree)
