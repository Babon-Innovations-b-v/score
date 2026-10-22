"""The character maker's pure pieces: the spec check, the routes' refusals and the prop route's free steps. Nothing
here loads a model."""
import json
import pathlib
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import spec  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
PERSON = {"name": "someone", "kind": "person", "approved": "the owner", "description": "a person",
          "hair": "short hair", "face": "a face", "route": "prop", "outfit_words": {"work": "a work suit"}}


def test_the_checked_in_specs_can_be_made():
    """Every spec written from a design (data/people/specs, score/stages/people_rows.py) passes the maker's checks and
    carries its person's name (its takes go to that person's candidates folder) in a file named <name>.json."""
    for path in sorted((REPO / "data/people/specs").glob("*.json")):
        found = spec.read(path)
        assert found["name"] == path.stem


def test_a_spec_without_approval_is_refused():
    assert "no approved" in spec.problems_of(dict(PERSON, approved=""))


def test_a_spec_needs_a_picture_or_words():
    problems = spec.problems_of(dict(PERSON, description=None))
    assert "neither a picture nor a description" in problems


def test_a_relative_picture_is_refused_and_one_from_home_is_kept():
    assert any("not an absolute path" in problem for problem in spec.problems_of(dict(PERSON, picture="a.png")))
    assert not spec.problems_of(dict(PERSON, picture="~/a.png"))


def test_an_outfit_without_words_is_refused():
    assert "no outfit_words for gown" in spec.problems_of(dict(PERSON, outfits=["gown"]))
    assert "route 'drape' is not prop" in spec.problems_of(dict(PERSON, route="drape"))


def test_reading_raises_with_every_problem(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"name": "bad", "kind": "robot"}))
    with pytest.raises(spec.SpecError, match="no approved.*kind 'robot'"):
        spec.read(path)


def test_experimental_routes_run_only_when_asked_for_and_the_shipped_chain_never():
    """Fault (audit of 2026-10-11, items 1-3): make.py over the old character specs started paid prop-route runs
    (the player fails tucks and pokes, Nev is not made) and the animal route had never run on a world; the shipped
    person chain and its garment drapes were retired on 2026-10-21, so a person on no route is refused always."""
    import make

    prop = dict(PERSON, name="player_prop")
    animal = {"name": "fish", "kind": "animal", "approved": "the owner", "description": "a fish"}
    shipped = {key: value for key, value in dict(PERSON, name="nev").items() if key != "route"}
    refused = make.refusals([prop, animal, shipped], experimental=False)
    assert [line.split(":")[0] for line in refused] == ["player_prop", "fish", "nev"], refused
    assert [line.split(":")[0] for line in make.refusals([prop, animal, shipped], experimental=True)] == ["nev"]
    assert "retired" in make.refusals([shipped], experimental=True)[0]


def test_the_experimental_routes_refuse_when_started_round_make(tmp_path):
    """Fault (review of 2026-10-11): --experimental was checked only in make.py, so prop_person.py run by hand and
    route.make called directly made a prop-route person or an animal without it."""
    import subprocess
    written = tmp_path / "player.json"
    written.write_text(json.dumps(dict(PERSON, name="player", route="prop", outfit_words={"work": "a work suit"})))
    started = subprocess.run([sys.executable, str(REPO / "tools/characters/maker/prop_person.py"),
                              str(written), "--who", "a check", "--dry-run"],
                             capture_output=True, text=True)
    assert started.returncode != 0 and "only with --experimental" in started.stderr
    sys.path.insert(0, str(REPO / "tools/characters/animals"))
    import route
    with pytest.raises(SystemExit, match="only with make.py --experimental"):
        route.make({"name": "fish_tang"}, tmp_path, "a check", dry_run=True)
    assert not (tmp_path / "work").exists()


