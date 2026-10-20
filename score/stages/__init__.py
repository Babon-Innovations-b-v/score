"""The stage table: every stage the runner knows, in the paper's order, and environment 1 as the runner reads it.

    from score import stages
    runner = stages.runner()        # environment 1, the framework's store on this machine
    runner.status(["hangar", "hdoor"])
    runner.drive(stages.places(runner.world))   # every line of the environment to its end (python -m score run world1)

Step 0 holds the worked example: assembly (P5) on environment 1's round-three stages as unverified seeds, and complete
(P11). Terrain (the paper's Methods, "Terrain") makes every ground of the environment from its plan, one environment node,
free (the code fallback until its prop-pipeline adapter lands), and ground-fit judges each seated place on it. The surface stage (step 1, its overlay) is each place's
own line of rows, split to checked bake, beside the environment's seed of the finish registry. Effects (experimental) makes
each staged place's effects layer from its record, which its assembly takes; effects-look renders it before and
after. Neighbours (experimental) stands the places a place's scene record shows in its assembly, each read as its
own accepted assembly. The prop route (props: close-up, Pixal3D, then the surface line, then the likeness gate) runs
only for a place with prop data. Plan and scene-record (experimental) write a place's scene record from its plan and
concept. Cast (experimental) places each place's people and measures them against its concept's count
(concept_people) and its geometry. Motion (experimental) makes each place's motion layer from its game motions
and its rigid moves. Each stage joins the table when it is built in its step (docs/bible.md, architecture/components).
"""
import contextlib
import dataclasses
import functools
import json
import pathlib

from score import checks, contracts, graph
from score.stages import (assembly, cast, complete, concept_people, concept_view, crops, demo_film, demo_turntable,
                          effects, gaps, images, library, light, motion, people, people_takes, physics,
                          props, proposals, rough_model, scene_record, settling, shell_split, sound, surface_tiles,
                          surfaces, terrain)
from score.stages.surfaces import bake_check, carry, library_reads
import score.stages.cast.layer as characters_layer
import score.stages.demo_film.stills as demo_stills
from score.stages.surfaces.surface_gates import guarded
from score.stages.assembly import neighbours
import score.stages.motion.models as motion_models
import score.stages.motion.models.boxes as model_boxes
import score.stages.props.prop_data as prop_data
import score.stages.complete.boxes as complete_boxes
from score.stages.assembly import ship_made
from score.stages.effects import look as effects_look
from score.stages.terrain import fit as ground_fit, inputs as terrain_inputs, look
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
# Experimental (PRD #6) until the owner reviews it: the proof place's before and after its made ground, rendered.
TERRAIN_LOOK = graph.Stage("terrain-look", "place", look.make, look.LOOK, look.CHECKS, files=look.files,
                           after={"assembly": ("openusd-stage", 1)}, paid=True, euros=look.EUROS,
                           applies=lambda place: place in look.LOOKED)
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
                   files=kit_if_laid(scene_record.plan.files), applies=scene_record.written,
                   beside={"shell-split": ("shell-split", 1)}, upward=True, neighbours=shell_of)
# Shapes first (CONTEXT.md "shell split"): an outside shell's plan split into the shapes of its inside places, free and
# local, for a place whose plan has a `split`; each inside place's plan reads its shell's split beside it (PLAN's
# `beside`, upward: up to the shell, never back down), so the drive makes the shell's split before its inside places.
SHELL_SPLIT = graph.Stage("shell-split", "place", shell_split.make, shell_split.CONTRACT, shell_split.CHECKS,
                          files=shell_split.files, after={"plan": ("place-plan", 2)}, applies=shell_split.applies)
# The place's rough model (shapes first: the prop pipeline on its whole concept, the picture its plan names), after its
# plan (score/stages/rough_model, its overlay); paid, for every place with a plan.
ROUGH_MODEL = graph.Stage("rough-model", "place", rough_model.make, rough_model.CONTRACT, rough_model.CHECKS,
                          files=rough_model.files, after=rough_model.AFTER, paid=True, euros=rough_model.EUROS,
                          applies=scene_record.written)
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
# concept's people (concept_people, in this table so the cast reads its accepted count) and its seed's geometry.
# Its `made` gate reads the looks' dress rows as optional inputs: a look whose dressed body stands usable is made.
DRESS_ROWS = tuple(row.name for row in people.ROWS if row.name.startswith(f"{characters_layer.DRESS}-"))
def cast_place(place):
    """A place with a cast row: its concept shows people (cast.PLACES), or its cast record names people its concept
    does not show, for the record's count_reason (the cockpit's two pilots of the owner's brief, overseer
    2026-10-15). In the table, so no other place's row moves."""
    path = REPO / "data/characters" / f"{place}.json"
    return place in cast.PLACES or (path.exists() and bool(json.loads(path.read_text()).get("people")))


