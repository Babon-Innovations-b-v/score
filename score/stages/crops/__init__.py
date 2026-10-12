"""The crops stage (experimental, PRD #6, design D of 2026-10-12): the crop kinds a place's concept shows, grown on
its beds as the concept grows them, as a layer of point instancers the assembly takes.

    crops-concept   paid  SAM 3 on the concept view and its tiles: each kind's patches and spacing (concept.py)
    crops-boxes     paid  the box gate's SAM 3 measure of the crop rows' boxes (boxes.py)
    crops-props-inputs, crops-closeup, crops-pixal, crops-surfaces-inputs ... crops-surfaces-check
                          the crops' own line: the prop route's close-up and Pixal3D rows and the surface stage's
                          method, paint, bake and check, unchanged, on the crop data's own files (line.py)
    crops-layer     free  each kind's baked model laid on its beds at the concept's spacing, one point instancer a
                          kind (layer.py; the assembly takes it as one of its LAYERS)
    crops-look      paid  the beds and crops rendered at the concept's slant and counted with SAM 3 again: the
                          concept-density check on the render (look.py)

Each row applies only to a place with crop data (data/crops/<place>.json, crop_data.py): the greenhouse. Import this
package's modules by their full name, never `from score.stages.crops import ...` (that hashes this file into their
code version, so a table edit would re-buy the paid rows).
"""
from score import contracts, graph
import score.stages.crops.concept as concept
import score.stages.crops.crop_data as crop_data
import score.stages.crops.layer as layer
import score.stages.crops.line as line
import score.stages.crops.look as look

CONCEPT = graph.Stage("crops-concept", "place", concept.make_concept,
                      contracts.Contract("crops-concept", 1, concept.concept_faults), concept.CHECKS,
                      files=crop_data.concept_files, paid=True, euros=concept.EUROS, applies=crop_data.applies)
LAYER = graph.Stage("crops-layer", "place", layer.make_layer, contracts.Contract("crops-layer", 1, layer.layer_faults),
                    layer.CHECKS, files=crop_data.layer_files,
                    after={"crops-concept": ("crops-concept", 1), "crops-surfaces-bake": ("surfaces-bake", 1),
                           "crops-surfaces-paint": ("surfaces-paint", 1)}, applies=crop_data.applies)
LOOK = graph.Stage("crops-look", "place", look.make_look, look.LOOK, look.CHECKS, files=crop_data.look_files,
                   after={"crops-concept": ("crops-concept", 1), "crops-layer": ("crops-layer", 1)}, paid=True,
                   euros=look.EUROS, applies=crop_data.applies)
ROWS = (CONCEPT, *line.ROWS, LAYER, LOOK)
