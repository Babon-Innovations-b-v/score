"""The worked example on world 1's real round-three stages, with no spend: the hangar's seed fails on its code-built
ship, so the place cannot complete, a second run makes nothing, and a change to its kit reruns its assembly. Skipped,
and says so, on a machine without the seeds.

The store is a folder of its own under $PROPS_HOME (never /tmp, never the framework's own store), removed at the end.

Run: .venv/bin/python score/stages/stages_test.py
"""
import dataclasses
import functools
import inspect
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
# The script's own folder (score/stages) off the path: on it, tools/usd's `import motion` also finds the motion
# stage, and the code versions measured here take in its imports (feet.py, triage.py) as `python -m score` never does.
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(REPO))

from score import checks, contracts, graph, review, stages  # noqa: E402
from score.store import PROPS_HOME, Store, file_hash  # noqa: E402

SEEDS = PROPS_HOME / "work"
PLACES = ("hangar",)
DATA = ("kit", "inventory", "library", "checks", "scene", "ground",
        "sound/surfaces.json", "characters", "surfaces", "definitions/place.json",
        "people/rows.json")


def world_data_copy(root):
    """The world files the assembly and effects stages read, copied so the test may change one."""
    for part in DATA:
        source, target = REPO / "data" / part, root / part
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if source.is_dir() else shutil.copy2)(source, target)
    # No claiming place here (ASSEMBLY below): the hangar's surface data names no model another place's line paints,
    # else the assembly reads the hangar's own surfaces-bake, a row this example does not run.
    surfaces = root / "surfaces/hangar.json"
    surfaces.write_text(json.dumps({**json.loads(surfaces.read_text()), "elsewhere": {}}, indent=1))
    # The example's failing seed: without the owner's accepted gap for the hangar's ship (2026-10-14), its placeholders
    # fail the assembly's own gate.
    (root / "checks/gaps/hangar.json").write_text(json.dumps({"gaps": []}))
    return root


def scenario(root):
    world = graph.Environment("world1", 3, {"data": str(world_data_copy(root / "data")), "seeds": str(SEEDS),
                                      "repo": str(REPO)})
    store = Store.in_folder(root / "store")
    # The worked example's own stages: terrain (a world node) spends and has its own test beside its module, so a
    # terrain that made no ground for these places stands in for it.
    return world, store, lambda: graph.Runner((NO_GROUND, stages.EFFECTS, *NO_SURFACES, ASSEMBLY,
                                               stages.NEIGHBOURS,
                                               stages.COMPLETE), world, store)



# The assembly with no claiming place: the hangar's rack is old_station's (data/surfaces/hangar.json `elsewhere`), whose
# line this example does not run.
ASSEMBLY = dataclasses.replace(stages.ASSEMBLY, neighbours=lambda place: [])

def no_ground(inputs, out, seed, params):
    (out / "none").mkdir()


def made(output, inputs, evidence):
    return checks.Verdict("made", checks.PASS, "no ground made for these places")


# The surface rows and the layer rows the assembly and complete read, and the likeness complete reads, applying to
# neither place here (their own checks are beside their modules): the motion models layer too, since the hangar's models
# record lays the ship from its bake (2026-10-15), a surface row this example does not run.
NO_SURFACES = tuple(graph.Stage(name, "place", no_ground, contracts.Contract(name, 1, lambda folder: []),
                                (checks.Check("made", made),), applies=lambda place: False)
                    for name in ("surfaces-paint", "surfaces-bake", "surfaces-check", "likeness", "surfaces-parts",
                                 "sound", "scene-record", "motion", "light", "crops-layer", "settle",
                                 "characters-layer", "surface-tiles"))
NO_GROUND = graph.Stage("terrain", "world", no_ground,
                        contracts.Contract("grounds", 2, lambda folder: [], {"length": "metre", "up axis": "Y"}),
                        (checks.Check("made", made),))


