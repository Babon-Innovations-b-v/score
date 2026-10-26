"""prop_makers.py's invariants, with stand-in runners (no cloud, no network): each paid step goes up as one batch,
never one per prop: Pixal3D as one batch.py batch of the takes not yet made (a made take is not asked again), the bake
as one library_bake.py batch of make_chunky jobs whose parts are the prop's own; each made prop records the ledger
batch that made it; a batch that made nothing raises; a prop that names no parts (and has no builder for its body)
stops before anything is paid, a bodied prop's parts written first and a refusal stopping it; a bodied prop's bake
entry is refused by name while the repo library is retired (2026-10-21); a close-up is drawn once, one that fails its
shape check is a gap, never drawn again (owner, 2026-10-20).

Break that turns it red: in `make_models` list every prop's take (drop the made-take filter); in `parts_named` return
(True, "") for a prop with no parts; or in `make_closeups` keep a picture without its shape check (a failed close-up
then counts as made).
"""
import json
import pathlib
import sys
import types

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import prop_makers  # noqa: E402
import place_line  # noqa: E402  (put on the path by prop_makers)

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


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """prop_makers pointed at a sandbox work folder and ledger, its surface data a stand-in entry."""
    real_bake_entry = prop_makers.bake_entry
    monkeypatch.setattr(prop_makers, "WORK", tmp_path / "work")
    monkeypatch.setattr(prop_makers, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(prop_makers, "bake_entry", lambda prop: ({"specs": {}}, dict(ENTRY, name=prop["take"], parts=prop["parts"])))
    return tmp_path, real_bake_entry


def made_takes(command):
    """The take files batch.py brings back for every line of its list."""
    listing = pathlib.Path(command[2]).read_text().split("\n")
    return [prop_makers.WORK / "pixal" / f"{line.split()[0]}{suffix}" for line in listing if line
            for suffix in prop_makers.TAKE_FILES]


def test_models_go_up_as_one_batch_and_a_made_take_is_not_asked(sandbox):
    folder, _ = sandbox
    (folder / "work/pixal").mkdir(parents=True)
    for suffix in prop_makers.TAKE_FILES:
        (folder / "work/pixal" / f"crane-b1{suffix}").write_text("made before")
    call = StandIn(folder / "ledger.jsonl", "pixal", made_takes)
    made = prop_makers.make_models(PROPS, folder / "out", "test", call)
    [command] = call.commands
    assert command[1].endswith("batch.py") and command[command.index("--inventory") + 1].endswith("hangar.json")
    assert pathlib.Path(command[2]).read_text() == "ship-b1 /pics/ship.png --faces 19000 --seed 1\n"
    assert made == {"ship-s1": {"batch": "pixal-1", "take": "ship-b1"},
                    "crane-r1": {"batch": None, "take": "crane-b1"}}


def test_bake_is_one_batch_of_make_chunky_jobs_of_each_props_parts(sandbox, monkeypatch):
    folder, _ = sandbox
    surfaces = folder / "surfaces.json"
    surfaces.write_text(json.dumps({"library": "hangar"}))
    monkeypatch.setattr(prop_makers, "bake_inputs", lambda place: {"surfaces": surfaces})
    monkeypatch.setattr(place_line, "baking_specs", lambda library, specs, folders: {"steel": {"recipe": "steel"}})
    out = folder / "out"

    def baked(command):
        jobs = [json.loads(pathlib.Path(job).read_text()) for job in command[2:command.index("--who")]]
        return [pathlib.Path(job["out"]) / f"{job['chunky'][0]['name']}.gltf" for job in jobs]

    call = StandIn(folder / "ledger.jsonl", "library", baked)
    made = prop_makers.make_bakes(PROPS, out, "test", call)
    [command] = call.commands
    assert command[1].endswith("library_bake.py")
    jobs = [json.loads(pathlib.Path(job).read_text()) for job in command[2:command.index("--who")]]
    assert sorted(job["chunky"][0]["parts"] for job in jobs) == ["/parts/crane", "/parts/ship"]
    assert all(job["specs"] == {"steel": {"recipe": "steel"}} for job in jobs)
    assert made == {"ship-s1": {"batch": "library-1", "model": str(out / "made/ship-b1.gltf")},
                    "crane-r1": {"batch": "library-1", "model": str(out / "made/crane-b1.gltf")}}


def test_a_batch_that_made_nothing_raises(sandbox):
    folder, _ = sandbox
    call = StandIn(folder / "ledger.jsonl", "pixal", lambda command: [], code=1)
    with pytest.raises(RuntimeError, match="made nothing"):
        prop_makers.make_models(PROPS, folder / "out", "test", call)


def test_a_prop_with_no_parts_stops_before_anything_is_paid():
    ok, why = prop_makers.parts_named(dict(PROPS[0], parts=None))
    assert not ok and "names no parts" in why
    assert prop_makers.parts_named(PROPS[0]) == (True, "")
    assert prop_makers.parts_named(dict(PROPS[0], parts=None, keep=["bake"])) == (True, "")
    assert prop_makers.parts_named(dict(PROPS[0], parts=None, body="main_console-s1")) == (True, "")
    ok, why = prop_makers.parts_named(dict(PROPS[0], parts=None, body="ship-s1"))
    assert not ok and "no builder" in why


def test_a_bodied_props_parts_are_written_before_its_bake_and_a_refusal_stops_it(sandbox, monkeypatch):
    folder, _ = sandbox
    bodied = dict(PROPS[0], parts=None, body="ship-s1")
    assert prop_makers.parts_folder(bodied) == folder / "work/body-parts" / bodied["take"]
    written = []
    monkeypatch.setattr(prop_makers, "write_body_parts",
                        lambda prop: (written.append(prop["name"]) or False, "lies 0.3 off"))
    assert prop_makers.check_parts(bodied) == (False, "lies 0.3 off") and written == [bodied["name"]]


def test_a_bodied_props_bake_entry_is_refused_by_name_while_the_repo_library_is_retired(sandbox, monkeypatch):
    import library
    import trimesh
    folder, real_bake_entry = sandbox
    labelled = folder / "labelled/aft_section-t1"
    labelled.mkdir(parents=True)
    trimesh.creation.box(extents=(2.0, 1.0, 1.0)).export(labelled / "hull_white.ply")
    (folder / "surfaces.json").write_text(json.dumps({"place": "wreck", "library": "wreck",
                                                      "bake": {"models": {"aft_section": "aft_section-t1"}}}))
    monkeypatch.setattr(prop_makers, "bake_inputs", lambda place: {"surfaces": folder / "surfaces.json"})
    monkeypatch.setattr(prop_makers, "accepted_labelled", lambda prop: labelled)
    bodied = {"name": "aft_section-t1", "place": "wreck", "take": "aft_section-b2", "body": "aft_section-t1"}
    with pytest.raises(library.LibraryEmpty, match="wreck: no wear"):
        real_bake_entry(bodied)


def test_a_close_up_is_drawn_once_and_one_that_fails_is_a_gap(tmp_path, monkeypatch):
    from PIL import Image
    import stage
    drawn = []
    concept = tmp_path / "concept.png"
    Image.new("RGB", (800, 600), (120, 120, 120)).save(concept)

    def row(prop):
        return {"id": prop["row"], "scene": prop["place"], "words": prop["row"], "size": [1.0, 1.0, 1.0],
                "concept": str(concept), "box": [100, 100, 200, 150]}

    def draw(key, asks):
        for path, (_, _, reference, _) in asks.items():  # text, crop, room, seed (ce306fd2)
            drawn.append((path.name, reference is not None))
            Image.new("RGB", (64, 64), (200, 200, 200)).save(path)  # a plain picture: the shape check fails it
        return dict.fromkeys(asks, True)
    monkeypatch.setattr(prop_makers, "closeup_row", row)
    monkeypatch.setattr(stage.pro, "draw", draw)
    monkeypatch.setitem(sys.modules, "secret_store", types.SimpleNamespace(secret=lambda name: "key"))
    made = prop_makers.make_closeups(PROPS, str(tmp_path))
    assert sorted(drawn) == [("crane.png", True), ("ship.png", True)]  # small crops take the room, once each
    assert made == {}  # both failed their shape check: gaps, not drawn again