CAST = graph.Stage("cast", "place", cast.make, cast.CAST, cast.CHECKS, files=cast.files,
                   after={"concept_people": ("concept-people", 1), **{name: ("people-dress", 1) for name in DRESS_ROWS}},
                   optional=DRESS_ROWS, applies=cast_place)
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
    within its reach). Set here, in the table, not in surfaces/__init__.py, which is in the turntable's and SegviGen's
    code version: an edit there re-buys them. Moves into surfaces/__init__.py, and the old check leaves place_line.py,
    once their fan-out of 2026-10-12 is done."""
    if row.name != "surfaces-check":
        return row
    return dataclasses.replace(row, make=bake_check.make_check,
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


def crops_check_files(place):
    """The crops twin's check files: its line's naming files and the stance rules check_step reads, as check_files
    gives the place's surfaces-check. Set here, in the table, so the crops line's paid rows (whose file maps are in
    crops/line.py) do not move."""
    return {**crops.line.naming_files(place), "stance rules": "{data}/checks/stance.json"}


def crops_bake_checked(row):
    """crops-surfaces-check with the stance rules among its files (crops_check_files)."""
    return dataclasses.replace(row, files=crops_check_files) if row.name == "crops-surfaces-check" else row


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


# The people's render row is not run: the owner reviews people in the browser viewer and page renders wait for each
# place's assembly (captain, 2026-10-13); its looks left the people line.
NOT_RUN = ("people-look",)


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


def people_surfaces(place):
    """The people line's surface data (an environment line: no place)."""
    from score.stages.people import line as people_line
    return json.loads(people_line.DATA.read_text())


# The rows keyed on the library parts they read (surfaces/library_reads.py), each with its surface data's reader.
LIBRARY_READERS = {"surfaces-paint": surfaces.data.record, "surfaces-bake": surfaces.data.record,
                   "crops-surfaces-paint": crops.line.line_record, "crops-surfaces-bake": crops.line.line_record,
                   "people-paint": people_surfaces}


