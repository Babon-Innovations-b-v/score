"""Checks for the prop batch's real makers (prop_makers.py) with stand-in runners: Pixal3D goes up as one batch.py
batch of the new takes (a take already made is not asked again), the bake as one library_bake.py batch of make_chunky
jobs, each step's ledger batch is recorded, a batch that made nothing raises, a prop that names no parts stops before
anything is paid, and `run` is refused without --yes after printing its price. No cloud, no network.

Run: python3 tools/props/cloud/prop_makers_test.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import types

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import prop_makers  # noqa: E402
import place_line  # noqa: E402  (put on the path by prop_makers)

BAKE_ENTRY = prop_makers.bake_entry  # in_sandbox stands it in; the real one, kept for its own check

ENTRY = {"name": "ship_1", "faces": 19000, "base": [1, 0, 0, 0, 1, 0, 0, 0, 1], "size": [9.02, 5.43, 31.0]}
PROPS = [{"name": "ship-s1", "place": "hangar", "row": "ship", "take": "ship-b1", "seed": 1,
          "picture": "/pics/ship.png", "parts": "/parts/ship", "keep": ["closeup"]},
         {"name": "crane-r1", "place": "campgrounds", "row": "crane", "take": "crane-b1", "seed": 1,
          "picture": "/pics/crane.png", "parts": "/parts/crane", "keep": ["closeup"]}]


class StandIn:
    """A stand-in for subprocess.run: records each command, writes the outputs `make` names and a ledger line."""

    def __init__(self, ledger, kind, make, code=0):
        self.ledger, self.kind, self.make, self.code, self.commands = ledger, kind, make, code, []

    def __call__(self, command, **_):
        self.commands.append(command)
        for path in self.make(command):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("made")
        with self.ledger.open("a") as ledger:
            ledger.write(json.dumps({"kind": self.kind, "batch": f"{self.kind}-{len(self.commands)}"}) + "\n")
        return types.SimpleNamespace(returncode=self.code, stdout="", stderr="")


def in_sandbox(folder):
    """prop_makers pointed at a sandbox work folder and ledger, its surface data a stand-in entry."""
    prop_makers.WORK = folder / "work"
    prop_makers.LEDGER = folder / "ledger.jsonl"
    prop_makers.bake_entry = lambda prop: ({"specs": {}}, dict(ENTRY, parts=prop["parts"]))


def made_takes(command):
    """The take files batch.py brings back for every line of its list."""
    listing = pathlib.Path(command[2]).read_text().split("\n")
    return [prop_makers.WORK / "pixal" / f"{line.split()[0]}{suffix}" for line in listing if line
            for suffix in prop_makers.TAKE_FILES]


def test_models_go_up_as_one_batch_and_a_made_take_is_not_asked():
    with tempfile.TemporaryDirectory() as temp:
        folder = pathlib.Path(temp)
        in_sandbox(folder)
        for suffix in prop_makers.TAKE_FILES:
            (folder / "work/pixal").mkdir(parents=True, exist_ok=True)
            (folder / "work/pixal" / f"crane-b1{suffix}").write_text("made before")
        call = StandIn(folder / "ledger.jsonl", "pixal", made_takes)
        made = prop_makers.make_models(PROPS, folder / "out", "test", call)
        assert len(call.commands) == 1, call.commands
        command = call.commands[0]
        assert command[1].endswith("batch.py") and command[command.index("--inventory") + 1].endswith("hangar.json")
        listing = pathlib.Path(command[2]).read_text()
        assert listing == "ship-b1 /pics/ship.png --faces 19000 --seed 1\n", listing
        assert made == {"ship-s1": {"batch": "pixal-1", "take": "ship-b1"},
                        "crane-r1": {"batch": None, "take": "crane-b1"}}, made


def test_bake_is_one_batch_of_make_chunky_jobs():
    with tempfile.TemporaryDirectory() as temp:
        folder = pathlib.Path(temp)
        in_sandbox(folder)
        surfaces = folder / "surfaces.json"
        surfaces.write_text(json.dumps({"library": "hangar"}))
        prop_makers.bake_inputs = lambda place: {"surfaces": surfaces}
        place_line.baking_specs = lambda library, specs, folders: {"steel": {"recipe": "steel"}}
        out = folder / "out"

        def baked(command):
            return [pathlib.Path(json.loads(pathlib.Path(job).read_text())["out"]) /
                    f"{json.loads(pathlib.Path(job).read_text())['chunky'][0]['name']}.gltf"
                    for job in command[2:command.index("--who")]]

        call = StandIn(folder / "ledger.jsonl", "library", baked)
        made = prop_makers.make_bakes(PROPS, out, "test", call)
        command = call.commands[0]
        assert len(call.commands) == 1 and command[1].endswith("library_bake.py")
        assert command[command.index("--classes") + 1] == place_line.CLASSES
        job = json.loads(pathlib.Path(command[2]).read_text())
        assert job["chunky"] == [dict(ENTRY, parts="/parts/ship")] and job["out"] == str(out / "made"), job
        assert job["specs"] == {"steel": {"recipe": "steel"}}
        assert made["crane-r1"] == {"batch": "library-1", "model": str(out / "made/ship_1.gltf")}, made


def test_a_batch_that_made_nothing_raises():
    with tempfile.TemporaryDirectory() as temp:
        folder = pathlib.Path(temp)
        in_sandbox(folder)
        call = StandIn(folder / "ledger.jsonl", "pixal", lambda command: [], code=1)
        try:
            prop_makers.make_models(PROPS, folder / "out", "test", call)
        except RuntimeError as fault:
            assert "made nothing" in str(fault), fault
        else:
            raise AssertionError("a failed batch that made nothing passed")


def test_a_prop_with_no_parts_stops_before_anything_is_paid():
    ok, why = prop_makers.parts_named(dict(PROPS[0], parts=None))
    assert not ok and "names no parts" in why, why
    assert prop_makers.parts_named(PROPS[0]) == (True, "")
    assert prop_makers.parts_named(dict(PROPS[0], parts=None, keep=["bake"])) == (True, "")
    assert prop_makers.parts_named(dict(PROPS[0], parts=None, body="main_console-s1")) == (True, "")
    ok, why = prop_makers.parts_named(dict(PROPS[0], parts=None, body="ship-s1"))
    assert not ok and "no builder" in why, why


def test_a_bodied_prop_s_parts_are_written_before_its_bake_and_a_refusal_stops_it():
    with tempfile.TemporaryDirectory() as temp:
        folder = pathlib.Path(temp)
        in_sandbox(folder)
        bodied = dict(PROPS[0], parts=None, body="ship-s1")
        assert prop_makers.parts_folder(bodied) == folder / "work/body-parts" / bodied["take"]
        written = []
        prop_makers.write_body_parts = lambda prop: (written.append(prop["name"]) or False, "lies 0.3 off")
        assert prop_makers.check_parts(bodied) == (False, "lies 0.3 off") and written == [bodied["name"]]


def test_a_bodied_prop_s_bake_entry_is_refused_by_name_while_the_repo_library_is_retired():
    """The old route's bake entry reads the repo library's per-place wear and kind details, both retired with every old
    material and model (2026-10-21): it is refused by name before anything is rented, never sized on old data."""
    import trimesh
    with tempfile.TemporaryDirectory() as temp:
        folder = pathlib.Path(temp)
        kept = prop_makers.WORK, prop_makers.bake_inputs, prop_makers.accepted_labelled
        try:
            prop_makers.WORK = folder / "work"
            labelled = folder / "labelled/aft_section-t1"
            labelled.mkdir(parents=True)
            trimesh.creation.box(extents=(2.0, 1.0, 1.0)).export(labelled / "hull_white.ply")
            records = {"surfaces": {"place": "wreck", "library": "wreck",
                                    "bake": {"models": {"aft_section": "aft_section-t1"}}}}
            for name, record in records.items():
                (folder / f"{name}.json").write_text(json.dumps(record))
            prop_makers.bake_inputs = lambda place: {name: folder / f"{name}.json" for name in records}
            prop_makers.accepted_labelled = lambda prop: labelled
            bodied = {"name": "aft_section-t1", "place": "wreck", "take": "aft_section-b2", "body": "aft_section-t1"}
            import library
            try:
                BAKE_ENTRY(bodied)
            except library.LibraryEmpty as refused:
                assert "wreck: no wear" in str(refused), refused
            else:
                raise AssertionError("a bake entry was written from the retired library")
        finally:
            prop_makers.WORK, prop_makers.bake_inputs, prop_makers.accepted_labelled = kept


def test_a_close_up_is_drawn_once_and_one_that_fails_is_a_gap():
    """A batch runs every job once (CONTEXT.md, owner 2026-10-20): Pro drew a second, room take of what the crop alone
    failed. Now each prop gets one take, its wording chosen free before it is drawn."""
    from PIL import Image
    import stage
    drawn = []
    with tempfile.TemporaryDirectory() as temp:
        concept = pathlib.Path(temp) / "concept.png"
        Image.new("RGB", (800, 600), (120, 120, 120)).save(concept)

        def row(prop):
            return {"id": prop["row"], "scene": prop["place"], "words": prop["row"], "size": [1.0, 1.0, 1.0],
                    "concept": str(concept), "box": [100, 100, 200, 150]}

        def draw(key, asks):
            for path, (_, _, reference) in asks.items():
                drawn.append((path.name, reference is not None))
                Image.new("RGB", (64, 64), (200, 200, 200)).save(path)  # a plain picture: the shape check fails it
            return dict.fromkeys(asks, True)
        kept = prop_makers.closeup_row, stage.pro.draw, sys.modules.get("secret_store")
        prop_makers.closeup_row, stage.pro.draw = row, draw
        sys.modules["secret_store"] = types.SimpleNamespace(secret=lambda name: "key")
        try:
            made = prop_makers.make_closeups(PROPS, temp)
        finally:
            prop_makers.closeup_row, stage.pro.draw = kept[:2]
            if kept[2] is None:
                del sys.modules["secret_store"]
            else:
                sys.modules["secret_store"] = kept[2]
    assert sorted(drawn) == [("crane.png", True), ("ship.png", True)], drawn  # small crops take the room, once each
    assert made == {}  # both failed their shape check: gaps, not drawn again


def test_run_is_refused_without_yes_after_its_price():
    with tempfile.TemporaryDirectory() as temp:
        props = pathlib.Path(temp) / "trial.json"
        props.write_text(json.dumps(PROPS))
        done = subprocess.run([sys.executable, str(HERE / "prop_batch.py"), "run", str(props), "--folder",
                               str(pathlib.Path(temp) / "batch")], capture_output=True, text=True)
        assert done.returncode == 1, done
        assert done.stdout.startswith("2 of 2 props to make, EUR "), done.stdout
        assert "nothing is paid without --yes" in done.stderr, done.stderr
        assert not (pathlib.Path(temp) / "batch").exists()


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    checks = [function for name, function in list(globals().items()) if name.startswith("test_")]
    for function in checks:
        function()
    print(f"prop_makers: {len(checks)} checks passed")
