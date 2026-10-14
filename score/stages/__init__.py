"""The stage table: every stage the runner knows, in the paper's order, and world 1 as the runner reads it.

    from score import stages
    runner = stages.runner()        # world 1, the framework's store on this machine
    runner.status(["hangar", "hdoor"])
    runner.drive(stages.places(runner.world))   # every line of the world to its end (python -m score run world1)

Step 0 holds the worked example: assembly (P5) on world 1's round-three stages as unverified seeds, and complete
(P11). Terrain (the paper's Methods, "Terrain") makes every ground of the world from its plan, one world node, paid
(pictures and depth in the cloud, cleared by the runner). The surface stage (step 1, its overlay) is each place's
own line of rows, split to checked bake, beside the world's seed of the finish registry. Effects (experimental) makes
each staged place's effects layer from its record, which its assembly takes; effects-look renders it before and
after. Neighbours (experimental) stands the places a place's scene record shows in its assembly, each read as its
own accepted assembly. The prop route (props: close-up, Pixal3D, then the surface line, then the likeness gate) runs
only for a place with prop data. Plan and scene-record (experimental) write a place's scene record from its plan and
concept. Cast (experimental) places each place's people and measures them against its concept's count
(concept_people) and its geometry. Motion (experimental) makes each place's motion layer from its game motions
and its movers. Each stage joins the table when it is built in its step (docs/bible.md, architecture/components).
"""
import dataclasses
import functools
import json
import pathlib

from score import checks, contracts, graph
from score.stages import (assembly, cast, complete, concept_people, concept_view, crops, demo_film, demo_turntable,
                          effects, gaps, images, light, machines, motion, people, people_takes, physics, props,
                          scene_record, settling, sound, surfaces, terrain)
from score.stages.surfaces import bake_check, carry, library_reads
import score.stages.cast.layer as characters_layer
from score.stages.surfaces.surface_gates import guarded
from score.stages.assembly import neighbours
import score.stages.machines.boxes as machine_boxes
from score.stages.effects import look as effects_look
from score.stages.terrain import inputs as terrain_inputs, look
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[2]
WORLD1 = REPO / "data/definitions/world.json"

TERRAIN = graph.Stage("terrain", "world", terrain.make, terrain.GROUNDS, terrain.CHECKS, files=terrain_inputs.FILES,
                      paid=True, euros=terrain.EUROS)
# Experimental (PRD #6) until the owner reviews it: each staged place's effects layer (effects.STAGED), which its
# assembly takes.
EFFECTS = graph.Stage("effects-layer", "place", effects.make, effects.LAYER, effects.CHECKS, files=effects.files,
                      applies=lambda place: place in effects.STAGED)
# Experimental (PRD #6) until the owner reviews it: each place's motion layer, the game's timed motions and the movers
# SCORE gives the things that move there (data/movers), over its seed with its accepted scene record written in (the
# seed alone where the place has no scene-record row); the final assembly takes it.
MOTION = graph.Stage("motion", "place", motion.make, motion.LAYER, motion.CHECKS, files=motion.files,
                     after={"scene-record": ("scene-record", 1), "terrain": ("grounds", 1),
                            "machines-layer": ("machines-layer", 1)},
                     applies=motion.applies)
# Experimental (PRD #6) until the owner reviews it: where each place's objects come to rest on its made ground,
# which its assembly takes (assembly.LAYERS). A place joins SETTLED once its settle row has passed (resting track).
SETTLED = ("airlock", "campgrounds", "garage", "greenhouse", "habitat", "hangar", "lab", "square", "workshop",
           "wreck")
SETTLE = graph.Stage("settle", "place", settling.make, settling.SETTLE_LAYER, settling.CHECKS, files=settling.files,
                     after={"scene-record": ("scene-record", 1), "terrain": ("grounds", 1)}, paid=True,
                     euros=settling.EUROS,
                     applies=lambda place: place in SETTLED)
# The place's final assembly: its seed with every accepted layer it reads in place of the seed's part (assembly.READS,
# joined in `layered` for each layer stage the table holds), its layers gate unknown while one it needs is missing.
ASSEMBLY = graph.Stage("assembly", "place", assembly.make_from_seed, contracts.OPENUSD_STAGE, assembly.CHECKS,
                       files=assembly.files, gatherers=assembly.GATHERERS,
                       after={"terrain": ("grounds", 1),
                              "surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                       beside={"surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)},
                       neighbours=assembly.claiming_places)
# Experimental (PRD #6) until the owner reviews it: each place's machines (data/machines/<place>.json), made models laid
# on what holds them up, as a layer the assembly takes.
MACHINES = graph.Stage("machines-layer", "place", machines.make, machines.LAYER_CONTRACT, machines.CHECKS,
                       files=machines.files, after=machines.AFTER, applies=machines.applies)