def library_narrowed(row):
    """A paint or bake row (and its crops and people twins) keyed on the library surfaces and place.json entries it
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
        own = prop_data.FOLDER.parent / "inventory" / f"{place}.json"
        scene = json.loads(own.read_text()).get("scene", place) if own.exists() else place
        return {**found, "inventories": "{data}/inventory/" + f"{scene}.json"}
    return declared


def prop_fed(row):
    """finish-route-views waiting on the prop route's Pixal3D row (props.FEEDS), whose takes its line paints. A place
    with no prop data reads without it (Runner.reads), so its key does not move."""
    if row.name != "finish-route-views":
        return row
    return dataclasses.replace(row, after={**row.after, **props.FEEDS})


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
# fails it only on its named gaps (gapped: the overseer, 2026-10-15), only for the places with a film record in
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


STAGES = (TERRAIN, CONCEPT_VIEWS, PARTITION_PROPOSALS, DEMO_TURNTABLES, EFFECTS, SETTLE, SOUND, ASSEMBLY, NEIGHBOURS,
          COMPLETE, DEMO_FILM, DEMO_FILM_EXTRA, DEMO_STILLS,
          GROUND_FIT, TERRAIN_LOOK, EFFECTS_LOOK, PHYSICS_LAYER,
          PHYSICS_TRIAL,
          dataclasses.replace(props.INPUTS, files=box_checked(scene_inventory_read(props.INPUTS.files))), props.CLOSEUP, props.PIXAL,
          *map(library_narrowed, map(prop_fed, map(feet_checked, map(bake_checked, surfaces.ROWS)))),
          props.CALIBRATION, props.LIKENESS,
          *(library_narrowed(far_judged(row)) for row in people.ROWS if row.name not in NOT_RUN), *people_takes.ROWS, PLAN, ROUGH_MODEL, SHELL_SPLIT, SCENE_RECORD, concept_people.STAGE, CAST, CHARACTERS, MOTION_MODELS, MOTION_MODEL_BOXES, MOTION,
          *light.ROWS, *map(library_narrowed, map(crops_bake_checked, crops.ROWS)), COMPLETE_BOXES,
          surface_tiles.STAGE)

# The motion layer (CONTEXT.md "motion", #26): one layer for everything that moves, its modules and the rows (fnmatch
# patterns) that make each. Every model comes from the prop pipeline; each module only adds what moves it.
MOTION_LAYER = {"models": ("motion-models", "motion-models-boxes"),  # rigid moving things' models laid
                "rigid": ("motion",),  # joints and paths: hinge, rail, lane, spin; the motion check
                "physics": ("settle", "physics-layer", "physics-trial"),  # settling, falling, cloth
                "bodies": ("cast", "characters-layer", "people-body-*", "people-dress-*", "people-clips"),
                "growth": ("crops-layer",)}


# The gates a named gap may move a fault from (score/stages/gaps.py: a dated decision in data/checks/gaps/<place>.json)
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


def with_gap_files(files, row=None):
    """A row's environment files and its place's gaps file where it names a gap of `row` (whole for complete, `row` None:
    gaps.files). It unwraps to the row's own files and keeps their attributes (the paint's carry), so the row's code
    version is its own."""
    def found(place):
        return {**(files(place) if callable(files) else files), **gaps.files(place, row)}
    found.__dict__.update(getattr(files, "__dict__", {}))
    found.__wrapped__ = files
    return found


def gap_moved(row, check):
    """A gate of `row` with its place's named gaps moved (gaps.moved). Defined here, in the table, and unwrapping to
    the gate's own judge, so no row's code version takes in gaps.py: moving a verdict changes no output, and a paid
    row (the paint) is never bought again for it."""
    def judged(output, inputs, evidence):
        return gaps.moved(check.judge(output, inputs, evidence), gaps.entries(inputs, row, check.name))
    judged.__wrapped__ = check.judge
    return checks.Check(check.name, judged, check.evidence)


def named_gaps(row):
    """The rows the owner's named gaps reach (2026-10-14: the hangar's ship, the wreck's three pieces, the camp grounds'
    crane ship today as named fails): a moving gate's faults on the named objects go down the line, and complete fails
    each gap by name with its numbers. Set here, in the table."""
    if row.name not in GAP_GATES and row.name != "complete":
        return row
    moving = GAP_GATES.get(row.name, ())
    kept = tuple(gap_moved(row.name, check) if check.name in moving else check for check in row.checks)
    named = (checks.Check(graph.GAPPED, gaps.judge_named),) if row.name == "complete" else ()
    reads = None if row.name == "complete" else row.name
    return dataclasses.replace(row, files=with_gap_files(row.files, reads), checks=(*kept, *named))


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


STAGES = tuple(named_gaps(layered(worn(row), {stage.name for stage in STAGES})) for row in STAGES)
# A process's code versions read the import folders it holds at its first key (score/graph/_code.py search_folders).
# `score run` and `score status` reach tools/characters/cast.py (a dress row's `applies`: cast_looks) before that, and
# the file puts its folder on the path; a process that keys a node first did not, and read every node whose code
# imports a tools/characters name as "code changed" (complete.py's stage requirement on the five prologue places:
# cast@ blocked there and pass, accepted in status, 2026-10-15). Loaded with the table, so every process keys alike.
characters_layer.loaded("cast")
STAGES = tuple(dataclasses.replace(row, files=ship_seeded(row.files)) if row.files else row for row in STAGES)


def ship_lit(applies):
    """The light rows for a ship place too: it has no round-three seed, so light.applies (a usd-r3 stage and the
    demo's views) leaves it out; its base stage is usd-ship/<place> (ship_seeded reads it as the seed) and its views
    are its scene record's, written as the demo's views file (2026-10-15). Wrapped here, in the table, so no place
    with a round-three seed moves."""
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
ASSEMBLY = next(row for row in STAGES if row.name == "assembly")
# The library rows (score/stages/library), appended last: library@<place> hands every accepted output of its place's
# line to the creator's library, library-world the environment's own; nothing reads them, so they re-key no other row. A place
# is complete once its library node stands accepted, the environment once every one does (library.world_completion).
STAGES = (*STAGES, *library.rows(STAGES, REPO / "data"))


def world1():
    """Environment 1: its record, its data in the repository, its old outputs in the work folder, the prop tools' home (the
    raw models, the routes' bake jobs) and the repository (the code a stage hands to a rented machine)."""
    return graph.Environment.from_file(WORLD1, data=str(REPO / "data"), seeds=str(PROPS_HOME / "work"),
                                 home=str(PROPS_HOME), repo=str(REPO))


def places(world):
    """An environment's places: each with a kit or a plan in its data (a new place has its plan before its kit is laid;
    none for an environment without data, the images environment)."""
    if "data" not in world.roots:
        return []
    data = pathlib.Path(world.roots["data"])
    return sorted({path.stem for folder in ("kit", "plans") for path in (data / folder).glob("*.json")})


WORLDS = {"world1": world1, "images": images.image_world}
# An environment whose stages are not environment 1's: the images environment (each job image rebuilt and proved, score/stages/images).
TABLES = {"images": images.STAGES}


def runner(store=None, world=None):
    """The runner over the stage table, on environment 1 and the framework's store unless told otherwise."""
    world = world or world1()
    return graph.Runner(TABLES.get(world.name, STAGES), world, store or Store.default())