def test_the_worked_example_on_world_1s_seeds():
    if not all((SEEDS / "usd-r3" / place / f"{place}.usda").exists() for place in PLACES):
        print("skipped: no round-three stage of the hangar on this machine")
        return
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    root = pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))
    try:
        world, store, runner = scenario(root)
        first = runner().run(PLACES)
        assert first["assembly@hangar"] == "made: fail", first
        assert first["complete@hangar"].startswith("blocked: assembly@hangar answered fail: layers: waits on "
                                                   "sound@hangar, light@hangar, motion@hangar, characters-layer@hangar "
                                                   "(no accepted output "
                                                   "taken); took effects-layer; placeholders: 12 meshes stand in for "
                                                   "made pieces; resting: no evidence"), first

        assert set(runner().run(PLACES).values()) == {"fresh", *(first[f"complete@{place}"] for place in PLACES)}

        kit = pathlib.Path(world.roots["data"]) / "kit/hangar.json"
        kit.write_text(json.dumps({**json.loads(kit.read_text()), "note": "a creator's edit"}, indent=1))
        assert runner().status(PLACES)["assembly@hangar"] == "to run: kit changed"
        third = runner().run(PLACES)
        assert third["assembly@hangar"] == "made: fail", third
        assert len(store.records("assembly@hangar")) == 2

        page = review.page(store, "assembly@hangar").read_text()
        assert "Unverified seed." in page and "/hangar/Structure/ship" in page and "It cannot be accepted" in page
        why = runner().why("assembly@hangar")[0]
        assert why.startswith("assembly@hangar: output") and "fail, not accepted" in why and "seed " in why
    finally:
        shutil.rmtree(root)


@functools.cache
def code_hashed(functions):
    """The runner's code version of these functions and {file: its hash} of each file it hashed, worked out once a
    process: the import walk parses every module behind a row, and the tests below ask it hundreds of times."""
    hashed = {}
    version = graph._code.code_version(list(functions), lambda path: hashed.setdefault(path, file_hash(path)))
    return version, hashed


def code_after_editing(stage, edited):
    """A stage's code version, as the runner works it out, as if the repository file `edited` had changed (its hash
    moved; nothing written)."""
    functions = (stage.make, stage.contract.faults, *(check.judge for check in stage.checks),
                 *([stage.files] if callable(stage.files) else []), *([stage.neighbours] if stage.neighbours else []))
    version, hashed = code_hashed(functions)
    path = REPO / edited
    return [part + "+edit" if path in hashed and part == f"{edited} {hashed[path]}" else part for part in version]


def terrain_code_after_editing(edited):
    """Terrain's code version as if the repository file `edited` had changed."""
    return code_after_editing(stages.TERRAIN, edited)


def test_terrain_s_code_version_moves_with_its_own_code_only():
    """Another line's edits to the runner, the stage table or another stage's module leave terrain's key alone (they
    re-made terrain under the effects line, 2026-10-12); its own module and what it imports move it."""
    before = terrain_code_after_editing("nothing")
    for unrelated in ("score/stages/__init__.py", "score/graph/__init__.py", "score/review/__init__.py",
                      "score/adapters/compute/__init__.py", "score/stages/effects/__init__.py",
                      "score/stages/assembly/__init__.py", "score/stages/surfaces/__init__.py"):
        assert terrain_code_after_editing(unrelated) == before, unrelated
    for own in ("score/stages/terrain/__init__.py", "score/stages/terrain/design.py", "score/stages/terrain/outside.py"):
        assert terrain_code_after_editing(own) != before, own


def test_the_earth_rows_key_on_the_surface_data_reader_not_the_surface_line():
    """earth-seed reads a place's surface data through surface_data.py alone: an edit to the surface
    line's rows leaves its key, an edit to the reader moves it (its package's __init__ pulled the whole line in,
    2026-10-21)."""
    table = {stage.name: stage for stage in stages.STAGES}
    for name in ("earth-seed",):
        before = code_after_editing(table[name], "nothing")
        for unrelated in ("score/stages/surfaces/__init__.py", "score/stages/surfaces/place_line.py"):
            assert code_after_editing(table[name], unrelated) == before, (name, unrelated)
        assert code_after_editing(table[name], "score/stages/surfaces/surface_data.py") != before, name


