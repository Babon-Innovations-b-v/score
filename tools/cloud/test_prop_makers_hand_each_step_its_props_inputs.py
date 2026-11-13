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


class Cloud:
    """A stand-in for subprocess.run serving both paid tools: records each command, writes the outputs the tool would
    bring back (batch.py: each listed take's files; library_bake.py: each job's model) and one ledger line of the
    tool's kind; `down` makes it fail and bring nothing back."""

    KINDS = {"batch.py": "pixal", "library_bake.py": "library"}

    def __init__(self, ledger):
        self.ledger, self.down, self.commands = ledger, False, []

    def __call__(self, command, **_):
        self.commands.append(command)
        kind = self.KINDS[pathlib.Path(command[1]).name]
        for path in [] if self.down else self.outputs(kind, command):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("made")
        count = sum(self.KINDS[pathlib.Path(sent[1]).name] == kind for sent in self.commands)
        with self.ledger.open("a") as ledger:
            ledger.write(json.dumps({"kind": kind, "batch": f"{kind}-{count}"}) + "\n")
        return types.SimpleNamespace(returncode=int(self.down), stdout="", stderr="")

    @staticmethod
    def outputs(kind, command):
        if kind == "pixal":
            listing = pathlib.Path(command[2]).read_text().split("\n")
            return [prop_makers.WORK / "pixal" / f"{line.split()[0]}{suffix}" for line in listing if line
                    for suffix in prop_makers.TAKE_FILES]
        return [pathlib.Path(job["out"]) / f"{job['chunky'][0]['name']}.gltf" for job in bake_jobs(command)]


def bake_jobs(command):
    """The make_chunky jobs a library_bake.py command names."""
    return [json.loads(pathlib.Path(job).read_text()) for job in command[2:command.index("--who")]]


BODIED = dict(PROPS[0], parts=None, body="ship-s1")
# The free checks before anything is paid: (row, check, prop, expected ok, a word its reason holds).
FREE_CHECKS = [
    ("no parts and no body", prop_makers.parts_named, dict(PROPS[0], parts=None), False, "names no parts"),
    ("its own parts", prop_makers.parts_named, PROPS[0], True, ""),
    ("keeps its bake", prop_makers.parts_named, dict(PROPS[0], parts=None, keep=["bake"]), True, ""),
    ("a body with a builder", prop_makers.parts_named, dict(PROPS[0], parts=None, body="main_console-s1"), True, ""),
    ("a body no builder makes", prop_makers.parts_named, BODIED, False, "no builder"),
    ("bodied, its parts refused", prop_makers.check_parts, BODIED, False, "lies 0.3 off"),
]


