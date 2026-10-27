"""The shared loop (CONTEXT.md "shapes first", "layer adapter", "prop pipeline"; #41): every model layer's models are
made one way, as these rows of the stage table, in this order, for each place:

    concept, plan        the place's (the plan names its concept picture; plan@<place> is the table's own row)
    rough-model    paid  the concept through the prop pipeline whole (score/stages/rough_model)
    rough-align    free  the rough model registered to the plan: scaled to its metres, stood in its frame (align.py)
    props-inputs   free  the parts split: every row a layer handed the loop (data/props/<place>.json, each object
                         named by its `layer`) as a close-up row; gates: boxed or drawn, and fits the plan (it reads
                         the registration)
    closeup        paid  the close-ups
    pixal          paid  Pixal3D in a cloud batch
    finish route         surfaces.ROWS: views, one Gemini batch list, the colour check and split, library parts with
                         settings and per-finish seed and wear, the bake, one recheck, surfaces-check
    likeness             each model held to its close-up (likeness-calibration sets DINOv2's least)
    after-steps          each layer adapter's own, reading the loop's ends (made.ENDS) through made.made()

A layer adapter (`Adapter`) adds nothing before the model: it hands the loop its rows in the place's hand-in record and
registers its after-steps here, in `ADAPTERS`. `rows(ADAPTERS)` gives the table these rows; an after-step that does
not read the loop's ends is refused, and one applies only where the place handed the loop rows of its layer.

This package is the table's wiring only (no make, judge or file map of its own, so it is in no row's code version);
align.py and made.py are the loop's code, imported by their full names.
"""
import dataclasses

from score import graph
from score.stages import props, rough_model, scene_record, surfaces
import score.stages.people.loop as people_loop
import score.stages.props.closeup_row as closeup_row
import score.stages.props.prop_data as prop_data
import score.stages.shapes_first.align as align
import score.stages.shapes_first.made as made
from score.stages.surfaces.surface_gates import guarded
import score.stages.terrain.join as ground_join  # by module: terrain's make (its __init__) stays out of this key


@dataclasses.dataclass(frozen=True)
class Adapter:
    """A model layer at the loop's seam: its name (the `layer` its rows carry in the hand-in record) and its own steps
    after the model, each a place row reading made.ENDS."""
    layer: str
    after: tuple = ()


# The object layer: the place's objects as inventory rows; nothing after the model (the reference user, #41).
OBJECTS = Adapter("objects")
# The terrain layer: an outdoor place's detail areas (its scene inventory's terrain rows), joined into its ground with
# collision and library finishes after the model (terrain/join.py, #27); the design's code ground is the named fallback.
TERRAIN = Adapter(ground_join.LAYER, after=(graph.Stage("ground-join", "place", ground_join.make, ground_join.CONTRACT,
                                                ground_join.CHECKS, files=ground_join.files, after=ground_join.AFTER),))
# The kit's layer: a scene's shell pieces and fittings, as inventory rows; nothing after the model (the old kits'
# sections, kit-sections, and code fallbacks, earth-kit, went with the old kits on 2026-10-21; a scene's own shell is
# its earth seed's, laid from its locked plan, earth_seed/design_shell.py).
KIT = Adapter("kit")  # its own word: earth_seed's module (and the shell code behind it) keys no loop row
# The people layer: every look a row, on the line `people`, which no place owns (align.NO_PLACE); after the model, the
# looks handed on (score/stages/people/loop.py; each look's parts row, before its rig, and its dress row read it).
PEOPLE = Adapter("people", after=(graph.Stage(people_loop.ROW, "place", people_loop.make, people_loop.CONTRACT,
                                              (guarded("made", people_loop.judge_made),), after=dict(people_loop.AFTER)),))
ADAPTERS = (OBJECTS, TERRAIN, KIT, PEOPLE)

ROUGH_MODEL = graph.Stage("rough-model", "place", rough_model.make, rough_model.CONTRACT, rough_model.CHECKS,
                          files=rough_model.files, after=rough_model.AFTER, paid=True, euros=rough_model.EUROS,
                          applies=scene_record.written)
ROUGH_ALIGN = graph.Stage("rough-align", "place", align.make, align.CONTRACT, align.CHECKS, after=align.AFTER,
                          applies=scene_record.written)
# The parts split reads the registration: it waits on it, and its gate holds every row to the registered floor.
SPLIT = dataclasses.replace(props.INPUTS, after={**props.INPUTS.after, "rough-align": ("rough-align", 1)},
                            checks=(*props.INPUTS.checks, guarded("fits the plan", align.judge_rows_fit)))


def no_place(place):
    """Whether `place` is a line of models no place owns (align.NO_PLACE): no place's rows (assembly, complete, the
    library hand-over) apply there."""
    return place in align.NO_PLACE


def handed(place, layer):
    """Whether the place handed the loop rows of `layer` (its hand-in record, prop_data's)."""
    return any(closeup_row.layer_of(entry) == layer for entry in prop_data.objects(place).values())


def layer_applies(layer, applies):
    """An after-step's `applies`: where the place handed rows of its layer, and its own says so."""
    def applied(place):
        return handed(place, layer) and (applies is None or applies(place))
    return applied


def after_step(adapter, step):
    """An adapter's after-step as the loop runs it; refused when it does not read the loop's ends."""
    missing = sorted(made.ENDS.keys() - step.after.keys())
    if step.grain != "place" or missing:
        raise ValueError(f"{adapter.layer}'s after-step {step.name}: a place row reading the loop's ends "
                         f"(made.ENDS) after the model; it lacks {missing or step.grain}")
    return dataclasses.replace(step, applies=layer_applies(adapter.layer, step.applies))


# The finish route's row that reads the Pixal3D row only as optional: the scene palette, which the surface library,
# and through it the base and every layer, reads. A stopped prop route leaves the palette without its takes' close-ups,
# never the place without its base (Buy of 2026-10-24: one crashed close-up stopped the square's whole line).
PALETTE = "finish-route-palette"


def finish_route():
    """The finish route's rows, its views and its scene palette (which sees every take's close-up) waiting on the
    Pixal3D row whose takes it paints (props.FEEDS; a place with no prop data reads without it, Runner.reads); the
    palette reads it as optional: it waits on it and runs without it once it stopped (Runner.unsettled)."""
    return tuple(dataclasses.replace(row, after={**row.after, **props.FEEDS},
                                     optional=(*row.optional, *props.FEEDS) if row.name == PALETTE else row.optional)
                 if row.name in ("finish-route-views", PALETTE) else row for row in surfaces.ROWS)


def rows(adapters=ADAPTERS):
    """The loop's rows for the stage table, in its order, then every adapter's after-steps."""
    layers = [adapter.layer for adapter in adapters]
    if len(set(layers)) != len(layers):
        raise ValueError(f"two adapters share a layer: {layers}")
    return (ROUGH_MODEL, ROUGH_ALIGN, SPLIT, props.CLOSEUP, props.PIXAL, *finish_route(), props.CALIBRATION,
            props.LIKENESS, *(after_step(adapter, step) for adapter in adapters for step in adapter.after))