def test_the_paint_bake_and_check_code_moves_only_their_own_rows():
    """Editing the surface line's paint, bake and check code (place_line.py, bake_check.py, feet.py), the resting
    triage, the settle, the pick check or the completion gate leaves the paid rows that do not run them alone: the
    finish route's views, list, split and recheck and terrain (each re-bought on the water
    tank's fix, 2026-10-12, through the surfaces __init__ and complete.py); the paint, bake and check rows move. The
    free effects layer is made over the scene record as the assembly writes it (layer_base.py, 2026-10-21: its
    effects ride the design's objects), so like the motion and light rows it reads the exporter's code."""
    table = {stage.name: stage for stage in stages.STAGES}
    edited = ("score/stages/surfaces/place_line.py", "score/stages/surfaces/bake_check.py",
              "tools/props/library/feet.py", "tools/usd/triage.py", "tools/usd/settle.py", "tools/usd/picks.py",
              "tools/usd/complete.py")
    for name in ("finish-route-views", "finish-route-list", "finish-route-split", "finish-route-recheck",
                 "terrain"):
        before = code_after_editing(table[name], "nothing")
        for path in edited:
            assert code_after_editing(table[name], path) == before, (name, path)
    for name in ("surfaces-paint", "surfaces-bake"):
        assert code_after_editing(table[name], edited[0]) != code_after_editing(table[name], "nothing"), name
    assert code_after_editing(table["surfaces-check"], edited[1]) != code_after_editing(table["surfaces-check"],
                                                                                       "nothing")


def test_run_machinery_moves_no_row_and_a_maker_moves_its_own():
    """Code that only decides where and how a job runs (the warm pool, spreading, the provider and its backend, the
    ledgers, forecasts, money guards, the cockpit) moves no row's code version (a body made again for EUR 0.30 by
    warm-pool edits, owner 2026-10-23); a maker's own code and a runner module that sends its scripts up still do."""
    machinery = ("tools/cloud/pool.py", "tools/cloud/spread.py", "tools/cloud/provider.py",
                 "tools/cloud/backends/scaleway.py", "tools/cloud/ledger.py",
                 "tools/cloud/google_spend.py", "tools/cloud/preflight.py",
                 "tools/cloud/secret_store.py", "score/adapters/compute/guard.py", "score/dashboard/__init__.py")
    moved = {(stage.name, path) for stage in stages.STAGES for path in machinery
             if code_after_editing(stage, path) != code_after_editing(stage, "nothing")}
    assert not moved, sorted(moved)
    bodies = [stage for stage in stages.STAGES if stage.name.startswith("people-body-")]
    assert bodies
    for maker in ("score/stages/people_bodies/bodies.py", "tools/cloud/similar.py"):
        assert all(code_after_editing(stage, maker) != code_after_editing(stage, "nothing") for stage in bodies), maker


def test_the_completion_gate_s_code_moves_only_complete_and_settle():
    """Editing the completion gate (complete.py, its contents checks, reach and snap, the complete stage) moves the
    complete row and no other: the assembly, neighbours and likeness read the inputs record's helpers from
    stage_inputs.py, not complete.py (each re-made by a gate edit before 2026-10-12). The settle row snaps held
    objects with snap.py (score/stages/settling/held.py), so a snap edit moves it too, and only it."""
    edited = ("tools/usd/complete.py", "tools/usd/contents.py", "tools/usd/reach.py", "tools/usd/snap.py",
              "score/stages/complete/__init__.py")
    moved = {stage.name for stage in stages.STAGES for path in edited
             if code_after_editing(stage, path) != code_after_editing(stage, "nothing")}
    assert moved == {"complete", "settle"}, moved


def test_the_light_layer_reads_and_waits_on_every_body_face_row():
    """light-layer@hub, 2026-10-23: read as optional, the face rows were in no place's line and the layer failed its
    sky-elements gate with no face drawn."""
    layer = next(row for row in stages.STAGES if row.name == "light-layer")
    faces = {row.name for row in stages.BODY_FACES}
    assert faces and faces <= set(layer.after) and not faces & set(layer.optional)


