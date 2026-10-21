"""The stage table: every stage the runner knows, in the paper's order, and environment 1 as the runner reads it.

    from score import stages
    runner = stages.runner()        # environment 1, the framework's store on this machine
    runner.status(["hangar", "garage"])
    runner.drive(stages.places(runner.world))   # every line of the environment to its end (python -m score run world1)

Step 0 holds the worked example: assembly (P5) on environment 1's round-three stages as unverified seeds, and complete
(P11). Terrain (the paper's Methods, "Terrain") makes every ground of the environment from its plan, one environment node,
free (the code fallback under its prop-pipeline adapter, ground-join), and ground-fit judges each seated place on it. The surface stage (step 1, its overlay) is each place's
own line of rows, split to checked bake, beside the environment's seed of the finish registry. Effects (experimental) makes
each staged place's effects layer from its record, which its assembly takes; effects-look renders it before and
after. Neighbours (experimental) stands the places a place's scene record shows in its assembly, each read as its
own accepted assembly. The shared loop (shapes_first, #41: rough model, its registration to the plan, the parts split,
close-up, Pixal3D, the finish route, the likeness gate, then each layer adapter's after-steps) is every model layer's
one way to a model; its prop rows run only for a place with prop data. Plan and scene-record (experimental) write a
place's scene record from its plan and concept. Cast (experimental) places each place's people and measures them against its concept's count
(concept_people) and its geometry. Motion (experimental) makes each place's motion layer from its game motions
and its rigid moves. Each stage joins the table when it is built in its step (docs/bible.md, architecture/components).
"""
import contextlib
import dataclasses
import functools
import json
import pathlib

from score import checks, contracts, graph
from score.checks import grain
from score.stages import (assembly, cast, complete, concept_people, concept_view, crops, demo_film, demo_turntable,
                          earth_seed, effects, gaps, images, late_bake, library, light, motion, people, people_rows,
                          physics, proposals, scene_record, settling, shapes_first, shell_split, sound,
                          surface_tiles, surfaces, terrain)
from score.stages.surfaces import bake_check, carry, library_reads, route_check
from score.stages.library import clips as library_clips
import score.stages.batch_gaps as batch_gaps
import score.stages.cast.layer as characters_layer
import score.stages.demo_film.stills as demo_stills
import score.stages.demo_film.final as demo_film_final
from score.stages.surfaces.surface_gates import guarded
from score.stages.assembly import neighbours
import score.stages.motion.models as motion_models
import score.stages.motion.models.boxes as model_boxes
import score.stages.props.prop_data as prop_data
import score.stages.complete.boxes as complete_boxes
from score.stages.assembly import ship_made
from score.stages.effects import look as effects_look
from score.stages.terrain import fit as ground_fit, inputs as terrain_inputs
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[2]
WORLD1 = REPO / "data/definitions/world.json"

TERRAIN = graph.Stage("terrain", "world", terrain.make, terrain.GROUNDS, terrain.CHECKS, files=terrain_inputs.FILES)
# Each seated place's own stage judged standing on its made ground (score/stages/terrain/fit.py): under, floating,
# continuous, openings; free, on its neighbours output where it shows other places, else its assembly.
GROUND_FIT = graph.Stage("ground-fit", "place", ground_fit.make, ground_fit.FIT, ground_fit.CHECKS,
                         files=ground_fit.files, after={"assembly": ("openusd-stage", 1),
                                                        "neighbours": ("openusd-stage", 1), "terrain": ("grounds", 1)},
                         applies=ground_fit.applies)
# Experimental (PRD #6) until the owner reviews it: each staged place's effects layer (effects.STAGED), which its
# assembly takes.
EFFECTS = graph.Stage("effects-layer", "place", effects.make, effects.LAYER, effects.CHECKS, files=effects.files,
                      after={"scene-record": ("scene-record", 1)}, applies=lambda place: place in effects.STAGED)
# Experimental (PRD #6) until the owner reviews it: each place's motion layer, the game's timed motions and the rigid
# moves SCORE gives the things that move there (data/motion/rigid), over its seed with its accepted scene record written in (the
# seed alone where the place has no scene-record row); the final assembly takes it.
MOTION = graph.Stage("motion", "place", motion.make, motion.LAYER, motion.CHECKS, files=motion.files,
                     after={"scene-record": ("scene-record", 1), "terrain": ("grounds", 1),
                            "motion-models": ("motion-models", 1)},
                     applies=motion.applies)
# Experimental (PRD #6) until the owner reviews it: where each place's objects come to rest on its made ground,
# which its assembly takes (assembly.LAYERS). A place joins SETTLED once its settle row has passed (resting track).
SETTLED = ("airlock", "campgrounds", "garage", "greenhouse", "habitat", "hangar", "lab", "square", "workshop",
           "wreck")