# Experimental (PRD #6): SAM 3's grounding of a place's machine rows' boxes, so the prop route may draw them.
MACHINE_BOXES = graph.Stage("machines-boxes", "place", machine_boxes.make_boxes, machine_boxes.CONTRACT,
                            machine_boxes.CHECKS, files=machine_boxes.files, paid=True, euros=machine_boxes.EUROS,
                            applies=machine_boxes.applies)
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
                              "characters-layer": ("characters-layer", 1)})
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
    """The plan row's world files without `kit` for a place whose kit is not laid, so its plan runs before it.
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


PLAN = graph.Stage("plan", "place", plan_as_kit(scene_record.plan.make, 0), scene_record.plan.PLACE_PLAN,
                   tuple(dataclasses.replace(check, judge=plan_as_kit(check.judge, 1))
                         for check in scene_record.plan.CHECKS),
                   files=kit_if_laid(scene_record.plan.files), applies=scene_record.written)
# The openings gate's finding for a place no made ground seats (scene_record/gates.py judge_openings).
NO_GROUND = "no made ground seats this place: its outside cannot be judged"


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
                                 if check.name == "openings" else check for check in scene_record.gates.CHECKS),
                           files=scene_record.writer.files,
                           after={"plan": ("place-plan", 2), "terrain": ("grounds", 1)},
                           applies=scene_record.written)
# Experimental (design 5, 2026-10-12) until the owner reviews it: each place's cast placed and measured against its
# concept's people (concept_people, in this table so the cast reads its accepted count) and its seed's geometry.
# Its `made` gate reads the looks' dress rows as optional inputs: a look whose dressed body stands usable is made.
DRESS_ROWS = tuple(row.name for row in people.ROWS if row.name.startswith(f"{characters_layer.DRESS}-"))
CAST = graph.Stage("cast", "place", cast.make, cast.CAST, cast.CHECKS, files=cast.files,
                   after={"concept_people": ("concept-people", 1), **{name: ("people-dress", 1) for name in DRESS_ROWS}},
                   optional=DRESS_ROWS, applies=lambda place: place in cast.PLACES)
# Experimental (2026-10-13): each cast place's people laid from its accepted cast, each in its own look's accepted
# dressed body (score/stages/cast/layer.py), as a layer the assembly takes. Its dress rows are optional reads: a look
# whose body is not usable is left out by name (the overseer's 14:00 rule: assemble with what passed; complete fails
# the gap), never a stand-in.
CHARACTERS = graph.Stage("characters-layer", "place", characters_layer.make, characters_layer.CONTRACT,
                         characters_layer.CHECKS, files=characters_layer.files,
                         after={"cast": ("cast", 1), **{name: ("people-dress", 1) for name in DRESS_ROWS}},
                         optional=DRESS_ROWS, applies=lambda place: place in cast.PLACES)
# Experimental (PRD #6) until the owner has heard it: each place's sound layer data (its sounds, their files and levels,
# MOSS takes for briefs no world file answers, paid), for the place's assembly to write into its stage.
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
    """The check's world files: the paint's (its line's, the inventories, the resting rules), the stance rules, and
    the place's kit and scene record (each model's spots and the views, its view distance)."""
    return {**{name: pattern for name, pattern in paint_files(place).items() if name != "paint script"},
            "stance rules": "{data}/checks/stance.json", "kit": "{data}/kit/" + f"{place}.json",
            "scene record": "{data}/scene/" + f"{place}.json"}


def feet_checked(row):
    """surfaces-paint with the gate "feet in one plane" beside its own (place_line.judge_feet: a take's short legs are
    stretched down before its bake, a missing leg fails by name). Set here, as bake_checked is, so the turntable's and
    SegviGen's code version does not move."""
    if row.name != "surfaces-paint":
        return row
    return dataclasses.replace(row, checks=(*row.checks, guarded("feet in one plane", surfaces.place_line.judge_feet)),
                               files=paint_files)


def paint_files(place):
    """The paint's world files: the line's, and the inventory of each place a take is made for with the resting rules,
    which it reads to tell a take laid loose on the floor or held, whose feet it levels (place_line.stands_on_feet)."""
    import stage_inputs  # tools/usd, on the path by the assembly stage's import: a place's inventory, or its kit's
    inventories = {f"inventory {entry['place']}": "{data}/inventory/" + stage_inputs.inventory_path(entry["place"]).name
                   for entry in surfaces.data.takes(place).values()}
    return {**surfaces.data.line_files(place), **inventories, "resting rules": "{data}/checks/resting.json",
            "paint script": "{repo}/score/stages/surfaces/inside/paint_take.py"}  # run by path on the machine


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
    """The people line's surface data (a world line: no place)."""
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


def prop_fed(row):
    """surfaces-inputs waiting on the prop route's Pixal3D row (props.FEEDS), whose takes its line paints. A place
    with no prop data reads without it (Runner.reads), so its key does not move."""
    if row.name != "surfaces-inputs":
        return row
    return dataclasses.replace(row, after={**row.after, **props.FEEDS})


# Experimental (2026-10-14) until the owner reviews it: concept views drawn by Pro from a creator's reference and a
# written request (data/definitions/concept_views.json), one world node, paid: the ship's top and side views first.
CONCEPT_VIEWS = graph.Stage("concept-views", "world", concept_view.make, concept_view.CONTRACT, concept_view.CHECKS,
                            files=concept_view.files, paid=True, euros=concept_view.euros())
