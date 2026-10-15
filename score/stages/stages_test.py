"""The worked example on world 1's real round-three stages, with no spend: the hangar's seed fails on its code-built
ship, the hangar door's has no drop run and answers unknown, neither place can complete, a second run makes nothing,
and a change to the door's kit reruns the door's assembly alone. Skipped, and says so, on a machine without the seeds.

The store is a folder of its own under $PROPS_HOME (never /tmp, never the framework's own store), removed at the end.

Run: .venv/bin/python score/stages/stages_test.py
"""
import dataclasses
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
PLACES = ("hangar", "hdoor")
DATA = ("kit", "inventory", "library", "checks", "effects", "scene", "motion", "movers", "ground",
        "sound/surfaces.json", "sound/places.json", "characters", "surfaces", "definitions/place.json",
        "people/bodies.json")


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
    # The example's failing seed: without the owner's named gap for the hangar's ship (2026-10-14), its placeholders
    # fail the assembly's own gate.
    (root / "checks/gaps/hangar.json").write_text(json.dumps({"gaps": []}))
    return root


def scenario(root):
    world = graph.World("world1", 3, {"data": str(world_data_copy(root / "data")), "seeds": str(SEEDS),
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
# neither place here (their own checks are beside their modules): the machines layer too, since the hangar's machines
# record lays the ship from its bake (2026-10-15), a surface row this example does not run.
NO_SURFACES = tuple(graph.Stage(name, "place", no_ground, contracts.Contract(name, 1, lambda folder: []),
                                (checks.Check("made", made),), applies=lambda place: False)
                    for name in ("surfaces-paint", "surfaces-bake", "surfaces-check", "likeness", "surfaces-parts",
                                 "sound", "scene-record", "motion", "light", "crops-layer", "settle",
                                 "characters-layer", "machines-layer"))
NO_GROUND = graph.Stage("terrain", "world", no_ground,
                        contracts.Contract("grounds", 1, lambda folder: [], {"length": "metre", "up axis": "Y"}),
                        (checks.Check("made", made),))


def test_the_worked_example_on_world_1s_seeds():
    if not all((SEEDS / "usd-r3" / place / f"{place}.usda").exists() for place in PLACES):
        print("skipped: no round-three stages of the hangar and its door on this machine")
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
        assert first["assembly@hdoor"] == "made: unknown", first
        assert first["complete@hdoor"] == ("blocked: assembly@hdoor answered unknown: resting: no evidence: a drop "
                                           "run (settle.py --dry-run) for this output is missing"), first

        assert set(runner().run(PLACES).values()) == {"fresh", *(first[f"complete@{place}"] for place in PLACES)}

        kit = pathlib.Path(world.roots["data"]) / "kit/hdoor.json"
        kit.write_text(json.dumps({**json.loads(kit.read_text()), "note": "a creator's edit"}, indent=1))
        assert runner().status(PLACES)["assembly@hdoor"] == "to run: kit changed"
        third = runner().run(PLACES)
        assert third["assembly@hdoor"] == "made: unknown" and third["assembly@hangar"] == "fresh", third
        assert len(store.records("assembly@hdoor")) == 2 and len(store.records("assembly@hangar")) == 1

        page = review.page(store, "assembly@hangar").read_text()
        assert "Unverified seed." in page and "/hangar/Structure/ship" in page and "It cannot be accepted" in page
        why = runner().why("assembly@hangar")[0]
        assert why.startswith("assembly@hangar: output") and "fail, not accepted" in why and "seed " in why
    finally:
        shutil.rmtree(root)


def code_after_editing(stage, edited):
    """A stage's code version, as the runner works it out, as if the repository file `edited` had changed (its hash
    moved; nothing written)."""
    functions = [stage.make, stage.contract.faults, *(check.judge for check in stage.checks),
                 *([stage.files] if callable(stage.files) else []), *([stage.neighbours] if stage.neighbours else [])]
    return graph._code.code_version(functions, lambda path: file_hash(path) + ("+edit" if path == REPO / edited
                                                                               else ""))


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
    for own in ("score/stages/terrain/__init__.py", "score/stages/terrain/landforms.py", "tools/usd/ground.py",
                "tools/props/cloud/depth.py"):
        assert terrain_code_after_editing(own) != before, own


def test_the_paint_bake_and_check_code_moves_only_their_own_rows():
    """Editing the surface line's paint, bake and check code (place_line.py, bake_check.py, feet.py), the resting
    triage, the settle, the pick check or the completion gate leaves the paid rows that do not run them alone: the
    turntable, SegviGen, terrain and the effects rows (each re-bought on the water tank's fix, 2026-10-12, through the
    surfaces __init__ and complete.py); the paint, bake and check rows move."""
    table = {stage.name: stage for stage in stages.STAGES}
    edited = ("score/stages/surfaces/place_line.py", "score/stages/surfaces/bake_check.py",
              "tools/props/library/feet.py", "tools/usd/triage.py", "tools/usd/settle.py", "tools/usd/picks.py",
              "tools/usd/complete.py")
    for name in ("surfaces-turntable", "surfaces-segvigen", "surfaces-inputs", "surfaces-maps", "terrain",
                 "effects-layer", "effects-look"):
        before = code_after_editing(table[name], "nothing")
        for path in edited:
            assert code_after_editing(table[name], path) == before, (name, path)
    for name in ("surfaces-paint", "surfaces-bake"):
        assert code_after_editing(table[name], edited[0]) != code_after_editing(table[name], "nothing"), name
    assert code_after_editing(table["surfaces-check"], edited[1]) != code_after_editing(table["surfaces-check"],
                                                                                       "nothing")


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


def test_a_coloured_place_reads_its_own_dress_rows():
    """A place data/people/colours.json colours reads its looks' `-in-<place>` dress rows, every other place the
    plain ones (captain, 2026-10-13: the concept decides the clothes)."""
    table = {stage.name: stage for stage in stages.STAGES}
    coloured, plain = table["people-dress-bram-work-in-camp"], table["people-dress-bram-work"]
    assert coloured.applies("camp") and not coloured.applies("greenhouse") and coloured.params == {"surface": "olive_drab"}
    assert plain.applies("greenhouse") and not plain.applies("camp")
    assert "people-dress-bram-work-in-camp" in table["characters-layer"].after


def test_the_turntable_row_s_code_moves_only_the_turntable_and_segvigen():
    """Editing turntable_row.py (its PNGs written without text, 2026-10-12) moves the turntable row, and SegviGen's
    through row_files.py (both rows' world files), and no other paid row: the maps read its pictures, never its code."""
    table = {stage.name: stage for stage in stages.STAGES}
    edited = "score/stages/surfaces/turntable_row.py"
    moved = {name for name, stage in table.items() if stage.paid
             and code_after_editing(stage, edited) != code_after_editing(stage, "nothing")}
    # The people line's turntable runs the same make (score/stages/people/line.py), so it moves with it. The crops'
    # line keeps its rows' files functions in score/stages/crops/line.py, which imports the turntable, so every paid
    # row of it moves too (its overlay: they move to a module of their own the next time that line is made again),
    # but paint and bake, which key only the library surfaces they read (library_reads.py) since 2026-10-13.
    crops = {"crops-boxes", "crops-closeup", "crops-pixal", *(f"crops-surfaces-{step}" for step in (
        "turntable", "lists", "maps", "names", "segvigen"))}
    assert moved == {"surfaces-turntable", "surfaces-segvigen", "people-turntable", *crops}, moved


def test_a_place_with_a_plan_and_no_kit_yet_is_a_place():
    """A new place (the ship's bridge) has its plan before its kit is laid; the runner lists it with the laid ones."""
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    root = pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))
    try:
        for part in ("kit/laid.json", "plans/laid.json", "plans/new.json"):
            (root / part).parent.mkdir(parents=True, exist_ok=True)
            (root / part).write_text("{}")
        assert stages.places(graph.World("world1", 3, {"data": str(root)})) == ["laid", "new"]
    finally:
        shutil.rmtree(root)