def test_no_base_or_layer_row_must_wait_on_the_prop_route():
    """Buy of 2026-10-24: one crashed close-up stopped the square's earth seed, scene record, light and tiles, since
    the scene palette, which the surface library and so the base read, waited on Pixal3D. Through every read that is
    not optional, neither the earth seed nor the scene record reaches the prop route's rows."""
    table = {stage.name: stage for stage in stages.STAGES}
    prop_route = {"closeup", "pixal"}

    def reached(name, seen):
        for before in table[name].after:
            if before not in table[name].optional and before not in seen:
                seen.add(before)
                reached(before, seen)
        return seen
    for start in ("earth-seed", "scene-record", "light-layer"):
        assert not reached(start, set()) & prop_route, (start, reached(start, set()) & prop_route)
    assert "pixal" in table["finish-route-palette"].optional


def test_a_dress_row_is_read_where_a_design_dresses_its_look_so():
    """A dress row is read where a place's design dresses its look so: `-in-<surface>` where a person row's words
    name a fabric near its torso (people_clothes.py), the plain row where the look wears its own paint; no
    hand-kept list of coloured places (captain, 2026-10-13: the concept decides the clothes)."""
    table = {stage.name: stage for stage in stages.STAGES}
    plain = table["people-dress-person_uniform-made"]
    assert plain.applies("tube") and not plain.applies("square")  # the tube's "person in uniform" names no fabric
    worn =[stage for stage in stages.STAGES if stage.name.startswith("people-dress-") and "-in-" in stage.name]
    for stage in worn:
        assert stage.params == {"surface": stage.name.partition("-in-")[2]} and stage.name in table["cast"].after


def test_a_worn_dress_row_applies_only_where_its_look_wears_that_fabric():
    """Today's designs dress no line look in a fabric of its own, so the table above holds no `-in-` row: the row a
    design would add applies where a person row wears its look in that fabric, and the plain row no longer there."""
    from unittest import mock

    from score.stages import people
    worn_row, plain_row = (stages.worn(people.dress_row("person_uniform-made", surface))
                           for surface in ("jacket_blue", None))
    dressed = {"deck": {("person_uniform-made", "jacket_blue")}, "hold": {("person_uniform-made", None)}}
    with mock.patch.object(stages.characters_layer, "dressed_looks", lambda place: dressed.get(place, set())):
        assert worn_row.applies("deck") and not worn_row.applies("hold") and not worn_row.applies("nowhere")
        assert plain_row.applies("hold") and not plain_row.applies("deck")
    assert worn_row.params == {"surface": "jacket_blue"}


def test_a_parent_scene_s_tree_reads_the_trees_of_its_child_scenes_of_the_batch():
    """scene-tree@<scene> reads its own assembly and, beside, the tree of each child scene its plan lays out that is a
    scene of the batch (one in design is none: the tree's gate names it); a place of every scene but a line no place
    owns; the library reads it, so a scene is complete once its tree stands."""
    table = {stage.name: stage for stage in stages.STAGES}
    row = table["scene-tree"]
    assert row.downward and row.after == {"assembly": ("openusd-stage", 1)}
    assert row.beside == {"scene-tree": ("openusd-stage", 1)} and row.neighbours is stages.held_scenes
    assert not row.applies("people") and row.applies("hangar") and "scene-tree" in table["library"].after
    held, listed = stages.scene_tree.held, stages.places
    try:
        stages.scene_tree.held = lambda place: {"base": ["hangar", "lab", "dome"]}.get(place, [])
        stages.places = lambda world, store=None: ["base", "hangar", "lab"]
        assert stages.held_scenes("base") == ["hangar", "lab"] and stages.held_scenes("lab") == []
    finally:
        stages.scene_tree.held, stages.places = held, listed
    assert stages.parent_first({"cockpit", "hangar", "base", "hub", "wreck", "camp"},
                               {"cockpit": "hangar", "hangar": "base", "hub": "base", "camp": "campgrounds"}) == [
        "base", "hangar", "cockpit", "hub", "camp", "wreck"]