# Experimental (2026-10-14): models that already exist turned round for the paper's demos
# (data/definitions/demo_turntables.json), one world node, paid: demo K2's hub objects first.
DEMO_TURNTABLES = graph.Stage("demo-turntables", "world", demo_turntable.make, demo_turntable.CONTRACT,
                              demo_turntable.CHECKS, files=demo_turntable.files, paid=True,
                              euros=demo_turntable.euros())
# Experimental (2026-10-14): demo K9's walk-through film of a place from its final stage once it passes complete, only
# for the places with a film record in data/definitions/demo_films/, paid.
DEMO_FILM = graph.Stage("demo-film", "place", demo_film.make, demo_film.CONTRACT, demo_film.CHECKS,
                        files=demo_film.files, after={"assembly": ("openusd-stage", 1),
                                                      "neighbours": ("openusd-stage", 1),
                                                      "complete": ("place-manifest", 1)},
                        paid=True, euros=demo_film.EUROS, applies=demo_film.applies)
# A place's other films (the ship's hull through the hangar), one node a place, so its own film's key never moves.
DEMO_FILM_EXTRA = dataclasses.replace(DEMO_FILM, name="demo-film-extra", make=demo_film.make_extra,
                                      contract=demo_film.EXTRA_CONTRACT, checks=demo_film.EXTRA_CHECKS,
                                      files=demo_film.extra_files, applies=demo_film.applies_extra)


STAGES = (TERRAIN, CONCEPT_VIEWS, DEMO_TURNTABLES, EFFECTS, SETTLE, SOUND, ASSEMBLY, NEIGHBOURS, COMPLETE, DEMO_FILM,
          DEMO_FILM_EXTRA,
          TERRAIN_LOOK, EFFECTS_LOOK, PHYSICS_LAYER,
          PHYSICS_TRIAL,
          props.INPUTS, props.CLOSEUP, props.PIXAL,
          *map(library_narrowed, map(prop_fed, map(feet_checked, map(bake_checked, surfaces.ROWS)))),
          props.CALIBRATION, props.LIKENESS,
          *(library_narrowed(far_judged(row)) for row in people.ROWS if row.name not in NOT_RUN), *people_takes.ROWS, PLAN, SCENE_RECORD, concept_people.STAGE, CAST, CHARACTERS, MACHINES, MACHINE_BOXES, MOTION,
          *light.ROWS, *map(library_narrowed, crops.ROWS))


# The gates a named gap may move a fault from (score/stages/gaps.py: a dated decision in data/checks/gaps/<place>.json)
# and the completion gate that fails it by name. Only these: any other gate's fault still stops its line.
GAP_GATES = {"assembly": ("placeholders", "resting"), "surfaces-check": ("stands level",),
             "surfaces-paint": ("colour against the close-up",)}


def with_gap_files(files):
    """A row's world files and its place's gaps file where it has one (gaps.files). It unwraps to the row's own files
    and keeps their attributes (the paint's carry), so the row's code version is its own."""
    def found(place):
        return {**(files(place) if callable(files) else files), **gaps.files(place)}
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
    if row.name in GAP_GATES:
        moving = GAP_GATES[row.name]
        return dataclasses.replace(row, files=with_gap_files(row.files),
                                   checks=tuple(gap_moved(row.name, check) if check.name in moving else check
                                                for check in row.checks))
    if row.name == "complete":
        return dataclasses.replace(row, files=with_gap_files(row.files),
                                   checks=(*row.checks, checks.Check("named gaps", gaps.judge_named)))
    return row


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


STAGES = tuple(named_gaps(layered(worn(row), {stage.name for stage in STAGES})) for row in STAGES)
ASSEMBLY = next(row for row in STAGES if row.name == "assembly")


def world1():
    """World 1: its record, its data in the repository, its old outputs in the work folder, the prop tools' home (the
    raw models, the routes' bake jobs) and the repository (the code a stage hands to a rented machine)."""
    return graph.World.from_file(WORLD1, data=str(REPO / "data"), seeds=str(PROPS_HOME / "work"),
                                 home=str(PROPS_HOME), repo=str(REPO))


def places(world):
    """A world's places: each with a kit or a plan in its data (a new place has its plan before its kit is laid;
    none for a world without data, the images world)."""
    if "data" not in world.roots:
        return []
    data = pathlib.Path(world.roots["data"])
    return sorted({path.stem for folder in ("kit", "plans") for path in (data / folder).glob("*.json")})


WORLDS = {"world1": world1, "images": images.image_world}
# A world whose stages are not world 1's: the images world (each job image rebuilt and proved, score/stages/images).
TABLES = {"images": images.STAGES}


def runner(store=None, world=None):
    """The runner over the stage table, on world 1 and the framework's store unless told otherwise."""
    world = world or world1()
    return graph.Runner(TABLES.get(world.name, STAGES), world, store or Store.default())