def test_an_outfit_without_a_palette_can_name_shoes_as_boots():
    """2026-10-13: with no shoe to choose, the judge gave kit_m_broad's shoes the belt's material."""
    props_python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    if not props_python.exists():
        pytest.skip("no props environment on this box")
    ask = ("import prop_parts; shoes = [name for name in prop_parts.palette_of('uniform-olive') "
           "if name in prop_parts.BOOTS]; print(shoes)")
    found = subprocess.run([str(props_python), "-B", "-c", ask], capture_output=True, text=True,
                           cwd=pathlib.Path(__file__).resolve().parent)
    assert found.returncode == 0 and "black leather shoe" in found.stdout


def test_a_far_surface_with_no_faces_is_left_out_not_crashed_on(tmp_path):
    """2026-10-13: kit_m_broad's wide take has no boot part, and the build crashed on the far body's empty boots."""
    prop_build = pytest.importorskip("prop_build")
    far = tmp_path / "far.npz"
    np.savez(far, points=np.eye(3), faces=np.array([[0, 1, 2]]), surface_of_face=np.array([1]),
             weights=np.ones((3, 27)) / 27, surfaces=np.array(["skin", "clothes", "boots"]),
             colours=np.zeros((3, 3)))
    assert [item[0] for item in prop_build.far_body(far)] == ["clothes"]


def test_any_outfit_with_words_can_be_split_and_one_without_is_refused_on_the_pc(tmp_path):
    """2026-10-13: the parts step refused a kit's uniform-olive after 4 machine-minutes; now an outfit with words takes
    the work suit's material names for its roles, and one with no words is refused by `check` before any machine."""
    props_python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    if not props_python.exists():
        pytest.skip("no props environment on this box")
    script = pathlib.Path(__file__).resolve().parent / "prop_parts.py"
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"outfit_words": {"uniform-olive": "an olive uniform"}}))
    ask = [str(props_python), "-B", str(script), "check", str(tmp_path), "take", str(spec_file), "--outfit"]
    assert subprocess.run(ask + ["uniform-olive"], capture_output=True).returncode == 0
    refused = subprocess.run(ask + ["driver-suit"], capture_output=True, text=True)
    assert refused.returncode != 0 and "no outfit_words" in refused.stderr


def test_a_failed_tucks_record_predicts_a_gap_only_on_the_same_inputs(tmp_path, monkeypatch):
    """#21: the settled pokes.json with a tuck over the gate in every clip writes a record on the hash of the take,
    spec, parts and the maker's and people tools' code, which predicts the same failure (nothing bought); a clip
    that passed writes none, and any changed input, the people tools' code included, predicts nothing."""
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path)
    folder = prop_person.folder_of(PERSON, "work")
    (folder / "parts" / "pp-a_s1").mkdir(parents=True)
    (folder / "checks").mkdir()
    (folder / "take.txt").write_text("pp-a_s1")
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"first parts")
    clips = {"walk": {"worst_tuck_out_mm": 9.32, "frames_tuck_over": 40},
             "idle": {"worst_tuck_out_mm": 6.1, "frames_tuck_over": 0}}
    (folder / "checks" / "pokes.json").write_text(json.dumps({"clips": clips}))
    assert prop_person.tucks_record(PERSON, "work") is None and prop_person.predicted_tucks(PERSON, "work") is None
    clips["idle"]["frames_tuck_over"] = 3
    (folder / "checks" / "pokes.json").write_text(json.dumps({"clips": clips}))
    record = prop_person.tucks_record(PERSON, "work")
    assert record["worst_tuck_out_mm"] == 9.32 and record["clips"] == 2, record
    assert prop_person.predicted_tucks(PERSON, "work") == record
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"new parts")
    assert prop_person.predicted_tucks(PERSON, "work") is None
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"first parts")
    people = tmp_path / "tools" / "people"
    people.mkdir(parents=True)
    (people / "joins.py").write_text("# joins")
    (people / "joins_test.py").write_text("# a test")
    monkeypatch.setattr(prop_person, "HERE", tmp_path / "tools" / "maker")
    (tmp_path / "tools" / "maker").mkdir()
    prop_person.tucks_record(PERSON, "work")
    assert prop_person.predicted_tucks(PERSON, "work") is not None
    (people / "joins_test.py").write_text("# a test, edited")
    assert prop_person.predicted_tucks(PERSON, "work") is not None, "a test edit moved the hash"
    (people / "joins.py").write_text("# joins, fixed")
    assert prop_person.predicted_tucks(PERSON, "work") is None, "a people tools fix left the old prediction"