def designed(store, place):
    """`place`'s design done in `store`: a concept locked, its scene inventory read from it and its plan written from
    that reading (plans.design_done)."""
    from score.review import concepts, plan_writing, reading
    sha = place.ljust(64, "0")
    concepts.recorded(store, f"concepts/{place}/picks/2026-10-20T09-00-00.json",
                      {"place": place, "sha": sha, "by": "joey", "at": "2026-10-20T09:00:00+00:00"})
    reading.kept(store, {"place": place, "concept": sha, "at": "2026-10-20T09:10:00+00:00", "method": reading.METHOD,
                         "inventory": {"rows": [{"id": "desk", "name": "desk", "count": 1}]}})
    plan_writing.kept(store, {"place": place, "concept": sha, "reading": "2026-10-20T09:10:00+00:00",
                              "method": plan_writing.METHOD, "at": "2026-10-20T09:30:00+00:00", "by": "test", "euros": 0.0,
                              "plan": {"title": place.upper(), "w": 3.0, "d": 3.0, "items": [], "doors": []}})


def test_a_place_is_a_scene_whose_design_is_done():
    """No kit or plan filed in the data names a place since 2026-10-21: a place is a scene of the design whose concept
    is locked, its inventory read and its plan written; one only drawn is still in design."""
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    root = pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))
    try:
        store = Store.in_folder(root / "store")
        for part in ("kit/old.json", "plans/old.json"):  # an old filed kit and plan: no place
            (root / part).parent.mkdir(parents=True, exist_ok=True)
            (root / part).write_text("{}")
        designed(store, "laid")
        designed(store, "new")
        from score.review import concepts
        concepts.recorded(store, "concepts/drawn/draws/2026-10-20T08-00-00.json",
                          {"place": "drawn", "sha": "d" * 64, "by": "joey", "at": "2026-10-20T08:00:00+00:00"})
        world = graph.Environment("world1", 3, {"data": str(root)})
        assert stages.places(world, store) == ["laid", "new"]
        # a scene merged into another has no stage line, though its design is done
        (root / "places").mkdir()
        (root / "places/within.json").write_text(json.dumps({"merged": {"new": {"into": "laid"}}}))
        assert stages.places(world, store) == ["laid"]
        # nor has a part of another scene's outside: the scene it is part of builds it (the owner, 2026-10-21)
        (root / "places/within.json").write_text(json.dumps({"parts": {"new": {"of": "laid", "as": "far off"}}}))
        assert stages.places(world, store) == ["laid"]
    finally:
        shutil.rmtree(root)


def test_the_plan_row_keeps_the_plan_stages_code_version():
    """The plan row is the scene record's plan step as it stands (its code version kept), reading no kit: its files
    are the step's own."""
    plain = graph.Stage("plan", "place", stages.scene_record.plan.make, stages.scene_record.plan.PLACE_PLAN,
                        stages.scene_record.plan.CHECKS, files=stages.scene_record.plan.files)
    assert code_after_editing(stages.PLAN, "nothing") == code_after_editing(plain, "nothing")
    assert stages.earth_seed.locked_plan("launch") is None
    assert stages.PLAN.files("launch") == stages.scene_record.plan.files("launch")
    assert "kit" not in stages.PLAN.files("launch")


def test_the_plan_row_maps_a_place_with_no_kit():
    """With no kit laid, the plan row's make names the place by its plan and its `mapped` gate judges it."""
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    root = pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))
    try:
        (root / "plans").mkdir()
        (root / "out").mkdir()
        plan = {"title": "NEW ROOM", "w": 3.0, "d": 3.0, "corner": 0.0, "height": "walls 2.5 m", "doors": [],
                "items": [["DESK", 1.0, 1.0, 1.0, 0.6, "S", "item"]], "rows": {"DESK": ["desk"]}, "leads": {},
                "elements": [{"element": "a desk", "rows": ["desk"]}, {"element": "a poster", "drop": "printed"}]}
        (root / "plans/new_room.json").write_text(json.dumps(plan))
        (root / "inventory.json").write_text(json.dumps({"rows": [{"id": "desk"}], "room": {"layout": {}}}))
        inputs = {"plan": str(root / "plans/new_room.json"), "inventory": str(root / "inventory.json"),
                  "plans": str(root / "plans")}
        stages.PLAN.make(inputs, root / "out", 0, {})
        assert json.loads((root / "out/plan.json").read_text())["place"] == "new_room"
        verdict = stages.PLAN.checks[0].judge(root / "out", inputs, {})
        assert verdict.answer == checks.PASS, verdict.reason
    finally:
        shutil.rmtree(root)