def test_the_plan_row_keeps_its_code_version_and_a_laid_place_s_files():
    """The plan row reads a place with no kit through wrappers in the table, so no laid place's key moves."""
    plain = graph.Stage("plan", "place", stages.scene_record.plan.make, stages.scene_record.plan.PLACE_PLAN,
                        stages.scene_record.plan.CHECKS, files=stages.scene_record.plan.files)
    assert code_after_editing(stages.PLAN, "nothing") == code_after_editing(plain, "nothing")
    assert stages.PLAN.files("lab") == stages.scene_record.plan.files("lab")
    declared = stages.kit_if_laid(lambda place: {"plan": f"{place}.plan", "kit": f"{place}.kit"})
    assert declared("no_kit_laid") == {"plan": "no_kit_laid.plan"}


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
                  "plans": str(root / "plans"), "assets": str(REPO / "data/assets/world1.json")}
        stages.PLAN.make(inputs, root / "out", 0, {})
        assert json.loads((root / "out/plan.json").read_text())["place"] == "new_room"
        verdict = stages.PLAN.checks[0].judge(root / "out", inputs, {})
        assert verdict.answer == checks.PASS, verdict.reason
    finally:
        shutil.rmtree(root)


def openings_judged(plan, findings):
    """The table's openings gate on a stand-in measure with these findings, for a place whose plan is `plan`."""
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    root = pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))
    try:
        for part, record in (("plan/plan.json", {"place": "room"}), ("plans/room.json", plan)):
            (root / part).parent.mkdir(parents=True, exist_ok=True)
            (root / part).write_text(json.dumps(record))
        measured = checks.Verdict("openings", checks.FAIL, "measured", {"void rays": len(findings) - 1}, {},
                                  tuple(findings))
        judge = stages.ground_free(lambda output, inputs, evidence: measured)
        return judge(root, {"plan": str(root / "plan"), "plans": str(root / "plans")}, {})
    finally:
        shutil.rmtree(root)


def test_a_ground_free_interior_is_judged_against_its_own_walls_only():
    """A plan's `ground_free` (with why) lifts the missing ground alone; a view into nothing still fails, and a place
    whose plan does not say it keeps the gate's verdict as it was."""
    free = {"ground_free": "stands in the hangar's ship"}
    assert openings_judged(free, [stages.NO_GROUND]).answer == checks.PASS
    void = "3 of 90 view rays run out below the horizon into nothing"
    assert openings_judged(free, [void, stages.NO_GROUND]).findings == (void,)
    assert openings_judged(free, [void, stages.NO_GROUND]).answer == checks.FAIL
    assert openings_judged({}, [stages.NO_GROUND]).answer == checks.FAIL
    assert stages.NO_GROUND in inspect.getsource(stages.scene_record.gates.judge_openings)


def test_the_scene_record_row_keeps_its_code_version():
    plain = dataclasses.replace(stages.SCENE_RECORD, checks=stages.scene_record.gates.CHECKS)
    assert code_after_editing(stages.SCENE_RECORD, "nothing") == code_after_editing(plain, "nothing")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