def test_the_cloth_count_reads_the_routed_bodys_own_node_whatever_its_outfit(tmp_path):
    """The route names a body's node work while its look's outfit is made (2026-10-22): the body-through-cloth count
    is asked for that node, not the outfit's name, so it is not refused on a node the routed body lacks."""
    import struct
    import prop_person
    document = {"nodes": [{"name": "far", "mesh": 0, "skin": 0}, {"name": "work", "mesh": 1, "skin": 0},
                          {"name": "Hips"}], "animations": [{"name": "walking"}]}
    text = json.dumps(document).encode().ljust(-(-len(json.dumps(document)) // 4) * 4, b" ")
    body = tmp_path / "body.glb"
    body.write_bytes(b"glTF" + struct.pack("<II", 2, 28 + len(text)) + struct.pack("<I", len(text)) + b"JSON" + text
                     + struct.pack("<I", 0) + b"BIN\x00")
    commands = prop_person.counts_by_clips(body, tmp_path)
    assert all(command[command.index("--outfit") + 1] == "work" for command in commands.values()), commands


def test_the_identity_is_read_off_the_takes_close_up(tmp_path, monkeypatch):
    """#26: SAM 3D Body reads the body under the clothes off the kept take's close-up (the A-pose picture is lost):
    one characters make whose only step is `identity`, its one file that close-up."""
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path / "candidates")
    monkeypatch.setattr(prop_person, "PIXAL", tmp_path / "pixal")
    asked = []
    monkeypatch.setattr(prop_person, "on_characters", lambda place, who, held, dry_run: asked.append(place))
    folder = prop_person.folder_of(PERSON, "work")
    folder.mkdir(parents=True)
    (folder / "take.txt").write_text("pp-a_s1")
    closeup = tmp_path / "pixal" / "pp-a_s1.svviews" / "input.png"
    closeup.parent.mkdir(parents=True)
    closeup.write_bytes(b"the close-up")
    assert prop_person.identity(PERSON, "work", "a test", None, True) is None
    machine = json.loads((asked[0] / "in" / "spec.json").read_text())
    assert machine["steps"] == ["identity"] and machine["program"] == "prop_chain.py", machine
    assert (asked[0] / machine["files"]["closeup"]).read_bytes() == b"the close-up"
    import prop_chain
    assert "identity" in prop_chain.STEPS


def test_a_kimodo_clip_is_made_with_the_fixed_seed_and_records_it(tmp_path):
    """#26: every clip is asked for with the one fixed seed, and its record beside it names the seed, so a lost clip
    is made again the same."""
    ask = ("import json, sys; import clips; arguments = clips.kimodo_arguments('walking', sys.argv[1]); "
           "clips.write_record('walking', sys.argv[1]); "
           "print(json.dumps([arguments, clips.CLIP_SEED, clips.SENTENCES['walking'][0], clips.MODEL]))")
    # its own process, in the people tools' folder: clips.py is found there by name
    done = subprocess.run([sys.executable, "-c", ask, str(tmp_path / "walking")], capture_output=True, text=True,
                          cwd=REPO / "tools/characters/people", check=True)
    arguments, seed, sentence, model = json.loads(done.stdout.splitlines()[-1])
    assert arguments[arguments.index("--seed") + 1] == str(seed), arguments
    record = json.loads((tmp_path / "walking.record.json").read_text())
    assert record == {"clip": "walking", "sentence": sentence, "seconds": 5.0, "model": model, "seed": seed}, record
    chain_words = (pathlib.Path(__file__).resolve().parent / "chain.py").read_text()
    assert "sentences.kimodo_arguments(name" in chain_words and "sentences.write_record(name" in chain_words


def test_the_route_is_the_bodys_binding_after_the_build(tmp_path, monkeypatch):
    """#26: a full body is put through the people route on the same held machine as its build: one make reading the
    close-up (SAM 3D Body's identity), the fitted rig, the shell's fit and the built body; the garment settle is gone."""
    import prop_chain
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path / "candidates")
    monkeypatch.setattr(prop_person, "PIXAL", tmp_path / "pixal")
    asked = []
    monkeypatch.setattr(prop_person, "on_characters", lambda place, who, held, dry_run: asked.append((place, held)))
    folder = prop_person.folder_of(PERSON, "work")
    for name, words in (("take.txt", "pp-a_s1"), ("fit/rig.npz", "rig"), ("fit/shell.json", "{}"),
                        (f"out/{PERSON['name']}.glb", "built")):
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(words)
    closeup = tmp_path / "pixal" / "pp-a_s1.svviews" / "input.png"
    closeup.parent.mkdir(parents=True)
    closeup.write_bytes(b"the close-up")
    assert prop_person.route(PERSON, "work", "a test", "held", True) is None
    place, held = asked[0]
    machine = json.loads((place / "in" / "spec.json").read_text())
    assert machine["steps"] == ["identity", "route"] and held == "held", machine
    assert {name: (place / path).read_bytes() for name, path in machine["files"].items()} == {
        "closeup": b"the close-up", "fit": b"rig", "shell": b"{}", "body": b"built"}
    assert "settle" not in prop_chain.STEPS and "settle" not in prop_person.STAGE_WORK
    assert {"clips", "rig", "route", "identity"} <= set(prop_chain.STEPS)