def inputs_read(function):
    """The constant keys a function reads as inputs["<key>"]."""
    import ast
    tree = ast.parse(inspect.getsource(function))
    return {node.slice.value for node in ast.walk(tree) if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name) and node.value.id == "inputs" and isinstance(node.slice, ast.Constant)}


def test_the_check_reads_every_input_check_step_reads():
    """surfaces-check hands check_step every key it reads (the crops' twin's stance rules were missing, 2026-10-16:
    KeyError at greenhouse), shortened as the prop environment hands them over (prop_env.short)."""
    bake_check, prop_env = sys.modules["bake_check"], sys.modules["prop_env"]
    read = inputs_read(bake_check.check_step) | inputs_read(bake_check.data_of)
    row = next(row for row in stages.STAGES if row.name == "surfaces-check")
    handed = prop_env.short({**row.files("greenhouse"), **dict.fromkeys(row.after, ".")})
    assert read <= set(handed), read - set(handed)


def test_a_ship_place_is_read_from_git():
    """On a home with no work folder: the cockpit is a ship place by its place.json mark and the hub is not."""
    assert not (SEEDS / "usd-ship" / "cockpit").exists()
    assert stages.ship_place("cockpit") and not stages.ship_place("hub")


def test_the_cast_crowds_from_its_plan_never_a_hand_written_record():
    """Every place's cast, the ship's and the earth's alike, takes its views from its plan row (an `after`) and
    declares no old scene record (data/scene/<place>.json, the game's shots), no kit and no views file under work/."""
    row = next(row for row in stages.STAGES if row.name == "cast")
    assert row.after["plan"] == ("place-plan", 2)
    for place in ("cockpit", "square", "hub"):
        declared = row.files(place)
        paths = [pattern[0] if isinstance(pattern, tuple) else pattern for pattern in declared.values()]
        assert not any(path.startswith(("{data}/scene", "{data}/kit")) or "world1-r4" in path for path in paths), \
            (place, declared)


# The environment data's paths into the work folder still standing, per file, and why: the work folder is no store
# (it went with the old disk on 2026-10-19). Shrinks to empty as the Pixal3D takes move into their row's output
# (the inputs track's item 6); a new one fails below.
WORK_PATHS_LEFT = {}  # the old hand-ins and inventories that named them were retired, 2026-10-21


def test_the_environment_data_names_no_new_path_into_the_work_folder():
    import subprocess
    found = subprocess.run(["git", "grep", "-c", "-E", r"\{home\}/work/|score-coordinator", "--", "data"], cwd=REPO,
                           capture_output=True, text=True).stdout.split()
    counts = {line.rsplit(":", 1)[0]: int(line.rsplit(":", 1)[1]) for line in found}
    grown = {path: count for path, count in counts.items() if count > WORK_PATHS_LEFT.get(path, 0)}
    assert not grown, f"new paths into the work folder (make them a row's output, or a gap): {grown}"
    shrunk = {path: counts.get(path, 0) for path, count in WORK_PATHS_LEFT.items() if counts.get(path, 0) < count}
    assert not shrunk, f"fewer paths into the work folder than WORK_PATHS_LEFT allows: lower it to {shrunk}"


def test_the_motion_layer_names_only_rows_of_the_table_and_no_old_layer():
    import fnmatch
    names = [row.name for row in stages.STAGES]
    empty = [pattern for patterns in stages.MOTION_LAYER.values() for pattern in patterns
             if not fnmatch.filter(names, pattern)]
    assert not empty, f"motion layer patterns that name no row of the table: {empty}"
    old = [name for name in names if name.startswith("machines")]
    assert not old, f"rows under the old machines name (the motion layer's models now): {old}"


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