SETTLE = graph.Stage("settle", "place", settling.make, settling.SETTLE_LAYER, settling.CHECKS, files=settling.files,
                     after={"scene-record": ("scene-record", 1), "terrain": ("grounds", 1),
                            "surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                     beside={"surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                     neighbours=assembly.claiming_places, paid=True, euros=settling.EUROS,
                     applies=lambda place: place in SETTLED)
# The place's final assembly: its seed with every accepted layer it reads in place of the seed's part (assembly.READS,
# joined in `layered` for each layer stage the table holds), its layers gate unknown while one it needs is missing.
ASSEMBLY = graph.Stage("assembly", "place", assembly.make_from_seed, contracts.OPENUSD_STAGE, assembly.CHECKS,
                       files=assembly.files, gatherers=assembly.GATHERERS,
                       after={"terrain": ("grounds", 1),
                              "surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                       beside={"surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                       neighbours=assembly.claiming_places)
# Experimental (PRD #6) until the owner reviews it: the motion layer's models (data/motion/models/<place>.json), the
# prop pipeline's models of its rigid moving things laid on what holds them up, as a layer the assembly takes.
MOTION_MODELS = graph.Stage("motion-models", "place", motion_models.make, motion_models.LAYER_CONTRACT,
                            motion_models.CHECKS, files=motion_models.files, after=motion_models.AFTER,
                            applies=motion_models.applies)
# Experimental (PRD #6): SAM 3's grounding of a place's ground_box rows' boxes, so the prop route may draw them.
MOTION_MODEL_BOXES = graph.Stage("motion-models-boxes", "place", model_boxes.make_boxes, model_boxes.CONTRACT,
                                 model_boxes.CHECKS, files=model_boxes.files, paid=True, euros=model_boxes.EUROS,
                                 applies=model_boxes.applies)
# Experimental (PRD #6) until the owner reviews it: each place's assembly with the places its scene record shows,
# each read beside as its own accepted assembly. Complete reads it: a place whose shown places do not stand is not
# complete, so a neighbour whose assembly fails (the hub's) stops every place that shows it.
NEIGHBOURS = graph.Stage("neighbours", "place", neighbours.make, contracts.OPENUSD_STAGE, neighbours.CHECKS,
                         files=neighbours.files, after={"assembly": ("openusd-stage", 1)},
                         beside={"assembly": ("openusd-stage", 1)}, neighbours=neighbours.neighbours,
                         applies=neighbours.applies)
# The completion gate on what the place holds (tools/usd/complete.py's checks, contents.py's among them), on its
# neighbours output where it shows other places, with its paint's check and its models' likeness to their close-ups.
COMPLETE = graph.Stage("complete", "place", complete.make_manifest, contracts.PLACE_MANIFEST, complete.CHECKS,
                       files=complete.files,
                       after={"assembly": ("openusd-stage", 1), "neighbours": ("openusd-stage", 1),
                              "surfaces-check": ("surfaces-check", 1), "likeness": ("props-likeness", 1),
                              "characters-layer": ("characters-layer", 1), "complete-boxes": ("complete-boxes", 1)})
# The box gate's measure of the boxes no other row measures (complete/boxes.py), so complete's boxes check has a
# verdict for every boxed row: a ship place's code rows and the rows it takes from another place's take
# (2026-10-15). The old places' partitions were measured whole by hand; a ship place only, so none of theirs moves.
COMPLETE_BOXES = graph.Stage("complete-boxes", "place", complete_boxes.make_boxes, complete_boxes.CONTRACT,
                             complete_boxes.CHECKS, files=complete_boxes.files, paid=True, euros=complete_boxes.EUROS,
                             applies=lambda place: ship_place(place) and complete_boxes.has_rows(place))
EFFECTS_LOOK = graph.Stage("effects-look", "place", effects_look.make, effects_look.LOOK, effects_look.CHECKS,
                           files=effects_look.files, after={"assembly": ("openusd-stage", 1)}, paid=True,
                           euros=effects_look.EUROS, applies=lambda place: place in effects_look.LOOKED)
# Experimental (PRD #6) until the owner reviews it: the place's plan in the store, and its scene record written from
# it (score/stages/scene_record), for the places whose plan says where each door leads. No assembly reads it yet.
def kit_laid(place):
    """Whether the place's kit is laid (data/kit/<place>.json): a new place, made from its plan, has none until its
    pieces are made."""
    return (REPO / "data/kit" / f"{place}.json").exists()


def kit_if_laid(files):
    """The plan row's environment files without `kit` for a place whose kit is not laid, so its plan runs before it.
    Wrapped here, in the table, so the plan's code version and every laid place's key stay as they were."""
    @functools.wraps(files)
    def declared(place):
        found = files(place)
        return found if kit_laid(place) else {name: path for name, path in found.items() if name != "kit"}
    return declared


def creator_plan(files):
    """The plan row's files with the place's plan made from its pick (score/review/plans.py, kept under
    {home}/design/plans: his edit, else made from the pick's scene inventory) as its `plan`, and that inventory
    (under {home}/design/inventory) as its `inventory`, and the picked concept (under {home}/design/concepts) as its
    `concept`, where they are kept. Wrapped here, in the table, so a place
    without one keeps its key and the plan's code version moves for none."""
    @functools.wraps(files)
    def declared(place):
        found, kept = files(place), PROPS_HOME / "design"
        if (kept / "plans" / f"{place}.json").is_file():
            found = {**found, "plan": "{home}/design/plans/{place}.json"}
        if (kept / "inventory" / f"{place}.json").is_file():
            found = {**found, "inventory": "{home}/design/inventory/{place}.json"}
        if (kept / "concepts" / f"{place}.png").is_file():  # the picked concept, not data/plans' older picture
            found = {**found, "concept": "{home}/design/concepts/{place}.png"}
        return found
    return declared


def plan_as_kit(function, position):
    """A plan row function (make, or a judge) reading a place with no kit laid: its `kit` input (argument `position`)
    is the plan itself, which lays no pieces and is named for the place, so the row reads a kit with nothing on it."""
    @functools.wraps(function)
    def read(*arguments):
        arguments = list(arguments)
        arguments[position] = {"kit": arguments[position]["plan"], **arguments[position]}
        return function(*arguments)
    return read


def shell_of(place):
    """[the outside shell whose split names the place], or []: what an inside place's plan reads beside it. Here in
    the table, so the plan row's code version never hashes the split's code (a neighbours function's file is part of
    its row's code version, and the table is the framework's)."""
    return shell_split.shell_of(place)


PLAN = graph.Stage("plan", "place", plan_as_kit(scene_record.plan.make, 0), scene_record.plan.PLACE_PLAN,
                   tuple(dataclasses.replace(check, judge=plan_as_kit(check.judge, 1))
                         for check in scene_record.plan.CHECKS),
                   files=creator_plan(kit_if_laid(scene_record.plan.files)), applies=scene_record.written,
                   beside={"shell-split": ("shell-split", 1)}, upward=True, neighbours=shell_of)
# Shapes first (CONTEXT.md "shell split"): an outside shell's plan split into the shapes of its inside places, free and
# local, for a place whose plan has a `split`; each inside place's plan reads its shell's split beside it (PLAN's
# `beside`, upward: up to the shell, never back down), so the drive makes the shell's split before its inside places.
SHELL_SPLIT = graph.Stage("shell-split", "place", shell_split.make, shell_split.CONTRACT, shell_split.CHECKS,
                          files=shell_split.files, after={"plan": ("place-plan", 2)}, applies=shell_split.applies)
# The openings gate's finding for a place no made ground seats (scene_record/gates.py judge_openings).
NO_GROUND = "no made ground seats this place: its outside cannot be judged"


def seed_if_any(files):
    """scene-record's environment files without `seed record` for a place that never had an old record (the ship's places,
    2026-10-15: the runner blocked on the missing file while `seed-matched` itself passes a place with none). Wrapped
    here, in the table, so every place with a seed keeps its key."""
    @functools.wraps(files)
    def declared(place):
        found = files(place)
        return found if (REPO / "data/scene" / f"{place}.json").exists() else \
            {name: path for name, path in found.items() if name != "seed record"}
    return declared


def seed_optional(judge):
    """`seed-matched` reading a place with no seed record declared (seed_if_any): its seed path is the one that does
    not exist, which the gate already passes as "the place had no old record"."""
    @functools.wraps(judge)
    def judged(output, inputs, evidence):
        place = scene_record.writer.record_in(output)[0]
        return judge(output, {"seed record": str(REPO / "data/scene" / f"{place}.json"), **inputs}, evidence)
    return judged


def ground_free(judge):
    """The openings gate for a ground-free interior (the overseer, 2026-10-14: the ship's rooms, which stand in the
    hangar's ship, not on a made ground): a place whose plan says `ground_free` and why is judged against its own
    walls (every doorway onto a floor, no view ray out into nothing, every door's place past it), all still measured;
    only the missing ground is not a fault. Wrapped here, in the table, so no other place's key or verdict moves;
    it moves into gates.py the next time scene-record is made again for every place."""
    @functools.wraps(judge)
    def judged(output, inputs, evidence):
        verdict = judge(output, inputs, evidence)
        place = scene_record.gates.plan_of(inputs)["place"]
        why = json.loads((pathlib.Path(inputs["plans"]) / f"{place}.json").read_text()).get("ground_free")
        if not why or NO_GROUND not in verdict.findings:
            return verdict
        findings = tuple(finding for finding in verdict.findings if finding != NO_GROUND)
        reason = "; ".join(findings[:3]) if findings else \
            f"a ground-free interior ({why}): judged against its own walls, no doorway onto nothing, no view out " \
            "into nothing, every door's place past it"
        return dataclasses.replace(verdict, answer=checks.FAIL if findings else checks.PASS, reason=reason,
                                   findings=findings)
    return judged


SCENE_RECORD = graph.Stage("scene-record", "place", scene_record.writer.make, scene_record.writer.SCENE_RECORD,
                           tuple(dataclasses.replace(check, judge=ground_free(check.judge))
                                 if check.name == "openings" else
                                 dataclasses.replace(check, judge=seed_optional(check.judge))
                                 if check.name == "seed-matched" else check for check in scene_record.gates.CHECKS),
                           files=seed_if_any(scene_record.writer.files),
                           after={"plan": ("place-plan", 2), "terrain": ("grounds", 1)},
                           applies=scene_record.written)
# Experimental (design 5, 2026-10-12) until the owner reviews it: each place's cast placed and measured against its
# picked design's people (data/people/rows.json, #26; concept_people's lost pictures no longer read) and its seed's
# geometry.
# Its `made` gate reads the looks' dress rows as optional inputs: a look whose dressed body stands usable is made.
DRESS_ROWS = tuple(row.name for row in people.ROWS if row.name.startswith(f"{characters_layer.DRESS}-"))
def cast_place(place):
    """A place with a cast row: its picked design shows people (data/people/rows.json, #26)."""
    return people_rows.has_people(place)


CAST = graph.Stage("cast", "place", cast.make, cast.CAST, cast.CHECKS, files=cast.files,
                   after={name: ("people-dress", 1) for name in DRESS_ROWS}, optional=DRESS_ROWS, applies=cast_place)
# Experimental (2026-10-13): each cast place's people laid from its accepted cast, each in its own look's accepted
# dressed body (score/stages/cast/layer.py), as a layer the assembly takes. Its dress rows are optional reads: a look
# whose body is not usable is left out by name (the overseer's 14:00 rule: assemble with what passed; complete fails
# the gap), never a stand-in.
CHARACTERS = graph.Stage("characters-layer", "place", characters_layer.make, characters_layer.CONTRACT,
                         characters_layer.CHECKS, files=characters_layer.files,
                         after={"cast": ("cast", 1), **{name: ("people-dress", 1) for name in DRESS_ROWS}},
                         optional=DRESS_ROWS, applies=cast_place)
# Experimental (PRD #6) until the owner has heard it: each place's sound layer data (its sounds, their files and levels,
# MOSS takes for briefs no environment file answers, paid), for the place's assembly to write into its stage.
SOUND = graph.Stage("sound", "place", sound.make, sound.LAYER, sound.CHECKS, files=sound.files, paid=True,
                    euros=sound.EUROS, models=(sound.moss_takes.KIND,), applies=sound.applies)

# Experimental (F11) until the owner reviews it: a place's physics in UsdPhysics and a trial in Bullet that shows its
# objects react (the places with a trial record, physics.applies).
PHYSICS_LAYER = graph.Stage("physics-layer", "place", physics.make_layer, physics.LAYER, physics.LAYER_CHECKS,
                            files=physics.LAYER_FILES, after={"assembly": ("openusd-stage", 1)},
                            applies=physics.applies)
PHYSICS_TRIAL = graph.Stage("physics-trial", "place", physics.make_trial, physics.TRIAL, physics.TRIAL_CHECKS,
                            files=physics.trial_files, after={"physics-layer": ("physics-layer", 1)}, paid=True,
                            euros=physics.EUROS, applies=physics.applies)


def bake_checked(row):
    """surfaces-check on bake_check.py, the check's own module (a border triangle a blotch only when off every surface
    within its reach), made through route_check.py (against the bake's specs: the finish list's settings, #18). Set
    here, in the table, not in surfaces/__init__.py, which is in the turntable's and SegviGen's code version: an edit
    there re-buys them. Moves into surfaces/__init__.py, and the old check leaves place_line.py, once their fan-out of
    2026-10-12 is done."""
    if row.name != "surfaces-check":
        return row
    return dataclasses.replace(row, make=route_check.make_check,
                               contract=contracts.Contract("surfaces-check", 1, bake_check.check_faults),
                               checks=(guarded("baked matches its surfaces", bake_check.judge_lit),
                                       guarded("triangles within budget", bake_check.judge_triangles),
                                       guarded("stands level", bake_check.judge_stance)),
                               files=check_files)


def check_files(place):
    """The check's environment files: the paint's (its line's, the inventories, the resting rules), the stance rules, and
    the place's kit, scene record and motion models record (each model's spots and the views, its view distance)."""
    # A place the game never had (the ship's rooms) has no old scene record, and no kit until its shell is laid: the
    # check reads none then (bake_check.seen_degrees does without), as scene-record's seed (78243df1).
    views = {"kit": REPO / "data/kit" / f"{place}.json", "scene record": REPO / "data/scene" / f"{place}.json",
             "models": REPO / "data/motion/models" / f"{place}.json"}
    return {**paint_files(place),
            "stance rules": "{data}/checks/stance.json",
            **{name: "{data}/" + path.relative_to(REPO / "data").as_posix() for name, path in views.items()
               if path.exists()}}


def paint_baked(row):
    """surfaces-bake with the paint's files beside its own (paint_files: the paint runs in its job on the rented card,
    route_bake.py, #18) and the job's scripts (inside/, run up there, never imported; the folder's overlay left out)."""
    if row.name != "surfaces-bake":
        return row
    own = row.files
    return dataclasses.replace(row, files=lambda place: {
        **paint_files(place), **own(place), **{f"paint bake {name}": "{repo}/score/stages/surfaces/inside/" + name
                                               for name in ("paint_bake.py", "paint_take.py")}})


def feet_checked(row):
    """surfaces-paint with the gate "feet in one plane" beside its own (place_line.judge_feet: a take's short legs are
    stretched down before its bake, a missing leg fails by name). Set here, as bake_checked is, so the turntable's and
    SegviGen's code version does not move."""
    if row.name != "surfaces-paint":
        return row
    return dataclasses.replace(row, checks=(*row.checks, guarded("feet in one plane", surfaces.place_line.judge_feet)),
                               files=paint_files)


def paint_files(place):
    """The paint's environment files: the line's, and the inventory of each place a take is made for with the resting rules,
    which it reads to tell a take laid loose on the floor or held, whose feet it levels (place_line.stands_on_feet)."""
    import stage_inputs  # tools/usd, on the path by the assembly stage's import: a place's inventory, or its kit's
    inventories = {f"inventory {entry['place']}": "{data}/inventory/" + stage_inputs.inventory_path(entry["place"]).name
                   for entry in surfaces.data.takes(place).values()}
    claiming = {other for found in surfaces.place_line.claimants(place).values() for other, _ in found}
    inventories.update({f"inventory {other}": "{data}/inventory/" + stage_inputs.inventory_path(other).name
                        for other in claiming})  # a claimant's rows stand the take too (place_line.claimed_rows)
    inventories.update({f"claimant {other}": surfaces.data.pattern(other) for other in claiming})
    return {**surfaces.data.line_files(place), **inventories, "resting rules": "{data}/checks/resting.json"}




def far_judged(row):
    """A far-only people body judged on what is drawn (captain, 2026-10-13; people/far.py): its joins, its likeness
    and the far body's triangles, the near outfit recorded. Set here, in the table, so the full bodies' code versions
    (people/bodies.py and the package) do not move."""
    if not row.name.startswith("people-body-") or not row.params.get("far_only"):
        return row
    from score.stages.people_bodies import bodies, far
    drawn = tuple(check for check in row.checks if check.name in ("joins", "likeness"))
    return dataclasses.replace(row, checks=drawn + (bodies.guarded("far triangles", far.judge_far_triangles),
                                                    bodies.guarded("near outfit recorded", far.judge_near_recorded)))


# The rows keyed on the library parts they read (surfaces/library_reads.py), each with its surface data's reader.
LIBRARY_READERS = {"surfaces-paint": surfaces.data.record, "surfaces-bake": surfaces.data.record}


def library_narrowed(row):
    """A paint or bake row (and its crops twins) keyed on the library surfaces and place.json entries it
    reads, not the whole library folder and place.json: one surface added for one place re-keyed every place's paint
    and bake (the hub's assembly wanted about EUR 60 of re-buys, 2026-10-13). Set here, in the table, so no other
    row's code version moves; surfaces/carry.py carries each accepted output over to its narrower key once."""
    if row.name not in LIBRARY_READERS:
        return row
    files = library_reads.narrowed(row.files, LIBRARY_READERS[row.name])
    files.carries, files.carried = carry.carries, carry.carried  # the runner's carry-over (here: no key moves)
    return dataclasses.replace(row, files=files)


def box_checked(files):
    """props-inputs' environment files with the box gate's decided boxes (WORK/partition/<scene>/boxes.json, which
    motion-models-boxes writes), so a box check that passes later re-runs the inputs row (the cockpit, 2026-10-14: it read
    the old failed boxes and stayed failed with its key unmoved). Wrapped here, in the table, so no row's code moves."""
    @functools.wraps(files)
    def declared(place):
        # A designed place's boxes are SAM 3's in its reading, in its hand-in (prepare/handin.py); a line no place owns
        # (the people's) takes its rows' boxes from the designs that map them (people_rows.drawn_from, #26).
        if prop_data.designed(place) or shapes_first.no_place(place):
            return files(place)
        return {**files(place), "decided boxes": "{seeds}/partition/" + f"{place}/boxes.json"}
    return declared


def scene_inventory_read(files):
    """props-inputs' environment files with "inventories" the scene's own inventory, the one the box gate reads
    (box_check.gate: inventory.path_of(scene), the scene the place's inventory names), not the whole folder: every
    place's inputs row was made again for the hangar's inventory alone (46313397, 2026-10-18). The name is kept, so an
    output whose scene's inventory reads as when it was made keeps it (the narrowing carry). Wrapped here, in the table,
    so no row's code moves."""
    @functools.wraps(files)
    def declared(place):
        found = files(place)
        if found.get("inventories") != "{data}/inventory":
            return found
        if prop_data.designed(place):  # a designed place's rows are its hand-in's (prepare/handin.py)
            return {**found, "inventories": prop_data.pattern(place)}
        own = prop_data.FOLDER.parent / "inventory" / f"{place}.json"
        scene = json.loads(own.read_text()).get("scene", place) if own.exists() else place
        return {**found, "inventories": "{data}/inventory/" + f"{scene}.json"}
    return declared


def designed_rough(row):
    """rough-model reading a designed place's design (prop_data.designed): its picked concept (under
    {home}/design/concepts) as its `concept` and its hand-in, the scene inventory the batch builds from, as its
    `inventory`. Wrapped here, in the table, so a place without one keeps its key and no row's code moves."""
    if row.name != "rough-model":
        return row

    @functools.wraps(row.files)
    def declared(place):
        found = row.files(place)
        if not prop_data.designed(place):
            return found
        return {**found, "concept": "{home}/design/concepts/" + f"{place}.png", "inventory": prop_data.pattern(place)}
    return dataclasses.replace(row, files=declared)


def boxed_split(row):
    """props-inputs, the loop's parts split, with the box gate's decided boxes and its scene's inventory declared
    (box_checked, scene_inventory_read)."""
    if row.name != "props-inputs":
        return row
    return dataclasses.replace(row, files=box_checked(scene_inventory_read(row.files)))


# Experimental (2026-10-14) until the owner reviews it: concept views drawn by Pro from a creator's reference and a
# written request (data/definitions/concept_views.json), one environment node, paid: the ship's top and side views first.
CONCEPT_VIEWS = graph.Stage("concept-views", "world", concept_view.make, concept_view.CONTRACT, concept_view.CHECKS,
                            files=concept_view.files, paid=True, euros=concept_view.euros())
# Experimental (2026-10-14): the concept partition's SAM 2.1 proposals for scenes whose inventory has not landed
# (data/definitions/partitions.json), one environment node, paid: the cockpit first.
PARTITION_PROPOSALS = graph.Stage("partition-proposals", "world", proposals.make, proposals.CONTRACT, proposals.CHECKS,
                                  files=proposals.files, paid=True, euros=proposals.euros())
# Experimental (2026-10-14): models that already exist turned round for the paper's demos
# (data/definitions/demo_turntables.json), one environment node, paid: demo K2's hub objects first.
DEMO_TURNTABLES = graph.Stage("demo-turntables", "world", demo_turntable.make, demo_turntable.CONTRACT,
                              demo_turntable.CHECKS, files=demo_turntable.files, paid=True,
                              euros=demo_turntable.euros())
# Experimental (2026-10-14): demo K9's walk-through film of a place from its final stage once it passes complete, or
# fails it only on its accepted gaps (gapped: the overseer, 2026-10-15), only for the places with a film record in
# data/definitions/demo_films/, paid.
DEMO_FILM = graph.Stage("demo-film", "place", demo_film.make, demo_film.CONTRACT, demo_film.CHECKS,
                        files=demo_film.files, after={"assembly": ("openusd-stage", 1),
                                                      "neighbours": ("openusd-stage", 1),
                                                      "complete": ("place-manifest", 1)},
                        paid=True, euros=demo_film.EUROS, applies=demo_film.applies, gapped=("complete",))
# A place's other films (the ship's hull through the hangar), one node a place, so its own film's key never moves.
DEMO_FILM_EXTRA = dataclasses.replace(DEMO_FILM, name="demo-film-extra", make=demo_film.make_extra,
                                      contract=demo_film.EXTRA_CONTRACT, checks=demo_film.EXTRA_CHECKS,
                                      files=demo_film.extra_files, applies=demo_film.applies_extra)
# Single pictures of a place's final stage for the paper's demos (data/definitions/demo_stills/<place>.json), paid.
DEMO_STILLS = dataclasses.replace(DEMO_FILM, name="demo-stills", make=demo_stills.make, contract=demo_stills.CONTRACT,
                                  checks=demo_stills.CHECKS, files=demo_stills.files, applies=demo_stills.applies,
                                  euros=demo_stills.euros())

# The environment's own final film (#28), cut locally from its film script (data/films/) over the place films it
# shows, read beside: an environment node the runner plans and prices with the paid films it reads, free itself.
ENVIRONMENT_FILM = graph.Stage("environment-film", "world", demo_film_final.make, demo_film_final.CONTRACT,
                               demo_film_final.CHECKS, files=demo_film_final.files,
                               beside={"demo-film": ("demo-film", 1), "demo-film-extra": ("demo-film-extra", 1)},
                               neighbours=demo_film_final.shown_places)


STAGES = (TERRAIN, CONCEPT_VIEWS, PARTITION_PROPOSALS, DEMO_TURNTABLES, EFFECTS, SETTLE, SOUND, ASSEMBLY, NEIGHBOURS,
          COMPLETE, DEMO_FILM, DEMO_FILM_EXTRA, DEMO_STILLS, ENVIRONMENT_FILM,
          GROUND_FIT, EFFECTS_LOOK, PHYSICS_LAYER,
          PHYSICS_TRIAL,
          # The place's plan (its scene record first: the cockpit groups the plan by its first reader, the base), then
          # the shared loop every model layer runs (score/stages/shapes_first, #41), the table's shims by row name.
          SCENE_RECORD, PLAN, *map(library_narrowed, map(paint_baked, map(feet_checked, map(bake_checked, map(
              boxed_split, map(designed_rough, shapes_first.rows())))))),
          *(library_narrowed(far_judged(row)) for row in people.ROWS), SHELL_SPLIT, concept_people.STAGE, CAST, CHARACTERS, MOTION_MODELS, MOTION_MODEL_BOXES, MOTION,
          *light.ROWS, *crops.ROWS, COMPLETE_BOXES,
          surface_tiles.STAGE)

# The motion layer (CONTEXT.md "motion", #26): one layer for everything that moves, its modules and the rows (fnmatch
# patterns) that make each. Every model comes from the prop pipeline; each module only adds what moves it.
MOTION_LAYER = {"models": ("motion-models", "motion-models-boxes"),  # rigid moving things' models laid
                "rigid": ("motion",),  # joints and paths: hinge, rail, lane, spin; the motion check
                "physics": ("settle", "physics-layer", "physics-trial"),  # settling, falling, cloth
                "bodies": ("cast", "characters-layer", "people-body-*", "people-dress-*", "people-clips"),
                "growth": ("crops-layer",)}


# The gates an accepted gap may move a fault from (score/stages/gaps.py: a dated decision in data/checks/gaps/<place>.json)
# and the completion gate that fails it by name. Only these: any other gate's fault still stops its line.
GAP_GATES = {"assembly": ("placeholders", "resting"), "surfaces-check": ("stands level", "baked matches its surfaces"),
             "surfaces-paint": ("colour against the close-up",),
             # the ship rooms' box gate: a box on a plain code piece against a concept drawn before the plan (overseer
             # 2026-10-15; navigation's door leaf, the walkway's upper wall plate), as complete's boxes check below
             "complete-boxes": ("grounded",),
             # complete's own: the people the cast names and no accepted body of its look lays (the owner's rule: they
             # ship as named fails until the people work lands), a likeness no props file answers, a motion not built,
             # a row no stage makes yet (the launch's two far towers), a layout still taken from the source game (the
             # 18 places whose records cite it, overseer 2026-10-15), a box on a plain code piece against a concept drawn
             # before the plan (the ship's rooms, overseer 2026-10-15), a generated model with no clean take to paint
             # (the camp's canister and sample props, overseer 2026-10-16), an effect no record holds yet (the Moon
             # places' dust, wheel dust, spray and ship exhaust on the effects follow-up list, overseer 2026-10-16)
             "complete": ("people", "likeness", "motion", "rows", "game", "boxes", "painted", "effects", "picks", "reach")}
# The gates a batch gap moves a fault from (score/stages/batch_gaps.py: a take a paid step failed inside the batch, a gap
# by the owner's yes to the batch, the batch rule of 2026-10-20): each paid step's own sorting gate, and the readers
# down the line that would fail the take it left out (the likeness, complete: every gate, ALL). Only the faults of the
# objects a batch gap names move; any other fault still stops the line.
ALL = None
BATCH_GATES = {"pixal": ("takes",), "finish-route-list": ("library first",),
               "finish-route-split": ("one finish a face",), "surfaces-bake": ("baked",),
               "finish-route-recheck": ("library surface fits",), "likeness": ALL, "complete": ALL}


def with_gap_files(files, row=None):
    """A row's environment files and its place's gaps file where it names a gap of `row` (whole for complete, `row` None:
    gaps.files). It unwraps to the row's own files and keeps their attributes (the paint's carry), so the row's code
    version is its own."""
    def found(place):
        return {**(files(place) if callable(files) else files), **gaps.files(place, row)}
    found.__dict__.update(getattr(files, "__dict__", {}))
    if callable(files):  # a plain map has no code to hash
        found.__wrapped__ = files
    return found


def gap_moved(row, check):
    """A gate of `row` with its place's accepted gaps moved (gaps.moved): the owner's that name the gate, and the batch
    gaps its output and inputs carry where BATCH_GATES names it. Defined here, in the table, and unwrapping to the
    gate's own judge, so no row's code version takes in gaps.py: moving a verdict changes no output, and a paid row
    (the paint) is never bought again for it."""
    batch = batch_moves(row, check.name)

    def judged(output, inputs, evidence):
        carried = batch_gaps.of(inputs, output) if batch else []
        return gaps.moved(check.judge(output, inputs, evidence), gaps.entries(inputs, row, check.name) + carried)
    judged.__wrapped__ = check.judge
    return checks.Check(check.name, judged, check.evidence)


def batch_moves(row, check):
    """Whether a batch gap may move a fault from this gate of `row` (BATCH_GATES)."""
    gates = BATCH_GATES.get(row, ())
    return gates is ALL or check in gates


def accepted_gaps(row):
    """The rows the owner's accepted gaps reach (2026-10-14: the hangar's ship, the wreck's three pieces, the camp grounds'
    crane ship today as named fails), and the batch gaps (BATCH_GATES): a moving gate's faults on the named objects go
    down the line, and complete fails each gap by name with its numbers. Set here, in the table."""
    if row.name not in GAP_GATES and row.name not in BATCH_GATES:
        return row
    kept = tuple(gap_moved(row.name, check) if check.name in GAP_GATES.get(row.name, ()) or
                 batch_moves(row.name, check.name) else check for check in row.checks)
    named = (checks.Check(graph.GAPPED, gaps.judge_accepted),) if row.name == "complete" else ()
    reads = None if row.name == "complete" else row.name
    return dataclasses.replace(row, files=with_gap_files(row.files, reads), checks=(*kept, *named))


# The rendered pictures of each row that ship (to the library, the films, the paper), relative to its output: the grain
# check fails a grainy one (the owner, 2026-10-20: the Library's Camp picture full of specks). Left out: the paid
# light-passes (its looks ship only through light's mix), the Workbench turntables (no sampling noise) and the
# people's close-ups (an image model's, not a render).
GRAIN_PICTURES = {"light": "looks/*/*-look.png", "demo-film": "concept.png", "demo-film-extra": "*/concept.png",
                  "demo-stills": "*.png", "effects-look": "*/*/*-look.png", "crops-look": "render/*-look.png",
                  "physics-trial": "frames/*-look.png"}


def grained(row):
    """A row of GRAIN_PICTURES with the grain check over its pictures; its judge unwraps to grain.verdict, so the
    check's rules are in the row's code version."""
    if row.name not in GRAIN_PICTURES:
        return row

    def judged(output, inputs, evidence):
        return grain.verdict("grain", pathlib.Path(output).glob(GRAIN_PICTURES[row.name]), output)
    judged.__wrapped__ = grain.verdict
    return dataclasses.replace(row, checks=(*row.checks, checks.Check("grain", judged)))


def layered(row, names):
    """The assembly reading every layer stage of assembly.READS the table holds (`names`): a layer stage joins its
    reads the day it joins the table, and one not built yet is never silently stood in for by the seed's (the
    assembly's layers gate answers unknown on a layer the place needs and lacks)."""
    if row.name != "assembly":
        return row
    return dataclasses.replace(row, after={**row.after, **{name: wanted for name, wanted in assembly.READS.items()
                                                         if name in names}})


def worn(row):
    """A look's dress row read by a place's characters layer only where that place's accepted cast names the look
    (characters_layer.cast_looks), so a cast place waits on its own looks, not the slowest of all."""
    if not row.name.startswith(f"{characters_layer.DRESS}-"):
        return row
    look, _, coloured = row.name.removeprefix(f"{characters_layer.DRESS}-").partition("-in-")
    return dataclasses.replace(row, applies=lambda place: look in characters_layer.cast_looks(place) and (
        place == coloured if coloured else place not in characters_layer.coloured_places()))


OLD_SEED, SHIP_SEED = "usd-r3", "usd-ship"


PLACE_DEFINITIONS = REPO / "data/definitions/place.json"


@functools.cache
def ship_places():
    """The places data/definitions/place.json marks `ship` (the ship's rooms, which the game never had)."""
    return frozenset(name for name, entry in json.loads(PLACE_DEFINITIONS.read_text()).items()
                     if isinstance(entry, dict) and entry.get("ship"))


def ship_place(place):
    """A place the game never had (the ship's rooms): no round-three seed, its base stage written from its kit. Read
    from git (its `ship` mark in place.json), never from the disk: with the work folder lost (2026-10-19) a test for
    usd-ship/<place> took the cockpit off the ship's route and its cast blocked on a scene record it never had."""
    return place is not None and place in ship_places()


def ship_seeded(files):
    """A row's environment files with a ship place's base stage for its seed: the ship's places never had a round-three stage
    (usd-r3), so each one's is written from its installed kit by tools/usd/export.py into usd-ship/<place> (2026-10-15)
    and read there. Kept out of usd-r3, which the terrain and scene-record rows declare whole, so no environment key moves;
    a place with a round-three seed reads it as before."""
    def declared(place):
        found = files(place) if callable(files) else files
        if not ship_place(place):
            return found
        old = (f"{{seeds}}/{OLD_SEED}/{{place}}", f"{{seeds}}/{OLD_SEED}/{place}")
        return {name: f"{{seeds}}/{SHIP_SEED}/{place}" if path in old else path for name, path in found.items()}
    if callable(files):
        declared = functools.wraps(files)(declared)
    return declared


STAGES = tuple(grained(accepted_gaps(layered(worn(row), {stage.name for stage in STAGES}))) for row in STAGES)
# A process's code versions read the import folders it holds at its first key (score/graph/_code.py search_folders).
# `score run` and `score status` reach tools/characters/cast.py (a dress row's `applies`: cast_looks) before that, and
# the file puts its folder on the path; a process that keys a node first did not, and read every node whose code
# imports a tools/characters name as "code changed" (complete.py's stage requirement on the five prologue places:
# cast@ blocked there and pass, accepted in status, 2026-10-15). Loaded with the table, so every process keys alike.
characters_layer.loaded("cast")
STAGES = tuple(dataclasses.replace(row, files=ship_seeded(row.files)) if row.files else row for row in STAGES)


def ship_lit(applies):
    """The light rows for a ship place too: it has no old scene record, so light.applies (data/scene/<place>.json)
    leaves it out; its base stage is usd-ship/<place> (ship_seeded reads it as the seed) and its views are its own
    scene-record output's, which its light layer writes into views.json. Wrapped here, in the table, so no place with
    an old record moves."""
    def lit(place):
        return applies(place) or ship_place(place)
    return functools.wraps(applies)(lit)


def has_old_record(place):
    return place is not None and (REPO / "data" / "scene" / f"{place}.json").exists()


@contextlib.contextmanager
def shows_no_neighbours():
    """The light stage's neighbours (the places a place's old scene record shows) answered as none while the block
    runs: a place the game never had (the ship's) has no old record to read them from (2026-10-15: score status died
    in light-passes for the cockpit on data/scene/cockpit.json)."""
    kept = light.passes.neighbours, light.neighbours
    light.passes.neighbours = light.neighbours = lambda place: []
    try:
        yield
    finally:
        light.passes.neighbours, light.neighbours = kept


def no_old_record(files):
    """A light row's environment files for a place with no old scene record: no neighbours and no `scene` file (its record
    is the scene-record row's output, which the row reads); a place with one declares them as before. Wrapped here, in
    the table, so no place's key moves."""
    def declared(place):
        if has_old_record(place) or place is None:
            return files(place)
        with shows_no_neighbours():
            found = files(place)
        return {name: path for name, path in found.items() if name not in ("scene", f"scene {place}")}
    return functools.wraps(files)(declared)


def made_without_old_record(make):
    """A light row's make for a place with no old scene record, showing no neighbours (shows_no_neighbours); a place
    with one is made as before."""
    def made(inputs, out, seed, params):
        place = pathlib.Path(inputs["kit"]).stem
        if has_old_record(place):
            return make(inputs, out, seed, params)
        # the place's record is its scene-record output's (light.passes.record_of reads it first); `scene` names it
        # only so light.place_of finds the place
        inputs = dict(inputs, scene=pathlib.Path(inputs["scene-record"]) / "record" / f"{place}.json")
        with shows_no_neighbours():
            return make(inputs, out, seed, params)
    return functools.wraps(make)(made)


def sounded_from_plan(files):
    """The sound row's environment files for a place with no old scene record (the ship's): its plan stands as `scene`. The
    row reads only the place's name (the file's stem) and the objects and structure the record names, for where object
    sounds may play; a ship place's plan names none, so its sounds play at its inventory rows alone (2026-10-15: the
    runner refused the ship's run on the missing data/scene/<place>.json). A place with an old record reads it as
    before; wrapped here, in the table, so no place's key moves."""
    def declared(place):
        found = files(place)
        if place is None or has_old_record(place):
            return found
        return dict(found, scene="{data}/plans/" + f"{place}.json")
    return functools.wraps(files)(declared)


STAGES = tuple(dataclasses.replace(row, files=sounded_from_plan(row.files)) if row.name == "sound" else row
               for row in STAGES)
STAGES = tuple(dataclasses.replace(row, applies=ship_lit(row.applies), files=no_old_record(row.files),
                                   make=made_without_old_record(row.make))
               if row.name in ("light-layer", "light-passes", "light") and row.applies else row for row in STAGES)


def ship_assembled(row):
    """The assembly with a ship place's made pieces laid on its kit-built base (assembly/ship_made.py, 2026-10-15:
    the base lays the kit's code pieces only, so its bake had no object to lay the bunks, lockers and consoles in),
    each from the bake of the place that paints it, read beside; its plan, the kit layout's tools and ship_made.py
    declared. A place with a round-three seed is assembled as before: wrapped here, in the table, so its key stays."""
    files, neighbours, make = row.files, row.neighbours, row.make

    def declared(place):
        return {**files(place), **ship_made.files(place)} if ship_place(place) else files(place)

    def beside(place):
        return sorted({*neighbours(place), *ship_made.neighbours(place)}) if ship_place(place) else neighbours(place)

    def made(inputs, out, seed, params):
        place = pathlib.Path(inputs["seed"]).name
        if not ship_place(place):
            return make(inputs, out, seed, params)
        claimed = set(neighbours(place))  # the made pieces' bakes are ship_made's, not the surface data's claims
        make({name: path for name, path in inputs.items() if "@" not in name or name.split("@", 1)[1] in claimed},
             out, seed, params)
        laid, unlaid = ship_made.lay(inputs, out, place)
        if not (laid or unlaid):  # a place with no made rows (the walkway) is its seed's assembly, byte for byte
            return
        origin = json.loads((out / "origin.json").read_text())
        (out / "origin.json").write_text(json.dumps({**origin, "made pieces": laid, "made rows unlaid": unlaid},
                                                    indent=1))
    return dataclasses.replace(row, files=functools.wraps(files)(declared),
                               neighbours=functools.wraps(neighbours)(beside), make=functools.wraps(make)(made))


OWN_RECORD = "scene-record"


def own_record(place):
    """[place] for a ship place, which reads its own scene record (`OWN_RECORD@<place>`, read beside), else none."""
    return [place] if ship_place(place) else []


def record_beside(inputs, place):
    """The scene record a ship place's row reads beside (own_record): record/<place>.json in its output."""
    return pathlib.Path(inputs[f"{OWN_RECORD}@{place}"]) / "record" / f"{place}.json"


def reading_own_record(row):
    """The row reading, for a ship place, its own scene-record output beside (own_record), so its views come from the
    stage that writes them and wait on it (2026-10-19: they were a copy under work/demo/world1-r4/views, made by hand,
    lost with the work folder). A place with an old record reads nothing beside, so its key stays."""
    beside = {OWN_RECORD: ("scene-record", 1)}
    if row.beside and row.beside != beside:
        raise ValueError(f"{row.name} already reads beside; own_record would give its other reads the same places")
    return dataclasses.replace(row, beside=beside, neighbours=own_record)


def ship_cast(row):
    """cast for a ship place: it has no old record (data/scene/<place>.json), so its `scene` (the views it crowds
    from) is its own scene record, read beside (reading_own_record). Wrapped here, so no other place's key moves."""
    files, make = row.files, row.make

    def declared(place):
        found = files(place)
        return {name: path for name, path in found.items() if name != "scene"} if ship_place(place) else found

    def made(inputs, out, seed, params):
        place = pathlib.Path(inputs["record"]).stem
        if not ship_place(place):
            return make(inputs, out, seed, params)
        return make(dict(inputs, scene=record_beside(inputs, place)), out, seed, params)
    return reading_own_record(dataclasses.replace(row, files=functools.wraps(files)(declared),
                                                  make=functools.wraps(make)(made)))


def ship_seen(row):
    """surfaces-check with a view distance for a ship place's models (2026-10-15: every model's was none, so the
    cockpit's pedestal, side console and ceiling equipment and the engine room's fuel tank were unknown): its views
    its own scene record's, read beside (reading_own_record; it has no data/scene record), and its made
    models' spots where the ship kit lays them (its installed kit holds the code pieces only), laid beside the kit
    for the check. A place with a round-three seed is checked as before: wrapped here, so its key stays."""
    files, make = row.files, row.make

    def declared(place):
        if not ship_place(place):
            return files(place)
        laid = {name: pattern for name, pattern in ship_made.files(place).items() if not name.startswith("surfaces ")}
        return {**files(place), **laid}

    def made(inputs, out, seed, params):
        place = json.loads(pathlib.Path(inputs["surfaces"]).read_text())["place"]
        if not ship_place(place):
            return make(inputs, out, seed, params)
        inventory = json.loads(pathlib.Path(inputs[f"inventory {place}"]).read_text())
        found = ship_made.row_models(inventory, {place: inputs["surfaces"]})
        models = {row: model for row, (_, model) in found.items()}
        kit = json.loads(pathlib.Path(inputs["kit"]).read_text())
        made_pieces = ship_made.pieces(place, json.loads(pathlib.Path(inputs["plan"]).read_text()), inventory, models)
        seen = out / ".seen-kit.json"
        seen.write_text(json.dumps(dict(kit, pieces=kit["pieces"] + made_pieces)))
        try:
            return make(dict(inputs, kit=seen, **{"scene record": record_beside(inputs, place)}), out, seed, params)
        finally:
            seen.unlink()
    return reading_own_record(dataclasses.replace(row, files=functools.wraps(files)(declared),
                                                  make=functools.wraps(make)(made)))


def ship_completed(row):
    """complete reading, for a ship place, the likeness output of each other place whose bake lays one of its made
    pieces (2026-10-16: the galley's lockers are the shiplock's take, held to their close-up by likeness@shiplock, and
    the gate read only likeness@galley), each where that place has props rows; read beside, so no other place's key
    moves (a place with no such neighbour has no beside part)."""
    def beside(place):
        return [other for other in ship_made.neighbours(place) if prop_data.applies(other)] if ship_place(place) else []
    return dataclasses.replace(row, beside={"likeness": ("props-likeness", 1)}, neighbours=beside)


STAGES = tuple(ship_assembled(row) if row.name == "assembly" else ship_seen(row) if row.name == "surfaces-check"
               else ship_completed(row) if row.name == "complete" else ship_cast(row) if row.name == "cast" else row
               for row in STAGES)
# The assembly reading the round-three seed itself, before earth_seeded below: the worked example's (stages_test.py).
ASSEMBLY = next(row for row in STAGES if row.name == "assembly")


def earth_place(place):
    """A place of the earth seed rows: its kit is laid and it is no ship place (whose base is usd-ship's)."""
    return place is not None and kit_laid(place) and not ship_place(place)


# earth-kit bakes the kit's named code fallbacks only, the rows not handed to the shared loop (#41;
# earth_seed.fallbacks); the shell's sections are the kit adapter's (shapes_first.KIT), a layer the assembly takes.
EARTH_KIT = graph.Stage("earth-kit", "place", earth_seed.make_kit, earth_seed.EARTH_KIT,
                        (checks.Check("made", late_bake.judge_made),
                         checks.Check("surfaces", late_bake.judge_surfaces)),
                        files=earth_seed.kit_files, paid=True, euros=earth_seed.EUROS, applies=earth_place)
EARTH_SEED = graph.Stage("earth-seed", "place", earth_seed.make_seed, earth_seed.EARTH_SEED, earth_seed.SEED_CHECKS,
                         files=earth_seed.seed_files,
                         after={"earth-kit": ("earth-kit", 2), "surfaces-bake": ("surfaces-bake", 1)},
                         beside={"surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                         neighbours=assembly.claiming_places, applies=earth_place)
SEED_READ = {"earth-seed": (earth_seed.EARTH_SEED.schema, earth_seed.EARTH_SEED.version)}
# Every row that read a place's round-three seed (`{seeds}/usd-r3/<place>`), each now reading earth-seed instead
# (earth_seeded); stages_test.py holds the list to the declared files. terrain-look, the last reader, is retired (#27).
EARTH_SEEDED = ("assembly", "settle", "effects-layer", "effects-look", "physics-trial", "cast", "motion",
                "motion-models", "light-layer", "light-passes", "light-haze", "light", "scene-record")


def seed_named(pattern, place):
    """The earth place whose round-three seed a declared file pattern is (`{place}` the node's own), else None."""
    start = f"{{seeds}}/{OLD_SEED}/"
    if not isinstance(pattern, str) or not pattern.startswith(start):
        return None
    named = pattern[len(start):].replace("{place}", str(place))
    return named if "/" not in named and earth_place(named) else None


def seed_inputs(inputs, found, place):
    """`inputs` with each declared seed (`found`, the row's own files) read from earth-seed: the place's own from its
    after, another place's from beside (`earth-seed@<other>`), each its stage folder (earth_seed.place_in's form)."""
    taken = dict(inputs)
    for name, pattern in found.items():
        named = seed_named(pattern, place)
        if named is not None:
            node = "earth-seed" if named == place else f"earth-seed@{named}"
            taken[name] = pathlib.Path(inputs[node]) / named
    return taken


def seeded_place(inputs):
    """The place a node reading its own earth seed is made for (the seed output's one stage folder), else None."""
    return earth_seed.place_in(inputs["earth-seed"]).name if "earth-seed" in inputs else None


def earth_seeded(row):
    """A row that read round-three seeds reading each from its earth-seed row (#27: the work folder's usd-r3 was lost
    on 2026-10-19 and blocked every line behind it): the place's own as an `after`, another place's beside; its make,
    judges and gatherers given the seed folders under their old names. A seed of a place with no earth-seed row (no kit
    laid) stays a declared file, so it is still named lost."""
    files, place_files = row.files, row.files if callable(row.files) else (lambda place: row.files)

    def declared(place):
        found = place_files(place)
        return {name: path for name, path in found.items() if seed_named(path, place) is None}

    def others(place):  # a row reading beside already (the assembly's claims) reads no other place's seed
        return sorted({seed_named(path, place) for path in place_files(place).values()} - {None, place})

    def with_seeds(function, position):
        @functools.wraps(function)
        def read(*arguments):
            arguments = list(arguments)
            place = seeded_place(arguments[position])
            if place is not None:
                arguments[position] = seed_inputs(arguments[position], place_files(place), place)
            return function(*arguments)
        return read

    beside = row.beside or SEED_READ
    return dataclasses.replace(
        row, files=functools.wraps(files)(declared) if callable(files) else declared,
        after={**row.after, **SEED_READ}, beside=beside, neighbours=row.neighbours or others,
        make=with_seeds(row.make, 0),
        checks=tuple(dataclasses.replace(check, judge=with_seeds(check.judge, 1)) for check in row.checks),
        gatherers={name: (with_seeds(gather, 1), euros) for name, (gather, euros) in row.gatherers.items()})


def joined_ground(row):
    """The assembly taking the ground-join's layer of the place's ground in place of the terrain row's, where the place
    has the row: the terrain adapter's after-step in the shared loop (shapes_first.TERRAIN), only where the place handed
    the loop terrain rows (Runner.reads leaves it out elsewhere, so no other place's key moves)."""
    make = row.make

    def made(inputs, out, seed, params):
        return make(dict(inputs, terrain=inputs["ground-join"]) if "ground-join" in inputs else inputs, out, seed,
                    params)
    return dataclasses.replace(row, after={**row.after, "ground-join": ("ground-join", 1)},
                               make=functools.wraps(make)(made))


STAGES = (*(earth_seeded(joined_ground(row) if row.name == "assembly" else row) if row.name in EARTH_SEEDED else row
            for row in STAGES), EARTH_KIT, EARTH_SEED)
# The library rows (score/stages/library), appended last: library@<place> hands every accepted output of its place's
# line to the creator's library, library-world the environment's own; nothing reads them, so they re-key no other row. A place
# is complete once its library node stands accepted, the environment once every one does (library.world_completion).
STAGES = (*STAGES, *library.rows(STAGES, REPO / "data"))
# Each item a place's handover made new gets its preview clip (score/stages/library/clips, paid; owner, 2026-10-20),
# rendered after the handover in the same batch; the one row that reads library@<place>, and nothing reads it. Its
# benchmark, library-clips-sample, clips the few drafts data/definitions/clip_samples.json names.
STAGES = (*STAGES, library_clips.STAGE, library_clips.SAMPLE_STAGE)
# A place's own rows, which apply to every place, kept off a line of models no place owns (the people's, #41:
# shapes_first.no_place): it has no stage to assemble, complete or hand over, only the shared loop's rows.
PLACE_ONLY = ("assembly", "complete", "library", "library-clips")


def placed(applies):
    """A place's own row's `applies`: never on a line no place owns, else its own (None: every place)."""
    def applied(place):
        return not shapes_first.no_place(place) and (applies is None or applies(place))
    return applied


STAGES = tuple(dataclasses.replace(row, applies=placed(row.applies)) if row.name in PLACE_ONLY else row
               for row in STAGES)


def world1():
    """Environment 1: its record, its data in the repository, its old outputs in the work folder, the prop tools' home (the
    raw models, the routes' bake jobs) and the repository (the code a stage hands to a rented machine)."""
    return graph.Environment.from_file(WORLD1, data=str(REPO / "data"), seeds=str(PROPS_HOME / "work"),
                                 home=str(PROPS_HOME), repo=str(REPO))


def places(world):
    """An environment's places: each with a kit or a plan in its data (a new place has its plan before its kit is laid;
    none for an environment without data, the images environment), less the scenes places/within.json names `merged`
    into another (no stage line of their own: the owner, 2026-10-21, navigation into the cockpit)."""
    if "data" not in world.roots:
        return []
    data = pathlib.Path(world.roots["data"])
    within = data / "places/within.json"
    merged = json.loads(within.read_text()).get("merged", {}) if within.exists() else {}
    return sorted({path.stem for folder in ("kit", "plans") for path in (data / folder).glob("*.json")} - set(merged))


WORLDS = {"world1": world1, "images": images.image_world}
# An environment whose stages are not environment 1's: the images environment (each job image rebuilt and proved, score/stages/images).
TABLES = {"images": images.STAGES}


def runner(store=None, world=None):
    """The runner over the stage table, on environment 1 and the framework's store unless told otherwise."""
    world = world or world1()
    return graph.Runner(TABLES.get(world.name, STAGES), world, store or Store.default())