def test_the_route_step_rebuilds_the_built_body_on_the_base_under_it(tmp_path):
    """prop_chain's route step: the base from the fitted rig, the shell's fit and the identity, the correctives of
    every clip of the built body, the route's build with them, its UsdSkel asset and its joins record, in that order,
    all on this make's own built body."""
    import prop_chain

    class Chain:
        out, spec, ran = tmp_path / "out", {"person": "a", "files": {"fit": "in/files/fit.npz",
                                                                      "shell": "in/files/shell.json"}}, []

        def file(self, relative):
            return tmp_path / relative

        def run(self, command):
            self.ran.append([str(part) for part in command])
            if pathlib.Path(command[1]).name == "route_build.py":
                pathlib.Path(command[5]).with_suffix(".json").write_text(json.dumps({"head": {"face": "made"}}))

    chain = Chain()
    chain.out.mkdir()
    (chain.out / "a.glb").write_text("built")
    assert prop_chain.route(chain) == "made"
    scripts = [pathlib.Path(command[1]).name + (f" {command[2]}" if command[1].endswith("route_base.py") else "")
               for command in chain.ran]
    assert scripts == ["route_base.py base", "route_base.py correctives", "route_build.py", "skel_usd.py", "joins.py"]
    base, build = chain.ran[0], chain.ran[2]
    assert base[3:6] == [str(tmp_path / "in/files/fit.npz"), str(tmp_path / "in/files/shell.json"),
                         str(chain.out / "identity.npz")]
    assert build[2] == str(chain.out / "a.glb") and build[5] == str(chain.out / "route" / "a.glb")
    assert "--correctives" in build and "--face" not in build, "the face is route_head.FACE, route_build's default"


def test_the_clips_and_the_rig_are_one_make_that_takes_no_clip_from_here(tmp_path, monkeypatch):
    """#26: people-clips-made's make: Kimodo's clips then the rig, on a rented machine; the lost work folder's
    clips are never copied up."""
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path / "candidates")
    asked = []
    monkeypatch.setattr(prop_person, "on_characters", lambda place, who, held, dry_run: asked.append((place, held)))
    assert prop_person.clips_rig(("standing", "bench"), tmp_path / "out", "a test", True) is None
    place, held = asked[0]
    machine = json.loads((place / "in" / "spec.json").read_text())
    assert machine["steps"] == ["clips", "rig"] and machine["clips"] == ["standing", "bench"] and held is None
    assert machine["approved"] and not (place / "in" / "motions").exists()
