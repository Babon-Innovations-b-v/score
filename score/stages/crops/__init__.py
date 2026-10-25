"""The crops stage (experimental, PRD #6, design D of 2026-10-12): the crop kinds a place's design shows (its
inventory's rows that grow on a bed), grown on the plan's beds as the concept grows them, as a layer of point
instancers the assembly takes.

    crops-concept   paid  SAM 3 on the concept view and its tiles: each kind's patches and spacing (concept.py)
    crops-boxes     paid  the box gate's SAM 3 measure of the crop rows' boxes (boxes.py)
    (the models)          the crop kinds are models like any other (the owner, 2026-10-20): the place's own prop
                          route (props-inputs, closeup, pixal: its design's hand-in) and its own surface line,
                          the finish route to surfaces-bake; this package adds only
                          what the motion layer's growth module needs around them (CONTEXT.md "layer adapter")
    crops-layer     free  each kind's baked model laid on its beds at the concept's spacing, one point instancer a
                          kind (layer.py; the assembly takes it as one of its LAYERS)
    crops-look      paid  the beds and crops rendered at the concept's slant and counted with SAM 3 again: the
                          concept-density check on the render (look.py)

Each row applies only to a place whose design shows crops, and reads them off its kept inventory and plan
(crop_data.py; no per-place crop data since 2026-10-21). Import this
package's modules by their full name, never `from score.stages.crops import ...` (that hashes this file into their
code version, so a table edit would re-buy the paid rows).
"""
from score import contracts, graph
import score.stages.crops.concept as concept
import score.stages.crops.crop_data as crop_data
import score.stages.crops.layer as layer
import score.stages.crops.boxes as boxes
import score.stages.crops.look as look

CONCEPT = graph.Stage("crops-concept", "place", concept.make_concept,
                      contracts.Contract("crops-concept", 1, concept.concept_faults), concept.CHECKS,
                      files=crop_data.concept_files, paid=True, euros=concept.EUROS, applies=crop_data.applies)
BOXES = graph.Stage("crops-boxes", "place", boxes.make_boxes, contracts.Contract("crops-boxes", 2, boxes.boxes_faults),
                    boxes.CHECKS, files=crop_data.boxes_files, paid=True, euros=boxes.EUROS, applies=crop_data.applies)
LAYER = graph.Stage("crops-layer", "place", layer.make_layer, contracts.Contract("crops-layer", 1, layer.layer_faults),
                    layer.CHECKS, files=crop_data.layer_files,
                    after={"crops-concept": ("crops-concept", 1), "surfaces-bake": ("surfaces-bake", 1),
                           "surfaces-paint": ("surfaces-paint", 1),
                           # the rows whose batch gaps say the prop route left a kind's take out (layer.left_out)
                           "pixal": ("props-pixal", 1), "finish-route-split": ("finish-route-split", 1),
                           "finish-route-recheck": ("finish-route-recheck", 1)}, applies=crop_data.applies)
LOOK = graph.Stage("crops-look", "place", look.make_look, look.LOOK, look.CHECKS, files=crop_data.look_files,
                   after={"crops-concept": ("crops-concept", 1), "crops-layer": ("crops-layer", 1)}, paid=True,
                   euros=look.EUROS, applies=crop_data.applies)
ROWS = (CONCEPT, BOXES, LAYER, LOOK)