def test_prop_makers_hand_each_step_its_props_inputs(tmp_path, monkeypatch):
    """One work folder, ledger and cloud: the close-ups, then image-to-3d (down once, then up with the crane's take
    already made), then the bake, each step's inputs read off what the cloud was handed; then the free checks."""
    from PIL import Image
    import library
    import stage
    import trimesh
    real_bake_entry = prop_makers.bake_entry
    out, cloud = tmp_path / "out", Cloud(tmp_path / "ledger.jsonl")
    monkeypatch.setattr(prop_makers, "WORK", tmp_path / "work")
    monkeypatch.setattr(prop_makers, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(prop_makers, "bake_entry",
                        lambda prop: ({"specs": {}}, dict(ENTRY, name=prop["take"], parts=prop["parts"])))
    monkeypatch.setattr(prop_makers, "bake_inputs", lambda place: {"surfaces": tmp_path / f"{place}.json"})
    for place in ("hangar", "campgrounds"):
        (tmp_path / f"{place}.json").write_text(json.dumps({"library": "hangar"}))
    monkeypatch.setattr(place_line, "baking_specs", lambda library, specs, folders: {"steel": {"recipe": "steel"}})

    concept, drawn = tmp_path / "concept.png", []
    Image.new("RGB", (800, 600), (120, 120, 120)).save(concept)

    def draw(asks):  # pro.draw reads its own key since 79df451c
        for path, (_, _, reference, _) in asks.items():  # text, crop, room, seed (ce306fd2)
            drawn.append((path.name, reference is not None))
            Image.new("RGB", (64, 64), (200, 200, 200)).save(path)  # a plain picture: the shape check fails it
        return dict.fromkeys(asks, True)
    monkeypatch.setattr(prop_makers, "closeup_row", lambda prop: {
        "id": prop["row"], "scene": prop["place"], "words": prop["row"], "size": [1.0, 1.0, 1.0],
        "concept": str(concept), "box": [100, 100, 200, 150]})
    monkeypatch.setattr(stage.pro, "draw", draw)
    monkeypatch.setitem(sys.modules, "secret_store", types.SimpleNamespace(secret=lambda name: "key"))

    closeups = prop_makers.make_closeups(PROPS, str(out))
    assert sorted(drawn) == [("crane.png", True), ("ship.png", True)]  # small crops take the room, once each
    assert closeups == {}  # both failed their shape check: gaps, not drawn again

    cloud.down = True
    with pytest.raises(RuntimeError, match="made nothing"):
        prop_makers.make_models(PROPS, out, "test", cloud)
    cloud.down = False
    (tmp_path / "work/pixal").mkdir(parents=True, exist_ok=True)
    for suffix in prop_makers.TAKE_FILES:
        (tmp_path / "work/pixal" / f"crane-b1{suffix}").write_text("made before")
    models = prop_makers.make_models(PROPS, out, "test", cloud)
    bakes = prop_makers.make_bakes(PROPS, out, "test", cloud)

    _, models_sent, bake_sent = cloud.commands
    assert models_sent[1].endswith("batch.py") and models_sent[models_sent.index("--inventory") + 1].endswith("hangar.json")
    # the made crane is not asked again; the failed close-up is not used, the kept picture is
    assert pathlib.Path(models_sent[2]).read_text() == "ship-b1 /pics/ship.png --faces 19000 --seed 1\n"
    assert models == {"ship-s1": {"batch": "pixal-2", "take": "ship-b1"},
                      "crane-r1": {"batch": None, "take": "crane-b1"}}
    assert bake_sent[1].endswith("library_bake.py")
    jobs = bake_jobs(bake_sent)
    assert sorted(job["chunky"][0]["parts"] for job in jobs) == ["/parts/crane", "/parts/ship"]
    assert all(job["specs"] == {"steel": {"recipe": "steel"}} for job in jobs)
    assert bakes == {"ship-s1": {"batch": "library-1", "model": str(out / "made/ship-b1.gltf")},
                     "crane-r1": {"batch": "library-1", "model": str(out / "made/crane-b1.gltf")}}

    written = []
    monkeypatch.setattr(prop_makers, "write_body_parts",
                        lambda prop: (written.append(prop["name"]) or False, "lies 0.3 off"))
    assert prop_makers.parts_folder(BODIED) == tmp_path / "work/body-parts" / BODIED["take"]
    for row, check, prop, ok, word in FREE_CHECKS:
        got_ok, why = check(prop)
        assert got_ok is ok and word in why and (why == "") is ok, f"{row}: {(got_ok, why)}"
    assert written == [BODIED["name"]]  # a bodied prop's parts are written before its bake is judged

    labelled = tmp_path / "labelled/aft_section-t1"
    labelled.mkdir(parents=True)
    trimesh.creation.box(extents=(2.0, 1.0, 1.0)).export(labelled / "hull_white.ply")
    (tmp_path / "wreck.json").write_text(json.dumps({"place": "wreck", "library": "wreck",
                                                     "bake": {"models": {"aft_section": "aft_section-t1"}}}))
    monkeypatch.setattr(prop_makers, "accepted_labelled", lambda prop: labelled)
    with pytest.raises(library.LibraryEmpty, match="wreck: no wear"):  # the repo library is retired (2026-10-21)
        real_bake_entry({"name": "aft_section-t1", "place": "wreck", "take": "aft_section-b2", "body": "aft_section-t1"})
